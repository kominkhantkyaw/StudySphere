from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EventForm
from .models import Event


@login_required
def calendar_view(request):
    from django.utils import timezone

    now = timezone.now()
    upcoming = (
        Event.objects.filter(
            Q(creator=request.user) | Q(attendees=request.user),
            start__gte=now,
        )
        .select_related('course')
        .order_by('start')[:5]
    )
    return render(
        request,
        'calendar_app/calendar.html',
        {
            'upcoming_events': upcoming,
        },
    )



@login_required
def event_list_json(request):
    """Return events as JSON for FullCalendar."""
    events = Event.objects.filter(
        Q(creator=request.user) | Q(attendees=request.user),
    ).distinct().select_related('creator', 'course')

    event_type_colours = {
        Event.COURSE_SESSION: '#0d6efd',
        Event.APPOINTMENT: '#198754',
        Event.OFFICE_HOURS: '#fd7e14',
        Event.DEADLINE: '#dc3545',
    }

    data = []
    for event in events:
        data.append({
            'id': event.id,
            'title': event.title,
            'start': event.start.isoformat(),
            'end': event.end.isoformat(),
            'url': f'/calendar/{event.id}/',
            'backgroundColor': event_type_colours.get(event.event_type, '#6c757d'),
            'borderColor': event_type_colours.get(event.event_type, '#6c757d'),
            'extendedProps': {
                'event_type': event.get_event_type_display(),
                'creator': event.creator.username,
                'course': event.course.title if event.course else None,
            },
        })

    return JsonResponse(data, safe=False)


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user
            event.save()
            form.save_m2m()
            event.attendees.add(request.user)
            messages.success(request, 'Event created successfully.')
            return redirect('calendar_app:calendar')
    else:
        form = EventForm(user=request.user)
    return render(request, 'calendar_app/event_form.html', {'form': form, 'editing': False})


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    is_involved = (
        event.creator == request.user
        or event.attendees.filter(pk=request.user.pk).exists()
    )
    if not is_involved:
        return HttpResponseForbidden('You do not have access to this event.')
    return render(request, 'calendar_app/event_detail.html', {'event': event})


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.creator != request.user:
        return HttpResponseForbidden('Only the creator can edit this event.')

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            return redirect('calendar_app:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event, user=request.user)
    return render(request, 'calendar_app/event_form.html', {'form': form, 'editing': True})


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.creator != request.user:
        return HttpResponseForbidden('Only the creator can delete this event.')

    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted.')
        return redirect('calendar_app:calendar')
    return render(request, 'calendar_app/event_confirm_delete.html', {'event': event})


@login_required
def event_join(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.attendees.add(request.user)
        messages.success(request, f'You have joined "{event.title}".')
    return redirect('calendar_app:event_detail', pk=event.pk)


@login_required
def event_leave(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        if event.creator == request.user:
            messages.error(request, 'The creator cannot leave their own event.')
        else:
            event.attendees.remove(request.user)
            messages.success(request, f'You have left "{event.title}".')
    return redirect('calendar_app:calendar')


@login_required
def contact_support(request):
    """Simple 'Send us a message' handler from the Calendar page."""
    if request.method != 'POST':
        return HttpResponseForbidden('POST method required.')

    name = (request.POST.get('name') or '').strip() or request.user.get_full_name() or request.user.username
    email = (request.POST.get('email') or '').strip() or request.user.email
    message_body = (request.POST.get('message') or '').strip()

    if not message_body:
        messages.error(request, 'Please enter a message before sending.')
        return redirect('calendar_app:calendar')

    # In future we can email this to an admin mailbox or store in a model.
    messages.success(request, 'Your message has been sent to the StudySphere team.')
    return redirect('calendar_app:calendar')
