from django.apps import AppConfig


class UserProviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.provider'
    label = 'user_provider'
