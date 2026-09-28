import uuid
from unittest.mock import patch

from django.core import mail
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from modules.city.models import Country
from modules.provider.models import Provider, TypeId
from modules.user.models import User

VALID_REGISTRATION_PAYLOAD = {
    'email': 'newprovider@example.com',
    'password': 'pass12345',
    'provider': {
        'company': 'Acme Tours',
        'fullname': 'Acme Corp',
        'id_type': None,    # filled in per-test once a TypeId exists
        'id_number': '123456',
        'rnt': 'RNT001',
        'address': 'Main St 123',
        'phone': '3001234567',
        'country': None,    # filled in per-test once a Country exists
    },
}


def make_payload(type_id, country):
    payload = {
        'email': VALID_REGISTRATION_PAYLOAD['email'],
        'password': VALID_REGISTRATION_PAYLOAD['password'],
        'provider': dict(VALID_REGISTRATION_PAYLOAD['provider']),
    }
    payload['provider']['id_type'] = type_id.id
    payload['provider']['country'] = country.id
    return payload


def make_country():
    return Country.objects.create(name='Colombia', iso_country='CO')


class ProviderModelTests(TestCase):
    def test_provider_and_type_id_resolve_correctly(self):
        country = make_country()
        type_id = TypeId.objects.create(name='Cedula')
        user = User.objects.create_user(email='p1@example.com', password='pass12345')
        provider = Provider.objects.create(
            user=user, company='Acme', fullname='Acme Corp', id_number='1',
            rnt='R1', address='Addr', phone='300', id_type=type_id, country=country,
        )
        self.assertEqual(str(provider), str(user))
        self.assertEqual(provider.user_id, user.id)

    def test_app_label_is_user_provider(self):
        self.assertEqual(Provider._meta.app_label, 'user_provider')
        self.assertEqual(TypeId._meta.app_label, 'user_provider')

    def test_database_tables_unchanged(self):
        self.assertEqual(Provider._meta.db_table, 'provider')
        self.assertEqual(TypeId._meta.db_table, 'type_id')

    def test_provider_user_fk_is_plain_foreign_key_not_one_to_one(self):
        """
        Pins the existing (documented mismatch, preserved - see
        docs/migrations/provider.md 1.1/10 item 2) schema behavior: despite
        CLAUDE.md describing this as a 1:1 relationship, Provider.user is a
        plain ForeignKey. Multiple Providers per User are not prevented by
        the database. Not fixed by this migration.
        """
        field = Provider._meta.get_field('user')
        self.assertFalse(field.one_to_one)
        self.assertTrue(field.many_to_one)

    def test_id_type_uses_protect_on_delete(self):
        field = Provider._meta.get_field('id_type')
        from django.db.models import PROTECT
        self.assertIs(field.remote_field.on_delete, PROTECT)

    def test_country_fk_uses_protect_on_delete(self):
        field = Provider._meta.get_field('country')
        from django.db.models import PROTECT
        self.assertIs(field.remote_field.on_delete, PROTECT)

    def test_country_fk_points_to_city_country(self):
        from modules.city.models import Country as CityCountry
        field = Provider._meta.get_field('country')
        self.assertIs(field.related_model, CityCountry)

    def test_country_related_name_is_providers(self):
        field = Provider._meta.get_field('country')
        self.assertEqual(field.remote_field.related_name, 'providers')


