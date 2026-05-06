from django.db.models import Count, Q, Sum, Avg, Max
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service for dashboard statistics and real-time data
    """
    
    @staticmethod
    def get_dashboard_stats(user):
        """
        Get comprehensive dashboard statistics based on user permissions
        """
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit, VisitorMovement
        from apps.firmware.models import EdgeNode
        from apps.access.models import AccessLog
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'timestamp': timezone.now().isoformat(),
            'user': {
                'username': user.username,
                'role': DashboardService._get_user_role(user),
                'permissions': DashboardService._get_user_permissions(user)
            },
            'attendance': {},
            'visitors': {},
            'devices': {},
            'security': {},
            'recent_activity': []
        }
        
        # Attendance statistics
        stats['attendance'] = {
            'today': ClassAttendance.objects.filter(
                scan_time__date=today,
                verification_status='success'
            ).count(),
            'this_week': ClassAttendance.objects.filter(
                scan_time__date__gte=week_ago,
                verification_status='success'
            ).count(),
            'total': ClassAttendance.objects.filter(
                verification_status='success'
            ).count(),
            'success_rate': DashboardService._calculate_success_rate(),
            'trend': DashboardService._get_attendance_trend()
        }
        
        # Visitor statistics
        stats['visitors'] = {
            'active': VisitorVisit.objects.filter(status='active').count(),
            'today': VisitorVisit.objects.filter(
                check_in_time__date=today,
                status='completed'
            ).count(),
            'this_week': VisitorVisit.objects.filter(
                check_in_time__date__gte=week_ago,
                status='completed'
            ).count(),
            'peak_hour': DashboardService._get_visitor_peak_hour(),
            'current_locations': DashboardService._get_visitor_locations()
        }
        
        # Device statistics
        stats['devices'] = {
            'online': EdgeNode.objects.filter(status='online').count(),
            'offline': EdgeNode.objects.filter(status='offline').count(),
            'maintenance': EdgeNode.objects.filter(status='maintenance').count(),
            'total': EdgeNode.objects.count(),
            'health': DashboardService._get_device_health(),
            'last_heartbeats': DashboardService._get_recent_heartbeats()
        }
        
        # Security statistics
        stats['security'] = {
            'access_denied_today': AccessLog.objects.filter(
                access_time__date=today,
                result='denied'
            ).count(),
            'alerts_today': DashboardService._get_alerts_count(today),
            'active_2fa_sessions': DashboardService._get_active_2fa_sessions(),
            'suspicious_activity': DashboardService._get_suspicious_activity()
        }
        
        # Recent activity feed
        stats['recent_activity'] = DashboardService._get_recent_activity()
        
        return stats
    
    @staticmethod
    def _get_user_role(user):
        """Get user's primary role"""
        if user.is_superuser:
            return 'super_admin'
        if user.groups.exists():
            return user.groups.first().name
        return 'viewer'
    
    @staticmethod
    def _get_user_permissions(user):
        """Get user's permissions"""
        from apps.users.permissions import PermissionChecker
        return list(PermissionChecker.get_user_permissions(user))
    
    @staticmethod
    def _calculate_success_rate():
        """Calculate attendance success rate"""
        from apps.classroom.models import ClassAttendance
        
        total = ClassAttendance.objects.count()
        if total == 0:
            return 0
        success = ClassAttendance.objects.filter(verification_status='success').count()
        return round((success / total) * 100, 2)
    
    @staticmethod
    def _get_attendance_trend():
        """Get attendance trend for last 7 days"""
        from apps.classroom.models import ClassAttendance
        
        trend = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            count = ClassAttendance.objects.filter(
                scan_time__date=date,
                verification_status='success'
            ).count()
            trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count,
                'day': date.strftime('%A')
            })
        return trend
    
    @staticmethod
    def _get_visitor_peak_hour():
        """Get peak visitor hour"""
        from apps.vms.models import VisitorVisit
        from django.db.models.functions import ExtractHour
        
        peak = VisitorVisit.objects.filter(
            check_in_time__date=timezone.now().date()
        ).annotate(
            hour=ExtractHour('check_in_time')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        return peak['hour'] if peak else None
    
    @staticmethod
    def _get_visitor_locations():
        """Get current visitor locations"""
        from apps.vms.models import VisitorMovement
        from apps.access.models import AccessZone
        
        # Get latest movement for each active visitor
        latest_movements = VisitorMovement.objects.filter(
            timestamp__gte=timezone.now() - timedelta(minutes=15)
        ).values('visitor').annotate(
            last_time=Max('timestamp')
        )
        
        location_stats = {}
        for zone in AccessZone.objects.filter(is_active=True):
            count = VisitorMovement.objects.filter(
                zone=zone,
                timestamp__gte=timezone.now() - timedelta(minutes=15),
                event_type='enter'
            ).exclude(
                visitor__in=VisitorMovement.objects.filter(
                    zone=zone,
                    timestamp__gte=timezone.now() - timedelta(minutes=15),
                    event_type='exit'
                ).values('visitor')
            ).values('visitor').distinct().count()
            
            if count > 0:
                location_stats[zone.name] = count
        
        return location_stats
    
    @staticmethod
    def _get_device_health():
        """Get device health statistics"""
        from apps.firmware.models import NodeHealth
        
        return {
            'healthy': NodeHealth.objects.filter(health_status='healthy').count(),
            'degraded': NodeHealth.objects.filter(health_status='degraded').count(),
            'critical': NodeHealth.objects.filter(health_status='critical').count()
        }
    
    @staticmethod
    def _get_recent_heartbeats():
        """Get recent device heartbeats"""
        from apps.firmware.models import NodeHeartbeat
        
        return list(NodeHeartbeat.objects.filter(
            timestamp__gte=timezone.now() - timedelta(minutes=5)
        ).values('node__name', 'timestamp', 'rssi', 'battery_level')[:10])
    
    @staticmethod
    def _get_alerts_count(date):
        """Get alerts count for a date"""
        from apps.vms.models import VisitorAlert
        
        return VisitorAlert.objects.filter(
            triggered_at__date=date,
            status='new'
        ).count()
    
    @staticmethod
    def _get_active_2fa_sessions():
        """Get active 2FA sessions count"""
        from apps.access.models import TwoFactorSession
        
        return TwoFactorSession.objects.filter(
            status='pending',
            expires_at__gt=timezone.now()
        ).count()
    
    @staticmethod
    def _get_suspicious_activity():
        """Get suspicious activity count"""
        from apps.access.models import AccessLog
        
        return AccessLog.objects.filter(
            access_time__gte=timezone.now() - timedelta(hours=24),
            result__in=['denied', 'blocked']
        ).count()
    
    @staticmethod
    def _get_recent_activity():
        """Get combined recent activity feed"""
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit, VisitorMovement
        from apps.access.models import AccessLog
        from apps.firmware.models import NodeHeartbeat
        from django.utils import timezone
        from datetime import timedelta

        activity = []

        # Attendance activity
        attendances = ClassAttendance.objects.select_related(
            'student__person',
            'class_obj__academic_unit'   
        ).order_by('-scan_time')[:10]

        for att in attendances:

            academic_unit = getattr(att.class_obj, "academic_unit", None)
            unit_name = getattr(academic_unit, "name", att.class_obj.class_code)

            activity.append({
                'type': 'attendance',
                'message': f"{att.student.person.full_name} checked in for {unit_name}",
                'status': att.verification_status,
                'timestamp': att.scan_time.isoformat(),
                'icon': 'check-circle',
                'color': 'success'
            })

        # Visitor check-ins
        checkins = VisitorVisit.objects.select_related(
            'visitor__person'
        ).order_by('-check_in_time')[:10]

        for visit in checkins:
            activity.append({
                'type': 'visitor',
                'message': f"Visitor {visit.visitor.person.full_name} checked in",
                'status': visit.status,
                'timestamp': visit.check_in_time.isoformat(),
                'icon': 'user-plus',
                'color': 'info'
            })

        # Access logs
        access_logs = AccessLog.objects.select_related(
            'person', 'zone'
        ).filter(
            result__in=['denied', 'blocked']
        ).order_by('-access_time')[:10]

        for log in access_logs:
            # Compute zone_name first so you can reuse it
            zone_name = getattr(log.zone, 'name', 'Unknown zone')
            
            activity.append({
                'type': 'security',
                'zone_name': zone_name, 
                'message': f"Access {log.result} for {log.person.full_name if log.person else 'Unknown'} at {zone_name}",
                'status': log.result,
                'timestamp': log.access_time.isoformat(),
                'icon': 'exclamation-triangle',
                'color': 'danger'
            })

        # Device heartbeats
        heartbeats = NodeHeartbeat.objects.select_related('node').filter(
            timestamp__gte=timezone.now() - timedelta(minutes=5)
        ).order_by('-timestamp')[:10]

        for hb in heartbeats:
            activity.append({
                'type': 'device',
                'message': f"Device {hb.node.name} heartbeat received",
                'status': 'online',
                'timestamp': hb.timestamp.isoformat(),
                'icon': 'microchip',
                'color': 'secondary'
            })

        # Sort by timestamp and return top 5
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity[:5]
    
    @staticmethod
    def get_realtime_stats():
        """
        Get real-time statistics for WebSocket updates
        """
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.firmware.models import EdgeNode
        
        return {
            'current_attendance': ClassAttendance.objects.filter(
                scan_time__gte=timezone.now() - timedelta(minutes=5)
            ).count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'online_devices': EdgeNode.objects.filter(status='online').count(),
            'timestamp': timezone.now().isoformat()
        }


    @staticmethod
    def get_chart_data(request):
        """Get real-time data for charts"""

        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.firmware.models import EdgeNode
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()

        # -----------------------------
        # 1. WEEKLY ATTENDANCE (LAST 7 DAYS)
        # -----------------------------
        weekly_attendance = []
        previous_week_attendance = []
        day_labels = []

        for i in range(6, -1, -1):   # FIX: exactly 7 days
            date = today - timedelta(days=i)
            day_labels.append(date.strftime('%a'))

            weekly_attendance.append(
                ClassAttendance.objects.filter(
                    scan_time__date=date,
                    verification_status='success'
                ).count()
            )

            previous_week_attendance.append(
                ClassAttendance.objects.filter(
                    scan_time__date=date - timedelta(days=7),
                    verification_status='success'
                ).count()
            )

        # -----------------------------
        # 2. DAILY VISITORS (LAST 7 DAYS)
        # -----------------------------
        daily_visitors = []

        for i in range(6, -1, -1):   # FIX: align with labels
            date = today - timedelta(days=i)

            daily_visitors.append(
                VisitorVisit.objects.filter(
                    check_in_time__date=date,
                    status='completed'
                ).count()
            )

        # -----------------------------
        # 3. EDGE NODE STATUS
        # -----------------------------
        online_tags = EdgeNode.objects.filter(status='online').count()
        offline_tags = EdgeNode.objects.filter(status='offline').count()
        maintenance_tags = EdgeNode.objects.filter(status='maintenance').count()

        # -----------------------------
        # 4. SUCCESS RATE
        # -----------------------------
        total_attendance = ClassAttendance.objects.count()
        successful = ClassAttendance.objects.filter(
            verification_status='success'
        ).count()

        success_rate = round(
            (successful / total_attendance * 100) if total_attendance else 0,
            2
        )

        # -----------------------------
        # 5. WEEKLY VISITOR PERCENTAGE
        # -----------------------------
        week_start = today - timedelta(days=6)

        weekly_visitors_total = VisitorVisit.objects.filter(
            check_in_time__date__gte=week_start,
            status='completed'
        ).count()

        today_visitors = daily_visitors[-1] if daily_visitors else 0

        weekly_percentage = round(
            (today_visitors / weekly_visitors_total * 100)
            if weekly_visitors_total else 0,
            2
        )

        # -----------------------------
        # RESPONSE
        # -----------------------------
        return {
            'attendance': {
                'weekly': weekly_attendance,
                'previous_week': previous_week_attendance,
                'labels': day_labels
            },
            'visitors': {
                'daily_data': daily_visitors,
                'weekly_percentage': weekly_percentage
            },
            'tags': {
                'online': online_tags,
                'offline': offline_tags,
                'maintenance': maintenance_tags,
                'defective': 0
            },
            'success_rate': success_rate
        }


class InstitutionService:
    """
    Service for institution hierarchy CRUD operations
    """
    
    @staticmethod
    def create_institution(data):
        """Create new institution"""
        from apps.core.models import Institution
        
        institution = Institution.objects.create(
            name=data.get('name'),
            code=data.get('code'),
            abbreviation=data.get('abbreviation', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            website=data.get('website', ''),
            established_year=data.get('established_year'),
            motto=data.get('motto', ''),
            vision=data.get('vision', ''),
            mission=data.get('mission', ''),
            vice_chancellor=data.get('vice_chancellor', ''),
            registrar=data.get('registrar', '')
        )
        
        # Clear cache
        cache.delete('institutions_list')
        
        return institution
    
    @staticmethod
    def update_institution(institution_id, data):
        """Update existing institution"""
        from apps.core.models import Institution
        
        institution = Institution.objects.get(id=institution_id)
        
        for key, value in data.items():
            if hasattr(institution, key) and value is not None:
                setattr(institution, key, value)
        
        institution.save()
        cache.delete(f'institution_{institution_id}')
        cache.delete('institutions_list')
        
        return institution
    
    @staticmethod
    def delete_institution(institution_id, soft=True):
        """Delete institution (soft or hard)"""
        from apps.core.models import Institution
        
        institution = Institution.objects.get(id=institution_id)
        
        if soft:
            institution.soft_delete()
        else:
            institution.delete()
        
        cache.delete(f'institution_{institution_id}')
        cache.delete('institutions_list')
        
        return True
    
    @staticmethod
    def get_institution(institution_id):
        """Get institution by ID with caching"""
        cache_key = f'institution_{institution_id}'
        institution = cache.get(cache_key)
        
        if not institution:
            from apps.core.models import Institution
            institution = Institution.objects.get(id=institution_id)
            cache.set(cache_key, institution, 3600)
        
        return institution
    
    @staticmethod
    def get_all_institutions():
        """Get all institutions with caching"""
        cache_key = 'institutions_list'
        institutions = cache.get(cache_key)
        
        if not institutions:
            from apps.core.models import Institution
            institutions = list(Institution.objects.filter(is_active=True))
            cache.set(cache_key, institutions, 3600)
        
        return institutions


class CollegeService:
    """Service for college CRUD operations"""
    
    @staticmethod
    def create_college(data):
        from apps.core.models import College
        college = College.objects.create(**data)
        cache.delete(f'colleges_{data["institution_id"]}')
        return college
    
    @staticmethod
    def update_college(college_id, data):
        from apps.core.models import College
        college = College.objects.get(id=college_id)
        for key, value in data.items():
            if hasattr(college, key) and value is not None:
                setattr(college, key, value)
        college.save()
        cache.delete(f'college_{college_id}')
        return college
    
    @staticmethod
    def delete_college(college_id, soft=True):
        from apps.core.models import College
        college = College.objects.get(id=college_id)
        if soft:
            college.soft_delete()
        else:
            college.delete()
        return True


class SchoolService:
    """Service for school CRUD operations"""
    
    @staticmethod
    def create_school(data):
        from apps.core.models import School
        school = School.objects.create(**data)
        cache.delete(f'schools_{data["college_id"]}')
        return school
    
    @staticmethod
    def update_school(school_id, data):
        from apps.core.models import School
        school = School.objects.get(id=school_id)
        for key, value in data.items():
            if hasattr(school, key) and value is not None:
                setattr(school, key, value)
        school.save()
        return school


class DepartmentService:
    """Service for department CRUD operations"""
    
    @staticmethod
    def create_department(data):
        from apps.core.models import Department
        department = Department.objects.create(**data)
        cache.delete(f'departments_{data["school_id"]}')
        return department
    
    @staticmethod
    def update_department(department_id, data):
        from apps.core.models import Department
        department = Department.objects.get(id=department_id)
        for key, value in data.items():
            if hasattr(department, key) and value is not None:
                setattr(department, key, value)
        department.save()
        return department


class ProgramService:
    """Service for program CRUD operations"""
    
    @staticmethod
    def create_program(data):
        from apps.core.models import Program
        program = Program.objects.create(**data)
        return program
    
    @staticmethod
    def update_program(program_id, data):
        from apps.core.models import Program
        program = Program.objects.get(id=program_id)
        for key, value in data.items():
            if hasattr(program, key) and value is not None:
                setattr(program, key, value)
        program.save()
        return program


class PersonService:
    """Service for person CRUD operations"""
    
    @staticmethod
    def create_person(data):
        from apps.core.models import Person
        
        person = Person.objects.create(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            national_id=data.get('national_id'),
            person_type=data.get('person_type'),
            date_of_birth=data.get('date_of_birth'),
            gender=data.get('gender')
        )
        
        # Create related record based on person_type
        if data.get('person_type') == 'student':
            from apps.core.models import Student
            Student.objects.create(
                person=person,
                student_reg_number=data.get('student_reg_number'),
                program_id=data.get('program_id'),
                department_id=data.get('department_id'),
                school_id=data.get('school_id'),
                college_id=data.get('college_id'),
                institution_id=data.get('institution_id'),
                current_year=data.get('current_year', 1),
                current_semester=data.get('current_semester', 1),
                admission_date=data.get('admission_date', timezone.now().date())
            )
        elif data.get('person_type') == 'staff':
            from apps.core.models import Staff
            Staff.objects.create(
                person=person,
                staff_number=data.get('staff_number'),
                department_id=data.get('department_id'),
                school_id=data.get('school_id'),
                college_id=data.get('college_id'),
                institution_id=data.get('institution_id'),
                staff_category=data.get('staff_category', 'academic'),
                employment_type=data.get('employment_type', 'full_time'),
                joined_date=data.get('joined_date', timezone.now().date())
            )
        
        return person
    
    @staticmethod
    def update_person(person_id, data):
        from apps.core.models import Person
        person = Person.objects.get(id=person_id)
        
        for key, value in data.items():
            if hasattr(person, key) and value is not None:
                setattr(person, key, value)
        
        person.save()
        return person