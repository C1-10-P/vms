# apps/users/views_auth.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings


class LoginView(View):
    """
    Custom login view with VMS-specific logic
    """
    
    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = AuthenticationForm()
        return render(request, 'registration/login.html', {
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
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                # Log successful login
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect to next or dashboard
                next_url = request.GET.get('next', reverse('dashboard:index'))
                return redirect(next_url)
        
        # If form is invalid or authentication failed
        messages.error(request, 'Invalid username or password. Please try again.')
        return render(request, 'registration/login.html', {
            'form': form,
            'debug': settings.DEBUG
        })


class LogoutView(View):
    """
    Custom logout view
    """
    
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been successfully logged out.')
        return redirect('login')
    
    def post(self, request):
        logout(request)
        messages.info(request, 'You have been successfully logged out.')
        return redirect('login')