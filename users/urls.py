from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_update, name='profile'),
    path('request-otp/', views.request_mobile_otp, name='request_mobile_otp'),
    path('verify-otp/', views.verify_mobile_otp, name='verify_mobile_otp'),
]
