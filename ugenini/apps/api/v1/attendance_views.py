from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from apps.classroom.services import AttendanceSessionService, AttendanceSession



class AttendanceSessionCreateView(APIView):
    """
    Create an attendance session (for kiosk/scanning)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        student_reg = request.data.get('student_reg')
        class_code = request.data.get('class_code')
        scan_method = request.data.get('scan_method', 'manual')  # default to manual if not provided
        scan_device = request.data.get('scan_device')
        
        if not student_reg:
            return Response({'error': 'student_reg required'}, status=400)
        
        result = AttendanceSessionService.create_session(
            student_reg=student_reg,
            class_code=class_code,
            scan_method=scan_method,
            scan_device=scan_device
        )
        
        return Response(result, status=200 if result['success'] else 400)


class AttendanceSessionValidateView(APIView):
    """
    Validate an attendance session and create attendance record
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, session_id):
        try:
            # 1. The service now returns the Session object instance
            session_obj = AttendanceSessionService.validate_session(session_id)
            
            # 2. Construct a dictionary for the Response
            return Response({
                'success': True,
                'message': 'Session validated successfully',
                'session_id': session_obj.session_id,
                'status': session_obj.status
            }, status=200)
            
        except AttendanceSession.DoesNotExist:
            return Response({
                'success': False, 
                'error': 'Session not found'
            }, status=404)
        except Exception as e:
            return Response({
                'success': False, 
                'error': str(e)
            }, status=400)