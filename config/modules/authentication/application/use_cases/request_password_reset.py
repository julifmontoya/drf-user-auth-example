from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from decouple import config

from modules.user.models import User
from shared.notifications.email import send_email_to

# NOTE: uses shared.notifications.email.send_email_to (variable recipient),
# not send_email (fixed recipient, suited to contact-form notifications) --
# see docs/shared-extraction-audit.md 5.1.


def request_password_reset(email):
    """
    Verbatim relocation of SendResetEmail.post's workflow -- see
    docs/migrations/user-authentication.md 1.5.

    Raises:
        django.http.Http404: no user with this email (via get_object_or_404,
            preserved exactly -- this leaks account existence, a known V2
            issue, not fixed here).
    """
    user = get_object_or_404(User, email=email)
    uidb64 = urlsafe_base64_encode(force_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)

    ## Test Postman
    ## relative_link = reverse('reset-password', kwargs={'uidb64': uidb64, 'token': token})
    ## url = config('HOST_BACK') + relative_link

    url = config('HOST_FRONT') + '/provider/reset-password/' + str(uidb64) + '/' + token + '/'

    email_subject = 'Cambia tu contraseña - Viaja y Descubre'
    email_body = f'Hola,\nUsa el siguiente enlace para cambiar tu contraseña:\n{url}\n\nFelipe Montoya\nViaja y Descubre\n3128663738'
    send_email_to(email, email_subject, email_body)
