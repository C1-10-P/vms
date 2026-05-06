from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""
    list_display = ['email', 'person_link', 'is_staff', 'is_active', 'last_login']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['email', 'username', 'person__first_name', 'person__last_name']
    
    fieldsets = UserAdmin.fieldsets + (
        ('VMS Specific', {
            'fields': ('person', 'last_ip_address', 'login_attempts', 'locked_until'),
        }),
    )
    
    def person_link(self, obj):
        if obj.person:
            from django.urls import reverse
            url = reverse('admin:core_person_change', args=[obj.person.id])
            return f'<a href="{url}">{obj.person.full_name}</a>'
        return '-'
    person_link.allow_tags = True
    person_link.short_description = 'Person Record'