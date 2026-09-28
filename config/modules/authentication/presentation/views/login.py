from rest_framework_simplejwt.views import TokenObtainPairView
from modules.authentication.presentation.serializers.token_obtain_pair_serializer import MyTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
