import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When, CharField, F
from django.utils import timezone
from django.http import FileResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseMaterialForm, CourseForm, FeedbackForm, VideoResourceForm, StudentSubmissionForm
from .models import Certificate, Course, Enrolment, Feedback, VideoResource, StudentSubmission
from .utils.supabase_storage import upload_file, delete_file_by_url
from .utils.certificates import generate_and_upload_certificate
from analytics.services import log_activity
from analytics.models import Activity

# Status values for enrolment
ENROLMENT_APPROVED = Enrolment.APPROVED
ENROLMENT_PENDING = Enrolment.PENDING
ENROLMENT_REJECTED = Enrolment.REJECTED


def course_list(request):
    courses = Course.objects.annotate(avg_rating=Avg('feedback__rating')).order_by('-created_at')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    if q:
        courses = courses.filter(Q(title__icontains=q))
    if category:
        courses = courses.filter(category=category)
    paginator = Paginator(courses, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    category_label = dict(Course.CATEGORY_CHOICES).get(category, category) if category else ''
    return render(request, 'courses/course_list.html', {
        'courses': page_obj,
        'page_obj': page_obj,
        'q': q,
        'category': category,
        'category_label': category_label,
    })


@login_required
def video_resources(request):
    """Videos page: list YouTube/video links; teachers can add new ones."""
    videos = VideoResource.objects.select_related('course', 'added_by').all()
    form = None
    if request.user.is_teacher():
        form = VideoResourceForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            obj = form.save(commit=False)
            obj.added_by = request.user
            obj.save()
            messages.success(request, f'Video "{obj.title}" added.')
            return redirect('courses:video_resources')
        form.fields['course'].queryset = Course.objects.filter(teacher=request.user).exclude(is_general=True)
        form.fields['course'].required = False
        form.fields['course'].empty_label = '— Global (no course) —'
    return render(request, 'courses/video_resources.html', {
        'videos': videos,
        'form': form,
    })


def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.annotate(avg_rating=Avg('feedback__rating')),
        pk=pk,
    )
    back_from = request.GET.get('from')
    is_teacher = (
        request.user.is_authenticated
        and request.user == course.teacher
    )
    if is_teacher:
        materials = course.materials.all()
    else:
        materials = course.materials.filter(published=True)
    feedback_list = course.feedback.select_related('student').all()
    is_enrolled = False
    enrolment = None
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'STUDENT':
        enrolment = Enrolment.objects.filter(
            student=request.user, course=course,
        ).first()
        is_enrolled = (
            enrolment is not None
            and enrolment.status == ENROLMENT_APPROVED
            and not enrolment.blocked
        )

    # Teacher: show ALL enrolments for this course (no status filter) so no student is ever missing
    all_enrolments = []
    approved_enrolments_for_certificate = []
    enrolment_ids_with_certificate = set()
    if is_teacher:
        all_enrolments = (
            Enrolment.objects.filter(course=course)
            .select_related('student', 'certificate')
            .annotate(
                certificate_status=Case(
                    When(certificate__status__isnull=False, then=F('certificate__status')),
                    default=Value(''),
                    output_field=CharField(),
                )
            )
            .order_by(
                Case(
                    When(status=ENROLMENT_PENDING, then=Value(0)),
                    When(status=ENROLMENT_APPROVED, then=Value(1)),
                    When(status=ENROLMENT_REJECTED, then=Value(2)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                '-enrolled_at',
            )
        )
        enrolment_ids_with_certificate = set(
            Certificate.objects.filter(
                enrolment__course=course,
                status=Certificate.STATUS_ISSUED,
            ).values_list('enrolment_id', flat=True)
        )
        approved_enrolments_for_certificate = [
            e for e in all_enrolments
            if e.status == ENROLMENT_APPROVED and not e.blocked
        ]

    material_form = CourseMaterialForm() if is_teacher else None
    user_feedback = None
    if is_enrolled and request.user.is_authenticated:
        user_feedback = Feedback.objects.filter(
            student=request.user, course=course,
        ).first()
    feedback_form = FeedbackForm(instance=user_feedback) if is_enrolled else None

    submissions = None
    show_submission_form = False
    submission_form = None
    if request.user.is_authenticated:
        if is_teacher:
            submissions = course.submissions.select_related('student').all()
        elif is_enrolled and hasattr(request.user, 'role') and request.user.role == 'STUDENT':
            submissions = course.submissions.filter(student=request.user).select_related('student')
            show_submission_form = True
            submission_form = StudentSubmissionForm()

    has_certificate = False
    if enrolment and is_enrolled:
        has_certificate = Certificate.objects.filter(enrolment=enrolment).exists()

    if request.user.is_authenticated and (is_teacher or is_enrolled):
        log_activity(request.user, Activity.VIEW, course=course)

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'materials': materials,
        'feedback_list': feedback_list,
        'is_teacher': is_teacher,
        'is_enrolled': is_enrolled,
        'enrolment': enrolment,
        'has_certificate': has_certificate,
        'all_enrolments': all_enrolments,
        'approved_enrolments_for_certificate': approved_enrolments_for_certificate,
        'enrolment_ids_with_certificate': enrolment_ids_with_certificate,
        'material_form': material_form,
        'feedback_form': feedback_form,
        'user_feedback': user_feedback,
        'back_from': back_from,
        'submissions': submissions,
        'show_submission_form': show_submission_form,
        'submission_form': submission_form,
    })


