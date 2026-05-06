from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.core.models import Institution, College, School
from apps.core.tests.factories import InstitutionFactory, CollegeFactory, SchoolFactory


class InstitutionModelTest(TestCase):
    """Test cases for Institution model"""
    
    def setUp(self):
        self.institution = InstitutionFactory(
            name="Jomo Kenyatta University of Agriculture and Technology",
            code="JKUAT",
            abbreviation="JKUAT",
            email="info@jkuat.ac.ke",
            website="www.jkuat.ac.ke",
            established_year=1994,
            motto="Setting Trends in Higher Education",
            vision="To be a university of global excellence",
            mission="To provide quality education"
        )
    
    def test_create_institution(self):
        """Test creating an institution"""
        self.assertEqual(self.institution.name, "Jomo Kenyatta University of Agriculture and Technology")
        self.assertEqual(self.institution.code, "JKUAT")
        self.assertEqual(self.institution.abbreviation, "JKUAT")
        self.assertEqual(self.institution.email, "info@jkuat.ac.ke")
        self.assertEqual(self.institution.established_year, 1994)
        self.assertTrue(self.institution.is_active)
    
    def test_institution_code_uniqueness(self):
        """Test that institution code must be unique"""
        with self.assertRaises(IntegrityError):
            InstitutionFactory(code="JKUAT")
    
    def test_institution_name_uniqueness(self):
        """Test that institution name must be unique"""
        with self.assertRaises(IntegrityError):
            InstitutionFactory(name="Jomo Kenyatta University of Agriculture and Technology")
    
    def test_str_method(self):
        """Test string representation"""
        expected = "Jomo Kenyatta University of Agriculture and Technology (JKUAT)"
        self.assertEqual(str(self.institution), expected)
    
    def test_total_students_property(self):
        """Test total_students property"""
        from apps.core.tests.factories import StudentFactory
        
        # Initially 0
        self.assertEqual(self.institution.total_students, 0)
        
        # Add students
        StudentFactory(institution=self.institution)
        StudentFactory(institution=self.institution)
        
        self.assertEqual(self.institution.total_students, 2)
    
    def test_total_staff_property(self):
        """Test total_staff property"""
        from apps.core.tests.factories import StaffFactory
        
        self.assertEqual(self.institution.total_staff, 0)
        
        StaffFactory(institution=self.institution)
        StaffFactory(institution=self.institution)
        
        self.assertEqual(self.institution.total_staff, 2)
    
    def test_total_colleges_property(self):
        """Test total_colleges property"""
        self.assertEqual(self.institution.total_colleges, 0)
        
        CollegeFactory(institution=self.institution)
        CollegeFactory(institution=self.institution)
        
        self.assertEqual(self.institution.total_colleges, 2)
    
    def test_soft_delete(self):
        """Test soft delete institution"""
        self.institution.soft_delete()
        self.assertFalse(self.institution.is_active)
        self.assertFalse(Institution.objects.filter(id=self.institution.id).exists())
        self.assertTrue(Institution.objects.archived().filter(id=self.institution.id).exists())


class CollegeModelTest(TestCase):
    """Test cases for College model"""
    
    def setUp(self):
        self.institution = InstitutionFactory()
        self.college = CollegeFactory(
            institution=self.institution,
            name="College of Engineering and Technology",
            code="CET",
            dean_name="Prof. John Maina",
            building="Engineering Complex",
            floors=5
        )
    
    def test_create_college(self):
        """Test creating a college"""
        self.assertEqual(self.college.name, "College of Engineering and Technology")
        self.assertEqual(self.college.code, "CET")
        self.assertEqual(self.college.institution, self.institution)
        self.assertEqual(self.college.dean_name, "Prof. John Maina")
        self.assertEqual(self.college.building, "Engineering Complex")
        self.assertEqual(self.college.floors, 5)
        self.assertTrue(self.college.is_active)
    
    def test_college_code_uniqueness(self):
        """Test that college code must be unique"""
        with self.assertRaises(IntegrityError):
            CollegeFactory(code="CET")
    
    def test_unique_together(self):
        """Test unique together constraint (institution, code)"""
        # This should work - different institution
        other_institution = InstitutionFactory(code="OTHER")
        CollegeFactory(institution=other_institution, code="CET")
        
        # This should fail - same institution
        with self.assertRaises(IntegrityError):
            CollegeFactory(institution=self.institution, code="CET")
    
    def test_str_method(self):
        """Test string representation"""
        expected = "College of Engineering and Technology (CET)"
        self.assertEqual(str(self.college), expected)
    
    def test_total_schools_property(self):
        """Test total_schools property"""
        self.assertEqual(self.college.total_schools, 0)
        
        SchoolFactory(college=self.college)
        SchoolFactory(college=self.college)
        
        self.assertEqual(self.college.total_schools, 2)
    
    def test_total_departments_property(self):
        """Test total_departments property (cached)"""
        from apps.core.tests.factories import DepartmentFactory, SchoolFactory
        
        school = SchoolFactory(college=self.college)
        DepartmentFactory(school=school)
        DepartmentFactory(school=school)
        
        # The property should count departments
        self.assertEqual(self.college.total_departments, 2)
    
    def test_cascade_delete_protection(self):
        """Test that deleting institution cascades to colleges"""
        institution_id = self.institution.id
        self.institution.delete()
        
        with self.assertRaises(College.DoesNotExist):
            College.objects.get(id=self.college.id)


class SchoolModelTest(TestCase):
    """Test cases for School model"""
    
    def setUp(self):
        self.college = CollegeFactory()
        self.school = SchoolFactory(
            college=self.college,
            name="School of Electrical, Electronic and Information Engineering",
            code="SEEIE",
            director_name="Prof. Jane Doe",
            building="Engineering Building",
            floor=3,
            accreditation_status="accredited"
        )
    
    def test_create_school(self):
        """Test creating a school"""
        self.assertEqual(self.school.name, "School of Electrical, Electronic and Information Engineering")
        self.assertEqual(self.school.code, "SEEIE")
        self.assertEqual(self.school.college, self.college)
        self.assertEqual(self.school.director_name, "Prof. Jane Doe")
        self.assertEqual(self.school.building, "Engineering Building")
        self.assertEqual(self.school.floor, 3)
        self.assertEqual(self.school.accreditation_status, "accredited")
    
    def test_unique_together(self):
        """Test unique together constraint (college, code)"""
        with self.assertRaises(IntegrityError):
            SchoolFactory(college=self.college, code="SEEIE")
    
    def test_str_method(self):
        """Test string representation"""
        expected = "School of Electrical, Electronic and Information Engineering (SEEIE)"
        self.assertEqual(str(self.school), expected)
    
    def test_total_departments_property(self):
        """Test total_departments property"""
        from apps.core.tests.factories import DepartmentFactory
        
        self.assertEqual(self.school.total_departments, 0)
        
        DepartmentFactory(school=self.school)
        DepartmentFactory(school=self.school)
        
        self.assertEqual(self.school.total_departments, 2)
    
    def test_accreditation_status_choices(self):
        """Test accreditation status choices"""
        valid_statuses = ['accredited', 'provisional', 'pending']
        
        for status in valid_statuses:
            school = SchoolFactory(college=self.college, accreditation_status=status)
            self.assertEqual(school.accreditation_status, status)
        
        # Invalid status should raise error
        with self.assertRaises(ValidationError):
            school = SchoolFactory(college=self.college, accreditation_status="invalid")
            school.full_clean()