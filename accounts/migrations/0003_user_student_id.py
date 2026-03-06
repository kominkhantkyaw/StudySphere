# Add student_id for students (reporting, enrolment counts per course)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_user_id_column'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='student_id',
            field=models.CharField(
                blank=True,
                help_text='Unique ID for students (e.g. STU00001). Used for reporting and to track enrolments per course.',
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
    ]
