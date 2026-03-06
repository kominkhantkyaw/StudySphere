import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'studysphere.settings')

django_asgi_app = get_asgi_application()

import chat.routing  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        AllowedHostsOriginValidator(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})
