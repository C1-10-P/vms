import uuid
import random
from datetime import datetime, timedelta
from django.utils import timezone
from faker import Faker

fake = Faker()

from apps.access.models.zone import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.two_factor import TwoFactorSession
from apps.access.models.log import AccessLog
from apps.core.models import Institution, Department, Person, Staff


class AccessDataSeeder:
    """Seed data for access control"""
    
    @staticmethod
    def seed_access_zones(institution, count=15):
        """Create access zones"""
        zones = []
        zone_templates = [
            ('Main Gate', 'MAIN_GATE', 'campus', 1),
            ('Engineering Building', 'ENG_BLDG', 'building', 1),
            ('Science Complex', 'SCI_COMPLEX', 'building', 1),
            ('Library', 'LIBRARY', 'building', 2),
            ('Server Room', 'SERVER_RM', 'restricted', 4),
            ('Research Lab', 'RESEARCH_LAB', 'lab', 3),
            ('Lecture Hall A', 'LECT_HALL_A', 'classroom', 1),
            ('Lecture Hall B', 'LECT_HALL_B', 'classroom', 1),
            ('Staff Office Area', 'STAFF_OFFICE', 'office', 2),
            ('Medical School', 'MED_SCHOOL', 'hospital', 2),
            ('Data Center', 'DATA_CENTER', 'server_room', 5),
            ('Chemistry Lab', 'CHEM_LAB', 'lab', 3),
            ('Physics Lab', 'PHYS_LAB', 'lab', 3),
            ('Administration Block', 'ADMIN_BLOCK', 'building', 2),
            ('Sports Complex', 'SPORTS_COMPLEX', 'building', 1)
        ]
        
        for name, code, zone_type, level in zone_templates[:count]:
            zone, created = AccessZone.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'zone_type': zone_type,
                    'institution': institution,
                    'access_level': level,
                    'requires_2fa': level >= 3,
                    'building': name.split()[0] if ' ' in name else name,
                    'capacity': random.randint(50, 500),
                    'is_active': True
                }
            )
            zones.append(zone)
        
        print(f"✓ Created {len(zones)} access zones")
        return zones
    
    @staticmethod
    def seed_access_permissions(zones, count=30):
        """Create access permissions"""
        permissions = []
        person_types = ['student', 'staff', 'visitor', 'all']
        departments = list(Department.objects.filter(is_active=True))
        
        for _ in range(count):
            zone = random.choice(zones)
            person_type = random.choice(person_types)
            
            permission, created = AccessPermission.objects.get_or_create(
                zone=zone,
                person_type=person_type,
                defaults={
                    'department': random.choice(departments) if person_type in ['student', 'staff'] else None,
                    'priority': random.randint(0, 10),
                    'monday': True,
                    'tuesday': True,
                    'wednesday': True,
                    'thursday': True,
                    'friday': True,
                    'saturday': random.choice([True, False]),
                    'sunday': random.choice([True, False]),
                    'start_time': '08:00' if zone.access_level >= 2 else None,
                    'end_time': '18:00' if zone.access_level >= 2 else None,
                    'is_active': True
                }
            )
            permissions.append(permission)
        
        print(f"✓ Created {len(permissions)} access permissions")
        return permissions
    
    @staticmethod
    def seed_access_logs(days_back=30, logs_per_day=50):
        """Create access logs"""
        logs = []
        persons = list(Person.objects.filter(is_active=True))
        zones = list(AccessZone.objects.filter(is_active=True))
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        current_date = start_date
        while current_date <= end_date:
            # Create logs for this day
            day_logs = min(logs_per_day, len(persons))
            selected_persons = random.sample(persons, day_logs)
            
            for person in selected_persons:
                zone = random.choice(zones)
                hour = random.randint(7, 22)
                minute = random.randint(0, 59)
                access_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                access_time = timezone.make_aware(access_time)
                
                # Check if person has permission
                has_permission = AccessDataSeeder._check_permission(person, zone)
                result = 'granted' if has_permission else 'denied'
                
                log, created = AccessLog.objects.get_or_create(
                    person=person,
                    zone=zone,
                    access_time=access_time,
                    defaults={
                        'person_type': person.person_type,
                        'verification_method': random.choice(['tag', 'rfid', 'face']),
                        'result': result,
                        'reason': '' if result == 'granted' else 'Permission denied',
                        'response_time_ms': random.randint(50, 300),
                        'ip_address': f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                    }
                )
                logs.append(log)
            
            current_date += timedelta(days=1)
        
        print(f"✓ Created {len(logs)} access logs")
        return logs
    
    @staticmethod
    def _check_permission(person, zone):
        """Check if person has permission to access zone"""
        # Super admin check
        if hasattr(person, 'system_user') and person.system_user.is_superuser:
            return True
        
        # Check specific permissions
        permission = AccessPermission.objects.filter(
            zone=zone,
            specific_person=person,
            is_active=True
        ).first()
        
        if permission:
            return permission.is_valid_now()
        
        # Check person type permission
        type_permission = AccessPermission.objects.filter(
            zone=zone,
            person_type=person.person_type,
            is_active=True
        ).first()
        
        if type_permission:
            return type_permission.is_valid_now()
        
        # Public zone
        return zone.access_level == 1
    
    @staticmethod
    def seed_two_factor_sessions(count=50):
        """Create 2FA sessions"""
        sessions = []
        persons = list(Person.objects.filter(is_active=True, phone_number__isnull=False))
        zones = list(AccessZone.objects.filter(requires_2fa=True))
        
        for _ in range(min(count, len(persons))):
            person = random.choice(persons)
            zone = random.choice(zones)
            
            session, created = TwoFactorSession.objects.get_or_create(
                session_token=str(uuid.uuid4()).replace('-', '')[:32],
                defaults={
                    'person': person,
                    'zone': zone,
                    'channel': random.choice(['sms', 'ussd']),
                    'otp_code': f"{random.randint(100000, 999999)}",
                    'phone_number': person.phone_number,
                    'expires_at': timezone.now() + timedelta(minutes=5),
                    'status': random.choice(['pending', 'verified', 'expired']),
                    'attempts': random.randint(0, 2)
                }
            )
            sessions.append(session)
        
        print(f"✓ Created {len(sessions)} 2FA sessions")
        return sessions