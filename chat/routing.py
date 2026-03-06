from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    path('ws/chat/teachers/', consumers.TeachersRoomConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<course_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
