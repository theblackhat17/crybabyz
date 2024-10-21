from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Pack
from .models import Coupon
from django.forms.widgets import DateTimeInput

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']


class PackForm(forms.ModelForm):
    class Meta:
        model = Pack
        fields = ['name', 'description', 'image', 'download_url']

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'street', 'city', 'country', 'avatar']

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_percent', 'valid_from', 'valid_until', 'is_active', 'user']
        widgets = {
            'valid_from': DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_until': DateTimeInput(attrs={'type': 'datetime-local'}),
        }