from django.conf import settings
from django.db import models

from courses.models import Course


class Activity(models.Model):
    """
    One row per engagement action. Used for weekly engagement analytics:
    - Daily Active Students: distinct users per day (any action)
    - Daily Submissions: count of action_type=submit per day
    """
    VIEW = 'view'
    SUBMIT = 'submit'
    MESSAGE = 'message'
    COMPLETE = 'complete'
    ACTION_CHOICES = [
        (VIEW, 'View (lesson/material)'),
        (SUBMIT, 'Submit (assignment/quiz)'),
        (MESSAGE, 'Message (chat)'),
        (COMPLETE, 'Complete (milestone/certificate)'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='engagement_activities',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='engagement_activities',
        help_text='Course context; null for app-level actions.',
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Activities'
        indexes = [
            models.Index(fields=['timestamp', 'course']),
            models.Index(fields=['course', 'action_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user_id} {self.action_type} @ {self.timestamp}"
