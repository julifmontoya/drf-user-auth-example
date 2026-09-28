from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve 
from django.urls import re_path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/auth/', include('modules.authentication.urls')),
    path('v1/affiliate/', include('modules.provider.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]

