# Data migration: ensure General announcement room exists

from django.db import migrations


def create_general_room(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    User = apps.get_model('accounts', 'User')
    teacher = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not teacher:
        return
    Course.objects.get_or_create(
        is_general=True,
        defaults={
            'title': 'General',
            'description': 'Announcements for everyone. Teachers and students can post and read here.',
            'teacher_id': teacher.id,
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_add_course_is_general'),
        ('accounts', '__first__'),
    ]

    operations = [
        migrations.RunPython(create_general_room, noop),
    ]
