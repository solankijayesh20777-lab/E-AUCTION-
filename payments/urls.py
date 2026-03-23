from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<int:item_id>/', views.initiate_payment, name='initiate_payment'),
    path('callback/', views.payment_callback, name='payment_callback'),
    path('stripe-success/', views.stripe_success, name='stripe_success'),
    path('stripe-cancel/', views.stripe_cancel, name='stripe_cancel'),
    path('wallet/', views.wallet_dashboard, name='wallet_dashboard'),
    path('wallet/deposit/', views.deposit_funds, name='deposit_funds'),
    path('wallet/withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('confirm-delivery/<int:item_id>/', views.confirm_delivery, name='confirm_delivery'),
    path('invoice/<int:payment_id>/', views.download_invoice, name='download_invoice'),
    path('mock-success/<int:payment_id>/', views.mock_payment_success, name='mock_payment_success'),
]
