from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions as drf_permissions
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action, api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import College, School
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
User = get_user_model()

from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from apps.users.permissions import VMSPermissions, PermissionChecker
from apps.users.decorators import api_permission_required
from apps.classroom.models import ClassAttendance
from apps.classroom.serializers import AttendanceSerializer
from apps.vms.models import Visitor, VisitorVisit, BLETag
from apps.vms.serializers import VisitorSerializer, VisitorCheckinSerializer
from apps.access.models.zone import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.log import AccessLog
from apps.access.serializers import AccessLogSerializer, AccessZoneSerializer
from apps.firmware.models import EdgeNode
from apps.firmware.serializers import EdgeNodeSerializer
from apps.core.models import Person, Student, Staff, Institution, Department, Class
from apps.core.serializers import PersonSerializer, StudentSerializer, StaffSerializer, InstitutionSerializer, DepartmentSerializer, ClassSerializer
from apps.api.v1.serializers import (
    UserSerializer, GroupSerializer, DashboardStatsSerializer,
    ChangePasswordSerializer, PasswordResetSerializer
)


#  Authentication Views 

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with additional user data"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            user = authenticate(
                username=request.data.get('username'),
                password=request.data.get('password')
            )
            
        person = getattr(user, "person", None)

        response.data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'permissions': list(PermissionChecker.get_user_permissions(user)),
            'role': PermissionChecker.get_user_role(user)
                }

        if person:
            response.data.setdefault('user', {}).setdefault('person', {
                'id': person.id,
                'name': person.full_name,
                'type':getattr(person, "person_type", None)
            })
        
        return response


