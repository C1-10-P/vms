import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.access.models.zone import AccessZone
from .models import (
    Institution, College, School, Department, Program,
    Person, Student, Staff, Visitor,
    AcademicUnit, Class, ClassEnrollment
)


class InstitutionForm(forms.ModelForm):
    """Form for Institution CRUD operations"""
    
    class Meta:
        model = Institution
        fields = ['name', 'code', 'abbreviation', 'address', 'phone', 'email',
                  'website', 'logo', 'established_year', 'motto', 'vision',
                  'mission', 'vice_chancellor', 'registrar']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full institution name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short code (e.g., JKUAT)'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'motto': forms.TextInput(attrs={'class': 'form-control'}),
            'vision': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mission': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vice_chancellor': forms.TextInput(attrs={'class': 'form-control'}),
            'registrar': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper()
            if Institution.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('Institution with this code already exists.')
        return code


class CollegeForm(forms.ModelForm):
    """Form for College CRUD operations"""
    
    class Meta:
        model = College
        fields = ['institution', 'name', 'code', 'abbreviation', 'dean_title', 'dean_name',
                  'office_location', 'contact_phone', 'contact_email', 'building', 'floors',
                  'established_year', 'description']
        widgets = {
            'institution': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
            'dean_title': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', 'Select Title'), ('Prof.', 'Professor'), ('Dr.', 'Doctor'), 
                ('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.')
            ]),
            'dean_name': forms.TextInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floors': forms.NumberInput(attrs={'class': 'form-control'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# class SchoolForm(forms.ModelForm):
#     """Form for School CRUD operations"""
    
#     class Meta:
#         model = School
#         fields = ['college', 'name', 'code', 'abbreviation', 'director_title', 'director_name',
#                   'office_location', 'contact_phone', 'contact_email', 'building', 'floor',
#                   'established_year', 'accreditation_status']
#         widgets = {
#             'college': forms.Select(attrs={'class': 'form-control'}),
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'code': forms.TextInput(attrs={'class': 'form-control'}),
#             'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
#             'director_title': forms.Select(attrs={'class': 'form-control'}, choices=[
#                 ('', 'Select Title'), ('Prof.', 'Professor'), ('Dr.', 'Doctor'),
#                 ('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.')
#             ]),
#             'director_name': forms.TextInput(attrs={'class': 'form-control'}),
#             'office_location': forms.TextInput(attrs={'class': 'form-control'}),
#             'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'building': forms.TextInput(attrs={'class': 'form-control'}),
#             'floor': forms.NumberInput(attrs={'class': 'form-control'}),
#             'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
#             'accreditation_status': forms.Select(attrs={'class': 'form-control'}, choices=[
#                 ('accredited', 'Accredited'), ('provisional', 'Provisional'), ('pending', 'Pending')
#             ]),
           
#         }



class SchoolForm(forms.ModelForm):
    """Form for School CRUD operations"""
    
    class Meta:
        model = School
        fields = ['college', 'name', 'code', 'director_name', 'contact_email', 
                  'contact_phone', 'is_active']
        widgets = {
            'college': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'director_name': forms.Select(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['college'].queryset = College.objects.filter(is_active=True)
        self.fields['college'].empty_label = "Select College"
        self.fields['college'].required = True
        
        # if 'director_name' in self.fields:
        self.fields['director_name'].queryset = Staff.objects.filter(is_active=True)
        self.fields['director_name'].label = "School Director"
        self.fields['direcor_name'].required = False


class SchoolModalForm(forms.ModelForm):
    """Simplified form for modal popup"""
    
    class Meta:
        model = School
        fields = ['college', 'name', 'code', 'director_name', 'contact_email', 
                  'contact_phone', 'is_active']
        widgets = {
            'college': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
           
            'director_name': forms.Select(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['college'].queryset = College.objects.filter(is_active=True)
        self.fields['college'].empty_label = "Select College"
        self.fields['college'].required = True
        self.fields['director_name'].queryset = Staff.objects.filter(is_active=True)
        self.fields['director_name'].label = "School Director"
        self.fields['direcor_name'].required = False

class DepartmentForm(forms.ModelForm):
    """Form for Department CRUD operations"""
    
    class Meta:
        model = Department
        fields = ['school', 'name', 'code', 'abbreviation', 'hod_title', 'hod_name',
                  'office_location', 'contact_phone', 'contact_email', 'building', 'floor',
                  'room_number', 'established_year', 'description']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
            'hod_title': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', 'Select Title'), ('Prof.', 'Professor'), ('Dr.', 'Doctor'),
                ('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.')
            ]),
            'hod_name': forms.TextInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProgramForm(forms.ModelForm):
    """Form for Program CRUD operations"""
    
    class Meta:
        model = Program
        fields = ['department', 'name', 'code', 'level', 'duration_years', 'duration_semesters',
                  'total_credit_hours', 'coordinator_name', 'coordinator_email', 'coordinator_phone',
                  'tuition_fee', 'max_intake', 'description', 'admission_requirements']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('certificate', 'Certificate'), ('diploma', 'Diploma'),
                ('bachelor', 'Bachelor'), ('master', 'Master'),
                ('doctorate', 'Doctorate'), ('postdoc', 'Post-Doctoral')
            ]),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'duration_semesters': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_credit_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'coordinator_name': forms.TextInput(attrs={'class': 'form-control'}),
            'coordinator_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'coordinator_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'tuition_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_intake': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'admission_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PersonForm(forms.ModelForm):
    """Form for Person CRUD operations"""
    
    class Meta:
        model = Person
        fields = ['first_name', 'last_name', 'other_names', 'date_of_birth', 'gender',
                  'phone_number', 'email', 'address', 'national_id', 'passport_number',
                  'person_type', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'other_names': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}, choices=[('', 'Select'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other')]),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control'}),
            'person_type': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('student', 'Student'), ('staff', 'Staff'), ('visitor', 'Visitor'),
                ('contractor', 'Contractor'), ('alumni', 'Alumni')
            ]),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            if Person.objects.filter(national_id=national_id).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A person with this National ID already exists.')
        return national_id
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if Person.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A person with this email already exists.')
        return email


