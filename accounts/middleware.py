"""Middleware for accounts app."""

from django.utils import translation

from .models import User


class UserLanguageMiddleware:
    """
    Set Django's language from the authenticated user's preferred_language (EN/DE)
    so that the UI is shown in English or German. Runs after LocaleMiddleware so
    it overrides cookie/header language for logged-in users.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Read from DB so we always use the latest saved preference
            lang = User.objects.filter(pk=request.user.pk).values_list('preferred_language', flat=True).first()
            if lang == 'DE':
                translation.activate('de')
                request.LANGUAGE_CODE = 'de'
            elif lang in ('EN', 'OTHER'):
                translation.activate('en')
                request.LANGUAGE_CODE = 'en'
        response = self.get_response(request)
        return response
