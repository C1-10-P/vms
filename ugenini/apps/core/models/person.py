from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.contrib.auth.hashers import make_password, check_password
from .base import BaseModel, SoftDeleteManager
from .department import Department, Program
from .institution import Institution, College, School

class Person(BaseModel):
    """
    Unified Person Model - Base for all people in the system.
    Uses Single Table Inheritance pattern.
    """
    class PersonType(models.TextChoices):
        STUDENT = 'student', 'Student'
        STAFF = 'staff', 'Staff'
        VISITOR = 'visitor', 'Visitor'
        CONTRACTOR = 'contractor', 'Contractor'
        ALUMNI = 'alumni', 'Alumni'
    
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'
    
    # Basic Information
    first_name = models.CharField(
        max_length=50,
        db_index=True,
        help_text="First name/given name"
    )
    last_name = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Last name/family name"
    )
    other_names = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Middle names or other names"
    )
    date_of_birth = models.DateField(
        null=True, 
        blank=True,
        db_index=True
    )
    gender = models.CharField(
        max_length=1, 
        choices=Gender.choices, 
        blank=True,
        db_index=True
    )
    
    # Contact Information
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        validators=[RegexValidator(regex=r'^\+?254[0-9]{9}$')],
        help_text="Phone number with country code (e.g., +254712345678)"
    )
    email = models.EmailField(
        blank=True,
        db_index=True,
        help_text="Primary email address"
    )
    alternate_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    # Identification
    national_id = models.CharField(
        max_length=20, 
        unique=True, 
        null=True, 
        blank=True,
        db_index=True,
        help_text="National ID number (e.g., Kenyan ID)"
    )
    passport_number = models.CharField(
        max_length=20, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Passport number for international visitors"
    )
    tax_id = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Tax identification number (KRA PIN)"
    )
    
    # System Information
    person_type = models.CharField(
        max_length=20, 
        choices=PersonType.choices,
        db_index=True,
        help_text="Type of person in the system"
    )
    photo = models.ImageField(
        upload_to='persons/photos/',
        blank=True,
        null=True,
        help_text="Profile photo"
    )
    signature = models.ImageField(
        upload_to='persons/signatures/',
        blank=True,
        null=True
    )
    
    # Biometric Data (encrypted)
    fingerprint_template = models.BinaryField(null=True, blank=True)
    face_encoding = models.JSONField(null=True, blank=True)
    
    # Authentication (for system access)
    system_password = models.CharField(max_length=128, blank=True)
    is_system_user = models.BooleanField(
        default=False,
        help_text="Can this person access the system?"
    )
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Person"
        verbose_name_plural = "Persons"
        indexes = [
            models.Index(fields=['national_id']),
            models.Index(fields=['email']),
            models.Index(fields=['person_type']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['phone_number']),
        ]
    
    def __str__(self):
        return self.full_name
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name_with_title(self):
        """Get full name with title if available"""
        if hasattr(self, 'staff') and self.staff.designation:
            return f"{self.staff.designation} {self.full_name}"
        return self.full_name
    
    @property
    def initials(self):
        """Get initials"""
        return f"{self.first_name[0]}{self.last_name[0]}".upper()
    
    @property
    def age(self):
        """Calculate age"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < 
                (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def set_system_password(self, raw_password):
        """Hash and set system password"""
        self.system_password = make_password(raw_password)
        self.is_system_user = True
    
    def check_system_password(self, raw_password):
        """Verify system password"""
        return check_password(raw_password, self.system_password)
    
    def get_related_object(self):
        """Get the related student, staff, or visitor object"""
        if self.person_type == 'student' and hasattr(self, 'student'):
            return self.student
        elif self.person_type == 'staff' and hasattr(self, 'staff'):
            return self.staff
        elif self.person_type == 'visitor' and hasattr(self, 'visitor'):
            return self.visitor
        return None


class Student(BaseModel):
    """
    Student extension - links Person to academic structure.
    """
    person = models.OneToOneField(
        Person, 
        on_delete=models.CASCADE, 
        related_name='student',
        help_text="Person record"
    )
    student_reg_number = models.CharField(
        max_length=20, 
        unique=True,
        null=False, 
        blank=False,
        validators=[MinLengthValidator(8)],
        db_index=True,
        help_text="Registration number (e.g., ENE221-0108/2018)"
    )
    
    # Academic hierarchy (denormalized for performance)
    program = models.ForeignKey(
        Program, 
        on_delete=models.PROTECT, 
        related_name='students',
        help_text="Program of study"
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.PROTECT,
        help_text="Department (denormalized)"
    )
    school = models.ForeignKey(
        School, 
        on_delete=models.PROTECT,
        help_text="School (denormalized)"
    )
    college = models.ForeignKey(
        College, 
        on_delete=models.PROTECT,
        help_text="College (denormalized)"
    )
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.PROTECT,
        help_text="Institution (denormalized)"
    )
    
    # Academic progress
    current_year = models.PositiveSmallIntegerField(
        help_text="Current year of study (1-6)"
    )
    current_semester = models.PositiveSmallIntegerField(
        help_text="Current semester (1-3)"
    )
    admission_date = models.DateField(db_index=True)
    expected_graduation = models.DateField(null=True, blank=True)
    actual_graduation = models.DateField(null=True, blank=True)
    
    # Academic performance
    cumulative_gpa = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    total_credits_earned = models.PositiveIntegerField(default=0)
    
    # Relationships
    supervisor = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='supervisees',
        help_text="Academic supervisor"
    )
    class_representative = models.BooleanField(
        default=False,
        help_text="Is class representative?"
    )
    
    # Status
    mode_of_study = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('distance', 'Distance Learning'),
            ('evening', 'Evening'),
            ('online', 'Online')
        ],
        default='full_time'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('probation', 'Probation'),
            ('suspended', 'Suspended'),
            ('graduated', 'Graduated'),
            ('withdrawn', 'Withdrawn'),
            ('deferred', 'Deferred')
        ],
        default='active',
        db_index=True
    )
    
    # Special needs
    has_disability = models.BooleanField(default=False)
    disability_description = models.TextField(blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['student_reg_number']
        verbose_name = "Student"
        verbose_name_plural = "Students"
        indexes = [
            models.Index(fields=['student_reg_number']),
            models.Index(fields=['program', 'current_year']),
            models.Index(fields=['status']),
            models.Index(fields=['admission_date']),
            models.Index(fields=['department', 'current_year']),
        ]
    
    def __str__(self):
        return f"{self.student_reg_number} - {self.person.full_name}"
    
    def save(self, *args, **kwargs):
        """Auto-fill denormalized fields from program"""
        if self.program_id and not self.department_id:
            self.department = self.program.department
            self.school = self.department.school
            self.college = self.school.college
            self.institution = self.college.institution
        super().save(*args, **kwargs)
    
    @property
    def attendance_percentage(self, class_id=None):
        """Calculate attendance percentage"""
        from apps.classroom.models.attendance import ClassAttendance
        from django.utils import timezone
        from datetime import timedelta
        
        # Get attendance for last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        attended = ClassAttendance.objects.filter(
            student=self,
            scan_time__gte=thirty_days_ago,
            verification_status='success'
        ).count()
        
        # Get total classes in period
        total = self.program.classes.filter(
            start_date__lte=timezone.now(),
            end_date__gte=thirty_days_ago
        ).count()
        
        return (attended / total * 100) if total > 0 else 0
    
    @property
    def current_courses(self):
        """Get current semester courses"""
        from apps.core.models.academic import Class
        from django.utils import timezone
        
        return Class.objects.filter(
            program=self.program,
            semester=self.current_semester,
            academic_year=self.get_academic_year(),
            is_active=True
        )
    
    def get_academic_year(self):
        """Get current academic year based on admission date"""
        from datetime import date
        today = date.today()
        year = self.admission_date.year + (self.current_year - 1)
        return f"{year}/{year+1}"


class Staff(BaseModel):
    """
    Staff extension - employees of the institution.
    """
    class StaffCategory(models.TextChoices):
        ACADEMIC = 'academic', 'Academic'
        ADMINISTRATIVE = 'administrative', 'Administrative'
        TECHNICAL = 'technical', 'Technical'
        SUPPORT = 'support', 'Support'
        SECURITY = 'security', 'Security'
    
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        CONTRACT = 'contract', 'Contract'
        VISITING = 'visiting', 'Visiting'
        EMERITUS = 'emeritus', 'Emeritus'
    
    person = models.OneToOneField(
        Person, 
        on_delete=models.CASCADE, 
        related_name='staff'
    )
    staff_number = models.CharField(
        max_length=20, 
        unique=True,
        db_index=True
    )
    
    # Academic hierarchy
    department = models.ForeignKey(
        Department, 
        on_delete=models.PROTECT, 
        related_name='staff_members'
    )
    school = models.ForeignKey(
        School, 
        on_delete=models.PROTECT,
        help_text="School (denormalized)"
    )
    college = models.ForeignKey(
        College, 
        on_delete=models.PROTECT,
        help_text="College (denormalized)"
    )
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.PROTECT,
        help_text="Institution (denormalized)"
    )
    
    # Job details
    job_title = models.CharField(max_length=100, blank=True)
    staff_category = models.CharField(
        max_length=20, 
        choices=StaffCategory.choices,
        db_index=True
    )
    employment_type = models.CharField(
        max_length=20, 
        choices=EmploymentType.choices,
        db_index=True
    )
    designation = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Academic title (e.g., Professor, Senior Lecturer)"
    )
    
    # Office
    office_location = models.CharField(max_length=100, blank=True)
    office_phone = models.CharField(max_length=20, blank=True)
    office_hours = models.CharField(max_length=200, blank=True)
    
    # Qualifications
    qualifications = models.JSONField(
        default=list,
        blank=True,
        help_text="List of qualifications: [{'degree': 'PhD', 'field': 'Engineering', 'institution': 'JKUAT', 'year': 2020}]"
    )
    research_interests = models.JSONField(default=list, blank=True)
    
    # Employment dates
    joined_date = models.DateField(db_index=True)
    contract_end_date = models.DateField(null=True, blank=True)
    
    # Management
    is_hod = models.BooleanField(default=False)
    is_dean = models.BooleanField(default=False)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['staff_number']
        verbose_name = "Staff"
        verbose_name_plural = "Staff"
        indexes = [
            models.Index(fields=['staff_number']),
            models.Index(fields=['staff_category']),
            models.Index(fields=['department', 'staff_category']),
        ]
    
    def __str__(self):
        return f"{self.staff_number} - {self.person.full_name}"
    
    def save(self, *args, **kwargs):
        """Auto-fill denormalized fields"""
        if self.department_id:
            self.school = self.department.school
            self.college = self.school.college
            self.institution = self.college.institution
        super().save(*args, **kwargs)


class Visitor(BaseModel):
    """
    Visitor extension - external people visiting the institution.
    """
    class IDType(models.TextChoices):
        NATIONAL_ID = 'national_id', 'National ID'
        PASSPORT = 'passport', 'Passport'
        DRIVERS_LICENSE = 'drivers_license', "Driver's License"
        ALIEN_ID = 'alien_id', 'Alien ID'
    
    person = models.OneToOneField(
        Person, 
        on_delete=models.CASCADE, 
        related_name='visitor'
    )
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.PROTECT,
        help_text="Institution being visited"
    )
    
    # Visit details
    purpose_of_visit = models.CharField(
        max_length=255,
        help_text="Reason for visit"
    )
    host_person = models.ForeignKey(
        Person, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='core_hosted_visitors',
        help_text="Staff member being visited"
    )
    host_department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="Department being visited"
    )
    
    # Identification
    id_type = models.CharField(
        max_length=20, 
        choices=IDType.choices,
        help_text="Type of ID provided"
    )
    id_number = models.CharField(
        max_length=50,
        help_text="ID number provided"
    )
    id_verified = models.BooleanField(default=False)
    id_verified_by = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='verified_ids'
    )
    id_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Vehicle
    vehicle_registration = models.CharField(max_length=20, blank=True)
    vehicle_make = models.CharField(max_length=50, blank=True)
    vehicle_color = models.CharField(max_length=30, blank=True)
    
    # Organization
    organization = models.CharField(
        max_length=150, 
        blank=True,
        help_text="Organization/company the visitor represents"
    )
    organization_contact = models.CharField(max_length=100, blank=True)
    
    # Security
    blacklisted = models.BooleanField(default=False, db_index=True)
    blacklist_reason = models.TextField(blank=True)
    blacklisted_at = models.DateTimeField(null=True, blank=True)
    blacklisted_by = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='blacklisted_visitors'
    )
    
    # Statistics
    total_visits = models.PositiveIntegerField(default=0)
    last_visit = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"
        indexes = [
            models.Index(fields=['id_number']),
            models.Index(fields=['blacklisted']),
            models.Index(fields=['purpose_of_visit']),
            models.Index(fields=['host_person']),
        ]
    
    def __str__(self):
        return f"Visitor: {self.person.full_name} ({self.person.national_id})"
    
    def increment_visit_count(self):
        """Increment total visits counter"""
        self.total_visits += 1
        self.last_visit = models.functions.Now()
        self.save(update_fields=['total_visits', 'last_visit'])
    
    @property
    def is_blacklisted(self):
        """Check if visitor is blacklisted"""
        return self.blacklisted