from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0010_coursematerial_author'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='language',
            field=models.CharField(
                choices=[
                    ('EN', 'English'),
                    ('DE', 'German'),
                    ('AR', 'Arabic'),
                    ('ZH', 'Chinese'),
                    ('FR', 'French'),
                    ('RU', 'Russian'),
                    ('ES', 'Spanish'),
                    ('OTHER', 'Other'),
                ],
                default='EN',
                help_text='Main language used in this course.',
                max_length=10,
            ),
        ),
    ]
