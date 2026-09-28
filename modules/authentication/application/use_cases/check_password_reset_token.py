import base64
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from modules.user.models import User


def check_password_reset_token(uidb64, token):
    """
    Verbatim relocation of PasswordTokenCheck.get's workflow -- see
    docs/migrations/user-authentication.md 1.5.

    Raises:
        ValueError: malformed base64 uidb64 (propagates unhandled here, the
            caller maps it to a response, exactly as the original view did).
        modules.user.models.User.DoesNotExist: decoded uidb64 doesn't match
            a real user.

    Returns:
        (uidb64_decode, is_valid): the decoded uid string and whether the
        token is currently valid for that user.
    """
    uidb64_decode = base64.urlsafe_b64decode(uidb64.encode()).decode()

    user = User.objects.get(id=uidb64_decode)
    is_valid = PasswordResetTokenGenerator().check_token(user, token)
    return uidb64_decode, is_valid
