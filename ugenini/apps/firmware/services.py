from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q, Avg
from datetime import datetime, timedelta
import logging
import json
import uuid

from .models import EdgeNode, NodeHeartbeat, NodeHealth, FirmwareVersion, OTASession, NodeConfiguration

logger = logging.getLogger(__name__)


class DeviceService:
    """
    Business logic for device management operations
    """
    
    @staticmethod
    def register_device(data):
        """
        Register a new edge device
        """
        try:
            with transaction.atomic():
                # Check if device already exists
                node = EdgeNode.objects.filter(
                    mac_address=data.get('mac_address')
                ).first()
                
                if node:
                    # Update existing device
                    node.last_heartbeat = timezone.now()
                    node.status = 'online'
                    node.firmware_version = data.get('firmware_version', node.firmware_version)
                    node.save()
                    
                    return {
                        'success': True,
                        'node_id': node.id,
                        'node_uuid': node.node_uuid,
                        'is_new': False
                    }
                
                # Create new device
                node = EdgeNode.objects.create(
                    node_uuid=data.get('node_uuid', str(uuid.uuid4())),
                    node_type=data.get('node_type'),
                    name=data.get('name', f"Node_{data.get('node_uuid', '')[:8]}"),
                    mac_address=data.get('mac_address'),
                    firmware_version=data.get('firmware_version', '1.0.0'),
                    ip_address=data.get('ip_address'),
                    has_camera=data.get('has_camera', False),
                    has_ble=data.get('has_ble', False),
                    status='online',
                    last_heartbeat=timezone.now()
                )
                
                # Create default configuration
                NodeConfiguration.objects.create(
                    node=node,
                    version='1.0.0'
                )
                
                # Create health record
                NodeHealth.objects.create(
                    node=node,
                    health_status='healthy'
                )
                
                return {
                    'success': True,
                    'node_id': node.id,
                    'node_uuid': node.node_uuid,
                    'is_new': True
                }
                
        except Exception as e:
            logger.error(f"Device registration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def process_heartbeat(node_uuid, data):
        """
        Process device heartbeat
        """
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            
            # Update node status
            node.last_heartbeat = timezone.now()
            node.status = 'online'
            node.wifi_rssi = data.get('rssi', node.wifi_rssi)
            node.battery_level = data.get('battery', node.battery_level)
            node.temperature = data.get('temperature', node.temperature)
            node.uptime_seconds = data.get('uptime', node.uptime_seconds)
            node.save()
            
            # Create heartbeat record
            heartbeat = NodeHeartbeat.objects.create(
                node=node,
                timestamp=timezone.now(),
                uptime_seconds=data.get('uptime', 0),
                free_heap=data.get('free_heap', 0),
                rssi=data.get('rssi'),
                battery_level=data.get('battery'),
                temperature=data.get('temperature'),
                data=data
            )
            
            # Update health status
            DeviceService._update_node_health(node)
            
            return {
                'success': True,
                'node_id': node.id,
                'heartbeat_id': heartbeat.id
            }
            
        except EdgeNode.DoesNotExist:
            return {'success': False, 'error': 'Node not found'}
        except Exception as e:
            logger.error(f"Heartbeat processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _update_node_health(node):
        """
        Update node health status based on recent heartbeats
        """
        # Get heartbeats from last 24 hours
        cutoff = timezone.now() - timedelta(hours=24)
        heartbeats = NodeHeartbeat.objects.filter(
            node=node,
            timestamp__gte=cutoff
        )
        
        if not heartbeats.exists():
            health_status = 'critical'
        else:
            # Calculate uptime percentage
            expected_heartbeats = 144  # Every 10 minutes for 24 hours
            actual_heartbeats = heartbeats.count()
            uptime_percentage = (actual_heartbeats / expected_heartbeats) * 100
            
            if uptime_percentage < 50:
                health_status = 'critical'
            elif uptime_percentage < 90:
                health_status = 'degraded'
            else:
                health_status = 'healthy'
            
            # Check battery
            avg_battery = heartbeats.aggregate(Avg('battery_level'))['battery_level__avg']
            if avg_battery and avg_battery < 20:
                health_status = 'critical'
            elif avg_battery and avg_battery < 50:
                health_status = 'degraded'
        
        # Update or create health record
        health, created = NodeHealth.objects.update_or_create(
            node=node,
            defaults={
                'health_status': health_status,
                'uptime_percentage_24h': uptime_percentage if 'uptime_percentage' in locals() else 0,
                'error_count_24h': 0,  # Would need error tracking
                'last_updated': timezone.now()
            }
        )
        
        return health
    
    @staticmethod
    def get_device_stats():
        """
        Get device statistics
        """
        nodes = EdgeNode.objects.filter(is_active=True)
        
        stats = {
            'total': nodes.count(),
            'online': nodes.filter(status='online').count(),
            'offline': nodes.filter(status='offline').count(),
            'maintenance': nodes.filter(status='maintenance').count(),
            'by_type': list(nodes.values('node_type').annotate(count=Count('id'))),
            'low_battery': nodes.filter(battery_level__lt=20).count(),
            'critical_health': NodeHealth.objects.filter(health_status='critical').count()
        }
        
        # Average metrics
        avg_metrics = NodeHeartbeat.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).aggregate(
            avg_battery=Avg('battery_level'),
            avg_rssi=Avg('rssi'),
            avg_uptime=Avg('uptime_seconds')
        )
        
        stats['average_battery'] = round(avg_metrics['avg_battery'], 1) if avg_metrics['avg_battery'] else 0
        stats['average_rssi'] = round(avg_metrics['avg_rssi'], 1) if avg_metrics['avg_rssi'] else 0
        stats['average_uptime_days'] = round(avg_metrics['avg_uptime'] / 86400, 1) if avg_metrics['avg_uptime'] else 0
        
        return stats
    
    @staticmethod
    def send_command(node_uuid, command, params=None):
        """
        Send command to a device via MQTT
        """
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            
            # In production, send via MQTT
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f'jkuat/system/commands/{node_uuid}', {
                'command': command,
                'params': params or {},
                'timestamp': timezone.now().isoformat()
            })
            
            return {
                'success': True,
                'command': command,
                'node_id': node.id
            }
            
        except EdgeNode.DoesNotExist:
            return {'success': False, 'error': 'Node not found'}
    
    @staticmethod
    def update_node_configuration(node_uuid, config_data):
        """
        Update node configuration
        """
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            
            config, created = NodeConfiguration.objects.update_or_create(
                node=node,
                defaults={
                    'version': config_data.get('version', '1.0.0'),
                    'scan_interval_seconds': config_data.get('scan_interval', 30),
                    'ble_scan_duration': config_data.get('ble_scan_duration', 5),
                    'log_level': config_data.get('log_level', 'info'),
                    'custom_settings': config_data.get('custom_settings', {})
                }
            )
            
            # Send config to device
            DeviceService.send_command(node_uuid, 'update_config', config.to_dict())
            
            return {
                'success': True,
                'config_version': config.version
            }
            
        except EdgeNode.DoesNotExist:
            return {'success': False, 'error': 'Node not found'}


