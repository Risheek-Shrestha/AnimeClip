"""
Management command: import_catalog
====================================
Pulls real anime/movie catalog metadata from Jikan — a free, unofficial
MyAnimeList REST API that needs no API key (https://docs.api.jikan.moe/) —
and upserts it into the Anime/Movie tables, instead of typing entries in
by hand.

Only CATALOG metadata is imported: title, synopsis, studio, genres,
score/rating, age rating, release date/duration, and (optionally) poster
art. Seasons, episodes, and video sources are deliberately NOT imported —
this app hosts its own video files, so you still need to add those
yourself for anything you actually want to stream. This command exists to
solve a different problem: giving the recommendation engine (content-based
TF-IDF + collaborative SVD) enough catalog breadth and genre variety to
have something real to work with, beyond 21 anime / 20 movies.

Examples:

    python manage.py import_catalog --type anime --count 50
    python manage.py import_catalog --type movie --count 30
    python manage.py import_catalog --type anime --count 50 --with-images
    python manage.py import_catalog --type anime --count 20 --dry-run

Notes:
  - `--with-images` downloads poster art and saves it as a MediaImage,
    which is uploaded through whatever storage backend is configured
    (Cloudinary in this project) — make sure CLOUDINARY_* env vars are
    set before using this flag, or it'll log failures and skip images.
  - Uses `mal_id` to upsert, so re-running this command is safe: existing
    rows get their metadata refreshed instead of duplicated.
  - Excludes 18+ "Rx"/hentai content (sfw=true) and excludes age_rating='r'
    entries are still imported but tagged 'r' — RecommendationEngine
    already filters those out for any user without a recorded adult age.
  - Sleeps 1s between paginated requests to stay well under Jikan's
    documented rate limit (3 req/sec, 60 req/min).
"""

import json
import logging
import re
import time
import urllib.error
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from ananimeclip.models import Anime, Genre, MediaImage, Movie

logger = logging.getLogger(__name__)

JIKAN_BASE = "https://api.jikan.moe/v4"
REQUEST_DELAY_SECONDS = 1.0  # stay well under Jikan's published rate limit

AGE_RATING_MAP = {
    "G": "pg",
    "PG": "pg",
    "PG-13": "pg13",
    "R": "r",
    "R+": "r",
    "Rx": "r",
}


def _http_get_json(url: str, retries: int = 3) -> dict:
    """GET a URL and return parsed JSON, retrying on 429/5xx with backoff."""
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AnimeClip-Importer/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429 and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", 5))
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_error


def _download_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AnimeClip-Importer/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def _parse_age_rating(raw: str | None) -> str:
    if not raw:
        return "pg13"
    code = raw.split(" - ")[0].strip()
    return AGE_RATING_MAP.get(code, "pg13")


def _parse_duration_minutes(raw: str | None) -> int:
    """Parse Jikan's free-text duration ('2 hr 15 min', '24 min per ep') into minutes."""
    if not raw:
        return 0
    hours = re.search(r"(\d+)\s*hr", raw)
    minutes = re.search(r"(\d+)\s*min", raw)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total


def _get_or_create_genres(genre_dicts) -> list:
    genres = []
    for g in genre_dicts or []:
        name = (g.get("name") or "").strip().lower()
        if not name:
            continue
        genre, _ = Genre.objects.get_or_create(name=name)
        genres.append(genre)
    return genres


