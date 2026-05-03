from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Profile, Anime, Episode, Comment, CommentLike, Season, MediaImage, Movie, Genre, WatchHistory, WatchLater, Playlist, PlaylistItem
from django.db.models import Max, Prefetch, Q
from django.utils import timezone
from datetime import timedelta, datetime

context = {
    'title': 'ananimeclip',
}


def attach_episode_info(anime_list):

    for anime in anime_list:
        seasons = list(anime.seasons.all())
        first_season = seasons[0] if seasons else None
        if first_season:
            episodes = list(first_season.episodes.all())
            first_episode = episodes[0] if episodes else None
        else:
            first_episode = None
        anime.first_season = first_season
        anime.first_episode = first_episode
    return anime_list


def index(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    week_days = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        week_days.append({
            'day': d.strftime('%A'),
            'date': d.strftime('%B ') + str(d.day),
            'id': d.strftime('%A').lower(),
            'is_today': d == today,
        })

    day_names = [d['day'] for d in week_days]

    # Featured
    featured_animes = list(
        Anime.objects.filter(
            is_featured=True
        ).prefetch_related(
            'media_images',
            'seasons__episodes__sources',
        )
    )
    attach_episode_info(featured_animes)

    # Recently updated
    recent_animes = list(
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update')[:8].prefetch_related(
            'media_images',
            'seasons__episodes__sources',
        )
    )
    attach_episode_info(recent_animes)

    # Coming soon
    coming_soon_season = Season.objects.filter(
        status='upcoming',
        release_date__isnull=False
    ).select_related('anime').prefetch_related(
        'anime__media_images',
        'anime__genres',
        'episodes__sources',
    ).order_by('release_date').first()

    # Popular animes
    popular_animes = list(
        Anime.objects.filter(
            is_popular=True
        ).prefetch_related(
            'media_images',
            'seasons__episodes__sources',
        )
    )
    attach_episode_info(popular_animes)

    # Weekly schedule — single query, grouped in Python
    scheduled_animes = list(
        Anime.objects.filter(
            seasons__release_day__in=day_names
        ).prefetch_related(
            'media_images',
            'seasons__episodes__sources',
        ).distinct()
    )
    attach_episode_info(scheduled_animes)

    schedule_map = {}
    for anime in scheduled_animes:
        for season in anime.seasons.all():
            if season.release_day in day_names:
                schedule_map.setdefault(season.release_day, [])
                if anime not in schedule_map[season.release_day]:
                    schedule_map[season.release_day].append(anime)

    for day in week_days:
        day['animes'] = schedule_map.get(day['day'], [])

    # Top rated
    top_animes = list(
        Anime.objects.order_by('-rating')[:5].prefetch_related(
            'media_images',
            'seasons__episodes',
        )
    )
    attach_episode_info(top_animes)

    # New — most recently added
    new_animes = list(
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update')[:5].prefetch_related(
            'media_images',
            'seasons__episodes',
        )
    )
    attach_episode_info(new_animes)

    # Recently completed
    completed_animes = list(
        Anime.objects.filter(
            seasons__status='completed'
        ).prefetch_related(
            'media_images',
            'seasons__episodes',
        ).distinct()[:5]
    )
    attach_episode_info(completed_animes)

    # User-specific data
    user_history = []
    user_watch_later = []
    if request.user.is_authenticated:
        user_history = list(
            WatchHistory.objects.filter(
                user=request.user
            ).select_related(
                'episode__season__anime', 'movie'
            ).prefetch_related(
                'episode__season__anime__media_images',
                'movie__media_images',
            ).order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(
                user=request.user
            ).select_related(
                'episode__season__anime', 'movie'
            ).prefetch_related(
                'episode__season__anime__media_images',
                'movie__media_images',
            ).order_by('-added_at')[:8]
        )

    context = {
        'title': 'ananimeclip',
        'today': today,
        'week_days': week_days,
        'featured_animes': featured_animes,
        'Recent_animes': recent_animes,
        'coming_soon_season': coming_soon_season,
        'Popular_animes': popular_animes,
        'top_animes': top_animes,
        'new_animes': new_animes,
        'completed_animes': completed_animes,
        'user_history': user_history,
        'user_watch_later': user_watch_later,
    }
    return render(request, 'index.html', context)