class TokenRefreshView(APIView):
    """Refresh JWT token"""
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({'access': access_token})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Logout - blacklist refresh token"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    """Get current user information"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.data.get('old_password')):
                return Response({'error': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    """Request password reset"""
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.data.get('email')
            try:
                user = User.objects.get(email=email)
                # Send reset email logic here
                return Response({'message': 'Reset link sent to email'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Confirm password reset"""
    
    def post(self, request):
        # Implementation for password reset confirmation
        return Response({'message': 'Password reset confirmed'})


#  Dashboard Views 

class DashboardStatsView(APIView):
    """Get dashboard statistics"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'attendance': {
                'today': ClassAttendance.objects.filter(scan_time__date=today).count(),
                'this_week': ClassAttendance.objects.filter(scan_time__date__gte=week_ago).count(),
                'total': ClassAttendance.objects.count(),
            },
            'visitors': {
                'active': VisitorVisit.objects.filter(status='active').count(),
                'today': VisitorVisit.objects.filter(check_in_time__date=today).count(),
                'total_today': VisitorVisit.objects.filter(check_in_time__date=today).count(),
            },
            'devices': {
                'online': EdgeNode.objects.filter(status='online').count(),
                'offline': EdgeNode.objects.filter(status='offline').count(),
                'total': EdgeNode.objects.count(),
            },
            'security': {
                'access_denied_today': AccessLog.objects.filter(access_time__date=today, result='denied').count(),
                'active_alerts': 0,  # Add alert count
            }
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)


class RealtimeDashboardView(APIView):
    """Get real-time dashboard data"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        data = {
            'current_attendance': ClassAttendance.objects.filter(
                scan_time__gte=timezone.now() - timedelta(minutes=5)
            ).count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'online_devices': EdgeNode.objects.filter(status='online').count(),
            'timestamp': timezone.now().isoformat()
        }
        return Response(data)


class DashboardAlertsView(APIView):
    """Get dashboard alerts"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        alerts = []
        
        # Low battery devices
        low_battery = EdgeNode.objects.filter(battery_level__lt=20)
        for device in low_battery:
            alerts.append({
                'type': 'warning',
                'message': f'Device {device.name} has low battery ({device.battery_level}%)',
                'timestamp': timezone.now().isoformat()
            })
        
        # Offline devices
        offline = EdgeNode.objects.filter(status='offline')
        for device in offline:
            alerts.append({
                'type': 'danger',
                'message': f'Device {device.name} is offline',
                'timestamp': timezone.now().isoformat()
            })
        
        # Access denials
        denied_today = AccessLog.objects.filter(
            access_time__date=timezone.now().date(),
            result='denied'
        ).count()
        
        if denied_today > 10:
            alerts.append({
                'type': 'warning',
                'message': f'High number of access denials today ({denied_today})',
                'timestamp': timezone.now().isoformat()
            })
        
        return Response({'alerts': alerts})


#  ViewSets 

class AttendanceViewSet(ModelViewSet):
    """ViewSet for attendance records"""
    queryset = ClassAttendance.objects.select_related('student__person', 'class_obj')
    serializer_class = AttendanceSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [drf_permissions.IsAuthenticated()]
        return [drf_permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(scan_time__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(scan_time__date__lte=end_date)
        
        # Filter by student
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get attendance summary"""
        today = timezone.now().date()
        return Response({
            'today': self.queryset.filter(scan_time__date=today).count(),
            'total': self.queryset.count(),
        })
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get attendance trends"""
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        
        trends = self.queryset.filter(
            scan_time__gte=timezone.now() - timedelta(days=7)
        ).annotate(date=TruncDate('scan_time')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return Response({'trends': trends})


class VisitorViewSet(ModelViewSet):
    """ViewSet for visitors"""
    queryset = Visitor.objects.select_related('person', 'host_person')
    serializer_class = VisitorSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status == 'active':
            queryset = queryset.filter(current_visit__isnull=False)
        elif status == 'blacklisted':
            queryset = queryset.filter(blacklisted=True)
        
        return queryset


class ZoneViewSet(ReadOnlyModelViewSet):
    """ViewSet for access zones (read-only)"""
    queryset = AccessZone.objects.filter(is_active=True)
    serializer_class = AccessZoneSerializer


class DeviceViewSet(ModelViewSet):
    """ViewSet for edge devices"""
    queryset = EdgeNode.objects.filter(is_active=True)
    serializer_class = EdgeNodeSerializer
    
    @action(detail=True, methods=['post'])
    def reboot(self, request, pk=None):
        """Reboot a device"""
        device = self.get_object()
        # Send reboot command
        return Response({'status': 'reboot_command_sent'})


class UserViewSet(ReadOnlyModelViewSet):
    """ViewSet for users (read-only)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class ReportViewSet(APIView):
    """ViewSet for reports"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        return Response({'message': 'Report endpoint'})


#  Attendance Check-in View 

class AttendanceCheckInView(APIView):
    """API endpoint for attendance check-in"""
    permission_classes = [drf_permissions.IsAuthenticated]

    def post(self, request):
        student_id = request.data.get('student_id')
        class_code = request.data.get('class_code')

        try:
            student = Student.objects.get(student_reg_number=student_id)

            class_obj = Class.objects.select_related('academic_unit').get(
                class_code__iexact=class_code
            )

            academic_unit = class_obj.academic_unit

            unit_name = getattr(academic_unit, "name", class_obj.class_code)

            attendance, created = ClassAttendance.objects.get_or_create(
                student=student,
                class_obj=class_obj,
                defaults={
                    "scan_time": timezone.now(),
                    "verification_method": "api",
                    "verification_status": "success"
                }
            )

            serializer = AttendanceSerializer(attendance)

            return Response({
                **serializer.data,
                "course_name": unit_name   # 👈 add readable name here
            }, status=status.HTTP_201_CREATED)

        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)


class BulkAttendanceView(APIView):
    """Bulk attendance submission"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        records = request.data.get('records', [])
        created = []
        errors = []
        
        for record in records:
            try:
                attendance = ClassAttendance.objects.create(
                    student_id=record.get('student_id'),
                    class_obj_id=record.get('class_id'),
                    scan_time=timezone.now(),
                    verification_method='api'
                )
                created.append(attendance.id)
            except Exception as e:
                errors.append({'record': record, 'error': str(e)})
        
        return Response({
            'success': True,
            'created': len(created),
            'errors': errors
        })


class AttendanceSummaryView(APIView):
    """Get attendance summary"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        
        summary = {
            'today': ClassAttendance.objects.filter(scan_time__date=today).count(),
            'this_week': ClassAttendance.objects.filter(
                scan_time__date__gte=today - timedelta(days=7)
            ).count(),
            'this_month': ClassAttendance.objects.filter(
                scan_time__month=today.month,
                scan_time__year=today.year
            ).count(),
            'total': ClassAttendance.objects.count(),
            'by_method': list(ClassAttendance.objects.values('verification_method').annotate(
                count=Count('id')
            ))
        }
        
        return Response(summary)


class AttendanceTrendsView(APIView):
    """Get attendance trends"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        
        trends = ClassAttendance.objects.filter(
            scan_time__gte=timezone.now() - timedelta(days=30)
        ).annotate(date=TruncDate('scan_time')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return Response({'trends': trends})


class AttendanceExportView(APIView):
    """Export attendance data"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Student ID', 'Student Name', 'Class', 'Status'])
        
        attendances = ClassAttendance.objects.select_related('student__person', 'class_obj')
        for att in attendances:
            writer.writerow([
                att.scan_time.date(),
                att.student.student_reg_number,
                att.student.person.full_name,
                att.class_obj.class_code,
                att.verification_status
            ])
        
        return response


#  Visitor Check-in/out Views 

class VisitorCheckInView(APIView):
    permission_classes = [drf_permissions.IsAuthenticated]

    def post(self, request):
        serializer = VisitorCheckinSerializer(data=request.data)

        if serializer.is_valid():

            # FIX 1: prevent duplicate person crash
            person, created = Person.objects.get_or_create(
                national_id=serializer.validated_data['national_id'],
                defaults={
                    "first_name": serializer.validated_data['first_name'],
                    "last_name": serializer.validated_data['last_name'],
                    "email": serializer.validated_data.get('email', ''),
                    "phone_number": serializer.validated_data['phone_number'],
                    "person_type": "visitor"
                }
            )

            # FIX 2: institution required
            institution = getattr(request.user, "institution", None)

            if not institution:
                return Response(
                    {"detail": "User has no institution assigned"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # FIX 3: visitor creation
            visitor = Visitor.objects.create(
                person=person,
                institution=institution,
                purpose=serializer.validated_data['purpose'],
                organization=serializer.validated_data.get('organization', ''),
                id_number=serializer.validated_data['national_id']
            )

            visit = visitor.start_new_visit()

            return Response({
                'success': True,
                'visitor_id': visitor.id,
                'visit_id': visit.id,
                'message': 'Visitor checked in successfully'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VisitorCheckOutView(APIView):
    """API endpoint for visitor check-out"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request, tag_uuid):
        try:
            tag = BLETag.objects.get(tag_uuid=tag_uuid)
            
            if tag.current_visitor:
                tag.current_visitor.end_current_visit()
                tag.release(request.user.person.staff if hasattr(request.user, 'person') else None)
                
                return Response({
                    'success': True,
                    'message': 'Visitor checked out successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Tag not assigned to any visitor'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except BLETag.DoesNotExist:
            return Response({'error': 'Tag not found'}, status=status.HTTP_404_NOT_FOUND)


class VisitorTrackingView(APIView):
    """API endpoint for visitor tracking"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        active_visitors = VisitorVisit.objects.filter(status='active').select_related('visitor__person')
        
        data = [{
            'id': v.visitor.id,
            'name': v.visitor.person.full_name,
            'check_in_time': v.check_in_time,
            'tag_id': v.assigned_tag.tag_uuid if v.assigned_tag else None
        } for v in active_visitors]
        
        return Response({'active_visitors': data})


class VisitorBlacklistView(APIView):
    """API endpoint for visitor blacklisting"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        visitor_id = request.data.get('visitor_id')
        reason = request.data.get('reason')
        
        try:
            visitor = Visitor.objects.get(id=visitor_id)
            visitor.blacklisted = True
            visitor.blacklist_reason = reason
            visitor.save()
            
            return Response({'success': True, 'message': 'Visitor blacklisted'})
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)


class VisitorHistoryView(APIView):
    """API endpoint for visitor history"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        visitor_id = request.query_params.get('visitor_id')
        
        if visitor_id:
            visits = VisitorVisit.objects.filter(visitor_id=visitor_id).order_by('-check_in_time')
        else:
            visits = VisitorVisit.objects.all().order_by('-check_in_time')[:100]
        
        data = [{
            'id': v.id,
            'visitor_name': v.visitor.person.full_name,
            'check_in': v.check_in_time,
            'check_out': v.check_out_time,
            'status': v.status
        } for v in visits]
        
        return Response({'history': data})


#  Access Control Views 

class AccessRequestView(APIView):
    """API endpoint for access request"""
    
    def post(self, request):
        credential = request.data.get('credential')
        zone_code = request.data.get('zone_code')
        
        # Implementation
        return Response({'granted': True})


class AccessVerifyView(APIView):
    """API endpoint for access verification"""
    
    def post(self, request):
        # Implementation
        return Response({'verified': True})


class AccessLogView(APIView):
    """API endpoint for access logs"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        logs = AccessLog.objects.select_related('person', 'zone').order_by('-access_time')[:100]
        serializer = AccessLogSerializer(logs, many=True)
        return Response(serializer.data)


class AccessZoneView(APIView):
    """API endpoint for access zones"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        zones = AccessZone.objects.filter(is_active=True)
        serializer = AccessZoneSerializer(zones, many=True)
        return Response(serializer.data)


class AccessPermissionView(APIView):
    """API endpoint for access permissions"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        permissions = AccessPermission.objects.filter(is_active=True).select_related('zone')
        data = [{
            'id': p.id,
            'zone': p.zone.name,
            'person_type': p.person_type,
            'valid_from': p.valid_from,
            'valid_to': p.valid_to
        } for p in permissions]
        return Response({'permissions': data})


#  Device Views 

class DeviceHeartbeatView(APIView):
    """API endpoint for device heartbeat"""
    def post(self, request):
        # 1. Reach inside the 'data' wrapper safely
        payload = request.data.get('data', {}) 
        
        # 2. Get the UUID from the payload
        node_uuid = payload.get('node_uuid')
        
        if not node_uuid:
            return Response({'error': 'node_uuid is required inside the data object'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            node.last_heartbeat = timezone.now()
            node.status = 'online'
            # Update other fields if they are passed in the payload
            node.ip_address = payload.get('ip_address', node.ip_address)
            node.save()
            
            return Response({'status': 'ok'})
        except EdgeNode.DoesNotExist:
            return Response({'error': 'Node not found'}, status=status.HTTP_404_NOT_FOUND)


class DeviceRegisterView(APIView):
    """API endpoint for device registration"""
    
    def post(self, request):
        data = request.data
        
        node = EdgeNode.objects.create(
            node_uuid=data.get('node_uuid'),
            node_type=data.get('node_type'),
            name=data.get('name', data.get('node_uuid')[:8]),
            mac_address=data.get('mac_address'),
            firmware_version=data.get('firmware_version', '1.0.0')
        )
        
        return Response({
            'success': True,
            'node_id': node.id,
            'config': {
                'scan_interval': 30,
                'log_level': 'info'
            }
        })


class DeviceCommandView(APIView):
    """API endpoint for sending device commands"""
    
    def post(self, request):
        node_uuid = request.data.get('node_uuid')
        command = request.data.get('command')
        
        # Send command via MQTT
        return Response({'success': True, 'command_sent': command})


class FirmwareUpdateView(APIView):
    """API endpoint for firmware updates"""
    
    def post(self, request):
        node_uuid = request.data.get('node_uuid')
        firmware_url = request.data.get('firmware_url')
        
        # Trigger OTA update
        return Response({'success': True, 'update_initiated': True})


class OTAUpdateView(APIView):
    """API endpoint for OTA updates"""
    
    def post(self, request):
        # Implementation
        return Response({'success': True})


#  Report Views 

class ReportGenerateView(APIView):
    """API endpoint for report generation"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        report_type = request.data.get('report_type')
        format = request.data.get('format', 'json')
        
        # Generate report
        return Response({'message': f'Report {report_type} generated', 'format': format})


class ReportDownloadView(APIView):
    """API endpoint for report download"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request, pk):
        # Return report file
        return Response({'message': 'Report download'})


class ReportScheduleView(APIView):
    """API endpoint for report scheduling"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        # Schedule report
        return Response({'success': True})


#  Notification Views 

class NotificationView(APIView):
    """API endpoint for notifications"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        # Return user notifications
        return Response({'notifications': []})


class MarkNotificationReadView(APIView):
    """API endpoint to mark notification as read"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        notification_id = request.data.get('notification_id')
        return Response({'success': True})


class SubscribePushView(APIView):
    """API endpoint for push notification subscription"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def post(self, request):
        # Subscribe device for push notifications
        return Response({'success': True})


#  Search Views 

class GlobalSearchView(APIView):
    """Global search API endpoint"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        results = []
        
        # Search students
        students = Student.objects.filter(
            Q(student_reg_number__icontains=query) |
            Q(person__first_name__icontains=query) |
            Q(person__last_name__icontains=query)
        )[:5]
        
        for student in students:
            results.append({
                'type': 'student',
                'id': student.id,
                'name': student.person.full_name,
                'reg_number': student.student_reg_number
            })
        
        # Search visitors
        visitors = Visitor.objects.filter(
            Q(person__first_name__icontains=query) |
            Q(person__last_name__icontains=query) |
            Q(id_number__icontains=query)
        )[:5]
        
        for visitor in visitors:
            results.append({
                'type': 'visitor',
                'id': visitor.id,
                'name': visitor.person.full_name,
                'id_number': visitor.id_number
            })
        
        # Search devices
        devices = EdgeNode.objects.filter(
            Q(name__icontains=query) |
            Q(node_uuid__icontains=query) |
            Q(mac_address__icontains=query)
        )[:5]
        
        for device in devices:
            results.append({
                'type': 'device',
                'id': device.id,
                'name': device.name,
                'status': device.status
            })
        
        return Response({'results': results, 'query': query})


class StudentSearchView(APIView):
    """Student search API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        students = Student.objects.filter(
            Q(student_reg_number__icontains=query) |
            Q(person__first_name__icontains=query) |
            Q(person__last_name__icontains=query),
            is_active=True
        ).select_related('person')[:20]
        
        serializer = StudentSerializer(students, many=True)
        return Response({'students': serializer.data})


class VisitorSearchView(APIView):
    """Visitor search API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        visitors = Visitor.objects.filter(
            Q(person__first_name__icontains=query) |
            Q(person__last_name__icontains=query) |
            Q(id_number__icontains=query),
            is_active=True
        ).select_related('person')[:20]
        
        serializer = VisitorSerializer(visitors, many=True)
        return Response({'visitors': serializer.data})


class DeviceSearchView(APIView):
    """Device search API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        devices = EdgeNode.objects.filter(
            Q(name__icontains=query) |
            Q(node_uuid__icontains=query),
            is_active=True
        )[:20]
        
        serializer = EdgeNodeSerializer(devices, many=True)
        return Response({'devices': serializer.data})


#  Statistics Views 

class AttendanceStatsView(APIView):
    """Attendance statistics API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        from django.db.models import Count
        
        stats = {
            'total': ClassAttendance.objects.count(),
            'by_status': list(ClassAttendance.objects.values('verification_status').annotate(
                count=Count('id')
            )),
            'by_method': list(ClassAttendance.objects.values('verification_method').annotate(
                count=Count('id')
            )),
            'today': ClassAttendance.objects.filter(scan_time__date=timezone.now().date()).count()
        }
        
        return Response(stats)


class VisitorStatsView(APIView):
    """Visitor statistics API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        stats = {
            'total_visitors': Visitor.objects.count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'total_visits': VisitorVisit.objects.count(),
            'today_visits': VisitorVisit.objects.filter(check_in_time__date=timezone.now().date()).count()
        }
        
        return Response(stats)


class DeviceStatsView(APIView):
    """Device statistics API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        stats = {
            'total': EdgeNode.objects.count(),
            'online': EdgeNode.objects.filter(status='online').count(),
            'offline': EdgeNode.objects.filter(status='offline').count(),
            'by_type': list(EdgeNode.objects.values('node_type').annotate(count=Count('id')))
        }
        
        return Response(stats)


class AccessStatsView(APIView):
    """Access statistics API"""
    permission_classes = [drf_permissions.IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        
        stats = {
            'total_access': AccessLog.objects.count(),
            'today_access': AccessLog.objects.filter(access_time__date=today).count(),
            'granted_today': AccessLog.objects.filter(access_time__date=today, result='granted').count(),
            'denied_today': AccessLog.objects.filter(access_time__date=today, result='denied').count(),
            'by_zone': list(AccessLog.objects.values('zone__name').annotate(count=Count('id'))[:10])
        }
        
        return Response(stats)
    

@api_view(['GET'])
def institution_colleges(request, pk):
    colleges = College.objects.filter(institution_id=pk, is_active=True)
    data = [{'id': c.id, 'name': c.name} for c in colleges]
    return Response(data)

@api_view(['GET'])
def college_schools(request, pk):
    schools = School.objects.filter(college_id=pk, is_active=True)
    data = [{'id': s.id, 'name': s.name} for s in schools]
    return Response(data)

@api_view(['GET'])
def school_departments(request, pk):
    departments = Department.objects.filter(school_id=pk, is_active=True)
    data = [{'id': d.id, 'name': d.name} for d in departments]
    return Response(data)