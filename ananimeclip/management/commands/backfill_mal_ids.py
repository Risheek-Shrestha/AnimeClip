"""
Management command: backfill_mal_ids
======================================
For your original hand-entered catalog (the Anime/Movie rows with no
mal_id), search Jikan by title and link a matching MAL entry. This is
NON-DESTRUCTIVE: it only ever sets mal_id, plus studio/genres if those
happen to be empty already. It NEVER touches your hand-written
description, rating, or age_rating — your manual curation on those stays
exactly as you wrote it.

Matching is conservative on purpose: only an exact (case-insensitive)
title match against Jikan's `title` or `title_english` is applied
automatically. Everything else is printed as a "needs review" line so
you can fix the title manually and re-run, instead of silently linking
to the wrong show.

If the matched mal_id already belongs to a DIFFERENT row in your catalog
(e.g. you also ran `import_catalog` and it separately pulled in the same
show under its own row), that's a sign of a duplicate entry — this command
reports it as a conflict and skips it rather than crashing the whole run.

    python manage.py backfill_mal_ids --type anime
    python manage.py backfill_mal_ids --type movie
    python manage.py backfill_mal_ids --type anime --dry-run
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import IntegrityError

from ananimeclip.models import Anime, Genre, Movie

logger = logging.getLogger(__name__)

JIKAN_BASE = "https://api.jikan.moe/v4"
REQUEST_DELAY_SECONDS = 1.0


def _http_get_json(url: str, retries: int = 3) -> dict:
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AnimeClip-Importer/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429 and attempt < retries - 1:
                time.sleep(int(e.headers.get("Retry-After", 5)))
                continue
            raise
        except urllib.error.URLError as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_error


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
    help = "Link hand-entered Anime/Movie rows to a MAL id by exact title match, non-destructively."

    def add_arguments(self, parser):
        parser.add_argument("--type", choices=["anime", "movie"], required=True)
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Only print matches/candidates, don't write anything.",
        )

    def handle(self, *args, **options):
        media_type = options["type"]
        dry_run = options["dry_run"]
        model_cls = Anime if media_type == "anime" else Movie
        expected_jikan_type = "tv" if media_type == "anime" else "movie"

        unlinked = model_cls.objects.filter(mal_id__isnull=True)
        total = unlinked.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                f"Nothing to backfill — every {media_type} already has a mal_id."
            ))
            return

        self.stdout.write(f"Searching Jikan for {total} unlinked {media_type} entries …")

        linked = needs_review = conflicts = 0

        for obj in unlinked:
            query = urllib.parse.quote(obj.title)
            url = f"{JIKAN_BASE}/anime?q={query}&type={expected_jikan_type}&sfw=true&limit=5"
            try:
                payload = _http_get_json(url)
            except Exception as exc:
                self.stderr.write(f"  ! search failed for '{obj.title}': {exc}")
                needs_review += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            candidates = (payload or {}).get("data", [])
            match = self._find_exact_match(obj.title, candidates)

            if not match:
                if candidates:
                    top = candidates[0]
                    self.stdout.write(
                        f"  ? '{obj.title}' — no exact match. Closest: "
                        f"'{top.get('title_english') or top.get('title')}' (mal_id={top.get('mal_id')})"
                    )
                else:
                    self.stdout.write(f"  ? '{obj.title}' — no results at all on Jikan.")
                needs_review += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            if dry_run:
                self.stdout.write(f"  [dry-run] would link '{obj.title}' -> mal_id={match['mal_id']}")
                linked += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            # A failed save() inside an atomic() block only rolls back that
            # one savepoint, not the whole connection — so one collision
            # (e.g. this title was *also* pulled in separately by
            # import_catalog and already owns this mal_id) can't poison
            # the rest of the batch on Postgres.
            try:
                with transaction.atomic():
                    self._apply_match(obj, match)
            except IntegrityError:
                existing = model_cls.objects.filter(mal_id=match["mal_id"]).exclude(pk=obj.pk).first()
                existing_note = f" ('{existing.title}', id={existing.pk})" if existing else ""
                self.stderr.write(
                    f"  ! '{obj.title}' -> mal_id={match['mal_id']} conflicts with an "
                    f"existing row{existing_note} — likely a duplicate already imported "
                    f"separately. Skipped; not linked."
                )
                conflicts += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            self.stdout.write(f"  linked: '{obj.title}' -> mal_id={match['mal_id']}")
            linked += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        verb = "Would link" if dry_run else "Linked"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {linked} entries; {needs_review} need manual review "
            f"(title mismatch or no results); {conflicts} skipped due to mal_id "
            f"conflicts with an existing duplicate row."
        ))

    def _apply_match(self, obj, match: dict) -> None:
        """Non-destructive: only fills mal_id, and studio/genres if currently empty."""
        obj.mal_id = match["mal_id"]
        if not obj.studio:
            studios = match.get("studios") or []
            if studios:
                obj.studio = studios[0].get("name", "")[:100]
        obj.save(update_fields=["mal_id", "studio"])

        if obj.genres.count() == 0:
            genres_data = (match.get("genres") or []) + (match.get("explicit_genres") or [])
            obj.genres.set(_get_or_create_genres(genres_data))

    @staticmethod
    def _find_exact_match(title: str, candidates: list):
        target = title.strip().lower()
        for c in candidates:
            names = {
                (c.get("title") or "").strip().lower(),
                (c.get("title_english") or "").strip().lower(),
            }
            if target in names:
                return c
        return None