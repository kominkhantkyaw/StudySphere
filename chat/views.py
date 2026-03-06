from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
import json
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from courses.models import Course, Enrolment
from .models import Message, ChannelMessage


@login_required
@xframe_options_sameorigin
def chat_room(request, course_id):
    """Course chat room: teacher + approved students; or General room (all authenticated)."""
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    embed = request.GET.get('embed') == '1'

    if getattr(course, 'is_general', False):
        # General announcement room: all authenticated users can join
        pass
    else:
        is_teacher = course.teacher == user
        is_enrolled = Enrolment.objects.filter(
            student=user, course=course, status=Enrolment.APPROVED, blocked=False,
        ).exists()
        if not (is_teacher or is_enrolled):
            return HttpResponseForbidden('You do not have access to this chat room.')

    from social.models import StatusUpdate
    statuses = StatusUpdate.objects.select_related('user').order_by('-created_at')[:20]

    return render(request, 'chat/room.html', {
        'course': course,
        'room_type': 'course',
        'room_title': course.title,
        'ws_path': f'/ws/chat/{course.id}/',
        'upload_url': f'/chat/{course.id}/upload/',
        'statuses': statuses,
        'embed': embed,
    })


@login_required
@xframe_options_sameorigin
def chat_teachers_room(request):
    """Teachers-only room for teacher-to-teacher chat."""
    if not request.user.is_teacher():
        return HttpResponseForbidden('Only teachers can access the Teachers\' room.')

    embed = request.GET.get('embed') == '1'
    from social.models import StatusUpdate
    statuses = StatusUpdate.objects.select_related('user').order_by('-created_at')[:20]

    return render(request, 'chat/room.html', {
        'course': None,
        'room_type': 'teachers',
        'room_title': "Teachers' room",
        'ws_path': '/ws/chat/teachers/',
        'upload_url': '/chat/teachers/upload/',
        'statuses': statuses,
        'embed': embed,
    })


@login_required
@require_POST
def upload_teachers_attachment(request):
    """Handle file upload for the Teachers' room and broadcast via Channels."""
    if not request.user.is_teacher():
        return HttpResponseForbidden('Only teachers can upload files to the Teachers\' room.')

    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({'ok': False, 'error': 'No file uploaded.'}, status=400)

    message = ChannelMessage.objects.create(
        room_name=ChannelMessage.ROOM_TEACHERS,
        sender=request.user,
        content=file_obj.name,
        attachment=file_obj,
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'chat_teachers',
        {
            'type': 'chat.message',
            'id': message.id,
            'message': message.content,
            'username': request.user.username,
            'timestamp': str(message.timestamp),
            'attachment_url': message.attachment.url if message.attachment else '',
            'attachment_name': message.attachment.name if message.attachment else '',
        },
    )

    return JsonResponse({
        'ok': True,
        'id': message.id,
        'message': message.content,
        'attachment_url': message.attachment.url if message.attachment else '',
        'attachment_name': message.attachment.name if message.attachment else '',
        'timestamp': str(message.timestamp),
        'username': request.user.username,
    })


@login_required
def chat_lobby(request):
    """Chat hub: left = chat rooms (General default), right = Activity Feed (Chat & Feed)."""
    user = request.user
    from social.models import StatusUpdate

    general_room = Course.objects.filter(is_general=True).first()
    statuses = StatusUpdate.objects.select_related('user').prefetch_related('reactions').order_by('-created_at')[:20]

    if user.is_teacher():
        courses = Course.objects.filter(teacher=user).exclude(is_general=True)
        return render(
            request,
            'chat/teacher_hub.html',
            {
                'courses': courses,
                'general_room': general_room,
                'show_teachers_room': True,
                'statuses': statuses,
                'is_teacher': True,
            },
        )
    else:
        enrolled_ids = Enrolment.objects.filter(
            student=user, status=Enrolment.APPROVED, blocked=False,
        ).values_list('course_id', flat=True)
        courses = Course.objects.filter(pk__in=enrolled_ids).exclude(is_general=True)
        return render(
            request,
            'chat/teacher_hub.html',
            {
                'courses': courses,
                'general_room': general_room,
                'show_teachers_room': False,
                'statuses': statuses,
                'is_teacher': False,
            },
        )


@login_required
@require_POST
def upload_attachment(request, course_id):
    """Handle file upload for a course chat room and broadcast it via Channels."""
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_teacher = course.teacher == user
    is_enrolled = Enrolment.objects.filter(
        student=user, course=course, status=Enrolment.APPROVED, blocked=False,
    ).exists()
    if not (is_teacher or is_enrolled):
        return HttpResponseForbidden('You do not have access to this chat room.')

    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({'ok': False, 'error': 'No file uploaded.'}, status=400)

    message = Message.objects.create(
        course=course,
        sender=user,
        content=file_obj.name,
        attachment=file_obj,
    )

    channel_layer = get_channel_layer()
    group_name = f'chat_{course.id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'chat.message',
            'id': message.id,
            'message': message.content,
            'username': user.username,
            'timestamp': str(message.timestamp),
            'attachment_url': message.attachment.url if message.attachment else '',
            'attachment_name': message.attachment.name if message.attachment else '',
        },
    )

    return JsonResponse({
        'ok': True,
        'id': message.id,
        'message': message.content,
        'attachment_url': message.attachment.url if message.attachment else '',
        'attachment_name': message.attachment.name if message.attachment else '',
        'timestamp': str(message.timestamp),
        'username': user.username,
    })


@login_required
@require_POST
def delete_message(request, message_id):
    """Allow sender (or course teacher) to delete a chat message (including attachment)."""
    msg = get_object_or_404(Message, pk=message_id)
    user = request.user
    course = msg.course

    is_teacher = course.teacher == user
    is_sender = msg.sender == user
    if not (is_teacher or is_sender):
        return HttpResponseForbidden('You cannot delete this message.')

    course_id = course.id
    msg.delete()

    channel_layer = get_channel_layer()
    group_name = f'chat_{course_id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'chat.delete',
            'id': message_id,
        },
    )

    return JsonResponse({'ok': True, 'id': message_id})


@login_required
@require_POST
def edit_message(request, message_id):
    """
    Allow the sender (or course teacher) to edit a chat message's text/filename
    and broadcast the updated content to the room.
    """
    msg = get_object_or_404(Message, pk=message_id)
    user = request.user
    course = msg.course

    is_teacher = course.teacher == user
    is_sender = msg.sender == user
    if not (is_teacher or is_sender):
        return HttpResponseForbidden('You cannot edit this message.')

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return HttpResponseBadRequest('Invalid JSON.')

    new_text = (data.get('message') or '').strip()
    if not new_text:
        return HttpResponseBadRequest('Message cannot be empty.')

    msg.content = new_text
    msg.save(update_fields=['content'])

    channel_layer = get_channel_layer()
    group_name = f'chat_{course.id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'chat.edit',
            'id': msg.id,
            'message': msg.content,
            'username': msg.sender.username,
            'timestamp': str(msg.timestamp),
            'attachment_url': msg.attachment.url if msg.attachment else '',
            'attachment_name': msg.attachment.name if msg.attachment else '',
        },
    )

    return JsonResponse({
        'ok': True,
        'id': msg.id,
        'message': msg.content,
        'attachment_url': msg.attachment.url if msg.attachment else '',
        'attachment_name': msg.attachment.name if msg.attachment else '',
        'timestamp': str(msg.timestamp),
        'username': msg.sender.username,
    })
