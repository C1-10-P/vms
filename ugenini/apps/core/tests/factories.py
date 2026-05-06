import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import uuid

from apps.core.models import (
    Institution, College, School, Department, Program,
    Person, Student, Staff, Visitor,
    AcademicUnit, Class, ClassEnrollment
)
from apps.vms.models import Visitor
from apps.vms.models import BLETag, VisitorVisit, VisitorMovement
from apps.access.models import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.log import AccessLog
from apps.firmware.models import EdgeNode, NodeHeartbeat
from apps.classroom.models.attendance import ClassAttendance

User = get_user_model()

# ============ Institution Hierarchy Factories ============

class InstitutionFactory(DjangoModelFactory):
    class Meta:
        model = Institution
    
    name = factory.Sequence(lambda n: f"Test University {n}")
    code = factory.Sequence(lambda n: f"TU{n:03d}")
    abbreviation = factory.LazyAttribute(lambda o: o.code[:3])
    email = factory.LazyAttribute(lambda o: f"info@{o.code.lower()}.ac.ke")
    website = factory.LazyAttribute(lambda o: f"www.{o.code.lower()}.ac.ke")
    established_year = 2000
    is_active = True


class CollegeFactory(DjangoModelFactory):
    class Meta:
        model = College
    
    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"College of Test {n}")
    code = factory.Sequence(lambda n: f"CT{n:03d}")
    abbreviation = factory.LazyAttribute(lambda o: o.code[:3])
    dean_name = "Dr. Test Dean"
    contact_email = factory.LazyAttribute(lambda o: f"dean@{o.code.lower()}.ac.ke")
    is_active = True


class SchoolFactory(DjangoModelFactory):
    class Meta:
        model = School
    
    college = factory.SubFactory(CollegeFactory)
    name = factory.Sequence(lambda n: f"School of Testing {n}")
    code = factory.Sequence(lambda n: f"ST{n:03d}")
    abbreviation = factory.LazyAttribute(lambda o: o.code[:3])
    director_name = "Prof. Test Director"
    contact_email = factory.LazyAttribute(lambda o: f"director@{o.code.lower()}.ac.ke")
    is_active = True


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department
    
    school = factory.SubFactory(SchoolFactory)
    name = factory.Sequence(lambda n: f"Department of Test {n}")
    code = factory.Sequence(lambda n: f"DT{n:03d}")
    abbreviation = factory.LazyAttribute(lambda o: o.code[:3])
    hod_name = "Prof. Test HOD"
    contact_email = factory.LazyAttribute(lambda o: f"hod@{o.code.lower()}.ac.ke")
    is_active = True


class ProgramFactory(DjangoModelFactory):
    class Meta:
        model = Program
    
    department = factory.SubFactory(DepartmentFactory)
    name = factory.Sequence(lambda n: f"Bachelor of Test {n}")
    code = factory.Sequence(lambda n: f"BT{n:03d}")
    level = 'bachelor'
    duration_years = 4
    coordinator_name = "Dr. Test Coordinator"
    is_active = True


# ============ Person Factories ============

class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person
    
    uuid = factory.LazyFunction(lambda: str(uuid.uuid4()))
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
    national_id = factory.Sequence(lambda n: f"{n:08d}")
    person_type = 'student'
    is_active = True


class StudentFactory(DjangoModelFactory):
    class Meta:
        model = Student
    
    person = factory.SubFactory(PersonFactory, person_type='student')
    student_reg_number = factory.Sequence(lambda n: f"STU{n:05d}")
    program = factory.SubFactory(ProgramFactory)
    department = factory.LazyAttribute(lambda o: o.program.department)
    school = factory.LazyAttribute(lambda o: o.department.school)
    college = factory.LazyAttribute(lambda o: o.school.college)
    institution = factory.LazyAttribute(lambda o: o.college.institution)
    current_year = 2
    current_semester = 1
    admission_date = date(2024, 9, 1)
    status = 'active'
    is_active = True


class StaffFactory(DjangoModelFactory):
    class Meta:
        model = Staff
    
    person = factory.SubFactory(PersonFactory, person_type='staff')
    staff_number = factory.Sequence(lambda n: f"STF{n:05d}")
    department = factory.SubFactory(DepartmentFactory)
    school = factory.LazyAttribute(lambda o: o.department.school)
    college = factory.LazyAttribute(lambda o: o.school.college)
    institution = factory.LazyAttribute(lambda o: o.college.institution)
    staff_category = 'academic'
    employment_type = 'full_time'
    designation = 'Senior Lecturer'
    joined_date = date(2020, 1, 1)
    is_active = True


class VisitorFactory(DjangoModelFactory):
    class Meta:
        model = Visitor
    
    person = factory.SubFactory(PersonFactory, person_type='visitor')
    institution = factory.SubFactory(InstitutionFactory)
    # purpose = 'meeting'
    id_type = 'national_id'
    id_number = factory.Sequence(lambda n: f"ID{n:08d}")
    organization = factory.Faker('company')
    is_active = True


# ============ Academic Factories ============

class AcademicUnitFactory(DjangoModelFactory):
    class Meta:
        model = AcademicUnit
    
    department = factory.SubFactory(DepartmentFactory)
    code = factory.Sequence(lambda n: f"TEST{n:03d}")
    name = factory.Sequence(lambda n: f"Test Course {n}")
    credit_hours = 3
    level = 2
    semester_offered = '1'
    is_elective = False
    is_active = True


