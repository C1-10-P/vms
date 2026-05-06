from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from .base import BaseModel, SoftDeleteManager

class Institution(BaseModel):
    """
    Top-level organization (University).
    Example: Jomo Kenyatta University of Agriculture and Technology
    """
    name = models.CharField(
        max_length=150, 
        unique=True,
        help_text="Full legal name of the institution"
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        validators=[MinLengthValidator(2)],
        help_text="Short institution code (e.g., JKUAT)"
    )
    abbreviation = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Common abbreviation (e.g., JKUAT)"
    )
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to='institutions/logos/',
        blank=True,
        null=True
    )
    established_year = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        help_text="Year of establishment"
    )
    motto = models.CharField(max_length=200, blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    
    # Contact persons
    vice_chancellor = models.CharField(max_length=100, blank=True)
    registrar = models.CharField(max_length=100, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = "Institution"
        verbose_name_plural = "Institutions"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def total_students(self):
        """Get total number of students"""
        return self.students.filter(is_active=True).count()
    
    @property
    def total_staff(self):
        """Get total number of staff"""
        return self.staff.filter(is_active=True).count()
    
    @property
    def total_colleges(self):
        """Get total number of colleges"""
        return self.colleges.filter(is_active=True).count()


class College(BaseModel):
    """
    College/School/Faculty (Level 1 in hierarchy).
    Example: College of Engineering and Technology
    """
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.CASCADE, 
        related_name='colleges',
        help_text="Parent institution"
    )
    name = models.CharField(
        max_length=150,
        help_text="Full name of the college"
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="College code (e.g., CET)"
    )
    abbreviation = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Short abbreviation"
    )
    
    # Leadership
    dean_title = models.CharField(max_length=50, blank=True)
    dean_name = models.CharField(max_length=100, blank=True)
    deputy_dean_name = models.CharField(max_length=100, blank=True)
    
    # Contact
    office_location = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Physical location
    building = models.CharField(max_length=100, blank=True)
    floors = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Metadata
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = "College"
        verbose_name_plural = "Colleges"
        unique_together = [['institution', 'code']]
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['institution', 'code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def total_schools(self):
        return self.schools.filter(is_active=True).count()
    
    @property
    def total_departments(self):
        return self.departments.filter(is_active=True).count()
    
    @property
    def total_students(self):
        from apps.core.models.person import Student
        return Student.objects.filter(
            college=self, 
            is_active=True
        ).count()


class School(BaseModel):
    """
    School (Level 2 in hierarchy).
    Example: School of Electrical, Electronic and Information Engineering
    """
    college = models.ForeignKey(
        College, 
        on_delete=models.CASCADE, 
        related_name='schools',
        help_text="Parent college"
    )
    name = models.CharField(
        max_length=150,
        help_text="Full name of the school"
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="School code (e.g., SEEIE)"
    )
    abbreviation = models.CharField(max_length=20, blank=True)
    
    # Leadership
    director_title = models.CharField(max_length=50, blank=True)
    director_name = models.CharField(max_length=100, blank=True)
    assistant_director = models.CharField(max_length=100, blank=True)
    
    # Contact
    office_location = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Physical location
    building = models.CharField(max_length=100, blank=True)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Metadata
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    accreditation_status = models.CharField(
        max_length=20,
        choices=[
            ('accredited', 'Accredited'),
            ('provisional', 'Provisional'),
            ('pending', 'Pending'),
        ],
        default='accredited'
    )
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = "School"
        verbose_name_plural = "Schools"
        unique_together = [['college', 'code']]
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['college', 'code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def total_departments(self):
        return self.departments.filter(is_active=True).count()
    
    @property
    def total_students(self):
        from apps.core.models.person import Student
        return Student.objects.filter(
            school=self, 
            is_active=True
        ).count()