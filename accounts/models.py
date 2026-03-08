from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    ROLE_CHOICES = (
        ('STUDENT', _('Student')),
        ('TEACHER', _('Teacher')),
    )

    AVAILABLE = 'AVAILABLE'
    ONLINE = 'ONLINE'
    BUSY = 'BUSY'
    AWAY = 'AWAY'
    OFFLINE = 'OFFLINE'
    PRESENCE_CHOICES = (
        (AVAILABLE, _('Available')),
        (ONLINE, _('Online')),
        (BUSY, _('Busy')),
        (AWAY, _('Away')),
        (OFFLINE, _('Offline')),
    )

    CLEAR_NEVER = 'NEVER'
    CLEAR_1H = '1H'
    CLEAR_5H = '5H'
    CLEAR_TODAY = 'TODAY'
    CLEAR_WEEK = 'WEEK'
    STATUS_CLEAR_CHOICES = (
        (CLEAR_NEVER, _('Never')),
        (CLEAR_1H, _('1 hour')),
        (CLEAR_5H, _('5 hours')),
        (CLEAR_TODAY, _('Today')),
        (CLEAR_WEEK, _('This week')),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    presence = models.CharField(
        max_length=10,
        choices=PRESENCE_CHOICES,
        default=AVAILABLE,
        help_text='User-set availability (Available / Online / Busy / Away / Offline).',
    )
    status_text = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Short status message (e.g. Studying now, Taking a break, Listening to Music).',
    )
    status_clear_after = models.CharField(
        max_length=10,
        choices=STATUS_CLEAR_CHOICES,
        default=CLEAR_NEVER,
        help_text='When to clear the custom status message.',
    )
    status_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Automatically derived from clear-after choice; when reached, the status message is cleared.',
    )
    student_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='Unique ID for students (e.g. STU00001). Used for reporting and to track enrolments per course.',
    )
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    bio = models.TextField(blank=True, default='')
    address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Optional address or city/country information.',
    )

    THEME_LIGHT = 'LIGHT'
    THEME_DARK = 'DARK'
    THEME_SYSTEM = 'SYSTEM'
    THEME_CHOICES = (
        (THEME_LIGHT, _('Light')),
        (THEME_DARK, _('Dark')),
        (THEME_SYSTEM, _('System')),
    )

    LANGUAGE_EN = 'EN'
    LANGUAGE_DE = 'DE'
    LANGUAGE_OTHER = 'OTHER'
    LANGUAGE_CHOICES = (
        (LANGUAGE_EN, _('English')),
        (LANGUAGE_DE, _('German')),
        (LANGUAGE_OTHER, _('Other')),
    )

    theme_mode = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default=THEME_SYSTEM,
        help_text='Preferred app theme mode.',
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_EN,
        help_text='Preferred language for the interface.',
    )

    # Notification and privacy preferences
    notify_email = models.BooleanField(
        default=True,
        help_text='Receive important updates by email.',
    )
    notify_in_app = models.BooleanField(
        default=True,
        help_text='Show in-app notifications for updates.',
    )
    subscribe_course_updates = models.BooleanField(
        default=True,
        help_text='Receive course updates and up-to-date info by email (e.g. new materials, announcements).',
    )
    share_activity = models.BooleanField(
        default=True,
        help_text='Allow your activity (e.g. course completions) to appear in feeds and dashboards.',
    )

    def is_teacher(self):
        return self.role == 'TEACHER'

    def is_student(self):
        return self.role == 'STUDENT'

    def get_or_set_student_id(self):
        """Ensure student has a student_id (for reporting, enrolment counts). Call after save when role is STUDENT."""
        if self.role != 'STUDENT':
            return self.student_id
        if self.student_id:
            return self.student_id
        self.student_id = f'STU{str(self.pk).zfill(5)}'
        self.save(update_fields=['student_id'])
        return self.student_id

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
