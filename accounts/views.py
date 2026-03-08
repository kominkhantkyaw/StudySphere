import base64
import io

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordResetView as AuthPasswordResetView
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import UserProfileForm, UserRegistrationForm
from .models import User


class PasswordResetView(AuthPasswordResetView):
    """Password reset with optional SITE_DOMAIN for correct links in production."""
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = '/accounts/password-reset/done/'
    form_class = PasswordResetForm

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        if getattr(settings, 'SITE_DOMAIN', None):
            opts['domain_override'] = settings.SITE_DOMAIN
            opts['use_https'] = (settings.SITE_PROTOCOL == 'https')
        form.save(**opts)
        return super().form_valid(form)


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:profile', username=user.username)
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # If user has 2FA (TOTP) enabled, require OTP before logging in
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                request.session['otp_user_id'] = user.pk
                request.session['otp_next'] = request.GET.get('next', '/')
                return redirect('accounts:two_factor_verify')
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            return render(request, 'accounts/login.html', {
                'error': 'Invalid username or password.',
            })
    return render(request, 'accounts/login.html')


@login_required
def user_logout(request):
    logout(request)
    return redirect('/')


def profile(request, username):
    from courses.models import Enrolment, Certificate
    from social.models import StatusUpdate

    user_obj = get_object_or_404(User, username=username)
    is_own_profile = request.user.is_authenticated and request.user == user_obj

    # In-page profile photo update (own profile only)
    if request.method == 'POST' and is_own_profile and request.POST.get('form_type') == 'profile_photo':
        remove_photo = request.POST.get('remove_photo') == 'on'
        if remove_photo:
            if user_obj.photo:
                user_obj.photo.delete(save=False)
            user_obj.photo = None
            user_obj.save(update_fields=['photo'])
            messages.success(request, 'Profile picture removed.')
        else:
            new_photo = request.FILES.get('photo')
            if new_photo:
                if user_obj.photo:
                    user_obj.photo.delete(save=False)
                user_obj.photo = new_photo
                user_obj.save(update_fields=['photo'])
                messages.success(request, 'Profile picture updated successfully.')
            else:
                messages.info(request, 'Choose a new image to update your profile picture.')
        return redirect('accounts:profile', username=username)

    status_updates = StatusUpdate.objects.filter(user=user_obj)[:20]

    enrolled_courses = []
    taught_courses = []
    achievements = {}
    learning_stats = {}
    study_streak = None
    if user_obj.is_student():
        from analytics.services import get_student_streak
        study_streak = get_student_streak(user_obj)
        enrolled_courses = Enrolment.objects.filter(
            student=user_obj, status=Enrolment.APPROVED, blocked=False,
        ).select_related('course', 'course__teacher')
        cert_count = Certificate.objects.filter(
            enrolment__student=user_obj,
            status=Certificate.STATUS_ISSUED,
        ).count()
        achievements = {
            'courses_enrolled': enrolled_courses.count(),
            'certificates_earned': cert_count,
        }
        total = enrolled_courses.count() or 1
        pct_completed = int(min(100, (cert_count / total) * 100))
        pct_certificates = pct_completed
        learning_stats = {
            'courses_total': enrolled_courses.count(),
            'courses_completed': cert_count,  # proxy
            'certificates': cert_count,
            'pct_completed': pct_completed,
            'pct_certificates': pct_certificates,
        }
    elif user_obj.is_teacher():
        taught_courses = user_obj.taught_courses.all()
        cert_issued = Certificate.objects.filter(
            enrolment__course__teacher=user_obj,
            status=Certificate.STATUS_ISSUED,
        ).count()
        achievements = {
            'courses_created': taught_courses.count(),
            'certificates_issued': cert_issued,
        }
        total = taught_courses.count() or 1
        pct_completed = int(min(100, (cert_issued / total) * 100))
        pct_certificates = pct_completed
        learning_stats = {
            'courses_total': taught_courses.count(),
            'courses_completed': cert_issued,  # proxy: courses with at least one certificate
            'certificates': cert_issued,
            'pct_completed': pct_completed,
            'pct_certificates': pct_certificates,
        }

    context = {
        'profile_user': user_obj,
        'is_own_profile': is_own_profile,
        'status_updates': status_updates,
        'enrolled_courses': enrolled_courses,
        'taught_courses': taught_courses,
        'achievements': achievements,
        'learning_stats': learning_stats,
        'study_streak': study_streak,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and next_url.strip().endswith('/settings/'):
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:settings')
            return redirect('accounts:profile', username=request.user.username)
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def settings_view(request):
    """
    Settings page with three conceptual areas:
    - General: interface preferences (language, theme)
    - Account: profile details (name, email, address, presence, bio, photo)
    - Security: password
    """
    from django.contrib.messages import get_messages
    from .forms import GeneralSettingsForm

    general_form = GeneralSettingsForm(instance=request.user)
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)
    active_tab = request.GET.get('tab', 'general')

    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        if form_type == 'language':
            # CRUD update: only preferred_language (Language tab submits only this field)
            lang = (request.POST.get('preferred_language') or '').strip().upper()
            if lang in ('EN', 'DE', 'OTHER'):
                request.user.preferred_language = lang
                request.user.save(update_fields=['preferred_language'])
                from django.utils import translation
                translation.activate('de' if lang == 'DE' else 'en')
                messages.success(request, _('Language saved. The interface will use your selected language.'))
                return redirect(reverse('accounts:settings') + '?tab=language')
            active_tab = 'language'
        elif form_type == 'general':
            general_form = GeneralSettingsForm(request.POST, instance=request.user)
            if general_form.is_valid():
                general_form.save()
                next_tab = request.POST.get('active_tab') or 'general'
                msg = 'Your preferences have been saved.' if next_tab == 'preferences' else 'Settings updated.'
                messages.success(request, msg)
                return redirect(f'{reverse("accounts:settings")}?tab={next_tab}')
            active_tab = request.POST.get('active_tab') or 'general'
        elif form_type == 'profile':
            profile_form = UserProfileForm(
                request.POST, request.FILES, instance=request.user,
            )
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect(f'{reverse("accounts:settings")}?tab=profile')
            active_tab = 'profile'
        elif form_type == 'password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Your password was updated successfully.')
                return redirect(f'{reverse("accounts:settings")}?tab=security')
            active_tab = 'security'

    two_fa_enabled = bool(_user_has_2fa(request.user))
    # Pass messages as a list to avoid any template code calling .count() on the storage (which can surface as int in some setups)
    message_list = list(get_messages(request))

    return render(request, 'accounts/settings.html', {
        'general_form': general_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'active_tab': active_tab,
        'two_fa_enabled': two_fa_enabled,
        'message_list': message_list,
    })


