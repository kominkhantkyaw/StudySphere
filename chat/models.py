from django.conf import settings
from django.db import models


class Message(models.Model):
    """Course-scoped chat message (teacher + enrolled students)."""
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    content = models.TextField(blank=True, default='')
    attachment = models.FileField(
        upload_to='chat_attachments/',
        null=True,
        blank=True,
    )
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.SET_NULL,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        base = self.content or (self.attachment.name if self.attachment else '')
        return f"{self.sender.username} in {self.course.title}: {base[:30]}"


class ChannelMessage(models.Model):
    """Room-scoped chat message (e.g. Teachers' room — teacher-to-teacher)."""
    ROOM_TEACHERS = 'teachers'

    ROOM_CHOICES = [
        (ROOM_TEACHERS, 'Teachers\' room'),
    ]

    room_name = models.CharField(max_length=50, choices=ROOM_CHOICES, db_index=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_messages',
    )
    content = models.TextField(blank=True, default='')
    attachment = models.FileField(
        upload_to='chat_teachers_attachments/',
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} in {self.room_name}: {self.content[:30]}"


class MessageReaction(models.Model):
    """Emoji reaction on a chat message. One reaction per user per message (last wins)."""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions',
    )
    emoji = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['message', 'user']]
        ordering = ['-created_at']


class ChannelMessageReaction(models.Model):
    """Emoji reaction on a channel message (Teachers room). One reaction per user per message (last wins)."""
    channel_message = models.ForeignKey(
        ChannelMessage,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_message_reactions',
    )
    emoji = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['channel_message', 'user']]
        ordering = ['-created_at']


class RoomPresence(models.Model):
    """Tracks who is currently in a chat room (for 'Online now' list)."""
    ROOM_TYPE_COURSE = 'course'
    ROOM_TYPE_TEACHERS = 'teachers'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_room_presence',
    )
    room_type = models.CharField(max_length=20)  # 'course' or 'teachers'
    room_id = models.PositiveIntegerField(null=True, blank=True)  # course_id for course rooms
    channel_name = models.CharField(max_length=255, unique=True)  # Channels channel name for this connection

    class Meta:
        indexes = [
            models.Index(fields=['room_type', 'room_id']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.room_type}:{self.room_id}"
