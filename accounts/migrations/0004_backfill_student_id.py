# Backfill student_id for existing students (STU + zero-padded pk)

from django.db import migrations


def backfill_student_id(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(role='STUDENT', student_id__isnull=True):
        user.student_id = f'STU{str(user.pk).zfill(5)}'
        user.save(update_fields=['student_id'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_student_id'),
    ]

    operations = [
        migrations.RunPython(backfill_student_id, noop),
    ]
