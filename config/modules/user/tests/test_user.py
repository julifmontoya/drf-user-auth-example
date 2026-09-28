from django.contrib import admin
from django.test import TestCase

from modules.user.models import User


class UserManagerTests(TestCase):
    def test_create_user_sets_email_and_hashes_password(self):
        user = User.objects.create_user(email='jane@example.com', password='pass12345')
        self.assertEqual(user.email, 'jane@example.com')
        self.assertTrue(user.check_password('pass12345'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_verified)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pass12345')

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser(email='admin@example.com', password='pass12345')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_without_password_raises(self):
        with self.assertRaises(TypeError):
            User.objects.create_superuser(email='admin2@example.com', password=None)


class UserModelTests(TestCase):
    def test_str_returns_email(self):
        user = User.objects.create_user(email='jane@example.com', password='pass12345')
        self.assertEqual(str(user), 'jane@example.com')

    def test_db_table_is_unchanged(self):
        self.assertEqual(User._meta.db_table, 'user')

    def test_username_field_and_required_fields_unchanged(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertEqual(User.REQUIRED_FIELDS, [])

    def test_email_is_unique(self):
        from django.db import IntegrityError
        User.objects.create_user(email='dup@example.com', password='pass12345')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='dup@example.com', password='pass12345')

    def test_app_label_is_user_not_modules_user(self):
        self.assertEqual(User._meta.app_label, 'user')


class UserAdminTests(TestCase):
    def test_user_model_registered_in_admin(self):
        self.assertIn(User, admin.site._registry)
