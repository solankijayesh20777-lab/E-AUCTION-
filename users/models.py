from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
import random

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    is_mobile_verified = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    is_seller_approved = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class MobileOTP(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='mobile_otp')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        """Generates a 6-digit OTP and prints it to console."""
        self.otp = str(random.randint(100000, 999999))
        self.save()
        # In a real app, integrate SMS gateway here like Twilio:
        print(f"--- DUMMY SMS GATEWAY ---")
        print(f"OTP for {self.user.mobile_number} is: {self.otp}")
        print(f"-------------------------")
