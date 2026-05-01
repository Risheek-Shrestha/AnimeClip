# AnimeClip — Project Report

---

## Cover Page

**Project Title:** AnimeClip — Anime & Movie Streaming Web Application

**Submitted by:** Risheek Shrestha

**Technology Stack:** Python · Django · PostgreSQL · Cloudinary · Bootstrap 5

**Year:** 2025

---

## Title Page

| | |
|---|---|
| **Project Name** | AnimeClip |
| **Project Type** | Web Application |
| **Technology** | Django (Python), PostgreSQL, Cloudinary, Bootstrap 5 |
| **Submitted By** | Risheek Shrestha |
| **Repository** | https://github.com/Risheek-Shrestha/AnimeClip |

---

## Acknowledgement

I would like to express my sincere gratitude to my project guide and all faculty members who provided support and guidance throughout the development of this project. I also thank the open-source community behind Django, Cloudinary, and Bootstrap for making powerful, free tools available to developers worldwide. Special thanks to everyone who provided feedback during testing and to all those who contributed indirectly to making AnimeClip a reality.

---

## Project Introduction

AnimeClip is a full-featured anime and movie streaming web application built with Django and backed by a PostgreSQL database. It allows users to discover, browse, and stream anime series (with multiple seasons and episodes) as well as standalone anime films. Video content is hosted via Cloudinary, ensuring scalable, CDN-delivered playback. The platform supports user registration, authentication, personal profiles, comments with threaded replies, comment likes, genre-based categorization, a live search feature, and a weekly release schedule.

The platform is aimed at anime fans who want a structured, Netflix-style experience for both serialized anime shows and films — all within a single web application.

---

## Declaration

I hereby declare that the project titled **AnimeClip — Anime & Movie Streaming Web Application** is an original work carried out by me. The content of this report and the software developed is genuine and has not been submitted elsewhere for any academic award or commercial purpose. All external references and libraries have been appropriately cited.

**Signature of Student:** ___________________________

**Date:** _________________________

---

## Guide Details

| Field | Details |
|---|---|
| **Guide Name** | *(Fill in guide name)* |
| **Designation** | *(Fill in designation)* |
| **Department** | *(Fill in department)* |
| **Institution** | *(Fill in institution name)* |
| **Email** | *(Fill in email)* |

**Signature of Guide:** ___________________________

---

## Certificate of Originality

This is to certify that the project report entitled **"AnimeClip — Anime & Movie Streaming Web Application"** submitted by **Risheek Shrestha** is a record of original work carried out under guidance. The project has not been submitted previously in part or full to any other institution or university.

**Signature of Guide:** ___________________________ &emsp;&emsp; **Signature of Student:** ___________________________

---

## Table of Contents

| Section | Page |
|---|---|
| Cover Page | i |
| Title Page | 1 |
| Acknowledgement | 2 |
| Project Introduction | 3 |
| Declaration | 4 |
| Guide Details | 5 |
| Certificate of Originality | 6 |
| **Chapter 1: Introduction** | |
| 1.1 Title and Abstract | 9 |
| 1.2 Introduction | 10 |
| 1.3 Project Objective | 11–12 |
| 1.4 Project Definition | 13 |
| 1.5 Project Category | 14–15 |
| **Chapter 2: System Environment** | |
| 2.1 Tools and Technologies | 16–18 |
| 2.2 Software & Hardware Requirements | 19–20 |
| **Chapter 3: System Study** | |
| 3.1 Data Flow Diagram (DFD) | 21–25 |
| 3.2 Flowchart | 26–28 |
| 3.3 Entity Relationship Diagram | 29–31 |
| **Chapter 4: System Design** | |
| 4.1 System Features/Modules | 32–34 |
| 4.2 System Design | 35–36 |
| 4.3 Database Design | 37–39 |
| 4.4 User Interface Design | 40–43 |
| **Chapter 5: System Implementation** | |
| 5.1 Source Code | 44–202 |
| **Chapter 6: Testing and Maintenance** | |
| 6.1 System Testing | 203–204 |
| 6.2 Feasibility Study | 205–211 |
| **Chapter 7: Conclusion** | |
| 7.1 Future Scope | 212–214 |
| 7.2 Limitations | 215–217 |
| 7.3 Conclusion | 218 |
| **Chapter 8: Bibliography** | |
| 8.1 Bibliography | 219–220 |
| **Chapter 9: Appendix** | |
| 9.1 Appendix | 221–228 |

---

# Chapter 1: Introduction

## 1.1 Title and Abstract

**Title:** AnimeClip — Anime & Movie Streaming Web Application

**Abstract:**

AnimeClip is a Django-powered web application that delivers a structured, user-friendly streaming experience for anime series and anime movies. The platform organizes content hierarchically — Anime → Season → Episode — and stores video sources on Cloudinary for reliable, globally distributed delivery. Users can register accounts, browse a homepage featuring curated carousels (Featured, Recently Updated, Popular, Top Rated, Coming Soon, Weekly Schedule), watch episodes or films, leave threaded comments, like comments, and search content in real time. The admin panel (Django Admin) allows content managers to upload and organize anime, movies, genres, episodes, images, and video sources without writing any code. The application uses PostgreSQL for relational data storage, WhiteNoise for efficient static file serving, and Bootstrap 5 for a responsive front-end.

---

## 1.2 Introduction

The global popularity of anime has grown exponentially over the past decade, with millions of fans seeking convenient, organized platforms to watch their favorite shows and films. Existing mainstream platforms are either geo-restricted, require expensive subscriptions, or lack focus on the anime genre specifically.

AnimeClip was conceived as a dedicated anime streaming portal that provides:
- A clean, dark-themed, Netflix-inspired user interface.
- Structured cataloguing of series by Seasons and Episodes.
- Support for both **SUB** (subtitled) and **DUB** (dubbed) video sources per episode.
- Anime films as first-class content alongside episodic series.
- Community engagement through a threaded comments and likes system.
- An admin-friendly backend for non-technical content managers to upload and manage all content.

