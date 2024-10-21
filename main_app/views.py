from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Pack, Payment
from django.contrib import messages
import stripe
from .forms import CustomUserCreationForm, RegistrationForm, CustomUserChangeForm, PackForm
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
import logging
import datetime
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .forms import CouponForm
from .models import Coupon
from django.views.decorators.http import require_POST
from django.http import JsonResponse




stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger('main_app')

def can_access_packs(user):
    if user.is_subscribed:
        return True
    elif user.subscription_end_date and user.subscription_end_date > timezone.now():
        return True
    return False

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Received Stripe event: {event['type']}")
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)

    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        logger.info(f"Subscription deleted for customer: {customer_id}")

        try:
            user = CustomUser.objects.get(stripe_customer_id=customer_id)
            user.is_subscribed = False
            
            # Mettre à jour la date de fin de l'abonnement
            current_period_end = subscription.get('current_period_end')
            if current_period_end:
                user.subscription_end_date = datetime.datetime.fromtimestamp(current_period_end)
                logger.info(f"Set subscription_end_date to {user.subscription_end_date} for user {user.email}")
            
            user.save()
        except CustomUser.DoesNotExist:
            logger.error(f"No user found with customer ID: {customer_id}")
            return HttpResponse(status=404)
        except Exception as e:
            logger.error(f"Error updating user subscription: {str(e)}")

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        logger.info(f"Invoice payment succeeded for customer: {customer_id}")

        try:
            user = CustomUser.objects.get(stripe_customer_id=customer_id)
            
            # Récupérer l'abonnement et définir la date de fin de période
            subscription_id = invoice.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                current_period_end = subscription['current_period_end']
                
                # Mettre à jour l'état et la date de fin d'abonnement
                user.is_subscribed = True
                user.subscription_end_date = datetime.datetime.fromtimestamp(current_period_end)
                logger.info(f"User {user.email} subscription end date set to {user.subscription_end_date}")
            
            user.save()
            logger.info(f"User {user.email} subscription status updated to True")
        except CustomUser.DoesNotExist:
            logger.error(f"No user found with customer ID: {customer_id}")
            return HttpResponse(status=404)
        except Exception as e:
            logger.error(f"Error updating user subscription: {str(e)}")

    return HttpResponse(status=200)



@login_required
def cancel_subscription(request):
    user = request.user

    if not user.stripe_customer_id:
        messages.error(request, "Aucun abonnement actif à annuler.")
        return redirect('member_area')

    try:
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status='active', limit=1)
        if subscriptions and len(subscriptions['data']) > 0:
            subscription_id = subscriptions['data'][0].id
            logger.info(f"Attempting to cancel subscription with ID: {subscription_id} for user {user.email}")

            # Annuler l'abonnement à la fin de la période de facturation actuelle
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            # Mettre à jour l'utilisateur localement, mais conserver l'accès jusqu'à la fin de la période
            user.is_subscribed = True  # L'utilisateur reste abonné jusqu'à la fin de la période
            user.subscription_end_date = datetime.datetime.fromtimestamp(subscriptions['data'][0]['current_period_end'])
            user.save()
            logger.info(f"Subscription with ID: {subscription_id} set to cancel at period end for user {user.email}")

            messages.success(request, "Votre abonnement a été annulé. Vous aurez accès jusqu'à la fin de la période actuelle.")
        else:
            messages.error(request, "Aucun abonnement actif à annuler.")
    except Exception as e:
        logger.error(f"Error canceling subscription for user {user.email}: {str(e)}")
        messages.error(request, f"Une erreur s'est produite lors de l'annulation de l'abonnement : {str(e)}")
    
    return redirect('member_area')



@login_required
def create_stripe_session(request):
    user = request.user

    # Créer un client Stripe si nécessaire
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            phone=user.phone,
        )
        user.stripe_customer_id = customer['id']
        user.save()

    # Vérifier si l'utilisateur a un coupon valide et non utilisé
    coupon = user.user_coupons.filter(is_active=True, is_used=False, valid_until__gte=timezone.now()).first()
    discounts = []

    if coupon:
        try:
            # Créer un coupon Stripe lié au coupon de l'utilisateur
            stripe_coupon = stripe.Coupon.create(
                percent_off=coupon.discount_percent,
                duration='once'  # Le coupon ne s'applique qu'une seule fois
            )
            discounts = [{'coupon': stripe_coupon.id}]
            
            # Marquer le coupon comme utilisé après avoir vérifié que la session a été créée avec succès
        except Exception as e:
            logger.error(f"Erreur lors de la création du coupon Stripe : {str(e)}")

    # Créer la session de paiement Stripe avec le coupon si applicable
    checkout_session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': 'Abonnement mensuel',
                },
                'unit_amount': 1000,  # Prix de l'abonnement en centimes
            },
            'quantity': 1,
        }],
        mode='subscription',
        discounts=discounts,  # Appliquer le coupon s'il existe
        success_url=request.build_absolute_uri('/packs/'),
        cancel_url=request.build_absolute_uri('/packs/'),
    )

    # Une fois la session Stripe créée avec succès, marquer le coupon comme utilisé
    if coupon:
        coupon.is_used = True
        coupon.save()

    return redirect(checkout_session.url, code=303)




