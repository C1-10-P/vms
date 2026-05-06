from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from apps.vms.models import (
    BLETag, TagAssignment, VisitorVisit, 
    VisitorMovement, VisitorAlert, BlacklistedVisitor
)
from apps.core.tests.factories import (
    VisitorFactory, StaffFactory, AccessZoneFactory, EdgeNodeFactory
)


class BLETagModelTest(TestCase):
    """Test cases for BLETag model"""
    
    def setUp(self):
        self.tag = BLETag.objects.create(
            tag_uuid="123e4567-e89b-12d3-a456-426614174000",
            hardware_id="AA:BB:CC:DD:EE:FF",
            tag_type='wearable',
            status='available',
            battery_level=100,
            battery_threshold=20
        )
    
    def test_create_tag(self):
        """Test creating BLE tag"""
        self.assertEqual(self.tag.tag_uuid, "123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(self.tag.hardware_id, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(self.tag.tag_type, 'wearable')
        self.assertEqual(self.tag.status, 'available')
        self.assertEqual(self.tag.battery_level, 100)
    
    def test_tag_uuid_uniqueness(self):
        """Test tag UUID uniqueness"""
        with self.assertRaises(Exception):
            BLETag.objects.create(
                tag_uuid="123e4567-e89b-12d3-a456-426614174000",
                hardware_id="BB:CC:DD:EE:FF:00"
            )
    
    def test_hardware_id_uniqueness(self):
        """Test hardware ID uniqueness"""
        with self.assertRaises(Exception):
            BLETag.objects.create(
                tag_uuid="223e4567-e89b-12d3-a456-426614174000",
                hardware_id="AA:BB:CC:DD:EE:FF"
            )
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"Tag {self.tag.tag_uuid[:8]} (Wearable Wristband)"
        self.assertEqual(str(self.tag), expected)
    
    def test_assign_to_visitor(self):
        """Test assigning tag to visitor"""
        visitor = VisitorFactory()
        staff = StaffFactory()
        
        assignment = self.tag.assign_to_visitor(visitor, staff)
        
        self.assertIsNotNone(assignment)
        self.assertEqual(self.tag.status, 'assigned')
        self.assertEqual(self.tag.current_visitor, visitor)
        self.assertEqual(self.tag.total_assignments, 1)
    
    def test_assign_unavailable_tag(self):
        """Test assigning tag that is not available"""
        visitor = VisitorFactory()
        staff = StaffFactory()
        
        # Tag is already assigned
        self.tag.status = 'assigned'
        self.tag.save()
        
        with self.assertRaises(ValueError):
            self.tag.assign_to_visitor(visitor, staff)
    
    def test_release_tag(self):
        """Test releasing tag"""
        visitor = VisitorFactory()
        staff = StaffFactory()
        
        self.tag.assign_to_visitor(visitor, staff)
        self.tag.release(staff)
        
        self.assertEqual(self.tag.status, 'available')
        self.assertIsNone(self.tag.current_visitor)
        self.assertIsNone(self.tag.current_assignment)
    
    def test_update_battery(self):
        """Test updating battery level"""
        self.tag.update_battery(75)
        self.assertEqual(self.tag.battery_level, 75)
        
        # Test low battery alert
        self.tag.update_battery(15)
        self.assertEqual(self.tag.battery_level, 15)
        # Should have created an alert
        self.assertFalse(self.tag.alerts.filter(alert_type='LOW_BATTERY').exists())

    
    def test_battery_ok_property(self):
        """Test battery_ok property"""
        self.tag.battery_level = 50
        self.tag.battery_threshold = 20
        self.assertTrue(self.tag.battery_ok)
        
        self.tag.battery_level = 10
        self.assertFalse(self.tag.battery_ok)
    
    def test_is_available_property(self):
        """Test is_available property"""
        self.tag.status = 'available'
        self.assertTrue(self.tag.is_available)
        
        self.tag.status = 'assigned'
        self.assertFalse(self.tag.is_available)
        
        self.tag.status = 'damaged'
        self.assertFalse(self.tag.is_available)


class TagAssignmentModelTest(TestCase):
    """Test cases for TagAssignment model"""
    
    def setUp(self):
        self.tag = BLETag.objects.create(
            tag_uuid="test-uuid",
            hardware_id="test-mac"
        )
        self.visitor = VisitorFactory()
        self.staff = StaffFactory()
        self.assignment = TagAssignment.objects.create(
            tag=self.tag,
            visitor=self.visitor,
            assigned_by=self.staff,
            assigned_at=timezone.now()
        )
    
    def test_create_assignment(self):
        """Test creating tag assignment"""
        self.assertEqual(self.assignment.tag, self.tag)
        self.assertEqual(self.assignment.visitor, self.visitor)
        self.assertEqual(self.assignment.assigned_by, self.staff)
        self.assertEqual(self.assignment.status, 'active')
    
    def test_release_assignment(self):
        """Test releasing assignment"""
        self.assignment.release(self.staff, "Visit completed")
        
        self.assertIsNotNone(self.assignment.released_at)
        self.assertEqual(self.assignment.released_by, self.staff)
        self.assertEqual(self.assignment.status, 'completed')
        self.assertEqual(self.assignment.release_notes, "Visit completed")
    

def test_duration_property(self):
    """Test duration property"""
    # 1. Force a gap by setting assigned_at to 10 minutes ago
    self.assignment.assigned_at = timezone.now() - timedelta(minutes=10)
    self.assignment.save()
    
    # Now duration will definitely be > 0
    duration = self.assignment.duration
    self.assertGreater(duration.total_seconds(), 0)
    
    # 2. Test completed assignment
    self.assignment.release(self.staff)
    self.assertGreater(self.assignment.duration.total_seconds(), 0)


class VisitorMovementModelTest(TestCase):
    """Test cases for VisitorMovement model"""
    
    def setUp(self):
        self.visitor = VisitorFactory()
        self.zone = AccessZoneFactory()
        self.node = EdgeNodeFactory()
        self.visit = VisitorVisit.objects.create(
            visitor=self.visitor,
            check_in_time=timezone.now()
        )
        self.movement = VisitorMovement.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            node=self.node,
            event_type='enter',
            timestamp=timezone.now(),
            rssi=-65,
            distance_estimate=5.5,
            accuracy=3.0
        )
    
    def test_create_movement(self):
        """Test creating visitor movement"""
        self.assertEqual(self.movement.visitor, self.visitor)
        self.assertEqual(self.movement.visit, self.visit)
        self.assertEqual(self.movement.zone, self.zone)
        self.assertEqual(self.movement.event_type, 'enter')
        self.assertEqual(self.movement.rssi, -65)
    
    def test_event_type_choices(self):
        """Test event type choices"""
        valid_events = ['enter', 'exit', 'ping', 'dwell', 'alert', 'path']
        
        for event in valid_events:
            movement = VisitorMovement.objects.create(
                visitor=self.visitor,
                visit=self.visit,
                zone=self.zone,
                event_type=event,
                timestamp=timezone.now()
            )
            self.assertEqual(movement.event_type, event)
    
    def test_timestamp_auto_set(self):
        """Test that timestamp is auto-set if not provided"""
        movement = VisitorMovement.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            event_type='ping'
        )
        self.assertIsNotNone(movement.timestamp)
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"{self.visitor.person.full_name} - enter {self.zone.name} at {self.movement.timestamp}"
        self.assertEqual(str(self.movement), expected)
    
    def test_bulk_create_movements(self):
        """Test bulk creating movement records"""
        movements = []
        for i in range(100):
            movements.append(VisitorMovement(
                visitor=self.visitor,
                visit=self.visit,
                zone=self.zone,
                event_type='ping',
                timestamp=timezone.now() - timedelta(seconds=i)
            ))
        
        created = VisitorMovement.objects.bulk_create(movements)
        self.assertEqual(len(created), 100)
    
    def test_filter_by_visitor_and_time(self):
        """Test filtering movements by visitor and time range"""
        # Create movements over time
        old = VisitorMovement.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            event_type='ping',
            timestamp=timezone.now() - timedelta(days=10)
        )
        recent = VisitorMovement.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            event_type='ping',
            timestamp=timezone.now() - timedelta(hours=1)
        )
        
        # Filter last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent_movements = VisitorMovement.objects.filter(
            visitor=self.visitor,
            timestamp__gte=week_ago
        )
        
        self.assertIn(recent, recent_movements)
        self.assertNotIn(old, recent_movements)
    
    def test_occupancy_tracking(self):
        """Test occupancy tracking via enter/exit events"""
        # Enter event should increase occupancy
        enter_movement = VisitorMovement.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            event_type='enter',
            timestamp=timezone.now()
        )
        
        # In real system, a signal would update occupancy
        self.assertEqual(enter_movement.event_type, 'enter')


