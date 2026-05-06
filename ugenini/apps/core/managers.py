from django.db import models
from django.utils import timezone
from datetime import timedelta


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def active(self):
        """Get only active records"""
        return self.get_queryset()
    
    def archived(self):
        """Get only archived (soft-deleted) records"""
        return super().get_queryset().filter(is_active=False)
    
    def all_including_archived(self):
        """Get all records including archived"""
        return super().get_queryset()


class PersonManager(SoftDeleteManager):
    """
    Custom manager for Person model with common filters
    """
    def students(self):
        """Get only students"""
        return self.filter(person_type='student')
    
    def staff(self):
        """Get only staff"""
        return self.filter(person_type='staff')
    
    def visitors(self):
        """Get only visitors"""
        return self.filter(person_type='visitor')
    
    def by_department(self, department_id):
        """Get persons by department"""
        from apps.core.models import Student, Staff
        student_ids = Student.objects.filter(department_id=department_id).values_list('person_id', flat=True)
        staff_ids = Staff.objects.filter(department_id=department_id).values_list('person_id', flat=True)
        return self.filter(id__in=list(student_ids) + list(staff_ids))
    
    def search(self, query):
        """Search persons by name, email, or ID"""
        return self.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(phone_number__icontains=query) |
            models.Q(national_id__icontains=query)
        )
    
    def active_today(self):
        """Get persons active today (has attendance or visit)"""
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        
        today = timezone.now().date()
        attendance_persons = ClassAttendance.objects.filter(
            scan_time__date=today
        ).values_list('student__person_id', flat=True)
        visitor_persons = VisitorVisit.objects.filter(
            check_in_time__date=today
        ).values_list('visitor__person_id', flat=True)
        
        return self.filter(id__in=list(attendance_persons) + list(visitor_persons))


class InstitutionManager(SoftDeleteManager):
    """
    Custom manager for Institution model
    """
    def with_statistics(self):
        """Get institutions with annotated statistics"""
        from django.db.models import Count
        return self.annotate(
            college_count=Count('colleges', filter=models.Q(colleges__is_active=True)),
            student_count=Count('students', filter=models.Q(students__is_active=True)),
            staff_count=Count('staff', filter=models.Q(staff__is_active=True))
        )
    
    def search(self, query):
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(code__icontains=query) |
            models.Q(abbreviation__icontains=query)
        )


class StudentManager(SoftDeleteManager):
    """
    Custom manager for Student model
    """
    def active(self):
        """Get active students"""
        return self.filter(status='active')
    
    def graduating(self):
        """Get students expected to graduate this year"""
        current_year = timezone.now().year
        return self.filter(
            expected_graduation__year=current_year,
            status='active'
        )
    
    def by_program(self, program_id):
        """Get students by program"""
        return self.filter(program_id=program_id, is_active=True)
    
    def by_year(self, year):
        """Get students by current year of study"""
        return self.filter(current_year=year, is_active=True)
    
    def with_attendance_stats(self, days=30):
        """Get students with attendance statistics"""
        from django.db.models import Count, Q
        from apps.classroom.models import ClassAttendance
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return self.annotate(
            attendance_count=Count('attendances', filter=Q(
                attendances__scan_time__gte=cutoff_date,
                attendances__verification_status='success'
            )),
            total_classes=Count('classes', filter=Q(classes__is_active=True))
        )
    
    def search(self, query):
        """Search students by registration number or name"""
        return self.filter(
            models.Q(student_reg_number__icontains=query) |
            models.Q(person__first_name__icontains=query) |
            models.Q(person__last_name__icontains=query)
        )


class StaffManager(SoftDeleteManager):
    """
    Custom manager for Staff model
    """
    def academic(self):
        """Get academic staff only"""
        return self.filter(staff_category='academic')
    
    def hod(self):
        """Get Heads of Department"""
        return self.filter(is_hod=True)
    
    def dean(self):
        """Get Deans"""
        return self.filter(is_dean=True)
    
    def by_department(self, department_id):
        """Get staff by department"""
        return self.filter(department_id=department_id, is_active=True)
    
    def by_category(self, category):
        """Get staff by category"""
        return self.filter(staff_category=category, is_active=True)