class StudentForm(forms.ModelForm):
    """Form for Student CRUD operations"""
    
    class Meta:
        model = Student
        fields = ['person', 'student_reg_number', 'program', 'current_year', 'current_semester',
                  'admission_date', 'expected_graduation', 'mode_of_study', 'status',
                  'supervisor', 'class_representative', 'has_disability', 'disability_description']
        widgets = {
            'person': forms.Select(attrs={'class': 'form-control'}),
            'student_reg_number': forms.TextInput(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'current_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'current_semester': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 3}),
            'admission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_graduation': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mode_of_study': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('full_time', 'Full Time'), ('part_time', 'Part Time'),
                ('distance', 'Distance Learning'), ('evening', 'Evening'), ('online', 'Online')
            ]),
            'status': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('active', 'Active'), ('probation', 'Probation'), ('suspended', 'Suspended'),
                ('graduated', 'Graduated'), ('withdrawn', 'Withdrawn'), ('deferred', 'Deferred')
            ]),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'class_representative': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_disability': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'disability_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_student_reg_number(self):
        reg_number = self.cleaned_data.get('student_reg_number')
        if reg_number:
            if Student.objects.filter(student_reg_number=reg_number).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A student with this registration number already exists.')
        return reg_number


class StaffForm(forms.ModelForm):
    """Form for Staff CRUD operations"""
    
    class Meta:
        model = Staff
        fields = ['person', 'staff_number', 'department', 'job_title', 'staff_category',
                  'employment_type', 'designation', 'office_location', 'office_phone',
                  'office_hours', 'joined_date', 'contract_end_date', 'is_hod', 'is_dean']
        widgets = {
            'person': forms.Select(attrs={'class': 'form-control'}),
            'staff_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_category': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('academic', 'Academic'), ('administrative', 'Administrative'),
                ('technical', 'Technical'), ('support', 'Support'), ('security', 'Security')
            ]),
            'employment_type': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('full_time', 'Full Time'), ('part_time', 'Part Time'),
                ('contract', 'Contract'), ('visiting', 'Visiting'), ('emeritus', 'Emeritus')
            ]),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
            'office_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'office_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'joined_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_hod': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_dean': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_staff_number(self):
        staff_number = self.cleaned_data.get('staff_number')
        if staff_number:
            if Staff.objects.filter(staff_number=staff_number).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A staff member with this number already exists.')
        return staff_number


class AcademicUnitForm(forms.ModelForm):
    """Form for Academic Unit CRUD operations"""
    
    class Meta:
        model = AcademicUnit
        fields = ['department', 'code', 'name', 'credit_hours', 'lecture_hours', 'lab_hours',
                  'tutorial_hours', 'level', 'semester_offered', 'is_elective', 'is_required',
                  'is_lab_course', 'prerequisites', 'description', 'learning_outcomes']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'lecture_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'lab_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'tutorial_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'level': forms.NumberInput(attrs={'class': 'form-control'}),
            'semester_offered': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('1', 'Semester 1'), ('2', 'Semester 2'), ('3', 'Semester 3')
            ]),
            'is_elective': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_lab_course': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prerequisites': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'learning_outcomes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            if AcademicUnit.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('An academic unit with this code already exists.')
        return code