def movies(request):
    today = timezone.now().date()

    # Featured movies for banner slider (up to 3)
    featured_movies = Movie.objects.filter(
        is_featured=True
    ).prefetch_related(
        'media_images',
        'sources',
        'genres',
    )[:3]

    # Recently updated — ordered by latest release_date
    recent_movies = Movie.objects.filter(
        release_date__isnull=False
    ).prefetch_related(
        'media_images',
        'sources',
        'genres',
    ).order_by('-release_date')[:8]

    # Coming soon movie — nearest future release
    coming_soon_movie = Movie.objects.filter(
        release_date__gt=today
    ).prefetch_related(
        'media_images',
        'sources',
        'genres',
    ).order_by('release_date').first()

    # Top rated movies
    top_rated_movies = Movie.objects.order_by('-rating')[:6].prefetch_related(
        'media_images',
        'sources',
        'genres',
    )

    # Popular movies
    popular_movies = Movie.objects.filter(
        is_popular=True
    ).prefetch_related(
        'media_images',
        'sources',
        'genres',
    )

    user_history = []
    user_watch_later = []
    if request.user.is_authenticated:
        user_history = list(
            WatchHistory.objects.filter(
                user=request.user,
                movie__isnull=False  # only movies on the movies page
            ).select_related('movie').prefetch_related(
                'movie__media_images',
            ).order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(
                user=request.user,
                movie__isnull=False
            ).select_related('movie').prefetch_related(
                'movie__media_images',
            ).order_by('-added_at')[:8]
        )

    context = {
        'title': 'ananimeclip - Movies',
        'featured_movies': featured_movies,
        'recent_movies': recent_movies,
        'coming_soon_movie': coming_soon_movie,
        'top_rated_movies': top_rated_movies,
        'popular_movies': popular_movies,
        'user_history': user_history,
        'user_watch_later': user_watch_later,
    }
    return render(request, 'movies.html', context)


@login_required
def profile(request):
    history = WatchHistory.objects.filter(
        user=request.user
    ).select_related(
        'episode__season__anime', 'movie'
    ).prefetch_related(
        'episode__season__anime__media_images',
        'movie__media_images',
    ).order_by('-updated_at')[:20]

    watch_later_count = WatchLater.objects.filter(user=request.user).count()
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('items')

    return render(request, 'profile.html', {
        'title': f'{request.user.first_name} - Profile',
        'history': history,
        'watch_later_count': watch_later_count,
        'playlists': playlists,
    })

@login_required
def edit_profile(request):
    return render(request, "edit_profile.html", context)


@login_required
def playlist(request):
    return render(request, "playlist.html", context)


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            return render(request, "login.html", {
                "title": "ananimeclip",
                "error": "Invalid email or password"
            })
    return render(request, "login.html", {"title": "ananimeclip"})