class VisitorManager(SoftDeleteManager):
    """
    Custom manager for Visitor model
    """
    def active(self):
        """Get visitors currently on campus"""
        from apps.vms.models import VisitorVisit
        active_visit_ids = VisitorVisit.objects.filter(
            status='active'
        ).values_list('visitor_id', flat=True)
        return self.filter(id__in=active_visit_ids)
    
    def blacklisted(self):
        """Get blacklisted visitors"""
        return self.filter(blacklisted=True)
    
    def frequent(self, min_visits=5):
        """Get frequent visitors"""
        return self.filter(total_visits__gte=min_visits)
    
    def today(self):
        """Get visitors who checked in today"""
        today = timezone.now().date()
        from apps.vms.models import VisitorVisit
        visitor_ids = VisitorVisit.objects.filter(
            check_in_time__date=today
        ).values_list('visitor_id', flat=True)
        return self.filter(id__in=visitor_ids)
    
    def search(self, query):
        """Search visitors by name or ID"""
        return self.filter(
            models.Q(person__first_name__icontains=query) |
            models.Q(person__last_name__icontains=query) |
            models.Q(id_number__icontains=query) |
            models.Q(organization__icontains=query)
        )


class ClassAttendanceManager(models.Manager):
    """
    Custom manager for ClassAttendance model
    """
    def today(self):
        """Get today's attendance records"""
        return self.filter(scan_time__date=timezone.now().date())
    
    def successful(self):
        """Get successful attendance records"""
        return self.filter(verification_status='success')
    
    def failed(self):
        """Get failed attendance records"""
        return self.filter(verification_status='failed')
    
    def by_student(self, student_id, days=30):
        """Get student attendance for last N days"""
        cutoff = timezone.now() - timedelta(days=days)
        return self.filter(student_id=student_id, scan_time__gte=cutoff)
    
    def by_class(self, class_id, date=None):
        """Get attendance for a specific class"""
        queryset = self.filter(class_obj_id=class_id)
        if date:
            queryset = queryset.filter(scan_time__date=date)
        return queryset
    
    def get_daily_summary(self, date=None):
        """Get daily attendance summary"""
        from django.db.models import Count
        
        if not date:
            date = timezone.now().date()
        
        return self.filter(scan_time__date=date).values(
            'class_obj__class_code'
        ).annotate(
            present=Count('id', filter=models.Q(verification_status='success')),
            absent=Count('id', filter=models.Q(verification_status='failed')),
            total=Count('id')
        )
    
    def get_weekly_stats(self):
        """Get weekly attendance statistics"""
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        
        week_ago = timezone.now() - timedelta(days=7)
        return self.filter(
            scan_time__gte=week_ago,
            verification_status='success'
        ).annotate(
            date=TruncDate('scan_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')


class AccessLogManager(models.Manager):
    """
    Custom manager for AccessLog model
    """
    def today(self):
        """Get today's access logs"""
        return self.filter(access_time__date=timezone.now().date())
    
    def denied(self):
        """Get denied access attempts"""
        return self.filter(result='denied')
    
    def granted(self):
        """Get granted access attempts"""
        return self.filter(result='granted')
    
    def by_person(self, person_id, days=30):
        """Get person's access logs"""
        cutoff = timezone.now() - timedelta(days=days)
        return self.filter(person_id=person_id, access_time__gte=cutoff)
    
    def by_zone(self, zone_id, date=None):
        """Get access logs for a zone"""
        queryset = self.filter(zone_id=zone_id)
        if date:
            queryset = queryset.filter(access_time__date=date)
        return queryset
    
    def get_failure_rate(self, hours=24):
        """Get failure rate for last N hours"""
        from django.db.models import Count
        
        cutoff = timezone.now() - timedelta(hours=hours)
        logs = self.filter(access_time__gte=cutoff)
        
        total = logs.count()
        if total == 0:
            return 0
        
        failures = logs.filter(result='denied').count()
        return (failures / total) * 100


class EdgeNodeManager(models.Manager):
    """
    Custom manager for EdgeNode model
    """
    def online(self):
        """Get online nodes"""
        return self.filter(status='online')
    
    def offline(self):
        """Get offline nodes"""
        return self.filter(status='offline')
    
    def by_type(self, node_type):
        """Get nodes by type"""
        return self.filter(node_type=node_type)
    
    def with_heartbeat(self, minutes=5):
        """Get nodes with recent heartbeat"""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return self.filter(last_heartbeat__gte=cutoff)
    
    def needs_maintenance(self):
        """Get nodes that need maintenance"""
        return self.filter(
            models.Q(status='error') |
            models.Q(battery_level__lt=20) |
            models.Q(last_heartbeat__lt=timezone.now() - timedelta(minutes=30))
        )
    
    def get_health_summary(self):
        """Get health summary for all nodes"""
        from django.db.models import Count
        
        return {
            'total': self.count(),
            'online': self.online().count(),
            'offline': self.offline().count(),
            'maintenance': self.filter(status='maintenance').count(),
            'by_type': self.values('node_type').annotate(count=Count('id')),
            'low_battery': self.filter(battery_level__lt=20).count()
        }


class BLETagManager(models.Manager):
    """
    Custom manager for BLETag model
    """
    def available(self):
        """Get available tags"""
        return self.filter(status='available')
    
    def assigned(self):
        """Get assigned tags"""
        return self.filter(status='assigned')
    
    def low_battery(self, threshold=20):
        """Get tags with low battery"""
        return self.filter(battery_level__lte=threshold)
    
    def needs_charging(self):
        """Get tags that need charging"""
        return self.filter(
            models.Q(battery_level__lt=15) |
            models.Q(last_charged__lt=timezone.now() - timedelta(days=30))
        )
    
    def get_usage_stats(self):
        """Get tag usage statistics"""
        from django.db.models import Avg, Sum
        
        return {
            'total': self.count(),
            'available': self.available().count(),
            'assigned': self.assigned().count(),
            'avg_battery': self.aggregate(Avg('battery_level'))['battery_level__avg'],
            'total_assignments': self.aggregate(Sum('total_assignments'))['total_assignments__sum'],
            'total_hours': self.aggregate(Sum('total_hours_used'))['total_hours_used__sum']
        }


class VisitorMovementManager(models.Manager):
    """
    Custom manager for VisitorMovement model
    """
    def recent(self, minutes=15):
        """Get recent movements"""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return self.filter(timestamp__gte=cutoff)
    
    def by_visitor(self, visitor_id, hours=24):
        """Get visitor's movements for last N hours"""
        cutoff = timezone.now() - timedelta(hours=hours)
        return self.filter(visitor_id=visitor_id, timestamp__gte=cutoff)
    
    def by_zone(self, zone_id, hours=24):
        """Get movements in a zone"""
        cutoff = timezone.now() - timedelta(hours=hours)
        return self.filter(zone_id=zone_id, timestamp__gte=cutoff)
    
    def get_current_locations(self):
        """Get current locations of all active visitors"""
        from django.db.models import Subquery, OuterRef
        
        # Get latest movement for each visitor
        latest_movement = self.filter(
            visitor=OuterRef('visitor')
        ).order_by('-timestamp')
        
        return self.filter(
            id=Subquery(latest_movement.values('id')[:1]),
            event_type='enter'
        ).select_related('visitor__person', 'zone')
    
    def get_heatmap_data(self, hours=24):
        """Get heatmap data for zone occupancy"""
        from django.db.models import Count
        
        cutoff = timezone.now() - timedelta(hours=hours)
        return self.filter(
            timestamp__gte=cutoff,
            event_type='enter'
        ).values('zone__name', 'zone__latitude', 'zone__longitude').annotate(
            count=Count('id')
        ).order_by('-count')