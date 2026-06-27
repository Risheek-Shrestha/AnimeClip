from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from .models import (
    Profile, Genre, Anime, Movie, Season, Episode,
    WatchHistory, WatchLater, Playlist, PlaylistItem,
    VideoSource, MovieSource, SubProfile, Follow, Notification, Subtitle,
)
from .video_access import sign_video_url, unsign_video_url


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
        anime = make_anime()
        ep = make_episode(anime)
        wh = WatchHistory.objects.create(user=user, episode=ep, progress_seconds=120)
        self.assertEqual(wh.progress_seconds, 120)

    def test_create_movie_history(self):
        user = make_user()
        movie = make_movie()
        wh = WatchHistory.objects.create(user=user, movie=movie, progress_seconds=600)
        self.assertEqual(wh.progress_seconds, 600)

    def test_unique_per_episode(self):
        from django.db import IntegrityError
        user = make_user()
        anime = make_anime()
        ep = make_episode(anime)
        WatchHistory.objects.create(user=user, episode=ep, progress_seconds=10)
        with self.assertRaises(IntegrityError):
            WatchHistory.objects.create(user=user, episode=ep, progress_seconds=20)


# ──────────────────────────────────────────────────────────────
# View tests — Authentication
# ──────────────────────────────────────────────────────────────