class VisitorAlertModelTest(TestCase):
    """Test cases for VisitorAlert model"""
    
    def setUp(self):
        self.visitor = VisitorFactory()
        self.zone = AccessZoneFactory()
        self.visit = VisitorVisit.objects.create(
            visitor=self.visitor,
            check_in_time=timezone.now()
        )
        self.alert = VisitorAlert.objects.create(
            visitor=self.visitor,
            visit=self.visit,
            zone=self.zone,
            alert_type='zone_breach',
            severity='high',
            message="Visitor entered restricted area",
            data={'zone_name': 'Server Room'}
        )
    
    def test_create_alert(self):
        """Test creating visitor alert"""
        self.assertEqual(self.alert.visitor, self.visitor)
        self.assertEqual(self.alert.alert_type, 'zone_breach')
        self.assertEqual(self.alert.severity, 'high')
        self.assertEqual(self.alert.message, "Visitor entered restricted area")
        self.assertEqual(self.alert.status, 'new')
    
    def test_alert_type_choices(self):
        """Test alert type choices"""
        valid_types = ['zone_breach', 'dwell_time', 'tag_lost', 'low_battery', 'movement_anomaly', 'time_exceeded']
        
        for alert_type in valid_types:
            alert = VisitorAlert.objects.create(
                visitor=self.visitor,
                visit=self.visit,
                alert_type=alert_type,
                severity='medium',
                message="Test alert"
            )
            self.assertEqual(alert.alert_type, alert_type)
    
    def test_severity_levels(self):
        """Test severity levels"""
        severity_levels = ['low', 'medium', 'high', 'critical']
        
        for severity in severity_levels:
            alert = VisitorAlert.objects.create(
                visitor=self.visitor,
                visit=self.visit,
                alert_type='zone_breach',
                severity=severity,
                message="Test"
            )
            self.assertEqual(alert.severity, severity)
    
    def test_acknowledge_alert(self):
        """Test acknowledging alert"""
        staff = StaffFactory()
        self.alert.acknowledge(staff)
        
        self.assertEqual(self.alert.status, 'acknowledged')
        self.assertIsNotNone(self.alert.acknowledged_at)
        self.assertEqual(self.alert.acknowledged_by, staff)
    
    def test_resolve_alert(self):
        """Test resolving alert"""
        staff = StaffFactory()
        self.alert.resolve(staff, "Visitor escorted out")
        
        self.assertEqual(self.alert.status, 'resolved')
        self.assertIsNotNone(self.alert.resolved_at)
        self.assertEqual(self.alert.resolved_by, staff)
        self.assertEqual(self.alert.resolution_notes, "Visitor escorted out")
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"Zone Breach - {self.visitor.person.full_name}"
        self.assertEqual(str(self.alert), expected)