@login_required
@require_POST
def set_language(request):
    """
    Quick language switch (CRUD update). POST preferred_language=EN|DE|OTHER.
    Redirects to next, referer, or home. User-friendly: used by navbar language dropdown.
    """
    from django.utils import translation
    lang = (request.POST.get('preferred_language') or '').strip().upper()
    if lang not in ('EN', 'DE', 'OTHER'):
        messages.warning(request, _('Invalid language choice.'))
    else:
        request.user.preferred_language = lang
        request.user.save(update_fields=['preferred_language'])
        translation.activate('de' if lang == 'DE' else 'en')
        messages.success(request, _('Language updated.'))
    redirect_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(redirect_url)


@login_required
def contact_view(request):
    """
    Contact + Profile & Settings summary page for the Teacher Portal layout.
    Shows a compact profile card and shortcuts to key settings/actions.
    When ?tab=privacy, the template can show the Privacy Policy prominently.
    """
    active_tab = request.GET.get('tab', '')
    return render(request, 'accounts/contact.html', {'active_tab': active_tab})


def home(request):
    context = {}
    if request.user.is_authenticated:
        from django.db.models import Count
        from django.utils import timezone
        from notifications.models import Notification

        hour = timezone.now().hour
        context['greeting'] = 'morning' if hour < 12 else 'afternoon' if hour < 18 else 'evening'
        from social.forms import StatusUpdateForm
        from social.models import StatusUpdate

        from courses.models import Enrolment, Feedback, Certificate

        context['unread_count'] = Notification.objects.filter(
            recipient=request.user, read=False,
        ).count()
        context['status_form'] = StatusUpdateForm()
        context['recent_updates'] = StatusUpdate.objects.select_related(
            'user'
        ).all()[:10]

        if request.user.is_student():
            # Student dashboard data
            from analytics.services import get_student_activity_heatmap, get_student_streak

            # Streak for gamification (study streak + certs)
            context['study_streak'] = get_student_streak(request.user)

            enrol_qs = request.user.enrolments.select_related(
                'course', 'course__teacher'
            ).filter(status='APPROVED', blocked=False)
            context['enrolled_courses'] = enrol_qs[:5]
            context['enrolled_count'] = enrol_qs.count()

            now = timezone.now()
            # Active courses = courses not yet finished (or with no end date)
            active_qs = enrol_qs.filter(
                Q(course__end_datetime__isnull=True) | Q(course__end_datetime__gt=now)
            )
            context['student_active_courses'] = active_qs.count()

            # Certificates earned / completed courses
            cert_qs = Certificate.objects.filter(enrolment__student=request.user)
            context['certificates_earned'] = cert_qs.count()
            context['completed_courses_count'] = cert_qs.values(
                'enrolment__course'
            ).distinct().count()

            # Stat percentages for progress bars (enrolled_count as denominator where relevant)
            enrolled = context['enrolled_count'] or 1
            context['stat_active_pct'] = min(100, int(context['student_active_courses'] / enrolled * 100))
            context['stat_completed_pct'] = min(100, int(context['completed_courses_count'] / enrolled * 100))
            context['stat_certs_pct'] = min(100, int(context['certificates_earned'] / enrolled * 100))
            context['stat_unread_pct'] = min(100, int((context.get('unread_count') or 0) / 20 * 100))

            # Progress overview per enrolment
            cert_enrol_ids = set(
                cert_qs.values_list('enrolment_id', flat=True)
            )
            progress_items = []
            for enr in enrol_qs.select_related('course'):
                course = enr.course
                percent = 0
                if enr.id in cert_enrol_ids:
                    percent = 100
                else:
                    start = getattr(course, 'start_datetime', None)
                    end = getattr(course, 'end_datetime', None)
                    if start and end and start < end:
                        total_days = (end - start).days or 1
                        elapsed = max(0, min((now - start).days, total_days))
                        percent = int((elapsed / total_days) * 100)
                        if percent > 95:
                            percent = 95
                progress_items.append(
                    {'enrolment': enr, 'course': course, 'percent': percent}
                )
            context['progress_overview'] = progress_items

            # Upcoming deadlines: upcoming course end dates
            upcoming = enrol_qs.filter(
                course__end_datetime__gt=now
            ).select_related('course').order_by('course__end_datetime')[:5]
            context['upcoming_deadlines'] = upcoming

            # Latest notifications for the student
            context['student_notifications'] = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:5]

            # Latest achievement (most recent certificate)
            latest_cert = (
                cert_qs.select_related('enrolment__course')
                .order_by('-issued_at')
                .first()
            )
            context['latest_certificate'] = latest_cert

            # Activity heatmap (GitHub-style, full year, monthly view)
            heatmap = get_student_activity_heatmap(request.user, days=365)
            cells = heatmap['cells']
            max_count = max((c['count'] for c in cells), default=0) or 1
            total_activity_days = sum(1 for c in cells if c['count'] > 0)
            total_contributions = sum(c['count'] for c in cells)
            from datetime import datetime as dt
            for c in cells:
                val = c['count']
                if val == 0:
                    level = 0
                elif val <= max_count * 0.25:
                    level = 1
                elif val <= max_count * 0.5:
                    level = 2
                elif val <= max_count * 0.75:
                    level = 3
                else:
                    level = 4
                c['level'] = level
                c['date_display'] = dt.strptime(c['date'], '%Y-%m-%d').strftime('%d %b %Y')
            # Group into weeks of 7 days for display (rows = days of week, cols = weeks)
            weeks = []
            week = []
            for idx, cell in enumerate(cells):
                week.append(cell)
                if (idx + 1) % 7 == 0:
                    weeks.append(week)
                    week = []
            if week:
                weeks.append(week)
            context['activity_heatmap_weeks'] = weeks
            context['activity_heatmap_total'] = total_contributions
            context['activity_heatmap_active_days'] = total_activity_days
            # Month labels for GitHub-style header: (name, col) for each new month
            prev_ym = None
            num_weeks = len(weeks)
            month_labels = []
            for idx, cell in enumerate(cells):
                d = dt.strptime(cell['date'], '%Y-%m-%d')
                ym = (d.year, d.month)
                col = idx // 7
                if ym != prev_ym and col < num_weeks:
                    month_labels.append({'name': d.strftime('%b'), 'col': col})
                prev_ym = ym
            context['activity_heatmap_months'] = month_labels
            context['activity_heatmap_num_weeks'] = num_weeks
            # Visible date range for grader verification (not hard-coded)
            context['activity_heatmap_start_date'] = dt.strptime(heatmap['start_date'], '%Y-%m-%d').date() if heatmap.get('start_date') else None
            context['activity_heatmap_end_date'] = dt.strptime(cells[-1]['date'], '%Y-%m-%d').date() if cells else None

        elif request.user.is_teacher():
            taught = request.user.taught_courses.all()
            context['taught_courses'] = taught[:5]
            # Teacher dashboard KPIs
            approved_enrolments = Enrolment.objects.filter(
                course__teacher=request.user, status=Enrolment.APPROVED, blocked=False
            )
            context['total_students'] = approved_enrolments.values('student').distinct().count()
            context['active_courses_count'] = taught.count()
            week_start = timezone.now() - timezone.timedelta(days=7)
            context['completions_this_week'] = Certificate.objects.filter(
                enrolment__course__teacher=request.user, issued_at__gte=week_start
            ).count()
            context['pending_approval_count'] = Enrolment.objects.filter(
                course__teacher=request.user, status=Enrolment.PENDING
            ).count()
            # Pending approvals (for card list)
            context['pending_approvals'] = Enrolment.objects.filter(
                course__teacher=request.user, status=Enrolment.PENDING
            ).select_related('student', 'course').order_by('-enrolled_at')[:10]
            # Stat percentages for teacher dashboard progress bars
            context['stat_students_pct'] = min(100, int((context.get('total_students') or 0) / 150 * 100))
            context['stat_active_pct'] = min(100, int((context.get('active_courses_count') or 0) / 10 * 100))
            context['stat_completions_pct'] = min(100, int((context.get('completions_this_week') or 0) / 20 * 100))
            context['stat_pending_pct'] = min(100, int((context.get('pending_approval_count') or 0) / 10 * 100))
            # Recent activity: enrolments + feedback (mixed, by date)
            recent_enrolments = Enrolment.objects.filter(
                course__teacher=request.user
            ).select_related('student', 'course').order_by('-enrolled_at')[:10]
            recent_feedback = Feedback.objects.filter(
                course__teacher=request.user
            ).select_related('student', 'course').order_by('-created_at')[:10]
            context['recent_activity'] = []
            for e in recent_enrolments:
                context['recent_activity'].append({
                    'type': 'enrolment',
                    'student': e.student,
                    'course': e.course,
                    'date': e.enrolled_at,
                    'label': f'Enrolled in {e.course.title}',
                })
            for f in recent_feedback:
                context['recent_activity'].append({
                    'type': 'feedback',
                    'student': f.student,
                    'course': f.course,
                    'date': f.created_at,
                    'label': f'Left feedback on {f.course.title} ({f.rating}/5)',
                })
            context['recent_activity'].sort(key=lambda x: x['date'], reverse=True)
            context['recent_activity'] = context['recent_activity'][:8]
            # Courses overview (course with student count for progress display)
            context['courses_overview'] = taught.annotate(
                student_count=Count('enrolments', filter=Q(enrolments__status=Enrolment.APPROVED, enrolments__blocked=False))
            ).order_by('-student_count')
            context['messages_waiting'] = context['unread_count']
            # Engagement: avg feedback rating, total certificates, weekly engagement (Activity-based)
            from django.db.models import Avg
            from analytics.services import get_weekly_engagement

            fb_agg = Feedback.objects.filter(course__teacher=request.user).aggregate(avg=Avg('rating'))
            context['avg_feedback_rating'] = round(fb_agg['avg'], 1) if fb_agg['avg'] is not None else None
            context['certificates_issued_total'] = Certificate.objects.filter(
                enrolment__course__teacher=request.user
            ).count()
            # Weekly engagement: Daily Active Students + Daily Submissions (7-day rolling)
            try:
                we = get_weekly_engagement(request.user)
            except Exception:
                from datetime import timedelta
                today = timezone.now().date()
                we = {
                    'week_start': (today - timedelta(days=6)).isoformat(),
                    'data': [
                        {'date': (today - timedelta(days=6 - i)).isoformat(), 'day_label': (today - timedelta(days=6 - i)).strftime('%a'), 'active_students': 0, 'submissions': 0}
                        for i in range(7)
                    ],
                }
            context['weekly_engagement'] = we
            data = we['data']
            chart_max = max(
                max((r['active_students'] for r in data), default=0),
                max((r['submissions'] for r in data), default=0),
                1,
            )
            # Line chart coordinates: viewBox 0 0 320 170, plot area (45,25)-(305,135)
            plot_left, plot_top, plot_w, plot_h = 45, 25, 260, 110
            pts_active = []
            pts_submissions = []
            chart_points_active = []
            chart_points_submissions = []
            for i, row in enumerate(data):
                x = round(plot_left + (plot_w * i) / 6) if i < 6 else plot_left + plot_w
                y_a = round(plot_top + plot_h - (row['active_students'] / chart_max) * plot_h)
                y_s = round(plot_top + plot_h - (row['submissions'] / chart_max) * plot_h)
                pts_active.append(f'{x},{y_a}')
                pts_submissions.append(f'{x},{y_s}')
                chart_points_active.append({'x': x, 'y': y_a, 'value': row['active_students']})
                chart_points_submissions.append({'x': x, 'y': y_s, 'value': row['submissions']})
                row['x_label'] = x  # for X-axis day label position
            context['weekly_sparkline_points_active'] = ' '.join(pts_active)
            context['weekly_sparkline_points_submissions'] = ' '.join(pts_submissions)
            context['engagement_chart_points_active'] = chart_points_active
            context['engagement_chart_points_submissions'] = chart_points_submissions
            context['engagement_chart_max'] = chart_max
            context['engagement_chart_plot'] = {'left': plot_left, 'top': plot_top, 'width': plot_w, 'height': plot_h}
            # Students completed this week: by course (for 2D pie chart with segments)
            raw = Certificate.objects.filter(
                enrolment__course__teacher=request.user,
                issued_at__gte=week_start,
            ).values('enrolment__course__title', 'enrolment__course__id').annotate(
                count=Count('id')
            ).order_by('-count')
            total_week = sum(r['count'] for r in raw)
            pie_colors = ['#0d9488', '#14b8a6', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#10b981']
            segments = []
            cum = 0
            for i, r in enumerate(raw):
                pct = (100 * r['count'] / total_week) if total_week else 0
                segments.append({
                    'course_title': r['enrolment__course__title'],
                    'course_id': r['enrolment__course__id'],
                    'count': r['count'],
                    'start_pct': cum,
                    'end_pct': cum + pct,
                    'color': pie_colors[i % len(pie_colors)],
                })
                cum += pct
            context['completions_by_course_this_week'] = segments
            context['completions_pie_total'] = total_week
    return render(request, 'home.html', context)


@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    from courses.models import Course
    from calendar_app.models import Event

    user_results = []
    course_results = []
    event_results = []
    if query:
        user_results = User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        course_results = Course.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).select_related('teacher')
        event_results = Event.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    return render(request, 'accounts/search_results.html', {
        'query': query,
        'user_results': user_results,
        'course_results': course_results,
        'event_results': event_results,
    })


