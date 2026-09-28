from django.urls import path
from modules.provider.presentation.views.provider_create import ProviderCreate
from modules.provider.presentation.views.provider_list import ProviderList
from modules.provider.presentation.views.provider_detail import ProviderDetail

urlpatterns = [
    path('providers/signup/', ProviderCreate.as_view()),
    path('providers/', ProviderList.as_view()),
    path('providers/<id>/', ProviderDetail.as_view()),
]
