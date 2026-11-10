from rest_framework.throttling import SimpleRateThrottle


class BaseScopedThrottle(SimpleRateThrottle):
    """
    Applies a separate rate limit to each API scope.
    Authenticated users are identified by user ID.
    Anonymous users are identified by IP address.
    """

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class RegisterRateThrottle(BaseScopedThrottle):
    scope = "register"


class OTPRateThrottle(BaseScopedThrottle):
    scope = "otp"


class LoginRateThrottle(BaseScopedThrottle):
    scope = "login"


class ResendOTPThrottle(BaseScopedThrottle):
    scope = "resend_otp"


class DeleteRegistrationThrottle(BaseScopedThrottle):
    scope = "delete_registration"


class EventRegisterThrottle(BaseScopedThrottle):
    scope = "event_register"


class EventListThrottle(BaseScopedThrottle):
    scope = "event_list"


class EventDetailsThrottle(BaseScopedThrottle):
    scope = "event_details"


class QRThrottle(BaseScopedThrottle):
    scope = "qr"


class AttendanceLookupThrottle(BaseScopedThrottle):
    scope = "attendance_lookup"


class AttendanceMarkThrottle(BaseScopedThrottle):
    scope = "attendance_mark"