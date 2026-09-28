from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from modules.provider.models import Provider
from modules.provider.presentation.serializers.provider_serializer import ProviderSerializer
from shared.permissions import IsVerified
from shared.pagination import CustomPagination


class ProviderList(APIView):
    permission_classes = (IsAuthenticated, IsVerified,)

    def get(self, request, *args, **kwargs):
        providers = self.get_providers()

        paginator = CustomPagination()
        paginated_providers = paginator.paginate_queryset(providers, request)

        serializer = ProviderSerializer(paginated_providers, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_providers(self):
        user = self.request.user
        company = self.request.query_params.get('company', None)

        if user.is_superuser:
            queryset = Provider.objects.all()
        else:
            queryset = Provider.objects.filter(user=user)

        if company:
            queryset = queryset.filter(company__icontains=company)

        return queryset
