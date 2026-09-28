from django.conf import settings
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
import time

from modules.user.models import User


class ActivationExpired(Exception):
    """Raised when the manual expiry check (see note below) fails."""


def verify_email(token):
    """
    Verbatim relocation of VerifyEmail.get's workflow -- see
    docs/migrations/user-authentication.md 1.5.

    NOTE (preserved exactly, not fixed - see docs/migrations/user-authentication.md
    9 item 1): `exp` is a Unix timestamp in seconds (the JWT `exp` claim),
    while `now` is computed in milliseconds. This means `now > exp` is
    effectively always True, and the "Activation Expired" branch below is
    practically unreachable in production. This is existing, load-bearing
    behavior and must not be corrected in V1.

    Raises:
        rest_framework_simplejwt.exceptions.TokenBackendError: token cannot
            be decoded.
        ActivationExpired: the (broken) manual expiry check's else branch.
        modules.user.models.User.DoesNotExist: token's `id` claim does not
            match a real user -- intentionally left unhandled here, exactly
            as in the original view (see docs/migrations/user-authentication.md
            9 item 2).

    Returns:
        (user, already_active): the User instance and whether it was already
        verified before this call.
    """
    tokenBackend = TokenBackend(algorithm=settings.SIMPLE_JWT['ALGORITHM'])
    valid_data = tokenBackend.decode(token, verify=False)
    exp = valid_data['exp']
    now = int(time.time() * 1000)

    if (now > exp):
        user = User.objects.get(id=valid_data['id'])
        if not user.is_verified:
            user.is_verified = True
            user.save()
            return user, False
        return user, True
    else:
        raise ActivationExpired()
