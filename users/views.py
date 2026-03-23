from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MobileOTP
from .forms import UserUpdateForm
from allauth.account.views import PasswordResetView
from allauth.account.utils import user_pk_to_url_str
from django.conf import settings
from django.urls import reverse
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from allauth.account.forms import default_token_generator
from allauth.account.adapter import get_adapter

@login_required
def profile_update(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
        
    return render(request, 'users/profile.html', {'form': form})

@login_required
def request_mobile_otp(request):
    if request.user.is_mobile_verified:
        messages.info(request, "Your mobile number is already verified.")
        return redirect('home')

    if request.method == 'POST':
        mobile_number = request.POST.get('mobile_number')
        if mobile_number:
            request.user.mobile_number = mobile_number
            request.user.save()
            
        otp_obj, created = MobileOTP.objects.get_or_create(user=request.user)
        otp_obj.generate_otp()
        messages.success(request, 'An OTP has been sent to your mobile.')
        return redirect('verify_mobile_otp')
        
    return render(request, 'users/request_otp.html')

@login_required
def verify_mobile_otp(request):
    if request.user.is_mobile_verified:
        return redirect('home')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        try:
            otp_obj = MobileOTP.objects.get(user=request.user)
            if otp_obj.otp == entered_otp:
                request.user.is_mobile_verified = True
                request.user.save()
                otp_obj.delete() # Consumed
                messages.success(request, 'Mobile number verified successfully!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
        except MobileOTP.DoesNotExist:
            messages.error(request, 'Please request an OTP first.')
            return redirect('request_mobile_otp')
            
    return render(request, 'users/verify_otp.html')

class CustomPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        print(f"DEBUG: CustomPasswordResetView hit for {email}")
        
        if settings.DEBUG:
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=email)
                is_social = SocialAccount.objects.filter(user=user).exists()
                
                if not is_social:
                    form.save(self.request) # Standard allauth behavior
                    from allauth.account.utils import user_pk_to_url_str
                    token = default_token_generator.make_token(user)
                    uid = user_pk_to_url_str(user)
                    url = reverse("account_reset_password_from_key", kwargs=dict(uidb36=uid, key=token))
                    print(f"DEBUG: Auto-redirecting to: {url}")
                    return redirect(url)
            except User.DoesNotExist:
                print(f"DEBUG: User not found: {email}")
            except Exception as e:
                print(f"DEBUG: Error: {str(e)}")
        
        return super().form_valid(form)