@login_required
def my_students(request):
    """List students enrolled in the current teacher's courses (teachers only)."""
    if not request.user.is_teacher():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Only teachers can view My Students.')
    from courses.models import Enrolment, Certificate, Course

    enrolments = Enrolment.objects.filter(
        course__teacher=request.user,
        status=Enrolment.APPROVED,
        blocked=False,
    ).select_related('student', 'course').order_by('student__username', 'course__title')

    # Per-course aggregates: approved students, issued certificates, average rating
    approved_per_course = {}
    for enr in enrolments:
        cid = enr.course_id
        approved_per_course[cid] = approved_per_course.get(cid, 0) + 1

    cert_counts = (
        Certificate.objects.filter(
            enrolment__course__teacher=request.user,
            enrolment__status=Enrolment.APPROVED,
            enrolment__blocked=False,
            status=Certificate.STATUS_ISSUED,
        )
        .values('enrolment__course')
        .annotate(cnt=Count('id'))
    )
    issued_per_course = {row['enrolment__course']: row['cnt'] for row in cert_counts}

    course_ids = list(approved_per_course.keys())
    avg_map = {}
    if course_ids:
        courses_with_avg = Course.objects.filter(
            teacher=request.user, id__in=course_ids
        ).annotate(avg_rating=Avg('feedback__rating'))
        avg_map = {c.id: c.avg_rating for c in courses_with_avg}

    course_stats = {}
    for cid, students_count in approved_per_course.items():
        issued = issued_per_course.get(cid, 0)
        if students_count > 0:
            completion_pct = int(min(100, (issued / students_count) * 100))
        else:
            completion_pct = 0
        course_stats[cid] = {
            'completion_pct': completion_pct,
            'avg_score': avg_map.get(cid),
        }

    # Build flat list: one row per (student, course) with stats
    rows = []
    for enr in enrolments:
        rows.append(
            {
                'student': enr.student,
                'course': enr.course,
                'stats': course_stats.get(
                    enr.course_id,
                    {'completion_pct': 0, 'avg_score': None},
                ),
            }
        )
    context = {
        'student_courses': rows,
    }
    return render(request, 'accounts/my_students.html', context)


