from django.core.management.base import BaseCommand
from django.db import transaction
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../scripts'))

try:
    from seed_database import DatabaseSeeder, DatabaseCleaner
except ImportError:
    print("Error: Could not import seed_database module. Make sure scripts/seed_database.py exists.")
    sys.exit(1)


class Command(BaseCommand):
    help = 'Seed the database with test data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['seed', 'clean', 'reset'],
            default='seed',
            help='Action to perform: seed, clean, or reset'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(self.style.SUCCESS(f'Starting database {action}...'))
        
        try:
            if action == 'seed':
                DatabaseSeeder.run_all()
            elif action == 'clean':
                DatabaseCleaner.clean_all()
            elif action == 'reset':
                DatabaseCleaner.clean_all()
                DatabaseSeeder.run_all()
            
            self.stdout.write(self.style.SUCCESS(f'Database {action} completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during {action}: {str(e)}'))
            raise