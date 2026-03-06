from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_material_publish_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursematerial',
            name='author',
            field=models.ForeignKey(
                blank=True,
                help_text='Teacher who uploaded this material.',
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='materials_authored',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

