# Migration to fix accounts_user table missing 'id' column
# (e.g. when table was created outside Django or schema is out of sync)

from django.db import migrations


def add_id_column_if_missing(apps, schema_editor):
    """Add id BIGSERIAL PRIMARY KEY to accounts_user if the column does not exist."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'accounts_user'
              AND column_name = 'id'
        """)
        if cursor.fetchone() is not None:
            return  # id already exists, nothing to do

        # Table exists but has no id column - add it
        # First check if there is an existing primary key we need to drop
        cursor.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = 'accounts_user'
              AND constraint_type = 'PRIMARY KEY'
        """)
        pk_row = cursor.fetchone()
        if pk_row is not None:
            constraint_name = pk_row[0]
            cursor.execute(
                'ALTER TABLE accounts_user DROP CONSTRAINT "{}"'.format(constraint_name)
            )

        # Add id as bigserial (auto-incrementing bigint) and set as primary key
        cursor.execute("""
            ALTER TABLE accounts_user
            ADD COLUMN id BIGSERIAL PRIMARY KEY
        """)


def noop_reverse(apps, schema_editor):
    """Cannot safely remove id column (Django expects it)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_id_column_if_missing, noop_reverse),
    ]
