from django.http import JsonResponse
from django.db.models.functions import ExtractHour
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
import json

from apps.core.services import DashboardService
from apps.firmware.models import EdgeNode
from apps.core.models import Student, Staff, Department, Program, School
from apps.classroom.models import ClassAttendance
from apps.vms.models import VisitorVisit, VisitorMovement, BLETag
from apps.access.models import AccessLog


class DashboardHomeView(View):
    """Main dashboard view"""
    template_name = 'dashboard/index.html'

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # Basic counts
        total_students = Student.objects.filter(is_active=True).count()
        total_staff = Staff.objects.filter(is_active=True).count()
        total_departments = Department.objects.filter(is_active=True).count()
        total_programs = Program.objects.filter(is_active=True).count()
        total_schools = School.objects.filter(is_active=True).count()

        # Attendance statistics
        attendance_today = ClassAttendance.objects.filter(
            scan_time__date=today, verification_status='success'
        ).count()
        attendance_week = ClassAttendance.objects.filter(
            scan_time__date__gte=week_ago, verification_status='success'
        ).count()

        # Attendance trend (last 7 days)
        attendance_trend = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = ClassAttendance.objects.filter(
                scan_time__date=date, verification_status='success'
            ).count()
            attendance_trend.append(count)
        # Labels for last 7 days (short day names)
        attendance_labels = [(today - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]

        # Visitor statistics
        active_visitors = VisitorVisit.objects.filter(status='active').count()
        visitor_today = VisitorVisit.objects.filter(check_in_time__date=today).count()
        visitor_week = VisitorVisit.objects.filter(check_in_time__date__gte=week_ago).count()

        # Visitor peak hour (hour with most check-ins today)
        peak_hour_data = VisitorVisit.objects.filter(
        check_in_time__date=today
        ).annotate(
            hour=ExtractHour('check_in_time')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count').first()
        visitor_peak_hour = peak_hour_data['hour'] if peak_hour_data else None

        # Current visitor locations (simplified: from last movements)
        # Get latest movement for each active visitor
        latest_movements_qs = VisitorMovement.objects.filter(
        visitor__in=VisitorVisit.objects.filter(status='active').values('visitor')
        ).order_by('visitor', '-timestamp')

        # Manually pick latest per visitor
        seen = set()
        latest_movements = []

        for mv in latest_movements_qs:
            if mv.visitor_id not in seen:
                seen.add(mv.visitor_id)
                latest_movements.append(mv)

        # BLE Tag statistics
        total_tags = BLETag.objects.count()
        online_tags = BLETag.objects.filter(status='available').count()
        offline_tags = BLETag.objects.filter(status='assigned').count()   # adjust as per your statuses
        maintenance_tags = BLETag.objects.filter(status='maintenance').count()

        # Recent activity (combine attendance, visitor check-ins, access logs)
        recent_activity = []

        # Attendance activity
        recent_attendance = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        ).order_by('-scan_time')[:10]
        for att in recent_attendance:
            recent_activity.append({
                'type': 'attendance',
                'message': f"{att.student.person.full_name} checked in for {att.class_obj.class_code}",
                'timestamp': att.scan_time,
                'icon': 'calendar-check',
                'color': 'success'
            })

        # Visitor check-ins
        recent_visits = VisitorVisit.objects.select_related(
            'visitor__person'
        ).order_by('-check_in_time')[:10]
        for visit in recent_visits:
            recent_activity.append({
                'type': 'visitor',
                'message': f"Visitor {visit.visitor.person.full_name} checked in",
                'timestamp': visit.check_in_time,
                'icon': 'user-plus',
                'color': 'info'
            })

        # Access logs (denied attempts)
        recent_denied = AccessLog.objects.filter(
            result='denied'
        ).select_related('person', 'zone').order_by('-access_time')[:10]
        for log in recent_denied:
            recent_activity.append({
                'type': 'security',
                'message': f"Access denied for {log.person.full_name if log.person else 'Unknown'} at {log.zone.name if log.zone else 'Unknown'}",
                'timestamp': log.access_time,
                'icon': 'shield-x',
                'color': 'danger'
            })

        # Sort all activity by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)

        context = {
            'total_students': total_students,
            'total_staff': total_staff,
            'total_departments': total_departments,
            'total_programs': total_programs,
            'total_schools': total_schools,
            'attendance_today': attendance_today,
            'attendance_week': attendance_week,
            'attendance_labels': attendance_labels,
            'attendance_data': attendance_trend,
            'active_visitors': active_visitors,
            'visitor_today': visitor_today,
            'visitor_week': visitor_week,
            'visitor_peak_hour': visitor_peak_hour,
            
            'total_tags': total_tags,
            'online_tags': online_tags,
            'offline_tags': offline_tags,
            'maintenance_tags': maintenance_tags,
            'recent_activity': recent_activity[:5],  # Show top 5 recent activities
            'now': timezone.now(),
            'user_role': 'Admin' if user.is_superuser else ('Staff' if user.is_staff else 'User'),
        }
        return render(request, self.template_name, context)


def get_chart_data(request):
    """
    API endpoint to provide real-time data for dashboard charts.
    Called by JavaScript fetch() every 30 seconds.
    """
    try:
        today = timezone.now().date()
        
        # ============================================
        # 1. Attendance Data (This Week vs Previous Week)
        # ============================================
        weekly_attendance = []
        previous_week_attendance = []
        day_labels = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            day_labels.append(date.strftime('%a'))
            
            # This week's attendance
            count = ClassAttendance.objects.filter(
                scan_time__date=date,
                verification_status='success'
            ).count()
            weekly_attendance.append(count)
            
            # Previous week's attendance (same day last week)
            prev_date = date - timedelta(days=7)
            prev_count = ClassAttendance.objects.filter(
                scan_time__date=prev_date,
                verification_status='success'
            ).count()
            previous_week_attendance.append(prev_count)
        
        # ============================================
        # 2. Success Rate Calculation
        # ============================================
        total_attendance = ClassAttendance.objects.count()
        successful = ClassAttendance.objects.filter(verification_status='success').count()
        success_rate = round((successful / total_attendance * 100), 2) if total_attendance > 0 else 0
        
        # ============================================
        # 3. Visitor Data (Last 8 days)
        # ============================================
        daily_visitors = []
        for i in range(7, -1, -1):
            date = today - timedelta(days=i)
            count = VisitorVisit.objects.filter(
                check_in_time__date=date,
                status='completed'
            ).count()
            daily_visitors.append(count)
        
        # Calculate weekly visitor percentage
        total_weekly = sum(daily_visitors[:7])  # First 7 days of the array
        today_visitors = daily_visitors[-1] if daily_visitors else 0
        weekly_percentage = round((today_visitors / total_weekly * 100), 2) if total_weekly > 0 else 0
        
        # ============================================
        # 4. Tag Statistics (Device Status)
        # ============================================
        online_tags = EdgeNode.objects.filter(status='online').count()
        offline_tags = EdgeNode.objects.filter(status='offline').count()
        maintenance_tags = EdgeNode.objects.filter(status='maintenance').count()
        defective_tags = EdgeNode.objects.filter(status='defective').count()
        
        # ============================================
        # Prepare JSON Response
        # ============================================
        response_data = {
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
                'defective': defective_tags
            },
            'success_rate': success_rate,
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data, safe=False)
        
    except Exception as e:
        # Return fallback data if there's an error
        return JsonResponse({
            'error': str(e),
            'attendance': {
                'weekly': [12, 18, 15, 22, 28, 25, 20],
                'previous_week': [10, 14, 12, 18, 22, 20, 16],
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            },
            'visitors': {
                'daily_data': [24, 21, 30, 22, 42, 26, 35, 29],
                'weekly_percentage': 65
            },
            'tags': {
                'online': 85,
                'offline': 15,
                'maintenance': 50,
                'defective': 0
            },
            'success_rate': 78
        }, status=200)


