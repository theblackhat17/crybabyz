from django.urls import path
from . import views
from .views import stripe_webhook
from .views import register_view, login_view, logout_view, member_area, edit_profile, packs_view, subscribe_view, apply_coupon
urlpatterns = [
    path('home/', views.index, name='index'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('member-area/', member_area, name='member_area'),
    path('edit-profile/', edit_profile, name='edit_profile'),
    path('subscribe/', views.subscribe_view, name='subscribe'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'), 
    path('packs/', packs_view, name='packs'),
    path('cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),
    path('manage-packs/', views.manage_packs, name='manage_packs'),
    path('manage-packs/', views.manage_packs, name='manage_packs'),
    path('manage-packs/edit/<int:pack_id>/', views.edit_pack, name='edit_pack'),
    path('manage-packs/delete/<int:pack_id>/', views.delete_pack, name='delete_pack'),
    path('', views.splash_view, name='splash'),    
    path('manage-subscriptions/', views.manage_subscriptions, name='manage_subscriptions'),
    path('apply-coupon/<str:coupon_code>/', apply_coupon, name='apply_coupon'),
    path('send-coupon/', views.send_coupon_view, name='send_coupon'),

]