class ProviderRegistrationTests(APITestCase):
    def setUp(self):
        self.type_id = TypeId.objects.create(name='Cedula')
        self.country = make_country()

    def test_successful_registration_creates_user_and_provider_and_returns_token(self):
        response = self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        user = User.objects.get(email='newprovider@example.com')
        self.assertFalse(user.is_verified)
        provider = Provider.objects.get(user=user)
        self.assertEqual(provider.company, 'Acme Tours')
        self.assertEqual(provider.country, self.country)

    def test_registration_sends_exactly_one_verification_email(self):
        self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, 'Verifica tu email - Viaja y Descubre')
        self.assertIn('/provider/email-verify/', sent.body)
        self.assertEqual(sent.to, ['newprovider@example.com'])

    def test_duplicate_email_returns_400_with_exact_message(self):
        self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        response = self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'There is already a registered user with this email'})

    def test_malformed_registration_fields_use_default_drf_400_shape(self):
        payload = make_payload(self.type_id, self.country)
        payload['email'] = 'not-an-email'
        response = self.client.post('/v1/affiliate/providers/signup/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_invalid_country_id_returns_400(self):
        payload = make_payload(self.type_id, self.country)
        payload['provider']['country'] = 999999
        response = self.client.post('/v1/affiliate/providers/signup/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_newly_registered_user_still_receives_token(self):
        """
        Pins the deliberate use of MyTokenObtainPairSerializer.get_token(user)
        directly (bypassing its .validate() method): a freshly-registered,
        unverified user still receives a real token pair from registration,
        which would NOT happen if .validate() were called instead (it would
        raise AuthenticationFailed for an unverified user). get_token() only
        builds claims (including 'role'); the email-verification gate lives
        solely in .validate(), which registration deliberately never calls.
        """
        response = self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email='newprovider@example.com')
        self.assertFalse(user.is_verified)
        self.assertIn('access', response.data)

    def test_registration_token_carries_role_claim(self):
        """
        Confirms register_provider() reuses MyTokenObtainPairSerializer.get_token()
        directly, so the registration-issued token carries the same 'role'
        claim a normal /v1/auth/login/ token would -- not just a bare
        access/refresh pair from the plain library serializer.
        """
        response = self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        decoded = AccessToken(response.data['access'])
        self.assertEqual(decoded['role'], 'user')
        self.assertIn('id', decoded)

    def test_registration_token_is_accepted_by_authentication_email_verification(self):
        """
        Verifies the cross-module contract documented in
        docs/migrations/provider.md 5 point 7 and required by this
        migration's instructions: the access token produced by Provider
        registration must still be accepted by
        modules.authentication.VerifyEmail as a valid email-verification
        token, end-to-end through the real HTTP routes of both modules.
        """
        registration_response = self.client.post(
            '/v1/affiliate/providers/signup/',
            make_payload(self.type_id, self.country),
            format='json',
        )
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
        access_token = registration_response.data['access']

        user = User.objects.get(email='newprovider@example.com')
        self.assertFalse(user.is_verified)

        verify_response = self.client.get(f'/v1/auth/email-verify/{access_token}/')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_response.data, {'success': 'User Successfully activated'})

        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_provider_creation_failure_does_not_leave_orphaned_user(self):
        """
        Simulates a Provider-persistence failure (any DB-level error, e.g. a
        constraint violation not caught by serializer validation) happening
        AFTER User.objects.create_user() has already run inside
        ProviderRegistrationSerializer.create(). Before the transaction-
        boundary fix, the User row was left committed (orphaned, unverified,
        no Provider) even though the request itself failed with a 400 --
        see docs/refactoring-audit.md P1 item. Response/status code
        unchanged: the view's existing `except IntegrityError` branch
        already produces this exact 400 regardless of which persistence
        step raised it.
        """
        with patch(
            'modules.provider.presentation.serializers.provider_registration_serializer.Provider.objects.create',
            side_effect=IntegrityError('simulated Provider persistence failure'),
        ):
            response = self.client.post(
                '/v1/affiliate/providers/signup/',
                make_payload(self.type_id, self.country),
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'There is already a registered user with this email'})
        self.assertFalse(User.objects.filter(email='newprovider@example.com').exists())

    def test_email_failure_does_not_roll_back_user_and_provider_persistence(self):
        """
        Explicit requirement: email sending must NOT be assumed to belong
        inside the transaction. A transient SMTP failure after User+Provider
        are already correctly persisted must not undo that persistence --
        unlike booking's reservation flow, where email failure is a
        separate, already-documented, deliberately-preserved issue (see
        docs/refactoring-audit.md P2 item on booking's PDF/email scope).
        """
        with patch(
            'modules.provider.application.use_cases.register_provider.send_email_to',
            side_effect=RuntimeError('SMTP down'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    '/v1/affiliate/providers/signup/',
                    make_payload(self.type_id, self.country),
                    format='json',
                )

        user = User.objects.get(email='newprovider@example.com')
        self.assertFalse(user.is_verified)
        self.assertTrue(Provider.objects.filter(user=user).exists())


class ProviderListTests(APITestCase):
    def setUp(self):
        self.country = make_country()
        self.type_id = TypeId.objects.create(name='Cedula')
        self.superuser = User.objects.create_superuser(email='admin@example.com', password='pass12345')
        self.owner = User.objects.create_user(email='owner@example.com', password='pass12345', is_verified=True)
        self.other = User.objects.create_user(email='other@example.com', password='pass12345', is_verified=True)
        self.owner_provider = Provider.objects.create(
            user=self.owner, company='Owner Co', fullname='Owner', id_number='1',
            rnt='R1', address='Addr', phone='300', id_type=self.type_id, country=self.country,
        )
        Provider.objects.create(
            user=self.other, company='Other Co', fullname='Other', id_number='2',
            rnt='R2', address='Addr', phone='300', id_type=self.type_id, country=self.country,
        )

    def test_unauthenticated_is_rejected(self):
        response = self.client.get('/v1/affiliate/providers/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superuser_sees_all_providers(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/v1/affiliate/providers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_regular_user_sees_only_own_provider(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/v1/affiliate/providers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['company'], 'Owner Co')

    def test_response_includes_country_id(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/v1/affiliate/providers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]
        self.assertIn('country', result)
        self.assertEqual(result['country'], self.country.id)

    def test_company_filter(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/v1/affiliate/providers/', {'company': 'Owner'})
        self.assertEqual(response.data['count'], 1)

    def test_pagination_page_size_is_15(self):
        for i in range(20):
            user = User.objects.create_user(email=f'bulk{i}@example.com', password='pass12345')
            Provider.objects.create(
                user=user, company=f'Bulk {i}', fullname='X', id_number=str(i),
                rnt='R', address='Addr', phone='300', id_type=self.type_id, country=self.country,
            )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/v1/affiliate/providers/')
        self.assertEqual(len(response.data['results']), 15)
        self.assertEqual(response.data['count'], 22)

    def test_pagination_uses_shared_custom_pagination_class(self):
        from modules.provider.presentation.views.provider_list import CustomPagination
        from shared.pagination import CustomPagination as SharedCustomPagination
        self.assertIs(CustomPagination, SharedCustomPagination)
        self.assertEqual(CustomPagination.page_size, 15)


class ProviderDetailTests(APITestCase):
    def setUp(self):
        self.country = make_country()
        self.type_id = TypeId.objects.create(name='Cedula')
        self.owner = User.objects.create_user(email='owner2@example.com', password='pass12345', is_verified=True)
        self.other = User.objects.create_user(email='other2@example.com', password='pass12345', is_verified=True)
        self.provider = Provider.objects.create(
            user=self.owner, company='Owner Co', fullname='Owner', id_number='1',
            rnt='R1', address='Addr', phone='300', id_type=self.type_id, country=self.country,
        )

    def test_owner_can_get(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/v1/affiliate/providers/{self.provider.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company'], 'Owner Co')

    def test_get_response_includes_country_id(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/v1/affiliate/providers/{self.provider.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('country', response.data)
        self.assertEqual(response.data['country'], self.country.id)

    def test_non_owner_get_is_forbidden(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f'/v1/affiliate/providers/{self.provider.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_id_get_returns_404(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/v1/affiliate/providers/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Not found'})

    def test_owner_can_update(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.put(
            f'/v1/affiliate/providers/{self.provider.id}/',
            {
                'company': 'Updated Co', 'fullname': 'Owner', 'id_type': self.type_id.id,
                'id_number': '1', 'rnt': 'R1', 'address': 'Addr', 'phone': '300',
                'country': self.country.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.company, 'Updated Co')

    def test_update_with_invalid_country_id_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.put(
            f'/v1/affiliate/providers/{self.provider.id}/',
            {
                'company': 'Updated Co', 'fullname': 'Owner', 'id_type': self.type_id.id,
                'id_number': '1', 'rnt': 'R1', 'address': 'Addr', 'phone': '300',
                'country': 999999,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_changes_country(self):
        ecuador = Country.objects.create(name='Ecuador', iso_country='EC')
        self.client.force_authenticate(user=self.owner)
        response = self.client.put(
            f'/v1/affiliate/providers/{self.provider.id}/',
            {
                'company': 'Owner Co', 'fullname': 'Owner', 'id_type': self.type_id.id,
                'id_number': '1', 'rnt': 'R1', 'address': 'Addr', 'phone': '300',
                'country': ecuador.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.country_id, ecuador.id)

    def test_current_behavior_unknown_id_put_is_unhandled_500(self):
        """
        Pins the existing asymmetric-guard behavior documented in
        docs/migrations/provider.md 1.5/10 item 3 (same shape as
        city.DestinationDetailProv): get() catches Provider.DoesNotExist,
        put() does not. Not fixed by this migration.
        """
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user=self.owner)
        response = client.put(
            f'/v1/affiliate/providers/{uuid.uuid4()}/',
            {
                'company': 'X', 'fullname': 'X', 'id_type': self.type_id.id,
                'id_number': '1', 'rnt': 'R1', 'address': 'Addr', 'phone': '300',
                'country': self.country.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
