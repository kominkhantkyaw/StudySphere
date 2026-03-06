# Generated manually to backfill link_url for existing notifications

from django.db import migrations
from django.urls import reverse


def backfill_link_url(apps, schema_editor):
    Notification = apps.get_model('notifications', 'Notification')
    Course = apps.get_model('courses', 'Course')

    for notification in Notification.objects.filter(link_url=''):
        msg = (notification.message or '').strip()
        course_title = None
        if ' requested to enrol in ' in msg:
            course_title = msg.split(' requested to enrol in ', 1)[-1].strip()
        elif ' added to ' in msg:
            course_title = msg.split(' added to ', 1)[-1].strip()

        if course_title:
            course = Course.objects.filter(title=course_title).first()
            if course:
                notification.link_url = reverse('courses:course_detail', args=[course.id])
                notification.save(update_fields=['link_url'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_add_notification_link_url'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_link_url, noop),
    ]
