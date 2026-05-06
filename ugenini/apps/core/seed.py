import random
import uuid
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db import transaction
from faker import Faker

fake = Faker('en_KE')

from .models import (
    Institution, College, School, Department, Program,
    Person, Student, Staff, Visitor,
    AcademicUnit, Class, ClassEnrollment
)


class CoreDataSeeder:
    """Seed data for core app models - FIXED VERSION"""
    
    @staticmethod
    def seed_institutions():
        """Create institutions"""
        institutions = []
        
        inst, created = Institution.objects.get_or_create(
            code='JKUAT',
            defaults={
                'name': 'Jomo Kenyatta University of Agriculture and Technology',
                'abbreviation': 'JKUAT',
                'email': 'info@jkuat.ac.ke',
                'website': 'www.jkuat.ac.ke',
                'established_year': 1994,
                'motto': 'Setting Trends in Higher Education',
                'is_active': True
            }
        )
        institutions.append(inst)
        print(f"✓ Institution: {inst.name}")
        
        return institutions
    
    @staticmethod
    def seed_colleges(institution):
        """Create colleges under an institution"""
        colleges = []
        colleges_data = [
            {'name': 'College of Engineering and Technology', 'code': 'CET', 'dean_name': 'Prof. John Maina'},
            {'name': 'College of Health Sciences', 'code': 'CHS', 'dean_name': 'Prof. Mary Wanjiku'},
            {'name': 'College of Pure and Applied Sciences', 'code': 'CPAS', 'dean_name': 'Prof. Peter Omondi'},
            {'name': 'College of Humanities and Social Sciences', 'code': 'CHSS', 'dean_name': 'Prof. Jane Akinyi'},
        ]
        
        for data in colleges_data:
            college, created = College.objects.get_or_create(
                institution=institution,
                code=data['code'],
                defaults=data
            )
            colleges.append(college)
            print(f"  ✓ College: {college.name}")
        
        return colleges
    
    @staticmethod
    def seed_schools(college):
        """Create schools under a college - ONE TIME ONLY"""
        schools = []
        
        # Define schools per college (avoid duplicates)
        schools_by_college = {
            'CET': [
                ('School of Electrical, Electronic and Information Engineering', 'SEEIE', 'Dr. James Otieno'),
                ('School of Mechanical, Manufacturing and Materials Engineering', 'SMMME', 'Prof. Ann Njeri'),
                ('School of Civil and Environmental Engineering', 'SCEE', 'Dr. David Kipruto')
            ],
            'CHS': [
                ('School of Medicine', 'SOM', 'Prof. Lucy Muthoni'),
                ('School of Pharmacy', 'SOP', 'Dr. Samuel Kariuki'),
                ('School of Nursing', 'SON', 'Prof. Grace Wanjiru')
            ],
            'CPAS': [
                ('School of Biological Sciences', 'SBS', 'Dr. Catherine Wangari'),
                ('School of Physical Sciences', 'SPS', 'Prof. Joseph Njoroge'),
                ('School of Mathematics', 'SM', 'Dr. Esther Chepkirui')
            ],
            'CHSS': [
                ('School of Business', 'SOB', 'Prof. Richard Mwangi'),
                ('School of Economics', 'SOE', 'Dr. Patrick Ochieng'),
                ('School of Law', 'SOL', 'Prof. Nancy Barasa')
            ],
        }
        
        college_code = college.code
        if college_code in schools_by_college:
            for name, code, director in schools_by_college[college_code]:
                school, created = School.objects.get_or_create(
                    college=college,
                    code=code,
                    defaults={
                        'name': name,
                        'director_name': director,
                        'building': f'{college.name.split()[0]} Building',
                        'is_active': True
                    }
                )
                schools.append(school)
                print(f"    ✓ School: {school.name}")
        
        return schools
    
    @staticmethod
    def seed_departments(school):
        """Create departments under a school - ONE TIME ONLY"""
        departments = []
        
        # Define departments per school
        dept_by_school = {
            'SEEIE': [
                ('Telecommunication and Information Engineering', 'TIE', 'Prof. Elijah Mwangi'),
                ('Electrical and Electronic Engineering', 'EEE', 'Dr. Florence Adhiambo'),
                ('Computer Science', 'CS', 'Prof. Timothy Kinyua'),
            ],
            'SMMME': [
                ('Mechanical Engineering', 'MEE', 'Prof. Samuel Kimani'),
                ('Mechatronics Engineering', 'MTE', 'Prof. Bernard Kipchumba'),
                ('Manufacturing Engineering', 'MFE', 'Dr. Elizabeth Wanjiku'),
            ],
            'SCEE': [
                ('Civil Engineering', 'CVE', 'Dr. Elizabeth Wanjiku'),
                ('Structural Engineering', 'STE', 'Prof. Joseph Mbugua'),
                ('Construction Management', 'CMT', 'Dr. Peter Mwangi'),
            ],
            'SOM': [
                ('Human Pathology', 'HUP', 'Prof. James Kariuki'),
                ('Medical Physiology', 'MDP', 'Dr. Ann Wanjiku'),
                ('Clinical Medicine', 'CLM', 'Prof. Peter Odhiambo'),
            ],
            'SOP': [
                ('Pharmaceutical Chemistry', 'PHC', 'Dr. Mary Atieno'),
                ('Pharmacology', 'PHA', 'Prof. John Otieno'),
                ('Clinical Pharmacy', 'CLP', 'Dr. Susan Wambui'),
            ],
            'SON': [
                ('Nursing Education', 'NED', 'Prof. Grace Muthoni'),
                ('Community Health', 'COH', 'Dr. James Mwangi'),
                ('Midwifery', 'MID', 'Prof. Jane Akinyi'),
            ],
            'SBS': [
                ('Biochemistry', 'BCH', 'Dr. Peter Kipchoge'),
                ('Microbiology', 'MCB', 'Prof. Ann Njeri'),
                ('Biotechnology', 'BTE', 'Dr. John Mwangi'),
            ],
            'SPS': [
                ('Physics', 'PHY', 'Prof. David Kiptoo'),
                ('Chemistry', 'CHE', 'Dr. Sarah Chemutai'),
                ('Geology', 'GEL', 'Prof. Joseph Kipruto'),
            ],
            'SM': [
                ('Pure Mathematics', 'PMT', 'Dr. Esther Chepkirui'),
                ('Applied Mathematics', 'AMT', 'Prof. Timothy Kinyua'),
                ('Statistics', 'STA', 'Dr. James Otieno'),
            ],
            'SOB': [
                ('Accounting', 'ACC', 'Prof. John Maina'),
                ('Marketing', 'MKT', 'Dr. Ann Wanjiku'),
                ('Human Resource', 'HRM', 'Prof. Peter Omondi'),
            ],
            'SOE': [
                ('Economics', 'ECO', 'Dr. James Kariuki'),
                ('Econometrics', 'ECM', 'Prof. Mary Atieno'),
                ('Development Economics', 'DEV', 'Dr. John Otieno'),
            ],
            'SOL': [
                ('Civil Law', 'CIV', 'Prof. Nancy Barasa'),
                ('Criminal Law', 'CRM', 'Dr. James Mwangi'),
                ('Business Law', 'BUS', 'Prof. Jane Akinyi'),
            ],
        }
        
        school_code = school.code
        if school_code in dept_by_school:
            for name, code, hod in dept_by_school[school_code]:
                department, created = Department.objects.get_or_create(
                    school=school,
                    code=code,
                    defaults={
                        'name': name,
                        'hod_name': hod,
                        'building': school.building,
                        'is_active': True
                    }
                )
                departments.append(department)
                print(f"      ✓ Department: {department.name}")
        
        return departments
    
    @staticmethod
    def seed_programs(department):
        """Create programs under a department"""
        programs = []
        
        # Define programs per department
        program_by_dept = {
            'TIE': [
                ('Bachelor of Science in Telecommunication and Information Engineering', 'BSc.TIE', 'bachelor', 4),
                ('Master of Science in Telecommunication Engineering', 'MSc.TE', 'master', 2),
                ('PhD in Telecommunication Engineering', 'PhD.TE', 'doctorate', 3),
            ],
            'EEE': [
                ('Bachelor of Science in Electrical and Electronic Engineering', 'BSc.EEE', 'bachelor', 4),
                ('Master of Science in Electrical Engineering', 'MSc.EE', 'master', 2),
            ],
            'CS': [
                ('Bachelor of Science in Computer Science', 'BSc.CS', 'bachelor', 4),
                ('Master of Science in Computer Science', 'MSc.CS', 'master', 2),
            ],
            'MEE': [
                ('Bachelor of Science in Mechanical Engineering', 'BSc.MEE', 'bachelor', 4),
                ('Master of Science in Mechanical Engineering', 'MSc.ME', 'master', 2),
            ],
            'MTE': [
                ('Bachelor of Science in Mechatronics Engineering', 'BSc.MTE', 'bachelor', 4),
                ('Master of Science in Mechatronics', 'MSc.MT', 'master', 2),
            ],
            'CVE': [
                ('Bachelor of Science in Civil Engineering', 'BSc.CVE', 'bachelor', 4),
                ('Master of Science in Civil Engineering', 'MSc.CV', 'master', 2),
            ],
        }
        
        dept_code = department.code
        if dept_code in program_by_dept:
            for name, code, level, duration in program_by_dept[dept_code]:
                program, created = Program.objects.get_or_create(
                    department=department,
                    code=code,
                    defaults={
                        'name': name,
                        'level': level,
                        'duration_years': duration,
                        'duration_semesters': duration * 2,
                        'total_credit_hours': duration * 30,
                        'coordinator_name': fake.name(),
                        'coordinator_email': fake.email(),
                        'is_active': True
                    }
                )
                programs.append(program)
                print(f"        ✓ Program: {program.name}")
        
        return programs


