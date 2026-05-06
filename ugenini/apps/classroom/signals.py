from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import ClassAttendance
# from apps.realtime.mqtt_bridge import publish_to_mqtt

@receiver(post_save, sender=ClassAttendance)
def attendance_created(sender, instance, created, **kwargs):
    """Send real-time update when attendance is recorded"""
    if created:
        # Update cache
        cache_key = f"attendance_today_{instance.student.id}"
        cache.delete(cache_key)
        
        # Send WebSocket update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"attendance_{instance.class_id}",
            {
                'type': 'attendance_update',
                'data': {
                    'student_id': instance.student.student_reg_number,
                    'student_name': instance.student.person.full_name,
                    'class_code': instance.class_obj.class_code,
                    'timestamp': instance.scan_time.isoformat(),
                    'status': instance.verification_status
                }
            }
        )
        
        # Publish to MQTT for edge nodes
        # publish_to_mqtt('jkuat/attendance/confirmed', {
        #     'student_id': instance.student.student_reg_number,
        #     'class_code': instance.class_obj.class_code,
        #     'timestamp': instance.scan_time.isoformat()
        # })
        
        # Trigger Celery task for processing
        from .tasks import process_attendance_notifications
        process_attendance_notifications.delay(instance.id)