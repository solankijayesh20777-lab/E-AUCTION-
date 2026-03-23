from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from users import views as users_views

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/password/reset/fast/', users_views.CustomPasswordResetView.as_view(), name='fast_account_reset_password'),
    path('accounts/password/reset/', users_views.CustomPasswordResetView.as_view(), name='account_reset_password'),
    path('accounts/', include('allauth.urls')),
    path('users/', include('users.urls')),
    path('auctions/', include('auctions.urls')),
    path('payments/', include('payments.urls')),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