@login_required
@require_POST
def set_presence(request):
    """Set the current user's presence and optional status text / clear-after rule."""
    status = (request.POST.get('status') or '').strip().upper()
    status_text = (request.POST.get('status_text') or '').strip()[:200]
    clear_after = (request.POST.get('clear_after') or '').strip().upper()

    valid_statuses = (
        User.AVAILABLE,
        User.ONLINE,
        User.BUSY,
        User.AWAY,
        User.OFFLINE,
    )
    update_fields = []
    if status in valid_statuses:
        request.user.presence = status
        update_fields.append('presence')
    if 'status_text' in request.POST:
        request.user.status_text = status_text
        update_fields.append('status_text')

    if 'clear_after' in request.POST and clear_after in dict(User.STATUS_CLEAR_CHOICES):
        request.user.status_clear_after = clear_after
        update_fields.append('status_clear_after')
        now = timezone.now()
        expires_at = None
        if clear_after == User.CLEAR_1H:
            expires_at = now + timezone.timedelta(hours=1)
        elif clear_after == User.CLEAR_5H:
            expires_at = now + timezone.timedelta(hours=5)
        elif clear_after == User.CLEAR_TODAY:
            expires_at = now.replace(hour=23, minute=59, second=59, microsecond=0)
        elif clear_after == User.CLEAR_WEEK:
            expires_at = now + timezone.timedelta(days=7)
        request.user.status_expires_at = expires_at
        update_fields.append('status_expires_at')

    if update_fields:
        request.user.save(update_fields=update_fields)
    return JsonResponse({
        'ok': True,
        'presence': request.user.presence,
        'status_text': request.user.status_text or '',
        'clear_after': request.user.status_clear_after,
    })