def index(request):
    packs = Pack.objects.all()
    return render(request, 'main_app/index.html', {'packs': packs})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')  
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Connexion réussie. Bienvenue !")
                return redirect('index')
            else:
                messages.error(request, "Erreur d'authentification. Veuillez réessayer.")
        else:
            messages.error(request, "Formulaire invalide. Vérifiez vos informations.")
    else:
        form = AuthenticationForm()
    return render(request, 'main_app/login.html', {'form': form})

@login_required
def member_area(request):
    user = request.user
    coupons = user.user_coupons.filter(is_active=True, is_used=False, valid_until__gte=timezone.now())
    return render(request, 'main_app/member_area.html', {'user': user, 'coupons': coupons})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('member_area')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'main_app/edit_profile.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription réussie. Bienvenue !")
            return redirect('index')
        else:
            messages.error(request, "Erreur lors de l'inscription. Veuillez vérifier vos informations.")
    else:
        form = RegistrationForm()
    return render(request, 'main_app/register.html', {'form': form})

@login_required
def subscribe_view(request):
    user = request.user

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            phone=user.phone,
        )
        user.stripe_customer_id = customer['id']
        user.save()
    
    price_id = 'price_1Put2x09WfzmYEEc7wTMiUO0'

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/packs/'),
            cancel_url=request.build_absolute_uri('/packs/'),
        )
        logger.info(f"Stripe checkout session created: {checkout_session.url}")
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        logger.error(f"Erreur lors de la création de la session de paiement Stripe: {str(e)}")
        return HttpResponse(f"Une erreur s'est produite : {str(e)}", status=500)



def packs_view(request):
    packs = Pack.objects.all()

    # Vérifier l'état de l'utilisateur
    user = request.user
    is_authenticated = user.is_authenticated
    is_subscribed = user.is_authenticated and user.is_subscribed
    is_admin = user.is_staff

    context = {
        'packs': packs,
        'is_authenticated': is_authenticated,
        'is_subscribed': is_subscribed,
        'is_admin': is_admin,
        'manage_pack_url': 'manage_packs',  # Lien vers la page de gestion des packs
    }

    return render(request, 'main_app/packs.html', context)

@staff_member_required
def manage_packs(request):
    packs = Pack.objects.all()
    edit_pack_id = request.GET.get('edit_pack_id')
    pack_to_edit = None

    if edit_pack_id:
        pack_to_edit = get_object_or_404(Pack, id=edit_pack_id)

    if request.method == 'POST':
        if pack_to_edit:
            # Modifier le pack existant
            form = PackForm(request.POST, request.FILES, instance=pack_to_edit)
        else:
            # Ajouter un nouveau pack
            form = PackForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, 'Pack ajouté ou modifié avec succès.')
            return redirect('manage_packs')
    else:
        form = PackForm(instance=pack_to_edit) if pack_to_edit else PackForm()

    context = {
        'packs': packs,
        'form': form,
        'pack_to_edit': pack_to_edit,  # Passe le pack à modifier au template
    }
    return render(request, 'main_app/manage_packs.html', context)


