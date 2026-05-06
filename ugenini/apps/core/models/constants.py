"""
Global constants and choice tuples for the VMS system.
"""

# Person constants
GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

PERSON_TYPE_CHOICES = [
    ('student', 'Student'),
    ('staff', 'Staff'),
    ('visitor', 'Visitor'),
    ('contractor', 'Contractor'),
    ('alumni', 'Alumni'),
]

# Academic constants
PROGRAM_LEVEL_CHOICES = [
    ('certificate', 'Certificate'),
    ('diploma', 'Diploma'),
    ('bachelor', 'Bachelor'),
    ('master', 'Master'),
    ('doctorate', 'Doctorate'),
    ('postdoc', 'Post-Doctoral'),
]

STUDENT_STATUS_CHOICES = [
    ('active', 'Active'),
    ('probation', 'Probation'),
    ('suspended', 'Suspended'),
    ('graduated', 'Graduated'),
    ('withdrawn', 'Withdrawn'),
    ('deferred', 'Deferred'),
]

STAFF_CATEGORY_CHOICES = [
    ('academic', 'Academic'),
    ('administrative', 'Administrative'),
    ('technical', 'Technical'),
    ('support', 'Support'),
    ('security', 'Security'),
]

EMPLOYMENT_TYPE_CHOICES = [
    ('full_time', 'Full Time'),
    ('part_time', 'Part Time'),
    ('contract', 'Contract'),
    ('visiting', 'Visiting'),
    ('emeritus', 'Emeritus'),
]

# Attendance constants
ATTENDANCE_STATUS_CHOICES = [
    ('present', 'Present'),
    ('absent', 'Absent'),
    ('late', 'Late'),
    ('excused', 'Excused'),
    ('holiday', 'Holiday'),
]

VERIFICATION_METHOD_CHOICES = [
    ('rfid', 'RFID Card'),
    # ('face', 'Face Recognition'),
    ('bar_code', 'Bar Code'),
    ('qr', 'QR Code'),
    ('manual', 'Manual Entry'),
    ('ble', 'BLE Tag'),
    ('nfc', 'NFC'),
]

# Access control constants
ZONE_TYPE_CHOICES = [
    ('campus', 'Campus'),
    ('building', 'Building'),
    ('floor', 'Floor'),
    ('lab', 'Laboratory'),
    ('office', 'Office'),
    ('classroom', 'Classroom'),
    ('library', 'Library'),
    ('hospital', 'Hospital'),
    ('restricted', 'Restricted Area'),
    ('research', 'Research Facility'),
]

ACCESS_LEVEL_CHOICES = [
    (1, 'Public'),
    (2, 'Staff Only'),
    (3, 'Restricted'),
    (4, 'Research'),
    (5, 'Authorized Personnel Only'),
]

# Device constants
NODE_TYPE_CHOICES = [
    ('gateway', 'Gateway'),
    ('camera', 'Camera Node'),
    ('ble_scanner', 'BLE Scanner'),
    ('rfid_reader', 'RFID Reader'),
    ('access_point', 'Access Point'),
]

NODE_STATUS_CHOICES = [
    ('online', 'Online'),
    ('offline', 'Offline'),
    ('maintenance', 'Maintenance'),
    ('error', 'Error'),
]

# Visitor constants
VISITOR_ID_TYPE_CHOICES = [
    ('national_id', 'National ID'),
    ('passport', 'Passport'),
    ('drivers_license', "Driver's License"),
    ('alien_id', 'Alien ID'),
]

# Notification constants
NOTIFICATION_TYPE_CHOICES = [
    ('sms', 'SMS'),
    ('email', 'Email'),
    ('push', 'Push Notification'),
    ('ussd', 'USSD'),
]

NOTIFICATION_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('normal', 'Normal'),
    ('high', 'High'),
    ('urgent', 'Urgent'),
]

# Report constants
REPORT_FORMAT_CHOICES = [
    ('pdf', 'PDF'),
    ('excel', 'Excel'),
    ('csv', 'CSV'),
    ('json', 'JSON'),
]

REPORT_TYPE_CHOICES = [
    ('attendance', 'Attendance Report'),
    ('visitor', 'Visitor Report'),
    ('access', 'Access Log Report'),
    ('security', 'Security Report'),
    ('summary', 'Daily Summary'),
]

STATUS_CHOICES = [
    ('active', 'Active'),
    ('inactive', 'Inactive'),
]