class ClassFactory(DjangoModelFactory):
    class Meta:
        model = Class

    # Step 1: Create program FIRST
    program = factory.SubFactory(ProgramFactory)

    # Step 2: Force academic_unit to use SAME department
    academic_unit = factory.SubFactory(
        AcademicUnitFactory,
        department=factory.SelfAttribute('..program.department')
    )

    class_code = factory.Sequence(lambda n: f"CLS{n:05d}")
    academic_year = "2024/2025"
    semester = 1
    start_date = date(2024, 9, 1)
    end_date = date(2024, 12, 15)

    lecturer = factory.SubFactory(StaffFactory, staff_category='academic')

    capacity = 50
    enrolled_count = 0

    schedule = {
        'monday': {'start': '08:00', 'end': '10:00', 'room': 'Lab 1'},
        'wednesday': {'start': '14:00', 'end': '16:00', 'room': 'Lecture Hall A'}
    }

    is_active = True


class ClassEnrollmentFactory(DjangoModelFactory):
    class Meta:
        model = ClassEnrollment
    
    class_obj = factory.SubFactory(ClassFactory)
    student = factory.SubFactory(StudentFactory)
    enrollment_date = date(2024, 9, 1)
    status = 'registered'


# ============ Attendance Factories ============

class ClassAttendanceFactory(DjangoModelFactory):
    class Meta:
        model = ClassAttendance
    
    student = factory.SubFactory(StudentFactory)
    class_obj = factory.LazyAttribute(lambda o: o.student.program.classes.first())
    node = None
    scan_time = factory.LazyFunction(timezone.now)
    scan_date = factory.LazyAttribute(lambda o: o.scan_time.date())
    verification_method = 'qr'
    verification_status = 'success'
    confidence_score = 95.5
    latitude = -1.2921
    longitude = 36.8219
    ip_address = "192.168.1.100"


# ============ Visitor Tracking Factories ============

class BLETagFactory(DjangoModelFactory):
    class Meta:
        model = BLETag
    
    tag_uuid = factory.LazyFunction(lambda: str(uuid.uuid4()))
    hardware_id = factory.Sequence(lambda n: f"AA:BB:CC:DD:{n:04d}")
    tag_type = 'wearable'
    status = 'available'
    battery_level = 100
    total_assignments = 0
    is_active = True


class VisitorVisitFactory(DjangoModelFactory):
    class Meta:
        model = VisitorVisit
    
    visitor = factory.SubFactory(VisitorFactory)
    assigned_tag = factory.SubFactory(BLETagFactory, status='assigned')
    check_in_time = factory.LazyFunction(timezone.now)
    status = 'active'
    checked_in_by = factory.SubFactory(StaffFactory)


class VisitorMovementFactory(DjangoModelFactory):
    class Meta:
        model = VisitorMovement
    
    visitor = factory.SubFactory(VisitorFactory)
    tag = factory.LazyAttribute(lambda o: o.visitor.current_visit.assigned_tag if o.visitor.current_visit else None)
    visit = factory.LazyAttribute(lambda o: o.visitor.current_visit)
    zone = None
    node = None
    event_type = 'ping'
    timestamp = factory.LazyFunction(timezone.now)
    rssi = -65


# ============ Access Control Factories ============

class AccessZoneFactory(DjangoModelFactory):
    class Meta:
        model = AccessZone
    
    name = factory.Sequence(lambda n: f"Test Zone {n}")
    code = factory.Sequence(lambda n: f"ZONE{n:03d}")
    zone_type = 'building'
    institution = factory.SubFactory(InstitutionFactory)
    access_level = 1
    requires_2fa = False
    capacity = 100
    current_occupancy = 0
    is_active = True


class AccessPermissionFactory(DjangoModelFactory):
    class Meta:
        model = AccessPermission
    
    zone = factory.SubFactory(AccessZoneFactory)
    person_type = 'student'
    priority = 0
    monday = True
    tuesday = True
    wednesday = True
    thursday = True
    friday = True
    saturday = False
    sunday = False
    is_active = True


class AccessLogFactory(DjangoModelFactory):
    class Meta:
        model = AccessLog
    
    person = factory.SubFactory(PersonFactory)
    person_type = 'student'
    zone = factory.SubFactory(AccessZoneFactory)
    verification_method = 'tag'
    result = 'granted'
    access_time = factory.LazyFunction(timezone.now)
    response_time_ms = 150
    ip_address = "192.168.1.100"


# ============ Device Factories ============

class EdgeNodeFactory(DjangoModelFactory):
    class Meta:
        model = EdgeNode
    
    node_uuid = factory.LazyFunction(lambda: str(uuid.uuid4()))
    node_type = 'ble_scanner'
    name = factory.Sequence(lambda n: f"Node {n}")
    mac_address = factory.Sequence(lambda n: f"AA:BB:CC:DD:EE:{n:02d}")
    institution = factory.SubFactory(InstitutionFactory)
    status = 'offline'
    has_ble = True
    has_camera = False
    config_version = "1.0.0"
    is_active = True


class NodeHeartbeatFactory(DjangoModelFactory):
    class Meta:
        model = NodeHeartbeat
    
    node = factory.SubFactory(EdgeNodeFactory)
    timestamp = factory.LazyFunction(timezone.now)
    uptime_seconds = 86400
    free_heap = 150000
    rssi = -55
    battery_level = 85
    is_active = True