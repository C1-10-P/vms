"""
Configuration for different ID types and their extraction patterns
"""

ID_PATTERNS = {
    'student_kenyan_university': {
        'name': 'Kenyan University Student ID',
        'fields': {
            'registration_number': {
                'pattern': r'([A-Z]{3,4}\d{3}-\d{4}/\d{4})',
                'required': True,
                'description': 'Student registration number (e.g., ENE221-0108/2018)'
            },
            'full_name': {
                'pattern': r'(?:Name|Student Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                'required': True,
                'description': 'Student full name'
            },
            'program': {
                'pattern': r'(?:Program|Course)[:\s]+([A-Z][a-zA-Z\s]+)',
                'required': False,
                'description': 'Program of study'
            },
            'year': {
                'pattern': r'(?:Year)[:\s]+(\d+)',
                'required': False,
                'description': 'Year of study'
            },
            'institution': {
                'pattern': r'(?:University|Institution)[:\s]+([A-Z][a-zA-Z\s]+University)',
                'required': False,
                'description': 'Institution name'
            }
        }
    },
    
    'national_id_kenyan': {
        'name': 'Kenyan National ID Card',
        'fields': {
            'id_number': {
                'pattern': r'(?:ID|ID Number|National ID)[:\s]+(\d{8})',
                'required': True,
                'description': 'National ID number (8 digits)'
            },
            'full_name': {
                'pattern': r'(?:Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                'required': True,
                'description': 'Full name as on ID'
            },
            'date_of_birth': {
                'pattern': r'(?:DOB|Date of Birth)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                'required': False,
                'description': 'Date of birth'
            }
        }
    },
    
    'visitor_badge': {
        'name': 'Visitor Badge/Tag',
        'fields': {
            'tag_uuid': {
                'pattern': r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
                'required': True,
                'description': 'BLE Tag UUID'
            },
            'visitor_name': {
                'pattern': r'(?:Visitor|Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                'required': False,
                'description': 'Visitor name'
            }
        }
    }
}


def get_id_pattern(id_type):
    """Get pattern configuration for ID type"""
    return ID_PATTERNS.get(id_type, None)


def get_all_id_types():
    """Get all supported ID types"""
    return list(ID_PATTERNS.keys())