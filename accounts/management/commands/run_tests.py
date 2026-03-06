"""
Run the test suite with verbosity 2 so each test is shown with OK when it passes.
Usage: python manage.py run_tests [--keepdb] [app_name ...]
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run tests with verbosity 2 (shows each test name and OK when it passes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keepdb',
            action='store_true',
            help='Preserve the test database between runs',
        )
        parser.add_argument(
            '--color',
            action='store_true',
            dest='force_green',
            help='Always show "ok" in green (for graders; set STUDYSPHERE_FORCE_COLOR=1 as alternative)',
        )
        parser.add_argument(
            'args',
            nargs='*',
            help='Optional app labels to test (e.g. accounts, courses)',
        )

    def handle(self, *args, **options):
        keepdb = options.get('keepdb', False)
        force_green = options.get('force_green', False)
        if force_green:
            import os
            os.environ['STUDYSPHERE_FORCE_COLOR'] = '1'
        test_labels = options.get('args', []) or list(args)
        call_command(
            'test',
            *test_labels,
            verbosity=2,
            keepdb=keepdb,
            testrunner='studysphere.test_runner.ColoredDiscoverRunner',
        )
