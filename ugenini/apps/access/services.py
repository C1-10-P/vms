from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from datetime import datetime, timedelta
import logging
import random
import string

from apps.core.models import Person, Student, Staff
from apps.access.models.zone import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.two_factor import TwoFactorSession
from apps.access.models.log import AccessLog

logger = logging.getLogger(__name__)


class AccessControlService:
    """
    Business logic for access control operations
    """
    
    @staticmethod
    def process_access_request(credential, zone_code, node_uuid):
        """
        Process an access request from ESP32 device
        """
        try:
            # Find the person by credential (tag UUID, RFID, or ID)
            person = AccessControlService._find_person_by_credential(credential)
            
            if not person:
                return {
                    'granted': False,
                    'reason': 'Invalid credential',
                    'timestamp': timezone.now().isoformat()
                }
            
            # Find the zone
            zone = AccessZone.objects.get(code=zone_code, is_active=True)
            
            # Check if zone requires 2FA
            if zone.requires_2fa:
                # Create 2FA session
                session = AccessControlService._create_2fa_session(person, zone)
                
                return {
                    'granted': False,
                    'requires_2fa': True,
                    'session_token': session.session_token,
                    'message': '2FA verification required',
                    'timestamp': timezone.now().isoformat()
                }
            
            # Check access permission
            has_access = AccessControlService._check_access_permission(person, zone)
            
            # Log the access attempt
            AccessLog.objects.create(
                person=person,
                person_type=person.person_type,
                zone=zone,
                verification_method='tag',
                result='granted' if has_access else 'denied',
                reason=None if has_access else 'Permission denied',
                access_time=timezone.now(),
                response_time_ms=0,
                credential_used=credential
            )
            
            return {
                'granted': has_access,
                'reason': None if has_access else 'Permission denied',
                'person_name': person.full_name,
                'zone_name': zone.name,
                'timestamp': timezone.now().isoformat()
            }
            
        except AccessZone.DoesNotExist:
            return {
                'granted': False,
                'reason': 'Zone not found',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Access request failed: {e}")
            return {
                'granted': False,
                'reason': 'System error',
                'timestamp': timezone.now().isoformat()
            }
    
    @staticmethod
    def _find_person_by_credential(credential):
        """
        Find person by credential (tag UUID, RFID, National ID, etc.)
        """
        # Check by BLE tag
        from apps.vms.models import BLETag
        tag = BLETag.objects.filter(tag_uuid=credential, status='assigned').first()
        if tag and tag.current_visitor:
            return tag.current_visitor.person
        
        # Check by RFID/Student ID
        student = Student.objects.filter(student_reg_number=credential, is_active=True).first()
        if student:
            return student.person
        
        # Check by National ID
        person = Person.objects.filter(national_id=credential, is_active=True).first()
        if person:
            return person
        
        return None
    
    @staticmethod
    def _check_access_permission(person, zone):
        """
        Check if a person has permission to access a zone
        """
        # Super admins have access to everything
        if hasattr(person, 'system_user') and person.system_user.is_superuser:
            return True
        
        # Check for specific person permission
        specific_permission = AccessPermission.objects.filter(
            zone=zone,
            specific_person=person,
            is_active=True
        ).first()
        
        if specific_permission and specific_permission.is_valid_now():
            return True
        
        # Check by person type
        type_permission = AccessPermission.objects.filter(
            zone=zone,
            person_type=person.person_type,
            is_active=True
        ).first()
        
        if type_permission and type_permission.is_valid_now():
            # Additional checks for students/staff
            if person.person_type == 'student' and hasattr(person, 'student'):
                student = person.student
                if type_permission.year_of_study and student.current_year != type_permission.year_of_study:
                    return False
                if type_permission.department and student.department != type_permission.department:
                    return False
                return True
                
            elif person.person_type == 'staff' and hasattr(person, 'staff'):
                staff = person.staff
                if type_permission.department and staff.department != type_permission.department:
                    return False
                if type_permission.staff_category and staff.staff_category != type_permission.staff_category:
                    return False
                return True
            
            return True
        
        # Check zone's default access level
        if zone.access_level == 1:  # Public
            return True
        elif zone.access_level == 2 and person.person_type in ['staff', 'student']:  # Staff/Student only
            return True
        elif zone.access_level == 3 and person.person_type == 'staff':  # Staff only
            return True
        
        return False
    
    @staticmethod
    def _create_2fa_session(person, zone):
        """
        Create a 2FA session for access verification
        """
        # Generate OTP code
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Create session
        session = TwoFactorSession.objects.create(
            person=person,
            zone=zone,
            session_token=AccessControlService._generate_session_token(),
            otp_code=otp_code,
            phone_number=person.phone_number,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # In production, send OTP via SMS/USSD here
        # For now, log it
        logger.info(f"2FA OTP for {person.full_name}: {otp_code}")
        
        return session
    
    @staticmethod
    def _generate_session_token():
        """
        Generate a unique session token
        """
        import uuid
        return str(uuid.uuid4()).replace('-', '')[:32]
    
    @staticmethod
    def verify_2fa(session_token, code):
        """
        Verify 2FA code
        """
        try:
            session = TwoFactorSession.objects.get(session_token=session_token)
            success, message = session.verify(code)
            
            if success:
                # Grant access after successful 2FA
                has_access = AccessControlService._check_access_permission(session.person, session.zone)
                
                AccessLog.objects.create(
                    person=session.person,
                    person_type=session.person.person_type,
                    zone=session.zone,
                    verification_method='ussd',
                    result='granted' if has_access else 'denied',
                    two_factor_used=True,
                    two_factor_verified=True,
                    access_time=timezone.now()
                )
                
                return {
                    'success': True,
                    'granted': has_access,
                    'message': message
                }
            
            return {
                'success': False,
                'granted': False,
                'message': message
            }
            
        except TwoFactorSession.DoesNotExist:
            return {
                'success': False,
                'granted': False,
                'message': 'Session not found'
            }
    
    @staticmethod
    def get_zone_occupancy(zone_id):
        """
        Get current occupancy for a zone
        """
        zone = AccessZone.objects.get(id=zone_id)
        
        return {
            'zone_id': zone.id,
            'zone_name': zone.name,
            'current_occupancy': zone.current_occupancy,
            'capacity': zone.capacity,
            'percentage': (zone.current_occupancy / zone.capacity * 100) if zone.capacity > 0 else 0,
            'is_full': zone.is_full,
            'last_updated': zone.updated_at
        }
    
    @staticmethod
    def update_zone_occupancy(zone_id, delta):
        """
        Update zone occupancy (called from movement signals)
        """
        try:
            zone = AccessZone.objects.get(id=zone_id)
            zone.update_occupancy(delta)
            return {'success': True, 'new_occupancy': zone.current_occupancy}
        except AccessZone.DoesNotExist:
            return {'success': False, 'error': 'Zone not found'}
    
    @staticmethod
    def get_access_statistics(hours=24):
        """
        Get access control statistics
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        
        logs = AccessLog.objects.filter(access_time__gte=cutoff)
        
        total = logs.count()
        granted = logs.filter(result='granted').count()
        denied = logs.filter(result='denied').count()
        
        # Most accessed zones
        top_zones = logs.values('zone__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Access by hour
        hourly = logs.extra(
            {'hour': "EXTRACT(HOUR FROM access_time)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        # 2FA usage
        two_factor_usage = logs.filter(two_factor_used=True).count()
        
        return {
            'period_hours': hours,
            'total_attempts': total,
            'granted': granted,
            'denied': denied,
            'success_rate': (granted / total * 100) if total > 0 else 0,
            'two_factor_usage': two_factor_usage,
            'top_zones': list(top_zones),
            'hourly_distribution': list(hourly)
        }