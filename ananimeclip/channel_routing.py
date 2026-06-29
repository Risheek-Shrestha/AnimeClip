"""
Django Channels routing for live support chat WebSocket.
"""
from django.urls import re_path

try:
    from .consumers import SupportChatConsumer
    websocket_urlpatterns = [
        re_path(r"ws/support/(?P<ticket_id>\d+)/$", SupportChatConsumer.as_asgi()),
    ]
except ImportError:
    websocket_urlpatterns = []
