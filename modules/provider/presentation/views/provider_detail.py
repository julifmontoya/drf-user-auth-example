from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from modules.provider.models import Provider
from modules.provider.presentation.serializers.provider_serializer import ProviderSerializer
from shared.permissions import IsVerified
from shared.permissions import has_permission


class ProviderDetail(APIView):
    permission_classes = (IsAuthenticated, IsVerified,)

    def get(self, request, id):
        try:
            provider = Provider.objects.get(id=id)
            user = self.request.user

            has_permission(provider.user, user)
            serializer = ProviderSerializer(provider)
            return Response(serializer.data)

        except Provider.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, id):
        provider = Provider.objects.get(id=id)
        user = self.request.user

        has_permission(provider.user, user)
        serializer = ProviderSerializer(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
