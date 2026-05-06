from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model

User = get_user_model()

from django.contrib.auth.models import Group, Permission
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions, RoleGroups, PermissionChecker
from apps.core.models import Person, Staff
from apps.access.models.log import AccessLog
from .models import User
from .forms import UserCreateForm, UserUpdateForm, UserPermissionForm, GroupForm


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    ordering = ['-created_at']
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    def get_queryset(self):
        # Get all users with prefetched groups
        queryset = User.objects.all().prefetch_related('groups').select_related('person')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filter by role (Group)
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(groups__name=role)
        
        # Filter by active status
        is_active_filter = self.request.GET.get('is_active')
        if is_active_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.distinct().order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth.models import Group
        from apps.core.models import Person
        
        context['roles'] = Group.objects.all()
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['persons'] = Person.objects.filter(is_active=True, system_user__isnull=True)
        
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'role': self.request.GET.get('role', ''),
            'is_active': self.request.GET.get('is_active', '')
        }
        
        # Debug: Print to console
        print(f"Total users in queryset: {context['users'].count()}")
        for user in context['users']:
            print(f"User: {user.username}, Groups: {list(user.groups.all())}")
        
        return context


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create new system user
    """
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:list')
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New User'
        # Optimizing the person lookup for the form
        context['persons'] = Person.objects.filter(is_active=True).order_by('last_name')
        context['groups'] = Group.objects.all()
        return context
    
    def form_valid(self, form):
        # We call super().form_valid(form) which saves the object
        response = super().form_valid(form)
        
        # Now we can safely access self.object
        messages.success(self.request, f'User {self.object.username} created successfully.')
        
        # Logic for assigning groups if your form doesn't handle it automatically:
        # selected_groups = self.request.POST.getlist('groups')
        # if selected_groups:
        #     self.object.groups.set(selected_groups)
            
        return response


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update existing user
    """
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:list')
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit User: {self.object.username}'
        context['groups'] = Group.objects.all()
        context['user_groups'] = self.object.groups.all().values_list('id', flat=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.username} updated successfully.')
        return response


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    User detail view
    """
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = self.object.get_all_permissions()
        context['user_groups'] = self.object.groups.all()
        context['login_history'] = self.object.user_login_history.all()[:20] if hasattr(self.object, 'user_login_history') else []
        return context


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete user (soft delete by deactivating)
    """
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:list')
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        messages.success(request, f'User {user.username} has been deactivated.')
        return redirect(self.success_url)


