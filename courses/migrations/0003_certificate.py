# Generated migration for Certificate model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0002_enrolment_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Certificate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='certificates/%Y/%m/')),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('enrolment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='certificate', to='courses.enrolment')),
                ('issued_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_certificates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-issued_at'],
            },
        ),
    ]