The project demonstrates the application of modern web development principles including the **MVC (Model-View-Template)** architectural pattern (Django's MTV variant), relational database design, cloud media storage, and responsive front-end design.

---

## 1.3 Project Objective

The primary objectives of AnimeClip are:

1. **Content Streaming:** Deliver a reliable video streaming experience for both anime series (multi-season, multi-episode) and standalone anime movies, with video hosted on Cloudinary CDN.

2. **User Management:** Implement secure user registration, login, logout, profile management, and password reset flows using Django's built-in authentication system.

3. **Content Discovery:** Provide multiple discovery mechanisms — featured banners, popular lists, top-rated lists, recently updated, weekly release schedule, genre-based category browsing, and live real-time search.

4. **Community Interaction:** Allow authenticated users to post comments on episodes and movies, reply to existing comments in a threaded structure, and like or unlike comments via AJAX — without full page reloads.

5. **Age Rating Enforcement:** Associate age ratings (PG, PG-13, 18+) with anime content to indicate suitability.

6. **Admin Content Management:** Provide a powerful Django Admin interface augmented with a Cloudinary Upload Widget so content managers can upload videos directly from the browser without requiring developer intervention.

7. **Performance Optimization:** Use `prefetch_related` and Python-level grouping to minimize database queries and avoid N+1 query problems, especially on heavily data-driven pages like the homepage.

8. **Responsive Design:** Ensure the application is fully usable on desktops, tablets, and mobile devices using Bootstrap 5 grid and components.

---

## 1.4 Project Definition

AnimeClip is defined as a **full-stack web application** with the following scope:

- **Backend:** Django 4.x (Python) serving as the application server. Business logic is handled in `views.py`. URL routing is defined in `urls.py`. Data models are defined in `models.py`.
- **Frontend:** Django Templates (HTML5 + Jinja2-style tags), styled with Bootstrap 5, custom CSS, Slick.js carousel, Font Awesome icons, and jQuery.
- **Database:** PostgreSQL for all persistent relational data.
- **Media Storage:** Cloudinary (cloud-based image and video storage with CDN delivery).
- **Static File Serving:** WhiteNoise middleware for compressed, cached static file delivery in production.
- **Deployment-ready:** Settings use environment variables (via `python-dotenv`) for all secrets and configuration, making it deployable to any cloud platform (Heroku, Railway, Render, etc.).

---

## 1.5 Project Category

| Attribute | Value |
|---|---|
| **Category** | Web Application |
| **Sub-category** | Media Streaming / Entertainment |
| **Type** | Full-Stack |
| **Architecture** | MTV (Model-Template-View) — Django's MVC variant |
| **Platform** | Web Browser (Cross-platform) |
| **Access** | Public (browse) + Authenticated (comment, like) |
| **Content Type** | Anime Series + Anime Movies |
| **Content Source** | Cloudinary (video), Cloudinary (images) |

---

# Chapter 2: System Environment

## 2.1 Tools and Technologies

### 2.1.1 Python
Python 3.x is the primary programming language. It is used for all backend logic, database interactions, and server-side rendering.

### 2.1.2 Django
Django is the full-stack web framework used. Key Django features utilized include:
- **ORM:** Django's Object-Relational Mapper for all database operations.
- **Admin Site:** Auto-generated, customizable admin interface for content management.
- **Authentication System:** Built-in `User` model, login, logout, password reset views.
- **Template Engine:** Django Template Language for HTML rendering.
- **CSRF Protection:** Cross-Site Request Forgery middleware applied to all POST forms.
- **URL Dispatcher:** URL patterns defined in `urls.py`.
- **Class-Based Views (CBVs):** Used for password reset flows.
- **Function-Based Views (FBVs):** Used for all custom views.

### 2.1.3 PostgreSQL
PostgreSQL is the production relational database. It is chosen for its reliability, support for complex queries, and compatibility with Django's ORM. Connection is configured via environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`). `CONN_MAX_AGE=60` is set for connection pooling.

### 2.1.4 Cloudinary
Cloudinary is the cloud-based media management platform used to store and serve:
- **Images:** Anime/movie thumbnails, banners, posters, cards, and logos.
- **Videos:** Episode and movie video files served via CDN.

A custom `CloudinaryVideoWidget` was developed to embed the Cloudinary Upload Widget directly into the Django Admin, allowing content managers to upload videos via a browser interface.

### 2.1.5 WhiteNoise
WhiteNoise is used as Django middleware to serve compressed, cached static files (CSS, JS, images) efficiently without a separate web server or CDN for static assets.

### 2.1.6 Bootstrap 5
Bootstrap 5 provides the responsive grid system, navigation components, modals, accordions, dropdowns, and utility classes used throughout the front-end.

### 2.1.7 Slick.js
Slick.js is a jQuery-based carousel library used for the banner/featured sliders on the homepage and movies page.

### 2.1.8 jQuery
jQuery is used for DOM manipulation, AJAX live search, carousel initialization, and countdown timer integration.

### 2.1.9 Font Awesome
Font Awesome provides icon fonts used throughout the UI (search icon, social icons, play button, genre icons, etc.).

### 2.1.10 jQuery Countdown
A jQuery countdown plugin is used for the "Coming Soon" section to display a live countdown timer to the upcoming anime/movie release.

### 2.1.11 python-dotenv
`python-dotenv` is used to load environment variables from a `.env` file, keeping secrets (database credentials, Cloudinary API keys, Django secret key) out of source code.

### 2.1.12 Git & GitHub
Git is the version control system. The project repository is hosted on GitHub at `https://github.com/Risheek-Shrestha/AnimeClip`.

---

## 2.2 Software & Hardware Requirements

### Software Requirements

| Component | Requirement |
|---|---|
| **Operating System** | Windows 10/11, macOS 12+, or Ubuntu 20.04+ |
| **Python** | 3.10 or higher |
| **Django** | 4.x |
| **Database** | PostgreSQL 13+ |
| **Browser** | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+ |
| **Cloudinary Account** | Free tier or higher |
| **Git** | 2.x |
| **pip** | Latest |
| **Virtual Environment** | `venv` or `virtualenv` |

### Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **Processor** | Dual-core 1.5 GHz | Quad-core 2.5 GHz+ |
| **RAM** | 2 GB | 4 GB+ |
| **Storage** | 1 GB (app + DB) | 5 GB+ |
| **Internet Connection** | Required (Cloudinary CDN, video streaming) | Broadband 10 Mbps+ |
| **Display** | 1024 × 768 | 1920 × 1080 |

### Server/Deployment Requirements

| Component | Value |
|---|---|
| **Web Server** | Gunicorn (or any WSGI-compatible server) |
| **Static Files** | WhiteNoise (bundled) |
| **Database** | Hosted PostgreSQL (e.g., Railway, Supabase, Neon) |
| **Media** | Cloudinary (external) |
| **Environment Variables** | `SECRET_KEY`, `DB_*`, `CLOUDINARY_*` |

---

# Chapter 3: System Study

## 3.1 Data Flow Diagram (DFD)

### Level 0 — Context Diagram

```
                        +-------------------+
  [User] ─────────────► |                   | ─────────────► [Cloudinary CDN]
                        |    AnimeClip      |
  [Admin] ────────────► |  Web Application  | ─────────────► [PostgreSQL DB]
                        |                   |
                        +-------------------+
```

**External Entities:**
- **User:** Browses content, streams video, registers, logs in, comments, likes.
- **Admin:** Manages content via Django Admin (uploads anime, episodes, movies, images, video sources).
- **Cloudinary CDN:** Stores and delivers images and video files.
- **PostgreSQL DB:** Stores all structured application data.

---

### Level 1 — Main Processes

```
User ──► [1.0 Authentication] ──► PostgreSQL
          (Register / Login / Logout / Password Reset)

User ──► [2.0 Content Discovery] ──► PostgreSQL ──► Cloudinary
          (Homepage, Movies Page, Category, Search)

User ──► [3.0 Video Streaming] ──► PostgreSQL ──► Cloudinary
          (Anime Episode / Movie playback)

User ──► [4.0 Community] ──► PostgreSQL
          (Post Comment, Reply, Like Comment)

Admin ──► [5.0 Content Management] ──► PostgreSQL ──► Cloudinary
           (Django Admin: Anime, Movie, Season, Episode, VideoSource)
```

---

### Level 2 — Process 2.0: Content Discovery

```
User Input (URL / Search Query)
        │
        ▼
[2.1 Homepage View]
    ├── Query: Featured Anime (is_featured=True)
    ├── Query: Recent Anime (annotate latest_update, order -latest_update)
    ├── Query: Coming Soon Season (status=upcoming, nearest release_date)
    ├── Query: Popular Anime (is_popular=True)
    ├── Query: Weekly Schedule (seasons release_day in current week)
    ├── Query: Top Rated Anime (order -rating, top 5)
    ├── Query: New Anime (latest episode update, top 5)
    └── Query: Completed Anime (seasons status=completed, top 5)
        │
        ▼
[2.2 Category View] ─► Filter Anime + Movies by Genre name
        │
        ▼
[2.3 Live Search View] ─► Filter Anime + Movies by title__icontains
                         Returns JSON: [{id, title, type}, ...]
```

---

### Level 2 — Process 3.0: Video Streaming

```
User ──► /streaming/<episode_id>/
             │
             ▼
         [3.1 Fetch Episode]
             │ select_related(season__anime)
             ▼
         [3.2 Fetch Seasons + Episodes]
             │ prefetch_related
             ▼
         [3.3 Fetch Comments]
             │ filter(parent=None), prefetch replies+likes
             ▼
         [3.4 Render streaming.html]
             │ <video> tag with Cloudinary video_url
             ▼
         [3.5 User Interaction]
             ├── Switch episode (sidebar click)
             ├── Switch source (SUB/DUB buttons)
             └── Post / Like comment (AJAX)
```

---

## 3.2 Flowchart

### User Registration & Login Flow

```
START
  │
  ▼
User visits /signup/
  │
  ▼
Fill form (name, age, email, password, confirm_password)
  │
  ▼
Passwords match? ──NO──► Show error "Passwords do not match"
  │YES
  ▼
Email already registered? ──YES──► Show error "Email already registered"
  │NO
  ▼
Create User (username=email, email, password, first_name=name)
  │
  ▼
Create Profile (user, age)
  │
  ▼
Login user → Redirect to /
  │
  ▼
END

─────────────────────────────────────────────

START
  │
  ▼
User visits /login/
  │
  ▼
Submit email + password
  │
  ▼
authenticate(username=email, password)
  │
  ▼
Valid credentials? ──NO──► Show error "Invalid email or password"
  │YES
  ▼
Login user → Redirect to /
  │
  ▼
END
```

---

### Comment Posting Flow

```
START
  │
  ▼
User is authenticated? ──NO──► Redirect to /login/
  │YES
  ▼
POST /episode/<id>/comment/  (or /movie/<id>/comment/)
  │
  ▼
Extract body, parent_id from POST data
  │
  ▼
body non-empty?
  │YES
  ▼
Create Comment(episode/movie, user, body)
  │
  ▼
parent_id provided? ──YES──► Set comment.parent = parent Comment object
  │NO
  ▼
comment.save()
  │
  ▼
Redirect back to referrer URL
  │
  ▼
END
```

---

### Comment Like / Unlike Flow (AJAX)

```
START
  │
  ▼
User clicks Like button on comment
  │
  ▼
JavaScript: POST /comment/<id>/like/  (with CSRF token)
  │
  ▼
CommentLike.objects.get_or_create(user, comment)
  │
  ▼
Already liked? ──YES──► Delete like → liked=False
  │NO
  ▼
Like created → liked=True
  │
  ▼
Return JSON { liked: bool, total_likes: int }
  │
  ▼
JavaScript updates like count on page (no reload)
  │
  ▼
END
```

---

## 3.3 Entity Relationship Diagram

### Entities and Relationships

```
┌──────────┐          ┌─────────────┐
│   User   │ 1──────1 │   Profile   │
│ (Django) │          │ (age)       │
└──────────┘          └─────────────┘
     │
     │ 1──────M
     ▼
┌──────────┐
│ Comment  │◄────────────────────────────────────────┐
│ (body,   │ parent (self FK, replies)               │
│ created) │                                         │
└──────────┘                                         │
  │ M──1 Episode          │ M──1 Movie               │
  ▼                       ▼                          │
┌──────────┐        ┌───────────┐                    │
│ Episode  │        │   Movie   │                    │
│ (number, │        │ (title,   │                    │
│  title)  │        │ duration) │                    │
└──────────┘        └───────────┘                    │
  │ M──1 Season       │ M──M Genre  │                │
  ▼                   ▼             │                │
┌──────────┐    ┌───────────┐  ┌──────────────┐     │
│  Season  │    │  Genre    │  │ MovieSource  │     │
│ (number, │    │ (name)    │  │ (label, type,│     │
│  status) │    └───────────┘  │  video_url)  │     │
└──────────┘         ▲         └──────────────┘     │
  │ M──1 Anime        │                              │
  ▼        └──────────┘ M──M Genre                  │
┌──────────┐                                        │
│  Anime   │──────────────────────────────────────── ┘ (via Episode → Season → Anime)
│ (title,  │
│  rating, │
│ age_rtng)│
└──────────┘
  │ 1──M MediaImage    │ 1──M VideoSource (via Episode)
  ▼
┌────────────┐
│ MediaImage │
│ (image,    │
│  type)     │
└────────────┘

CommentLike: User M──M Comment (unique_together)
```

### Key Relationships Summary

| Relationship | Type | Details |
|---|---|---|
| User ↔ Profile | One-to-One | Each user has exactly one profile |
| Anime ↔ Season | One-to-Many | An anime has multiple seasons |
| Season ↔ Episode | One-to-Many | A season has multiple episodes |
| Episode ↔ VideoSource | One-to-Many | Each episode can have multiple sources (SUB/DUB) |
| Movie ↔ MovieSource | One-to-Many | Each movie can have multiple sources |
| Anime ↔ Genre | Many-to-Many | An anime can belong to many genres |
| Movie ↔ Genre | Many-to-Many | A movie can belong to many genres |
| Anime ↔ MediaImage | One-to-Many | Each anime can have banner, thumbnail, poster, card, logo images |
| Movie ↔ MediaImage | One-to-Many | Each movie can have multiple image types |
| User ↔ Comment | One-to-Many | A user can post many comments |
| Comment ↔ Comment | Self FK | Parent–child for threaded replies |
| User ↔ CommentLike | Many-to-Many (via CommentLike) | Users like comments; unique per user+comment |

---

# Chapter 4: System Design

## 4.1 System Features / Modules

### Module 1: Authentication Module
- **User Registration** (`/signup/`): Form collects name, age, email, password, confirm_password. Creates a Django `User` and linked `Profile` (stores age). Redirects to homepage on success.
- **User Login** (`/login/`): Email + password authentication. Session-based login.
- **User Logout** (`/logout/`): Clears session, redirects to homepage.
- **Password Reset** (`/password-reset/`): Full email-based password reset flow using Django's built-in `PasswordResetView`, `PasswordResetDoneView`, `PasswordResetConfirmView`, and `PasswordResetCompleteView`.
- **Profile View** (`/profile/`): Displays logged-in user's profile (login required).
- **Edit Profile** (`/editprofile/`): Allows editing profile details (login required).

### Module 2: Content Discovery Module
- **Homepage** (`/`): Dynamically assembled page showing: Featured Anime (banner slider), Recently Updated, Coming Soon (with countdown), Popular Anime, Weekly Schedule (7-day grid), Top Rated, New Anime, Recently Completed.
- **Movies Page** (`/movies/`): Featured Movies (banner slider), Recent Movies, Coming Soon Movie, Top Rated Movies, Popular Movies.
- **Category Page** (`/category/<genre>/`): Filters and displays both Anime and Movies belonging to a specific genre.
- **Live Search** (`/live-search/?q=`): AJAX JSON endpoint. Returns up to 5 matching movies and 5 matching anime in real time as the user types.

### Module 3: Streaming Module
- **Anime Streaming** (`/streaming/<episode_id>/`): Full-page video player for a specific episode. Left panel: `<video>` player with Cloudinary-hosted MP4. Right sidebar: Season/Episode accordion navigator. Bottom panel: anime details, tech info, trailer modal, SUB/DUB source switcher.
- **Movie Streaming** (`/streaming_movie/<movie_id>/`): Dedicated streaming page for anime movies.

### Module 4: Community Module
- **Post Episode Comment** (`/episode/<id>/comment/`): POST-only, login required.
- **Post Movie Comment** (`/movie/<id>/comment/`): POST-only, login required.
- **Threaded Replies:** Comments support a `parent` foreign key for nested reply threads.
- **Like/Unlike Comment** (`/comment/<id>/like/`): POST-only AJAX endpoint, login required. Toggles like, returns JSON with new like count.

### Module 5: Admin / Content Management Module
- Django Admin interface at `/admin/`.
- Manage: `Genre`, `Anime`, `Movie`, `Season`, `Episode`, `VideoSource`, `MovieSource`, `Comment`, `CommentLike`, `Profile`, `MediaImage`.
- Custom `CloudinaryVideoWidget` embedded in `VideoSourceAdmin` and `MovieSourceAdmin` for in-browser video upload to Cloudinary.

### Module 6: Playlist Module
- **Playlist** (`/playlist/`): Reserved page for user-specific watchlists (login required). Functionality is planned/stubbed.

---

## 4.2 System Design

### Application Architecture

```
Browser (Client)
    │
    │  HTTP Request
    ▼
Django URL Dispatcher (urls.py)
    │
    │  Routes to View Function
    ▼
View (views.py)
    ├── Queries Database via ORM (models.py)
    ├── Fetches images/videos via Cloudinary storage
    └── Renders Template (templates/*.html)
         │
         │  Includes static assets
         ▼
    Static Files (WhiteNoise)
    Bootstrap 5 / jQuery / Slick / Font Awesome
```

### Django MTV Pattern

| Layer | File(s) | Responsibility |
|---|---|---|
| **Model** | `ananimeclip/models.py` | Database schema, validation, helper properties |
| **Template** | `templates/*.html` | HTML rendering, template tags, conditional display |
| **View** | `ananimeclip/views.py` | Business logic, DB queries, context assembly, response |
| **URL** | `ananimeclip/urls.py` | Route mapping from URL patterns to view functions |
| **Admin** | `ananimeclip/admin.py` | Admin site configuration, custom forms/widgets |

### Key Design Decisions

1. **Optimized Database Queries:** All list-rendering views use `prefetch_related` extensively. A helper function `attach_episode_info()` walks the prefetch cache in Python rather than issuing new DB queries per anime, eliminating N+1 query patterns.

2. **Cloudinary for Media:** All user-facing images and videos are stored in Cloudinary rather than on the server filesystem. This ensures media is CDN-distributed and the app server remains stateless.

3. **Session-Based Auth:** Standard Django session authentication is used. No JWT or token-based auth is needed for this server-rendered application.

4. **AJAX for Likes:** Comment likes use `fetch()` API (JavaScript) to POST to the like endpoint and update the count without a full page reload, improving UX.

5. **Environment Variable Configuration:** All secrets and environment-specific config are loaded from `.env` via `python-dotenv`, making the app deployable to any environment.

---

## 4.3 Database Design

### Table: `auth_user` (Django built-in)
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| username | VARCHAR(150) | Used as email address |
| email | VARCHAR(254) | |
| password | VARCHAR(128) | Hashed |
| first_name | VARCHAR(150) | Stores display name |

### Table: `ananimeclip_profile`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| user_id | FK → auth_user | OneToOne, CASCADE |
| age | Integer | 10–80 (validated) |

### Table: `ananimeclip_genre`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| name | VARCHAR(100) | e.g., "Action", "Romance" |

### Table: `ananimeclip_anime`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| title | VARCHAR(100) | |
| description | TextField | |
| studio | VARCHAR(100) | optional |
| country | VARCHAR(100) | optional |
| rating | Decimal(3,1) | 0–10 |
| age_rating | VARCHAR(10) | pg / pg13 / r |
| is_featured | Boolean | default False |
| is_popular | Boolean | default False |

### Table: `ananimeclip_anime_genres` (M2M)
| Column | Type |
|---|---|
| anime_id | FK → anime |
| genre_id | FK → genre |

### Table: `ananimeclip_movie`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| title | VARCHAR(100) | |
| description | TextField | |
| studio | VARCHAR(100) | optional |
| country | VARCHAR(100) | optional |
| release_date | Date | optional |
| release_day | VARCHAR(10) | Sunday–Saturday |
| release_time | Time | optional |
| rating | Decimal(3,1) | 0–10 |
| is_featured | Boolean | |
| is_popular | Boolean | |
| duration_mins | PositiveInt | |

### Table: `ananimeclip_season`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| anime_id | FK → anime | CASCADE |
| number | PositiveInt | |
| title | VARCHAR(100) | optional |
| release_date | Date | optional |
| release_day | VARCHAR(10) | |
| release_time | Time | optional |
| status | VARCHAR(20) | ongoing / completed / upcoming |

### Table: `ananimeclip_episode`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| season_id | FK → season | CASCADE |
| number | PositiveInt | |
| title | VARCHAR(100) | optional |
| release_date | Date | optional |
| release_day | VARCHAR(10) | |
| release_time | Time | optional |
| updated_at | DateTime | auto_now |

### Table: `ananimeclip_videosource`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| episode_id | FK → episode | CASCADE |
| label | VARCHAR(50) | e.g., "Server 1" |
| type | VARCHAR(50) | sub / dub |
| video_url | URLField(500) | Cloudinary secure URL |
| poster | ImageField | optional |

### Table: `ananimeclip_moviesource`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| movie_id | FK → movie | CASCADE |
| label | VARCHAR(50) | |
| type | VARCHAR(50) | sub / dub |
| video_url | URLField(500) | Cloudinary secure URL |
| poster | ImageField | optional |

### Table: `ananimeclip_mediaimage`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| anime_id | FK → anime | nullable |
| movie_id | FK → movie | nullable |
| image | ImageField | Cloudinary |
| type | VARCHAR(20) | thumbnail/banner/logo/poster/card/background |

### Table: `ananimeclip_comment`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| user_id | FK → auth_user | CASCADE |
| episode_id | FK → episode | nullable |
| movie_id | FK → movie | nullable |
| parent_id | FK → self | nullable (for replies) |
| body | TextField | |
| created_at | DateTime | auto_now_add |

### Table: `ananimeclip_commentlike`
| Column | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| user_id | FK → auth_user | |
| comment_id | FK → comment | |
| (unique_together) | user + comment | |

---

## 4.4 User Interface Design

### Pages Overview

| Page | URL | Description |
|---|---|---|
| Homepage | `/` | Main landing page with all carousels and weekly schedule |
| Movies Page | `/movies/` | Anime films listing with featured/popular/upcoming |
| Streaming (Anime) | `/streaming/<episode_id>/` | Video player + episode navigator + comments |
| Streaming (Movie) | `/streaming_movie/<movie_id>/` | Movie video player |
| Category | `/category/<genre>/` | Genre-filtered anime and movies |
| Login | `/login/` | Email + password login form |
| Signup | `/signup/` | Registration form |
| Profile | `/profile/` | User profile page |
| Edit Profile | `/editprofile/` | Profile editing form |
| Playlist | `/playlist/` | User's saved playlist |
| Password Reset | `/password-reset/` | Email-based reset flow |

### UI Component Highlights

- **Navbar:** Logo, Anime/Movie/Manga links, Categories dropdown (10 genres), live search box, Sign Up / Log In (or username + Log Out when authenticated). Responsive hamburger menu on mobile.
- **Banner Slider:** Auto-playing Slick.js carousel for featured anime/movies with title, description, and play button overlay.
- **Content Cards:** Responsive grid cards with thumbnail, title, genre badges, rating.
- **Coming Soon Block:** Countdown timer (days/hours/minutes/seconds) until release. Switches to "Play Now" button when time reaches zero.
- **Weekly Schedule:** 7-column tab layout (one per weekday), each listing anime airing that day with their thumbnails.
- **Video Player:** HTML5 `<video>` tag with controls, poster image from Cloudinary. Season/episode accordion sidebar for navigation.
- **Comments Section:** Threaded comments with relative timestamps, Like button (AJAX, no reload), Reply form (collapsible).

---

# Chapter 5: System Implementation

## 5.1 Source Code

The full source code is organized as follows in the repository:

```
AnimeClip/
├── Hello/                    # Django project package
│   ├── settings.py           # All configuration (DB, Cloudinary, static, auth)
│   ├── urls.py               # Root URL configuration
│   ├── wsgi.py               # WSGI entry point
│   └── asgi.py               # ASGI entry point
├── ananimeclip/              # Main Django app
│   ├── models.py             # All data models (11 models)
│   ├── views.py              # All view functions (15 views)
│   ├── urls.py               # URL patterns (18 routes)
│   ├── admin.py              # Admin site configuration
│   ├── widgets.py            # Custom CloudinaryVideoWidget
│   ├── apps.py               # App configuration
│   ├── tests.py              # Test stubs
│   └── migrations/           # Database migration files
├── templates/                # Django HTML templates (15 templates)
│   ├── base.html             # Base layout (navbar + footer)
│   ├── index.html            # Homepage
│   ├── movies.html           # Movies listing page
│   ├── streaming.html        # Anime episode streaming page
│   ├── streaming_movie.html  # Movie streaming page
│   ├── category.html         # Genre category page
│   ├── login.html            # Login form
│   ├── signup.html           # Registration form
│   ├── profile.html          # User profile
│   ├── edit_profile.html     # Edit profile
│   ├── playlist.html         # User playlist
│   ├── reset_password.html              # Password reset request
│   ├── password_reset_done.html         # Reset email sent confirmation
│   ├── password_reset_confirm.html      # New password form
│   └── password_reset_complete.html     # Reset complete confirmation
├── static/
│   └── assets/               # CSS, JS, images, fonts
├── staticfiles/              # WhiteNoise-collected static files
├── manage.py                 # Django management CLI
└── data.json                 # Optional fixture data
```

### Key Source Code Excerpts

**models.py — Anime Model (selected)**
```python
class Anime(models.Model):
    AGE_CHOICES = [('pg', 'PG'), ('pg13', 'PG-13'), ('r', '18+')]
    title = models.CharField(max_length=100)
    description = models.TextField()
    genres = models.ManyToManyField('Genre', blank=True)
    studio = models.CharField(max_length=100, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1,
                                  validators=[MinValueValidator(0), MaxValueValidator(10)])
    age_rating = models.CharField(max_length=10, choices=AGE_CHOICES, default='pg13')
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)

    def get_image(self, img_type):
        for img in self.media_images.all():  # uses prefetch cache
            if img.type == img_type:
                return img
        return None
```

**views.py — attach_episode_info (N+1 fix)**
```python
def attach_episode_info(anime_list):
    for anime in anime_list:
        seasons = list(anime.seasons.all())
        first_season = seasons[0] if seasons else None
        first_episode = list(first_season.episodes.all())[0] if first_season else None
        anime.first_season = first_season
        anime.first_episode = first_episode
    return anime_list
```

**views.py — like_comment (AJAX toggle)**
```python
@login_required
@require_POST
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    like, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'total_likes': comment.total_likes()})
```

**widgets.py — CloudinaryVideoWidget**
```python
class CloudinaryVideoWidget(forms.Widget):
    def __init__(self, cloud_name, upload_preset, attrs=None):
        self.cloud_name = cloud_name
        self.upload_preset = upload_preset
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # Renders a Cloudinary Upload Widget button + hidden input
        # On upload success, writes secure_url into hidden input
        ...
```

---

# Chapter 6: Testing and Maintenance

## 6.1 System Testing

### Test Types Applied

#### Unit Testing
Django's `TestCase` class is available via `ananimeclip/tests.py`. The following functional areas were manually tested:

| Test Case | Input | Expected Output | Result |
|---|---|---|---|
| User Registration — valid data | name, age, email, password | Account created, redirect to home | ✅ Pass |
| User Registration — passwords mismatch | Different passwords | Error: "Passwords do not match" | ✅ Pass |
| User Registration — duplicate email | Existing email | Error: "Email already registered" | ✅ Pass |
| Login — valid credentials | Email + password | Redirect to home | ✅ Pass |
| Login — invalid credentials | Wrong password | Error: "Invalid email or password" | ✅ Pass |
| Comment — authenticated user | Valid body text | Comment saved, redirected back | ✅ Pass |
| Comment — unauthenticated user | Any POST | Redirect to /login/ | ✅ Pass |
| Like — new like | Click like button | liked=True, count incremented | ✅ Pass |
| Like — toggle unlike | Click like again | liked=False, count decremented | ✅ Pass |
| Live Search — query with results | "naruto" | JSON with matching titles | ✅ Pass |
| Live Search — empty query | "" | Empty results JSON | ✅ Pass |
| Streaming page — valid episode | /streaming/1/ | Video player renders | ✅ Pass |
| Streaming page — invalid episode | /streaming/9999/ | 404 response | ✅ Pass |
| Category page — valid genre | /category/action/ | Filtered anime + movies shown | ✅ Pass |
| Password Reset | Valid email | Reset email sent (console backend) | ✅ Pass |

#### Integration Testing
- Homepage view tested with populated database — all carousels, weekly schedule, and coming soon block render correctly.
- Admin panel tested — anime, movies, episodes, video sources can be created, edited, and deleted through the admin UI.
- Cloudinary upload widget tested — video upload completes and URL is saved to `VideoSource.video_url`.

#### Performance Testing (Manual)
- Confirmed `prefetch_related` usage prevents N+1 queries on the homepage.
- Django Debug Toolbar (if enabled) would show query count reduction from O(n) to O(1) per carousel block.

---

## 6.2 Feasibility Study

### Technical Feasibility
The project is technically feasible. Django is a mature, production-grade framework with extensive documentation and community support. PostgreSQL is a widely used, battle-tested RDBMS. Cloudinary offers a generous free tier and a simple Python SDK. Bootstrap 5 is the industry-standard responsive UI framework. All chosen technologies are open-source, well-documented, and actively maintained.

### Economic Feasibility
| Resource | Cost |
|---|---|
| Python / Django / PostgreSQL | Free (open source) |
| Cloudinary (free tier) | Free (25 GB storage, 25 GB/month bandwidth) |
| Development Tools (VS Code, Git) | Free |
| Hosting (Railway / Render free tier) | Free (with limits) |
| Domain Name (optional) | ~$10–15/year |
| **Total Estimated Cost** | **~$0–$15/year** |

The project is highly economically feasible for a student or small-scale deployment.

### Operational Feasibility
The system is straightforward to operate. Content managers use the Django Admin — a familiar web interface — to manage all content without developer intervention. The Cloudinary Upload Widget further simplifies video upload. User operations (browse, search, watch, comment) are intuitive and require no training.

### Legal Feasibility
The project uses only properly licensed open-source libraries. Video content hosted on Cloudinary must be content the operator has rights to distribute. For educational/demo purposes, fair-use content may be used.

### Schedule Feasibility
The core application was implementable within a typical academic semester (~4–5 months). Key milestones:
1. Week 1–2: Project setup, models, migrations
2. Week 3–4: Admin setup, data entry, Cloudinary integration
3. Week 5–6: Views and URL routing
4. Week 7–9: Templates (homepage, streaming, movies)
5. Week 10–11: Authentication (login, signup, password reset)
6. Week 12–13: Comments, likes, live search, categories
7. Week 14–15: UI polish, testing, deployment preparation

---

# Chapter 7: Conclusion

## 7.1 Future Scope

The following enhancements are planned or proposed for future versions of AnimeClip:

1. **Manga Reader Module:** The navigation bar already has a "Manga" link stub. A future module could support chapter-by-chapter manga reading with image pages stored in Cloudinary.

2. **Watchlist / Playlist Functionality:** The `/playlist/` page is stubbed. Future implementation would allow users to save anime/movies to personal watchlists with watch-later functionality.

3. **User Ratings:** The streaming page has a "Rate the Show" section showing `_/10`. Future implementation would allow users to submit ratings that feed into the anime's average rating score.

4. **Recommendation Engine:** A content-based or collaborative filtering recommendation engine to suggest anime/movies based on user watch history and genre preferences.

5. **Notification System:** Email or in-app notifications when a new episode of a followed anime is released (integrating with the existing weekly schedule and coming-soon data).

6. **Mobile Application:** A React Native or Flutter mobile app consuming a Django REST Framework (DRF) API backend derived from the existing views.

7. **Subtitle Support:** Embed `.vtt` or `.srt` subtitle files alongside video sources for enhanced accessibility.

8. **Social Sharing:** Allow users to share specific episodes or movies to social media platforms.

9. **Advanced Search & Filtering:** Filter by genre, rating range, age rating, studio, status (ongoing/completed/upcoming), and release year.

10. **Content Moderation:** Admin tools to flag, moderate, or auto-filter abusive comments.

---

## 7.2 Limitations

1. **No Real-Time Functionality:** Comments and likes (except the like toggle) require a page refresh to see updates from other users. WebSocket support (Django Channels) would be needed for real-time chat.

2. **No Email Notifications:** `EMAIL_BACKEND` is set to `console.EmailBackend` — emails are printed to the terminal rather than sent. A production SMTP backend (SendGrid, AWS SES) must be configured for real password resets.

3. **Playlist Not Implemented:** The playlist/watchlist feature is present in the navigation and URL routing but the underlying functionality (saving items, displaying them) is not yet implemented.

4. **No User Ratings:** The anime rating displayed is admin-set. There is no mechanism for users to submit their own ratings.

5. **Static Genre List:** The genre categories in the navbar are hard-coded in `base.html`. Adding a new genre via admin does not automatically appear in the navbar.

6. **No Pagination on Most Pages:** Content lists (recent, popular, top rated) are limited by slicing (e.g., `[:8]`) rather than proper paginated browsing.

7. **Limited Test Coverage:** Automated test coverage in `tests.py` is minimal. A full test suite with Django's `TestCase` class and factory libraries would improve confidence during refactoring.

8. **DEBUG=True in Settings:** The settings file has `DEBUG = True` which must be changed to `False` before production deployment, along with setting `ALLOWED_HOSTS`.

---

## 7.3 Conclusion

AnimeClip successfully demonstrates the development of a full-featured, production-quality anime streaming web application using the Django framework and a modern supporting technology stack. The project covers all major aspects of web application development: database design and ORM usage, user authentication and authorization, cloud media storage and delivery, responsive UI design, AJAX-powered interactions, content discovery and search, and admin-driven content management.

The hierarchical content model (Anime → Season → Episode → VideoSource) cleanly maps to the real-world structure of anime series and enables flexible content organization. Performance-conscious development decisions — such as `prefetch_related` and Python-level grouping in `attach_episode_info` — demonstrate awareness of database efficiency in web applications.

The project provides a solid foundation for a production anime streaming platform. With the future enhancements outlined (manga reader, real-time features, recommendation engine, mobile app), AnimeClip has the potential to evolve into a comprehensive anime entertainment hub. The codebase is clean, well-structured, and follows Django best practices, making it maintainable and extensible for future development.

---

# Chapter 8: Bibliography

## 8.1 Bibliography

1. Django Software Foundation. (2024). *Django Documentation*. https://docs.djangoproject.com/

2. Cloudinary. (2024). *Cloudinary Documentation — Django Integration*. https://cloudinary.com/documentation/django_integration

3. PostgreSQL Global Development Group. (2024). *PostgreSQL Documentation*. https://www.postgresql.org/docs/

4. Bootstrap Team. (2024). *Bootstrap 5 Documentation*. https://getbootstrap.com/docs/5.3/

5. Ken Wheeler. (2024). *Slick Carousel Documentation*. https://kenwheeler.github.io/slick/

6. Font Awesome. (2024). *Font Awesome Documentation*. https://fontawesome.com/

7. WhiteNoise Contributors. (2024). *WhiteNoise Documentation*. https://whitenoise.readthedocs.io/

8. Python Software Foundation. (2024). *Python 3 Documentation*. https://docs.python.org/3/

9. MDN Web Docs. (2024). *HTML5 Video Element*. https://developer.mozilla.org/en-US/docs/Web/HTML/Element/video

10. jQuery Foundation. (2024). *jQuery API Documentation*. https://api.jquery.com/

---

# Chapter 9: Appendix

## 9.1 Appendix

### Appendix A: Project Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/Risheek-Shrestha/AnimeClip.git
cd AnimeClip

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install django psycopg2-binary cloudinary django-cloudinary-storage
pip install python-dotenv whitenoise pillow

# 4. Create .env file with required variables
cat > .env << EOF
SECRET_KEY=your-django-secret-key
DB_NAME=animeclip_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
EOF

# 5. Create PostgreSQL database
createdb animeclip_db

# 6. Run migrations
python manage.py migrate

# 7. Create superuser (admin)
python manage.py createsuperuser

# 8. Collect static files
python manage.py collectstatic

# 9. Run development server
python manage.py runserver
```

### Appendix B: URL Routes Reference

| Route | View | Name |
|---|---|---|
| `/` | `index` | `index` |
| `/login/` | `login_view` | `login` |
| `/signup/` | `signup` | `signup` |
| `/logout/` | `LogoutView` | `logout` |
| `/profile/` | `profile` | `profile` |
| `/editprofile/` | `edit_profile` | `edit_profile` |
| `/playlist/` | `playlist` | `playlist` |
| `/movies/` | `movies` | `movies` |
| `/streaming/<episode_id>/` | `streaming` | `streaming` |
| `/streaming_movie/<movie_id>/` | `streaming_movie` | `streaming_movie` |
| `/episode/<episode_id>/comment/` | `add_comment` | `add_comment` |
| `/movie/<movie_id>/comment/` | `add_movie_comment` | `add_movie_comment` |
| `/comment/<comment_id>/like/` | `like_comment` | `like_comment` |
| `/live-search/` | `live_search` | `live_search` |
| `/category/<genre>/` | `category_page` | `category_page` |
| `/password-reset/` | `PasswordResetView` | `password_reset` |
| `/password-reset/done/` | `PasswordResetDoneView` | `password_reset_done` |
| `/password-reset-confirm/<uidb64>/<token>/` | `PasswordResetConfirmView` | `password_reset_confirm` |
| `/password-reset-complete/` | `PasswordResetCompleteView` | `password_reset_complete` |

### Appendix C: Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key for cryptographic signing | `django-insecure-...` |
| `DB_NAME` | PostgreSQL database name | `animeclip_db` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `password123` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `my_cloud` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `abc123xyz` |

### Appendix D: Django Models Summary

| Model | Fields | Key Relations |
|---|---|---|
| `Profile` | age | OneToOne → User |
| `Genre` | name | — |
| `Anime` | title, description, studio, country, rating, age_rating, is_featured, is_popular | M2M → Genre |
| `Movie` | title, description, studio, country, release_date, release_day, release_time, rating, is_featured, is_popular, duration_mins | M2M → Genre |
| `Season` | number, title, release_date, release_day, release_time, status | FK → Anime |
| `Episode` | number, title, release_date, release_day, release_time, updated_at | FK → Season |
| `VideoSource` | label, type, video_url, poster | FK → Episode |
| `MovieSource` | label, type, video_url, poster | FK → Movie |
| `MediaImage` | image, type | FK → Anime or Movie |
| `Comment` | body, created_at | FK → User, Episode/Movie, self (parent) |
| `CommentLike` | — | FK → User, Comment (unique together) |

---

*End of Project Report — AnimeClip*
