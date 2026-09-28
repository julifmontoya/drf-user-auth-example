from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from modules.authentication.presentation.serializers.reset_password_email_request_serializer import ResetPasswordEmailRequestSerializer
from modules.authentication.application.use_cases.request_password_reset import request_password_reset


class SendResetEmail(GenericAPIView):
    serializer_class = ResetPasswordEmailRequestSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        request_password_reset(email)
        return Response({'success': 'We have sent you a link to reset your password'}, status=status.HTTP_200_OK)
