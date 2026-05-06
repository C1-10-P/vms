class UserService:
    @staticmethod
    def create_system_user(person, email, password, is_admin=False):
        """Create system user linked to a Person record"""
        from apps.users.models import User
        
        # Check if person already has a system user
        if hasattr(person, 'system_user'):
            raise ValueError("Person already has a system user")
        
        # Create user
        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            password=password,
            person=person,
            is_staff=is_admin,
        )
        
        # Assign appropriate permissions based on person type
        if person.person_type == 'staff':
            # if person.staff.staff_category == 'academic':
            #     user.groups.add(Group.objects.get(name='Lecturers'))
            # elif person.staff.staff_category == 'security':
            #     user.groups.add(Group.objects.get(name='Security'))
        # elif is_admin:
            user.is_superuser = True
        
        user.save()
        return user
    
    @staticmethod
    def get_or_create_system_user(person):
        """Get existing system user or create one"""
        if hasattr(person, 'system_user'):
            return person.system_user
        return None  # Manual creation required