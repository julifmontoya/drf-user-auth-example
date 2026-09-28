from rest_framework import serializers
from modules.provider.models import Provider
from modules.user.models import User
from modules.provider.presentation.serializers.provider_serializer import ProviderSerializer


class ProviderRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, min_length=3)
    password = serializers.CharField(max_length=20, min_length=6, write_only=True)
    provider = ProviderSerializer(many=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'provider']

    def create(self, validated_data):
        provider_data = validated_data.pop('provider')
        user = User.objects.create_user(**validated_data)
        Provider.objects.create(user=user, **provider_data)
        return user
