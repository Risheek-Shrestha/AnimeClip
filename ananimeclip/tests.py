import hashlib
import hmac
import re
import time
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import (
    Anime,
    Episode,
    Follow,
    Genre,
    Movie,
    MovieSource,
    Notification,
    Playlist,
    PlaylistItem,
    Profile,
    Season,
    SubProfile,
    Subtitle,
    VideoSource,
    WatchHistory,
    WatchLater,
)
from .video_access import _build_cloudinary_auth_token, sign_video_url, to_hls_url, unsign_video_url

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def make_user(username='testuser', password='pass1234', age=25):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    Profile.objects.create(user=user, age=age)
    return user


def make_anime(title='Test Anime', rating=7.5):
    return Anime.objects.create(title=title, description='desc', rating=rating)


def make_movie(title='Test Movie', duration_mins=90, rating=7.0):
    return Movie.objects.create(title=title, description='desc', duration_mins=duration_mins, rating=rating)


def make_episode(anime, season_num=1, ep_num=1, duration_mins=24):
    season, _ = Season.objects.get_or_create(anime=anime, number=season_num)
    return Episode.objects.create(season=season, number=ep_num, duration_mins=duration_mins)


# ──────────────────────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────────────────────


class ProfileModelTest(TestCase):
    def test_profile_created_with_valid_age(self):
        user = make_user(age=20)
        self.assertEqual(user.profile.age, 20)

    def test_str_returns_username(self):
        user = make_user()
        self.assertIn(user.username, str(user.profile))


class EpisodeDurationTest(TestCase):
    def test_episode_has_duration_mins(self):
        anime = make_anime()
        ep = make_episode(anime, duration_mins=24)
        self.assertEqual(ep.duration_mins, 24)

    def test_episode_duration_defaults_to_zero(self):
        anime = make_anime()
        season = Season.objects.create(anime=anime, number=1)
        ep = Episode.objects.create(season=season, number=1)
        self.assertEqual(ep.duration_mins, 0)


class WatchHistoryModelTest(TestCase):
    def test_create_episode_history(self):
        user = make_user()
        sp = SubProfile.objects.create(user=user, name='Main')
        ep = make_episode(make_anime())
        wh = WatchHistory.objects.create(user=user, subprofile=sp, episode=ep, progress_seconds=120)
        self.assertEqual(wh.progress_seconds, 120)

    def test_create_movie_history(self):
        user = make_user()
        sp = SubProfile.objects.create(user=user, name='Main')
        wh = WatchHistory.objects.create(user=user, subprofile=sp, movie=make_movie(), progress_seconds=600)
        self.assertEqual(wh.progress_seconds, 600)

    def test_unique_per_episode(self):
        from django.db import IntegrityError

        user = make_user()
        anime = make_anime()
        ep = make_episode(anime)
        sp = SubProfile.objects.create(user=user, name='Main')  # <-- add this
        WatchHistory.objects.create(user=user, subprofile=sp, episode=ep, progress_seconds=10)
        with self.assertRaises(IntegrityError):
            WatchHistory.objects.create(user=user, subprofile=sp, episode=ep, progress_seconds=20)


# ──────────────────────────────────────────────────────────────
# View tests — Authentication
# ──────────────────────────────────────────────────────────────


class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.core.cache import cache

        cache.clear()

    def test_signup_valid_age(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Alice',
                'email': 'alice@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 22,
            },
        )
        # Email verification flow: signup shows a "check your email" page
        # rather than logging the user in immediately.
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'verify_pending.html')
        user = User.objects.filter(username='alice@test.com').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)

    def test_signup_age_too_low_rejected(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Baby',
                'email': 'baby@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 5,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')
        self.assertFalse(User.objects.filter(username='baby@test.com').exists())

    def test_signup_age_too_high_rejected(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Elder',
                'email': 'elder@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 90,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')

    def test_signup_non_integer_age_rejected(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Hacker',
                'email': 'hack@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 'abc',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')

    def test_signup_password_mismatch(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Bob',
                'email': 'bob@test.com',
                'password': 'secret123',
                'confirm_password': 'wrong',
                'age': 25,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='bob@test.com').exists())

    def test_login_redirects_on_success(self):
        make_user(username='loginuser@test.com', password='pass1234')
        resp = self.client.post(
            reverse('login'),
            {
                'email': 'loginuser@test.com',
                'password': 'pass1234',
            },
        )
        self.assertRedirects(resp, reverse('index'))

    def test_login_fails_bad_password(self):
        make_user(username='loginuser2@test.com', password='pass1234')
        resp = self.client.post(
            reverse('login'),
            {
                'email': 'loginuser2@test.com',
                'password': 'wrongpassword',
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_verify_email_activates_account(self):
        self.client.post(
            reverse('signup'),
            {
                'name': 'Carol',
                'email': 'carol@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 22,
            },
        )
        user = User.objects.get(username='carol@test.com')
        token = user.profile.verification_token
        resp = self.client.get(reverse('verify_email', args=[token]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'verify_success.html')
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.profile.email_verified)

    def test_verify_email_expired_link_rejected(self):
        from datetime import timedelta

        from django.utils import timezone

        self.client.post(
            reverse('signup'),
            {
                'name': 'Dave',
                'email': 'dave@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 22,
            },
        )
        user = User.objects.get(username='dave@test.com')
        profile = user.profile
        token = profile.verification_token
        profile.verification_sent_at = timezone.now() - timedelta(hours=25)
        profile.save(update_fields=['verification_sent_at'])

        resp = self.client.get(reverse('verify_email', args=[token]))
        self.assertContains(resp, 'expired')
        user.refresh_from_db()
        self.assertFalse(user.is_active)


# ──────────────────────────────────────────────────────────────
# Rate limiting must fail OPEN, not closed, when the cache is down.
#
# django-ratelimit treats a cache it can't read/write as "rate limited".
# Combined with IGNORE_EXCEPTIONS on the Redis cache backend, an outage of
# Redis alone — with no code change, no attacker, no actual traffic spike —
# would otherwise silently block every login and signup attempt. This is
# exactly what happened in CI, which never provisions a Redis service.
# RATELIMIT_FAIL_OPEN in settings.py is the fix; this test guards it.
# ──────────────────────────────────────────────────────────────

_UNREACHABLE_CACHE = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # Nothing listens here — guaranteed connection failure, regardless
        # of whether a real Redis happens to be running wherever this test
        # executes.
        'LOCATION': 'redis://127.0.0.1:6399/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
            'SOCKET_CONNECT_TIMEOUT': 1,
            'SOCKET_TIMEOUT': 1,
        },
    }
}


@override_settings(CACHES=_UNREACHABLE_CACHE)
class RateLimitFailsOpenTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_proceeds_when_cache_unreachable(self):
        resp = self.client.post(
            reverse('signup'),
            {
                'name': 'Eve',
                'email': 'eve@test.com',
                'password': 'secret123',
                'confirm_password': 'secret123',
                'age': 22,
            },
        )
        self.assertTemplateUsed(resp, 'verify_pending.html')
        self.assertTrue(User.objects.filter(username='eve@test.com').exists())

    def test_login_proceeds_when_cache_unreachable(self):
        make_user(username='cachefail@test.com', password='pass1234')
        resp = self.client.post(
            reverse('login'),
            {
                'email': 'cachefail@test.com',
                'password': 'pass1234',
            },
        )
        self.assertRedirects(resp, reverse('index'))


# ──────────────────────────────────────────────────────────────
# View tests — Watch History
# ──────────────────────────────────────────────────────────────


class UpdateWatchHistoryViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.anime = make_anime()
        self.ep = make_episode(self.anime)
        self.movie = make_movie()
        self.url = reverse('update_watch_history')

    def test_saves_episode_progress(self):
        resp = self.client.post(
            self.url,
            {
                'episode_id': self.ep.id,
                'progress_seconds': 300,
            },
        )
        self.assertEqual(resp.status_code, 200)
        wh = WatchHistory.objects.get(user=self.user, episode=self.ep)
        self.assertEqual(wh.progress_seconds, 300)

    def test_saves_movie_progress(self):
        resp = self.client.post(
            self.url,
            {
                'movie_id': self.movie.id,
                'progress_seconds': 600,
            },
        )
        self.assertEqual(resp.status_code, 200)
        wh = WatchHistory.objects.get(user=self.user, movie=self.movie)
        self.assertEqual(wh.progress_seconds, 600)

    def test_malformed_progress_returns_400(self):
        resp = self.client.post(
            self.url,
            {
                'episode_id': self.ep.id,
                'progress_seconds': 'not_a_number',
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_id_returns_400(self):
        resp = self.client.post(self.url, {'progress_seconds': 100})
        self.assertEqual(resp.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.post(
            self.url,
            {
                'episode_id': self.ep.id,
                'progress_seconds': 100,
            },
        )
        self.assertEqual(resp.status_code, 302)


# ──────────────────────────────────────────────────────────────
# View tests — Continue Watching progress percentage
# ──────────────────────────────────────────────────────────────


class ContinueWatchingProgressTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)

    def test_progress_pct_episode(self):
        anime = make_anime()
        ep = make_episode(anime, duration_mins=24)  # 1440 seconds
        WatchHistory.objects.create(user=self.user, episode=ep, progress_seconds=720)
        resp = self.client.get(reverse('continue_watching'))
        self.assertEqual(resp.status_code, 200)
        entry = resp.context['history'][0]
        self.assertEqual(entry.progress_pct, 50)

    def test_progress_pct_movie(self):
        movie = make_movie(duration_mins=100)  # 6000 seconds
        WatchHistory.objects.create(user=self.user, movie=movie, progress_seconds=3000)
        resp = self.client.get(reverse('continue_watching'))
        self.assertEqual(resp.status_code, 200)
        entry = resp.context['history'][0]
        self.assertEqual(entry.progress_pct, 50)

    def test_progress_pct_zero_when_no_duration(self):
        anime = make_anime()
        ep = make_episode(anime, duration_mins=0)
        WatchHistory.objects.create(user=self.user, episode=ep, progress_seconds=120)
        resp = self.client.get(reverse('continue_watching'))
        entry = resp.context['history'][0]
        self.assertEqual(entry.progress_pct, 0)

    def test_progress_pct_capped_at_100(self):
        movie = make_movie(duration_mins=10)
        WatchHistory.objects.create(user=self.user, movie=movie, progress_seconds=9999)
        resp = self.client.get(reverse('continue_watching'))
        entry = resp.context['history'][0]
        self.assertEqual(entry.progress_pct, 100)


# ──────────────────────────────────────────────────────────────
# View tests — Watch Later
# ──────────────────────────────────────────────────────────────


class WatchLaterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.anime = make_anime()
        self.ep = make_episode(self.anime)
        self.movie = make_movie()

    def test_toggle_adds_episode(self):
        resp = self.client.post(
            reverse('toggle_watch_later'),
            {
                'episode_id': self.ep.id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'added')
        self.assertTrue(WatchLater.objects.filter(user=self.user, episode=self.ep).exists())

    def test_toggle_removes_episode(self):
        WatchLater.objects.create(user=self.user, episode=self.ep)
        resp = self.client.post(
            reverse('toggle_watch_later'),
            {
                'episode_id': self.ep.id,
            },
        )
        self.assertEqual(resp.json()['status'], 'removed')
        self.assertFalse(WatchLater.objects.filter(user=self.user, episode=self.ep).exists())

    def test_toggle_adds_movie(self):
        resp = self.client.post(reverse('toggle_watch_later'), {'movie_id': self.movie.id})
        self.assertEqual(resp.json()['status'], 'added')


# ──────────────────────────────────────────────────────────────
# View tests — Playlists
# ──────────────────────────────────────────────────────────────


class PlaylistViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.anime = make_anime()
        self.ep = make_episode(self.anime)
        self.movie = make_movie()

    def test_create_playlist(self):
        resp = self.client.post(reverse('create_playlist'), {'name': 'My List'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Playlist.objects.filter(user=self.user, name='My List').exists())

    def test_add_episode_to_playlist(self):
        pl = Playlist.objects.create(user=self.user, name='Favs')
        resp = self.client.post(
            reverse('add_to_playlist'),
            {
                'playlist_id': pl.id,
                'episode_id': self.ep.id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PlaylistItem.objects.filter(playlist=pl, episode=self.ep).exists())

    def test_add_movie_to_playlist(self):
        pl = Playlist.objects.create(user=self.user, name='Favs')
        resp = self.client.post(
            reverse('add_to_playlist'),
            {
                'playlist_id': pl.id,
                'movie_id': self.movie.id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PlaylistItem.objects.filter(playlist=pl, movie=self.movie).exists())

    def test_remove_item_from_playlist(self):
        pl = Playlist.objects.create(user=self.user, name='Favs')
        item = PlaylistItem.objects.create(playlist=pl, episode=self.ep)
        resp = self.client.post(reverse('remove_from_playlist', args=[item.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(PlaylistItem.objects.filter(id=item.id).exists())

    def test_delete_playlist(self):
        pl = Playlist.objects.create(user=self.user, name='ToDelete')
        resp = self.client.post(reverse('delete_playlist', args=[pl.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Playlist.objects.filter(id=pl.id).exists())

    def test_cannot_add_to_other_users_playlist(self):
        other = make_user(username='other@test.com')
        pl = Playlist.objects.create(user=other, name='Private')
        resp = self.client.post(
            reverse('add_to_playlist'),
            {
                'playlist_id': pl.id,
                'episode_id': self.ep.id,
            },
        )
        # Should be 403/404, not silently succeed
        self.assertIn(resp.status_code, [403, 404])

    def test_add_to_playlist_without_episode_or_movie_id_errors(self):
        pl = Playlist.objects.create(user=self.user, name='Favs')
        resp = self.client.post(reverse('add_to_playlist'), {'playlist_id': pl.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')


# ──────────────────────────────────────────────────────────────
# View tests — Index / Personalised Recommendations
# ──────────────────────────────────────────────────────────────


class IndexRecommendationsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)

    def test_no_recommendations_without_history(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context['recommended_animes']), [])
        # Movie recommendations live on the Movies page, not the homepage.

    def test_recommendations_populated_from_watch_history(self):
        genre = Genre.objects.create(name='Action')

        # Watched anime
        watched = make_anime(title='Watched Anime')
        watched.genres.add(genre)
        ep = make_episode(watched)
        WatchHistory.objects.create(user=self.user, episode=ep, progress_seconds=100)

        # Un-watched anime in same genre
        fresh = make_anime(title='Fresh Anime', rating=9.0)
        fresh.genres.add(genre)

        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        rec_titles = [a.title for a in resp.context['recommended_animes']]
        self.assertIn('Fresh Anime', rec_titles)
        self.assertNotIn('Watched Anime', rec_titles)

    def test_watched_anime_excluded_from_recommendations(self):
        genre = Genre.objects.create(name='Drama')
        anime = make_anime(title='Already Watched')
        anime.genres.add(genre)
        ep = make_episode(anime)
        WatchHistory.objects.create(user=self.user, episode=ep, progress_seconds=500)

        resp = self.client.get(reverse('index'))
        rec_titles = [a.title for a in resp.context['recommended_animes']]
        self.assertNotIn('Already Watched', rec_titles)


# ──────────────────────────────────────────────────────────────
# View tests — Search results page renders for every code path
# (regression: a stray {% endif %} previously made this 500 always)
# ──────────────────────────────────────────────────────────────


class SearchResultsViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_search_with_no_results_renders(self):
        resp = self.client.get(reverse('search_results'), {'q': 'NoSuchTitleAtAll'})
        self.assertEqual(resp.status_code, 200)

    def test_search_with_anime_result_renders(self):
        anime = make_anime(title='Searchable Anime')
        make_episode(anime)
        resp = self.client.get(reverse('search_results'), {'q': 'Searchable'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Searchable Anime')

    def test_search_with_movie_result_renders(self):
        make_movie(title='Searchable Movie')
        resp = self.client.get(reverse('search_results'), {'q': 'Searchable'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Searchable Movie')


# ──────────────────────────────────────────────────────────────
# View tests — Search filters (sort, year range, dub/sub)
# (regression: sort=rating referenced a non-existent `average_rating`
# field; sort=newest/oldest and year_from/year_to referenced
# `release_date` on Anime, which only exists on Season; lang=dub/sub
# referenced VideoSource.language, but the real field is `type` —
# all three were 500s whenever these params were used)
# ──────────────────────────────────────────────────────────────


class SearchResultsFilterTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_sort_by_rating_does_not_crash_and_orders_correctly(self):
        make_anime(title='Searchable Low Rated', rating=3.0)
        make_anime(title='Searchable High Rated', rating=9.5)

        resp = self.client.get(reverse('search_results'), {'q': 'Searchable', 'sort': 'rating'})
        self.assertEqual(resp.status_code, 200)
        titles = [a.title for a in resp.context['anime_list']]
        self.assertEqual(titles, ['Searchable High Rated', 'Searchable Low Rated'])

    def test_sort_newest_does_not_crash_and_orders_by_season_release_date(self):
        old = make_anime(title='Searchable Old Anime')
        Season.objects.create(anime=old, number=1, release_date=date(2010, 1, 1))
        new = make_anime(title='Searchable New Anime')
        Season.objects.create(anime=new, number=1, release_date=date(2022, 1, 1))

        resp = self.client.get(reverse('search_results'), {'q': 'Searchable', 'sort': 'newest'})
        self.assertEqual(resp.status_code, 200)
        titles = [a.title for a in resp.context['anime_list']]
        self.assertEqual(titles, ['Searchable New Anime', 'Searchable Old Anime'])

    def test_year_from_filter_does_not_crash_for_anime(self):
        old = make_anime(title='Searchable Old Anime')
        Season.objects.create(anime=old, number=1, release_date=date(2010, 1, 1))
        new = make_anime(title='Searchable New Anime')
        Season.objects.create(anime=new, number=1, release_date=date(2022, 1, 1))

        resp = self.client.get(reverse('search_results'), {'q': 'Searchable', 'year_from': '2020'})
        self.assertEqual(resp.status_code, 200)
        titles = [a.title for a in resp.context['anime_list']]
        self.assertEqual(titles, ['Searchable New Anime'])

    def test_lang_filter_does_not_crash_and_filters_by_source_type(self):
        dubbed = make_anime(title='Searchable Dubbed Anime')
        dubbed_ep = make_episode(dubbed)
        VideoSource.objects.create(episode=dubbed_ep, label='1080p', type='dub', video_url='https://example.com/v.mp4')

        sub_only = make_anime(title='Searchable Subbed Only Anime')
        sub_ep = make_episode(sub_only)
        VideoSource.objects.create(episode=sub_ep, label='1080p', type='sub', video_url='https://example.com/v2.mp4')

        resp = self.client.get(reverse('search_results'), {'q': 'Searchable', 'lang': 'dub'})
        self.assertEqual(resp.status_code, 200)
        titles = [a.title for a in resp.context['anime_list']]
        self.assertIn('Searchable Dubbed Anime', titles)
        self.assertNotIn('Searchable Subbed Only Anime', titles)


# ──────────────────────────────────────────────────────────────
# View tests — "Browse all" pages render
# (regression: these included "_browse_filters.html", a file that
# didn't exist — the real file was named "browse_filters.html")
# ──────────────────────────────────────────────────────────────


class BrowseAllPagesViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_all_recent_movies_renders(self):
        resp = self.client.get(reverse('all_recent_movies'))
        self.assertEqual(resp.status_code, 200)

    def test_all_popular_movies_renders(self):
        resp = self.client.get(reverse('all_popular_movies'))
        self.assertEqual(resp.status_code, 200)

    def test_all_recent_anime_renders(self):
        resp = self.client.get(reverse('all_recent_anime'))
        self.assertEqual(resp.status_code, 200)

    def test_all_popular_anime_renders(self):
        resp = self.client.get(reverse('all_popular_anime'))
        self.assertEqual(resp.status_code, 200)


# ──────────────────────────────────────────────────────────────
# Age-rating / Kids Mode enforcement
# (regression: 18+ content was previously only excluded inside the
# recommendation engine — direct streaming URLs, search, and category
# pages all ignored age_rating entirely)
# ──────────────────────────────────────────────────────────────


class AgeGateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.minor = make_user(username='minor', age=12)
        self.adult = make_user(username='adult', age=30)

        self.genre = Genre.objects.create(name='Action')
        self.adult_anime = Anime.objects.create(
            title='Adult Anime',
            description='d',
            age_rating='r',
        )
        self.adult_anime.genres.add(self.genre)
        self.episode = make_episode(self.adult_anime)
        VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='sub',
            video_url='https://example.com/v.mp4',
        )

        self.adult_movie = Movie.objects.create(
            title='Adult Movie',
            description='d',
            age_rating='r',
        )
        MovieSource.objects.create(
            movie=self.adult_movie,
            label='1080p',
            type='sub',
            video_url='https://example.com/m.mp4',
        )

    def test_minor_blocked_from_streaming_episode(self):
        self.client.force_login(self.minor)
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertRedirects(resp, reverse('index'))

    def test_minor_blocked_from_streaming_movie(self):
        self.client.force_login(self.minor)
        resp = self.client.get(reverse('streaming_movie', args=[self.adult_movie.id]))
        self.assertRedirects(resp, reverse('index'))

    def test_adult_can_stream_episode(self):
        self.client.force_login(self.adult)
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertEqual(resp.status_code, 200)

    def test_adult_can_stream_movie(self):
        self.client.force_login(self.adult)
        resp = self.client.get(reverse('streaming_movie', args=[self.adult_movie.id]))
        self.assertEqual(resp.status_code, 200)

    def test_minor_does_not_see_adult_title_in_search(self):
        self.client.force_login(self.minor)
        resp = self.client.get(reverse('search_results'), {'q': 'Adult'})
        self.assertNotContains(resp, 'Adult Anime')
        self.assertNotContains(resp, 'Adult Movie')

    def test_adult_sees_adult_title_in_search(self):
        self.client.force_login(self.adult)
        resp = self.client.get(reverse('search_results'), {'q': 'Adult'})
        self.assertContains(resp, 'Adult Anime')
        self.assertContains(resp, 'Adult Movie')

    def test_minor_does_not_see_adult_title_in_category(self):
        self.client.force_login(self.minor)
        resp = self.client.get(reverse('category_page', args=['Action']))
        self.assertNotContains(resp, 'Adult Anime')

    def test_kids_mode_blocks_even_an_adult_account(self):
        sp = SubProfile.objects.create(user=self.adult, name='Kiddo', kids_mode=True)
        self.client.force_login(self.adult)
        session = self.client.session
        session['active_subprofile_id'] = sp.id
        session.save()
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertRedirects(resp, reverse('index'))

    def test_non_kids_subprofile_does_not_block_adult_account(self):
        sp = SubProfile.objects.create(user=self.adult, name='Grownup', kids_mode=False)
        self.client.force_login(self.adult)
        session = self.client.session
        session['active_subprofile_id'] = sp.id
        session.save()
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertEqual(resp.status_code, 200)


# ──────────────────────────────────────────────────────────────
# Movie follow + release notifications
# (regression: notify_new_movie fired on Movie creation, but nobody
# could have a Follow/WatchLater/WatchHistory row for a movie that
# didn't exist yet, so it could never reach anyone. Movies can now be
# followed, and followers are notified by a periodic command once the
# movie's release_date actually arrives.)
# ──────────────────────────────────────────────────────────────


class MovieFollowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user(username='follower', age=25)
        self.movie = make_movie(title='Upcoming Movie')

    def test_toggle_follow_movie_adds_then_removes(self):
        self.client.force_login(self.user)
        url = reverse('toggle_follow_movie', args=[self.movie.id])

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['following'])
        self.assertTrue(Follow.objects.filter(user=self.user, movie=self.movie).exists())

        resp = self.client.post(url)
        self.assertFalse(resp.json()['following'])
        self.assertFalse(Follow.objects.filter(user=self.user, movie=self.movie).exists())

    def test_followed_movie_appears_in_favourites(self):
        Follow.objects.create(user=self.user, movie=self.movie)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('favourites'))
        self.assertContains(resp, 'Upcoming Movie')


class NotifyMovieReleasesCommandTest(TestCase):
    def test_notifies_followers_once_release_date_arrives(self):
        from django.core.management import call_command
        from django.utils import timezone

        user = make_user(username='waiting_fan', age=25)
        movie = Movie.objects.create(
            title='Just Released',
            description='d',
            release_date=timezone.now().date(),
        )
        Follow.objects.create(user=user, movie=movie)

        call_command('notify_movie_releases')

        movie.refresh_from_db()
        self.assertTrue(movie.release_notified)
        self.assertTrue(Notification.objects.filter(user=user, movie=movie, notif_type='new_movie').exists())

        # Running it again shouldn't duplicate the notification.
        call_command('notify_movie_releases')
        self.assertEqual(Notification.objects.filter(user=user, movie=movie).count(), 1)

    def test_does_not_notify_for_future_releases(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        user = make_user(username='early_follower', age=25)
        movie = Movie.objects.create(
            title='Not Out Yet',
            description='d',
            release_date=timezone.now().date() + timedelta(days=30),
        )
        Follow.objects.create(user=user, movie=movie)

        call_command('notify_movie_releases')

        movie.refresh_from_db()
        self.assertFalse(movie.release_notified)
        self.assertFalse(Notification.objects.filter(user=user, movie=movie).exists())


# ──────────────────────────────────────────────────────────────
# Signed video playback links (video_access.py)
# ──────────────────────────────────────────────────────────────


class VideoAccessTokenTest(TestCase):
    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=None)
    def test_roundtrip(self):
        token = sign_video_url('https://example.com/v.mp4')
        self.assertEqual(unsign_video_url(token), 'https://example.com/v.mp4')

    def test_token_does_not_contain_raw_url(self):
        token = sign_video_url('https://example.com/super-secret-episode.mp4')
        self.assertNotIn('super-secret-episode', token)

    def test_expired_token_returns_none(self):
        token = sign_video_url('https://example.com/v.mp4')
        # max_age=-1 guarantees the token is "too old" regardless of clock resolution
        self.assertIsNone(unsign_video_url(token, max_age=-1))

    def test_tampered_token_returns_none(self):
        token = sign_video_url('https://example.com/v.mp4')
        tampered = token[:-2] + ('aa' if token[-2:] != 'aa' else 'bb')
        self.assertIsNone(unsign_video_url(tampered))

    def test_garbage_token_returns_none(self):
        self.assertIsNone(unsign_video_url('not-a-real-token'))

    def test_empty_token_returns_none(self):
        self.assertIsNone(unsign_video_url(''))
        self.assertIsNone(unsign_video_url(None))


# ──────────────────────────────────────────────────────────────
# Cloudinary CDN-edge token auth (the CLOUDINARY_AUTH_TOKEN_KEY path)
#
# This setting is *required* in production (settings.py refuses to start
# without it when DEBUG=False), but the rest of the suite intentionally
# runs without it set, so this path previously had no coverage at all —
# a regression here would only surface after deploying to production.
# ──────────────────────────────────────────────────────────────

_TEST_CLD_TOKEN_KEY = 'deadbeefcafebabe00112233445566778899aabbccddeeff0011223344556677'


def _verify_cld_token(url, expected_raw_url):
    """
    Re-derive the Cloudinary token-auth HMAC for *url* and assert it matches
    Cloudinary's documented spec: HMAC-SHA256 over "exp=<exp>~url=<path>".
    Returns the parsed expiry (int) for further assertions.
    """
    base, _, query = url.partition('?__cld_token__=')
    assert base == expected_raw_url, f'{base!r} != {expected_raw_url!r}'
    params = dict(p.split('=', 1) for p in query.split('~'))
    exp = int(params['exp'])
    url_path = re.sub(r'^https?://[^/]+', '', expected_raw_url)
    to_sign = f'exp={exp}~url={url_path}'
    expected_digest = hmac.new(bytes.fromhex(_TEST_CLD_TOKEN_KEY), to_sign.encode(), hashlib.sha256).hexdigest()
    assert params['hmac'] == expected_digest, 'HMAC does not match Cloudinary token-auth spec'
    return exp


class CloudinaryAuthTokenTest(TestCase):
    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_build_auth_token_appends_valid_cld_token(self):
        raw_url = 'https://res.cloudinary.com/demo/video/upload/v1/anime/clip.mp4'
        signed = _build_cloudinary_auth_token(raw_url, expiry=3600)
        self.assertIsNotNone(signed)
        _verify_cld_token(signed, raw_url)

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_build_auth_token_uses_ampersand_when_url_already_has_query_string(self):
        raw_url = 'https://example.com/v.mp4?quality=1080p'
        signed = _build_cloudinary_auth_token(raw_url, expiry=3600)
        self.assertTrue(signed.startswith('https://example.com/v.mp4?quality=1080p&__cld_token__='))

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=None)
    def test_build_auth_token_is_noop_without_key_configured(self):
        # Default test settings have no CLOUDINARY_AUTH_TOKEN_KEY set.
        self.assertIsNone(_build_cloudinary_auth_token('https://example.com/v.mp4', expiry=3600))

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_unsign_video_url_upgrades_to_cdn_signed_url_when_key_configured(self):
        raw_url = 'https://example.com/v.mp4'
        token = sign_video_url(raw_url)
        resolved = unsign_video_url(token)
        self.assertNotEqual(resolved, raw_url)  # upgraded, not the bare URL
        _verify_cld_token(resolved, raw_url)

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_unsign_video_url_cdn_token_expiry_is_in_the_future(self):
        token = sign_video_url('https://example.com/v.mp4')
        resolved = unsign_video_url(token)
        exp = _verify_cld_token(resolved, 'https://example.com/v.mp4')
        self.assertGreater(exp, int(time.time()))

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_tampered_token_still_returns_none_when_key_configured(self):
        # CDN-token upgrade must never run on a forged/expired Django token —
        # signature verification has to happen before the Cloudinary upgrade.
        token = sign_video_url('https://example.com/v.mp4')
        tampered = token[:-2] + ('aa' if token[-2:] != 'aa' else 'bb')
        self.assertIsNone(unsign_video_url(tampered))


class StreamRedirectViewTest(TestCase):
    def setUp(self):
        self.user = make_user(username='viewer', age=25)

    def test_requires_login(self):
        token = sign_video_url('https://example.com/v.mp4')
        resp = self.client.get(reverse('stream_redirect', args=[token]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    def test_valid_token_redirects_to_real_url(self):
        self.client.force_login(self.user)
        token = sign_video_url('https://example.com/v.mp4')
        resp = self.client.get(reverse('stream_redirect', args=[token]))
        self.assertRedirects(resp, 'https://example.com/v.mp4', fetch_redirect_response=False)

    def test_invalid_token_404s(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('stream_redirect', args=['garbage-token']))
        self.assertEqual(resp.status_code, 404)

    @override_settings(CLOUDINARY_AUTH_TOKEN_KEY=_TEST_CLD_TOKEN_KEY)
    def test_valid_token_redirects_to_cdn_signed_url_when_key_configured(self):
        self.client.force_login(self.user)
        raw_url = 'https://example.com/v.mp4'
        token = sign_video_url(raw_url)
        resp = self.client.get(reverse('stream_redirect', args=[token]))
        self.assertEqual(resp.status_code, 302)
        _verify_cld_token(resp.url, raw_url)


# ──────────────────────────────────────────────────────────────
# Streaming pages: source switching + signed URLs + subtitles
# ──────────────────────────────────────────────────────────────


class StreamingSourceSwitchingTest(TestCase):
    def setUp(self):
        self.user = make_user(username='switcher', age=25)
        self.anime = make_anime()
        self.episode = make_episode(self.anime)
        self.sub_source = VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='sub',
            video_url='https://example.com/sub.mp4',
        )
        self.dub_source = VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='dub',
            video_url='https://example.com/dub.mp4',
        )
        self.client.force_login(self.user)

    def test_default_source_is_first(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertEqual(resp.context['current_source'].pk, self.sub_source.pk)

    def test_source_query_param_switches_source(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]), {'source': self.dub_source.pk})
        self.assertEqual(resp.context['current_source'].pk, self.dub_source.pk)

    def test_invalid_source_param_falls_back_to_first(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]), {'source': 999999})
        self.assertEqual(resp.context['current_source'].pk, self.sub_source.pk)

    def test_raw_video_url_never_appears_in_response(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertNotContains(resp, 'https://example.com/sub.mp4')
        self.assertNotContains(resp, 'https://example.com/dub.mp4')

    def test_response_uses_signed_watch_link(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertContains(resp, '/watch/')
        signed_url = resp.context['playable_url']
        self.assertTrue(signed_url.startswith('/watch/'))
        token = signed_url.rsplit('/watch/', 1)[1].rstrip('/')
        self.assertEqual(unsign_video_url(token), 'https://example.com/sub.mp4')

    def test_switcher_buttons_link_to_distinct_sources(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertContains(resp, f'?source={self.sub_source.pk}')
        self.assertContains(resp, f'?source={self.dub_source.pk}')


class MovieStreamingSourceSwitchingTest(TestCase):
    def setUp(self):
        self.user = make_user(username='movie_switcher', age=25)
        self.movie = make_movie()
        self.source = MovieSource.objects.create(
            movie=self.movie,
            label='1080p',
            type='sub',
            video_url='https://example.com/movie.mp4',
        )
        self.client.force_login(self.user)

    def test_raw_video_url_never_appears_in_response(self):
        resp = self.client.get(reverse('streaming_movie', args=[self.movie.id]))
        self.assertNotContains(resp, 'https://example.com/movie.mp4')
        self.assertContains(resp, '/watch/')


# ──────────────────────────────────────────────────────────────
# Adaptive bitrate (HLS) streaming via Cloudinary's sp_auto profile
# ──────────────────────────────────────────────────────────────


class ToHlsUrlTest(TestCase):
    def test_cloudinary_video_url_converted(self):
        url = 'https://res.cloudinary.com/demo/video/upload/v123/anime/clip.mp4'
        self.assertEqual(
            to_hls_url(url),
            'https://res.cloudinary.com/demo/video/upload/sp_auto/v123/anime/clip.m3u8',
        )

    def test_cloudinary_video_url_without_version_converted(self):
        url = 'https://res.cloudinary.com/demo/video/upload/anime/clip.mov'
        self.assertEqual(
            to_hls_url(url),
            'https://res.cloudinary.com/demo/video/upload/sp_auto/anime/clip.m3u8',
        )

    def test_non_cloudinary_url_returns_none(self):
        self.assertIsNone(to_hls_url('https://example.com/video.mp4'))

    def test_cloudinary_image_resource_returns_none(self):
        url = 'https://res.cloudinary.com/demo/image/upload/v1/pic.jpg'
        self.assertIsNone(to_hls_url(url))

    def test_empty_or_none_returns_none(self):
        self.assertIsNone(to_hls_url(''))
        self.assertIsNone(to_hls_url(None))


class HlsStreamingViewTest(TestCase):
    def setUp(self):
        self.user = make_user(username='hls_viewer', age=25)
        self.anime = make_anime()
        self.episode = make_episode(self.anime)
        self.client.force_login(self.user)

    def test_cloudinary_source_exposes_hls_url(self):
        VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='sub',
            video_url='https://res.cloudinary.com/demo/video/upload/v1/anime/clip.mp4',
        )
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertIsNotNone(resp.context['hls_url'])
        self.assertIn('?format=hls', resp.context['hls_url'])
        self.assertContains(resp, 'hls.js')

    def test_non_cloudinary_source_has_no_hls_url(self):
        VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='sub',
            video_url='https://example.com/clip.mp4',
        )
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertIsNone(resp.context['hls_url'])
        self.assertNotContains(resp, 'hls.js')


class StreamRedirectHlsFormatTest(TestCase):
    def setUp(self):
        self.user = make_user(username='hls_redirect_viewer', age=25)
        self.client.force_login(self.user)

    def test_format_hls_redirects_to_manifest_for_cloudinary_source(self):
        token = sign_video_url('https://res.cloudinary.com/demo/video/upload/v1/anime/clip.mp4')
        resp = self.client.get(reverse('stream_redirect', args=[token]) + '?format=hls')
        self.assertRedirects(
            resp,
            'https://res.cloudinary.com/demo/video/upload/sp_auto/v1/anime/clip.m3u8',
            fetch_redirect_response=False,
        )

    def test_format_hls_falls_back_to_raw_url_for_non_cloudinary_source(self):
        token = sign_video_url('https://example.com/clip.mp4')
        resp = self.client.get(reverse('stream_redirect', args=[token]) + '?format=hls')
        self.assertRedirects(resp, 'https://example.com/clip.mp4', fetch_redirect_response=False)

    def test_no_format_param_redirects_to_raw_mp4(self):
        token = sign_video_url('https://res.cloudinary.com/demo/video/upload/v1/anime/clip.mp4')
        resp = self.client.get(reverse('stream_redirect', args=[token]))
        self.assertRedirects(
            resp,
            'https://res.cloudinary.com/demo/video/upload/v1/anime/clip.mp4',
            fetch_redirect_response=False,
        )


class SubtitleRenderingTest(TestCase):
    def setUp(self):
        self.user = make_user(username='caption_viewer', age=25)
        self.anime = make_anime()
        self.episode = make_episode(self.anime)
        self.source = VideoSource.objects.create(
            episode=self.episode,
            label='1080p',
            type='sub',
            video_url='https://example.com/v.mp4',
        )
        Subtitle.objects.create(
            video_source=self.source,
            language_code='en',
            label='English',
            file_url='https://example.com/captions/en.vtt',
            is_default=True,
        )
        self.client.force_login(self.user)

    def test_subtitle_track_rendered(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertContains(resp, '<track')
        self.assertContains(resp, 'https://example.com/captions/en.vtt')
        self.assertContains(resp, 'English')


# ──────────────────────────────────────────────────────────────
# Subtitle model
# ──────────────────────────────────────────────────────────────


class SubtitleModelTest(TestCase):
    def setUp(self):
        anime = make_anime()
        episode = make_episode(anime)
        self.source = VideoSource.objects.create(
            episode=episode,
            label='1080p',
            type='sub',
            video_url='https://example.com/v.mp4',
        )

    def test_valid_subtitle_passes_clean(self):
        sub = Subtitle(
            video_source=self.source,
            language_code='en',
            label='English',
            file_url='https://example.com/en.vtt',
        )
        sub.full_clean()  # should not raise

    def test_clean_rejects_neither_source_set(self):
        sub = Subtitle(language_code='en', label='English', file_url='https://example.com/en.vtt')
        with self.assertRaises(ValidationError):
            sub.clean()

    def test_clean_rejects_both_sources_set(self):
        movie_source = MovieSource.objects.create(
            movie=make_movie(),
            label='1080p',
            type='sub',
            video_url='https://example.com/m.mp4',
        )
        sub = Subtitle(
            video_source=self.source,
            movie_source=movie_source,
            language_code='en',
            label='English',
            file_url='https://example.com/en.vtt',
        )
        with self.assertRaises(ValidationError):
            sub.clean()


# ──────────────────────────────────────────────────────────────
# Transcoding pipeline tests
# ──────────────────────────────────────────────────────────────

from unittest.mock import patch  # noqa: E402

from .transcoding import (  # noqa: E402
    EAGER_TRANSFORMS,
    _extract_public_id,
    get_rendition_url,
    request_eager_transcoding,
)


class TranscodingPublicIdTest(TestCase):
    """Unit tests for the Cloudinary public_id extractor."""

    def test_extracts_public_id_with_version(self):
        url = 'https://res.cloudinary.com/demo/video/upload/v1234567890/sample.mp4'
        self.assertEqual(_extract_public_id(url), 'sample')

    def test_extracts_public_id_without_version(self):
        url = 'https://res.cloudinary.com/demo/video/upload/my_folder/clip.mp4'
        self.assertEqual(_extract_public_id(url), 'my_folder/clip')

    def test_returns_none_for_non_cloudinary_url(self):
        self.assertIsNone(_extract_public_id('https://example.com/video.mp4'))

    def test_returns_none_for_image_resource(self):
        # image/ not video/
        url = 'https://res.cloudinary.com/demo/image/upload/v1/sample.jpg'
        self.assertIsNone(_extract_public_id(url))

    def test_returns_none_for_empty(self):
        self.assertIsNone(_extract_public_id(''))
        self.assertIsNone(_extract_public_id(None))


class TranscodingRenditionUrlTest(TestCase):
    """Unit tests for get_rendition_url()."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/sample.mp4'

    def test_720p_mp4_url_contains_transform(self):
        url = get_rendition_url(self.CL_URL, 720, 'mp4')
        self.assertIn('h_720', url)
        self.assertTrue(url.endswith('.mp4'))

    def test_360p_mp4_url(self):
        url = get_rendition_url(self.CL_URL, 360, 'mp4')
        self.assertIn('h_360', url)

    def test_non_cloudinary_returns_none(self):
        self.assertIsNone(get_rendition_url('https://example.com/v.mp4', 720))

    def test_none_url_returns_none(self):
        self.assertIsNone(get_rendition_url(None, 720))


class EagerTransformListTest(TestCase):
    """EAGER_TRANSFORMS list sanity checks."""

    def test_has_multiple_resolutions(self):
        # Should have at least one transform for each canonical height
        heights = {t.get('height') for t in EAGER_TRANSFORMS if 'height' in t}
        for h in (360, 480, 720, 1080):
            self.assertIn(h, heights, f'Missing eager transform for {h}p')

    def test_includes_m3u8_format(self):
        formats = {t.get('format') for t in EAGER_TRANSFORMS}
        self.assertIn('m3u8', formats)

    def test_includes_mp4_format(self):
        formats = {t.get('format') for t in EAGER_TRANSFORMS}
        self.assertIn('mp4', formats)


class RequestEagerTranscodingTest(TestCase):
    """request_eager_transcoding() integration (Cloudinary SDK mocked)."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/anime_ep1.mp4'
    NON_CL_URL = 'https://example.com/video.mp4'

    @patch('ananimeclip.transcoding.cloudinary')
    def test_calls_explicit_for_cloudinary_url(self, mock_cl):
        mock_cl.uploader.explicit.return_value = {'version': 1}
        result = request_eager_transcoding(self.CL_URL)
        self.assertTrue(result)
        mock_cl.uploader.explicit.assert_called_once()
        call_kwargs = mock_cl.uploader.explicit.call_args
        self.assertEqual(call_kwargs.kwargs.get('resource_type'), 'video')
        self.assertTrue(call_kwargs.kwargs.get('eager_async'))

    def test_returns_false_for_non_cloudinary_url(self):
        result = request_eager_transcoding(self.NON_CL_URL)
        self.assertFalse(result)

    def test_returns_false_for_empty_url(self):
        self.assertFalse(request_eager_transcoding(''))

    @patch('ananimeclip.transcoding.cloudinary')
    def test_returns_false_on_api_error(self, mock_cl):
        mock_cl.uploader.explicit.side_effect = Exception('API error')
        result = request_eager_transcoding(self.CL_URL)
        self.assertFalse(result)


class TranscodingSignalTest(TestCase):
    """Signals trigger transcoding when a VideoSource / MovieSource is saved."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/ep1.mp4'

    def _make_episode_source(self):
        anime = make_anime()
        episode = make_episode(anime)
        return episode

    @patch('ananimeclip.signals.request_eager_transcoding')
    def test_video_source_save_triggers_transcoding(self, mock_transcode):
        episode = self._make_episode_source()
        VideoSource.objects.create(
            episode=episode,
            label='Server 1',
            type='sub',
            video_url=self.CL_URL,
        )
        mock_transcode.assert_called_once_with(self.CL_URL)

    @patch('ananimeclip.signals.request_eager_transcoding')
    def test_video_source_without_url_does_not_transcode(self, mock_transcode):
        episode = self._make_episode_source()
        VideoSource.objects.create(episode=episode, label='Server 1', type='sub', video_url=None)
        mock_transcode.assert_not_called()

    @patch('ananimeclip.signals.request_eager_transcoding')
    def test_movie_source_save_triggers_transcoding(self, mock_transcode):
        movie = make_movie()
        MovieSource.objects.create(movie=movie, label='Server 1', type='sub', video_url=self.CL_URL)
        mock_transcode.assert_called_once_with(self.CL_URL)


# ──────────────────────────────────────────────────────────────
# Offline download tests
# ──────────────────────────────────────────────────────────────

from .offline_downloads import (  # noqa: E402
    ALLOWED_HEIGHTS,
    QUALITY_OPTIONS,
    build_download_url,
    generate_download_token,
    validate_download_token,
)


class DownloadTokenTest(TestCase):
    """Unit tests for generate_download_token / validate_download_token."""

    def _gen(self, height=720, user_pk=1, source_pk=42, source_type='episode'):
        return generate_download_token(
            source_pk=source_pk,
            source_type=source_type,
            height=height,
            user_pk=user_pk,
        )

    def test_roundtrip(self):
        token = self._gen()
        self.assertIsNotNone(token)
        payload = validate_download_token(token, requesting_user_pk=1)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['h'], 720)
        self.assertEqual(payload['spk'], 42)
        self.assertEqual(payload['st'], 'episode')
        self.assertEqual(payload['uid'], 1)

    def test_unsupported_height_returns_none(self):
        token = self._gen(height=999)
        self.assertIsNone(token)

    def test_empty_token_returns_none(self):
        self.assertIsNone(validate_download_token('', requesting_user_pk=1))

    def test_tampered_token_returns_none(self):
        token = self._gen()
        tampered = token[:-4] + 'xxxx'
        self.assertIsNone(validate_download_token(tampered, requesting_user_pk=1))

    def test_wrong_user_returns_none(self):
        token = self._gen(user_pk=1)
        # Another user tries to reuse the token
        self.assertIsNone(validate_download_token(token, requesting_user_pk=99))

    def test_all_allowed_heights_produce_tokens(self):
        for h in ALLOWED_HEIGHTS:
            self.assertIsNotNone(self._gen(height=h), f'Failed for height={h}')


class BuildDownloadUrlTest(TestCase):
    """Unit tests for build_download_url()."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/sample.mp4'

    def test_720p_url_contains_transform(self):
        url = build_download_url(self.CL_URL, 720)
        self.assertIn('h_720', url)
        self.assertIn('vc_h264', url)
        self.assertTrue(url.endswith('.mp4'))

    def test_1080p_uses_h265(self):
        url = build_download_url(self.CL_URL, 1080)
        self.assertIn('vc_h265', url)

    def test_360p_uses_eco_quality(self):
        url = build_download_url(self.CL_URL, 360)
        self.assertIn('q_auto:eco', url)

    def test_non_cloudinary_returns_none(self):
        self.assertIsNone(build_download_url('https://example.com/v.mp4', 720))

    def test_none_returns_none(self):
        self.assertIsNone(build_download_url(None, 720))

    def test_unsupported_height_returns_none(self):
        self.assertIsNone(build_download_url(self.CL_URL, 144))


class QualityOptionsTest(TestCase):
    def test_all_standard_heights_present(self):
        heights = {opt['height'] for opt in QUALITY_OPTIONS}
        self.assertEqual(heights, {360, 480, 720, 1080})

    def test_each_option_has_required_keys(self):
        for opt in QUALITY_OPTIONS:
            self.assertIn('height', opt)
            self.assertIn('label', opt)
            self.assertIn('size_hint', opt)


class EpisodeDownloadViewTest(TestCase):
    """Integration tests for the episode download request view."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/ep1.mp4'

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.anime = make_anime(title='DL Anime')
        self.episode = make_episode(self.anime)
        self.source = VideoSource.objects.create(episode=self.episode, label='S1', type='sub', video_url=self.CL_URL)

    def _post(self, height=720, source_id=None):
        import json

        url = reverse('request_episode_download', args=[self.episode.pk])
        payload = {'height': height}
        if source_id:
            payload['source_id'] = source_id
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_returns_download_url(self):
        resp = self._post(height=720)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('url', data)
        self.assertIn('/dl/', data['url'])

    def test_requires_login(self):
        self.client.logout()
        resp = self._post()
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_unsupported_height_returns_400(self):
        resp = self._post(height=999)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_explicit_source_id_accepted(self):
        resp = self._post(height=480, source_id=self.source.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('url', resp.json())

    def test_all_quality_options_produce_url(self):
        for h in (360, 480, 720, 1080):
            resp = self._post(height=h)
            self.assertEqual(resp.status_code, 200, f'Failed for height={h}')


class MovieDownloadViewTest(TestCase):
    """Integration tests for the movie download request view."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/movie1.mp4'

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='dlmovieuser')
        self.client.force_login(self.user)
        self.movie = make_movie(title='DL Movie')
        self.source = MovieSource.objects.create(movie=self.movie, label='S1', type='sub', video_url=self.CL_URL)

    def _post(self, height=720):
        import json

        url = reverse('request_movie_download', args=[self.movie.pk])
        return self.client.post(
            url,
            data=json.dumps({'height': height}),
            content_type='application/json',
        )

    def test_returns_download_url(self):
        resp = self._post(height=720)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('url', resp.json())

    def test_requires_login(self):
        self.client.logout()
        resp = self._post()
        self.assertEqual(resp.status_code, 302)

    def test_unsupported_height_returns_400(self):
        resp = self._post(height=240)
        self.assertEqual(resp.status_code, 400)


class ServeDownloadViewTest(TestCase):
    """Integration tests for the serve_download redirect view."""

    CL_URL = 'https://res.cloudinary.com/demo/video/upload/v1/ep1.mp4'

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='servdluser')
        self.client.force_login(self.user)
        self.anime = make_anime(title='Serve DL Anime')
        self.episode = make_episode(self.anime)
        self.source = VideoSource.objects.create(episode=self.episode, label='S1', type='sub', video_url=self.CL_URL)

    def _get_token(self, height=720):
        return generate_download_token(
            source_pk=self.source.pk,
            source_type='episode',
            height=height,
            user_pk=self.user.pk,
        )

    def test_valid_token_redirects_to_cloudinary(self):
        token = self._get_token(720)
        resp = self.client.get(reverse('serve_download', args=[token]))
        self.assertEqual(resp.status_code, 302)
        location = resp['Location']
        self.assertIn('res.cloudinary.com', location)
        self.assertIn('fl_attachment', location)

    def test_invalid_token_raises_404(self):
        resp = self.client.get(reverse('serve_download', args=['not-a-real-token']))
        self.assertEqual(resp.status_code, 404)

    def test_requires_login(self):
        self.client.logout()
        token = self._get_token()
        resp = self.client.get(reverse('serve_download', args=[token]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_wrong_user_cannot_use_token(self):
        other = make_user(username='otherservuser')
        token = generate_download_token(
            source_pk=self.source.pk,
            source_type='episode',
            height=720,
            user_pk=other.pk,  # token belongs to 'other'
        )
        # self.user (not 'other') tries to use it
        resp = self.client.get(reverse('serve_download', args=[token]))
        self.assertEqual(resp.status_code, 404)

    def test_redirect_url_contains_mp4(self):
        token = self._get_token(480)
        resp = self.client.get(reverse('serve_download', args=[token]))
        self.assertIn('.mp4', resp['Location'])

    def test_redirect_url_contains_height_transform(self):
        token = self._get_token(480)
        resp = self.client.get(reverse('serve_download', args=[token]))
        self.assertIn('h_480', resp['Location'])

    def test_quality_options_in_streaming_context(self):
        """streaming view must pass quality_options to the template."""
        self.source.video_url = self.CL_URL
        self.source.save(update_fields=['video_url'])
        resp = self.client.get(reverse('streaming', args=[self.episode.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('quality_options', resp.context)
        self.assertTrue(len(resp.context['quality_options']) > 0)


# ──────────────────────────────────────────────────────────────
# Production-readiness fixes
# ──────────────────────────────────────────────────────────────


class PasswordResetTimeoutTest(TestCase):
    """PASSWORD_RESET_TIMEOUT was 300s (5 min) — far too short for an email
    flow. Guard against it silently regressing back to a short value."""

    def test_timeout_is_at_least_one_day(self):
        from django.conf import settings

        self.assertGreaterEqual(settings.PASSWORD_RESET_TIMEOUT, 60 * 60 * 24)


class SitemapTest(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name='Action')
        anime = make_anime()
        anime.genres.add(self.genre)

    def test_sitemap_returns_200_and_xml(self):
        resp = self.client.get('/sitemap.xml')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'<urlset', resp.content)

    def test_sitemap_includes_static_pages(self):
        resp = self.client.get('/sitemap.xml')
        body = resp.content.decode()
        self.assertIn(reverse('index'), body)
        self.assertIn(reverse('movies'), body)
        self.assertIn(reverse('all_categories'), body)

    def test_sitemap_includes_genre_pages(self):
        resp = self.client.get('/sitemap.xml')
        body = resp.content.decode()
        self.assertIn(reverse('category_page', args=[self.genre.name]), body)

    def test_robots_txt_sitemap_line_resolves(self):
        """robots.txt previously pointed at a sitemap.xml that 404'd."""
        robots_resp = self.client.get('/robots.txt')
        sitemap_line = next(line for line in robots_resp.content.decode().splitlines() if line.startswith('Sitemap:'))
        sitemap_url = sitemap_line.split('Sitemap:', 1)[1].strip()
        sitemap_resp = self.client.get(sitemap_url.replace('http://testserver', ''))
        self.assertEqual(sitemap_resp.status_code, 200)


class LegalPagesTest(TestCase):
    def test_privacy_policy_renders(self):
        resp = self.client.get(reverse('privacy_policy'))
        self.assertEqual(resp.status_code, 200)

    def test_terms_of_service_renders(self):
        resp = self.client.get(reverse('terms_of_service'))
        self.assertEqual(resp.status_code, 200)

    def test_footer_links_to_legal_pages(self):
        resp = self.client.get(reverse('index'))
        body = resp.content.decode()
        self.assertIn(reverse('privacy_policy'), body)
        self.assertIn(reverse('terms_of_service'), body)


class ContentSecurityPolicyTest(TestCase):
    def test_csp_header_present_on_homepage(self):
        resp = self.client.get(reverse('index'))
        self.assertIn('Content-Security-Policy', resp)
        csp = resp['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        self.assertIn('frame-ancestors', csp)

    def test_csp_allows_known_third_party_script_origins(self):
        """Regression guard: hls.js, the Cloudinary upload widget, and the
        Chromecast sender SDK are loaded from these origins — if someone
        tightens script-src without updating this list, those features
        break silently in the browser instead of failing a test."""
        resp = self.client.get(reverse('index'))
        csp = resp['Content-Security-Policy']
        for origin in ('cdn.jsdelivr.net', 'upload-widget.cloudinary.com', 'www.gstatic.com'):
            self.assertIn(origin, csp)

    def test_csp_allows_blob_for_hls_playback(self):
        """hls.js doesn't just load from a CDN — at runtime it creates a
        blob: worker (script-src) and feeds segments to <video> through a
        blob: MediaSource URL (media-src). Without both, playback fails
        even though the script itself loaded fine."""
        resp = self.client.get(reverse('index'))
        csp = resp['Content-Security-Policy']
        directives = dict(d.strip().split(' ', 1) for d in csp.split(';') if d.strip() and ' ' in d.strip())
        self.assertIn('blob:', directives.get('script-src', ''))
        self.assertIn('blob:', directives.get('media-src', ''))


# ============================================================
# Trending, ContentReport, WatchParty, Offline, SW
# ============================================================


class TrendingViewTest(TestCase):
    def test_trending_page_renders_for_anonymous(self):
        resp = self.client.get(reverse('trending'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Trending')

    def test_trending_page_in_nav(self):
        resp = self.client.get(reverse('index'))
        self.assertContains(resp, reverse('trending'))


class OfflineViewTest(TestCase):
    def test_offline_page_renders(self):
        resp = self.client.get(reverse('offline'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Offline')

    def test_service_worker_js_served(self):
        resp = self.client.get(reverse('service_worker'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/javascript')
        self.assertIn('no-cache', resp.get('Cache-Control', ''))
        self.assertEqual(resp.get('Service-Worker-Allowed'), '/')


class ContentReportTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user('reporter', password='pass')
        from ananimeclip.models import Anime, Episode, Genre, Season, VideoSource

        genre = Genre.objects.create(name='Action')
        anime = Anime.objects.create(title='Test Anime', description='desc', slug='test-anime')
        anime.genres.add(genre)
        season = Season.objects.create(anime=anime, number=1)
        self.episode = Episode.objects.create(season=season, number=1)
        VideoSource.objects.create(
            episode=self.episode, label='HD', type='sub', video_url='https://example.com/vid.mp4'
        )

    def test_report_episode_requires_login(self):
        resp = self.client.post(reverse('report_episode', args=[self.episode.id]), {'reason': 'broken_video'})
        self.assertIn(resp.status_code, [302, 403])

    def test_report_episode_authenticated(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('report_episode', args=[self.episode.id]), {'reason': 'broken_video'})
        self.assertEqual(resp.status_code, 200)
        import json

        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'reported')
        from ananimeclip.models import ContentReport

        self.assertTrue(ContentReport.objects.filter(user=self.user, episode=self.episode).exists())

    def test_report_episode_invalid_reason(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('report_episode', args=[self.episode.id]), {'reason': 'invalid_reason'})
        self.assertEqual(resp.status_code, 400)


class WatchPartyTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.host = User.objects.create_user('host', password='pass')
        self.guest = User.objects.create_user('guest', password='pass')
        from ananimeclip.models import Anime, Episode, Genre, Season, VideoSource

        genre = Genre.objects.create(name='Action')
        anime = Anime.objects.create(title='Party Anime', description='desc', slug='party-anime')
        anime.genres.add(genre)
        season = Season.objects.create(anime=anime, number=1)
        self.episode = Episode.objects.create(season=season, number=1)
        VideoSource.objects.create(episode=self.episode, label='HD', type='sub', video_url='https://example.com/v.mp4')

    def test_create_party_requires_login(self):
        resp = self.client.post(reverse('create_watch_party'), {'episode_id': self.episode.id})
        self.assertIn(resp.status_code, [302, 403])

    def test_create_party_authenticated(self):
        self.client.force_login(self.host)
        resp = self.client.post(reverse('create_watch_party'), {'episode_id': self.episode.id})
        self.assertEqual(resp.status_code, 200)
        import json

        data = json.loads(resp.content)
        self.assertIn('room_code', data)
        self.assertEqual(len(data['room_code']), 8)

    def test_join_and_sync_party(self):
        self.client.force_login(self.host)
        resp = self.client.post(reverse('create_watch_party'), {'episode_id': self.episode.id})
        import json

        code = json.loads(resp.content)['room_code']

        # Guest joins
        self.client.logout()
        self.client.force_login(self.guest)
        resp = self.client.post(reverse('join_watch_party', args=[code]))
        self.assertEqual(resp.status_code, 200)
        state = json.loads(resp.content)['state']
        self.assertIn('guest', state['members'])

        # Host syncs state
        self.client.logout()
        self.client.force_login(self.host)
        resp = self.client.post(reverse('sync_watch_party', args=[code]), {'position': 42.5, 'is_playing': 'true'})
        self.assertEqual(resp.status_code, 200)
        state = json.loads(resp.content)['state']
        self.assertAlmostEqual(state['playback_position'], 42.5)
        self.assertTrue(state['is_playing'])

    def test_end_party(self):
        self.client.force_login(self.host)
        resp = self.client.post(reverse('create_watch_party'), {'episode_id': self.episode.id})
        import json

        code = json.loads(resp.content)['room_code']
        resp = self.client.post(reverse('end_watch_party', args=[code]))
        self.assertEqual(resp.status_code, 200)
        from ananimeclip.models import WatchParty

        self.assertFalse(WatchParty.objects.get(room_code=code).is_active)

    def test_guest_cannot_sync(self):
        self.client.force_login(self.host)
        resp = self.client.post(reverse('create_watch_party'), {'episode_id': self.episode.id})
        import json

        code = json.loads(resp.content)['room_code']
        self.client.logout()
        self.client.force_login(self.guest)
        resp = self.client.post(reverse('sync_watch_party', args=[code]), {'position': 99, 'is_playing': 'true'})
        self.assertEqual(resp.status_code, 404)
