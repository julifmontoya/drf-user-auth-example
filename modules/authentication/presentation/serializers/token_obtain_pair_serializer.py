from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = 'admin' if user.is_superuser else 'user'
        token['email'] = user.email
        token['initials'] = user.get_initials()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['message'] = 'User login  successfully'
        token = self.get_token(self.user)

        if self.user.is_superuser:
            return data
        elif not self.user.is_verified:
            raise AuthenticationFailed('Email is not verified')
        else:
            return data
