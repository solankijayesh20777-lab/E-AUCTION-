from django.contrib import admin
from .models import Wallet, Transaction, Payment

class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__email',)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('wallet__user__email', 'reference_id')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('item', 'buyer', 'amount', 'status', 'created_at')
    list_filter = ('status', 'gateway_name')
    search_fields = ('buyer__email', 'gateway_order_id')

admin.site.register(Wallet, WalletAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Payment, PaymentAdmin)
