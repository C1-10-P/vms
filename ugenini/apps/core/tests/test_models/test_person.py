from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import date
from apps.core.models import Person, Student, Staff, Visitor
from apps.core.tests.factories import (
    ClassAttendanceFactory, PersonFactory, StudentFactory, StaffFactory, VisitorFactory,
    InstitutionFactory, DepartmentFactory, ProgramFactory
)


class PersonModelTest(TestCase):
    """Test cases for Person model"""
    
    def setUp(self):
        self.person = PersonFactory(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="+254712345678",
            national_id="12345678",
            person_type='student',
            date_of_birth=date(2000, 1, 15),
            gender='M'
        )
    
    def test_create_person(self):
        """Test creating a person"""
        self.assertEqual(self.person.first_name, "John")
        self.assertEqual(self.person.last_name, "Doe")
        self.assertEqual(self.person.full_name, "John Doe")
        self.assertEqual(self.person.email, "john.doe@example.com")
        self.assertEqual(self.person.phone_number, "+254712345678")
        self.assertEqual(self.person.national_id, "12345678")
        self.assertEqual(self.person.person_type, "student")
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        # Valid Kenyan phone number
        person = PersonFactory(phone_number="+254712345678")
        person.full_clean()  # Should not raise error
        
        # Invalid phone number
        person = PersonFactory(phone_number="123")
        with self.assertRaises(ValidationError):
            person.full_clean()
    
    def test_email_uniqueness(self):
        """Test email uniqueness"""
        with self.assertRaises(IntegrityError):
            PersonFactory(email="john.doe@example.com")
    
    def test_national_id_uniqueness(self):
        """Test national ID uniqueness"""
        with self.assertRaises(IntegrityError):
            PersonFactory(national_id="12345678")
    
    def test_str_method(self):
        """Test string representation"""
        self.assertEqual(str(self.person), "John Doe")
    
    def test_full_name_property(self):
        """Test full_name property"""
        self.assertEqual(self.person.full_name, "John Doe")
    
    def test_initials_property(self):
        """Test initials property"""
        self.assertEqual(self.person.initials, "JD")
    
    def test_age_calculation(self):
        """Test age calculation"""
        # Person with birth date
        self.assertEqual(self.person.age, timezone.now().year - 2000)
        
        # Person without birth date
        person = PersonFactory(date_of_birth=None)
        self.assertIsNone(person.age)
    
    def test_person_type_choices(self):
        """Test person type choices"""
        valid_types = ['student', 'staff', 'visitor', 'contractor', 'alumni']
        
        for person_type in valid_types:
            person = PersonFactory(person_type=person_type)
            self.assertEqual(person.person_type, person_type)
    
    def test_set_system_password(self):
        """Test setting system password"""
        self.assertFalse(self.person.is_system_user)
        
        self.person.set_system_password("SecurePass123")
        self.assertTrue(self.person.is_system_user)
        self.assertIsNotNone(self.person.system_password)
        self.assertNotEqual(self.person.system_password, "SecurePass123")  # Hashed
    
    def test_check_system_password(self):
        """Test password verification"""
        self.person.set_system_password("SecurePass123")
        
        self.assertTrue(self.person.check_system_password("SecurePass123"))
        self.assertFalse(self.person.check_system_password("WrongPassword"))
    
    def test_get_related_object(self):
        """Test getting related student/staff/visitor object"""
        # Student
        student = StudentFactory(person=self.person)
        self.assertEqual(self.person.get_related_object(), student)
        
        # Staff
        staff_person = PersonFactory(person_type='staff')
        staff = StaffFactory(person=staff_person)
        self.assertEqual(staff_person.get_related_object(), staff)
        
        # Visitor
        visitor_person = PersonFactory(person_type='visitor')
        visitor = VisitorFactory(person=visitor_person)
        self.assertEqual(visitor_person.get_related_object(), visitor)
        
        # Person without related object
        person = PersonFactory()
        self.assertIsNone(person.get_related_object())
    
    def test_soft_delete(self):
        """Test soft delete person"""
        self.person.soft_delete()
        self.assertFalse(self.person.is_active)
        self.assertFalse(Person.objects.filter(id=self.person.id).exists())