@login_required
def course_create(request):
    if not hasattr(request.user, 'role') or request.user.role != 'TEACHER':
        return HttpResponseForbidden("Only teachers can create courses.")

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            hero = form.cleaned_data.get('hero_image')
            uploaded_hero = False
            if hero:
                url = upload_file(hero)
                if url:
                    # Store Supabase URL and avoid persisting the local file
                    course.hero_image_url = url
                    course.hero_image = None
                    uploaded_hero = True
            course.save()
            if uploaded_hero:
                messages.success(request, 'Course created and image uploaded successfully.')
            else:
                messages.success(request, 'Course created successfully.')
            return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm()

    return render(request, 'courses/course_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can edit this course.")

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            course = form.save(commit=False)
            hero = form.cleaned_data.get('hero_image')
            hero_message = None

            # hero is an UploadedFile when a new image is chosen; None when unchanged.
            if hero:
                url = upload_file(hero)
                if url:
                    course.hero_image_url = url
                    course.hero_image = None
                    hero_message = 'Course image updated successfully.'
            else:
                # Optional explicit remove flag from the form.
                remove_flag = bool(request.POST.get('remove_hero_image'))
                if remove_flag:
                    course.hero_image_url = ''
                    course.hero_image = None
                    hero_message = 'Course image removed.'

            course.save()
            if hero_message:
                messages.success(request, f'Course updated. {hero_message}')
            else:
                messages.success(request, 'Course updated successfully.')
            return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)

    return render(request, 'courses/course_form.html', {
        'form': form,
        'action': 'Edit',
    })


@login_required
def enrol(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    if not hasattr(request.user, 'role') or request.user.role != 'STUDENT':
        return HttpResponseForbidden("Only students can enrol in courses.")

    course = get_object_or_404(Course, pk=pk)
    # Every first enrolment: default Pending (Action) and no certificate (Not issued). Teacher approves → student sees Active; teacher issues certificate → student sees it.
    enrolment, created = Enrolment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': ENROLMENT_PENDING},
    )
    if created:
        messages.success(
            request,
            f'You have requested to enrol in {course.title}. The teacher will approve your enrolment.',
        )
    elif enrolment.status == ENROLMENT_REJECTED:
        enrolment.status = ENROLMENT_PENDING
        enrolment.save(update_fields=['status'])
        messages.success(request, f'You have re-applied to enrol in {course.title}.')
    elif enrolment.status == ENROLMENT_PENDING:
        messages.info(request, 'Your enrolment request is pending approval by the teacher.')
    else:
        messages.info(request, 'You are already enrolled in this course.')

    return redirect('courses:course_detail', pk=pk)


