from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache
import logging
import json

from .models import Notification, SMSLog, EmailLog, USSDSession

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Business logic for sending notifications
    """
    
    @staticmethod
    def send_notification(recipient, title, message, notification_type='system', priority='normal', action_url=None):
        """
        Create and send a notification to a user
        """
        try:
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                priority=priority,
                title=title,
                message=message,
                action_url=action_url or '',
                status='pending'
            )
            
            # Send real-time via WebSocket if user is online
            NotificationService._send_websocket_notification(recipient, notification)
            
            return {
                'success': True,
                'notification_id': notification.id
            }
            
        except Exception as e:
            logger.error(f"Notification creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_sms(phone_number, message, person=None):
        """
        Send SMS notification
        """
        try:
            # Create SMS log
            sms_log = SMSLog.objects.create(
                recipient_number=phone_number,
                recipient_person=person,
                message=message,
                status='queued'
            )
            
            # In production, integrate with SMS gateway (Africastalking, Twilio, etc.)
            # For now, just log it
            logger.info(f"SMS to {phone_number}: {message}")
            
            # Mark as sent
            sms_log.status = 'sent'
            sms_log.sent_at = timezone.now()
            sms_log.save()
            
            return {
                'success': True,
                'sms_id': sms_log.id
            }
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_email(recipient_email, subject, body_html, body_text=None, cc=None, bcc=None):
        """
        Send email notification
        """
        try:
            # Create email log
            email_log = EmailLog.objects.create(
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text or '',
                body_html=body_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                status='queued'
            )
            
            # Send email
            send_mail(
                subject=subject,
                message=body_text or body_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
                html_message=body_html
            )
            
            # Update status
            email_log.status = 'sent'
            email_log.sent_at = timezone.now()
            email_log.save()
            
            return {
                'success': True,
                'email_id': email_log.id
            }
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_attendance_notification(student, class_obj, status):
        """
        Send attendance notification to student
        """
        title = f"Attendance Recorded - {class_obj.class_code}"
        message = f"Your attendance for {class_obj.academic_unit.name} has been recorded as {status}."
        
        if student.person.email:
            NotificationService.send_email(
                recipient_email=student.person.email,
                subject=title,
                body_html=f"<p>{message}</p><p>Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>"
            )
        
        if student.person.phone_number:
            NotificationService.send_sms(
                phone_number=student.person.phone_number,
                message=message,
                person=student.person
            )
        
        return NotificationService.send_notification(
            recipient=student.person,
            title=title,
            message=message,
            notification_type='attendance'
        )
    
    @staticmethod
    def send_visitor_notification(visitor, event_type, details=None):
        """
        Send visitor-related notifications
        """
        if event_type == 'checkin':
            title = "Visitor Check-in Confirmed"
            message = f"Welcome to {visitor.institution.name}. Your visit has been registered."
        elif event_type == 'checkout':
            title = "Visitor Check-out Confirmed"
            message = "Thank you for your visit. You have been checked out successfully."
        elif event_type == 'blacklisted':
            title = "Blacklist Notification"
            message = "You have been blacklisted from accessing the facility."
        else:
            return
        
        return NotificationService.send_notification(
            recipient=visitor.person,
            title=title,
            message=message,
            notification_type='visitor'
        )
    
    @staticmethod
    def send_alert_notification(alert):
        """
        Send security alert notification
        """
        title = f"Security Alert: {alert.get_alert_type_display()}"
        message = f"{alert.message}\nSeverity: {alert.get_severity_display()}"
        
        # Send to security personnel
        from apps.core.models import Staff
        security_staff = Staff.objects.filter(staff_category='security', is_active=True)
        
        for staff in security_staff:
            if staff.person.email:
                NotificationService.send_email(
                    recipient_email=staff.person.email,
                    subject=f"[URGENT] {title}",
                    body_html=f"<p><strong>{message}</strong></p><p>Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
                )
            
            NotificationService.send_notification(
                recipient=staff.person,
                title=title,
                message=message,
                notification_type='security',
                priority='high'
            )
    
    @staticmethod
    def _send_websocket_notification(recipient, notification):
        """
        Send real-time notification via WebSocket
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{recipient.id}',
                {
                    'type': 'notification',
                    'data': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.notification_type,
                        'priority': notification.priority,
                        'timestamp': notification.created_at.isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"WebSocket notification failed: {e}")
    
    @staticmethod
    def get_unread_count(person):
        """
        Get unread notification count for a person
        """
        cache_key = f"unread_notifications_{person.id}"
        count = cache.get(cache_key)
        
        if count is None:
            count = Notification.objects.filter(
                recipient=person,
                status='pending'
            ).count()
            cache.set(cache_key, count, timeout=60)
        
        return count
    
    @staticmethod
    def mark_as_read(notification_id, person):
        """
        Mark notification as read
        """
        try:
            notification = Notification.objects.get(id=notification_id, recipient=person)
            notification.mark_as_read()
            
            # Clear cache
            cache_key = f"unread_notifications_{person.id}"
            cache.delete(cache_key)
            
            return {'success': True}
        except Notification.DoesNotExist:
            return {'success': False, 'error': 'Notification not found'}


