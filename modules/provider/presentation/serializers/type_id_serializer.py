from rest_framework import serializers
from modules.provider.models import TypeId


class TypeIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeId
        fields = ['id']