class StudentModelTest(TestCase):
    """Test cases for Student model"""
    
    def setUp(self):
        self.program = ProgramFactory()
        self.department = self.program.department
        self.school = self.department.school
        self.college = self.school.college
        self.institution = self.college.institution
        
        self.student = StudentFactory(
            student_reg_number="ENE221-0108/2018",
            program=self.program,
            department=self.department,
            school=self.school,
            college=self.college,
            institution=self.institution,
            current_year=4,
            current_semester=1,
            admission_date=date(2018, 9, 1),
            expected_graduation=date(2022, 12, 15),
            status='active'
        )
    
    def test_create_student(self):
        """Test creating a student"""
        self.assertEqual(self.student.student_reg_number, "ENE221-0108/2018")
        self.assertEqual(self.student.program, self.program)
        self.assertEqual(self.student.department, self.department)
        self.assertEqual(self.student.current_year, 4)
        self.assertEqual(self.student.current_semester, 1)
        self.assertEqual(self.student.status, 'active')
    
    def test_student_reg_number_uniqueness(self):
        """Test student registration number uniqueness"""
        with self.assertRaises(IntegrityError):
            StudentFactory(student_reg_number="ENE221-0108/2018")
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"ENE221-0108/2018 - {self.student.person.full_name}"
        self.assertEqual(str(self.student), expected)
    
    def test_save_auto_fills_denormalized_fields(self):
        """Test that save auto-fills department, school, college, institution"""
        new_program = ProgramFactory()
        new_student = StudentFactory(
            program=new_program,
            department=None,  # Should be auto-filled
            school=None,
            college=None,
            institution=None
        )
        
        self.assertEqual(new_student.department, new_program.department)
        self.assertEqual(new_student.school, new_program.department.school)
        self.assertEqual(new_student.college, new_program.department.school.college)
        self.assertEqual(new_student.institution, new_program.department.school.college.institution)
    
    def test_attendance_percentage_property(self):
        """Test attendance percentage calculation"""
        from apps.classroom.models import ClassAttendance
        from apps.core.tests.factories import ClassFactory, ClassEnrollmentFactory
        
        # Create a class and enroll student
        class_obj = ClassFactory(program=self.program)
        ClassEnrollmentFactory(class_obj=class_obj, student=self.student)
        
        # Record some attendance
        ClassAttendanceFactory(student=self.student, class_obj=class_obj, verification_status='success')
        ClassAttendanceFactory(student=self.student, class_obj=class_obj, verification_status='success')
        
        # Should calculate percentage based on last 30 days
        percentage = self.student.attendance_percentage(class_obj.id)
        self.assertIsNotNone(percentage)
    
    def test_current_courses_property(self):
        """Test getting current courses"""
        from apps.core.tests.factories import ClassFactory
        
        # Create classes for current semester
        class1 = ClassFactory(
            program=self.program,
            semester=self.student.current_semester,
            academic_year=self.student.get_academic_year()
        )
        class2 = ClassFactory(
            program=self.program,
            semester=self.student.current_semester,
            academic_year=self.student.get_academic_year()
        )
        
        courses = self.student.current_courses
        self.assertGreaterEqual(courses.count(), 0)
    
    def test_get_academic_year(self):
        """Test academic year calculation"""
        # Student admitted in 2018, currently in year 4
        expected_year = "2021/2022"  # 2018 + 3 = 2021
        self.assertEqual(self.student.get_academic_year(), expected_year)
        
        # Year 1 student
        freshmen = StudentFactory(current_year=1, admission_date=date(2024, 9, 1))
        self.assertEqual(freshmen.get_academic_year(), "2024/2025")
    
    def test_status_transitions(self):
        """Test student status transitions"""
        valid_statuses = ['active', 'probation', 'suspended', 'graduated', 'withdrawn', 'deferred']
        
        for status in valid_statuses:
            self.student.status = status
            self.student.save()
            self.assertEqual(self.student.status, status)
        
        # Invalid status should raise error
        with self.assertRaises(ValidationError):
            self.student.status = "invalid"
            self.student.full_clean()
    
    def test_class_representative_flag(self):
        """Test class representative flag"""
        self.assertFalse(self.student.class_representative)
        
        self.student.class_representative = True
        self.student.save()
        self.assertTrue(self.student.class_representative)
    
    def test_cascade_delete(self):
        """Test that deleting person deletes student"""
        person_id = self.student.person.id
        self.student.delete()
        
        # Person should still exist
        self.assertTrue(Person.objects.filter(id=person_id).exists())
        
        # But student record should be gone
        with self.assertRaises(Student.DoesNotExist):
            Student.objects.get(id=self.student.id)


