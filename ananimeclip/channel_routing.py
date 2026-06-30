"""
Django Channels routing for live support chat WebSocket.
"""

from django.urls import re_path

try:
    from .consumers import SupportChatConsumer
    from .watch_party_consumer import WatchPartyConsumer

    websocket_urlpatterns = [
        re_path(r'ws/support/(?P<ticket_id>\d+)/$', SupportChatConsumer.as_asgi()),
        re_path(r'ws/watch-party/(?P<room_code>[A-Z0-9]{8})/$', WatchPartyConsumer.as_asgi()),
    ]
except ImportError:
    websocket_urlpatterns = []
