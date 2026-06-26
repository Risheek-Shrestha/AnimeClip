# AnimeClip

A full-stack anime streaming web application built with Django, PostgreSQL, Redis, and Cloudinary. Users can browse anime and movies, stream episodes, manage playlists, track watch history, and receive personalised recommendations based on their viewing habits.

---

## Features

- Browse anime series and movies with genre filtering and live search
- Stream episodes and movies with automatic watch-progress saving
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
| Backend | Django 4.2, Python 3.11+ |
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

### 5. (Optional) Load sample data

```bash
python manage.py loaddata data.json
```

> **Note:** `data.json` is a development fixture. It includes admin log entries — safe to ignore.

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