class PersonDataSeeder:
    """Seed data for persons - FIXED VERSION"""
    
    @staticmethod
    def _make_aware(dt):
        """Convert naive datetime to aware datetime"""
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt)
        return dt
    
    @staticmethod
    def seed_students(count=50):
        """Create student records"""
        students = []
        programs = list(Program.objects.filter(is_active=True))
        
        if not programs:
            print("⚠ No programs found. Please seed programs first.")
            return []
        
        for i in range(count):
            program = random.choice(programs)
            department = program.department
            school = department.school
            college = school.college
            institution = college.institution
            
            first_name = fake.first_name()
            last_name = fake.last_name()
            national_id = f"{random.randint(10000000, 99999999)}"
            
            # Ensure unique national_id
            while Person.objects.filter(national_id=national_id).exists():
                national_id = f"{random.randint(10000000, 99999999)}"
            
            person = Person.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@student.{institution.code.lower()}.ac.ke",
                phone_number=f"+254{random.randint(700000000, 799999999)}",
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=30),
                gender=random.choice(['M', 'F']),
                national_id=national_id,
                person_type='student',
                is_active=True
            )
            
            year = random.randint(1, 4)
            admission_year = 2024 - (year - 1)
            reg_number = f"{department.code}{random.randint(1000, 9999)}/{admission_year}"
            
            # Ensure unique reg number
            while Student.objects.filter(student_reg_number=reg_number).exists():
                reg_number = f"{department.code}{random.randint(1000, 9999)}/{admission_year}"
            
            student = Student.objects.create(
                person=person,
                student_reg_number=reg_number,
                program=program,
                department=department,
                school=school,
                college=college,
                institution=institution,
                current_year=year,
                current_semester=random.choice([1, 2]),
                admission_date=date(admission_year, 9, 1),
                expected_graduation=date(admission_year + 4, 12, 15),
                mode_of_study=random.choice(['full_time', 'part_time']),
                status='active',
                cumulative_gpa=round(random.uniform(2.0, 4.0), 2),
                is_active=True
            )
            students.append(student)
        
        print(f"✓ Created {len(students)} student records")
        return students
    
    @staticmethod
    def seed_staff(count=25):
        """Create staff records"""
        staff_members = []
        departments = list(Department.objects.filter(is_active=True))
        
        if not departments:
            print("⚠ No departments found. Please seed departments first.")
            return []
        
        for i in range(count):
            department = random.choice(departments)
            school = department.school
            college = school.college
            institution = college.institution
            
            first_name = fake.first_name()
            last_name = fake.last_name()
            national_id = f"{random.randint(10000000, 99999999)}"
            
            while Person.objects.filter(national_id=national_id).exists():
                national_id = f"{random.randint(10000000, 99999999)}"
            
            person = Person.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@{institution.code.lower()}.ac.ke",
                phone_number=f"+254{random.randint(700000000, 799999999)}",
                date_of_birth=fake.date_of_birth(minimum_age=30, maximum_age=65),
                gender=random.choice(['M', 'F']),
                national_id=national_id,
                person_type='staff',
                is_active=True
            )
            
            staff_number = f"STF{random.randint(10000, 99999)}"
            while Staff.objects.filter(staff_number=staff_number).exists():
                staff_number = f"STF{random.randint(10000, 99999)}"
            
            staff = Staff.objects.create(
                person=person,
                staff_number=staff_number,
                department=department,
                school=school,
                college=college,
                institution=institution,
                job_title=fake.job(),
                staff_category='academic',
                employment_type='full_time',
                designation=random.choice(['Professor', 'Senior Lecturer', 'Lecturer']),
                office_location=f"Room {random.randint(100, 500)}",
                office_phone=f"+254{random.randint(700000000, 799999999)}",
                joined_date=date(random.randint(2010, 2023), random.randint(1, 12), random.randint(1, 28)),
                is_hod=i < 3,
                is_active=True
            )
            staff_members.append(staff)
        
        print(f"✓ Created {len(staff_members)} staff records")
        return staff_members
    
    @staticmethod
    def seed_visitors(count=20):
        """Create visitor records"""
        visitors = []
        institutions = list(Institution.objects.filter(is_active=True))
        
        if not institutions:
            print("⚠ No institutions found.")
            return []
        
        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            national_id = f"{random.randint(10000000, 99999999)}"
            
            while Person.objects.filter(national_id=national_id).exists():
                national_id = f"{random.randint(10000000, 99999999)}"
            
            person = Person.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@example.com",
                phone_number=f"+254{random.randint(700000000, 799999999)}",
                national_id=national_id,
                person_type='visitor',
                is_active=True
            )
            
            visitor = Visitor.objects.create(
                person=person,
                institution=random.choice(institutions),
                purpose=random.choice(['meeting', 'delivery', 'maintenance', 'conference', 'research']),
                id_type='national_id',
                id_number=national_id,
                organization=fake.company(),
                total_visits=random.randint(1, 5),
                last_visit=timezone.now() - timedelta(days=random.randint(1, 365)),
                is_active=True
            )
            visitors.append(visitor)
        
        print(f"✓ Created {len(visitors)} visitor records")
        return visitors


