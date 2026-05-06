from django import forms
from django.core.exceptions import ValidationError
from .models import VisitorSession, Visitor, BLETag
from apps.core.models import Staff


class VisitorSessionForm(forms.ModelForm):
    """
    Form for creating visitor session
    """
    session_type = forms.ChoiceField(
        choices=VisitorSession.SessionType.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = VisitorSession
        fields = ['session_type']
    
    def clean_session_type(self):
        session_type = self.cleaned_data.get('session_type')
        return session_type


class VisitorCheckinSessionForm(forms.Form):
    """
    Form for completing visitor check-in
    """
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'visitor@example.com'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+254712345678'
        })
    )
    organization = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Company/Organization'
        })
    )
    purpose = forms.ChoiceField(
        choices=Visitor.VisitPurpose.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    host_person = forms.ModelChoiceField(
        queryset=Staff.objects.select_related('person').filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes'
        })
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.startswith('+'):
            # Auto-format Kenyan numbers
            if phone.startswith('0'):
                phone = '+254' + phone[1:]
        return phone


class VisitorTagAssignForm(forms.Form):
    """
    Form for assigning BLE tag to visitor
    """
    tag_uuid = forms.CharField(
        max_length=36,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tag UUID or scan tag'
        })
    )
    
    def clean_tag_uuid(self):
        tag_uuid = self.cleaned_data.get('tag_uuid')
        try:
            tag = BLETag.objects.get(tag_uuid=tag_uuid, status='available')
        except BLETag.DoesNotExist:
            raise ValidationError('Tag not found or not available')
        return tag_uuid


class VisitorOCRProcessForm(forms.Form):
    """
    Form for OCR processing of ID
    """
    id_image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'capture': 'environment'  # For mobile devices
        })
    )
    id_type = forms.ChoiceField(
        choices=VisitorSession.IdType.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )