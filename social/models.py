from django.conf import settings
from django.db import models


class StatusUpdate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='status_updates',
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to='status_attachments/%Y/%m/',
        null=True,
        blank=True,
        help_text='Optional file or image attached to this update.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"


class StatusReaction(models.Model):
    """Emoji reaction on a status update. One reaction per user per status (last wins)."""
    status = models.ForeignKey(
        StatusUpdate,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='status_reactions',
    )
    emoji = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['status', 'user']]
        ordering = ['-created_at']