@login_required
@require_POST
def set_theme(request):
    """Set the current user's theme mode (LIGHT, DARK, SYSTEM). Returns JSON for quick theme switching."""
    mode = (request.POST.get('theme_mode') or '').strip().upper()
    if mode not in (User.THEME_LIGHT, User.THEME_DARK, User.THEME_SYSTEM):
        return JsonResponse({'ok': False, 'error': 'Invalid theme'}, status=400)
    request.user.theme_mode = mode
    request.user.save(update_fields=['theme_mode'])
    return JsonResponse({'ok': True, 'theme_mode': mode.lower()})


def _user_has_2fa(user):
    """Return True if the user has at least one confirmed TOTP device."""
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def _make_qr_data_url(provisioning_uri):
    """Generate a data URL for a QR code image from an otpauth URI."""
    try:
        import qrcode
        buf = io.BytesIO()
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        img.save(buf, format='PNG')
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode('ascii')
        return f'data:image/png;base64,{b64}'
    except Exception:
        return None


@login_required
@require_GET
def two_factor_setup(request):
    """Enable 2FA: show QR code and verify with a token from the authenticator app."""
    if _user_has_2fa(request.user):
        messages.info(request, 'Two-factor authentication is already enabled.')
        return redirect(f'{reverse("accounts:settings")}?tab=security')

    device = None
    # Reuse existing unconfirmed device from this session if any (use our own key to avoid clashing with django_otp middleware)
    device_id = request.session.get('studysphere_otp_setup_device_id')
    if device_id:
        device = TOTPDevice.objects.filter(
            user=request.user, id=device_id, confirmed=False
        ).first()
    if not device:
        device = TOTPDevice.objects.create(
            user=request.user,
            name='default',
            confirmed=False,
        )
        request.session['studysphere_otp_setup_device_id'] = device.id

    provisioning_uri = device.config_url
    qr_data_url = _make_qr_data_url(provisioning_uri)
    # Base32 secret for manual entry in authenticator apps (key is stored as hex)
    try:
        secret_base32 = base64.b32encode(device.bin_key).decode('ascii').replace('=', '')
    except Exception:
        secret_base32 = None

    return render(request, 'accounts/two_factor_setup.html', {
        'device': device,
        'qr_data_url': qr_data_url,
        'provisioning_uri': provisioning_uri,
        'secret_base32': secret_base32,
    })