class Command(BaseCommand):
    help = "Import anime/movie catalog metadata from the Jikan (MyAnimeList) API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type", choices=["anime", "movie"], required=True,
            help="Which content type to import: 'anime' (TV series) or 'movie'.",
        )
        parser.add_argument(
            "--count", type=int, default=25,
            help="How many items to import (default: 25).",
        )
        parser.add_argument(
            "--with-images", action="store_true",
            help="Also download and attach poster art as a MediaImage. "
                 "Requires your storage backend (Cloudinary) to be configured.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be imported without writing to the database.",
        )

    def handle(self, *args, **options):
        media_type  = options["type"]
        count       = options["count"]
        with_images = options["with_images"]
        dry_run     = options["dry_run"]

        jikan_type = "tv" if media_type == "anime" else "movie"
        model_cls  = Anime if media_type == "anime" else Movie

        created_count = updated_count = skipped_count = 0
        page = 1

        while created_count + updated_count < count:
            url = (
                f"{JIKAN_BASE}/top/anime"
                f"?type={jikan_type}&filter=bypopularity&sfw=true&page={page}"
            )
            self.stdout.write(f"Fetching {url} …")
            try:
                payload = _http_get_json(url)
            except Exception as exc:
                raise CommandError(f"Failed to reach Jikan API: {exc}")

            entries = (payload or {}).get("data", [])
            if not entries:
                self.stdout.write("No more results from Jikan.")
                break

            for entry in entries:
                if created_count + updated_count >= count:
                    break
                try:
                    result = self._import_entry(entry, model_cls, media_type, with_images, dry_run)
                except Exception:
                    logger.exception("Failed to import mal_id=%s", entry.get("mal_id"))
                    result = None

                if result is True:
                    created_count += 1
                elif result is False:
                    updated_count += 1
                else:
                    skipped_count += 1

            if not (payload.get("pagination") or {}).get("has_next_page"):
                self.stdout.write("Reached the last page of results.")
                break

            page += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        verb = "Would import" if dry_run else "Imported"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {created_count} new + updated {updated_count} existing "
            f"{media_type} entries ({skipped_count} skipped)."
        ))

    def _import_entry(self, entry: dict, model_cls, media_type: str, with_images: bool, dry_run: bool):
        """Returns True (created), False (updated), or None (skipped)."""
        mal_id = entry.get("mal_id")
        title = entry.get("title_english") or entry.get("title") or ""
        if not mal_id or not title:
            return None

        genres_data = (entry.get("genres") or []) + (entry.get("explicit_genres") or [])
        studios = entry.get("studios") or []
        studio = studios[0].get("name", "") if studios else ""

        defaults = {
            "title": title[:100],
            "description": (entry.get("synopsis") or "")[:5000],
            "studio": studio[:100],
            "country": "Japan",
        }

        score = entry.get("score")
        if score:
            defaults["rating"] = round(score, 1)

        if media_type == "anime":
            defaults["age_rating"] = _parse_age_rating(entry.get("rating"))
        else:
            duration_mins = _parse_duration_minutes(entry.get("duration"))
            if duration_mins:
                defaults["duration_mins"] = duration_mins
            aired_from = (entry.get("aired") or {}).get("from")
            if aired_from:
                defaults["release_date"] = aired_from[:10]

        if dry_run:
            self.stdout.write(f"  [dry-run] {model_cls.__name__}: {title} (mal_id={mal_id})")
            return None

        obj, created = model_cls.objects.update_or_create(mal_id=mal_id, defaults=defaults)
        obj.genres.set(_get_or_create_genres(genres_data))

        if with_images:
            self._attach_poster(entry, obj, media_type)

        self.stdout.write(f"  {'created' if created else 'updated'}: {title}")
        return created

    def _attach_poster(self, entry: dict, obj, media_type: str) -> None:
        if obj.media_images.filter(type='poster').exists():
            return  # already has one, don't re-download every run

        images = (entry.get("images") or {}).get("jpg") or {}
        image_url = images.get("large_image_url") or images.get("image_url")
        if not image_url:
            return

        try:
            content = _download_bytes(image_url)
            media_image = MediaImage(type='poster')
            if media_type == "anime":
                media_image.anime = obj
            else:
                media_image.movie = obj
            filename = f"{slugify(obj.title)}-poster.jpg"
            media_image.image.save(filename, ContentFile(content), save=True)
        except Exception:
            logger.exception("Failed to download/store poster for %s", obj.title)