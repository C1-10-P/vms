import random
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from faker import Faker
from django.db.models import F

from ugenini.apps.firmware.models.edge_node import EdgeNode

fake = Faker()

from apps.core.models import Institution, Staff, Person 
from apps.vms.models import Visitor, BLETag, VisitorVisit, VisitorMovement, VisitorAlert
from apps.access.models.zone import AccessZone

class VisitorDataSeeder:
    """Seed data for visitor management"""
    
    @staticmethod
    def seed_ble_tags(count=20):
        """Create BLE tags for visitors"""
        tags = []
        tag_types = ['wearable', 'card', 'sticker']
        statuses = ['available', 'assigned', 'available', 'available', 'charging']
        
        for i in range(count):
            tag_uuid = str(uuid.uuid4())
            hardware_id = f"AA:BB:CC:{random.randint(10, 99)}:{random.randint(10, 99)}:{random.randint(10, 99)}"
            
            tag, created = BLETag.objects.get_or_create(
                tag_uuid=tag_uuid,
                defaults={
                    'hardware_id': hardware_id,
                    'tag_type': random.choice(tag_types),
                    'manufacturer': 'Nordic Semiconductor',
                    'model': f'nRF52{random.randint(80, 89)}',
                    'firmware_version': f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
                    'status': random.choice(statuses),
                    'battery_level': random.randint(10, 100),
                    'total_assignments': 0,
                    'is_active': True
                }
            )
            tags.append(tag)
        
        print(f"✓ Created {len(tags)} BLE tags")
        return tags
    
    @staticmethod
    def seed_visitor_visits(visitors, staff_list, node_list, tags_list, count_per_visitor=2):
        visits_created_count = 0
        now = timezone.now()

        if not node_list:
            raise Exception("❌ No nodes available")

        if not staff_list:
            raise Exception("❌ No staff available")

        for visitor in visitors:
            if not visitor.pk:
                print(f"⚠️ Skipping: Visitor {visitor} has no PK")
                continue

            for _ in range(random.randint(1, count_per_visitor)):
                node = EdgeNode.objects.order_by("?").first()
                staff_member = Staff.objects.order_by("?").first()
                tag = BLETag.objects.order_by("?").first()

                try:
                    VisitorVisit.objects.get_or_create(
                        visitor_id=visitor.pk,
                        check_in_node_id=node.pk,
                        checked_in_by_id=staff_member.pk,
                        assigned_tag_id=tag.pk if tag else None,
                        check_in_time=now - timedelta(hours=random.randint(1, 24)),
                        status='active',
                        check_in_notes="System seeded visit"
                    )
                    visits_created_count += 1

                except Exception as e:
                    print(f"\n❌ FAILED AT VISIT CREATION:")
                    print(f"  - Visitor ID: {visitor.pk}")
                    print(f"  - Node ID: {node.pk}")
                    print(f"  - Staff ID: {staff_member.pk}")
                    print(f"  - Error: {e}")
                    raise e

        return visits_created_count
    @staticmethod
    def seed_visitor_movements(visits, movements_per_visit=10):
        """Create movement tracking records for visitors"""
        movements = []
        zones = list(AccessZone.objects.filter(is_active=True))
        
        if not zones:
            print("⚠ No zones available for movement tracking")
            return []
        
        for visit in visits[:50]:  # Limit to 50 visits for performance
            current_zone = None
            for i in range(random.randint(5, movements_per_visit)):
                zone = random.choice(zones)
                timestamp = visit.check_in_time + timedelta(minutes=i * random.randint(5, 30))
                
                if timestamp > timezone.now():
                    break
                
                event_type = 'enter' if current_zone != zone else 'ping'
                if current_zone and zone != current_zone:
                    event_type = 'exit'
                
                movement, created = VisitorMovement.objects.get_or_create(
                    visitor=visit.visitor,
                    visit=visit,
                    zone=zone,
                    timestamp=timestamp,
                    defaults={
                        'tag': visit.assigned_tag,
                        'event_type': event_type,
                        'rssi': random.randint(-90, -40),
                        'distance_estimate': round(random.uniform(0.5, 20.0), 2)
                    }
                )
                movements.append(movement)
                current_zone = zone
        
        print(f"✓ Created {len(movements)} visitor movements")
        return movements
    
    @staticmethod
    def seed_visitor_alerts(count=15):
        """Create alert records for random visitors"""
        from apps.vms.models import Visitor, VisitorAlert  # Ensure consistent imports

        # 1. Fetch visitors from the database if they aren't passed in
        visitors = list(Visitor.objects.all())
    
        if not visitors:
            print("⚠ Skipping Alerts: No visitors found in the database to link alerts to.")
            return []

        alerts = []
        alert_types = ['overstay', 'unauthorized_area', 'tag_tamper']
        
        for _ in range(count):
            # 2. Now random.choice won't fail because we verified 'visitors' isn't empty
            visitor = random.choice(visitors)
            
            alert = VisitorAlert.objects.get_or_create(
                visitor_id=visitor.pk,  # Using .pk to avoid the previous assignment error
                alert_type=random.choice(alert_types),
                message=fake.sentence(),
                is_resolved=random.choice([True, False]),
                created_at=timezone.now() - timedelta(days=random.randint(0, 7))
            )
            alerts.append(alert)

        print(f"✓ Created {len(alerts)} visitor alerts")
        return alerts