class USSDService:
    """
    Business logic for USSD interactions
    """
    
    @staticmethod
    def process_ussd_request(session_id, phone_number, text):
        """
        Process USSD request and return response
        """
        # Get or create session
        session = USSDSession.objects.filter(
            session_id=session_id,
            status='active'
        ).first()
        
        if not session:
            session = USSDSession.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                session_type='two_factor',
                status='active'
            )
        
        # Parse input
        text_array = text.split('*')
        current_level = len(text_array)
        
        if text == '':
            # Main menu
            response = "CON Welcome to VMS\n"
            response += "1. Visitor Check-in\n"
            response += "2. Visitor Check-out\n"
            response += "3. Access Verification\n"
            response += "4. Report Incident\n"
            response += "0. Exit"
            return response
        
        if text_array[0] == '1':
            # Visitor Check-in
            return USSDService._handle_checkin(session, text_array)
        elif text_array[0] == '2':
            # Visitor Check-out
            return USSDService._handle_checkout(session, text_array)
        elif text_array[0] == '3':
            # Access Verification (2FA)
            return USSDService._handle_2fa(session, text_array)
        elif text_array[0] == '4':
            # Report Incident
            return USSDService._handle_incident(session, text_array)
        elif text_array[0] == '0':
            session.status = 'completed'
            session.save()
            return "END Thank you for using VMS. Goodbye!"
        
        return "END Invalid option. Please try again."
    
    @staticmethod
    def _handle_checkin(session, text_array):
        """Handle visitor check-in USSD flow"""
        level = len(text_array)
        
        if level == 1:
            return "CON Enter your National ID number:"
        elif level == 2:
            session.user_input['national_id'] = text_array[1]
            return "CON Enter your full name:"
        elif level == 3:
            session.user_input['name'] = text_array[2]
            return "CON Enter your phone number:"
        elif level == 4:
            session.user_input['phone'] = text_array[3]
            return "CON Enter purpose of visit:\n1. Meeting\n2. Delivery\n3. Maintenance\n4. Other"
        elif level == 5:
            purpose_map = {'1': 'meeting', '2': 'delivery', '3': 'maintenance', '4': 'other'}
            session.user_input['purpose'] = purpose_map.get(text_array[4], 'other')
            return "CON Enter host name or department:"
        elif level == 6:
            session.user_input['host'] = text_array[5]
            
            # Process check-in
            from apps.vms.services import VisitorService
            result = VisitorService.process_visitor_checkin({
                'first_name': session.user_input['name'].split()[0] if ' ' in session.user_input['name'] else session.user_input['name'],
                'last_name': session.user_input['name'].split()[-1] if ' ' in session.user_input['name'] else '',
                'national_id': session.user_input['national_id'],
                'phone_number': session.user_input['phone'],
                'purpose': session.user_input['purpose']
            })
            
            if result['success']:
                session.status = 'completed'
                session.save()
                return f"END Visitor check-in successful!\nID: {result['visitor_id']}\nTag: {result.get('tag_id', 'None')}"
            else:
                return f"END Check-in failed: {result.get('error', 'Unknown error')}"
        
        return "END Invalid request"
    
    @staticmethod
    def _handle_checkout(session, text_array):
        """Handle visitor check-out USSD flow"""
        if len(text_array) == 1:
            return "CON Enter your visitor ID or tag number:"
        elif len(text_array) == 2:
            from apps.vms.models import BLETag
            
            tag = BLETag.objects.filter(tag_uuid=text_array[1]).first()
            if tag:
                from apps.vms.services import VisitorService
                result = VisitorService.process_visitor_checkout(tag)
                
                if result['success']:
                    session.status = 'completed'
                    session.save()
                    return f"END Check-out successful! Visitor ID: {result['visitor_id']}"
                else:
                    return f"END Check-out failed: {result.get('error', 'Unknown error')}"
            else:
                return "END Tag not found. Please contact security."
        
        return "END Invalid request"
    
    @staticmethod
    def _handle_2fa(session, text_array):
        """Handle 2FA verification USSD flow"""
        if len(text_array) == 1:
            return "CON Enter your verification code:"
        elif len(text_array) == 2:
            # Find active 2FA session
            from apps.access.models import TwoFactorSession
            tfa_session = TwoFactorSession.objects.filter(
                phone_number=session.phone_number,
                status='pending',
                expires_at__gt=timezone.now()
            ).first()
            
            if tfa_session:
                success, message = tfa_session.verify(text_array[1])
                if success:
                    session.status = 'completed'
                    session.save()
                    return f"END {message}\nAccess granted. Proceed to gate."
                else:
                    return f"END {message}"
            else:
                return "END No active verification request found."
        
        return "END Invalid request"
    
    @staticmethod
    def _handle_incident(session, text_array):
        """Handle incident reporting USSD flow"""
        level = len(text_array)
        
        if level == 1:
            return "CON Report an incident:\n1. Security Threat\n2. Accident\n3. Lost Item\n4. Other"
        elif level == 2:
            incident_map = {'1': 'security', '2': 'accident', '3': 'lost_item', '4': 'other'}
            session.user_input['incident_type'] = incident_map.get(text_array[1], 'other')
            return "CON Describe the incident briefly:"
        elif level == 3:
            session.user_input['description'] = text_array[2]
            session.user_input['location'] = 'Reported via USSD'
            
            # Create alert
            from apps.vms.models import VisitorAlert
            VisitorAlert.objects.create(
                alert_type='movement_anomaly',
                severity='high',
                message=f"Incident reported: {session.user_input['incident_type']} - {session.user_input['description']}",
                data={
                    'phone': session.phone_number,
                    'type': session.user_input['incident_type'],
                    'description': session.user_input['description']
                }
            )
            
            session.status = 'completed'
            session.save()
            return "END Incident reported. Security has been notified."
        
        return "END Invalid request"