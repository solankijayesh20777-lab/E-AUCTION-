import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import auctions.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_auction.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            auctions.routing.websocket_urlpatterns
        )
    ),
})
