from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
    })


@login_required
def view_notification(request, pk):
    """Mark notification as read and redirect to its link (e.g. course) or back to list."""
    notification = get_object_or_404(
        Notification, pk=pk, recipient=request.user,
    )
    notification.read = True
    notification.save(update_fields=['read'])
    if notification.link_url:
        return redirect(notification.link_url)
    messages.success(request, 'Notification marked as read.')
    return redirect('notifications:notification_list')


@login_required
def mark_read(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    notification = get_object_or_404(
        Notification, pk=pk, recipient=request.user,
    )
    notification.read = True
    notification.save()
    messages.success(request, 'Notification marked as read.')
    return redirect('notifications:notification_list')


@login_required
def mark_all_read(request):
    if request.method != 'POST':
        return HttpResponseForbidden("POST method required.")

    Notification.objects.filter(
        recipient=request.user, read=False,
    ).update(read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:notification_list')
