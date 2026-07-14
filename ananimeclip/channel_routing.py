"""
Django Channels routing for support chat and watch-party WebSocket endpoints.
"""

from django.urls import re_path

try:
    import channels  # noqa: F401
except ImportError:
    # Channels itself isn't installed - disable websocket routes.
    websocket_urlpatterns = []
else:
    # Let broken consumer imports fail loudly instead of silently
    # disabling every websocket endpoint.
    from .consumers import SupportChatConsumer
    from .watch_party_consumer import WatchPartyConsumer

    websocket_urlpatterns = [
        re_path(r'ws/support/(?P<ticket_id>\d+)/$', SupportChatConsumer.as_asgi()),
        re_path(r'ws/watch-party/(?P<room_code>[A-Z0-9]{8})/$', WatchPartyConsumer.as_asgi()),
    ]
