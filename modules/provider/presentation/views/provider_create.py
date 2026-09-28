from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from modules.provider.presentation.serializers.provider_registration_serializer import ProviderRegistrationSerializer
from modules.provider.application.use_cases.register_provider import register_provider


class ProviderCreate(CreateAPIView):
    serializer_class = ProviderRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = register_provider(serializer)
            return Response(token, status=status.HTTP_201_CREATED)

        except IntegrityError:
            return Response({'error': 'There is already a registered user with this email'}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
