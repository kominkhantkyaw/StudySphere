# Generated manually for analytics.Activity

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0011_add_language_choices'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('view', 'View (lesson/material)'), ('submit', 'Submit (assignment/quiz)'), ('message', 'Message (chat)'), ('complete', 'Complete (milestone/certificate)')], db_index=True, max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('course', models.ForeignKey(blank=True, help_text='Course context; null for app-level actions.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='engagement_activities', to='courses.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='engagement_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
                'verbose_name_plural': 'Activities',
            },
        ),
        migrations.AddIndex(
            model_name='activity',
            index=models.Index(fields=['timestamp', 'course'], name='analytics_a_timesta_0a1f0d_idx'),
        ),
        migrations.AddIndex(
            model_name='activity',
            index=models.Index(fields=['course', 'action_type', 'timestamp'], name='analytics_a_course__e0e0b4_idx'),
        ),
    ]
