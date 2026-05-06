import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count
from faker import Faker

fake = Faker()

from .models import ClassAttendance, DailyAttendanceSummary
from apps.core.models import Student, Class


class AttendanceDataSeeder:
    """Seed data for attendance records"""
    
    @staticmethod
    def seed_attendance_records(days_back=30, records_per_day=100):
        """Create attendance records for past days"""
        records = []
        students = list(Student.objects.filter(is_active=True))
        classes = list(Class.objects.filter(is_active=True))
        
        if not students or not classes:
            print("⚠ Missing students or classes for attendance")
            return []
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Create records for this day
            day_records = min(records_per_day, len(students))
            selected_students = random.sample(students, day_records)
            
            for student in selected_students:
                # Find classes for this student's program
                student_classes = [c for c in classes if c.program == student.program]
                if not student_classes:
                    continue
                
                class_obj = random.choice(student_classes)
                
                # Random time between 8 AM and 5 PM
                hour = random.randint(8, 17)
                minute = random.randint(0, 59)
                scan_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                scan_time = timezone.make_aware(scan_time)
                
                # Random verification status
                status = random.choices(
                    ['success', 'success', 'success', 'failed', 'late'],
                    weights=[70, 20, 5, 3, 2]
                )[0]
                
                method = random.choices(
                    ['qr', 'face', 'rfid', 'manual'],
                    weights=[60, 25, 10, 5]
                )[0]
                
                record, created = ClassAttendance.objects.get_or_create(
                    student=student,
                    class_obj=class_obj,
                    scan_time__date=current_date,
                    defaults={
                        'scan_time': scan_time,
                        'verification_method': method,
                        'verification_status': status,
                        'confidence_score': random.randint(85, 100) if status == 'success' else random.randint(50, 84),
                        'latitude': -1.2921 + random.uniform(-0.01, 0.01),
                        'longitude': 36.8219 + random.uniform(-0.01, 0.01),
                        'ip_address': f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                    }
                )
                records.append(record)
            
            print(f"  ✓ {current_date}: {len(day_records)} attendance records")
            current_date += timedelta(days=1)
        
        print(f"✓ Created {len(records)} attendance records")
        
        # Update daily summaries
        AttendanceDataSeeder.update_daily_summaries()
        
        return records
    
    @staticmethod
    def update_daily_summaries():
        """Update daily attendance summaries"""
        from django.db.models import Count, Q
        
        classes = Class.objects.filter(is_active=True)
        dates = ClassAttendance.objects.dates('scan_time', 'day')
        
        for class_obj in classes:
            for date in dates:
                attendance_count = ClassAttendance.objects.filter(
                    class_obj=class_obj,
                    scan_time__date=date,
                    verification_status='success'
                ).count()
                
                total_students = class_obj.enrollments.filter(status='registered').count()
                
                summary, created = DailyAttendanceSummary.objects.update_or_create(
                    class_obj=class_obj,
                    summary_date=date,
                    defaults={
                        'total_students': total_students,
                        'present_count': attendance_count,
                        'absent_count': total_students - attendance_count,
                        'attendance_percentage': (attendance_count / total_students * 100) if total_students > 0 else 0
                    }
                )
        
        print(f"✓ Updated daily attendance summaries")
    
    @staticmethod
    def seed_verification_logs(count=200):
        """Create verification logs for auditing"""
        logs = []
        attendances = list(ClassAttendance.objects.all())
        
        if not attendances:
            print("⚠ No attendance records for verification logs")
            return []
        
        for _ in range(min(count, len(attendances))):
            attendance = random.choice(attendances)
            
            from apps.classroom.models import VerificationLog
            
            log, created = VerificationLog.objects.get_or_create(
                attendance=attendance,
                defaults={
                    'student': attendance.student,
                    'event_type': random.choice(['attempt', 'success', 'failure']),
                    'method': attendance.verification_method,
                    'success': attendance.verification_status == 'success',
                    'failure_reason': None if attendance.verification_status == 'success' else 'Verification failed',
                    'processing_time_ms': random.randint(50, 500)
                }
            )
            logs.append(log)
        
        print(f"✓ Created {len(logs)} verification logs")
        return logs