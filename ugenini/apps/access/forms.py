import json
from django import forms
from django.core.exceptions import ValidationError
from apps.access.models.zone import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.geofence import GeofenceBoundary
from apps.core.models import College, School, Department, Program, Person

class AccessZoneForm(forms.ModelForm):
    """Form for Access Zone CRUD operations"""
    
    class Meta:
        model = AccessZone
        fields = ['name', 'code', 'zone_type', 'parent_zone', 'institution', 'college',
                  'school', 'department', 'access_level', 'requires_2fa', 'requires_approval',
                  'building', 'floor', 'room_number', 'capacity', 'open_time', 'close_time',
                  'weekend_access', 'holiday_access', 'description', 'access_instructions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'zone_type': forms.Select(attrs={'class': 'form-control'}),
            'parent_zone': forms.Select(attrs={'class': 'form-control'}),
            'institution': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'access_level': forms.Select(attrs={'class': 'form-control'}),
            'requires_2fa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'weekend_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'holiday_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'access_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            if AccessZone.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A zone with this code already exists.')
        return code


class AccessPermissionForm(forms.ModelForm):
    """Form for Access Permission CRUD operations"""
    
    class Meta:
        model = AccessPermission
        fields = [
            'zone', 'person_type', 'college', 'school', 'department', 'program',
            'year_of_study', 'staff_category', 'specific_person', 'valid_from',
            'valid_to', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'start_time', 'end_time', 'requires_2fa',
            'requires_escort', 'requires_approval', 'priority'
        ]
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'person_type': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'year_of_study': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'staff_category': forms.TextInput(attrs={'class': 'form-control'}),
            'specific_person': forms.Select(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'monday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tuesday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wednesday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'thursday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'friday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'saturday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sunday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'requires_2fa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_escort': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values for days (all checked by default)
        if not self.instance.pk:
            self.fields['monday'].initial = True
            self.fields['tuesday'].initial = True
            self.fields['wednesday'].initial = True
            self.fields['thursday'].initial = True
            self.fields['friday'].initial = True
            self.fields['saturday'].initial = True
            self.fields['sunday'].initial = True
        
        # Add empty labels for optional fields
        self.fields['college'].empty_label = "All Colleges"
        self.fields['school'].empty_label = "All Schools"
        self.fields['department'].empty_label = "All Departments"
        self.fields['program'].empty_label = "All Programs"
        self.fields['specific_person'].empty_label = "None (Apply to all)"
        
        # Make specific fields not required
        self.fields['college'].required = False
        self.fields['school'].required = False
        self.fields['department'].required = False
        self.fields['program'].required = False
        self.fields['year_of_study'].required = False
        self.fields['staff_category'].required = False
        self.fields['specific_person'].required = False
        self.fields['valid_from'].required = False
        self.fields['valid_to'].required = False
        
        # Filter querysets
        self.fields['zone'].queryset = AccessZone.objects.filter(is_active=True)
        self.fields['specific_person'].queryset = Person.objects.filter(is_active=True)
        self.fields['college'].queryset = College.objects.filter(is_active=True)
        self.fields['school'].queryset = School.objects.filter(is_active=True)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['program'].queryset = Program.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate date range
        if valid_from and valid_to and valid_from > valid_to:
            raise ValidationError("Valid To date must be after Valid From date")
        
        # Validate time range
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Start time must be before end time")
        
        return cleaned_data


# Modal Form for Ajax (simpler version for modals)
class AccessPermissionModalForm(forms.ModelForm):
    """Simplified form for modal popup - keeps all fields but with better layout"""
    
    class Meta:
        model = AccessPermission
        fields = [
            'zone', 'person_type', 'college', 'school', 'department', 'program',
            'year_of_study', 'specific_person', 'valid_from', 'valid_to',
            'requires_2fa', 'requires_escort', 'requires_approval', 'priority'
        ]
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'person_type': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'year_of_study': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'specific_person': forms.Select(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'requires_2fa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_escort': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'value': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add empty labels
        self.fields['college'].empty_label = "All Colleges"
        self.fields['school'].empty_label = "All Schools"
        self.fields['department'].empty_label = "All Departments"
        self.fields['program'].empty_label = "All Programs"
        self.fields['specific_person'].empty_label = "None"
        
        # Make optional fields not required
        self.fields['college'].required = False
        self.fields['school'].required = False
        self.fields['department'].required = False
        self.fields['program'].required = False
        self.fields['year_of_study'].required = False
        self.fields['specific_person'].required = False
        self.fields['valid_from'].required = False
        self.fields['valid_to'].required = False
        self.fields['priority'].required = False
        
        # Filter querysets
        self.fields['zone'].queryset = AccessZone.objects.filter(is_active=True)
        self.fields['specific_person'].queryset = Person.objects.filter(is_active=True)
        self.fields['college'].queryset = College.objects.filter(is_active=True)
        self.fields['school'].queryset = School.objects.filter(is_active=True)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['program'].queryset = Program.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if valid_from and valid_to and valid_from > valid_to:
            raise ValidationError("Valid To date must be after Valid From date")
        
        return cleaned_data



class GeofenceForm(forms.ModelForm):
    """Form for Geofence CRUD operations"""
    
    class Meta:
        model = GeofenceBoundary
        fields = ['zone', 'boundary_type', 'coordinates', 'latitude', 'longitude',
                  'radius_meters', 'accuracy_threshold', 'is_active']
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'boundary_type': forms.Select(attrs={'class': 'form-control'}),
            'coordinates': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 
                'placeholder': '[[lat, lng], [lat, lng], ...]'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'radius_meters': forms.NumberInput(attrs={'class': 'form-control'}),
            'accuracy_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields not required initially
        self.fields['accuracy_threshold'].required = False
        self.fields['coordinates'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['radius_meters'].required = False
        
        # Filter zones
        self.fields['zone'].queryset = AccessZone.objects.filter(is_active=True)
        
        # Set initial values
        if not self.instance.pk:
            self.fields['accuracy_threshold'].initial = 10
            self.fields['is_active'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        boundary_type = cleaned_data.get('boundary_type')
        coordinates = cleaned_data.get('coordinates')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        radius_meters = cleaned_data.get('radius_meters')
        
        # Validate based on boundary type
        if boundary_type == 'polygon':
            if not coordinates:
                raise ValidationError("Polygon coordinates are required")
            try:
                coords = json.loads(coordinates)
                if not isinstance(coords, list) or len(coords) < 3:
                    raise ValidationError("Polygon must have at least 3 points")
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for coordinates")
                
        elif boundary_type == 'circle':
            if not latitude or not longitude:
                raise ValidationError("Latitude and longitude are required for circle")
            if not radius_meters:
                raise ValidationError("Radius is required for circle")
                
        elif boundary_type == 'point':
            if not latitude or not longitude:
                raise ValidationError("Latitude and longitude are required for point")
        
        return cleaned_data


class GeofenceModalForm(forms.ModelForm):
    """Simplified form for modal popup"""
    
    class Meta:
        model = GeofenceBoundary
        fields = ['zone', 'boundary_type', 'coordinates', 'latitude', 'longitude',
                  'radius_meters', 'accuracy_threshold', 'is_active']
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'boundary_type': forms.Select(attrs={'class': 'form-control'}),
            'coordinates': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'radius_meters': forms.NumberInput(attrs={'class': 'form-control'}),
            'accuracy_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['accuracy_threshold'].required = False
        self.fields['coordinates'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['radius_meters'].required = False
        self.fields['zone'].queryset = AccessZone.objects.filter(is_active=True)