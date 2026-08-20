"""
ASGI config for ydcleaning project.

It exposes the ASGI callable as a module-level variable named
``application``.
"""

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "ydcleaning.settings",
)

from django.core.asgi import get_asgi_application


# Initialise Django first.
django_asgi_app = get_asgi_application()


from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from support.routing import websocket_urlpatterns


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,

        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    }
)