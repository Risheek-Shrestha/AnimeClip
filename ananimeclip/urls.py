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
    path('playlist/', views.playlist, name='playlist'),
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

]
