from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync

from analytics.models import Activity
from analytics.services import log_activity
from courses.models import Course

from .models import Message, ChannelMessage, MessageReaction, ChannelMessageReaction, RoomPresence


def _online_list_for_room(room_type, room_id):
    """Return list of {username, presence, status_text} for users currently in this room."""
    qs = RoomPresence.objects.filter(room_type=room_type, room_id=room_id).select_related('user')
    return [
        {
            'username': p.user.username,
            'presence': getattr(p.user, 'presence', 'AVAILABLE'),
            'status_text': (getattr(p.user, 'status_text', None) or '')[:150],
        }
        for p in qs
    ]


class ChatConsumer(JsonWebsocketConsumer):
    """Course room: teacher + approved, non-blocked students."""

    def connect(self):
        course_id = self.scope['url_route']['kwargs']['course_id']
        self.room_group_name = f'chat_{course_id}'
        self.room_type = RoomPresence.ROOM_TYPE_COURSE
        self.room_id = course_id
        user = self.scope['user']

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name,
        )

        self.accept()

        if not user.is_anonymous:
            RoomPresence.objects.filter(channel_name=self.channel_name).delete()
            RoomPresence.objects.create(
                user=user,
                room_type=self.room_type,
                room_id=self.room_id,
                channel_name=self.channel_name,
            )
            online = _online_list_for_room(self.room_type, self.room_id)
            self.send_json({'type': 'user_list', 'users': online})
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'presence.join',
                    'username': user.username,
                    'presence': getattr(user, 'presence', 'AVAILABLE'),
                    'status_text': (getattr(user, 'status_text', None) or '')[:150],
                },
            )

        messages = Message.objects.filter(
            course_id=course_id,
        ).select_related('sender', 'reply_to').prefetch_related('reactions').order_by('-timestamp')[:50]

        history = []
        for msg in reversed(messages):
            item = {
                'id': msg.id,
                'message': msg.content,
                'username': msg.sender.username,
                'timestamp': str(msg.timestamp),
                'attachment_url': msg.attachment.url if msg.attachment else '',
                'attachment_name': msg.attachment.name if msg.attachment else '',
                'reactions': [{'emoji': r.emoji, 'username': r.user.username} for r in msg.reactions.all()],
            }
            if msg.reply_to:
                item.update({
                    'reply_to': msg.reply_to.id,
                    'reply_to_username': msg.reply_to.sender.username,
                    'reply_to_excerpt': (msg.reply_to.content or '')[:100],
                })
            history.append(item)

        self.send_json({'type': 'history', 'messages': history})

    def disconnect(self, close_code):
        user = self.scope.get('user')
        username = user.username if user and not user.is_anonymous else None
        RoomPresence.objects.filter(channel_name=self.channel_name).delete()
        if username:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {'type': 'presence.leave', 'username': username},
            )
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name,
        )

    def receive_json(self, content):
        user = self.scope['user']

        if user.is_anonymous:
            self.send_json({'type': 'error', 'message': 'Authentication required.'})
            return

        # Reactions: persist and broadcast so everyone sees them (sender and responder).
        reaction_emoji = content.get('reaction')
        reaction_msg_id = content.get('message_id')
        if reaction_emoji and reaction_msg_id:
            course_id = self.scope['url_route']['kwargs'].get('course_id')
            try:
                msg = Message.objects.get(pk=reaction_msg_id, course_id=course_id)
                MessageReaction.objects.update_or_create(
                    message=msg,
                    user=user,
                    defaults={'emoji': str(reaction_emoji)[:20]},
                )
            except Message.DoesNotExist:
                pass
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat.reaction',
                    'id': reaction_msg_id,
                    'emoji': str(reaction_emoji),
                    'username': user.username,
                },
            )
            return

        text = (content.get('message') or '').strip()
        reply_to_id = content.get('reply_to')

        if not text:
            return

        reply_obj = None
        if reply_to_id:
            try:
                reply_obj = Message.objects.get(pk=reply_to_id)
            except Message.DoesNotExist:
                reply_obj = None

        course_id = self.scope['url_route']['kwargs'].get('course_id')
        message = Message.objects.create(
            course_id=course_id,
            sender=user,
            content=text,
            reply_to=reply_obj,
        )
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                log_activity(user, Activity.MESSAGE, course=course)
            except Course.DoesNotExist:
                pass

        payload = {
            'type': 'chat.message',
            'id': message.id,
            'message': text,
            'username': user.username,
            'timestamp': str(message.timestamp),
            'attachment_url': '',
            'attachment_name': '',
        }
        if reply_obj:
            payload.update({
                'reply_to': reply_obj.id,
                'reply_to_username': reply_obj.sender.username,
                'reply_to_excerpt': (reply_obj.content or '')[:100],
            })

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            payload,
        )

    def chat_message(self, event):
        self.send_json({
            'type': 'message',
            'id': event.get('id'),
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'attachment_url': event.get('attachment_url', ''),
            'attachment_name': event.get('attachment_name', ''),
            'reply_to': event.get('reply_to'),
            'reply_to_username': event.get('reply_to_username', ''),
            'reply_to_excerpt': event.get('reply_to_excerpt', ''),
        })

    def chat_edit(self, event):
        # Broadcast an in-place edit for an existing message.
        self.send_json({
            'type': 'edit',
            'id': event.get('id'),
            'message': event.get('message', ''),
            'username': event.get('username', ''),
            'timestamp': event.get('timestamp', ''),
            'attachment_url': event.get('attachment_url', ''),
            'attachment_name': event.get('attachment_name', ''),
        })

    def chat_reaction(self, event):
        self.send_json({
            'type': 'reaction',
            'id': event.get('id'),
            'emoji': event.get('emoji'),
            'username': event.get('username'),
        })

    def status_reaction(self, event):
        """Broadcast emoji reaction on Activity Feed status to all viewers."""
        self.send_json({
            'type': 'status_reaction',
            'status_id': event.get('status_id'),
            'emoji': event.get('emoji'),
            'username': event.get('username'),
        })

    def presence_join(self, event):
        self.send_json({
            'type': 'user_joined',
            'username': event['username'],
            'presence': event.get('presence', 'AVAILABLE'),
            'status_text': (event.get('status_text') or '')[:150],
        })

    def presence_leave(self, event):
        self.send_json({
            'type': 'user_left',
            'username': event['username'],
        })

    def chat_delete(self, event):
        self.send_json({
            'type': 'delete',
            'id': event['id'],
        })


class TeachersRoomConsumer(JsonWebsocketConsumer):
    """Teachers-only room for teacher-to-teacher chat."""

    GROUP_NAME = 'chat_teachers'
    ROOM_TYPE = RoomPresence.ROOM_TYPE_TEACHERS

    def connect(self):
        user = self.scope['user']
        if user.is_anonymous or not getattr(user, 'is_teacher', lambda: False) or not user.is_teacher():
            self.close(code=4000)
            return

        self.room_group_name = self.GROUP_NAME
        self.room_type = self.ROOM_TYPE
        self.room_id = None

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name,
        )
        self.accept()

        RoomPresence.objects.filter(channel_name=self.channel_name).delete()
        RoomPresence.objects.create(
            user=user,
            room_type=self.room_type,
            room_id=None,
            channel_name=self.channel_name,
        )
        online = _online_list_for_room(self.room_type, self.room_id)
        self.send_json({'type': 'user_list', 'users': online})
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'presence.join',
                'username': user.username,
                'presence': getattr(user, 'presence', 'AVAILABLE'),
                'status_text': (getattr(user, 'status_text', None) or '')[:150],
            },
        )

        messages = ChannelMessage.objects.filter(
            room_name=ChannelMessage.ROOM_TEACHERS,
        ).select_related('sender').prefetch_related('reactions').order_by('-timestamp')[:50]

        history = [
            {
                'id': msg.id,
                'message': msg.content or '',
                'username': msg.sender.username,
                'timestamp': str(msg.timestamp),
                'attachment_url': msg.attachment.url if msg.attachment else '',
                'attachment_name': msg.attachment.name if msg.attachment else '',
                'reactions': [{'emoji': r.emoji, 'username': r.user.username} for r in msg.reactions.all()],
            }
            for msg in reversed(messages)
        ]
        self.send_json({'type': 'history', 'messages': history})

    def disconnect(self, close_code):
        user = self.scope.get('user')
        username = user.username if user and not user.is_anonymous else None
        RoomPresence.objects.filter(channel_name=self.channel_name).delete()
        if username:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {'type': 'presence.leave', 'username': username},
            )
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name,
        )

    def receive_json(self, content):
        user = self.scope['user']

        if user.is_anonymous or not getattr(user, 'is_teacher', lambda: False) or not user.is_teacher():
            self.send_json({'type': 'error', 'message': 'Only teachers can send messages here.'})
            return

        # Reactions: persist and broadcast so everyone sees them.
        reaction_emoji = content.get('reaction')
        reaction_msg_id = content.get('message_id')
        if reaction_emoji and reaction_msg_id:
            try:
                msg = ChannelMessage.objects.get(
                    pk=reaction_msg_id,
                    room_name=ChannelMessage.ROOM_TEACHERS,
                )
                ChannelMessageReaction.objects.update_or_create(
                    channel_message=msg,
                    user=user,
                    defaults={'emoji': str(reaction_emoji)[:20]},
                )
            except ChannelMessage.DoesNotExist:
                pass
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat.reaction',
                    'id': reaction_msg_id,
                    'emoji': str(reaction_emoji),
                    'username': user.username,
                },
            )
            return

        text = content.get('message', '').strip()
        if not text:
            return

        message = ChannelMessage.objects.create(
            room_name=ChannelMessage.ROOM_TEACHERS,
            sender=user,
            content=text,
        )

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat.message',
                'id': message.id,
                'message': text,
                'username': user.username,
                'timestamp': str(message.timestamp),
                'attachment_url': '',
                'attachment_name': '',
            },
        )

    def chat_message(self, event):
        self.send_json({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message', ''),
            'username': event['username'],
            'timestamp': event['timestamp'],
            'attachment_url': event.get('attachment_url', ''),
            'attachment_name': event.get('attachment_name', ''),
        })

    def chat_reaction(self, event):
        self.send_json({
            'type': 'reaction',
            'id': event.get('id'),
            'emoji': event.get('emoji'),
            'username': event.get('username'),
        })

    def presence_join(self, event):
        self.send_json({
            'type': 'user_joined',
            'username': event['username'],
            'presence': event.get('presence', 'AVAILABLE'),
            'status_text': (event.get('status_text') or '')[:150],
        })

    def presence_leave(self, event):
        self.send_json({
            'type': 'user_left',
            'username': event['username'],
        })
