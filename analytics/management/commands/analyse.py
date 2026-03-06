"""
Run engagement analytics summary. For testing: python manage.py analyse
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count

from analytics.models import Activity


class Command(BaseCommand):
    help = 'Print engagement analytics summary (activity counts, recent activity)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to include in summary (default: 7)',
        )

    def handle(self, *args, **options):
        days = max(1, options['days'])
        self.stdout.write('Engagement analytics summary')
        self.stdout.write('-' * 40)

        # Total activity counts by type
        by_type = (
            Activity.objects.values('action_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        if by_type:
            self.stdout.write('Total activities by type:')
            for row in by_type:
                self.stdout.write(f"  {row['action_type']}: {row['count']}")
        else:
            self.stdout.write('No activity recorded yet.')

        # Recent period summary
        since = timezone.now() - timezone.timedelta(days=days)
        recent = Activity.objects.filter(timestamp__gte=since)
        total_recent = recent.count()
        distinct_users = recent.values('user').distinct().count()

        self.stdout.write('')
        self.stdout.write(f'Last {days} days:')
        self.stdout.write(f'  Total events: {total_recent}')
        self.stdout.write(f'  Distinct users: {distinct_users}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Analysis complete.'))
