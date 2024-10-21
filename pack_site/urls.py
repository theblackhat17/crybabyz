from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),  # Inclusion des URLs de l'application principale
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
