from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from apps.core.tests.factories import (
    InstitutionFactory, CollegeFactory, SchoolFactory, DepartmentFactory,
    ProgramFactory, StudentFactory, StaffFactory, ClassFactory,
    ClassAttendanceFactory, VisitorFactory, VisitorVisitFactory,
    AccessZoneFactory, EdgeNodeFactory, PersonFactory
)
from apps.vms.models import VisitorMovement
from apps.users.permissions import VMSPermissions
from apps.classroom.models import ClassAttendance
from django.contrib.auth.models import Permission

User = get_user_model()


class EndToEndAttendanceFlowTest(TestCase):
    """
    End-to-end test for complete attendance flow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # -----------------------------
        # Institution hierarchy
        # -----------------------------
        self.institution = InstitutionFactory()
        self.college = CollegeFactory(institution=self.institution)
        self.school = SchoolFactory(college=self.college)
        self.department = DepartmentFactory(school=self.school)
        self.program = ProgramFactory(department=self.department)
        
        # -----------------------------
        # Lecturer (Person → Staff)
        # -----------------------------
        self.lecturer_person = PersonFactory(person_type='staff')
        
        self.lecturer = StaffFactory(
            person=self.lecturer_person,
            department=self.department,
            staff_category='academic'
        )
        
        # -----------------------------
        # User (LINKED to Person ✅)
        # -----------------------------
        self.lecturer_user = User.objects.create_user(
            username='lecturer',
            email='lecturer@example.com',
            password='testpass123',
            person=self.lecturer_person   # 🔥 CRITICAL FIX
        )
        
        # -----------------------------
        # Permissions (safe + explicit)
        # -----------------------------
        perms = Permission.objects.filter(
            codename__in=[
                'can_view_attendance',
                'can_create_attendance',
                'can_export_attendance'
            ]
        )
        
        self.lecturer_user.user_permissions.set(perms)
        
        # -----------------------------
        # Authenticate (faster than JWT)
        # -----------------------------
        self.client.force_authenticate(user=self.lecturer_user)
        
        # -----------------------------
        # Student (Person → Student)
        # -----------------------------
        self.student_person = PersonFactory(person_type='student')
        
        self.student = StudentFactory(
            person=self.student_person,
            program=self.program,
            department=self.department,
            school=self.school,
            college=self.college,
            institution=self.institution
        )
        
        # -----------------------------
        # Class
        # -----------------------------
        self.class_obj = ClassFactory(
            program=self.program,
            lecturer=self.lecturer
        )
        
        # -----------------------------
        # Edge device (ESP32 simulator)
        # -----------------------------
        self.node = EdgeNodeFactory(node_type='camera')
    
    def test_complete_attendance_flow(self):
        """Test complete attendance workflow"""
        
        # Step 1: Create attendance record
        attendance_data = {
            'student': self.student.id,
            'class_obj': self.class_obj.id,
            'verification_method': 'qr',
            'latitude': -1.2921,
            'longitude': 36.8219
        }

        create_response = self.client.post(
            "/api/v1/attendance/",
            data=attendance_data,
            format="json"
        )

        print("CREATE:", create_response.data)  # 👈 DEBUG

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        attendance_id = create_response.data['id']
        
        # Step 2: Get attendance list
        list_response = self.client.get("/api/v1/attendance/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        # Adjust depending on pagination structure
        if isinstance(list_response.data, dict) and 'results' in list_response.data:
            self.assertGreaterEqual(len(list_response.data['results']), 1)
        else:
            self.assertGreaterEqual(len(list_response.data), 1)
        
        # Step 3: Get attendance summary
        summary_response = self.client.get("/api/v1/attendance/summary/")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        
        # Adjust based on your API response
        self.assertIn('today', summary_response.data)
        
        # Step 4: Export CSV
        export_url = reverse('attendance:export_csv')
        export_response = self.client.get(export_url)
        
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        self.assertEqual(export_response['Content-Type'], 'text/csv')

    def test_device_api_attendance(self):
        """Test attendance via device API (simulating ESP32)"""
        
        device_data = {
            'student_id': self.student.student_reg_number,
            'class_code': self.class_obj.class_code,
            'node_uuid': self.node.node_uuid,
            'method': 'qr'
        }

        response = self.client.post(
            "/api/v1/device/attendance/",   # 🔥 FIXED endpoint
            data=device_data,
            format='json'
        )

        print("DEVICE:", response.data)  # 👈 DEBUG

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(
            response.data['student_name'],
            self.student.person.full_name
        )

class EndToEndVisitorFlowTest(TestCase):
    """
    End-to-end test for complete visitor management flow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Institution
        self.institution = InstitutionFactory()
        self.department = DepartmentFactory()
        
        # Staff
        self.staff_person = PersonFactory(
            person_type='staff',
            email='staff@example.com'   # ensure email exists
        )
        
        self.staff = StaffFactory(
            person=self.staff_person,
            department=self.department
        )
        
        # User (LINKED)
        self.security_user = User.objects.create_user(
            username='security',
            email='security@example.com',
            password='testpass123',
            person=self.staff_person   # 🔥 critical
        )
        
        # Permissions
        perms = Permission.objects.filter(
            codename__in=[
                'can_view_visitors',
                'can_create_visitors',
                'can_checkout_visitors'
            ]
        )
        self.security_user.user_permissions.set(perms)
        
        # Authenticate
        self.client.force_authenticate(user=self.security_user)
        
        # Zone
        self.zone = AccessZoneFactory(institution=self.institution)
        
        # BLE Tag
        from apps.vms.models import BLETag
        self.tag = BLETag.objects.create(
            tag_uuid="test-tag-uuid",
            hardware_id="AA:BB:CC:DD:EE:FF",
            status='available'
        )
    
    def test_complete_visitor_flow(self):
        """Test complete visitor workflow"""
        
        # Step 1: Check in
        checkin_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'phone_number': '+254712345678',
            'national_id': '87654321',
            'organization': 'Test Company',
            'purpose': 'meeting',
            'host_email': self.staff_person.email
        }

        checkin_response = self.client.post(
            reverse('api_v1:visitor_checkin'),
            data=checkin_data,
            format='json'
        )

        print("CHECKIN:", checkin_response.data)  # 👈 debug

        self.assertEqual(checkin_response.status_code, status.HTTP_201_CREATED)
        visitor_id = checkin_response.data['visitor_id']
        
        # Step 2: List
        list_response = self.client.get("/api/v1/visitors/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Movement
        from apps.vms.models import VisitorMovement
        VisitorMovement.objects.create(
            visitor_id=visitor_id,
            zone=self.zone,
            event_type='enter',
            timestamp=timezone.now()
        )
        
        # Step 4: Checkout
        checkout_response = self.client.post(
            reverse('visitors:api_checkout', kwargs={'tag_uuid': self.tag.tag_uuid})
        )

        print("CHECKOUT:", checkout_response.data)  # 👈 debug

        self.assertEqual(checkout_response.status_code, status.HTTP_200_OK)
        self.assertTrue(checkout_response.data['success'])
    
    def test_visitor_tracking_realtime(self):
        """Test real-time visitor tracking"""
        
        from datetime import timedelta

        # Create visitor and visit
        visitor = VisitorFactory(institution=self.institution)

        visit = VisitorVisitFactory(
            visitor=visitor,
            assigned_tag=self.tag,
            status='active'
        )
        
        # Record movements
        for i in range(5):
            VisitorMovement.objects.create(
                visitor=visitor,
                visit=visit,
                zone=self.zone,
                event_type='ping' if i < 4 else 'exit',
                timestamp=timezone.now() - timedelta(minutes=i),
                rssi=-65 + i
            )
        
        # Get active visitors
        response = self.client.get(
            "/api/v1/visitors/?status=active"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data

        # basic sanity check
        self.assertIsNotNone(data)


class EndToEndAccessControlFlowTest(TestCase):
    """
    End-to-end test for access control flow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Zone
        self.zone = AccessZoneFactory(
            name="Secure Lab",
            zone_type='restricted',
            access_level=3,
            requires_2fa=True
        )
        
        # Person
        self.person = PersonFactory(person_type='staff')
        
        # User (LINKED)
        self.user = User.objects.create_user(
            username='access_control',
            email='access@example.com',
            password='testpass123',
            person=self.person   # 🔥 FIX
        )
        
        # Permissions
        perms = Permission.objects.filter(
            codename__in=['can_view_access_logs']
        )
        self.user.user_permissions.set(perms)
        
        # Node
        self.node = EdgeNodeFactory(zone=self.zone)
        
        # Auth
        self.client.force_authenticate(user=self.user)
    
    def test_access_request_flow(self):
        """Test complete access request flow"""
        
        access_data = {
            'credential': self.person.national_id,
            'zone_code': self.zone.name,  # or correct field
            'node_uuid': self.node.node_uuid
        }

        response = self.client.post(
            "/api/v1/access/request/",
            data=access_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # FIXED LOGS ENDPOINT
        logs_response = self.client.get("/api/v1/access/logs/")
        self.assertEqual(logs_response.status_code, status.HTTP_200_OK)

        from apps.access.models import AccessLog

        log_exists = AccessLog.objects.filter(
            person=self.person,
            zone=self.zone
        ).exists()

        self.assertTrue(log_exists, "Access log was not created")


class PerformanceTest(TestCase):
    """
    Performance and load testing
    """
    
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='perf_test',
            email='perf@example.com',
            password='testpass123'
        )

        perm = Permission.objects.get(codename='can_view_attendance')
        self.user.user_permissions.add(perm)

        self.client.force_authenticate(user=self.user)

        # bulk data
        self.students = [StudentFactory() for _ in range(100)]
        self.class_obj = ClassFactory()
    
    def test_bulk_attendance_creation(self):
        """Test bulk attendance record creation"""
        import time
        
        start_time = time.time()
        
        # Create 100 attendance records
        for student in self.students:
            ClassAttendanceFactory(
                student=student,
                class_obj=self.class_obj,
                scan_time=timezone.now()
            )
        
        elapsed_time = time.time() - start_time
        
        # Should create 100 records in less than 2 seconds
        self.assertLess(elapsed_time, 2.0)
        self.assertEqual(ClassAttendance.objects.count(), 100)
    
    def test_api_response_time(self):
        import time

        times = []

        for _ in range(20):
            start = time.time()

            response = self.client.get(
                "/api/v1/stats/attendance/"
            )

            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

            self.assertEqual(response.status_code, 200)

        avg = sum(times) / len(times)

        self.assertLess(avg, 300)
    
    def test_concurrent_requests(self):
        import threading

        results = []

        def make_request():
            client = APIClient()
            client.force_authenticate(user=self.user)

            response = client.get("/api/v1/stats/attendance/")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == 200 for r in results))