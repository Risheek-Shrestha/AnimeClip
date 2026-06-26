from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from ananimeclip import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('streaming/<int:episode_id>/', views.streaming, name='streaming'),
    path('streaming_movie/<int:movie_id>/', views.streaming_movie, name='streaming_movie'),

    # comment actions
    path('episode/<int:episode_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('movie/<int:movie_id>/comment/', views.add_movie_comment, name='add_movie_comment'),

    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('editprofile/', views.edit_profile, name='edit_profile'),
    path('movies/', views.movies, name='movies'),

    # password reset flow
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(template_name='reset_password.html'),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
        name='password_reset_complete'
    ),

    path('live-search/', views.live_search, name='live_search'),
    path('category/<str:genre>/', views.category_page, name='category_page'),

    path('search/', views.search_results, name='search_results'),
    path('categories/', views.all_categories, name='all_categories'),

    # Watch history
    path('watch-history/update/', views.update_watch_history, name='update_watch_history'),
    path('continue-watching/', views.continue_watching, name='continue_watching'),

    # Watch later
    path('watch-later/', views.watch_later, name='watch_later'),
    path('watch-later/toggle/', views.toggle_watch_later, name='toggle_watch_later'),

    # Playlists — fixed sub-paths MUST come before <int:playlist_id> capture
    # so Django matches them first and doesn't try to cast 'add-item'/'json' as int.
    path('playlists/', views.playlists, name='playlists'),
    path('playlists/create/', views.create_playlist, name='create_playlist'),
    path('playlists/add-item/', views.add_to_playlist, name='add_to_playlist'),
    path('playlists/remove-item/<int:item_id>/', views.remove_from_playlist, name='remove_from_playlist'),
    path('playlists/json/', views.get_user_playlists, name='get_user_playlists'),
    path('playlists/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('playlists/<int:playlist_id>/delete/', views.delete_playlist, name='delete_playlist'),

    path('anime/<int:anime_id>/follow/', views.toggle_follow, name='toggle_follow'),
    path('movie/<int:movie_id>/follow/', views.toggle_follow_movie, name='toggle_follow_movie'),
    path('favourites/', views.favourites, name='favourites'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/count/', views.unread_notification_count, name='unread_notification_count'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),

    # Sub-profile switcher
    path('profiles/', views.profile_select, name='profile_select'),
    path('profiles/switch/<int:subprofile_id>/', views.profile_switch, name='profile_switch'),
    path('profiles/create/', views.profile_create, name='profile_create'),
    path('profiles/delete/<int:subprofile_id>/', views.profile_delete, name='profile_delete'),
    path('anime/<int:anime_id>/rate/', views.rate_anime, name='rate_anime'),
    path('movie/<int:movie_id>/rate/', views.rate_movie, name='rate_movie'),
    path('movies/recent/', views.all_recent_movies, name='all_recent_movies'),
    path('movies/popular/', views.all_popular_movies, name='all_popular_movies'),
    path('anime/recent/', views.all_recent_anime, name='all_recent_anime'),
    path('anime/popular/', views.all_popular_anime, name='all_popular_anime'),
]