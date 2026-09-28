from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from modules.user.models import User
from modules.authentication.application.use_cases.check_password_reset_token import check_password_reset_token


class PasswordTokenCheck(GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            uidb64_decode, is_valid = check_password_reset_token(uidb64, token)

            if not is_valid:
                return Response({'error': 'Token is not valid, please request a new one'}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'success': True, 'message': 'Credentials valid', 'uidb64': uidb64_decode, 'token': token}, status=status.HTTP_200_OK)

        except (ValidationError, ValueError, User.DoesNotExist):
            return Response({'error': 'Token is not valid, please request a new one'}, status=status.HTTP_400_BAD_REQUEST)
