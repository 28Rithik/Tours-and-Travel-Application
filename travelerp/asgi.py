"""
ASGI config for travelerp project.

It exposes the ASGI callable as a module-level variable named ``application``.
Supports HTTP and high-performance WebSocket streaming via Django Channels.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import operations.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            operations.routing.websocket_urlpatterns
        )
    ),
})