class OTAService:
    """
    Business logic for Over-The-Air firmware updates
    """
    
    @staticmethod
    def deploy_firmware(firmware, nodes, initiated_by):
        """
        Deploy firmware to multiple nodes
        """
        results = {
            'deployed': 0,
            'failed': 0,
            'details': []
        }
        
        with transaction.atomic():
            for node in nodes:
                try:
                    # Create OTA session
                    session = OTASession.objects.create(
                        node=node,
                        firmware=firmware,
                        session_id=str(uuid.uuid4()),
                        status='pending',
                        initiated_by=initiated_by,
                        initiated_via='web'
                    )
                    
                    # Send OTA command to device
                    from apps.firmware.mqtt_client import mqtt_client
                    mqtt_client.publish(f'jkuat/system/commands/{node.node_uuid}', {
                        'command': 'ota_update',
                        'params': {
                            'firmware_url': firmware.firmware_file.url,
                            'version': firmware.version,
                            'session_id': session.session_id
                        },
                        'timestamp': timezone.now().isoformat()
                    })
                    
                    results['deployed'] += 1
                    results['details'].append({
                        'node_id': node.id,
                        'node_name': node.name,
                        'session_id': session.session_id,
                        'status': 'initiated'
                    })
                    
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'node_id': node.id,
                        'node_name': node.name,
                        'error': str(e)
                    })
        
        return results
    
    @staticmethod
    def update_ota_status(session_id, status, progress=None, error=None):
        """
        Update OTA session status
        """
        try:
            session = OTASession.objects.get(session_id=session_id)
            
            if progress is not None:
                session.update_progress(progress)
            
            if status == 'success':
                session.complete(success=True)
                # Update node firmware version
                session.node.firmware_version = session.firmware.version
                session.node.save()
            elif status == 'failed':
                session.complete(success=False, error=error)
            elif status == 'downloading' or status == 'updating':
                session.status = status
                session.save()
            
            return {'success': True}
            
        except OTASession.DoesNotExist:
            return {'success': False, 'error': 'Session not found'}
    
    @staticmethod
    def rollback_firmware(node, to_firmware, initiated_by):
        """
        Rollback firmware to previous version
        """
        try:
            # Create rollback session
            session = OTASession.objects.create(
                node=node,
                firmware=to_firmware,
                session_id=str(uuid.uuid4()),
                status='pending',
                initiated_by=initiated_by,
                initiated_via='web'
            )
            
            # Send rollback command
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f'jkuat/system/commands/{node.node_uuid}', {
                'command': 'rollback_firmware',
                'params': {
                    'firmware_url': to_firmware.firmware_file.url,
                    'version': to_firmware.version,
                    'session_id': session.session_id
                },
                'timestamp': timezone.now().isoformat()
            })
            
            return {
                'success': True,
                'session_id': session.session_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_ota_statistics():
        """
        Get OTA update statistics
        """
        sessions = OTASession.objects.all()
        
        stats = {
            'total': sessions.count(),
            'successful': sessions.filter(status='success').count(),
            'failed': sessions.filter(status='failed').count(),
            'pending': sessions.filter(status='pending').count(),
            'in_progress': sessions.filter(status__in=['downloading', 'updating']).count(),
            'success_rate': (sessions.filter(status='success').count() / sessions.count() * 100) if sessions.count() > 0 else 0
        }
        
        # Success by firmware
        by_firmware = sessions.values('firmware__version').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(status='success'))
        )
        
        stats['by_firmware'] = list(by_firmware)
        
        return stats