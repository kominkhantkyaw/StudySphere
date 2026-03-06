from django.conf import settings
from django.db import models


class Event(models.Model):
    COURSE_SESSION = 'SESSION'
    APPOINTMENT = 'APPOINTMENT'
    OFFICE_HOURS = 'OFFICE_HOURS'
    DEADLINE = 'DEADLINE'

    EVENT_TYPE_CHOICES = [
        (COURSE_SESSION, 'Course Session'),
        (APPOINTMENT, 'Appointment'),
        (OFFICE_HOURS, 'Office Hours'),
        (DEADLINE, 'Deadline'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_events',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='events',
        blank=True,
        null=True,
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default=APPOINTMENT,
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='attending_events',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return f'{self.title} ({self.get_event_type_display()})'