class AcademicDataSeeder:
    """Seed data for academic structures - FIXED VERSION"""
    
    @staticmethod
    def seed_academic_units(count=40):
        """Create academic units (courses)"""
        units = []
        departments = list(Department.objects.filter(is_active=True))
        
        if not departments:
            print("⚠ No departments found.")
            return []
        
        course_names = [
            'Introduction to Programming', 'Data Structures', 'Algorithms', 'Database Systems',
            'Computer Networks', 'Operating Systems', 'Software Engineering', 'Web Development',
            'Machine Learning', 'Artificial Intelligence', 'Cybersecurity', 'Cloud Computing',
            'Digital Signal Processing', 'Communication Systems', 'Wireless Networks',
            'Embedded Systems', 'IoT Systems', 'Robotics', 'Control Systems', 'Power Electronics',
            'Circuit Theory', 'Electromagnetic Fields', 'Microprocessors', 'VLSI Design'
        ]
        
        created = 0
        for i in range(count):
            department = random.choice(departments)
            level = random.randint(1, 4)
            code_num = random.randint(4000, 4999) if level > 2 else random.randint(2000, 3999)
            code = f"{department.code}{code_num}"
            
            if AcademicUnit.objects.filter(code=code).exists():
                continue
            
            unit = AcademicUnit.objects.create(
                department=department,
                code=code,
                name=random.choice(course_names) + f" {random.randint(101, 499)}",
                credit_hours=random.choice([2, 3, 4]),
                lecture_hours=random.choice([30, 45, 60]),
                lab_hours=random.choice([0, 15, 30]) if random.choice([True, False]) else 0,
                level=level,
                semester_offered=str(random.choice([1, 2])),
                is_elective=random.choice([True, False]),
                is_active=True
            )
            units.append(unit)
            created += 1
        
        print(f"✓ Created {len(units)} academic units")
        return units
    
    @staticmethod
    def seed_classes(count=25):
        """Create class offerings - FIXED"""
        classes = []
        academic_units = list(AcademicUnit.objects.filter(is_active=True))
        programs = list(Program.objects.filter(is_active=True))
        lecturers = list(Staff.objects.filter(staff_category='academic', is_active=True))
        
        if not academic_units:
            print("⚠ No academic units found.")
            return []
        if not programs:
            print("⚠ No programs found.")
            return []
        if not lecturers:
            print("⚠ No lecturers found. Creating some...")
            lecturers = PersonDataSeeder.seed_staff(10)
        
        academic_years = ['2024/2025']
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        for i in range(count):
            unit = random.choice(academic_units)
            program = random.choice(programs)
            lecturer = random.choice(lecturers) if lecturers else None
            
            if not lecturer:
                continue
            
            semester = random.choice([1, 2])
            class_code = f"{unit.code}-{academic_years[0][:4]}{semester}"
            
            if Class.objects.filter(class_code=class_code).exists():
                class_code = f"{unit.code}-{academic_years[0][:4]}{semester}-{chr(65+i)}"
            
            selected_day = random.choice(days)
            start_hour = random.choice([8, 10, 14, 16])
            
            class_obj = Class.objects.create(
                academic_unit=unit,
                program=program,
                class_code=class_code,
                academic_year=academic_years[0],
                semester=semester,
                start_date=date(2024, 9, 1),
                end_date=date(2024, 12, 15),
                schedule={
                    selected_day: {
                        'start': f"{start_hour:02d}:00",
                        'end': f"{start_hour + 2:02d}:00",
                        'room': f"Room {random.randint(100, 500)}"
                    }
                },
                lecturer=lecturer,
                capacity=random.choice([30, 45, 60]),
                enrolled_count=0,
                is_active=True
            )
            classes.append(class_obj)
        
        print(f"✓ Created {len(classes)} classes")
        return classes
    
    @staticmethod
    def seed_enrollments(students_per_class=15):
        """Enroll students in classes"""
        enrollments = []
        classes = list(Class.objects.filter(is_active=True))
        students = list(Student.objects.filter(is_active=True))
        
        if not classes:
            print("⚠ No classes found.")
            return []
        if not students:
            print("⚠ No students found.")
            return []
        
        for class_obj in classes:
            # Randomly select students for this class
            num_to_enroll = min(students_per_class, len(students))
            selected_students = random.sample(students, num_to_enroll)
            
            for student in selected_students:
                if ClassEnrollment.objects.filter(class_obj=class_obj, student=student).exists():
                    continue
                
                enrollment = ClassEnrollment.objects.create(
                    class_obj=class_obj,
                    student=student,
                    enrollment_date=date(2024, 9, 1),
                    status='registered'
                )
                enrollments.append(enrollment)
            
            # Update enrolled count
            class_obj.enrolled_count = ClassEnrollment.objects.filter(class_obj=class_obj, status='registered').count()
            class_obj.save()
        
        print(f"✓ Created {len(enrollments)} class enrollments")
        return enrollments