from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import BaseModel, TimeStampedModel, SoftDeleteManager
from .department import Department
from .person import Staff, Student

class AcademicUnit(BaseModel):
    """
    Course/Subject/Unit offered by department.
    Example: ETI 2403 - Analogue Filters
    """
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='academic_units'
    )
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Unit code (e.g., ETI2403)"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full unit name"
    )
    
    # Details
    credit_hours = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    lecture_hours = models.PositiveSmallIntegerField(default=0)
    lab_hours = models.PositiveSmallIntegerField(default=0)
    tutorial_hours = models.PositiveSmallIntegerField(default=0)
    
    # Level
    level = models.PositiveSmallIntegerField(
        help_text="Year level (1-6)",
        validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    semester_offered = models.CharField(
        max_length=5,
        choices=[('1', 'Semester 1'), ('2', 'Semester 2')],
        help_text="Which semester is this offered?"
    )
    
    # Classification
    is_elective = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)
    is_lab_course = models.BooleanField(default=False)
    
    # Prerequisites
    prerequisites = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True,
        help_text="Required prerequisite units"
    )
    
    # Description
    description = models.TextField(blank=True)
    learning_outcomes = models.TextField(blank=True)
    assessment_methods = models.JSONField(default=list, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['department', 'level', 'code']
        verbose_name = "Academic Unit"
        verbose_name_plural = "Academic Units"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['department', 'level']),
            models.Index(fields=['level', 'semester_offered']),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class Class(BaseModel):
    """
    Specific offering of an academic unit in a semester.
    Example: TIE 4th Year - Class of 2025/2026 Semester 
    """
    academic_unit = models.ForeignKey(
        AcademicUnit, 
        on_delete=models.CASCADE, 
        related_name='classes'
    )
    program = models.ForeignKey(
        'core.Program', 
        on_delete=models.CASCADE, 
        related_name='classes'
    )
    
    # Identification
    class_code = models.CharField(
        max_length=30, 
        unique=True,
        help_text="e.g., TIE4101-2025S1"
    )


    class_group = models.CharField(
        max_length=10,
        blank=True,
        help_text="Group number if multiple classes"
    )
    
    # Schedule
    academic_year = models.CharField(
        max_length=9,
        help_text="e.g., 2025/2026"
    )
    semester = models.PositiveSmallIntegerField(
        choices=[(1, 'Semester 1'), (2, 'Semester 2'), (3, 'Semester 3')]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Schedule (JSON for flexibility)
    schedule = models.JSONField(
        default=dict,
        help_text="""{
            'monday': {'start': '08:00', 'end': '10:00', 'room': 'Lab 1'},
            'wednesday': {'start': '14:00', 'end': '16:00', 'room': 'Lecture Hall A'}
        }"""
    )
    
    # Staff
    lecturer = models.ForeignKey(
        Staff, 
        on_delete=models.PROTECT, 
        related_name='classes_teaching',
        help_text="Primary lecturer"
    )
    assistant_lecturer = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='classes_assisting'
    )
    teaching_assistants = models.ManyToManyField(
        Staff, 
        blank=True,
        related_name='classes_ta'
    )
    
    # Capacity
    capacity = models.PositiveIntegerField(default=50)
    enrolled_count = models.PositiveIntegerField(default=0)
    
    # Students enrolled
    students = models.ManyToManyField(
        Student, 
        through='core.ClassEnrollment',
        related_name='classes'
    )
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['academic_year', '-semester', 'class_code']
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        indexes = [
            models.Index(fields=['class_code']),
            models.Index(fields=['academic_year', 'semester']),
            models.Index(fields=['lecturer']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        """
        Human-friendly display used everywhere (UI, dropdowns, logs)
        """
        if self.academic_unit:
            return f"{self.academic_unit.name} ({self.class_code})"
        return self.class_code
    
    def update_enrolled_count(self):
        """Update enrolled count from through model"""
        self.enrolled_count = self.enrollments.filter(status='registered').count()
        self.save(update_fields=['enrolled_count'])


class ClassEnrollment(TimeStampedModel):
    """
    Through model for Class-Student enrollment with status tracking.
    """
    class EnrollmentStatus(models.TextChoices):
        REGISTERED = 'registered', 'Registered'
        DROPPED = 'dropped', 'Dropped'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        PENDING = 'pending', 'Pending'
    
    class_obj = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    
    enrollment_date = models.DateField(auto_now_add=True)
    drop_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.REGISTERED,
        db_index=True
    )
    
    # Performance tracking
    attendance_count = models.PositiveIntegerField(default=0)
    total_classes = models.PositiveIntegerField(default=0)
    attendance_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Audit
    registered_by = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='enrollments_created'
    )
    
    class Meta:
        ordering = ['-enrollment_date']
        unique_together = [['class_obj', 'student']]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['class_obj', 'status']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.student_reg_number} - {self.class_obj.class_code}"
    
    def update_attendance_stats(self):
        """Update attendance statistics"""
        from apps.classroom.models.attendance import ClassAttendance
        
        self.attendance_count = ClassAttendance.objects.filter(
            student=self.student,
            class_obj=self.class_obj,
            verification_status='success'
        ).count()
        
        # Get total class sessions from schedule
        self.total_classes = self.calculate_total_sessions()
        
        if self.total_classes > 0:
            self.attendance_percentage = (
                self.attendance_count / self.total_classes * 100
            )
        else:
            self.attendance_percentage = 0
        
        self.save(update_fields=['attendance_count', 'total_classes', 'attendance_percentage'])
    
    def calculate_total_sessions(self):
        """Calculate number of class sessions in the semester"""
        from datetime import datetime, timedelta
        
        sessions = 0
        current = self.class_obj.start_date
        schedule = self.class_obj.schedule
        
        while current <= self.class_obj.end_date:
            weekday = current.strftime('%A').lower()
            if weekday in schedule:
                sessions += 1
            current += timedelta(days=1)
        
        return sessions