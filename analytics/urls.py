from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/watch/', views.record_watch, name='record_watch'),
    path('api/search/', views.record_search, name='record_search'),
]
