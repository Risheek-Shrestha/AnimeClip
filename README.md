# AnimeClip

A full-stack anime streaming web application built with Django, PostgreSQL, Redis, and Cloudinary. Users can browse anime and movies, stream episodes, manage playlists, track watch history, and receive personalised recommendations based on their viewing habits.

---

## Features

- Browse anime series and movies with genre filtering and live search
- Stream episodes and movies with automatic watch-progress saving
- Switchable SUB/DUB (or other) playback sources per episode/movie, with WebVTT subtitle/caption tracks
- Adaptive bitrate (HLS) streaming for Cloudinary-hosted videos — multi-quality playback that adjusts to bandwidth, via Cloudinary's `sp_auto` streaming profile + hls.js, with automatic fallback to plain MP4 for non-Cloudinary sources or unsupported browsers
- Time-limited signed playback links — raw video URLs are never rendered in HTML; links expire after 4 hours (see `video_access.py`)
- Continue Watching bar with real-time progress percentage
- Personalised recommendations derived from the user's genre history
- Playlist management — create, add to, and delete custom playlists
- Watch Later queue
- User profiles with editable age and avatar
- Password reset via email (SMTP-backed in production)
- Cloudinary media storage, WhiteNoise static file serving, Redis caching

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 LTS, Python 3.11+ |
| Database | PostgreSQL (psycopg2) |
| Cache | Redis (django-redis) |
| Media storage | Cloudinary |
| Static files | WhiteNoise |
| Frontend | Vanilla JS, custom CSS (3D dark space theme) |

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/Risheek-Shrestha/AnimeClip.git
cd AnimeClip
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in all required values (see .env.example for details)
```

Required variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DEBUG` | `True` for local dev, `False` in production |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host (e.g. `localhost`) |
| `DB_PORT` | Database port (default `5432`) |
| `REDIS_URL` | Redis connection URL (e.g. `redis://127.0.0.1:6379/1`) |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `EMAIL_HOST` | SMTP host — omit to fall back to console backend |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |

> **Cloudinary upload preset:** the admin video-upload widget uploads directly
> to Cloudinary from the browser, which requires an **unsigned** upload preset
> named `anime_videos_unsigned` to exist on your Cloudinary account (Settings →
> Upload → Upload presets → Add upload preset, signing mode "Unsigned"). The
> admin form will load without it, but video uploads will silently fail.

### 4. Set up the database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. (Optional) Import catalog data

Instead of a fixture file, use the included management command to pull real metadata from the Jikan API (no API key required):

```bash
python manage.py import_catalog --type anime --count 50
python manage.py import_catalog --type movie --count 30
```

Add `--with-images` to also download and store poster art via Cloudinary.

### 6. Run the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`

---

## Docker Setup

A `Dockerfile` and `docker-compose.yml` are included as an alternative to the
manual setup above.

```bash
cp .env.example .env
# fill in .env as described in step 3 above — docker-compose reads it via env_file
docker-compose up --build
```

This builds the app image, then on container start runs `collectstatic`,
applies migrations, and serves via Gunicorn on `http://localhost:8000/`.
You'll still need to create a superuser once the container is up:

```bash
docker-compose exec web python manage.py createsuperuser
```

---


## Production Deployment

### Environment variables checklist

Before going live, make sure these are set in your `.env`:

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Long random string — never the dev default |
| `DEBUG` | Must be `False` |
| `ALLOWED_HOSTS` | Your actual domain(s), space-separated |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Strong, unique password — not `animeclip` |
| `CLOUDINARY_*` | Required for media uploads |
| `EMAIL_HOST` + credentials | Required for password reset emails |
| `REDIS_URL` | Required for caching and rate limiting |

### Gunicorn workers

The default is 3 workers. Override via `GUNICORN_WORKERS` in your `.env`:

```
# Rule of thumb: 2 x CPU cores + 1
GUNICORN_WORKERS=5
```

### HTTPS

The app enforces HTTPS in production (`DEBUG=False`) via `SECURE_SSL_REDIRECT`. You must terminate TLS at the reverse proxy or load balancer level (Nginx, Caddy, your cloud provider's LB). If your proxy already handles TLS termination and forwards plain HTTP to Gunicorn, set `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` in settings so Django trusts the `X-Forwarded-Proto` header.

### Docker

```bash
cp .env.example .env
# Fill in all required values — DB_PASSWORD must be a strong password
docker-compose up --build -d
docker-compose exec web python manage.py createsuperuser
```

---
## Project Structure

```
AnimeClip/
├── ananimeclip/          # Main Django app
│   ├── models.py         # Anime, Movie, Episode, Genre, WatchHistory, Playlist, …
│   ├── views.py          # All view functions
│   ├── urls.py           # URL routing
│   └── migrations/       # Database migrations
├── Hello/                # Django project settings
│   └── settings.py
├── templates/            # HTML templates
├── static/               # CSS, JS, image assets
├── requirements.txt
├── .env.example
└── manage.py
```

---

## Key URL Routes

| URL | Description |
|---|---|
| `/` | Homepage with trending, new releases, and personalised recommendations |
| `/movies/` | Movies listing |
| `/streaming/<episode_id>/` | Anime episode player |
| `/streaming_movie/<movie_id>/` | Movie player |
| `/continue-watching/` | Resume where you left off |
| `/watch-later/` | Saved watch-later items |
| `/playlists/` | User playlists |
| `/search/` | Full search results |
| `/category/<genre>/` | Browse by genre |
| `/profile/` | User profile |
| `/admin/` | Django admin |

---

## Notes

- **Email:** Password reset emails only reach users when `EMAIL_HOST` is configured. Without it, reset tokens print to the console (dev only).
- **CSRF & Beacons:** Watch progress is saved via `fetch` with `keepalive: true` on pause/end events, and flushed on tab close/hide — fully CSRF-protected.
- **Secret Key:** The app will refuse to start in production (`DEBUG=False`) if `SECRET_KEY` is not set in the environment.
- **Signed playback links:** these stop a copied link from working forever and route every playback through the app's own age-gate/auth checks, but they are not real DRM — once a link is issued it streams from a public Cloudinary URL until it expires. Real content protection would require switching the Cloudinary delivery type to `authenticated` and enabling token-based authentication at the account level.
- **Adaptive streaming:** the first request for a given video's HLS manifest pays a one-time Cloudinary transcoding delay; later requests are served from cache. This also consumes Cloudinary transformation credits — worth watching at scale. Sources hosted outside Cloudinary (or non-video Cloudinary resources) automatically fall back to plain MP4.