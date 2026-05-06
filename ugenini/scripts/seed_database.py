#!/usr/bin/env python
# scripts/seed_database.py - FIXED VERSION

import os
import sys
import django
from django.db import transaction
from django.core.management import call_command
from apps.users.seed import UserPermissionSeeder


# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ugenini.settings')
django.setup()

from apps.core.seed import CoreDataSeeder, PersonDataSeeder, AcademicDataSeeder
from apps.vms.seed import VisitorDataSeeder
from apps.access.seed import AccessDataSeeder
from apps.firmware.seed import DeviceDataSeeder


class DatabaseSeeder:
    """Main seeder orchestrator - FIXED VERSION"""
    
    @staticmethod
    def run_all():
        print("\n" + "="*60)
        print("VMS DATABASE SEEDER (IDEMPOTENT VERSION)")
        print("="*60 + "\n")

        # -------------------------
        # STEP 1: CORE STRUCTURE
        # -------------------------
        print("📚 STEP 1: Core Structure")

        institutions = CoreDataSeeder.seed_institutions()
        if not institutions:
            raise Exception("No institutions created")

        institution = institutions[0]

        colleges = CoreDataSeeder.seed_colleges(institution)

        schools = []
        departments = []
        programs = []

        for col in colleges:
            s = CoreDataSeeder.seed_schools(col)
            schools.extend(s)

            for sch in s:
                d = CoreDataSeeder.seed_departments(sch)
                departments.extend(d)

                for dep in d:
                    programs.extend(CoreDataSeeder.seed_programs(dep))

        # -------------------------
        # STEP 2: ACADEMIC
        # -------------------------
        print("\n🏢 STEP 2: Academic")

        AcademicDataSeeder.seed_academic_units(count=30)
        classes = AcademicDataSeeder.seed_classes(count=20)

        # -------------------------
        # STEP 3: PEOPLE
        # -------------------------
        print("\n👥 STEP 3: People")

        staff = PersonDataSeeder.seed_staff(count=20)
        students = PersonDataSeeder.seed_students(count=50)
        visitors = PersonDataSeeder.seed_visitors(count=15)

        # -------------------------
        # STEP 4: DEVICES + ZONES
        # -------------------------
        print("\n🖥️ STEP 4: Devices & Zones")

        nodes = DeviceDataSeeder.seed_edge_nodes(institution, count=8)
        DeviceDataSeeder.seed_node_heartbeats(nodes, heartbeats_per_node=20)

        zones = AccessDataSeeder.seed_access_zones(institution, count=10)

        # -------------------------
        # STEP 5: TAGS
        # -------------------------
        print("\n🏷️ STEP 5: Tags")

        tags = VisitorDataSeeder.seed_ble_tags(count=10)

        # -------------------------
        # STEP 6: VISITS (LAST DEPENDENCY SAFE)
        # -------------------------
        print("\n📝 STEP 6: Visitor Visits")

        if visitors and staff and nodes:
            visits = VisitorDataSeeder.seed_visitor_visits(
                visitors=visitors,
                staff_list=staff,
                node_list=nodes,
                tags_list=tags,
                count_per_visitor=2
            )

            VisitorDataSeeder.seed_visitor_movements(visits, movements_per_visit=5)

        # -------------------------
        # STEP 7: ENROLLMENTS
        # -------------------------
        print("\n🎓 STEP 7: Enrollments")

        if classes and students:
            AcademicDataSeeder.seed_enrollments(students_per_class=12)

        # -------------------------
        # STEP 8: USERS & PERMISSIONS
        # -------------------------
        print("\n👤 STEP 8: Users & Permissions")

        UserPermissionSeeder.seed_all()

        # -------------------------
        # FINAL STATS
        # -------------------------
        print("\n" + "="*60)
        print("SEEDING COMPLETE")
        print("="*60)

        from apps.core.models import Class, ClassEnrollment, Student, Staff, Program, AcademicUnit

        print(f"\n📊 Final Counts:")
        print(f"Classes: {Class.objects.count()}")
        print(f"Enrollments: {ClassEnrollment.objects.count()}")
        print(f"Students: {Student.objects.count()}")
        print(f"Staff: {Staff.objects.count()}")
        print(f"Programs: {Program.objects.count()}")
        print(f"Academic Units: {AcademicUnit.objects.count()}")

        print("\n✅ DONE (IDEMPOTENT + FK SAFE)")

class DatabaseCleaner:
    """Clean all database tables"""
    
    @staticmethod
    def clean_all():
        """Delete all data from all tables"""
        print("\n" + "="*60)
        print("CLEANING DATABASE")
        print("="*60 + "\n")
        
        # Disable foreign key checks for SQLite
        from django.db import connection
        if 'sqlite' in connection.settings_dict['ENGINE']:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Order matters - child tables first
        models_to_clean = [
            'ClassEnrollment', 'ClassAttendance', 'DailyAttendanceSummary',
            'VisitorMovement', 'VisitorAlert', 'VisitorVisit', 'BlacklistedVisitor',
            'TagAssignment', 'BLETag', 'AccessLog', 'TwoFactorSession',
            'AccessPermission', 'GeofenceBoundary', 'NodeHeartbeat', 'OTASession',
            'NodeConfiguration', 'NodeHealth', 'EdgeNode', 'FirmwareVersion',
            'Class', 'AcademicUnit', 'Student', 'Staff', 'Visitor', 'Program',
            'Department', 'School', 'College', 'Person', 'Institution'
        ]
        
        from django.apps import apps
        for model_name in models_to_clean:
            try:
                model = apps.get_model('core', model_name)
                if model:
                    count, _ = model.objects.all().delete()
                    if count > 0:
                        print(f"  ✓ Deleted {count} records from {model_name}")
            except LookupError:
                # Try other apps
                for app in ['attendance', 'visitors', 'access', 'devices']:
                    try:
                        model = apps.get_model(app, model_name)
                        if model:
                            count, _ = model.objects.all().delete()
                            if count > 0:
                                print(f"  ✓ Deleted {count} records from {model_name}")
                            break
                    except LookupError:
                        continue
        
        # Re-enable foreign key checks
        if 'sqlite' in connection.settings_dict['ENGINE']:
            cursor.execute("PRAGMA foreign_keys = ON")
        
        print("\n✅ Database cleaning complete!\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed or clean VMS database')
    parser.add_argument('action', choices=['seed', 'clean', 'reset'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'seed':
        DatabaseSeeder.run_all()
    elif args.action == 'clean':
        DatabaseCleaner.clean_all()
    elif args.action == 'reset':
        DatabaseCleaner.clean_all()
        DatabaseSeeder.run_all()