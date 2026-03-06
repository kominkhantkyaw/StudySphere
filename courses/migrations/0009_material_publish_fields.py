from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_material_and_certificate_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursematerial',
            name='published',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='coursematerial',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