class ClassForm(forms.ModelForm):
    """Form for Class CRUD operations"""
    
    class Meta:
        model = Class
        fields = ['academic_unit', 'program', 'class_code', 'class_group', 'academic_year',
                  'semester', 'start_date', 'end_date', 'schedule', 'lecturer',
                  'assistant_lecturer', 'teaching_assistants', 'capacity', 'students']
        widgets = {
            'academic_unit': forms.Select(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'class_code': forms.TextInput(attrs={'class': 'form-control'}),
            'class_group': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2024/2025'}),
            'semester': forms.Select(attrs={'class': 'form-control'}, choices=[(1, 'Semester 1'), (2, 'Semester 2'), (3, 'Semester 3')]),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'schedule': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 
                'placeholder': '{"monday": {"start": "08:00", "end": "10:00", "room": "Lab 1"}}'}),
            'lecturer': forms.Select(attrs={'class': 'form-control'}),
            'assistant_lecturer': forms.Select(attrs={'class': 'form-control'}),
            'teaching_assistants': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'students': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
    
    def clean_class_code(self):
        class_code = self.cleaned_data.get('class_code')
        if class_code:
            if Class.objects.filter(class_code=class_code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A class with this code already exists.')
        return class_code
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data


# ============ Visitor Form (for manual entry) ============

class VisitorManualForm(forms.ModelForm):
    """
    Form for manual visitor check-in (for security desk)
    """
    
    class Meta:
        model = Visitor
        fields = ['person','host_person',
                  'host_department', 'id_type', 'id_number', 'organization',
                  'vehicle_registration', 'vehicle_make']
        widgets = {
            'person': forms.Select(attrs={'class': 'form-control'}),
            'purpose': forms.Select(attrs={'class': 'form-control'}),
            'purpose_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'host_person': forms.Select(attrs={'class': 'form-control'}),
            'host_department': forms.Select(attrs={'class': 'form-control'}),
            'id_type': forms.Select(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_make': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_model': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit person selection to non-staff/non-student
        self.fields['person'].queryset = Person.objects.filter(
            person_type='visitor',
            is_active=True
        )
        self.fields['host_person'].queryset = Person.objects.filter(
            person_type='staff',
            is_active=True
        )


class VisitorQuickCheckinForm(forms.Form):
    """
    Quick check-in form for visitors (no pre-registration)
    """
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    national_id = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    organization = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # purpose = forms.ChoiceField(choices=Visitor.VisitPurpose.choices, widget=forms.Select(attrs={'class': 'form-control'}))
    host_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of person being visited'}))
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            # Check if visitor already exists
            existing = Person.objects.filter(national_id=national_id).first()
            if existing and existing.person_type != 'visitor':
                raise ValidationError('This ID belongs to a registered student/staff member.')
        return national_id


# ============ Classroom/Class Forms ============

class ClassroomForm(forms.ModelForm):
    """
    Form for classroom/room management
    """
    
    class Meta:
        model = AccessZone
        fields = ['name', 'code', 'building', 'floor', 'room_number', 'capacity',
                  'zone_type', 'institution', 'college', 'school', 'department',
                  'access_level', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'zone_type': forms.Select(attrs={'class': 'form-control'}),
            'institution': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'access_level': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['zone_type'].initial = 'classroom'
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            if AccessZone.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A classroom with this code already exists.')
        return code


class ClassScheduleForm(forms.ModelForm):
    """
    Form for class schedule management
    """
    
    class Meta:
        model = Class
        fields = ['academic_unit', 'program', 'class_code', 'class_group', 
                  'academic_year', 'semester', 'start_date', 'end_date', 
                  'schedule', 'lecturer', 'assistant_lecturer', 'capacity']
        widgets = {
            'academic_unit': forms.Select(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'class_code': forms.TextInput(attrs={'class': 'form-control'}),
            'class_group': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2024/2025'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'schedule': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 
                'placeholder': json.dumps({
                    "monday": {"start": "08:00", "end": "10:00", "room": "Lab 1"},
                    "wednesday": {"start": "14:00", "end": "16:00", "room": "Lecture Hall A"}
                }, indent=2)}),
            'lecturer': forms.Select(attrs={'class': 'form-control'}),
            'assistant_lecturer': forms.Select(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError('End date must be after start date.')
        
        # Validate schedule JSON format
        schedule = cleaned_data.get('schedule')
        if schedule:
            try:
                if isinstance(schedule, str):
                    schedule = json.loads(schedule)
                # Basic validation
                for day, times in schedule.items():
                    if 'start' not in times or 'end' not in times:
                        raise ValidationError(f'Missing start/end time for {day}')
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format for schedule')
        
        return cleaned_data


class RoomBookingForm(forms.Form):
    """
    Form for booking a classroom/room
    """
    room_id = forms.ModelChoiceField(
        queryset=AccessZone.objects.filter(zone_type='classroom', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    booking_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))
    purpose = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    attendees = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError('End time must be after start time.')
        
        # Check for booking conflicts
        room = cleaned_data.get('room_id')
        booking_date = cleaned_data.get('booking_date')
        
        if room and booking_date:
            # This would check existing bookings (requires a Booking model)
            pass
        
        return cleaned_data