# Optional: Cached version for better performance
from django.core.cache import cache

def get_cached_chart_data(request):
    """Cached version of chart data to reduce database queries"""
    cache_key = 'dashboard_chart_data'
    data = cache.get(cache_key)
    
    if not data:
        # Call the main function but with caching
        response = get_chart_data(request)
        data = json.loads(response.content)
        cache.set(cache_key, data, 30)  # Cache for 30 seconds
    
    return JsonResponse(data)


def home(request):
    return render(request, "home.html")


# -----------------------------
# AJAX ENDPOINT (FUNCTION VIEW)
# -----------------------------
# @login_required
# def get_chart_data(request):
#     """AJAX endpoint for real-time chart data"""
#     data = DashboardService.get_chart_data(request)
#     return JsonResponse(data)


# -----------------------------
# DASHBOARD HOME VIEW
# -----------------------------
# @method_decorator(login_required, name='dispatch')
# class DashboardHomeView(TemplateView):
#     """Main dashboard view"""
#     template_name = 'dashboard/index.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         stats = DashboardService.get_dashboard_stats(self.request.user)
#         chart_data = DashboardService.get_chart_data(self.request)

#         context['stats'] = stats
#         context['chart_data'] = chart_data

#         # safer + cleaner: avoid manual indexing loops in template
#         context['visitors_daily'] = chart_data['visitors']['daily_data']