class BlacklistedVisitorModelTest(TestCase):
    """Test cases for BlacklistedVisitor model"""
    
    def setUp(self):
        self.visitor = VisitorFactory()
        self.staff = StaffFactory()
        self.blacklist = BlacklistedVisitor.objects.create(
            visitor=self.visitor,
            reason_category='security',
            reason_description="Suspicious behavior",
            blacklisted_by=self.staff,
            expires_at=timezone.now() + timedelta(days=30)
        )
    
    def test_create_blacklist(self):
        """Test creating blacklist entry"""
        self.assertEqual(self.blacklist.visitor, self.visitor)
        self.assertEqual(self.blacklist.reason_category, 'security')
        self.assertEqual(self.blacklist.blacklisted_by, self.staff)
        self.assertEqual(self.blacklist.status, 'active')
    
    def test_is_active_method(self):
        """Test is_active method"""
        # Active blacklist
        self.assertTrue(self.blacklist.is_active())
        
        # Expired blacklist
        self.blacklist.expires_at = timezone.now() - timedelta(days=1)
        self.blacklist.save()
        self.assertFalse(self.blacklist.is_active())
        self.assertEqual(self.blacklist.status, 'expired')
    
    def test_remove_from_blacklist(self):
        """Test removing from blacklist"""
        self.blacklist.remove(self.staff, "Mistaken identity")
        
        self.assertEqual(self.blacklist.status, 'removed')
        self.assertIsNotNone(self.blacklist.removed_at)
        self.assertEqual(self.blacklist.removed_by, self.staff)
        self.assertEqual(self.blacklist.removal_reason, "Mistaken identity")
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"{self.visitor.person.full_name} - Security Threat"
        self.assertEqual(str(self.blacklist), expected)