def signup(request):
    if request.method == "POST":
        name = request.POST.get("name")
        age = request.POST.get("age")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "signup.html", {
                "title": "ananimeclip",
                "error": "Passwords do not match"
            })

        if User.objects.filter(username=email).exists():
            return render(request, "signup.html", {
                "title": "ananimeclip",
                "error": "Email already registered"
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        Profile.objects.create(user=user, age=age)
        login(request, user)
        return redirect("index")

    return render(request, "signup.html", context)


def streaming(request, episode_id):
    episode = get_object_or_404(
        Episode.objects.select_related('season__anime'),
        id=episode_id
    )
    anime = episode.season.anime
    anime_with_images = Anime.objects.prefetch_related('media_images').get(pk=anime.pk)

    seasons = anime.seasons.prefetch_related('episodes').all()
    comments = episode.comments.filter(parent=None).prefetch_related(
        'replies__user', 'likes', 'replies__likes'
    ).select_related('user')

    context = {
        'title': anime.title,
        'episode': episode,
        'anime': anime_with_images,
        'seasons': seasons,
        'comments': comments,
    }
    return render(request, 'streaming.html', context)


def streaming_movie(request, movie_id):
    movie = get_object_or_404(
        Movie.objects.prefetch_related('media_images', 'sources', 'genres'),
        id=movie_id
    )
    comments = movie.comments.filter(parent=None).prefetch_related(
        'replies__user', 'likes', 'replies__likes'
    ).select_related('user')

    context = {
        'title': movie.title,
        'movie': movie,
        'comments': comments,
    }
    return render(request, 'streaming_movie.html', context)


@login_required
@require_POST
def add_comment(request, episode_id):
    episode = get_object_or_404(Episode, id=episode_id)
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if body:
        comment = Comment(episode=episode, user=request.user, body=body)
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id)
        comment.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def add_movie_comment(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if body:
        comment = Comment(movie=movie, user=request.user, body=body)
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id)
        comment.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


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


def reset(request):
    return render(request, "reset_password.html", context)


def live_search(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        movies = Movie.objects.filter(
            Q(title__icontains=query)
        )[:5]

        anime_qs = Anime.objects.filter(
            Q(title__icontains=query)
        ).prefetch_related('seasons__episodes')[:5]

        for movie in movies:
            results.append({
                'id': movie.id,
                'title': movie.title,
                'type': 'movie'
            })

        for a in anime_qs:
            seasons = list(a.seasons.all())
            if seasons:
                episodes = list(seasons[0].episodes.all())
                first_episode = episodes[0] if episodes else None
            else:
                first_episode = None

            if first_episode:
                results.append({
                    'id': first_episode.id,
                    'title': a.title,
                    'type': 'anime'
                })

    return JsonResponse({'results': results})


def category_page(request, genre):
    movies = Movie.objects.filter(genres__name__iexact=genre).prefetch_related('media_images', 'sources')
    anime_list = list(
        Anime.objects.filter(genres__name__iexact=genre).prefetch_related(
            'media_images',
            'seasons__episodes__sources',
        )
    )
    attach_episode_info(anime_list)

    return render(request, 'category.html', {
        'genre': genre,
        'movies': movies,
        'anime': anime_list,
    })


def search_results(request):
    query = request.GET.get('q', '').strip()
    movies = []
    anime_list = []

    if query:
        movies = Movie.objects.filter(
            title__icontains=query
        ).prefetch_related('media_images')

        anime_list = Anime.objects.filter(
            title__icontains=query
        ).prefetch_related('media_images', 'seasons__episodes')
        attach_episode_info(list(anime_list))

    return render(request, 'search_results.html', {
        'query': query,
        'movies': movies,
        'anime_list': anime_list,
    })

def all_categories(request):
    genres = Genre.objects.all()
    return render(request, 'all_categories.html', {'genres': genres})

# ---------- Watch History (Continue Watching) ----------

@login_required
@require_POST
def update_watch_history(request):
    """Called via JS every few seconds with current video progress."""
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')
    progress = int(request.POST.get('progress_seconds', 0))

    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        obj, _ = WatchHistory.objects.update_or_create(
            user=request.user, episode=episode,
            defaults={'progress_seconds': progress, 'movie': None}
        )
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        obj, _ = WatchHistory.objects.update_or_create(
            user=request.user, movie=movie,
            defaults={'progress_seconds': progress, 'episode': None}
        )
    else:
        return JsonResponse({'error': 'No episode or movie id'}, status=400)

    return JsonResponse({'saved': True, 'progress': progress})


@login_required
def continue_watching(request):
    history = WatchHistory.objects.filter(
        user=request.user
    ).select_related(
        'episode__season__anime', 'movie'
    ).prefetch_related(
        'episode__season__anime__media_images',
        'movie__media_images',
    )[:20]

    return render(request, 'continue_watching.html', {'history': history})


# ---------- Watch Later ----------

@login_required
@require_POST
def toggle_watch_later(request):
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')

    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        obj, created = WatchLater.objects.get_or_create(
            user=request.user, episode=episode
        )
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        obj, created = WatchLater.objects.get_or_create(
            user=request.user, movie=movie
        )
    else:
        return JsonResponse({'error': 'No id provided'}, status=400)

    if not created:
        obj.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})


