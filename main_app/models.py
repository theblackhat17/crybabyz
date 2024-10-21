from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.contrib.auth import get_user_model

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_subscribed = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    coupons = models.ManyToManyField('Coupon', blank=True, related_name='users')

    
    # Champ pour stocker le code promo actuel et sa date d'expiration
    current_coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
class Payment(models.Model):
    user = models.ForeignKey('main_app.CustomUser', on_delete=models.CASCADE)  # Utilisez une chaîne pour référencer le modèle CustomUser
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"Paiement de {self.user.email} - {self.amount} €"

class Pack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='pack_images/')
    download_url = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_used = models.BooleanField(default=False)  # Nouveau champ pour marquer le coupon comme utilisé
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_coupons')

    def __str__(self):
        return f"Coupon {self.code} - {self.discount_percent}%"


# Supprimer le modèle PromoCode si vous n'en avez plus besoin
