from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Garçom
    path('garcom/', views.waiter_view, name='waiter_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('order/submit/', views.submit_order, name='submit_order'),
    
    # Cozinha
    path('cozinha/', views.kitchen_view, name='kitchen_view'),
    path('order/ready/<int:order_id>/', views.mark_order_ready, name='mark_order_ready'),
    
    # Admin - Dashboard
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    
    # Admin - Relatórios
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
    
    # Admin - Cardápio
    path('admin-panel/menu/', views.admin_menu, name='admin_menu'),
    path('admin-panel/product/new/', views.product_create, name='product_create'),
    path('admin-panel/product/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('admin-panel/product/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('admin-panel/category/new/', views.category_create, name='category_create'),
    path('admin-panel/category/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('admin-panel/category/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    
    # Admin - Usuários
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/user/new/', views.user_create, name='user_create'),
    path('admin-panel/user/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    
    # Admin - Configurações
    path('admin-panel/settings/', views.admin_settings, name='admin_settings'),
    path('admin-panel/store/toggle/', views.toggle_store_status, name='toggle_store_status'),
    
    # Admin - Pedidos Online
    path('admin-panel/online/', views.admin_online_orders, name='admin_online_orders'),
    
    # Pedidos
    path('order/<int:order_id>/close/', views.close_order, name='close_order'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/print/', views.print_order, name='print_order'),
    
    # API (AJAX)
    path('api/cart/add/<int:product_id>/', views.api_add_to_cart, name='api_add_to_cart'),
    path('api/cart/remove/<int:product_id>/', views.api_remove_from_cart, name='api_remove_from_cart'),
    path('api/cart/', views.api_get_cart, name='api_get_cart'),
    path('api/cart/clear/', views.api_clear_cart, name='api_clear_cart'),
]
