from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from .permissions import PermissionChecker


def permission_required(permission, raise_exception=True, return_json=False):
    """
    Decorator to check if user has required permission
    
    Usage:
        @permission_required('can_view_attendance')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if PermissionChecker.has_permission(request.user, permission):
                return view_func(request, *args, **kwargs)
            
            if return_json:
                return JsonResponse({
                    'error': 'Permission denied',
                    'required_permission': permission,
                    'user_permissions': list(PermissionChecker.get_user_permissions(request.user))
                }, status=403)
            
            if raise_exception:
                raise PermissionDenied(f"You don't have permission: {permission}")
            
            # Return forbidden response
            from django.shortcuts import render
            return render(request, '403.html', {'permission': permission}, status=403)
        
        return wrapped_view
    return decorator


def permissions_required(permissions, require_all=False, raise_exception=True):
    """
    Decorator to check multiple permissions
    
    Usage:
        @permissions_required(['can_view_attendance', 'can_edit_attendance'], require_all=True)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if require_all:
                has_permission = PermissionChecker.has_all_permissions(request.user, permissions)
            else:
                has_permission = PermissionChecker.has_any_permission(request.user, permissions)
            
            if has_permission:
                return view_func(request, *args, **kwargs)
            
            if raise_exception:
                raise PermissionDenied(f"Missing required permissions: {permissions}")
            
            from django.shortcuts import render
            return render(request, '403.html', {'permissions': permissions}, status=403)
        
        return wrapped_view
    return decorator


def role_required(role_names):
    """
    Decorator to check if user has specific role
    
    Usage:
        @role_required(['admin', 'security'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            user_roles = [group.name for group in request.user.groups.all()]
            
            if isinstance(role_names, str):
                role_names = [role_names]
            
            if any(role in user_roles for role in role_names):
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied(f"Required role: {role_names}")
        
        return wrapped_view
    return decorator


def api_permission_required(permission):
    """
    Decorator for API views that returns JSON response
    """
    return permission_required(permission, return_json=True)