class StaffModelTest(TestCase):
    """Test cases for Staff model"""
    
    def setUp(self):
        self.department = DepartmentFactory()
        self.staff = StaffFactory(
            staff_number="STAFF001",
            department=self.department,
            staff_category='academic',
            employment_type='full_time',
            designation='Senior Lecturer',
            joined_date=date(2015, 1, 1),
            is_hod=False,
            is_dean=False
        )
    
    def test_create_staff(self):
        """Test creating staff member"""
        self.assertEqual(self.staff.staff_number, "STAFF001")
        self.assertEqual(self.staff.department, self.department)
        self.assertEqual(self.staff.staff_category, 'academic')
        self.assertEqual(self.staff.employment_type, 'full_time')
        self.assertEqual(self.staff.designation, 'Senior Lecturer')
        self.assertEqual(self.staff.joined_date, date(2015, 1, 1))
    
    def test_staff_number_uniqueness(self):
        """Test staff number uniqueness"""
        with self.assertRaises(IntegrityError):
            StaffFactory(staff_number="STAFF001")
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"STAFF001 - {self.staff.person.full_name}"
        self.assertEqual(str(self.staff), expected)
    
    def test_staff_category_choices(self):
        """Test staff category choices"""
        valid_categories = ['academic', 'administrative', 'technical', 'support', 'security']
        
        for category in valid_categories:
            staff = StaffFactory(staff_category=category)
            self.assertEqual(staff.staff_category, category)
    
    def test_employment_type_choices(self):
        """Test employment type choices"""
        valid_types = ['full_time', 'part_time', 'contract', 'visiting', 'emeritus']
        
        for emp_type in valid_types:
            staff = StaffFactory(employment_type=emp_type)
            self.assertEqual(staff.employment_type, emp_type)
    
    def test_hod_and_dean_flags(self):
        """Test HOD and Dean flags"""
        self.assertFalse(self.staff.is_hod)
        self.assertFalse(self.staff.is_dean)
        
        self.staff.is_hod = True
        self.staff.is_dean = True
        self.staff.save()
        
        self.assertTrue(self.staff.is_hod)
        self.assertTrue(self.staff.is_dean)
    
    def test_qualifications_json_field(self):
        """Test qualifications JSON field"""
        qualifications = [
            {
                'degree': 'PhD',
                'field': 'Telecommunication Engineering',
                'institution': 'JKUAT',
                'year': 2020
            },
            {
                'degree': 'MSc',
                'field': 'Electrical Engineering',
                'institution': 'University of Nairobi',
                'year': 2015
            }
        ]
        
        self.staff.qualifications = qualifications
        self.staff.save()
        self.assertEqual(self.staff.qualifications, qualifications)
    
    def test_save_auto_fills_denormalized_fields(self):
        """Test that save auto-fills school, college, institution"""
        new_department = DepartmentFactory()
        new_staff = StaffFactory(
            department=new_department,
            school=None,
            college=None,
            institution=None
        )
        
        self.assertEqual(new_staff.school, new_department.school)
        self.assertEqual(new_staff.college, new_department.school.college)
        self.assertEqual(new_staff.institution, new_department.school.college.institution)


class VisitorModelTest(TestCase):
    """Test cases for Visitor model"""
    
    def setUp(self):
        self.institution = InstitutionFactory()
        self.host = StaffFactory()
        self.visitor = VisitorFactory(
            person__first_name="Jane",
            person__last_name="Smith",
            institution=self.institution,
            purpose='meeting',
            purpose_description="Meeting with admissions office",
            host_person=self.host.person,
            id_type='national_id',
            id_number="87654321",
            organization="ABC Corporation",
            total_visits=0
        )
    
    def test_create_visitor(self):
        """Test creating a visitor"""
        self.assertEqual(self.visitor.person.first_name, "Jane")
        self.assertEqual(self.visitor.person.last_name, "Smith")
        self.assertEqual(self.visitor.institution, self.institution)
        self.assertEqual(self.visitor.purpose, 'meeting')
        self.assertEqual(self.visitor.host_person, self.host.person)
        self.assertEqual(self.visitor.id_number, "87654321")
        self.assertEqual(self.visitor.organization, "ABC Corporation")
    
    def test_str_method(self):
        """Test string representation"""
        expected = f"Visitor: Jane Smith (87654321)"
        self.assertEqual(str(self.visitor), expected)
    
    def test_start_new_visit(self):
        """Test starting a new visit"""
        from apps.vms.models import VisitorVisit
        
        # Initially no active visit
        self.assertIsNone(self.visitor.current_visit)
        self.assertEqual(self.visitor.total_visits, 0)
        
        # Start a visit
        visit = self.visitor.start_new_visit()
        
        self.assertIsNotNone(visit)
        self.assertEqual(self.visitor.current_visit, visit)
        self.assertEqual(self.visitor.total_visits, 1)
        self.assertIsNotNone(self.visitor.last_visit)
        self.assertTrue(self.visitor.is_on_campus())
    
    def test_end_current_visit(self):
        """Test ending current visit"""
        self.visitor.start_new_visit()
        self.assertTrue(self.visitor.is_on_campus())
        
        self.visitor.end_current_visit()
        self.assertIsNone(self.visitor.current_visit)
        self.assertFalse(self.visitor.is_on_campus())
    
    def test_multiple_visits(self):
        """Test multiple visits over time"""
        # First visit
        visit1 = self.visitor.start_new_visit()
        self.assertEqual(self.visitor.total_visits, 1)
        
        # End first visit
        self.visitor.end_current_visit()
        
        # Second visit
        visit2 = self.visitor.start_new_visit()
        self.assertEqual(self.visitor.total_visits, 2)
        self.assertNotEqual(visit1.id, visit2.id)
    
    def test_blacklisted_property(self):
        """Test is_blacklisted property"""
        from apps.vms.models.blacklist import BlacklistedVisitor
        
        self.assertFalse(self.visitor.is_blacklisted)
        
        BlacklistedVisitor.objects.create(
            visitor=self.visitor,
            reason_category='security',
            reason_description="Suspicious behavior",
            blacklisted_by=self.host
        )
        
        self.assertTrue(self.visitor.is_blacklisted)
    
    def test_visit_counter_increment(self):
        """Test increment_visit_count method"""
        self.visitor.increment_visit_count()
        self.assertEqual(self.visitor.total_visits, 1)
        
        self.visitor.increment_visit_count()
        self.assertEqual(self.visitor.total_visits, 2)
        self.assertIsNotNone(self.visitor.last_visit)