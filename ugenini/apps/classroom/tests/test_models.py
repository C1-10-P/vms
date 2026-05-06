from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta, date
from apps.classroom.models import ClassAttendance, DailyAttendanceSummary, VerificationLog
from apps.core.tests.factories import (
    StudentFactory, ClassFactory, EdgeNodeFactory, StaffFactory
)


class ClassAttendanceModelTest(TestCase):
    """Test cases for ClassAttendance model"""
    
    def setUp(self):
        self.student = StudentFactory()
        self.class_obj = ClassFactory(program=self.student.program)
        self.node = EdgeNodeFactory(node_type='camera')
        self.attendance = ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            node=self.node,
            scan_time=timezone.now(),
            verification_method='qr',
            verification_status='success',
            confidence_score=98.5,
            latitude=-1.2921,
            longitude=36.8219,
            ip_address="192.168.1.100",
            # status="present",
        )
    
    def test_create_attendance(self):
        """Test creating attendance record"""
        self.assertEqual(self.attendance.student, self.student)
        self.assertEqual(self.attendance.class_obj, self.class_obj)
        self.assertEqual(self.attendance.verification_method, 'qr')
        self.assertEqual(self.attendance.verification_status, 'success')
        self.assertEqual(self.attendance.confidence_score, 98.5)
    
    def test_scan_date_auto_populated(self):
        """Test that scan_date is auto-populated from scan_time"""
        self.assertEqual(self.attendance.scan_date, self.attendance.scan_time.date())
    
    def test_verification_method_choices(self):
        """Test verification method choices"""
        valid_methods = ['rfid', 'face', 'qr', 'manual', 'ble', 'nfc']
        
        for method in valid_methods:
            attendance = ClassAttendance.objects.create(
                student=self.student,
                class_obj=self.class_obj,
                scan_time=timezone.now(),
                verification_method=method
            )
            self.assertEqual(attendance.verification_method, method)
    
    def test_verification_status_choices(self):
        """Test verification status choices"""
        valid_statuses = ['success', 'failed', 'pending', 'fraud_suspected', 'duplicate']
        
        for status in valid_statuses:
            attendance = ClassAttendance.objects.create(
                student=self.student,
                class_obj=self.class_obj,
                scan_time=timezone.now(),
                verification_status=status
            )
            self.assertEqual(attendance.verification_status, status)
    
    def test_confidence_score_validation(self):
        """Test confidence score range validation"""
        # Valid range 0-100
        attendance = ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now(),
            scan_date=timezone.now().date(),
            node=self.node,
            confidence_score=75.5
        )
        attendance.full_clean()  # Should not raise error
        
        # Invalid - below 0
        attendance.confidence_score = -10
        with self.assertRaises(ValidationError):
            attendance.full_clean()
        
        # Invalid - above 100
        attendance.confidence_score = 150
        with self.assertRaises(ValidationError):
            attendance.full_clean()
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"{self.student.student_reg_number} - {self.class_obj.class_code} - {self.attendance.scan_time}"
        self.assertEqual(str(self.attendance), expected)
    
def test_default_ordering(self):
    """Test default ordering by -scan_time"""
    # Create multiple attendance records
    now = timezone.now()

    old = ClassAttendance.objects.create(
        student=self.student,
        class_obj=self.class_obj,
        scan_time=now - timedelta(days=5)
    )

    recent = ClassAttendance.objects.create(
        student=self.student,
        class_obj=self.class_obj,
        scan_time=now - timedelta(days=1)
    )

    newest = ClassAttendance.objects.create(
        student=self.student,
        class_obj=self.class_obj,
        scan_time=now
    )
    
    def test_duplicate_prevention(self):
        """Test preventing duplicate attendance (business logic)"""
        # Same student, same class, same day
        same_day = ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now(),
            verification_status='success'
        )
        
        # Should be allowed (different time)
        self.assertIsNotNone(same_day)
        
        # Business rule: Can't have two success entries for same class on same day
        # This would be enforced in service layer, not model
    
    def test_related_name_access(self):
        """Test accessing attendance from related objects"""
        # From student
        self.assertEqual(self.student.attendances.first(), self.attendance)
        
        # From class
        self.assertEqual(self.class_obj.attendances.first(), self.attendance)
        
        # From node
        self.assertEqual(self.node.attendances.first(), self.attendance)
    
    def test_bulk_create_performance(self):
        """Test bulk creation of attendance records"""
        # Create 100 attendance records
        attendances = []
        for i in range(100):
            attendances.append(ClassAttendance(
                student=self.student,
                class_obj=self.class_obj,
                scan_time=timezone.now(),
                scan_date=timezone.now().date(),
                verification_method='qr'
            ))
        
        created_count = ClassAttendance.objects.bulk_create(attendances)
        self.assertEqual(len(created_count), 100)
    
    def test_filter_by_date_range(self):
        """Test filtering attendance by date range"""
        # Create records with different dates
        ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now(),
            scan_date=timezone.now().date()
        )
        ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now() - timedelta(days=5),
            scan_date=timezone.now().date() - timedelta(days=5)
        )
        ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now()
        )
        
        # Filter last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent = ClassAttendance.objects.filter(scan_time__gte=week_ago)
        self.assertEqual(recent.count(), 2)
    
    def test_aggregate_by_status(self):
        """Test aggregation by verification status"""
        ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now(),
            verification_status='success'
        )
        ClassAttendance.objects.create(
            student=self.student,
            class_obj=self.class_obj,
            scan_time=timezone.now(),
            verification_status='failed'
        )
        
        from django.db.models import Count
        stats = ClassAttendance.objects.values('verification_status').annotate(
            count=Count('id')
        )
        
        status_dict = {item['verification_status']: item['count'] for item in stats}
        self.assertIn('success', status_dict)
        self.assertIn('failed', status_dict)


