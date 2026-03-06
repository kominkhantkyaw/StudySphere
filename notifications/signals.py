from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Notification


@receiver(post_save, sender='courses.Enrolment')
def notify_teacher_on_enrolment(sender, instance, created, **kwargs):
    if created:
        link_url = reverse('courses:course_detail', args=[instance.course_id])
        Notification.objects.create(
            recipient=instance.course.teacher,
            message=(
                f"{instance.student.username} requested to enrol in "
                f"{instance.course.title}"
            ),
            link_url=link_url,
        )


@receiver(post_save, sender='courses.CourseMaterial')
def notify_students_on_material(sender, instance, created, **kwargs):
    if created:
        from courses.models import Enrolment

        link_url = reverse('courses:course_detail', args=[instance.course_id])
        enrolments = Enrolment.objects.filter(
            course=instance.course,
            status=Enrolment.APPROVED,
            blocked=False,
        ).select_related('student')

        notifications = [
            Notification(
                recipient=enrolment.student,
                message=(
                    f"New material '{instance.title}' added to "
                    f"{instance.course.title}"
                ),
                link_url=link_url,
            )
            for enrolment in enrolments
        ]
        Notification.objects.bulk_create(notifications)