@login_required
def watch_later(request):
    items = WatchLater.objects.filter(
        user=request.user
    ).select_related(
        'episode__season__anime', 'movie'
    ).prefetch_related(
        'episode__season__anime__media_images',
        'movie__media_images',
    )
    return render(request, 'watch_later.html', {'items': items})


# ---------- Playlists ----------

@login_required
def playlists(request):
    user_playlists = Playlist.objects.filter(
        user=request.user
    ).prefetch_related('items')
    return render(request, 'playlists.html', {'playlists': user_playlists})


@login_required
@require_POST
def create_playlist(request):
    name = request.POST.get('name', '').strip()
    if name:
        Playlist.objects.create(user=request.user, name=name)
    return redirect('playlists')


@login_required
def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    items = playlist.items.select_related(
        'episode__season__anime', 'movie'
    ).prefetch_related(
        'episode__season__anime__media_images',
        'movie__media_images',
    )
    return render(request, 'playlist_detail.html', {
        'playlist': playlist,
        'items': items,
    })


@login_required
@require_POST
def add_to_playlist(request):
    playlist_id = request.POST.get('playlist_id')
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')

    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        PlaylistItem.objects.get_or_create(playlist=playlist, episode=episode)
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        PlaylistItem.objects.get_or_create(playlist=playlist, movie=movie)

    return JsonResponse({'status': 'added', 'playlist': playlist.name})


@login_required
@require_POST
def remove_from_playlist(request, item_id):
    item = get_object_or_404(PlaylistItem, id=item_id, playlist__user=request.user)
    item.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def delete_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist.delete()
    return redirect('playlists')


@login_required
def get_user_playlists(request):
    """Returns user's playlists as JSON for the add-to-playlist modal."""
    playlists_data = list(
        Playlist.objects.filter(user=request.user).values('id', 'name')
    )
    return JsonResponse({'playlists': playlists_data})

# Movies - Recently Updated
def all_recent_movies(request):
    movies = Movie.objects.filter(
        release_date__isnull=False
    ).prefetch_related('media_images', 'sources', 'genres').order_by('-release_date')
    return render(request, 'all_recent_movies.html', {
        'title': 'Recently Updated Movies',
        'movies': movies,
    })

# Movies - Popular/Recommended
def all_popular_movies(request):
    movies = Movie.objects.filter(
        is_popular=True
    ).prefetch_related('media_images', 'sources', 'genres')
    return render(request, 'all_popular_movies.html', {
        'title': 'Popular Movies',
        'movies': movies,
    })

# Anime - Recently Updated
def all_recent_anime(request):
    from django.db.models import Max
    anime_list = list(
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update').prefetch_related(
            'media_images', 'seasons__episodes__sources',
        )
    )
    attach_episode_info(anime_list)
    return render(request, 'all_recent_anime.html', {
        'title': 'Recently Updated Anime',
        'anime_list': anime_list,
    })

# Anime - Popular/Recommended
def all_popular_anime(request):
    anime_list = list(
        Anime.objects.filter(
            is_popular=True
        ).prefetch_related(
            'media_images', 'seasons__episodes__sources',
        )
    )
    attach_episode_info(anime_list)
    return render(request, 'all_popular_anime.html', {
        'title': 'Popular Anime',
        'anime_list': anime_list,
    })