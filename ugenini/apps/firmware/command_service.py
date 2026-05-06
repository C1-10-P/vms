import logging
from django.utils import timezone
from .mqtt_client import mqtt_client

logger = logging.getLogger(__name__)


class DeviceCommandService:
    """
    Service for sending commands to edge devices via MQTT
    """
    
    @staticmethod
    def reboot_device(node_uuid: str):
        """Send reboot command to device"""
        logger.info(f"Rebooting device: {node_uuid}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'reboot',
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def update_config(node_uuid: str, config: dict):
        """Send configuration update to device"""
        logger.info(f"Updating config for {node_uuid}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'update_config',
            'config': config,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def start_ota_update(node_uuid: str, firmware_url: str, version: str):
        """Start OTA firmware update"""
        logger.info(f"Starting OTA for {node_uuid} to version {version}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'ota_update',
            'firmware_url': firmware_url,
            'version': version,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def set_scan_interval(node_uuid: str, interval_seconds: int):
        """Set device scan interval"""
        logger.info(f"Setting scan interval for {node_uuid} to {interval_seconds}s")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'set_scan_interval',
            'interval': interval_seconds,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def enable_debug_logging(node_uuid: str, enable: bool):
        """Enable/disable debug logging on device"""
        logger.info(f"Setting debug logging for {node_uuid} to {enable}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'debug_logging',
            'enable': enable,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def trigger_scan(node_uuid: str):
        """Trigger immediate scan"""
        logger.info(f"Triggering scan for {node_uuid}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'scan_now',
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def set_led_status(node_uuid: str, led_id: int, state: bool):
        """Control device LED"""
        logger.info(f"Setting LED {led_id} on {node_uuid} to {state}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'set_led',
            'led_id': led_id,
            'state': state,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def get_device_status(node_uuid: str):
        """Request device status"""
        logger.info(f"Requesting status from {node_uuid}")
        mqtt_client.publish(f"jkuat/system/commands/{node_uuid}", {
            'command': 'get_status',
            'timestamp': timezone.now().isoformat()
        })