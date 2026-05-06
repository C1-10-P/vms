from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()

from .models import (
    Institution, College, School, Department, Program,
    Person, Student, Staff, Visitor,
    AcademicUnit, Class, ClassEnrollment
)


class InstitutionSerializer(serializers.ModelSerializer):
    """Serializer for Institution model"""
    total_students = serializers.IntegerField(read_only=True)
    total_staff = serializers.IntegerField(read_only=True)
    total_colleges = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Institution
        fields = ['id', 'uuid', 'name', 'code', 'abbreviation', 'address', 'phone',
                  'email', 'website', 'logo', 'logo_url', 'established_year', 'motto', 
                  'vision', 'mission', 'vice_chancellor', 'registrar', 'total_students',
                  'total_staff', 'total_colleges', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'logo_url']


class CollegeSerializer(serializers.ModelSerializer):
    """Serializer for College model"""
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    total_schools = serializers.IntegerField(read_only=True)
    total_departments = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = College
        fields = ['id', 'uuid', 'institution', 'institution_name', 'name', 'code',
                  'abbreviation', 'dean_title', 'dean_name', 'office_location',
                  'contact_phone', 'contact_email', 'building', 'floors',
                  'established_year', 'description', 'total_schools', 'total_departments',
                  'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class SchoolSerializer(serializers.ModelSerializer):
    """Serializer for School model"""
    college_name = serializers.CharField(source='college.name', read_only=True)
    institution_name = serializers.CharField(source='college.institution.name', read_only=True)
    total_departments = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = School
        fields = ['id', 'uuid', 'college', 'college_name', 'institution_name', 'name', 'code',
                  'abbreviation', 'director_title', 'director_name', 'office_location',
                  'contact_phone', 'contact_email', 'building', 'floor',
                  'established_year', 'accreditation_status', 'description',
                  'total_departments', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    college_name = serializers.CharField(source='school.college.name', read_only=True)
    institution_name = serializers.CharField(source='school.college.institution.name', read_only=True)
    full_hierarchy = serializers.CharField(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    total_staff = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'uuid', 'school', 'school_name', 'college_name', 'institution_name',
                  'name', 'code', 'abbreviation', 'hod_title', 'hod_name', 'hod_contact',
                  'deputy_hod', 'office_location', 'contact_phone', 'contact_email',
                  'building', 'floor', 'room_number', 'total_lecturers',
                  'total_students', 'total_staff', 'established_year', 'description',
                  'full_hierarchy', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'full_hierarchy']


class ProgramSerializer(serializers.ModelSerializer):
    """Serializer for Program model"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    school_name = serializers.CharField(source='department.school.name', read_only=True)
    college_name = serializers.CharField(source='department.school.college.name', read_only=True)
    institution_name = serializers.CharField(source='department.school.college.institution.name', read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = Program
        fields = ['id', 'uuid', 'department', 'department_name', 'school_name', 'college_name',
                  'institution_name', 'name', 'code', 'level', 'level_display',
                  'duration_years', 'duration_semesters', 'total_credit_hours',
                  'coordinator_name', 'coordinator_email', 'coordinator_phone',
                  'tuition_fee', 'max_intake', 'description', 'admission_requirements',
                  'total_students', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class PersonSerializer(serializers.ModelSerializer):
    """Serializer for Person model"""
    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Person
        fields = ['id', 'uuid', 'first_name', 'last_name', 'other_names', 'full_name',
                  'initials', 'date_of_birth', 'age', 'gender', 'phone_number',
                  'email', 'alternate_email', 'address', 'national_id', 'passport_number',
                  'tax_id', 'person_type', 'photo', 'photo_url', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'full_name',
                           'initials', 'age', 'photo_url']
    
    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url
        return None


class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student model"""
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(person_type='student'),
        source='person',
        write_only=True
    )
    program_name = serializers.CharField(source='program.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    mode_of_study_display = serializers.CharField(source='get_mode_of_study_display', read_only=True)
    
    class Meta:
        model = Student
        fields = ['id', 'uuid', 'person', 'person_id', 'student_reg_number',
                  'program', 'program_name', 'department', 'department_name',
                  'school', 'school_name', 'college', 'college_name',
                  'institution', 'institution_name', 'current_year', 'current_semester',
                  'admission_date', 'expected_graduation', 'actual_graduation',
                  'cumulative_gpa', 'total_credits_earned', 'supervisor',
                  'class_representative', 'mode_of_study', 'mode_of_study_display',
                  'status', 'status_display', 'has_disability', 'disability_description',
                  'attendance_percentage', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class StaffSerializer(serializers.ModelSerializer):
    """Serializer for Staff model"""
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(person_type='staff'),
        source='person',
        write_only=True
    )
    department_name = serializers.CharField(source='department.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    staff_category_display = serializers.CharField(source='get_staff_category_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    
    class Meta:
        model = Staff
        fields = ['id', 'uuid', 'person', 'person_id', 'staff_number', 'department',
                  'department_name', 'school', 'school_name', 'college', 'college_name',
                  'institution', 'institution_name', 'job_title', 'staff_category',
                  'staff_category_display', 'employment_type', 'employment_type_display',
                  'designation', 'office_location', 'office_phone', 'office_hours',
                  'qualifications', 'research_interests', 'joined_date', 'contract_end_date',
                  'is_hod', 'is_dean', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class AcademicUnitSerializer(serializers.ModelSerializer):
    """Serializer for AcademicUnit model"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    prerequisites_list = serializers.StringRelatedField(many=True, read_only=True)
    semester_offered_display = serializers.CharField(source='get_semester_offered_display', read_only=True)
    
    class Meta:
        model = AcademicUnit
        fields = ['id', 'uuid', 'department', 'department_name', 'code', 'name',
                  'credit_hours', 'lecture_hours', 'lab_hours', 'tutorial_hours',
                  'level', 'semester_offered', 'semester_offered_display',
                  'is_elective', 'is_required', 'is_lab_course', 'prerequisites',
                  'prerequisites_list', 'description', 'learning_outcomes',
                  'assessment_methods', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model"""
    academic_unit_name = serializers.CharField(source='academic_unit.name', read_only=True)
    academic_unit_code = serializers.CharField(source='academic_unit.code', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    lecturer_name = serializers.CharField(source='lecturer.person.full_name', read_only=True)
    assistant_lecturer_name = serializers.CharField(source='assistant_lecturer.person.full_name', read_only=True, allow_null=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    semester_display = serializers.CharField(source='get_semester_display', read_only=True)
    
    class Meta:
        model = Class
        fields = ['id', 'uuid', 'academic_unit', 'academic_unit_name', 'academic_unit_code',
                  'program', 'program_name', 'class_code', 'class_group', 'academic_year',
                  'semester', 'semester_display', 'start_date', 'end_date', 'schedule',
                  'lecturer', 'lecturer_name', 'assistant_lecturer', 'assistant_lecturer_name',
                  'teaching_assistants', 'capacity', 'enrolled_count', 'attendance_percentage',
                  'students', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class ClassEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for ClassEnrollment model"""
    student_name = serializers.CharField(source='student.person.full_name', read_only=True)
    student_reg = serializers.CharField(source='student.student_reg_number', read_only=True)
    class_code = serializers.CharField(source='class_obj.class_code', read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ClassEnrollment
        fields = ['id', 'class_obj', 'class_code', 'student', 'student_name',
                  'student_reg', 'enrollment_date', 'drop_date', 'status',
                  'status_display', 'attendance_count', 'total_classes',
                  'attendance_percentage', 'registered_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']