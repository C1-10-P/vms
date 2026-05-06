from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth import get_user_model
User = get_user_model()

import re
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log all user actions for audit trail
    """
    
    # Paths to exclude from logging
    EXCLUDE_PATHS = [
        r'^/static/',
        r'^/media/',
        r'^/admin/jsi18n/',
        r'^/health/',
    ]
    
    # Methods to log
    LOG_METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']
    
    def process_request(self, request):
        """Store request start time"""
        request.start_time = timezone.now()
    
    def process_response(self, request, response):
        """Log request after response"""
        
        # Skip excluded paths
        for pattern in self.EXCLUDE_PATHS:
            if re.match(pattern, request.path):
                return response
        
        # Only log specific methods
        if request.method not in self.LOG_METHODS:
            return response
        
        # Only log authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Calculate response time
        response_time = None
        if hasattr(request, 'start_time'):
            response_time = (timezone.now() - request.start_time).total_seconds() * 1000
        
        # Create audit log entry
        from apps.access.models import AccessLog
        
        try:
            AccessLog.objects.create(
                person=request.user.person if hasattr(request.user, 'person') else None,
                person_type=request.user.person.person_type if hasattr(request.user, 'person') else 'staff',
                zone=None,
                verification_method='web',
                result='granted' if response.status_code < 400 else 'denied',
                reason=f"HTTP {response.status_code}",
                access_time=timezone.now(),
                response_time_ms=int(response_time) if response_time else 0,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware to prevent abuse
    """
    
    # Rate limit configurations
    RATE_LIMITS = {
        'default': {'requests': 100, 'window': 60},  # 100 requests per minute
        'api': {'requests': 300, 'window': 60},       # 300 requests per minute
        'login': {'requests': 5, 'window': 300},      # 5 attempts per 5 minutes
        'attendance': {'requests': 200, 'window': 60}, # 200 check-ins per minute
    }
    
    def process_request(self, request):
        """Check rate limit"""
        
        # Determine rate limit key
        key = self.get_rate_limit_key(request)
        
        # Get rate limit configuration
        config = self.get_rate_limit_config(request)
        
        # Check if rate limited
        if self.is_rate_limited(key, config):
            logger.warning(f"Rate limit exceeded for {key}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'retry_after': config['window'],
                'message': f'Too many requests. Please wait {config["window"]} seconds.'
            }, status=429)
        
        # Increment counter
        self.increment_counter(key, config)
    
    def get_rate_limit_key(self, request):
        """Generate unique key for rate limiting"""
        if request.user.is_authenticated:
            return f"ratelimit:{request.user.id}:{request.path}"
        return f"ratelimit:{self.get_client_ip(request)}:{request.path}"
    
    def get_rate_limit_config(self, request):
        """Get rate limit config based on request type"""
        
        # Login attempts
        if request.path == '/api/auth/login/' or request.path == '/admin/login/':
            return self.RATE_LIMITS['login']
        
        # API endpoints
        if request.path.startswith('/api/'):
            # Attendance API has higher limit
            if 'attendance' in request.path:
                return self.RATE_LIMITS['attendance']
            return self.RATE_LIMITS['api']
        
        return self.RATE_LIMITS['default']
    
    def is_rate_limited(self, key, config):
        """Check if request should be rate limited"""
        cache_key = f"{key}:count"
        count = cache.get(cache_key, 0)
        return count >= config['requests']
    
    def increment_counter(self, key, config):
        """Increment request counter"""
        cache_key = f"{key}:count"
        
        # Use atomic increment
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, config['window'])
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', 'unknown')


class RequestLogMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests for debugging
    """
    
    def process_request(self, request):
        """Log incoming request"""
        logger.info(f"Request: {request.method} {request.path} - User: {request.user}")
    
    def process_response(self, request, response):
        """Log response"""
        logger.info(f"Response: {response.status_code} for {request.path}")
        return response


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enforce session security
    """
    
    def process_request(self, request):
        """Check session security"""
        
        # Session timeout check (30 minutes)
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            if last_activity:
                last_activity_time = timezone.datetime.fromisoformat(last_activity)
                if (timezone.now() - last_activity_time).seconds > 1800:
                    # Session expired
                    from django.contrib.auth import logout
                    logout(request)
                    return JsonResponse({
                        'error': 'Session expired. Please login again.'
                    }, status=401)
            
            # Update last activity
            request.session['last_activity'] = timezone.now().isoformat()
        
        # IP binding check (optional)
        if request.session.get('ip_address'):
            current_ip = self.get_client_ip(request)
            if request.session['ip_address'] != current_ip:
                # IP changed - possible session hijacking
                logger.warning(f"IP mismatch for user {request.user}: {request.session['ip_address']} vs {current_ip}")
                from django.contrib.auth import logout
                logout(request)
                return JsonResponse({
                    'error': 'Session invalid. IP address changed.'
                }, status=401)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware to handle maintenance mode
    """
    
    def process_request(self, request):
        """Check if system is in maintenance mode"""
        
        # Check if maintenance mode is enabled
        maintenance_mode = cache.get('maintenance_mode', False)
        
        if maintenance_mode:
            # Allow superusers and specific IPs
            if not (request.user.is_authenticated and request.user.is_superuser):
                # Check if IP is whitelisted
                whitelist_ips = cache.get('maintenance_whitelist', [])
                client_ip = self.get_client_ip(request)
                
                if client_ip not in whitelist_ips:
                    return JsonResponse({
                        'error': 'System is under maintenance',
                        'estimated_completion': cache.get('maintenance_eta', 'Unknown'),
                        'contact': 'admin@vms.com'
                    }, status=503)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')