@staff_member_required
def edit_pack(request, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    if request.method == 'POST':
        form = PackForm(request.POST, request.FILES, instance=pack)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pack modifié avec succès.')
            return redirect('manage_packs')
    else:
        form = PackForm(instance=pack)
    return render(request, 'main_app/edit_pack.html', {'form': form, 'pack': pack})


@staff_member_required
def delete_pack(request, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    pack.delete()
    messages.success(request, 'Pack supprimé avec succès.')
    return redirect('manage_packs')

def splash_view(request):
    return render(request, 'main_app/splash.html')

def offer_referral_reward(user):
    if user.referred_by:
        referred_by_user = user.referred_by
        referred_by_user.free_months += 1  # Ajoute un mois gratuit
        referred_by_user.save()
        logger.info(f"Offert 1 mois gratuit à {referred_by_user.email} pour avoir parrainé {user.email}")


@staff_member_required
def manage_subscriptions(request):
    # Récupérer les abonnés actifs
    active_subscribers = CustomUser.objects.filter(is_subscribed=True)

    # Récupérer les abonnements expirant bientôt (dans les 7 prochains jours)
    expiring_soon = CustomUser.objects.filter(
        is_subscribed=True,
        subscription_end_date__lte=timezone.now() + timezone.timedelta(days=7)
    )

    # Historique des paiements (assurez-vous d'avoir un modèle Payment pour cela)
    payment_history = Payment.objects.all().order_by('-date')  # Assume that you have a Payment model with a 'date' field

    context = {
        'active_subscribers': active_subscribers,
        'expiring_soon': expiring_soon,
        'payment_history': payment_history
    }
    
    return render(request, 'main_app/manage_subscriptions.html', context)

def notify_users_new_pack(pack):
    users = CustomUser.objects.all()
    for user in users:
        send_mail(
            'Nouveau pack ajouté!',
            f'Un nouveau pack "{pack.name}" est disponible sur BabyCry.',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

@staff_member_required
def manage_subscriptions(request):
    # Récupérer les abonnés actifs
    active_subscribers = CustomUser.objects.filter(is_subscribed=True)

    # Récupérer les abonnements expirant bientôt (dans les 7 prochains jours)
    expiring_soon = CustomUser.objects.filter(
        is_subscribed=True,
        subscription_end_date__lte=timezone.now() + timezone.timedelta(days=7)
    )

    # Récupérer tous les utilisateurs (abonnés et non abonnés)
    all_users = CustomUser.objects.all()

    # Historique des paiements
    payment_history = Payment.objects.all().order_by('-date')

    context = {
        'active_subscribers': active_subscribers,
        'expiring_soon': expiring_soon,
        'all_users': all_users,  # Ajouter tous les utilisateurs au contexte
        'payment_history': payment_history,
    }
    
    return render(request, 'main_app/manage_subscriptions.html', context)



@staff_member_required
def create_coupon_view(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.user = form.cleaned_data['user']  # Assigner le coupon à l'utilisateur sélectionné
            coupon.save()
            messages.success(request, 'Le coupon a été créé avec succès.')
            return redirect('manage_coupons')
    else:
        form = CouponForm()
    
    return render(request, 'main_app/create_coupon.html', {'form': form})

@login_required
def apply_coupon(request, coupon_code):
    try:
        # Vérifier que le coupon existe, est valide, non utilisé, et n'a pas expiré
        coupon = Coupon.objects.get(code=coupon_code, is_active=True, is_used=False, valid_until__gte=timezone.now())
        user = request.user

        # Créer un coupon temporaire dans Stripe
        stripe_coupon = stripe.Coupon.create(
            percent_off=coupon.discount_percent,
            duration='once',  # Le coupon s'applique une seule fois
        )

        # Si l'utilisateur est déjà abonné, appliquer le coupon pour le prochain paiement
        if user.stripe_customer_id:
            subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status='active', limit=1)
            if subscriptions and len(subscriptions['data']) > 0:
                subscription_id = subscriptions['data'][0].id
                stripe.Subscription.modify(
                    subscription_id,
                    coupon=stripe_coupon.id  # Appliquer le coupon à l'abonnement existant
                )

        # Marquer le coupon comme utilisé
        coupon.is_used = True
        coupon.save()

        return JsonResponse({'success': True, 'message': 'Coupon appliqué avec succès !'})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Ce coupon n\'est pas valide, expiré ou déjà utilisé.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)




@staff_member_required
def send_coupon_view(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.code = get_random_string(8).upper()  # Générer un code unique aléatoire
            coupon.save()
            # Envoyer l'email à l'utilisateur
            send_mail(
                'Votre coupon BabyCry',
                f'Voici votre coupon : {coupon.code}. Utilisez-le lors de votre abonnement pour bénéficier d\'une réduction.',
                'admin@babycry.com',
                [coupon.user.email],
                fail_silently=False,
            )
            messages.success(request, 'Le coupon a été envoyé par e-mail.')
            return redirect('send_coupon')
    else:
        form = CouponForm()
    return render(request, 'main_app/send_coupon.html', {'form': form})

