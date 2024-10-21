from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Pack, Coupon
from django.utils.translation import gettext_lazy as _

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_subscribed', 'stripe_customer_id', 'subscription_end_date', 'is_staff']  # Ajout de 'subscription_end_date'
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'street', 'city', 'country', 'avatar')}),
        (_('Subscription'), {'fields': ('is_subscribed', 'stripe_customer_id', 'subscription_end_date', 'coupons')}),  # Ajout de 'coupons'
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_subscribed', 'stripe_customer_id', 'subscription_end_date'),  # Ajout de 'subscription_end_date'
        }),
    )
    
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)

# Enregistrement des modèles dans l'admin
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Pack)
admin.site.register(Coupon)  # Ajoutez l'enregistrement du modèle Coupon