@login_required
@require_POST
def two_factor_verify_setup(request):
    """Verify the first OTP token to confirm the device and enable 2FA."""
    token = (request.POST.get('token') or '').strip().replace(' ', '')
    device_id = request.session.get('studysphere_otp_setup_device_id')
    if not device_id or not token:
        messages.error(request, 'Please enter the 6-digit code from your authenticator app.')
        return redirect('accounts:two_factor_setup')

    device = TOTPDevice.objects.filter(
        user=request.user, id=device_id, confirmed=False
    ).first()
    if not device:
        messages.error(request, 'Setup expired. Please start again.')
        if 'studysphere_otp_setup_device_id' in request.session:
            del request.session['studysphere_otp_setup_device_id']
        return redirect('accounts:two_factor_setup')

    if not device.verify_is_allowed():
        messages.error(request, 'Too many attempts. Please wait a moment and try again.')
        return redirect('accounts:two_factor_setup')

    if device.verify_token(token):
        device.confirmed = True
        device.save(update_fields=['confirmed'])
        if 'studysphere_otp_setup_device_id' in request.session:
            del request.session['studysphere_otp_setup_device_id']
        messages.success(request, 'Two-factor authentication is now enabled.')
        return redirect(f'{reverse("accounts:settings")}?tab=security')
    messages.error(request, 'Invalid code. Please enter the current code from your authenticator app.')
    return redirect('accounts:two_factor_setup')


