from django.contrib import admin
from django.urls import include, path

from common.views import homepage


urlpatterns = [
    path('', homepage, name='homepage'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
]
