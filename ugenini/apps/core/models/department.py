from django.db import models
from .base import BaseModel, SoftDeleteManager

class Department(BaseModel):
    """
    Department (Level 3 in hierarchy).
    Example: Department of Telecommunication and Information Engineering
    """
    school = models.ForeignKey(
        'core.School',  
        on_delete=models.CASCADE, 
        related_name='departments',
        help_text="Parent school"
    )
    name = models.CharField(
        max_length=150,
        help_text="Full name of the department"
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Department code (e.g., TIE)"
    )
    abbreviation = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Short abbreviation"
    )
    
    # Leadership
    hod_title = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Head of Department title (e.g., Professor, Dr.)"
    )
    hod_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Head of Department name"
    )
    hod_contact = models.CharField(max_length=50, blank=True)
    deputy_hod = models.CharField(max_length=100, blank=True)
    
    # Contact
    office_location = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Physical location
    building = models.CharField(max_length=100, blank=True)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    room_number = models.CharField(max_length=20, blank=True)
    
    # Statistics
    total_lecturers = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    
    # Metadata
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        unique_together = [['school', 'code']]
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['school', 'code']),
            models.Index(fields=['hod_name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def update_statistics(self):
        """Update department statistics"""
        from apps.core.models.person import Student, Staff
        
        self.total_students = Student.objects.filter(
            department=self, 
            is_active=True
        ).count()
        self.total_lecturers = Staff.objects.filter(
            department=self, 
            is_active=True,
            staff_category='academic'
        ).count()
        self.save(update_fields=['total_students', 'total_lecturers'])
    
    @property
    def full_hierarchy(self):
        """Get complete hierarchy path"""
        return f"{self.school.college.institution.name} > {self.school.college.name} > {self.school.name} > {self.name}"


class Program(BaseModel):
    """
    Academic Program/Course offered by department.
    Example: Bachelor of Science in Telecommunication and Information Engineering
    """
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='programs',
        help_text="Department offering this program"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full program name"
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Program code (e.g., BSc.TIE)"
    )
    
    # Program details
    level = models.CharField(
        max_length=20, 
        choices=[
            ('certificate', 'Certificate'),
            ('diploma', 'Diploma'),
            ('bachelor', 'Bachelor'),
            ('master', 'Master'),
            ('doctorate', 'Doctorate'),
            ('postdoc', 'Post-Doctoral')
        ],
        help_text="Academic level of program"
    )
    duration_years = models.DecimalField(
        max_digits=3, 
        decimal_places=1,
        help_text="Duration in years"
    )
    duration_semesters = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        help_text="Duration in semesters"
    )
    total_credit_hours = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Total credit hours required"
    )
    
    # Leadership
    coordinator_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Program coordinator"
    )
    coordinator_email = models.EmailField(blank=True)
    coordinator_phone = models.CharField(max_length=20, blank=True)
    
    # Fees and capacity
    tuition_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    max_intake = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    admission_requirements = models.TextField(blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['department', 'name']
        verbose_name = "Program"
        verbose_name_plural = "Programs"
        unique_together = [['department', 'code']]
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['level']),
            models.Index(fields=['department', 'code']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_students(self):
        from apps.core.models.person import Student
        return Student.objects.filter(
            program=self, 
            is_active=True
        ).count()
    
    @property
    def current_students_by_year(self):
        from apps.core.models.person import Student
        return Student.objects.filter(
            program=self, 
            is_active=True
        ).values('current_year').annotate(
            count=models.Count('id')
        )