"""
ASGI config for Hello project.
Upgraded to support Django Channels (WebSockets) for the live support chat.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hello.settings")

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from ananimeclip import channel_routing

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(channel_routing.websocket_urlpatterns)
        ),
    })
except ImportError:
    # channels not installed yet — fall back to pure WSGI-style ASGI
    application = django_asgi_app