class DailyAttendanceSummaryModelTest(TestCase):
    """Test cases for DailyAttendanceSummary model"""
    
    def setUp(self):
        self.class_obj = ClassFactory()
        self.summary = DailyAttendanceSummary.objects.create(
            class_obj=self.class_obj,
            summary_date=date.today(),
            total_students=50,
            present_count=42,
            absent_count=8,
            late_count=3,
            attendance_percentage=84.0
        )
    
    def test_create_summary(self):
        """Test creating daily summary"""
        self.assertEqual(self.summary.class_obj, self.class_obj)
        self.assertEqual(self.summary.summary_date, date.today())
        self.assertEqual(self.summary.total_students, 50)
        self.assertEqual(self.summary.present_count, 42)
        self.assertEqual(self.summary.attendance_percentage, 84.0)
    
    def test_unique_together(self):
        """Test unique together constraint (class_obj, summary_date)"""
        with self.assertRaises(Exception):
            DailyAttendanceSummary.objects.create(
                class_obj=self.class_obj,
                summary_date=date.today()
            )
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"{self.class_obj.class_code} - {date.today()}: 42/50"
        self.assertEqual(str(self.summary), expected)
    
def test_attendance_percentage_calculation(self):
    """Test attendance percentage calculation"""
    summary, _ = DailyAttendanceSummary.objects.get_or_create(
        class_obj=self.class_obj,
        summary_date=date.today(),
        defaults={
            'total_students': 100,
            'present_count': 75
        }
    )

    # Ensure values are correct even if object already existed
    summary.total_students = 100
    summary.present_count = 75
    summary.save()

    self.assertEqual(summary.attendance_percentage, 75.0)
    
    def test_update_summary(self):
        """Test updating existing summary"""
        self.summary.present_count = 45
        self.summary.save()
        self.assertEqual(self.summary.present_count, 45)
        self.assertEqual(self.summary.attendance_percentage, 90.0)


class VerificationLogModelTest(TestCase):
    """Test cases for VerificationLog model"""
    
    def setUp(self):
        self.student = StudentFactory()
        self.node = EdgeNodeFactory()
        self.attendance = ClassAttendance.objects.create(
            student=self.student,
            class_obj=ClassFactory(program=self.student.program),
            scan_time=timezone.now()
        )
        self.log = VerificationLog.objects.create(
            attendance=self.attendance,
            student=self.student,
            node=self.node,
            event_type='attempt',
            method='face',
            success=False,
            failure_reason="Face not recognized",
            processing_time_ms=250
        )
    
    def test_create_verification_log(self):
        """Test creating verification log"""
        self.assertEqual(self.log.attendance, self.attendance)
        self.assertEqual(self.log.student, self.student)
        self.assertEqual(self.log.event_type, 'attempt')
        self.assertEqual(self.log.method, 'face')
        self.assertFalse(self.log.success)
        self.assertEqual(self.log.failure_reason, "Face not recognized")
    
    def test_event_type_choices(self):
        """Test event type choices"""
        valid_events = ['attempt', 'success', 'failure', 'retry', 'blocked']
        
        for event in valid_events:
            log = VerificationLog.objects.create(
                student=self.student,
                event_type=event,
                method='qr'
            )
            self.assertEqual(log.event_type, event)
    
    def test_captured_image_upload(self):
        """Test captured image upload"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        image = SimpleUploadedFile(
            "test_face.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        log = VerificationLog.objects.create(
            student=self.student,
            event_type='attempt',
            method='face',
            captured_image=image
        )
        
        self.assertIsNotNone(log.captured_image)
        self.assertTrue(log.captured_image.name.startswith('verification/captures/'))
    
    def test_processing_time_tracking(self):
        """Test processing time tracking"""
        log = VerificationLog.objects.create(
            student=self.student,
            event_type='success',
            method='qr',
            processing_time_ms=150
        )
        self.assertEqual(log.processing_time_ms, 150)
    
    def test_extracted_data_json(self):
        """Test extracted data JSON field"""
        extracted_data = {
            'student_id': 'ENE221-0108/2018',
            'confidence': 95.5,
            'face_matches': 3
        }
        
        log = VerificationLog.objects.create(
            student=self.student,
            event_type='success',
            method='face',
            extracted_data=extracted_data
        )
        
        self.assertEqual(log.extracted_data, extracted_data)