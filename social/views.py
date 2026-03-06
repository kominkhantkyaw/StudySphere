from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from courses.models import Course

from .forms import StatusUpdateForm
from .models import StatusUpdate, StatusReaction


@login_required
def post_status(request):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    form = StatusUpdateForm(request.POST, request.FILES)
    if form.is_valid():
        status = form.save(commit=False)
        status.user = request.user
        status.save()
        messages.success(request, 'Status posted successfully.')
    else:
        messages.error(request, 'Failed to post status.')

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def delete_status(request, status_id):
    """Allow the sender (or staff/admin) to delete a status update and its attachment."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    status = get_object_or_404(StatusUpdate, pk=status_id)
    user = request.user

    if not (status.user == user or user.is_staff or user.is_superuser):
        return HttpResponseForbidden("You do not have permission to delete this update.")

    # Remove attachment file from storage if present
    if status.attachment:
        status.attachment.delete(save=False)

    status.delete()
    messages.success(request, 'Status deleted successfully.')

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def edit_status(request, status_id):
    """Allow the sender (or staff/admin) to edit the text of a status update."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    status = get_object_or_404(StatusUpdate, pk=status_id)
    user = request.user

    if not (status.user == user or user.is_staff or user.is_superuser):
        return HttpResponseForbidden("You do not have permission to edit this update.")

    new_content = (request.POST.get('content') or '').strip()
    if not new_content:
        messages.error(request, 'Content cannot be empty.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    status.content = new_content
    status.save(update_fields=['content'])
    messages.success(request, 'Status updated successfully.')

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def add_status_reaction(request, status_id):
    """Add or update emoji reaction on a status. Broadcasts to General room so everyone sees it."""
    status = get_object_or_404(StatusUpdate, pk=status_id)
    emoji = (request.POST.get('emoji') or '').strip()[:20]
    if not emoji:
        return JsonResponse({'ok': False, 'error': 'Emoji required.'}, status=400)

    reaction, _ = StatusReaction.objects.update_or_create(
        status=status,
        user=request.user,
        defaults={'emoji': emoji},
    )

    general_room = Course.objects.filter(is_general=True).first()
    if general_room:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{general_room.id}',
            {
                'type': 'status.reaction',
                'status_id': status_id,
                'emoji': emoji,
                'username': request.user.username,
            },
        )

    return JsonResponse({'ok': True, 'emoji': emoji})


@login_required
def status_feed(request):
    """Activity feed: available to all authenticated users (teachers and students)."""
    updates = StatusUpdate.objects.select_related('user').all()
    paginator = Paginator(updates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = StatusUpdateForm()
    return render(request, 'social/feed.html', {
        'statuses': page_obj,
        'form': form,
    })
