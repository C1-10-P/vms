import threading
import time
import logging
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


class MQTTConsumerManager:
    """
    Manages background MQTT consumer threads
    """
    
    _instance = None
    _consumers = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def start_all(self):
        """Start all MQTT consumers"""
        logger.info("Starting MQTT consumers...")
        
        consumers = [
            ('Attendance Consumer', self._attendance_consumer),
            ('Visitor Consumer', self._visitor_consumer),
            ('Device Consumer', self._device_consumer),
            ('Security Consumer', self._security_consumer),
        ]
        
        for name, consumer_func in consumers:
            thread = threading.Thread(target=consumer_func, daemon=True, name=name)
            thread.start()
            self._consumers.append(thread)
            logger.info(f"Started {name}")
    
    def _attendance_consumer(self):
        """Consumer for attendance-related MQTT messages"""
        from .mqtt_client import mqtt_client
        from apps.classroom.services import AttendanceService
        
        service = AttendanceService()
        
        while True:
            # This runs in background, actual processing is in mqtt_client
            time.sleep(1)
    
    def _visitor_consumer(self):
        """Consumer for visitor-related MQTT messages"""
        from .mqtt_client import mqtt_client
        
        while True:
            time.sleep(1)
    
    def _device_consumer(self):
        """Consumer for device-related MQTT messages"""
        from .mqtt_client import mqtt_client
        
        while True:
            time.sleep(1)
    
    def _security_consumer(self):
        """Consumer for security-related MQTT messages"""
        from .mqtt_client import mqtt_client
        
        while True:
            time.sleep(1)


# Singleton instance
consumer_manager = MQTTConsumerManager()