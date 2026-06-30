from django.contrib.auth import views as auth_views
from django.urls import include, path

from ananimeclip import billing as billing_views
from ananimeclip import reporting as report_views
from ananimeclip import session_views, views
from ananimeclip import totp as totp_views
from ananimeclip import trending as trending_views
from ananimeclip import watch_party as wp_views
from ananimeclip import web_push as push_views

urlpatterns = [
    path('healthz/', views.healthz, name='healthz'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('streaming/<int:episode_id>/', views.streaming, name='streaming'),
    path('streaming_movie/<int:movie_id>/', views.streaming_movie, name='streaming_movie'),
    path('watch/<str:token>/', views.stream_redirect, name='stream_redirect'),
    # comment actions
    path('episode/<int:episode_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('movie/<int:movie_id>/comment/', views.add_movie_comment, name='add_movie_comment'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('editprofile/', views.edit_profile, name='edit_profile'),
    path('movies/', views.movies, name='movies'),
    # password reset flow
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(template_name='reset_password.html'),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
        name='password_reset_confirm',
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('live-search/', views.live_search, name='live_search'),
    path('category/<str:genre>/', views.category_page, name='category_page'),
    path('search/', views.search_results, name='search_results'),
    path('categories/', views.all_categories, name='all_categories'),
    path('trending/', trending_views.trending, name='trending'),
    # Watch history
    path('watch-history/update/', views.update_watch_history, name='update_watch_history'),
    path('continue-watching/', views.continue_watching, name='continue_watching'),
    # Watch later
    path('watch-later/', views.watch_later, name='watch_later'),
    path('watch-later/toggle/', views.toggle_watch_later, name='toggle_watch_later'),
    # Playlists
    path('playlists/', views.playlists, name='playlists'),
    path('playlists/create/', views.create_playlist, name='create_playlist'),
    path('playlists/add-item/', views.add_to_playlist, name='add_to_playlist'),
    path('playlists/remove-item/<int:item_id>/', views.remove_from_playlist, name='remove_from_playlist'),
    path('playlists/json/', views.get_user_playlists, name='get_user_playlists'),
    path('playlists/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('playlists/<int:playlist_id>/delete/', views.delete_playlist, name='delete_playlist'),
    # Anime
    path('anime/recent/', views.all_recent_anime, name='all_recent_anime'),
    path('anime/popular/', views.all_popular_anime, name='all_popular_anime'),
    path('anime/<slug:slug>/', views.anime_detail, name='anime_detail'),
    path('anime/<int:anime_id>/follow/', views.toggle_follow, name='toggle_follow'),
    path('movie/<int:movie_id>/follow/', views.toggle_follow_movie, name='toggle_follow_movie'),
    path('favourites/', views.favourites, name='favourites'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/count/', views.unread_notification_count, name='unread_notification_count'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('profiles/', views.profile_select, name='profile_select'),
    path('profiles/create/', views.profile_create, name='profile_create'),
    path('profiles/<int:subprofile_id>/switch/', views.profile_switch, name='profile_switch'),
    path('profiles/<int:subprofile_id>/delete/', views.profile_delete, name='profile_delete'),
    path('anime/<int:anime_id>/rate/', views.rate_anime, name='rate_anime'),
    path('movie/<int:movie_id>/rate/', views.rate_movie, name='rate_movie'),
    path('movies/recent/', views.all_recent_movies, name='all_recent_movies'),
    path('movies/popular/', views.all_popular_movies, name='all_popular_movies'),
    # Offline downloads
    path('download/episode/<int:episode_id>/', views.request_episode_download, name='request_episode_download'),
    path('download/movie/<int:movie_id>/', views.request_movie_download, name='request_movie_download'),
    path('dl/<str:token>/', views.serve_download, name='serve_download'),
    # Content reporting
    path('report/episode/<int:episode_id>/', report_views.report_episode, name='report_episode'),
    path('report/movie/<int:movie_id>/', report_views.report_movie, name='report_movie'),
    path('offline/', views.offline, name='offline'),
    path('sw.js', views.service_worker, name='service_worker'),
    # Watch Party
    path('watch-party/create/', wp_views.create_watch_party, name='create_watch_party'),
    path('watch-party/<str:room_code>/', wp_views.watch_party_room, name='watch_party_room'),
    path('watch-party/<str:room_code>/join/', wp_views.join_watch_party, name='join_watch_party'),
    path('watch-party/<str:room_code>/state/', wp_views.watch_party_state, name='watch_party_state'),
    path('watch-party/<str:room_code>/sync/', wp_views.sync_watch_party, name='sync_watch_party'),
    path('watch-party/<str:room_code>/end/', wp_views.end_watch_party, name='end_watch_party'),
    # 2FA
    path('account/2fa/setup/', totp_views.totp_setup, name='totp_setup'),
    path('account/2fa/disable/', totp_views.totp_disable, name='totp_disable'),
    path('account/2fa/verify/', totp_views.totp_verify, name='totp_verify'),
    # Session / Device management
    path('account/devices/', session_views.device_list, name='device_list'),
    path('account/devices/revoke/', session_views.revoke_device, name='revoke_device'),
    path('account/devices/revoke-others/', session_views.revoke_other_devices, name='revoke_other_devices'),
    # Stream heartbeat
    path('stream/heartbeat/', session_views.stream_heartbeat_view, name='stream_heartbeat'),
    # Web Push
    path('push/subscribe/', push_views.push_subscribe, name='push_subscribe'),
    path('push/unsubscribe/', push_views.push_unsubscribe, name='push_unsubscribe'),
    path('push/vapid-key/', push_views.vapid_public_key, name='push_vapid_key'),
    # Upgrade page
    path('upgrade/', views.upgrade, name='upgrade'),
    # Stripe billing (checkout, portal, post-checkout landing pages — webhook lives
    # in Hello/urls.py since it must stay outside the catch-all and CSRF-exempt)
    path('billing/checkout/', billing_views.create_checkout_session, name='billing_checkout'),
    path('billing/portal/', billing_views.create_customer_portal_session, name='billing_portal'),
    path('billing/success/', billing_views.billing_success, name='billing_success'),
    path('billing/cancel/', billing_views.billing_cancel, name='billing_cancel'),
    # Password change (logged-in flow, separate from forgot-password reset)
    path('account/password/', views.change_password, name='change_password'),
    # Account deletion & GDPR data export
    path('account/delete/', views.request_account_deletion, name='request_account_deletion'),
    path('account/export/', views.export_user_data, name='export_user_data'),
    # Simulcast / release calendar
    path('schedule/', views.simulcast_calendar, name='simulcast_calendar'),
    # i18n language switcher
    path('i18n/', include('django.conf.urls.i18n')),
]
