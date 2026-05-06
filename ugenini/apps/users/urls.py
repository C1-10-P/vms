from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    #  User Management 
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    path('<int:pk>/activate/', views.user_activate, name='activate'),
    path('<int:pk>/deactivate/', views.user_deactivate, name='deactivate'),
    path('<int:pk>/edit/', views.get_user_edit_form, name='edit'),
    path('<int:pk>/update/', views.update_user, name='update'),
    path('<int:pk>/toggle-status/', views.toggle_user_status, name='toggle_status'),

    path('create/', views.create_user, name='create'),
    path('<int:pk>/detail/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit-form/', views.get_user_edit_form, name='edit_form'),
 

    
    #  User Permissions 
    path('<int:pk>/permissions/', views.UserPermissionsView.as_view(), name='permissions'),
    path('<int:pk>/groups/', views.UserGroupsView.as_view(), name='groups'),
    path('<int:pk>/permissions/add/', views.add_user_permission, name='add_permission'),
    path('<int:pk>/permissions/remove/', views.remove_user_permission, name='remove_permission'),
    
    #  Role/Group Management 
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role_edit'),
    path('roles/<int:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),

    path('roles/create/', views.create_role, name='role_create'),
    path('roles/<int:pk>/detail/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/<int:pk>/edit-form/', views.get_role_edit_form, name='role_edit_form'),
    path('roles/<int:pk>/update/', views.update_role, name='role_update'),
    path('roles/<int:pk>/delete/', views.delete_role, name='role_delete'),
    # path('roles/<int:pk>/edit/', views.get_role_edit_form, name='role_edit'),
    # path('roles/<int:pk>/update/', views.update_role, name='role_update'),
    # path('roles/<int:pk>/delete/', views.delete_role, name='role_delete'),
    
    #  Profile 
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('profile/sessions/', views.UserSessionsView.as_view(), name='sessions'),
    path('profile/sessions/<str:session_key>/revoke/', views.revoke_session, name='revoke_session'),
    
    #  Activity Logs 
    path('activity/', views.UserActivityLogView.as_view(), name='activity'),
    path('activity/<int:pk>/', views.ActivityDetailView.as_view(), name='activity_detail'),
    path('activity/export/', views.export_activity_logs, name='export_activity'),
    
    #  API Endpoints 
    path('api/users/', views.api_user_list, name='api_user_list'),
    path('api/users/<int:pk>/', views.api_user_detail, name='api_user_detail'),
    path('api/roles/', views.api_role_list, name='api_role_list'),
    path('api/permissions/', views.api_permission_list, name='api_permission_list'),
    
    #  AJAX Endpoints 
    path('ajax/check-username/', views.ajax_check_username, name='ajax_check_username'),
    path('ajax/check-email/', views.ajax_check_email, name='ajax_check_email'),
    path('ajax/user-search/', views.ajax_user_search, name='ajax_user_search'),
]