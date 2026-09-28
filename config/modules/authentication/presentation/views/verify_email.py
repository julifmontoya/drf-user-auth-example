from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenBackendError
from modules.authentication.application.use_cases.verify_email import verify_email, ActivationExpired


class VerifyEmail(APIView):
    def get(self, request, **kwargs):
        token = kwargs.get('token')

        try:
            user, already_active = verify_email(token)

            if already_active:
                return Response({'success': 'User has been previously activated'}, status=status.HTTP_200_OK)
            return Response({'success': 'User Successfully activated'}, status=status.HTTP_200_OK)

        except ActivationExpired:
            return Response({'error': 'Activation Expired'}, status=status.HTTP_400_BAD_REQUEST)

        except TokenBackendError:
            return Response({'error': 'Invalid'}, status=status.HTTP_400_BAD_REQUEST)
