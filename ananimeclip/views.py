from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Profile, Anime, Episode, Comment, CommentLike, Season, MediaImage, Movie
from django.db.models import Max, Prefetch, Q
from django.utils import timezone
from datetime import timedelta, datetime

context = {
    'title': 'ananimeclip',
}


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

    # Featured
    featured_animes = Anime.objects.filter(
        is_featured=True
    ).prefetch_related(
        'media_images',
        'seasons__episodes__sources'
    )

    # Recently updated
    recent_animes = list(
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update')[:8].prefetch_related(
            'media_images',
            'seasons__episodes__sources'
        )
    )

    # comint_out_in
    coming_soon_season = Season.objects.filter(
        status='upcoming',
        release_date__isnull=False
    ).select_related('anime').prefetch_related(
        'anime__media_images',
        'anime__genres',
        'episodes__sources'
    ).order_by('release_date').first()

    # Popular animes
    popular_animes = Anime.objects.filter(
        is_popular=True
    ).prefetch_related(
        'media_images',
        'seasons__episodes__sources'
    )

    # Weekly schedule — group animes by their season's release_day
    for day in week_days:
        day_name = day['day']

        day_animes = Anime.objects.filter(
            seasons__release_day=day_name
        ).prefetch_related(
            'media_images',
            'seasons__episodes__sources'
        ).distinct()

        day['animes'] = day_animes

    # Top rated
    top_animes = Anime.objects.order_by('-rating')[:5].prefetch_related(
        'media_images',
        'seasons__episodes__sources'
    )

    # New — most recently added seasons
    new_animes = Anime.objects.annotate(
        latest_update=Max('seasons__episodes__updated_at')
    ).order_by('-latest_update')[:5].prefetch_related(
        'media_images',
        'seasons__episodes__sources'
    )

    # Recently completed
    completed_animes = Anime.objects.filter(
        seasons__status='completed'
    ).prefetch_related(
        'media_images',
        'seasons__episodes__sources'
    ).distinct()[:5]

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
    )

    # Popular movies
    popular_movies = Movie.objects.filter(
        is_popular=True
    ).prefetch_related(
        'media_images',
        'sources',
        'genres',
    )

    context = {
        'title': 'ananimeclip - Movies',
        'featured_movies': featured_movies,
        'recent_movies': recent_movies,
        'coming_soon_movie': coming_soon_movie,
        'top_rated_movies': top_rated_movies,
        'popular_movies': popular_movies,
    }
    return render(request, 'movies.html', context)


@login_required
def profile(request):
    return render(request, "profile.html", context)


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


def streaming_movie(request):
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

        anime = Anime.objects.filter(
            Q(title__icontains=query)
        )[:5]

        for movie in movies:
            results.append({
                'id': movie.id,
                'title': movie.title,
                'type': 'movie'
            })

        for a in anime:
            first_episode = a.seasons.first().episodes.first() if a.seasons.exists() else None

            if first_episode:
                results.append({
                    'id': first_episode.id,
                    'title': a.title,
                    'type': 'anime'
                })

    return JsonResponse({'results': results})

def category_page(request, genre):
    movies = Movie.objects.filter(genres__name__iexact=genre)
    anime = Anime.objects.filter(genres__name__iexact=genre)

    return render(request, 'category.html', {
        'genre': genre,
        'movies': movies,
        'anime': anime,
    })
