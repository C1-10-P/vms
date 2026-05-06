from itertools import count
import random
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth import get_user_model
User = get_user_model()

fake = Faker()

from apps.core.models import Person, Staff
from apps.users.permissions import VMSPermissions, RoleGroups


class UserPermissionSeeder:
    """Seed users and permissions for the system"""
    
    @staticmethod
    def create_permissions():
        """Create all custom permissions for VMS"""
        print("\n📋 Creating permissions...")
        
        # Get content types for each app
        app_models = {
            'core': ['person', 'student', 'staff', 'visitor', 'institution', 'department'],
            'attendance': ['classattendance', 'dailyattendancesummary'],
            'visitors': ['visitor', 'bletag', 'visitorvisit', 'visitormovement'],
            'access': ['accesszone', 'accesspermission', 'accesslog'],
            'devices': ['edgenode', 'firmwareversion', 'otasession'],
            'reports': ['report', 'reportschedule'],
        }
        
        permissions_created = []
        
        for app_label, models in app_models.items():
            for model_name in models:
                try:
                    content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                    
                    # Create standard CRUD permissions
                    for action in ['add', 'change', 'delete', 'view']:
                        codename = f"{action}_{model_name}"
                        name = f"Can {action} {model_name.replace('_', ' ')}"
                        
                        permission, created = Permission.objects.get_or_create(
                            codename=codename,
                            content_type=content_type,
                            defaults={'name': name}
                        )
                        if created:
                            permissions_created.append(codename)
                            
                except ContentType.DoesNotExist:
                    continue
        
        print(f"  ✓ Created {len(permissions_created)} permissions")
        return permissions_created
    
    @staticmethod
    def create_groups():
        """Create default user groups with permissions"""
        print("\n👥 Creating user groups...")
        
        groups_created = []
        
        for role_key, role_data in RoleGroups.ROLES.items():
            group, created = Group.objects.get_or_create(name=role_key)
            
            if created:
                groups_created.append(role_key)
                
                # Assign permissions based on role
                if role_data['permissions'] == 'all':
                    # Give all permissions
                    permissions = Permission.objects.all()
                    group.permissions.set(permissions)
                else:
                    # Give specific permissions
                    permissions = Permission.objects.filter(
                        codename__in=role_data['permissions']
                    )
                    group.permissions.set(permissions)
                
                print(f"  ✓ Created group: {role_key} with {group.permissions.count()} permissions")
        
        return groups_created
    
    @staticmethod
    def create_superuser():
        """Create superuser account"""
        print("\n👑 Creating superuser...")
        
        superuser, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin1@vms.com',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        
        if created:
            superuser.set_password('Admin@123456')
            superuser.save()
            print("  ✓ Superuser created: admin / Admin@123456")
        else:
            print("  ✓ Superuser already exists")
        
        return superuser
    
    @staticmethod
    def create_staff_users(count=10):
        """Create staff users with appropriate group assignments"""
        print(f"\n👨‍🏫 Creating {count} staff users...")
        
        # 1. Get Staff instances (NOT Person instances)
        staff_members = list(Staff.objects.filter(is_active=True))
        
        if not staff_members:
            print("  ⚠ No staff persons found. Run core seeder first.")
            return []
        
        users_created = []
        
        # Pre-fetch groups to avoid repeat queries
        groups = {
            'lecturer': Group.objects.filter(name='lecturer').first(),
            'hod': Group.objects.filter(name='hod').first(),
            'admin': Group.objects.filter(name='admin').first(),
            'security': Group.objects.filter(name='security').first(),
        }
        
        for staff_instance in staff_members[:count]:
            # 2. Access the Person object linked to this Staff
            person_details = staff_instance.person 
            
            # 3. Role Logic (Correctly checking staff_instance attributes)
            # Assuming you have an 'is_hod' boolean or similar on Staff
            if getattr(staff_instance, 'is_hod', False):
                role = 'hod'
            elif staff_instance.staff_category == 'academic':
                role = 'lecturer'
            elif staff_instance.staff_category == 'security':
                role = 'security'
            elif staff_instance.staff_category == 'administrative':
                role = 'admin'
            else:
                role = 'viewer'
        
            # 4. Correctly fetch name from person_details
            username = f"{person_details.first_name.lower()}.{person_details.last_name.lower()}"
            email = person_details.email or f"{username}@vms.com"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': person_details.first_name,
                    'last_name': person_details.last_name,
                    'is_active': True,
                    'is_staff': role in ['admin', 'hod']
                }
            )
            
            if created:
                user.set_password('Password@123')
                user.save()
                
                # Assign to group
                target_group = groups.get(role)
                if target_group:
                    user.groups.add(target_group)
                
                # 5. Link the User to the Person (if the field exists on Person)
                if hasattr(person_details, 'system_user'):
                    person_details.system_user = user
                    person_details.save()
                
                users_created.append(user)
                print(f"  ✓ Created user: {username} ({role})")
        
        return users_created
    
    @staticmethod
    def create_viewer_users(count=5):
        """Create viewer users for testing"""
        print(f"\n👁️ Creating {count} viewer users...")
        
        users_created = []
        viewer_group = Group.objects.filter(name='viewer').first()
        
        for i in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"viewer.{first_name.lower()}.{last_name.lower()}"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@vms.com",
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                    'is_staff': False
                }
            )
            
            if created:
                user.set_password('Viewer@123')
                user.save()
                
                if viewer_group:
                    user.groups.add(viewer_group)
                
                users_created.append(user)
                print(f"  ✓ Created viewer: {username}")
        
        return users_created
    
    @staticmethod
    def seed_all():
        """Run all user and permission seeders"""
        print("\n" + "="*50)
        print("👥 USER & PERMISSION SEEDER")
        print("="*50)
        
        # Step 1: Create permissions
        permissions = UserPermissionSeeder.create_permissions()
        
        # Step 2: Create groups
        groups = UserPermissionSeeder.create_groups()
        
        # Step 3: Create superuser
        superuser = UserPermissionSeeder.create_superuser()
        
        # Step 4: Create staff users (if staff exist)
        staff_users = UserPermissionSeeder.create_staff_users(count=10)
        
        # Step 5: Create viewer users
        viewer_users = UserPermissionSeeder.create_viewer_users(count=5)
        
        # Summary
        print("\n" + "="*50)
        print("📊 USER SEED SUMMARY")
        print("="*50)
        print(f"  • Permissions created: {len(permissions)}")
        print(f"  • Groups created: {len(groups)}")
        print(f"  • Superuser: 1")
        print(f"  • Staff users: {len(staff_users)}")
        print(f"  • Viewer users: {len(viewer_users)}")
        print(f"  • Total users: {User.objects.count()}")
        
        return {
            'permissions': permissions,
            'groups': groups,
            'superuser': superuser,
            'staff_users': staff_users,
            'viewer_users': viewer_users
        }


class UserPermissionCleaner:
    """Clean up users and permissions"""
    
    @staticmethod
    def clean_all():
        """Delete all non-superuser users and permissions"""
        print("\n" + "="*50)
        print("🧹 CLEANING USERS & PERMISSIONS")
        print("="*50)
        
        # Delete non-superuser users
        deleted_users = User.objects.filter(is_superuser=False).delete()
        print(f"  ✓ Deleted {deleted_users[0]} non-superuser users")
        
        # Delete custom permissions (optional)
        # Be careful - this may affect other apps
        # Permission.objects.filter(codename__startswith='can_').delete()
        
        print("  ✓ Cleanup complete")