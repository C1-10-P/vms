from .models import VisitorSession
from typing import Dict
import uuid
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from datetime import datetime, timedelta
import logging
import uuid

from apps.core.models import Person, Staff
from apps.vms.models.blacklist import BlacklistedVisitor
from .models import Visitor, BLETag, VisitorVisit, VisitorMovement, VisitorAlert

logger = logging.getLogger(__name__)


class VisitorService:
    """Complete business logic for visitor management"""
    
    @staticmethod
    def process_visitor_checkin(self, data, staff_user=None): # Added staff_user param
        """Process visitor check-in with full validation"""
        try:
            with transaction.atomic():
                # Check if visitor already exists
                visitor = Visitor.objects.filter(
                    id_number=data.get('national_id'),
                    is_active=True
                ).first()
                
                if not visitor:
                    # Create new person
                    person = Person.objects.create(
                        first_name=data.get('first_name'),
                        last_name=data.get('last_name'),
                        email=data.get('email', ''),
                        phone_number=data.get('phone_number'),
                        national_id=data.get('national_id'),
                        person_type='visitor',
                        is_active=True
                    )
                    
                    # Find host if provided
                    host = None
                    if data.get('host_email'):
                        host = Staff.objects.filter(
                            person__email=data.get('host_email')
                        ).first()
                    
                    # Create visitor
                    visitor = Visitor.objects.create(
                        person=person,
                        purpose=data.get('purpose', 'meeting'),
                        purpose_description=data.get('purpose_description', ''),
                        host_person=host.person if host else None,
                        host_department=host.department if host else None,
                        id_type='national_id',
                        id_number=data.get('national_id'),
                        organization=data.get('organization', ''),
                        institution_id=1,
                        is_active=True
                    )
                
                # Start a new visit
                visit = visitor.start_new_visit()
                
                # --- FIXED TAG ASSIGNMENT ---
                tag_id = data.get('tag_id') # Get the specific tag from the form
                if tag_id:
                    tag = BLETag.objects.filter(id=tag_id, status='available').first()
                    if tag:
                        # VALIDATE STAFF: You cannot pass None here because of your DB constraint
                        # We use the staff_user passed from the view
                        if staff_user:
                            tag.assign_to_visitor(visitor, staff_user)
                            visit.assigned_tag = tag
                            visit.save(update_fields=['assigned_tag'])
                        else:
                            # If no staff user, we log a warning but allow check-in 
                            # OR raise an error if tag assignment is mandatory
                            logger.warning(f"Visitor {visitor.id} check-in: No staff provided for tag assignment.")

                # Cache active visitor
                cache_key = f"active_visitor_{visitor.id}"
                cache.set(cache_key, True, timeout=3600)
                
                return {
                    'success': True,
                    'visitor_id': visitor.id,
                    'visit_id': visit.id,
                    'tag_id': tag.tag_uuid if (tag_id and tag) else None,
                    'message': 'Visitor checked in successfully'
                }
                
        except Exception as e:
            logger.error(f"Visitor check-in failed: {e}")
            # Re-raise or return failure
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def process_visitor_checkout(tag):
        """Process visitor check-out by tag"""
        try:
            with transaction.atomic():
                if not tag.current_visitor:
                    return {'success': False, 'error': 'Tag not assigned to any visitor'}
                
                visitor = tag.current_visitor
                visitor.end_current_visit()
                tag.release(None)
                
                # Clear cache
                cache_key = f"active_visitor_{visitor.id}"
                cache.delete(cache_key)
                
                return {
                    'success': True,
                    'visitor_id': visitor.id,
                    'message': 'Visitor checked out successfully'
                }
                
        except Exception as e:
            logger.error(f"Visitor check-out failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def track_visitor_movement(tag_uuid, zone_code, node_uuid, rssi=None):
        """Track visitor movement between zones"""
        try:
            from apps.access.models import AccessZone
            from apps.firmware.models import EdgeNode
            
            tag = BLETag.objects.get(tag_uuid=tag_uuid)
            
            if not tag.current_visitor:
                return {'success': False, 'error': 'Tag not assigned'}
            
            zone = AccessZone.objects.get(code=zone_code)
            node = EdgeNode.objects.get(node_uuid=node_uuid) if node_uuid else None
            
            # Check if this is an enter or exit event
            last_movement = VisitorMovement.objects.filter(
                tag=tag,
                visitor=tag.current_visitor
            ).order_by('-timestamp').first()
            
            event_type = 'ping'
            if not last_movement or last_movement.zone != zone:
                event_type = 'enter'
                
                # Check if this is a restricted zone
                if zone.access_level >= 3 and not VisitorService._check_zone_permission(tag.current_visitor, zone):
                    VisitorAlert.objects.create(
                        visitor=tag.current_visitor,
                        tag=tag,
                        visit=tag.current_visitor.current_visit,
                        zone=zone,
                        alert_type='zone_breach',
                        severity='high',
                        message=f"Visitor entered restricted zone: {zone.name}"
                    )
                    event_type = 'alert'
            
            # Create movement record
            movement = VisitorMovement.objects.create(
                visitor=tag.current_visitor,
                tag=tag,
                visit=tag.current_visitor.current_visit,
                zone=zone,
                node=node,
                event_type=event_type,
                timestamp=timezone.now(),
                rssi=rssi
            )
            
            # Update tag's last known location
            tag.last_known_zone = zone
            tag.last_ping_time = timezone.now()
            tag.last_rssi = rssi
            tag.save(update_fields=['last_known_zone', 'last_ping_time', 'last_rssi'])
            
            # Update zone occupancy
            if event_type == 'enter':
                zone.update_occupancy(1)
            elif event_type == 'exit':
                zone.update_occupancy(-1)
            
            return {
                'success': True,
                'visitor_id': tag.current_visitor.id,
                'zone': zone.name,
                'event_type': event_type,
                'movement_id': movement.id
            }
            
        except BLETag.DoesNotExist:
            return {'success': False, 'error': 'Tag not found'}
        except AccessZone.DoesNotExist:
            return {'success': False, 'error': 'Zone not found'}
        except Exception as e:
            logger.error(f"Movement tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _check_zone_permission(visitor, zone):
        """Check if visitor has permission to enter zone"""
        from apps.access.models import AccessPermission
        
        # Check if there's a specific permission for this visitor
        permission = AccessPermission.objects.filter(
            zone=zone,
            specific_person=visitor.person,
            is_active=True
        ).first()
        
        if permission and permission.is_valid_now():
            return True
        
        # Check general visitor permissions
        general_permission = AccessPermission.objects.filter(
            zone=zone,
            person_type='visitor',
            is_active=True
        ).first()
        
        if general_permission and general_permission.is_valid_now():
            return True
        
        # Public zones only
        return zone.access_level <= 1
    
    @staticmethod
    def get_active_visitors():
        """Get all currently active visitors with their locations"""
        active_visits = VisitorVisit.objects.filter(
            status='active'
        ).select_related('visitor__person', 'assigned_tag')
        
        visitors = []
        for visit in active_visits:
            # Get last known location
            last_movement = VisitorMovement.objects.filter(
                visitor=visit.visitor
            ).order_by('-timestamp').first()
            
            visitors.append({
                'id': visit.visitor.id,
                'name': visit.visitor.person.full_name,
                'check_in_time': visit.check_in_time,
                'tag_id': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                'last_location': last_movement.zone.name if last_movement and last_movement.zone else 'Unknown',
                'last_seen': last_movement.timestamp if last_movement else visit.check_in_time
            })
        
        return visitors
    
    @staticmethod
    def get_visitor_history(visitor_id, days=30):
        """Get visitor's visit history with analytics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        visits = VisitorVisit.objects.filter(
            visitor_id=visitor_id,
            check_in_time__gte=cutoff_date
        ).order_by('-check_in_time')
        
        history = []
        for visit in visits:
            # Get zones visited during this visit
            zones = VisitorMovement.objects.filter(
                visit=visit,
                event_type='enter'
            ).values('zone__name').distinct()
            
            # Calculate duration
            duration = None
            if visit.check_out_time:
                duration_seconds = (visit.check_out_time - visit.check_in_time).total_seconds()
                duration = round(duration_seconds / 3600, 2)
            
            history.append({
                'visit_id': visit.id,
                'check_in': visit.check_in_time.isoformat(),
                'check_out': visit.check_out_time.isoformat() if visit.check_out_time else None,
                'duration_hours': duration,
                'zones_visited': [z['zone__name'] for z in zones],
                'status': visit.status
            })
        
        return {
            'visitor_id': visitor_id,
            'total_visits': len(history),
            'average_duration': sum(v['duration_hours'] for v in history if v['duration_hours']) / len(history) if history else 0,
            'history': history
        }
    
    @staticmethod
    def blacklist_visitor(visitor_id, reason, blacklisted_by):
        """Add visitor to blacklist"""
        try:
            visitor = Visitor.objects.get(id=visitor_id)
            
            blacklist_entry = BlacklistedVisitor.objects.create(
                visitor=visitor,
                reason_category='other',
                reason_description=reason,
                blacklisted_by=blacklisted_by,
                expires_at=timezone.now() + timedelta(days=365)
            )
            
            visitor.blacklisted = True
            visitor.save(update_fields=['blacklisted'])
            
            # End any active visit
            if visitor.current_visit:
                visitor.end_current_visit()
            
            return {'success': True, 'blacklist_id': blacklist_entry.id}
            
        except Visitor.DoesNotExist:
            return {'success': False, 'error': 'Visitor not found'}
    
    @staticmethod
    def get_visitor_statistics(days=30):
        """Get comprehensive visitor statistics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        visits = VisitorVisit.objects.filter(check_in_time__gte=cutoff_date)
        
        # Daily visitor count
        daily_visitors = visits.extra(
            {'date': "DATE(check_in_time)"}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Most common purposes
        purposes = Visitor.objects.values('purpose').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Top organizations
        organizations = Visitor.objects.exclude(
            organization=''
        ).values('organization').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Average visit duration
        completed_visits = visits.filter(check_out_time__isnull=False)
        total_duration = 0
        for visit in completed_visits:
            duration = (visit.check_out_time - visit.check_in_time).total_seconds()
            total_duration += duration
        
        avg_duration_hours = (total_duration / len(completed_visits) / 3600) if completed_visits.exists() else 0
        
        # Peak hours
        peak_hours = visits.extra(
            {'hour': "EXTRACT(HOUR FROM check_in_time)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return {
            'period_days': days,
            'total_visitors': Visitor.objects.filter(is_active=True).count(),
            'total_visits': visits.count(),
            'unique_visitors': visits.values('visitor').distinct().count(),
            'daily_average': round(visits.count() / days, 1),
            'average_duration_hours': round(avg_duration_hours, 2),
            'daily_trend': list(daily_visitors),
            'top_purposes': list(purposes),
            'top_organizations': list(organizations),
            'peak_hours': list(peak_hours)
        }
    

class VisitorSessionService:
    """
    Service for managing visitor check-in/out sessions
    """
    
    @staticmethod
    def create_checkin_session(extracted_data: Dict, scan_device: str = None) -> Dict:
        """
        Create a visitor check-in session from OCR/QR data
        """
        from .models import VisitorSession
        
        session_id = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(minutes=10)  # 10 minute window
        
        # Check if visitor already exists
        from apps.core.models import Person
        existing_person = None
        if extracted_data.get('id_number'):
            existing_person = Person.objects.filter(
                national_id=extracted_data['id_number']
            ).first()
        
        session = VisitorSession.objects.create(
            session_id=session_id,
            session_type='checkin',
            extracted_data=extracted_data,
            scan_method='ocr',
            scan_device=scan_device,
            expires_at=expires_at,
            status='awaiting_info' if not existing_person else 'awaiting_tag'
        )
        
        return {
            'success': True,
            'session_id': session_id,
            'expires_at': expires_at.isoformat(),
            'existing_visitor': existing_person is not None,
            'visitor_name': existing_person.full_name if existing_person else None,
            'message': 'Session created. ' + ('Please assign a tag.' if existing_person else 'Please complete visitor information.')
        }
    
    @staticmethod
    def complete_checkin_session(session_id: str, additional_info: Dict = None) -> Dict:
        """
        Complete a visitor check-in session
        """
        from .models import VisitorSession, Visitor, VisitorVisit
        from apps.core.models import Person
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            
            if not session.is_valid():
                return {'success': False, 'error': 'Session expired'}
            
            # Check if visitor already exists
            person = None
            id_number = session.extracted_data.get('id_number')
            if id_number:
                person = Person.objects.filter(national_id=id_number).first()
            
            if not person:
                # Create new person
                person = Person.objects.create(
                    first_name=session.extracted_data.get('first_name', ''),
                    last_name=session.extracted_data.get('last_name', ''),
                    email=additional_info.get('email', '') if additional_info else '',
                    phone_number=session.extracted_data.get('phone_number', '') or 
                                 (additional_info.get('phone_number', '') if additional_info else ''),
                    national_id=id_number,
                    person_type='visitor',
                    is_active=True
                )
            
            # Create or get visitor
            visitor, _ = Visitor.objects.get_or_create(
                person=person,
                defaults={
                    'institution_id': 1,  # Default institution
                    'purpose': session.extracted_data.get('purpose', 'meeting'),
                    'id_type': 'national_id',
                    'id_number': id_number or '',
                    'organization': session.extracted_data.get('organization', '')
                }
            )
            
            # Start visit
            visit = visitor.start_new_visit()
            
            # Complete session
            session.complete_checkin(visitor, visit)
            
            return {
                'success': True,
                'visitor_id': visitor.id,
                'visit_id': visit.id,
                'visitor_name': person.full_name,
                'message': 'Visitor checked in successfully'
            }
            
        except VisitorSession.DoesNotExist:
            return {'success': False, 'error': 'Session not found'}
    
    @staticmethod
    def create_tag_assignment_session(visitor_id: int) -> Dict:
        """
        Create a session for tag assignment
        """
        from .models import VisitorSession, Visitor
        
        try:
            visitor = Visitor.objects.get(id=visitor_id)
            
            session_id = str(uuid.uuid4())
            expires_at = timezone.now() + timedelta(minutes=5)
            
            session = VisitorSession.objects.create(
                session_id=session_id,
                session_type='tag_assign',
                visitor=visitor,
                expires_at=expires_at,
                status='pending'
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'visitor_id': visitor.id,
                'visitor_name': visitor.person.full_name,
                'expires_at': expires_at.isoformat()
            }
            
        except Visitor.DoesNotExist:
            return {'success': False, 'error': 'Visitor not found'}
    
    @staticmethod
    def complete_tag_assignment(session_id: str, tag_uuid: str) -> Dict:
        """
        Complete tag assignment for a visitor
        """
        from .models import VisitorSession, BLETag
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            
            if not session.is_valid():
                return {'success': False, 'error': 'Session expired'}
            
            tag = BLETag.objects.get(tag_uuid=tag_uuid, status='available')
            result = session.assign_tag(tag)
            
            return result
            
        except VisitorSession.DoesNotExist:
            return {'success': False, 'error': 'Session not found'}
        except BLETag.DoesNotExist:
            return {'success': False, 'error': 'Tag not found or not available'}