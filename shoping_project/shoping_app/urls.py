from  django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('favorites/', views.favorites, name='favorites'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('product/<int:product_id>/buy/', views.buy_now, name='buy_now'),
    path('favorites/<int:product_id>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('manage/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/products/', views.admin_products, name='admin_products'),
    path('manage/products/new/', views.admin_product_form, name='admin_product_new'),
    path('manage/products/<int:product_id>/edit/', views.admin_product_form, name='admin_product_edit'),
    path('manage/products/<int:product_id>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('manage/inventory/', views.admin_inventory, name='admin_inventory'),
    path('manage/orders/', views.admin_orders, name='admin_orders'),
    path('manage/expenses/', views.admin_expenses, name='admin_expenses'),
    path('manage/settings/', views.admin_settings, name='admin_settings'),
]
