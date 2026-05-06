# apps/authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings


class LoginView(View):
    """Custom login view"""
    
    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = AuthenticationForm()
        return render(request, 'verify/login.html', {
            'form': form,
            'debug': settings.DEBUG
        })
    
    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember = request.POST.get('remember', False)
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session expiry based on "Remember me"
                if not remember:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                next_url = request.GET.get('next', reverse('dashboard:home'))
                return redirect(next_url)
        
        messages.error(request, 'Invalid username or password. Please try again.')
        return render(request, 'verify/login.html', {'form': form, 'debug': settings.DEBUG})


class LogoutView(View):
    """Custom logout view"""
    
    def post(self, request):
        logout(request)
        messages.info(request, 'You have been successfully logged out.')
        return redirect('verify:login')
    
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been successfully logged out.')
        return redirect('verify:login')