@login_required
def upload_material(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can upload materials.")

    form = CourseMaterialForm(request.POST, request.FILES)
    if form.is_valid():
        material = form.save(commit=False)
        material.course = course
        material.author = request.user
        upload = form.cleaned_data.get('file')
        if upload:
            try:
                url = upload_file(upload, prefix='courses/materials')
            except Exception as exc:
                # Fall back to local file storage if cloud upload fails (e.g. Supabase RLS).
                material.file = upload
                material.material_url = ''
                messages.warning(
                    request,
                    'Cloud upload failed; the file has been stored locally instead. '
                    'Please contact the administrator to check Supabase storage/RLS settings.'
                )
            else:
                if url:
                    material.material_url = url
                    material.file = None
        # Newly uploaded materials default to unpublished; teacher can publish later.
        material.published = False
        material.published_at = None
        material.save()
        messages.success(request, 'Material uploaded successfully (currently unpublished).')
    else:
        messages.error(request, 'Failed to upload material. Please check the form.')

    return redirect('courses:course_detail', pk=pk)


@login_required
def submit_work(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    user = request.user

    if not hasattr(user, 'role') or user.role != 'STUDENT':
        return HttpResponseForbidden("Only students can submit coursework.")

    enrolment = Enrolment.objects.filter(
        student=user,
        course=course,
        status=ENROLMENT_APPROVED,
        blocked=False,
    ).first()
    if not enrolment:
        return HttpResponseForbidden("Only enrolled students can submit coursework.")

    form = StudentSubmissionForm(request.POST, request.FILES)
    if form.is_valid():
        submission = form.save(commit=False)
        submission.course = course
        submission.student = user
        upload = form.cleaned_data.get('file')
        if upload:
            try:
                url = upload_file(upload, prefix='courses/submissions')
            except Exception:
                submission.file = upload
                submission.file_url = ''
                messages.warning(
                    request,
                    'Cloud upload failed; your work has been stored locally instead. '
                    'Please contact the administrator to check Supabase storage/RLS settings.'
                )
            else:
                if url:
                    submission.file_url = url
                    submission.file = None
        submission.save()
        messages.success(request, 'Your work has been submitted successfully.')
    else:
        messages.error(request, 'Failed to submit work. Please check the form.')

    return redirect('courses:course_detail', pk=pk)


@login_required
def edit_submission(request, pk, submission_id):
    course = get_object_or_404(Course, pk=pk)
    user = request.user

    if not hasattr(user, 'role') or user.role != 'STUDENT':
        return HttpResponseForbidden("Only students can edit their submissions.")

    submission = get_object_or_404(
        StudentSubmission,
        pk=submission_id,
        course=course,
        student=user,
    )

    if request.method == 'POST':
        form = StudentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            upload = form.cleaned_data.get('file')
            if upload:
                try:
                    url = upload_file(upload, prefix='courses/submissions')
                except Exception:
                    submission.file = upload
                    submission.file_url = submission.file_url or ''
                    messages.warning(
                        request,
                        'Cloud upload failed; your new file has been stored locally instead. '
                        'Please contact the administrator to check Supabase storage/RLS settings.'
                    )
                else:
                    if url:
                        submission.file_url = url
                        submission.file = None
            submission.save()
            messages.success(request, 'Your submission has been updated.')
            return redirect('courses:course_detail', pk=pk)
    else:
        form = StudentSubmissionForm(instance=submission)

    return render(request, 'courses/submission_form.html', {
        'form': form,
        'course': course,
        'submission': submission,
    })


@login_required
def delete_submission(request, pk, submission_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    user = request.user

    if not hasattr(user, 'role') or user.role != 'STUDENT':
        return HttpResponseForbidden("Only students can delete their own submissions.")

    submission = get_object_or_404(
        StudentSubmission,
        pk=submission_id,
        course=course,
        student=user,
    )
    title = submission.title
    url = submission.file_url
    if url:
        delete_file_by_url(url)
    if submission.file:
        try:
            submission.file.delete(save=False)
        except Exception:
            pass
    submission.delete()
    messages.success(request, f'Submission "{title}" has been deleted.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def edit_material(request, pk, material_id):
    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can edit materials.")

    material = get_object_or_404(course.materials, pk=material_id)

    if request.method == 'POST':
        form = CourseMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            material = form.save(commit=False)
            upload = form.cleaned_data.get('file')
            if upload:
                try:
                    url = upload_file(upload, prefix='courses/materials')
                except Exception as exc:
                    material.file = upload
                    material.material_url = material.material_url or ''
                    messages.warning(
                        request,
                        'Cloud upload failed; the new file has been stored locally instead. '
                        'Please contact the administrator to check Supabase storage/RLS settings.'
                    )
                else:
                    if url:
                        material.material_url = url
                        material.file = None
            material.save()
            messages.success(request, 'Material updated successfully.')
            return redirect('courses:course_detail', pk=pk)
    else:
        form = CourseMaterialForm(instance=material)

    return render(request, 'courses/material_form.html', {
        'form': form,
        'course': course,
        'material': material,
    })


@login_required
def toggle_material_publish(request, pk, material_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can publish materials.")

    material = get_object_or_404(course.materials, pk=material_id)
    material.published = not material.published
    if material.published:
        material.published_at = timezone.now()
        messages.success(request, 'Material published.')
    else:
        messages.success(request, 'Material unpublished.')
    material.save(update_fields=['published', 'published_at'])

    return redirect('courses:course_detail', pk=pk)


@login_required
def delete_material(request, pk, material_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can delete materials.")

    material = get_object_or_404(course.materials, pk=material_id)
    title = material.title
    url = material.material_url
    if url:
        delete_file_by_url(url)
    material.delete()
    messages.success(request, f'Material "{title}" has been deleted.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def leave_feedback(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    enrolment = Enrolment.objects.filter(
        student=request.user, course=course,
        status=ENROLMENT_APPROVED, blocked=False,
    ).first()
    if not enrolment:
        return HttpResponseForbidden("Only enrolled students can leave feedback.")

    form = FeedbackForm(request.POST)
    if form.is_valid():
        feedback, created = Feedback.objects.update_or_create(
            student=request.user,
            course=course,
            defaults={'rating': form.cleaned_data['rating'], 'comment': form.cleaned_data['comment']},
        )
        log_activity(request.user, Activity.SUBMIT, course=course)
        messages.success(request, 'Feedback updated successfully.' if not created else 'Feedback submitted successfully.')
    else:
        messages.error(request, 'Failed to submit feedback. Please check the form.')

    return redirect('courses:course_detail', pk=pk)


@login_required
def edit_feedback(request, pk, feedback_id):
    """Edit own feedback (rating and comment)."""
    course = get_object_or_404(Course, pk=pk)
    feedback = get_object_or_404(Feedback, pk=feedback_id, course=course)
    if feedback.student != request.user:
        return HttpResponseForbidden("You can only edit your own feedback.")

    enrolment = Enrolment.objects.filter(
        student=request.user, course=course,
        status=ENROLMENT_APPROVED, blocked=False,
    ).first()
    if not enrolment:
        return HttpResponseForbidden("Only enrolled students can edit feedback.")

    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            messages.success(request, 'Feedback updated successfully.')
            return redirect('courses:course_detail', pk=pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackForm(instance=feedback)

    return render(request, 'courses/feedback_edit.html', {
        'course': course,
        'feedback': feedback,
        'form': form,
    })


@login_required
def delete_feedback(request, pk, feedback_id):
    """Delete own feedback."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    feedback = get_object_or_404(Feedback, pk=feedback_id, course=course)
    if feedback.student != request.user:
        return HttpResponseForbidden("You can only delete your own feedback.")

    enrolment = Enrolment.objects.filter(
        student=request.user, course=course,
        status=ENROLMENT_APPROVED, blocked=False,
    ).first()
    if not enrolment:
        return HttpResponseForbidden("Only enrolled students can delete feedback.")

    feedback.delete()
    messages.success(request, 'Your feedback has been removed.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def approve_student(request, pk, student_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can approve students.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_PENDING:
        messages.info(request, 'That enrolment is not pending.')
        return redirect('courses:course_detail', pk=pk)

    enrolment.status = ENROLMENT_APPROVED
    enrolment.save(update_fields=['status'])
    messages.success(request, f'Enrolment for {enrolment.student.username} has been approved.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def reject_student(request, pk, student_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can reject enrolments.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_PENDING:
        messages.info(request, 'Only pending enrolments can be rejected.')
        return redirect('courses:course_detail', pk=pk)

    enrolment.status = ENROLMENT_REJECTED
    enrolment.save(update_fields=['status'])
    messages.success(request, f'Enrolment request for {enrolment.student.username} has been rejected.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def block_student(request, pk, student_id):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can block/unblock students.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_APPROVED:
        messages.info(request, 'You can only block approved enrolments.')
        return redirect('courses:course_detail', pk=pk)

    enrolment.blocked = not enrolment.blocked
    enrolment.save(update_fields=['blocked'])

    action = 'blocked' if enrolment.blocked else 'unblocked'
    messages.success(request, f'Student has been {action}.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def set_enrolment_status(request, pk, student_id):
    """Teacher sets enrolment status (Pending, Approved, Reject) and optional Block. POST only."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can change enrolment status.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    status = request.POST.get('status')
    # BLOCK = course full, no more enrolments (stored as APPROVED + blocked=True)
    if status == 'BLOCK':
        enrolment.status = ENROLMENT_APPROVED
        enrolment.blocked = True
        enrolment.save(update_fields=['status', 'blocked'])
        messages.success(request, "Enrolment set to Block (course full).")
        return redirect('courses:course_detail', pk=pk)
    if status not in (ENROLMENT_PENDING, ENROLMENT_APPROVED, ENROLMENT_REJECTED):
        messages.error(request, 'Invalid status.')
        return redirect('courses:course_detail', pk=pk)

    enrolment.status = status
    enrolment.blocked = False
    enrolment.save(update_fields=['status', 'blocked'])

    labels = {'PENDING': 'Pending', 'APPROVED': 'Approved', 'REJECTED': 'Rejected'}
    messages.success(request, f"Enrolment set to {labels.get(status, status)}.")
    return redirect('courses:course_detail', pk=pk)


@login_required
def revoke_certificate(request, pk, student_id):
    """Teacher revokes (deletes) the certificate for an enrolment. POST only."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can revoke certificates.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    try:
        cert = enrolment.certificate
        cert.status = Certificate.STATUS_REVOKED
        cert.save(update_fields=['status'])
        messages.success(request, f'Certificate revoked for {enrolment.student.username}.')
    except Certificate.DoesNotExist:
        messages.info(request, 'No certificate to revoke.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def generate_certificate(request, pk, student_id):
    """Teacher generates a PDF certificate with QR code and uploads to Supabase. POST only."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can generate certificates.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_APPROVED or enrolment.blocked:
        msg = 'You can only generate certificates for approved, non-blocked enrolments.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('courses:course_detail', pk=pk)

    certificate, created = Certificate.objects.get_or_create(
        enrolment=enrolment,
        defaults={'status': Certificate.STATUS_ISSUED, 'issued_by': request.user},
    )
    if not created:
        certificate.issued_by = request.user
        certificate.status = Certificate.STATUS_ISSUED
        certificate.save(update_fields=['issued_by', 'status'])

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        url = generate_and_upload_certificate(enrolment.student, course, certificate)
    except Exception as e:
        err = f'Certificate generation failed. Check that ReportLab, qrcode and Supabase are configured. ({e!s})'
        if is_ajax:
            return JsonResponse({'success': False, 'error': err}, status=500)
        messages.error(request, err)
        return redirect('courses:course_detail', pk=pk)

    if not url:
        err = (
            'Certificate PDF was generated but upload failed. '
            'Check Supabase: SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET and that the bucket exists and allows uploads.'
        )
        if is_ajax:
            return JsonResponse({'success': False, 'error': err}, status=500)
        messages.error(request, err)
        return redirect('courses:course_detail', pk=pk)

    certificate.certificate_url = url
    certificate.save(update_fields=['certificate_url'])

    # AJAX: return JSON so the frontend can show "Export as PDF?" and trigger download
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.urls import reverse
        download_url = request.build_absolute_uri(
            reverse('courses:download_certificate', args=[enrolment.id])
        )
        return JsonResponse({
            'success': True,
            'download_url': download_url,
            'message': f'Certificate generated for {enrolment.student.username}.',
        })

    messages.success(request, f'PDF certificate with QR code generated for {enrolment.student.username}.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def set_certificate_action(request, pk, student_id):
    """Teacher chooses certificate action: Not issued (no op), Issue (redirect to upload), or Revoke. POST only."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can manage certificates.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_APPROVED:
        messages.error(request, 'Certificates can only be managed for approved enrolments.')
        return redirect('courses:course_detail', pk=pk)

    action = (request.POST.get('certificate_action') or '').strip().lower()
    if not action:
        # User left the status selector on the placeholder.
        messages.info(request, 'Please choose a certificate status before saving.')
        return redirect('courses:course_detail', pk=pk)

    if action == 'pending':
        # Reset to "pending validation" by removing any existing certificate.
        try:
            cert = enrolment.certificate
            cert.delete()
            messages.success(request, f'Certificate reset to pending validation for {enrolment.student.username}.')
        except Certificate.DoesNotExist:
            messages.info(request, 'Certificate is already pending validation.')
        return redirect('courses:course_detail', pk=pk)

    if action == 'issued':
        # If no certificate yet, go to upload screen; otherwise mark as issued.
        try:
            cert = enrolment.certificate
        except Certificate.DoesNotExist:
            return redirect('courses:issue_certificate', pk=pk, student_id=student_id)
        cert.status = Certificate.STATUS_ISSUED
        cert.save(update_fields=['status'])
        messages.success(request, f'Certificate marked as issued for {enrolment.student.username}.')
        return redirect('courses:course_detail', pk=pk)

    if action == 'revoked':
        try:
            cert = enrolment.certificate
            cert.status = Certificate.STATUS_REVOKED
            cert.save(update_fields=['status'])
            messages.success(request, f'Certificate revoked for {enrolment.student.username}.')
        except Certificate.DoesNotExist:
            messages.info(request, 'No certificate to revoke.')
        return redirect('courses:course_detail', pk=pk)

    if action == 'expired':
        try:
            cert = enrolment.certificate
            cert.status = Certificate.STATUS_EXPIRED
            cert.save(update_fields=['status'])
            messages.success(request, f'Certificate marked as expired for {enrolment.student.username}.')
        except Certificate.DoesNotExist:
            messages.info(request, 'No certificate to expire.')
        return redirect('courses:course_detail', pk=pk)

    messages.error(request, 'Invalid certificate action.')
    return redirect('courses:course_detail', pk=pk)


@login_required
def issue_certificate(request, pk, student_id):
    """Teacher uploads a certificate file for an approved enrolment."""
    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        return HttpResponseForbidden("Only the course teacher can issue certificates.")

    enrolment = get_object_or_404(
        Enrolment, course=course, student_id=student_id,
    )
    if enrolment.status != ENROLMENT_APPROVED:
        messages.error(request, 'You can only issue certificates for approved enrolments.')
        return redirect('courses:course_detail', pk=pk)

    if getattr(enrolment, 'certificate', None):
        messages.info(request, 'A certificate has already been issued for this student.')
        return redirect('courses:course_detail', pk=pk)

    if request.method == 'POST':
        cert_file = request.FILES.get('certificate_file')
        if cert_file:
            Certificate.objects.create(
                enrolment=enrolment,
                file=cert_file,
                status=Certificate.STATUS_ISSUED,
                issued_by=request.user,
            )
            messages.success(request, f'Certificate issued for {enrolment.student.username}.')
        else:
            messages.error(request, 'Please select a file to upload.')
        return redirect('courses:course_detail', pk=pk)

    return render(request, 'courses/issue_certificate.html', {
        'course': course,
        'enrolment': enrolment,
    })


@login_required
def download_certificate(request, enrolment_id):
    """Student or teacher downloads the certificate for an enrolment."""
    enrolment = get_object_or_404(Enrolment.objects.select_related('course'), pk=enrolment_id)
    try:
        cert = enrolment.certificate
    except Certificate.DoesNotExist:
        cert = None
    if not cert or cert.status != Certificate.STATUS_ISSUED:
        messages.error(request, 'No certificate found for this enrolment.')
        return redirect('courses:course_detail', pk=enrolment.course_id)

    # Student can download own; teacher can download any for their course
    if request.user != enrolment.student and request.user != enrolment.course.teacher:
        return HttpResponseForbidden("You do not have permission to download this certificate.")

    # Prefer Supabase URL if set (e.g. from Certificate Generator)
    if cert.certificate_url:
        return HttpResponseRedirect(cert.certificate_url)

    if not cert.file or not cert.file.name:
        messages.error(request, 'No certificate file available. Use Certificate Generator to create one.')
        return redirect('courses:course_detail', pk=enrolment.course_id)

    filename = os.path.basename(cert.file.name)
    try:
        return FileResponse(
            cert.file.open('rb'),
            as_attachment=True,
            filename=filename,
        )
    except Exception:
        messages.error(request, 'Could not open certificate file.')
        return redirect('courses:course_detail', pk=enrolment.course_id)


@login_required
def my_courses(request):
    if hasattr(request.user, 'role') and request.user.role == 'TEACHER':
        tab = request.GET.get('tab', 'all')
        # Base queryset for courses taught by this teacher
        taught_qs = (
            Course.objects.filter(teacher=request.user)
            .annotate(
                avg_rating=Avg('feedback__rating'),
                approved_count=Count(
                    'enrolments',
                    filter=Q(
                        enrolments__status=ENROLMENT_APPROVED,
                        enrolments__blocked=False,
                    ),
                    distinct=True,
                ),
            )
        )

        # Certificates issued per course (used as a proxy for completion)
        cert_counts = (
            Certificate.objects.filter(
                enrolment__course__teacher=request.user,
                status=Certificate.STATUS_ISSUED,
            )
            .values('enrolment__course')
            .annotate(cnt=Count('id'))
        )
        cert_map = {row['enrolment__course']: row['cnt'] for row in cert_counts}

        rows = []
        for course in taught_qs:
            students = course.approved_count or 0
            issued = cert_map.get(course.id, 0)
            if students > 0:
                completion_pct = int(min(100, (issued / students) * 100))
            else:
                completion_pct = 0
            rows.append(
                {
                    'course': course,
                    'students': students,
                    'completion_pct': completion_pct,
                    'avg_score': course.avg_rating,
                }
            )

        # Filter / sort according to current tab
        if tab == 'active':
            filtered = [
                r for r in rows
                if r['students'] > 0 and r['completion_pct'] < 100
            ]
        elif tab == 'completed':
            filtered = [
                r for r in rows
                if r['students'] > 0 and r['completion_pct'] >= 100
            ]
        elif tab == 'averages':
            filtered = sorted(
                rows,
                key=lambda r: (r['avg_score'] is None, -(r['avg_score'] or 0)),
            )
        elif tab == 'archive':
            filtered = [
                r for r in rows
                if r['students'] == 0
            ]
        else:
            tab = 'all'
            filtered = sorted(
                rows,
                key=lambda r: r['course'].created_at,
                reverse=True,
            )

        return render(
            request,
            'courses/my_courses.html',
            {
                'taught_courses_table': filtered,
                'courses_tab': tab,
            },
        )
    else:
        # Show all enrolment requests (pending, approved, rejected) with date and status
        all_my_enrolments = (
            Enrolment.objects.filter(student=request.user)
            .select_related('course', 'course__teacher')
            .order_by('-enrolled_at')
        )
        enrolment_ids_with_certificate = set(
            Certificate.objects.filter(
                enrolment__student=request.user,
                status=Certificate.STATUS_ISSUED,
            ).values_list('enrolment_id', flat=True)
        )
        all_my_enrolments = all_my_enrolments.annotate(
            certificate_status=Case(
                When(certificate__status__isnull=False, then=F('certificate__status')),
                default=Value(''),
                output_field=CharField(),
            )
        )
        # Enrolments that have an issued certificate (for "My certificates" section)
        enrolments_with_certificate = [
            e for e in all_my_enrolments
            if e.id in enrolment_ids_with_certificate
        ]
        return render(request, 'courses/my_courses.html', {
            'all_my_enrolments': all_my_enrolments,
            'enrolment_ids_with_certificate': enrolment_ids_with_certificate,
            'enrolments_with_certificate': enrolments_with_certificate,
        })
