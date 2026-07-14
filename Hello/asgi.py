"""
ASGI config for Hello project.
Upgraded to support Django Channels (WebSockets) for the live support chat.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hello.settings')

django_asgi_app = get_asgi_application()

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
except ImportError:
    # Channels itself isn't installed - fall back to plain HTTP.
    application = django_asgi_app
else:
    # Let any other import error (e.g. a broken consumer import) fail loudly
    # instead of silently disabling WebSockets in production.
    from ananimeclip import channel_routing

    application = ProtocolTypeRouter(
        {
            'http': django_asgi_app,
            'websocket': AuthMiddlewareStack(URLRouter(channel_routing.websocket_urlpatterns)),
        }
    )
