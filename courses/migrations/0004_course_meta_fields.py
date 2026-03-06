from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Latest existing courses migration before adding meta fields
        ('courses', '0003_certificate'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='hero_image',
            field=models.ImageField(blank=True, null=True, upload_to='course_images/'),
        ),
        migrations.AddField(
            model_name='course',
            name='start_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='end_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='duration_minutes',
            field=models.PositiveIntegerField(blank=True, help_text='Total duration in minutes (e.g. 45, 90, 120).', null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Course fee (leave empty if free).', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='location',
            field=models.CharField(blank=True, help_text='Physical or virtual location (e.g. Zoom link, classroom).', max_length=255),
        ),
        migrations.AddField(
            model_name='course',
            name='organiser',
            field=models.CharField(blank=True, help_text='Organisation or person responsible for this course.', max_length=255),
        ),
        migrations.AddField(
            model_name='course',
            name='capacity_type',
            field=models.CharField(choices=[('LIMITED', 'Limited'), ('UNLIMITED', 'Unlimited')], default='UNLIMITED', help_text='Whether places are limited or unlimited.', max_length=10),
        ),
        migrations.AddField(
            model_name='course',
            name='delivery_mode',
            field=models.CharField(choices=[('ONLINE', 'Online'), ('ONSITE', 'On-site')], default='ONLINE', help_text='How the course is delivered.', max_length=10),
        ),
        migrations.AddField(
            model_name='course',
            name='language',
            field=models.CharField(choices=[('EN', 'English'), ('DE', 'German'), ('OTHER', 'Other')], default='EN', help_text='Main language used in this course.', max_length=10),
        ),
    ]

