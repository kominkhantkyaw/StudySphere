from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_course_hero_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificate',
            name='status',
            field=models.CharField(
                choices=[
                    ('ISSUED', 'Issued'),
                    ('REVOKED', 'Revoked'),
                    ('EXPIRED', 'Expired'),
                ],
                default='ISSUED',
                help_text='Lifecycle status of this certificate.',
                max_length=10,
            ),
        ),
    ]

