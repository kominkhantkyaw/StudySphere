from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def set_student_id_for_students(sender, instance, created, **kwargs):
    """Ensure every student has a student_id (for reporting, enrolment counts)."""
    if instance.role == 'STUDENT' and not instance.student_id:
        instance.get_or_set_student_id()
