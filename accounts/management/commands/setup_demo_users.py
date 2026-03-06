from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users (admin, student, teacher) for testing'

    def handle(self, *args, **options):
        demos = [
            {
                'username': 'admin',
                'email': 'admin@studysphere.app',
                'password': 'Admin123!',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'TEACHER',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'teacher',
                'email': 'teacher@studysphere.app',
                'password': 'Teacher123!',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'TEACHER',
                'bio': 'Experienced educator with a passion for technology.',
            },
            {
                'username': 'teacher2',
                'email': 'teacher2@studysphere.app',
                'password': 'Teacher123!',
                'first_name': 'Robert',
                'last_name': 'Brown',
                'role': 'TEACHER',
                'bio': 'Mathematics lecturer specialising in applied sciences.',
            },
            {
                'username': 'student',
                'email': 'student@studysphere.app',
                'password': 'Student123!',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'STUDENT',
                'bio': 'Eager learner interested in computer science.',
            },
            {
                'username': 'student2',
                'email': 'student2@studysphere.app',
                'password': 'Student123!',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'role': 'STUDENT',
                'bio': 'Second-year student studying data science.',
            },
        ]

        for data in demos:
            username = data.pop('username')
            password = data.pop('password')
            is_staff = data.pop('is_staff', False)
            is_superuser = data.pop('is_superuser', False)

            user, created = User.objects.get_or_create(
                username=username,
                defaults=data,
            )

            if created:
                user.set_password(password)
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created {user.role} user: {username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists: {username}')
                )

        self.stdout.write(self.style.SUCCESS('\nDemo users ready!'))
        self.stdout.write('  admin    / Admin123!')
        self.stdout.write('  teacher  / Teacher123!')
        self.stdout.write('  teacher2 / Teacher123!')
        self.stdout.write('  student  / Student123!')
        self.stdout.write('  student2 / Student123!')
