"""
ASGI config for ydcleaning project.

It exposes the ASGI callable as a module-level variable named
``application``.
"""

import os
from urllib.parse import urlsplit

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "ydcleaning.settings",
)

from django.core.asgi import get_asgi_application


# Initialise Django first.
django_asgi_app = get_asgi_application()


from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from channels.routing import ProtocolTypeRouter, URLRouter

from support.routing import websocket_urlpatterns


class ProductionSecureOrigin:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if settings.IS_PRODUCTION:
            origin = dict(scope.get("headers", [])).get(b"origin", b"").decode(
                "latin1"
            )
            if not origin or urlsplit(origin).scheme.lower() != "https":
                await send({"type": "websocket.close", "code": 4403})
                return
        await self.application(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,

        "websocket": ProductionSecureOrigin(
            AllowedHostsOriginValidator(
                AuthMiddlewareStack(
                    URLRouter(
                        websocket_urlpatterns
                    )
                )
            )
        ),
    }
)