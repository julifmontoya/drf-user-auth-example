from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
import uuid

from shared.initials import generate_initials


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        """Create and return a `User` with an email, username and password."""
        if not email:
            raise ValueError('Users Must Have an email address')
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """Create and return a `User` with superuser (admin) permissions."""
        if password is None:
            raise TypeError('Superusers must have a password.')
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, unique=True,primary_key=True, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # Tells Django that the UserManager class defined above should manage
    objects = UserManager()

    def __str__(self):
        return self.email

    def get_initials(self):
        """Best-effort initials for lightweight UI use (e.g. JWT claims).

        User itself has no name fields, so this is sourced from the related
        Provider's `fullname` when one exists; returns '' rather than
        raising when there's no name information available (e.g. a
        non-provider user).
        """
        provider = self.provider_set.first()
        return generate_initials(provider.fullname if provider else '')

    class Meta:
        db_table = "user"