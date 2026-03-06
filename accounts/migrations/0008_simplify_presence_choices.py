# Generated migration: simplify presence to Available, Online, Busy, Away, Offline

from django.db import migrations, models


def migrate_dnd_brb_to_available(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(presence__in=('DND', 'BRB')).update(presence='AVAILABLE')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_presence_expiry'),
    ]

    operations = [
        migrations.RunPython(migrate_dnd_brb_to_available, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='presence',
            field=models.CharField(
                choices=[
                    ('AVAILABLE', 'Available'),
                    ('ONLINE', 'Online'),
                    ('BUSY', 'Busy'),
                    ('AWAY', 'Away'),
                    ('OFFLINE', 'Offline'),
                ],
                default='AVAILABLE',
                help_text='User-set availability.',
                max_length=10,
            ),
        ),
    ]
