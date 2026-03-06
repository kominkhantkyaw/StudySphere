# Generated migration for enrolment approval workflow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrolment',
            name='status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                default='APPROVED',  # existing enrolments stay approved
                max_length=10,
            ),
        ),
    ]