#         return context
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
        
    #     from apps.classroom.models import ClassAttendance
    #     from apps.vms.models import VisitorVisit
    #     from apps.firmware.models import EdgeNode
    #     from apps.core.models import Student, Staff
        
    #     today = timezone.now().date()
    #     week_ago = today - timedelta(days=7)
        
    #     # Statistics
    #     context['stats'] = {
    #         'attendance_today': ClassAttendance.objects.filter(
    #             scan_time__date=today,
    #             verification_status='success'
    #         ).count(),
    #         'attendance_week': ClassAttendance.objects.filter(
    #             scan_time__date__gte=week_ago,
    #             verification_status='success'
    #         ).count(),
    #         'active_visitors': VisitorVisit.objects.filter(status='active').count(),
    #         'visitors_today': VisitorVisit.objects.filter(
    #             check_in_time__date=today
    #         ).count(),
    #         'total_students': Student.objects.filter(is_active=True).count(),
    #         'total_staff': Staff.objects.filter(is_active=True).count(),
    #         'online_devices': EdgeNode.objects.filter(status='online').count(),
    #         'total_devices': EdgeNode.objects.filter(is_active=True).count(),
    #     }
        
    #     # Chart data
    #     context['chart_data'] = self._get_chart_data()
        
    #     # Recent activity
    #     context['recent_activity'] = self._get_recent_activity()
        
    #     return context
    
    # def _get_chart_data(self):
    #     """Get chart data for dashboard"""
    #     from apps.classroom.models import ClassAttendance
    #     from apps.vms.models import VisitorVisit
    #     from django.db.models import Count
    #     from django.db.models.functions import TruncDate
    #     from datetime import timedelta
        
    #     end_date = timezone.now().date()
    #     start_date = end_date - timedelta(days=6)
        
    #     # Attendance trend
    #     attendance_data = ClassAttendance.objects.filter(
    #         scan_time__date__gte=start_date,
    #         verification_status='success'
    #     ).annotate(date=TruncDate('scan_time')).values('date').annotate(
    #         count=Count('id')
    #     ).order_by('date')
        
    #     # Visitor trend
    #     visitor_data = VisitorVisit.objects.filter(
    #         check_in_time__date__gte=start_date
    #     ).annotate(date=TruncDate('check_in_time')).values('date').annotate(
    #         count=Count('id')
    #     ).order_by('date')
        
    #     # Build complete date range
    #     dates = []
    #     attendance_counts = []
    #     visitor_counts = []
        
    #     current = start_date
    #     while current <= end_date:
    #         dates.append(current.strftime('%a, %b %d'))
            
    #         att = next((d for d in attendance_data if d['date'] == current), None)
    #         attendance_counts.append(att['count'] if att else 0)
            
    #         vis = next((d for d in visitor_data if d['date'] == current), None)
    #         visitor_counts.append(vis['count'] if vis else 0)
            
    #         current += timedelta(days=1)
        
    #     return {
    #         'labels': dates,
    #         'attendance': attendance_counts,
    #         'visitors': visitor_counts,
    #     }
    
    # def _get_recent_activity(self):
        # """Get recent activity feed"""
        # from apps.classroom.models import ClassAttendance
        # from apps.vms.models import VisitorVisit
        # from apps.access.models import AccessLog
        
        # activities = []
        
        # # Recent attendance
        # attendances = ClassAttendance.objects.select_related(
        #     'student__person', 'class_obj'
        # ).order_by('-scan_time')[:10]
        
        # for att in attendances:
        #     activities.append({
        #         'type': 'attendance',
        #         'title': 'Attendance Recorded',
        #         'message': f"{att.student.person.full_name} checked in for {att.class_obj.class_code}",
        #         'time': att.scan_time,
        #         'icon': 'fa-calendar-check',
        #         'color': 'green'
        #     })
        
        # # Recent visitor check-ins
        # checkins = VisitorVisit.objects.select_related(
        #     'visitor__person'
        # ).order_by('-check_in_time')[:10]
        
        # for visit in checkins:
        #     activities.append({
        #         'type': 'visitor',
        #         'title': 'Visitor Check-in',
        #         'message': f"Visitor {visit.visitor.person.full_name} checked in",
        #         'time': visit.check_in_time,
        #         'icon': 'fa-user-plus',
        #         'color': 'blue'
        #     })
        
        # # Sort by time
        # activities.sort(key=lambda x: x['time'], reverse=True)
        
        # return activities[:20]