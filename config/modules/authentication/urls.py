from django.urls import path
from modules.authentication.presentation.views.login import LoginView
from modules.authentication.presentation.views.blacklist_refresh import BlacklistRefreshView
from modules.authentication.presentation.views.verify_email import VerifyEmail
from modules.authentication.presentation.views.send_reset_email import SendResetEmail
from modules.authentication.presentation.views.password_token_check import PasswordTokenCheck
from modules.authentication.presentation.views.set_new_password import SetNewPassword
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('logout/', BlacklistRefreshView.as_view()),
    path('email-verify/<token>/', VerifyEmail.as_view(), name='email-verify'),
    path('password-reset/', SendResetEmail.as_view()),
    path('password-reset/complete/', SetNewPassword.as_view()),
    path('password-reset/<uidb64>/<token>/', PasswordTokenCheck.as_view(), name='reset-password'),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('token/verify/', TokenVerifyView.as_view()),
]
