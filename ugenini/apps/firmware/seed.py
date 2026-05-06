import random
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from faker import Faker

fake = Faker()

from .models import EdgeNode, NodeHeartbeat, NodeHealth, FirmwareVersion, NodeConfiguration
from apps.core.models import Institution


class DeviceDataSeeder:
    """Seed data for edge devices"""
    
    @staticmethod
    def seed_edge_nodes(institution, count=15):
        """Create edge nodes (ESP32 devices)"""
        nodes = []
        node_types = ['camera', 'ble_scanner', 'gateway', 'rfid_reader', 'access_point']
        statuses = ['online', 'online', 'online', 'offline', 'maintenance']
        
        for i in range(count):
            node_type = random.choice(node_types)
            # Using a new UUID for the lookup
            node_uuid = str(uuid.uuid4())
        
            # Generate a unique serial and MAC for this iteration
            # This prevents the UNIQUE constraint failed: firmware_edgenode.serial_number
            serial_number = f"SN-{node_type[:2].upper()}-{random.randint(100000, 999999)}"
            mac_address = f"AA:BB:CC:DD:{random.randint(10, 99):02x}:{random.randint(10, 99):02x}".upper()
            
            node, created = EdgeNode.objects.get_or_create(
                node_uuid=node_uuid,
                defaults={
                    'serial_number': serial_number,  # 👈 REQUIRED: satisfy the unique constraint
                    'node_type': node_type,
                    'name': f"{node_type.upper()}_{i+1:02d}",
                    'mac_address': mac_address,
                    'ip_address': f"192.168.1.{random.randint(2, 254)}",
                    'institution': institution,
                    'firmware_version': f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
                    'status': random.choice(statuses),
                    'last_heartbeat': timezone.now() - timedelta(minutes=random.randint(1, 60)),
                    'has_camera': node_type == 'camera',
                    'has_ble': node_type in ['ble_scanner', 'gateway'],
                    'has_rfid': node_type == 'rfid_reader',
                    'battery_level': random.randint(20, 100) if random.choice([True, False]) else None,
                    'location_description': f"Building {random.randint(1, 10)}, Floor {random.randint(1, 5)}",
                    'is_active': True
                }
            )
            nodes.append(node)
            
            # Create default configuration
            NodeConfiguration.objects.get_or_create(
                node=node,
                defaults={
                    'version': '1.0.0',
                    'scan_interval_seconds': random.choice([5, 10, 30, 60]),
                    'log_level': random.choice(['info', 'debug', 'warn'])
                }
            )
            
            # Create health record
            NodeHealth.objects.get_or_create(
                node=node,
                defaults={
                    'health_status': random.choice(['healthy', 'healthy', 'healthy', 'degraded']),
                    'uptime_percentage_24h': random.randint(85, 100)
                }
            )
        
        print(f"✓ Created {len(nodes)} edge nodes")
        return nodes
    
    @staticmethod
    def seed_node_heartbeats(nodes, heartbeats_per_node=50):
        """Create heartbeat records for nodes"""
        heartbeats = []
        
        for node in nodes:
            for i in range(heartbeats_per_node):
                timestamp = timezone.now() - timedelta(minutes=i * 10)
                
                if timestamp < timezone.now() - timedelta(days=7):
                    continue
                
                heartbeat, created = NodeHeartbeat.objects.get_or_create(
                    node=node,
                    timestamp=timestamp,
                    defaults={
                        'uptime_seconds': random.randint(3600, 604800),
                        'free_heap': random.randint(50000, 200000),
                        'rssi': random.randint(-80, -30),
                        'battery_level': node.battery_level if node.battery_level else random.randint(20, 100),
                        'temperature': round(random.uniform(25.0, 45.0), 1)
                    }
                )
                heartbeats.append(heartbeat)
        
        print(f"✓ Created {len(heartbeats)} node heartbeats")
        return heartbeats
    
    @staticmethod
    def seed_firmware_versions(count=5):
        """Create firmware versions"""
        versions = []
        node_types = ['camera', 'ble_scanner', 'gateway', 'rfid_reader']
        
        for i in range(count):
            version_num = f"1.{i}.{random.randint(0, 9)}"
            
            version, created = FirmwareVersion.objects.get_or_create(
                version=version_num,
                node_type=random.choice(node_types),
                defaults={
                    'release_date': timezone.now() - timedelta(days=random.randint(0, 90)),
                    'file_size': random.randint(500000, 2000000),
                    'stability': random.choice(['stable', 'beta', 'alpha']),
                    'changelog': f"Version {version_num} released with bug fixes and improvements.",
                    'rollout_percentage': random.randint(0, 100),
                    'is_active': True
                }
            )
            versions.append(version)
        
        print(f"✓ Created {len(versions)} firmware versions")
        return versions