class UserPermissionsView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Manage user permissions
    """
    model = User
    form_class = UserPermissionForm
    template_name = 'users/user_permissions.html'
    success_url = reverse_lazy('users:list')
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Permissions for {self.object.username}'
        context['all_permissions'] = Permission.objects.all().order_by('content_type__app_label', 'codename')
        context['user_permissions'] = self.object.user_permissions.all().values_list('id', flat=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Permissions for {self.object.username} updated successfully.')
        return response


class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    ordering = ['-created_at']
    template_name = 'users/role_list.html'
    context_object_name = 'roles'
    
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    def get_queryset(self):
        # Prefetching permissions to avoid N+1 query issues in the template
        queryset = Group.objects.all().prefetch_related('permissions')
        
        # Debug: Print to console
        print(f"Found {queryset.count()} groups:")
        for group in queryset:
            print(f"  - Group: {group.name}, ID: {group.id}, Permissions: {group.permissions.count()}")
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth.models import Permission
        
        # Define your system roles list
        system_role_names = [
            'super_admin', 'admin', 'security', 'lecturer', 
            'hod', 'viewer', 'Super Admin'
        ]
        
        # Logic for categorizing roles
        context['system_roles'] = Group.objects.filter(name__in=system_role_names).count()
        context['custom_roles'] = Group.objects.exclude(name__in=system_role_names).count()
        
        # Permission metadata
        context['total_permissions'] = Permission.objects.count()
        context['permissions'] = Permission.objects.all().order_by('content_type__app_label', 'codename')
        
        # Debug: Verify context data
        print(f"Context roles count: {len(context['roles'])}")
        
        return context


class RoleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Role detail view
    """
    model = Group
    template_name = 'users/role_detail.html'
    context_object_name = 'role'
    
    # Correct CBV way to enforce permissions
    permission_required = VMSPermissions.SYSTEM_MANAGE_USERS
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permissions'] = self.object.permissions.all()
        context['users'] = self.object.user_set.all()[:20]
        context['total_users'] = self.object.user_set.count()
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile view
    """
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        
        if hasattr(self.request.user, 'person'):
            context['person'] = self.request.user.person
        
        context['permissions'] = PermissionChecker.get_user_permissions(self.request.user)
        context['role'] = PermissionChecker.get_user_role(self.request.user)
        
        return context


class ChangePasswordView(LoginRequiredMixin, TemplateView):
    """
    Change user password
    """
    template_name = 'users/change_password.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PasswordChangeForm(self.request.user)
        return context
    
    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Please correct the error below.')
            return render(request, self.template_name, {'form': form})
        
def user_activate(request, pk):
    """Activate a user account"""
    user = get_object_or_404(User, pk=pk)
    user.is_active = True
    user.save()
    messages.success(request, f'User {user.username} activated.')
    return redirect('users:detail', pk=pk)


def user_deactivate(request, pk):
    """Deactivate a user account"""
    user = get_object_or_404(User, pk=pk)
    user.is_active = False
    user.save()
    messages.success(request, f'User {user.username} deactivated.')
    return redirect('users:detail', pk=pk)


class UserGroupsView(LoginRequiredMixin, UpdateView):
    """Manage user groups"""
    model = User
    fields = ['groups']
    template_name = 'users/user_groups.html'
    
    def get_success_url(self):
        return reverse_lazy('users:detail', kwargs={'pk': self.object.pk})


def add_user_permission(request, pk):
    """Add permission to user"""
    user = get_object_or_404(User, pk=pk)
    perm_id = request.POST.get('permission_id')
    if perm_id:
        from django.contrib.auth.models import Permission
        perm = get_object_or_404(Permission, pk=perm_id)
        user.user_permissions.add(perm)
    return redirect('users:permissions', pk=pk)


def remove_user_permission(request, pk):
    """Remove permission from user"""
    user = get_object_or_404(User, pk=pk)
    perm_id = request.POST.get('permission_id')
    if perm_id:
        from django.contrib.auth.models import Permission
        perm = get_object_or_404(Permission, pk=perm_id)
        user.user_permissions.remove(perm)
    return redirect('users:permissions', pk=pk)


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'users/role_form.html'
    success_url = reverse_lazy('users:role_list')


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'users/role_form.html'
    success_url = reverse_lazy('users:role_list')


class RoleDeleteView(LoginRequiredMixin, DeleteView):
    model = Group
    template_name = 'users/role_confirm_delete.html'
    success_url = reverse_lazy('users:role_list')


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    model = User
    fields = ['first_name', 'last_name', 'email']
    template_name = 'users/profile_edit.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse_lazy('users:profile')


class UserSessionsView(LoginRequiredMixin, TemplateView):
    """View user sessions"""
    template_name = 'users/sessions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.sessions.models import Session
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        context['sessions'] = sessions
        return context


def revoke_session(request, session_key):
    """Revoke a user session"""
    from django.contrib.sessions.models import Session
    Session.objects.filter(session_key=session_key).delete()
    messages.success(request, 'Session revoked.')
    return redirect('users:sessions')


class UserActivityLogView(LoginRequiredMixin, ListView):
    """View user activity logs"""
    model = AccessLog
    ordering = ['-created_at']
    template_name = 'users/activity.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        return AccessLog.objects.filter(person__isnull=False).select_related('person', 'zone').order_by('-access_time')


class ActivityDetailView(LoginRequiredMixin, DetailView):
    model = AccessLog
    ordering = ['-created_at']
    template_name = 'users/activity_detail.html'
    context_object_name = 'log'


def export_activity_logs(request):
    """Export activity logs to CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Zone', 'Result', 'IP Address'])
    
    logs = AccessLog.objects.select_related('person', 'zone').order_by('-access_time')[:1000]
    for log in logs:
        writer.writerow([
            log.access_time,
            log.person.full_name if log.person else 'Unknown',
            f'Access {log.verification_method}',
            log.zone.name if log.zone else 'N/A',
            log.result,
            log.ip_address or ''
        ])
    
    return response


def api_user_list(request):
    """API endpoint for user list"""
    users = User.objects.values('id', 'username', 'email', 'is_active')
    return JsonResponse({'users': list(users)})


def api_user_detail(request, pk):
    """API endpoint for user detail"""
    user = get_object_or_404(User, pk=pk)
    return JsonResponse({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'groups': list(user.groups.values_list('name', flat=True))
    })


def api_role_list(request):
    """API endpoint for role list"""
    roles = Group.objects.values('id', 'name')
    return JsonResponse({'roles': list(roles)})


def api_permission_list(request):
    """API endpoint for permission list"""
    permissions = Permission.objects.values('id', 'codename', 'name')
    return JsonResponse({'permissions': list(permissions)})


def ajax_check_username(request):
    """Check if username is available"""
    username = request.GET.get('username')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'available': not exists})


def ajax_check_email(request):
    """Check if email is available"""
    email = request.GET.get('email')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'available': not exists})


def ajax_user_search(request):
    """Search users for autocomplete"""
    query = request.GET.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query)
    ).values('id', 'username', 'email')[:10]
    return JsonResponse({'users': list(users)})

