from django.urls import path
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/watchlist/', views.toggle_watchlist, name='toggle_watchlist'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('buyer-dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('item/create/', views.item_create, name='item_create'),
    path('item/<int:pk>/update/', views.item_update, name='item_update'),
    path('item/<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('notifications/mark-read/', views.mark_notifications_as_read, name='mark_notifications_read'),
]
