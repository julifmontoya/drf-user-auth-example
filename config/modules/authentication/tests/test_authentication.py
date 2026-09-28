from django.core import mail
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from modules.user.models import User


class LoginTests(APITestCase):
    def test_verified_user_can_login(self):
        User.objects.create_user(email='verified@example.com', password='pass12345', is_verified=True)
        response = self.client.post('/v1/auth/login/', {'email': 'verified@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_unverified_regular_user_is_blocked(self):
        User.objects.create_user(email='unverified@example.com', password='pass12345', is_verified=False)
        response = self.client.post('/v1/auth/login/', {'email': 'unverified@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Email is not verified')

    def test_superuser_bypasses_is_verified_check(self):
        User.objects.create_superuser(email='admin@example.com', password='pass12345')
        response = self.client.post('/v1/auth/login/', {'email': 'admin@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_access_token_carries_user_role_for_non_superuser(self):
        User.objects.create_user(email='roleuser@example.com', password='pass12345', is_verified=True)
        response = self.client.post('/v1/auth/login/', {'email': 'roleuser@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['role'], 'user')
        self.assertIn('id', decoded)

    def test_access_token_carries_admin_role_for_superuser(self):
        User.objects.create_superuser(email='roleadmin@example.com', password='pass12345')
        response = self.client.post('/v1/auth/login/', {'email': 'roleadmin@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['role'], 'admin')

    def test_refresh_token_also_carries_role_claim(self):
        User.objects.create_user(email='rolerefresh@example.com', password='pass12345', is_verified=True)
        response = self.client.post('/v1/auth/login/', {'email': 'rolerefresh@example.com', 'password': 'pass12345'})
        refresh_response = self.client.post('/v1/auth/token/refresh/', {'refresh': response.data['refresh']})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        decoded = AccessToken(refresh_response.data['access'])
        self.assertEqual(decoded['role'], 'user')

    def test_access_token_carries_email_claim(self):
        User.objects.create_user(email='emailclaim@example.com', password='pass12345', is_verified=True)
        response = self.client.post('/v1/auth/login/', {'email': 'emailclaim@example.com', 'password': 'pass12345'})
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['email'], 'emailclaim@example.com')

    def test_access_token_initials_are_blank_for_user_with_no_provider_profile(self):
        User.objects.create_user(email='noname@example.com', password='pass12345', is_verified=True)
        response = self.client.post('/v1/auth/login/', {'email': 'noname@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['initials'], '')

    def test_access_token_initials_derived_from_provider_fullname(self):
        from modules.provider.models import Provider

        user = User.objects.create_user(email='provider@example.com', password='pass12345', is_verified=True)
        Provider.objects.create(
            user=user,
            company='Acme Tours',
            fullname='Julian Felipe Montoya',
            id_number='123',
            rnt='RNT1',
            address='Street 1',
            phone='3000000000',
        )
        response = self.client.post('/v1/auth/login/', {'email': 'provider@example.com', 'password': 'pass12345'})
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['initials'], 'JF')

    def test_access_token_generation_does_not_crash_for_blank_provider_fullname(self):
        from modules.provider.models import Provider

        user = User.objects.create_user(email='blankname@example.com', password='pass12345', is_verified=True)
        Provider.objects.create(
            user=user,
            company='Acme Tours',
            fullname='',
            id_number='123',
            rnt='RNT2',
            address='Street 1',
            phone='3000000000',
        )
        response = self.client.post('/v1/auth/login/', {'email': 'blankname@example.com', 'password': 'pass12345'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['initials'], '')


class VerifyEmailTests(APITestCase):
    def _token_for(self, user, exp):
        from rest_framework_simplejwt.tokens import AccessToken
        access = AccessToken.for_user(user)
        access['exp'] = exp
        return str(access)

    def test_valid_fresh_token_activates_user(self):
        user = User.objects.create_user(email='new@example.com', password='pass12345', is_verified=False)
        import time
        token = self._token_for(user, exp=int(time.time()) + 7200)

        response = self.client.get(f'/v1/auth/email-verify/{token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'success': 'User Successfully activated'})
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_already_verified_user_returns_previously_activated_message(self):
        user = User.objects.create_user(email='already@example.com', password='pass12345', is_verified=True)
        import time
        token = self._token_for(user, exp=int(time.time()) + 7200)

        response = self.client.get(f'/v1/auth/email-verify/{token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'success': 'User has been previously activated'})

    def test_current_behavior_a_token_expired_since_1970_still_activates(self):
        """
        Pins the existing (broken, preserved - see docs/migrations/
        user-authentication.md 1.5) millisecond/second unit-mismatch bug:
        `now` is computed in milliseconds while `exp` is a real seconds-based
        JWT claim, so `now > exp` is effectively always True. A token whose
        `exp` claim is 1 (i.e. expired since 1970-01-01T00:00:01Z, about as
        expired as a token can be) STILL takes the "activate" branch instead
        of "Activation Expired". Not fixed by this migration.
        """
        user = User.objects.create_user(email='longexpired@example.com', password='pass12345', is_verified=False)
        token = self._token_for(user, exp=1)

        response = self.client.get(f'/v1/auth/email-verify/{token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'success': 'User Successfully activated'})
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_malformed_token_returns_400_invalid(self):
        response = self.client.get('/v1/auth/email-verify/not-a-real-token/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid'})

    def test_current_behavior_unknown_user_id_in_token_is_unhandled_500(self):
        """
        Pins existing behavior documented in docs/migrations/
        user-authentication.md 1.5/9 item 2: User.DoesNotExist is not
        caught, unlike TokenBackendError. Not fixed by this migration.
        """
        import uuid
        from rest_framework_simplejwt.tokens import AccessToken
        throwaway_user = User.objects.create_user(email='throwaway@example.com', password='pass12345')
        access = AccessToken.for_user(throwaway_user)
        access['id'] = str(uuid.uuid4())  # overwrite with an id that matches no real user
        token = str(access)

        client = APIClient(raise_request_exception=False)
        response = client.get(f'/v1/auth/email-verify/{token}/')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendResetEmailTests(APITestCase):
    def test_known_email_sends_reset_link_and_returns_200(self):
        User.objects.create_user(email='reset@example.com', password='pass12345')
        response = self.client.post('/v1/auth/password-reset/', {'email': 'reset@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'success': 'We have sent you a link to reset your password'})

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, 'Cambia tu contraseña - Viaja y Descubre')
        self.assertIn('/provider/reset-password/', sent.body)
        self.assertEqual(sent.to, ['reset@example.com'])

    def test_current_behavior_unknown_email_returns_404_account_enumeration(self):
        """
        Pins the existing (preserved, not fixed - see docs/migrations/
        user-authentication.md 9 item 3) account-enumeration behavior: an
        unknown email returns 404, a known email returns 200 - the client
        can distinguish which. Not fixed by this migration.
        """
        response = self.client.post('/v1/auth/password-reset/', {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(mail.outbox), 0)


class PasswordTokenCheckTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='reset2@example.com', password='pass12345')
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.id))
        self.token = PasswordResetTokenGenerator().make_token(self.user)

    def test_valid_token_returns_200_with_echoed_uidb64_and_token(self):
        response = self.client.get(f'/v1/auth/password-reset/{self.uidb64}/{self.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uidb64'], str(self.user.id))
        self.assertEqual(response.data['token'], self.token)

    def test_invalid_but_decodable_token_returns_401(self):
        response = self.client.get(f'/v1/auth/password-reset/{self.uidb64}/wrong-token/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {'error': 'Token is not valid, please request a new one'})

    def test_malformed_uidb64_returns_400(self):
        response = self.client.get(f'/v1/auth/password-reset/not-valid-base64!!!/{self.token}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Token is not valid, please request a new one'})

    def test_current_behavior_decodable_non_uuid_uidb64_is_unhandled_500(self):
        """
        Newly-confirmed-during-implementation nuance (not previously called
        out explicitly in docs/migrations/user-authentication.md): the view
        catches `rest_framework.exceptions.ValidationError`, but
        User.objects.get(id=<non-UUID string>) raises Django's OWN
        `django.core.exceptions.ValidationError` for an invalid UUID lookup
        - a different class with the same name (confirmed: the two classes
        share no inheritance relationship). It is NOT caught, so a
        syntactically-valid-base64 uidb64 that decodes to a non-UUID-shaped
        string produces an unhandled 500, not the graceful 400 the except
        clause appears to promise. Preserved exactly, not fixed.

        Note: must use raw (padded) base64, not Django's urlsafe_base64_encode
        (which strips padding). A short, non-36-byte payload like this needs
        padding that Django's helper strips - raw stdlib
        base64.urlsafe_b64decode (what the view actually uses) requires it
        present, so an unpadded value here would trip an earlier, different,
        already-handled binascii.Error (a ValueError subclass) instead of
        reaching the User.objects.get() call this test targets. Real uidb64
        values are unaffected either way since a 36-character UUID string
        happens to base64-encode to a padding-free length.
        """
        import base64
        decodable_non_uuid = base64.urlsafe_b64encode(b'not-a-uuid').decode()
        client = APIClient(raise_request_exception=False)
        response = client.get(f'/v1/auth/password-reset/{decodable_non_uuid}/{self.token}/')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetNewPasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='reset3@example.com', password='oldpassword')
        self.uidb64 = str(self.user.id)
        self.token = PasswordResetTokenGenerator().make_token(self.user)

    def test_valid_token_changes_password_and_returns_200(self):
        response = self.client.patch(
            '/v1/auth/password-reset/complete/',
            {'password': 'newpassword1', 'token': self.token, 'uidb64': self.uidb64},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'success': True, 'message': 'Password reset success'})

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword1'))

    def test_invalid_token_returns_401_authentication_failed(self):
        response = self.client.patch(
            '/v1/auth/password-reset/complete/',
            {'password': 'newpassword1', 'token': 'bad-token', 'uidb64': self.uidb64},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'The reset link is invalid')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword'))


class BlacklistRefreshViewTests(APITestCase):
    def test_valid_refresh_token_is_blacklisted(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        user = User.objects.create_user(email='logout@example.com', password='pass12345', is_verified=True)
        refresh = RefreshToken.for_user(user)
        jti = refresh['jti']

        response = self.client.post('/v1/auth/logout/', {'refresh': str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, 'Success')

        self.assertTrue(BlacklistedToken.objects.filter(token__jti=jti).exists())

    def test_no_authentication_required(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        user = User.objects.create_user(email='logout2@example.com', password='pass12345', is_verified=True)
        refresh = RefreshToken.for_user(user)
        response = self.client.post('/v1/auth/logout/', {'refresh': str(refresh)})
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_behavior_malformed_refresh_token_is_unhandled_500(self):
        """
        Pins existing behavior documented in docs/migrations/
        user-authentication.md 1.5/9 item 5: RefreshToken(...)/.blacklist()
        are unguarded. Not fixed by this migration.
        """
        client = APIClient(raise_request_exception=False)
        response = client.post('/v1/auth/logout/', {'refresh': 'not-a-real-token'})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
