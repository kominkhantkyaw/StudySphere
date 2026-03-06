from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_certificate_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursematerial',
            name='file',
            field=models.FileField(blank=True, upload_to='course_materials/'),
        ),
        migrations.AddField(
            model_name='coursematerial',
            name='material_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='certificate',
            name='file',
            field=models.FileField(blank=True, upload_to='certificates/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='certificate',
            name='certificate_url',
            field=models.URLField(blank=True, default=''),
        ),
    ]

