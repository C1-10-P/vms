from django import forms
from django.core.exceptions import ValidationError
from .models import EdgeNode, NodeConfiguration, FirmwareVersion


class EdgeNodeForm(forms.ModelForm):
    """Form for Edge Node CRUD operations"""
    
    class Meta:
        model = EdgeNode
        fields = ['node_uuid', 'node_type', 'name', 'model', 'hardware_version',
                  'firmware_version', 'serial_number', 'mac_address', 'ip_address',
                  'institution', 'college', 'school', 'department', 'zone',
                  'location_description', 'latitude', 'longitude', 'power_source',
                  'has_camera', 'has_ble', 'has_rfid', 'has_pir']
        widgets = {
            'node_uuid': forms.TextInput(attrs={'class': 'form-control'}),
            'node_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'hardware_version': forms.TextInput(attrs={'class': 'form-control'}),
            'firmware_version': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'institution': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'location_description': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'power_source': forms.Select(attrs={'class': 'form-control'}),
            'has_camera': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_ble': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_rfid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_pir': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_mac_address(self):
        mac = self.cleaned_data.get('mac_address')
        if mac:
            if EdgeNode.objects.filter(mac_address=mac).exclude(pk=self.instance.pk).exists():
                raise ValidationError('A device with this MAC address already exists.')
        return mac


class NodeConfigurationForm(forms.ModelForm):
    """Form for Node Configuration"""
    
    class Meta:
        model = NodeConfiguration
        fields = ['version', 'scan_interval_seconds', 'ble_scan_duration',
                  'ble_scan_window', 'ble_scan_interval', 'camera_resolution',
                  'camera_quality', 'camera_framesize', 'mqtt_qos', 'mqtt_retain',
                  'mqtt_keepalive', 'tls_enabled', 'deep_sleep_enabled',
                  'deep_sleep_duration', 'log_level', 'custom_settings']
        widgets = {
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'scan_interval_seconds': forms.NumberInput(attrs={'class': 'form-control'}),
            'ble_scan_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'ble_scan_window': forms.NumberInput(attrs={'class': 'form-control'}),
            'ble_scan_interval': forms.NumberInput(attrs={'class': 'form-control'}),
            'camera_resolution': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('QVGA', 'QVGA'), ('VGA', 'VGA'), ('SVGA', 'SVGA'), ('XGA', 'XGA')
            ]),
            'camera_quality': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 63}),
            'camera_framesize': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('FRAMESIZE_QVGA', 'QVGA'), ('FRAMESIZE_VGA', 'VGA'), ('FRAMESIZE_SVGA', 'SVGA')
            ]),
            'mqtt_qos': forms.Select(attrs={'class': 'form-control'}, choices=[(0, '0'), (1, '1'), (2, '2')]),
            'mqtt_retain': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mqtt_keepalive': forms.NumberInput(attrs={'class': 'form-control'}),
            'tls_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deep_sleep_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deep_sleep_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'log_level': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('debug', 'DEBUG'), ('info', 'INFO'), ('warn', 'WARN'), ('error', 'ERROR')
            ]),
            'custom_settings': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 
                'placeholder': '{"key": "value"}'}),
        }


class FirmwareUploadForm(forms.ModelForm):
    """Form for Firmware Upload"""
    
    class Meta:
        model = FirmwareVersion
        fields = ['version', 'node_type', 'firmware_file', 'stability', 'changelog',
                  'min_hardware_version', 'required_config_version', 'rollout_percentage']
        widgets = {
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'node_type': forms.Select(attrs={'class': 'form-control'}),
            'firmware_file': forms.FileInput(attrs={'class': 'form-control'}),
            'stability': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('stable', 'Stable'), ('beta', 'Beta'), ('alpha', 'Alpha')
            ]),
            'changelog': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'min_hardware_version': forms.TextInput(attrs={'class': 'form-control'}),
            'required_config_version': forms.TextInput(attrs={'class': 'form-control'}),
            'rollout_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }
    
    def clean_version(self):
        version = self.cleaned_data.get('version')
        if version:
            if FirmwareVersion.objects.filter(version=version).exists():
                raise ValidationError('A firmware with this version already exists.')
        return version