class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.core.cache import cache
        cache.clear()

    def test_signup_valid_age(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Alice',
            'email': 'alice@test.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'age': 22,
        })
        # Email verification flow: signup shows a "check your email" page
        # rather than logging the user in immediately.
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'verify_pending.html')
        user = User.objects.filter(username='alice@test.com').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)

    def test_signup_age_too_low_rejected(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Baby',
            'email': 'baby@test.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'age': 5,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')
        self.assertFalse(User.objects.filter(username='baby@test.com').exists())

    def test_signup_age_too_high_rejected(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Elder',
            'email': 'elder@test.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'age': 90,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')

    def test_signup_non_integer_age_rejected(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Hacker',
            'email': 'hack@test.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'age': 'abc',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Age must be')

    def test_signup_password_mismatch(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Bob',
            'email': 'bob@test.com',
            'password': 'secret123',
            'confirm_password': 'wrong',
            'age': 25,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='bob@test.com').exists())

    def test_login_redirects_on_success(self):
        make_user(username='loginuser@test.com', password='pass1234')
        resp = self.client.post(reverse('login'), {
            'email': 'loginuser@test.com',
            'password': 'pass1234',
        })
        self.assertRedirects(resp, reverse('index'))

    def test_login_fails_bad_password(self):
        make_user(username='loginuser2@test.com', password='pass1234')
        resp = self.client.post(reverse('login'), {
            'email': 'loginuser2@test.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(resp.status_code, 200)

    def test_verify_email_activates_account(self):
        self.client.post(reverse('signup'), {
            'name': 'Carol', 'email': 'carol@test.com',
            'password': 'secret123', 'confirm_password': 'secret123', 'age': 22,
        })
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
        self.client.post(reverse('signup'), {
            'name': 'Dave', 'email': 'dave@test.com',
            'password': 'secret123', 'confirm_password': 'secret123', 'age': 22,
        })
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
        resp = self.client.post(reverse('signup'), {
            'name': 'Eve', 'email': 'eve@test.com',
            'password': 'secret123', 'confirm_password': 'secret123', 'age': 22,
        })
        self.assertTemplateUsed(resp, 'verify_pending.html')
        self.assertTrue(User.objects.filter(username='eve@test.com').exists())

    def test_login_proceeds_when_cache_unreachable(self):
        make_user(username='cachefail@test.com', password='pass1234')
        resp = self.client.post(reverse('login'), {
            'email': 'cachefail@test.com', 'password': 'pass1234',
        })
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
        resp = self.client.post(self.url, {
            'episode_id': self.ep.id,
            'progress_seconds': 300,
        })
        self.assertEqual(resp.status_code, 200)
        wh = WatchHistory.objects.get(user=self.user, episode=self.ep)
        self.assertEqual(wh.progress_seconds, 300)

    def test_saves_movie_progress(self):
        resp = self.client.post(self.url, {
            'movie_id': self.movie.id,
            'progress_seconds': 600,
        })
        self.assertEqual(resp.status_code, 200)
        wh = WatchHistory.objects.get(user=self.user, movie=self.movie)
        self.assertEqual(wh.progress_seconds, 600)

    def test_malformed_progress_returns_400(self):
        resp = self.client.post(self.url, {
            'episode_id': self.ep.id,
            'progress_seconds': 'not_a_number',
        })
        self.assertEqual(resp.status_code, 400)

    def test_missing_id_returns_400(self):
        resp = self.client.post(self.url, {'progress_seconds': 100})
        self.assertEqual(resp.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.post(self.url, {
            'episode_id': self.ep.id,
            'progress_seconds': 100,
        })
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
        resp = self.client.post(reverse('toggle_watch_later'), {
            'episode_id': self.ep.id,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'added')
        self.assertTrue(WatchLater.objects.filter(user=self.user, episode=self.ep).exists())

    def test_toggle_removes_episode(self):
        WatchLater.objects.create(user=self.user, episode=self.ep)
        resp = self.client.post(reverse('toggle_watch_later'), {
            'episode_id': self.ep.id,
        })
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
        resp = self.client.post(reverse('add_to_playlist'), {
            'playlist_id': pl.id,
            'episode_id': self.ep.id,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PlaylistItem.objects.filter(playlist=pl, episode=self.ep).exists())

    def test_add_movie_to_playlist(self):
        pl = Playlist.objects.create(user=self.user, name='Favs')
        resp = self.client.post(reverse('add_to_playlist'), {
            'playlist_id': pl.id,
            'movie_id': self.movie.id,
        })
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
        resp = self.client.post(reverse('add_to_playlist'), {
            'playlist_id': pl.id,
            'episode_id': self.ep.id,
        })
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
            title='Adult Anime', description='d', age_rating='r',
        )
        self.adult_anime.genres.add(self.genre)
        self.episode = make_episode(self.adult_anime)
        VideoSource.objects.create(
            episode=self.episode, label='1080p', type='sub',
            video_url='https://example.com/v.mp4',
        )

        self.adult_movie = Movie.objects.create(
            title='Adult Movie', description='d', age_rating='r',
        )
        MovieSource.objects.create(
            movie=self.adult_movie, label='1080p', type='sub',
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
            title='Just Released', description='d',
            release_date=timezone.now().date(),
        )
        Follow.objects.create(user=user, movie=movie)

        call_command('notify_movie_releases')

        movie.refresh_from_db()
        self.assertTrue(movie.release_notified)
        self.assertTrue(
            Notification.objects.filter(user=user, movie=movie, notif_type='new_movie').exists()
        )

        # Running it again shouldn't duplicate the notification.
        call_command('notify_movie_releases')
        self.assertEqual(
            Notification.objects.filter(user=user, movie=movie).count(), 1
        )

    def test_does_not_notify_for_future_releases(self):
        from django.core.management import call_command
        from datetime import timedelta
        from django.utils import timezone

        user = make_user(username='early_follower', age=25)
        movie = Movie.objects.create(
            title='Not Out Yet', description='d',
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


# ──────────────────────────────────────────────────────────────
# Streaming pages: source switching + signed URLs + subtitles
# ──────────────────────────────────────────────────────────────

class StreamingSourceSwitchingTest(TestCase):
    def setUp(self):
        self.user = make_user(username='switcher', age=25)
        self.anime = make_anime()
        self.episode = make_episode(self.anime)
        self.sub_source = VideoSource.objects.create(
            episode=self.episode, label='1080p', type='sub',
            video_url='https://example.com/sub.mp4',
        )
        self.dub_source = VideoSource.objects.create(
            episode=self.episode, label='1080p', type='dub',
            video_url='https://example.com/dub.mp4',
        )
        self.client.force_login(self.user)

    def test_default_source_is_first(self):
        resp = self.client.get(reverse('streaming', args=[self.episode.id]))
        self.assertEqual(resp.context['current_source'].pk, self.sub_source.pk)

    def test_source_query_param_switches_source(self):
        resp = self.client.get(
            reverse('streaming', args=[self.episode.id]), {'source': self.dub_source.pk}
        )
        self.assertEqual(resp.context['current_source'].pk, self.dub_source.pk)

    def test_invalid_source_param_falls_back_to_first(self):
        resp = self.client.get(
            reverse('streaming', args=[self.episode.id]), {'source': 999999}
        )
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
            movie=self.movie, label='1080p', type='sub',
            video_url='https://example.com/movie.mp4',
        )
        self.client.force_login(self.user)

    def test_raw_video_url_never_appears_in_response(self):
        resp = self.client.get(reverse('streaming_movie', args=[self.movie.id]))
        self.assertNotContains(resp, 'https://example.com/movie.mp4')
        self.assertContains(resp, '/watch/')


class SubtitleRenderingTest(TestCase):
    def setUp(self):
        self.user = make_user(username='caption_viewer', age=25)
        self.anime = make_anime()
        self.episode = make_episode(self.anime)
        self.source = VideoSource.objects.create(
            episode=self.episode, label='1080p', type='sub',
            video_url='https://example.com/v.mp4',
        )
        Subtitle.objects.create(
            video_source=self.source, language_code='en', label='English',
            file_url='https://example.com/captions/en.vtt', is_default=True,
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
            episode=episode, label='1080p', type='sub',
            video_url='https://example.com/v.mp4',
        )

    def test_valid_subtitle_passes_clean(self):
        sub = Subtitle(
            video_source=self.source, language_code='en', label='English',
            file_url='https://example.com/en.vtt',
        )
        sub.full_clean()  # should not raise

    def test_clean_rejects_neither_source_set(self):
        sub = Subtitle(language_code='en', label='English', file_url='https://example.com/en.vtt')
        with self.assertRaises(ValidationError):
            sub.clean()

    def test_clean_rejects_both_sources_set(self):
        movie_source = MovieSource.objects.create(
            movie=make_movie(), label='1080p', type='sub',
            video_url='https://example.com/m.mp4',
        )
        sub = Subtitle(
            video_source=self.source, movie_source=movie_source,
            language_code='en', label='English', file_url='https://example.com/en.vtt',
        )
        with self.assertRaises(ValidationError):
            sub.clean()
