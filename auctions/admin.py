from django.contrib import admin
from django.urls import path
from .models import Category, Item, CommissionSetting
from .admin_views import admin_analytics

@admin.action(description="Approve selected items for Auction")
def approve_items(modeladmin, request, queryset):
    queryset.update(is_approved=True, status='active')

@admin.action(description="Reject selected items")
def reject_items(modeladmin, request, queryset):
    queryset.update(is_approved=False, status='draft')

class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'starting_price', 'is_approved', 'status', 'start_time', 'end_time')
    list_filter = ('is_approved', 'status', 'category', 'created_at')
    search_fields = ('title', 'description', 'seller__email')
    actions = [approve_items, reject_items]
    fieldsets = (
        (None, {
            'fields': ('seller', 'category', 'title', 'description', 'image')
        }),
        ('Pricing & Timing', {
            'fields': ('starting_price', 'reserve_price', 'start_time', 'end_time')
        }),
        ('Admin Control', {
            'fields': ('status', 'is_approved', 'rejection_reason', 'fraud_score')
        }),
    )

class CommissionSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'percentage', 'flat_fee', 'is_active')

# Add custom analytics URL to Admin
admin.site.get_urls = (lambda original_get_urls: 
    lambda: [path('analytics/', admin.site.admin_view(admin_analytics), name='platform_analytics')] + original_get_urls()
)(admin.site.get_urls)

admin.site.register(Category)
admin.site.register(Item, ItemAdmin)
admin.site.register(CommissionSetting, CommissionSettingAdmin)
