from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    Profile, Genre, Anime, Movie, Season, Episode,
    WatchHistory, WatchLater, Playlist, PlaylistItem,
)


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

    def test_signup_valid_age(self):
        resp = self.client.post(reverse('signup'), {
            'name': 'Alice',
            'email': 'alice@test.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'age': 22,
        })
        self.assertRedirects(resp, reverse('index'))
        self.assertTrue(User.objects.filter(username='alice@test.com').exists())

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
        self.assertEqual(list(resp.context['recommended_movies']), [])

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