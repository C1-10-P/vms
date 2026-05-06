# apps/dashboard/services.py
from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta


class DashboardDataService:
    """Service for dashboard data aggregation"""
    
    @staticmethod
    def get_dashboard_stats(user):
        """Get main dashboard statistics"""
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.firmware.models import EdgeNode
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        return {
            'attendance_today': ClassAttendance.objects.filter(
                scan_time__date=today,
                verification_status='success'
            ).count(),
            'attendance_week': ClassAttendance.objects.filter(
                scan_time__date__gte=week_ago,
                verification_status='success'
            ).count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'visitors_today': VisitorVisit.objects.filter(
                check_in_time__date=today
            ).count(),
            'online_devices': EdgeNode.objects.filter(status='online').count(),
            'total_devices': EdgeNode.objects.count(),
            'system_health': DashboardDataService._get_system_health(),
        }
    
    @staticmethod
    def get_recent_activity(limit=20):
        """Get recent activity feed"""
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.access.models import AccessLog
        
        activities = []
        
        # Recent attendance
        attendances = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        ).order_by('-scan_time')[:limit]
        
        for att in attendances:
            activities.append({
                'type': 'attendance',
                'message': f"{att.student.person.full_name} checked in for {att.class_obj.class_code}",
                'time': att.scan_time,
                'icon': 'fa-calendar-check',
                'color': 'green'
            })
        
        # Recent visitor check-ins
        checkins = VisitorVisit.objects.select_related(
            'visitor__person'
        ).order_by('-check_in_time')[:limit]
        
        for visit in checkins:
            activities.append({
                'type': 'visitor',
                'message': f"Visitor {visit.visitor.person.full_name} checked in",
                'time': visit.check_in_time,
                'icon': 'fa-user-plus',
                'color': 'blue'
            })
        
        # Sort by time and return top results
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:limit]
    
    @staticmethod
    def get_attendance_chart_data(days=7):
        """Get attendance chart data for the last N days"""
        from apps.classroom.models import ClassAttendance
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        data = ClassAttendance.objects.filter(
            scan_time__date__gte=start_date,
            verification_status='success'
        ).annotate(date=TruncDate('scan_time')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Fill in missing dates
        result = []
        current = start_date
        while current <= end_date:
            found = next((d for d in data if d['date'] == current), None)
            result.append({
                'date': current.strftime('%Y-%m-%d'),
                'count': found['count'] if found else 0
            })
            current += timedelta(days=1)
        
        return result
    
    @staticmethod
    def get_visitor_chart_data(days=7):
        """Get visitor chart data for the last N days"""
        from apps.vms.models import VisitorVisit
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        data = VisitorVisit.objects.filter(
            check_in_time__date__gte=start_date
        ).annotate(date=TruncDate('check_in_time')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        result = []
        current = start_date
        while current <= end_date:
            found = next((d for d in data if d['date'] == current), None)
            result.append({
                'date': current.strftime('%Y-%m-%d'),
                'count': found['count'] if found else 0
            })
            current += timedelta(days=1)
        
        return result
    
    @staticmethod
    def _get_system_health():
        """Get system health status"""
        from apps.firmware.models import EdgeNode, NodeHealth
        
        total = EdgeNode.objects.count()
        if total == 0:
            return {'status': 'unknown', 'message': 'No devices registered'}
        
        critical = NodeHealth.objects.filter(health_status='critical').count()
        degraded = NodeHealth.objects.filter(health_status='degraded').count()
        
        if critical > 0:
            return {'status': 'critical', 'message': f'{critical} devices need attention'}
        elif degraded > 0:
            return {'status': 'warning', 'message': f'{degraded} devices degraded'}
        else:
            return {'status': 'healthy', 'message': 'All systems operational'}