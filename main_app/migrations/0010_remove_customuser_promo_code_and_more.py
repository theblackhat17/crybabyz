# Generated by Django 5.1.1 on 2024-09-19 12:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0009_remove_customuser_free_months_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='promo_code',
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='promo_code_expiration',
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('discount_percent', models.DecimalField(decimal_places=2, max_digits=5)),
                ('valid_from', models.DateTimeField()),
                ('valid_until', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_coupons', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='current_coupon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main_app.coupon'),
        ),
    ]
