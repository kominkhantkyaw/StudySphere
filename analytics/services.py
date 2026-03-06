"""
Engagement analytics: weekly time-series for teachers.
"""
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import Activity


def log_activity(user, action_type, course=None):
    """Record one engagement event. Safe to call from views/consumers."""
    if not user or not user.is_authenticated:
        return
    Activity.objects.create(
        user=user,
        course=course,
        action_type=action_type,
    )


def get_weekly_engagement(teacher_user, week_start=None):
    """
    Last 7 days (Sun–Sat style) of engagement for the teacher's courses.
    Returns list of { date, day_label, active_students, submissions } and week_start (date string).
    """
    today = timezone.now().date()
    if week_start is None:
        # Rolling 7 days ending today
        start_date = today - timezone.timedelta(days=6)
    else:
        start_date = week_start if hasattr(week_start, 'date') else week_start

    result = []
    for i in range(7):
        d = start_date + timezone.timedelta(days=i)
        day_start = timezone.make_aware(
            timezone.datetime.combine(d, timezone.datetime.min.time())
        )
        day_end = day_start + timezone.timedelta(days=1)

        # Activities in teacher's courses within this day
        qs = Activity.objects.filter(
            course__teacher=teacher_user,
            timestamp__gte=day_start,
            timestamp__lt=day_end,
        )

        active_students = qs.values('user').distinct().count()
        submissions = qs.filter(action_type=Activity.SUBMIT).count()

        result.append({
            'date': d.isoformat(),
            'day_label': d.strftime('%a'),
            'active_students': active_students,
            'submissions': submissions,
        })

    return {
        'week_start': start_date.isoformat(),
        'data': result,
    }


def get_student_activity_heatmap(user, days=35):
    """
    Activity heatmap for a student: counts of actions per day over the last ``days``.
    Includes both Activity (views, submissions, messages) and Certificate completions.
    Returns {'start_date', 'cells'} where each cell is {date, count}.
    """
    today = timezone.now().date()
    if days < 1:
        days = 1
    start_date = today - timezone.timedelta(days=days - 1)

    # Activity counts per day
    qs = (
        Activity.objects.filter(
            user=user,
            timestamp__date__gte=start_date,
        )
        .values('timestamp__date')
        .annotate(count=Count('id'))
    )
    by_date = {row['timestamp__date']: row['count'] for row in qs}

    # Add certificate completions (each cert = strong signal, weight 10 so they show clearly)
    from courses.models import Certificate
    cert_qs = (
        Certificate.objects.filter(
            enrolment__student=user,
            status=Certificate.STATUS_ISSUED,
        )
        .annotate(day=TruncDate('issued_at'))
        .filter(day__gte=start_date)
        .values('day')
        .annotate(count=Count('id'))
    )
    for row in cert_qs:
        d = row['day']
        if d and d >= start_date:
            by_date[d] = by_date.get(d, 0) + row['count'] * 10

    cells = []
    for i in range(days):
        d = start_date + timezone.timedelta(days=i)
        cells.append(
            {
                'date': d.isoformat(),
                'count': by_date.get(d, 0),
                'day_label': d.strftime('%a'),
            }
        )

    return {
        'start_date': start_date.isoformat(),
        'cells': cells,
    }


def get_student_streak(user):
    """
    Compute study streak for a student: consecutive days with at least one activity.
    Returns dict: current_streak (days), longest_streak (days), studied_today (bool).
    """
    if not user or not user.is_authenticated:
        return {'current_streak': 0, 'longest_streak': 0, 'studied_today': False}

    today = timezone.now().date()
    # All distinct dates the user had activity (any action)
    activity_dates = set(
        Activity.objects.filter(user=user)
        .values_list('timestamp__date', flat=True)
        .distinct()
    )
    if not activity_dates:
        return {'current_streak': 0, 'longest_streak': 0, 'studied_today': False}

    # Current streak: count consecutive days backwards from today (or yesterday if no activity today)
    current = 0
    d = today
    while d in activity_dates:
        current += 1
        d = d - timezone.timedelta(days=1)
    # If no activity today, streak is from yesterday backwards (don't count today)
    if current == 0 and today not in activity_dates:
        d = today - timezone.timedelta(days=1)
        while d in activity_dates:
            current += 1
            d = d - timezone.timedelta(days=1)

    # Longest streak: scan sorted dates and find max consecutive run
    sorted_dates = sorted(activity_dates)
    longest = 1
    run = 1
    for i in range(1, len(sorted_dates)):
        prev, curr = sorted_dates[i - 1], sorted_dates[i]
        if (curr - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {
        'current_streak': current,
        'longest_streak': longest,
        'studied_today': today in activity_dates,
    }
