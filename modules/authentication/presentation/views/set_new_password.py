from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from modules.authentication.presentation.serializers.set_new_password_serializer import SetNewPasswordSerializer
from modules.authentication.application.use_cases.reset_password import reset_password


class SetNewPassword(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        reset_password(request.data)
        return Response({'success': True, 'message': 'Password reset success'}, status=status.HTTP_200_OK)