from django.http import JsonResponse
from django.template.loader import render_to_string

def get_user_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        user = User.objects.get(pk=pk)
        groups = Group.objects.all()
        persons = Person.objects.filter(is_active=True)
        user_groups = user.groups.all().values_list('id', flat=True)
        
        html = render_to_string('users/user_edit_form.html', {
            'user': user,
            'groups': groups,
            'persons': persons,
            'user_groups': user_groups,
            'csrf_token': request.COOKIES.get('csrftoken', '')
        })
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


def update_user(request, pk):
    """Update user via AJAX"""
    if request.method == 'POST':
        try:
            user = User.objects.get(pk=pk)
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.save()
            
            # Update groups
            group_ids = request.POST.getlist('groups')
            if group_ids:
                user.groups.set(group_ids)
            else:
                user.groups.clear()
            
            # Update linked person
            person_id = request.POST.get('person')
            if person_id:
                person = Person.objects.get(id=person_id)
                person.system_user = user
                person.save()
            
            return JsonResponse({'success': True, 'message': f'User {user.username} updated successfully'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def toggle_user_status(request, pk):
    """Toggle user active status via AJAX"""
    if request.method == 'POST':
        try:
            user = User.objects.get(pk=pk)
            user.is_active = not user.is_active
            user.save()
            status_text = 'activated' if user.is_active else 'deactivated'
            return JsonResponse({'success': True, 'message': f'User {user.username} {status_text} successfully'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# apps/users/views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.models import Group
from django.contrib.auth.hashers import make_password
from .forms import UserCreateForm, UserUpdateForm
from apps.core.models import Person

@login_required
@csrf_exempt
def create_user(request):
    """Create user via AJAX"""
    if request.method == 'POST':
        try:
            # Check if passwords match
            if request.POST.get('password1') != request.POST.get('password2'):
                return JsonResponse({'success': False, 'error': 'Passwords do not match'})
            
            user = User()
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.password = make_password(request.POST.get('password1'))
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()
            
            # Assign role/group
            group_id = request.POST.get('groups')
            if group_id:
                group = Group.objects.get(id=group_id)
                user.groups.add(group)
            
            # Link to person if provided
            person_id = request.POST.get('person')
            if person_id:
                person = Person.objects.get(id=person_id)
                person.system_user = user
                person.save()
            
            return JsonResponse({'success': True, 'message': f'User {user.username} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_user_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        user = User.objects.get(pk=pk)
        groups = Group.objects.all()
        persons = Person.objects.filter(is_active=True)
        user_groups = user.groups.all().values_list('id', flat=True)
        
        html = f'''
        <form id="editUserForm" method="POST" action="/users/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label required">Username</label>
                    <input type="text" name="username" class="form-control" value="{user.username}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label required">Email</label>
                    <input type="email" name="email" class="form-control" value="{user.email}" required>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">First Name</label>
                        <input type="text" name="first_name" class="form-control" value="{user.first_name or ''}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Last Name</label>
                        <input type="text" name="last_name" class="form-control" value="{user.last_name or ''}">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Role</label>
                    <select name="groups" class="form-select">
                        <option value="">Select Role</option>
        '''
        
        for group in groups:
            selected = 'selected' if group.id in user_groups else ''
            html += f'<option value="{group.id}" {selected}>{group.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Linked Person</label>
                    <select name="person" class="form-select">
                        <option value="">Select Person (Optional)</option>
        '''
        
        for person in persons:
            selected = 'selected' if user.person and user.person.id == person.id else ''
            html += f'<option value="{person.id}" {selected}>{person.get_full_name()} - {person.email}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="form-check mb-3">
                    <input type="checkbox" name="is_active" class="form-check-input" id="editIsActive" {'checked' if user.is_active else ''}>
                    <label class="form-check-label" for="editIsActive">Active</label>
                </div>
                <div class="form-check mb-3">
                    <input type="checkbox" name="is_staff" class="form-check-input" id="editIsStaff" {'checked' if user.is_staff else ''}>
                    <label class="form-check-label" for="editIsStaff">Staff Status</label>
                </div>
                <div class="form-check mb-3">
                    <input type="checkbox" name="is_superuser" class="form-check-input" id="editIsSuperuser" {'checked' if user.is_superuser else ''}>
                    <label class="form-check-label" for="editIsSuperuser">Superuser Status</label>
                </div>
                <div class="alert alert-info">
                    <i class="bx bx-info-circle me-1"></i>
                    <small>Password cannot be changed here. Use the security settings to change password.</small>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update User</button>
            </div>
        </form>
        
        <script>
            $('#editUserForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editUserModal')
            }});
            
            $('#editUserForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editUserModal').modal('hide');
                            toastr.success(response.message || 'User updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update user');
                            submitBtn.prop('disabled', false).html('Update User');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update User');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
@csrf_exempt
def update_user(request, pk):
    """Update user via AJAX"""
    if request.method == 'POST':
        try:
            user = User.objects.get(pk=pk)
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_superuser = request.POST.get('is_superuser') == 'on'
            user.save()
            
            # Update groups
            group_id = request.POST.get('groups')
            if group_id:
                user.groups.set([group_id])
            else:
                user.groups.clear()
            
            # Update linked person
            person_id = request.POST.get('person')
            if person_id:
                person = Person.objects.get(id=person_id)
                person.system_user = user
                person.save()
            
            return JsonResponse({'success': True, 'message': f'User {user.username} updated successfully'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@csrf_exempt
def toggle_user_status(request, pk):
    """Toggle user active status via AJAX"""
    if request.method == 'POST':
        try:
            user = User.objects.get(pk=pk)
            user.is_active = not user.is_active
            user.save()
            status_text = 'activated' if user.is_active else 'deactivated'
            return JsonResponse({'success': True, 'message': f'User {user.username} {status_text} successfully'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# apps/users/views.py (continued)
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

@login_required
@csrf_exempt
def create_role(request):
    """Create role via AJAX"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            if Group.objects.filter(name=name).exists():
                return JsonResponse({'success': False, 'error': 'Role with this name already exists'})
            
            group = Group.objects.create(name=name)
            
            # Assign permissions
            permission_ids = request.POST.getlist('permissions')
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            
            return JsonResponse({'success': True, 'message': f'Role {name} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_role_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        role = Group.objects.get(pk=pk)
        permissions = Permission.objects.all().order_by('content_type__app_label', 'codename')
        role_permissions = role.permissions.all().values_list('id', flat=True)
        
        # Group permissions by app label
        perms_by_app = {}
        for perm in permissions:
            app_label = perm.content_type.app_label
            if app_label not in perms_by_app:
                perms_by_app[app_label] = []
            perms_by_app[app_label].append(perm)
        
        html = f'''
        <form id="editRoleForm" method="POST" action="/users/roles/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-12">
                        <label class="form-label required">Role Name</label>
                        <input type="text" name="name" class="form-control" value="{role.name}" required>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Assign Permissions</label>
                        <div class="card">
                            <div class="card-body" style="max-height: 350px; overflow-y: auto;">
        '''
        
        for app_label, perms in perms_by_app.items():
            html += f'<div class="mb-3"><h6 class="text-primary mb-2 border-bottom pb-1">{app_label.title()}</h6>'
            for perm in perms:
                checked = 'checked' if perm.id in role_permissions else ''
                html += f'''
                <div class="form-check mb-1">
                    <input type="checkbox" name="permissions" value="{perm.id}" class="form-check-input" id="edit_perm_{perm.id}" {checked}>
                    <label class="form-check-label small" for="edit_perm_{perm.id}">
                        {perm.name}
                    </label>
                </div>
                '''
            html += '</div>'
        
        html += '''
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Role</button>
            </div>
        </form>
        
        <script>
            // Select All / Deselect All functionality
            const checkboxes = $('#editRoleForm input[type="checkbox"]');
            
            $('#editRoleForm').on('submit', function(e) {
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {
                        if (response.success) {
                            $('#editRoleModal').modal('hide');
                            toastr.success(response.message || 'Role updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        } else {
                            toastr.error(response.error || 'Failed to update role');
                            submitBtn.prop('disabled', false).html('Update Role');
                        }
                    },
                    error: function(xhr) {
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {
                            errorMsg = xhr.responseJSON.error;
                        }
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update Role');
                    }
                });
            });
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
@csrf_exempt
def update_role(request, pk):
    """Update role via AJAX"""
    if request.method == 'POST':
        try:
            role = Group.objects.get(pk=pk)
            new_name = request.POST.get('name')
            
            # Check if name already exists (excluding current role)
            if Group.objects.filter(name=new_name).exclude(pk=pk).exists():
                return JsonResponse({'success': False, 'error': 'Role with this name already exists'})
            
            role.name = new_name
            role.save()
            
            # Update permissions
            permission_ids = request.POST.getlist('permissions')
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
            else:
                role.permissions.clear()
            
            return JsonResponse({'success': True, 'message': f'Role {role.name} updated successfully'})
        except Group.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Role not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@csrf_exempt
def delete_role(request, pk):
    """Delete role via AJAX"""
    if request.method == 'POST':
        try:
            role = Group.objects.get(pk=pk)
            # Prevent deletion of system roles
            if role.name.lower() in ['admin', 'superadmin', 'system']:
                return JsonResponse({'success': False, 'error': 'System roles cannot be deleted'})
            role_name = role.name
            role.delete()
            return JsonResponse({'success': True, 'message': f'Role {role_name} deleted successfully'})
        except Group.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Role not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})