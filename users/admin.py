from django.contrib import admin
from .models import CustomUser, MobileOTP

@admin.action(description="Approve selected users as Sellers")
def approve_sellers(modeladmin, request, queryset):
    queryset.update(is_seller=True, is_seller_approved=True)

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'mobile_number', 'is_seller', 'is_seller_approved', 'is_kyc_verified', 'is_active', 'is_staff')
    list_filter = ('is_seller', 'is_seller_approved', 'is_kyc_verified', 'is_active', 'is_staff')
    search_fields = ('email', 'mobile_number')
    actions = [approve_sellers]

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(MobileOTP)
