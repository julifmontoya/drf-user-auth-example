from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField
from modules.provider.models import Provider, TypeId


class ProviderSerializer(serializers.ModelSerializer):
    address = serializers.CharField(max_length=100, min_length=3)
    phone = serializers.CharField(max_length=15, min_length=3)
    fullname = serializers.CharField(max_length=100, min_length=3)
    company = serializers.CharField(max_length=100, min_length=3)
    id_type = PrimaryKeyRelatedField(queryset=TypeId.objects.all())

    class Meta:
        model = Provider
        fields = [
            'id',
            'company',
            'fullname',
            'id_type',
            'id_number',
            'rnt',
            'address',
            'phone',
        ]

