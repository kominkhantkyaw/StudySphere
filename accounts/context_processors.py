"""Template context processors for accounts app."""

from django.contrib.messages import get_messages

from .models import User


def messages_as_list(request):
    """Expose messages as a list so templates can safely iterate without .count() on storage."""
    return {'messages': list(get_messages(request))}


def theme_mode(request):
    """Expose the current user's theme preference for Light/Dark/System mode.
    Reads from the database so the value is always up to date after saving in Settings.
    """
    if request.user.is_authenticated:
        try:
            # Refetch from DB so we never use a cached in-memory value (e.g. after changing theme in Settings)
            mode = User.objects.filter(pk=request.user.pk).values_list('theme_mode', flat=True).first()
            if mode:
                return {'theme_mode': mode.lower()}
        except Exception:
            pass
    return {'theme_mode': 'light'}
