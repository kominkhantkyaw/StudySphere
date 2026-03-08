"""
Middleware to fix session key used by django_otp.

Our 2FA setup flow previously stored device.id (int) in 'otp_device_id';
django_otp expects device.persistent_id (str). This middleware removes the
invalid int value so the OTP middleware does not crash (existing sessions only).
"""

from django_otp import DEVICE_ID_SESSION_KEY


class OTPSessionFixMiddleware:
    """Remove otp_device_id from session when it is an int (legacy bug)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        val = request.session.get(DEVICE_ID_SESSION_KEY)
        if isinstance(val, int):
            request.session.pop(DEVICE_ID_SESSION_KEY, None)
        return self.get_response(request)