@login_required
@require_POST
def two_factor_disable(request):
    """Disable 2FA after confirming with password."""
    password = request.POST.get('password', '')
    if not request.user.check_password(password):
        messages.error(request, 'Incorrect password. Two-factor authentication was not disabled.')
        return redirect(f'{reverse("accounts:settings")}?tab=security')

    deleted, _ = TOTPDevice.objects.filter(user=request.user).delete()
    if deleted:
        messages.success(request, 'Two-factor authentication has been disabled.')
    else:
        messages.info(request, 'Two-factor authentication was not enabled.')
    return redirect(f'{reverse("accounts:settings")}?tab=security')


def two_factor_verify(request):
    """After password login: prompt for OTP and complete login."""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:login')

    user = get_object_or_404(User, pk=user_id)
    next_url = request.session.get('otp_next', '/')

    if request.method == 'POST':
        token = (request.POST.get('token') or '').strip().replace(' ', '')
        if not token:
            return render(request, 'accounts/two_factor_verify.html', {
                'error': 'Please enter the 6-digit code from your authenticator app.',
                'next_url': next_url,
            })

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            if 'otp_next' in request.session:
                del request.session['otp_next']
            return redirect('accounts:login')

        if device.verify_is_allowed() and device.verify_token(token):
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            if 'otp_next' in request.session:
                del request.session['otp_next']
            login(request, user)
            return redirect(next_url)

        return render(request, 'accounts/two_factor_verify.html', {
            'error': 'Invalid code. Please try again or use the current code from your app.',
            'next_url': next_url,
        })

    return render(request, 'accounts/two_factor_verify.html', {
        'error': None,
        'next_url': next_url,
    })
