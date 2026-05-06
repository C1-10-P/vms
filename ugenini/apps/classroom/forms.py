from django import forms
from django.core.exceptions import ValidationError
from .models import AttendanceSession
from apps.core.models import Student, Class
from .models import AttendanceSession

class AttendanceSessionForm(forms.ModelForm):
    """
    Form for creating attendance session
    """
    student_reg_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter student registration number'
        })
    )
    class_code = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter class code'
        })
    )
    scan_method = forms.ChoiceField(
        choices=AttendanceSession.ScanMethod.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = AttendanceSession
        fields = ['student_reg_number', 'class_code', 'scan_method']
    
    def clean_student_reg_number(self):
        reg = self.cleaned_data.get('student_reg_number')
        if reg:
            # Optional: validate against existing students
            student = Student.objects.filter(student_reg_number=reg, is_active=True).first()
            if not student:
                # Don't fail, just warn - will be validated later
                pass
        return reg
    
    def clean_class_code(self):
        code = self.cleaned_data.get('class_code')
        if code:
            class_obj = Class.objects.filter(class_code=code, is_active=True).first()
            if not class_obj:
                # Don't fail, just warn
                pass
        return code


class AttendanceSessionValidateForm(forms.ModelForm):
    """
    Form for validating attendance session
    """
    confirm_validation = forms.BooleanField(
        required=True,
        label="Confirm this attendance is valid",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about this validation'
        })
    )
    
    def clean_confirm_validation(self):
        confirmed = self.cleaned_data.get('confirm_validation')
        if not confirmed:
            raise forms.ValidationError('You must confirm the validation to proceed.')
        return confirmed

    # --- ADD THIS FIX BELOW ---
    class Meta:
        model = AttendanceSession  # Tells Django which model this form is for
        fields = []                # We are using custom fields above, so this can be empty