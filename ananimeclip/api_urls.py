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
    path('anime/<int:anime_id>/rate/', api_views.api_rate_anime, name='api_rate_anime'),
    path('anime/<int:anime_id>/follow/', api_views.api_toggle_follow_anime, name='api_toggle_follow_anime'),
    path('movies/', api_views.api_movie_list, name='api_movie_list'),
    path('movies/<int:movie_id>/', api_views.api_movie_detail, name='api_movie_detail'),
    path('movies/<int:movie_id>/rate/', api_views.api_rate_movie, name='api_rate_movie'),
    path('movies/<int:movie_id>/follow/', api_views.api_toggle_follow_movie, name='api_toggle_follow_movie'),
    path('movies/<int:movie_id>/comments/', api_views.api_movie_comments, name='api_movie_comments'),
    path('movies/<int:movie_id>/comments/post/', api_views.api_post_movie_comment, name='api_post_movie_comment'),
    path('genres/', api_views.api_genre_list, name='api_genre_list'),
    path('search/', api_views.api_search, name='api_search'),
    path('trending/', api_views.api_trending, name='api_trending'),
    # Episode sub-resources
    path('episodes/<int:episode_id>/comments/', api_views.api_episode_comments, name='api_episode_comments'),
    path(
        'episodes/<int:episode_id>/comments/post/', api_views.api_post_episode_comment, name='api_post_episode_comment'
    ),
    # Authenticated user
    path('me/', api_views.api_me, name='api_me'),
    path('me/watch-history/', api_views.api_watch_history, name='api_watch_history'),
    path('me/watch-history/<int:history_id>/', api_views.api_delete_watch_history, name='api_delete_watch_history'),
    path('me/watch-later/', api_views.api_watch_later, name='api_watch_later'),
    path('me/recommendations/', api_views.api_recommendations, name='api_recommendations'),
    path('me/notifications/', api_views.api_notifications, name='api_notifications'),
    path(
        'me/notifications/read-all/', api_views.api_mark_all_notifications_read, name='api_mark_all_notifications_read'
    ),
    path('me/profiles/', api_views.api_subprofiles, name='api_subprofiles'),
    # Content reporting
    path('report/episode/<int:episode_id>/', api_views.api_report_episode, name='api_report_episode'),
    path('report/movie/<int:movie_id>/', api_views.api_report_movie, name='api_report_movie'),
    # Watch party REST shim
    path('watch-party/create/', api_views.api_create_watch_party, name='api_create_watch_party'),
    path('watch-party/<str:room_code>/state/', api_views.api_watch_party_state, name='api_watch_party_state'),
    path('watch-party/<str:room_code>/sync/', api_views.api_sync_watch_party, name='api_sync_watch_party'),
]
