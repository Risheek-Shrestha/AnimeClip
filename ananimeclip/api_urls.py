"""
URL patterns for the /api/v1/ REST surface.

Mounted in Hello/urls.py under the prefix api/v1/.
"""

from django.urls import path

from . import api_views

urlpatterns = [
    # Public catalog
    path('anime/', api_views.api_anime_list, name='api_anime_list'),
    path('anime/<slug:slug>/', api_views.api_anime_detail, name='api_anime_detail'),
    path('movies/', api_views.api_movie_list, name='api_movie_list'),
    path('movies/<int:movie_id>/', api_views.api_movie_detail, name='api_movie_detail'),
    path('genres/', api_views.api_genre_list, name='api_genre_list'),
    # Authenticated user
    path('me/', api_views.api_me, name='api_me'),
    path('me/watch-history/', api_views.api_watch_history, name='api_watch_history'),
    path('me/watch-history/<int:history_id>/', api_views.api_delete_watch_history, name='api_delete_watch_history'),
    path('me/watch-later/', api_views.api_watch_later, name='api_watch_later'),
    path('me/recommendations/', api_views.api_recommendations, name='api_recommendations'),
]
