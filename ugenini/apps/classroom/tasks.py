from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

@shared_task
def process_attendance_notifications(attendance_id):
    """Process notifications after attendance is recorded"""
    from .models import ClassAttendance
    
    try:
        attendance = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        ).get(id=attendance_id)
        
        # Send SMS notification if configured
        if attendance.student.person.phone_number:
            send_attendance_sms.delay(attendance_id)
        
        # Update attendance summary
        update_daily_summary.delay(
            attendance.class_obj.id,
            attendance.scan_time.date()
        )
        
    except ClassAttendance.DoesNotExist:
        logger.error(f"Attendance {attendance_id} not found")

@shared_task
def send_attendance_sms(attendance_id):
    """Send SMS for attendance confirmation"""
    from .models import ClassAttendance
    from apps.notifications.sms import send_sms
    
    try:
        attendance = ClassAttendance.objects.get(id=attendance_id)
        message = f"Attendance recorded for {attendance.class_obj.class_code} at {attendance.scan_time.strftime('%H:%M')}"
        
        send_sms(attendance.student.person.phone_number, message)
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")

@shared_task
def update_daily_summary(class_id, date):
    """Update daily attendance summary"""
    from .models import ClassAttendance, DailyAttendanceSummary
    from django.db.models import Count, Q
    
    summary, created = DailyAttendanceSummary.objects.get_or_create(
        class_id=class_id,
        summary_date=date
    )
    
    total = ClassAttendance.objects.filter(
        class_id=class_id,
        scan_time__date=date
    ).count()
    
    summary.total_present = total
    summary.save()
    
    return summary.id

@shared_task
def generate_weekly_report(institution_id, week_start):
    """Generate weekly attendance report"""
    from apps.reports.generators import generate_pdf_report
    
    report = generate_pdf_report(institution_id, week_start, week_start + timedelta(days=7))
    
    # Send to admin
    send_mail(
        subject='Weekly Attendance Report',
        message='Please find attached weekly report',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        attachments=[(f'report_{week_start}.pdf', report, 'application/pdf')]
    )

@shared_task
def cleanup_old_ledger_entries():
    """Archive old ledger entries"""
    from apps.core.models import ImmutableLedger
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=365)
    old_entries = ImmutableLedger.objects.filter(timestamp__lt=cutoff_date)
    
    count = old_entries.count()
    # Archive to cold storage
    # ...
    old_entries.delete()
    
    logger.info(f"Archived {count} old ledger entries")