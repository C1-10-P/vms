from django.core.management.base import BaseCommand
from apps.firmware.camera_service import camera_scanner
import signal
import sys


class Command(BaseCommand):
    help = 'Start continuous QR code scanner for attendance/visitor check-in'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['attendance', 'visitor', 'both'],
            default='attendance',
            help='Scan type: attendance, visitor, or both'
        )
        parser.add_argument(
            '--camera',
            type=int,
            default=0,
            help='Camera device ID (default: 0)'
        )
    
    def handle(self, *args, **options):
        scan_type = options['type']
        camera_id = options['camera']
        
        self.stdout.write(self.style.SUCCESS(f'Starting QR scanner for {scan_type}...'))
        
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('\nShutting down scanner...'))
            camera_scanner.release_camera()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize camera
        if not camera_scanner.initialize_camera(camera_id):
            self.stdout.write(self.style.ERROR('Failed to initialize camera'))
            sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS('Camera ready. Place QR code in front of camera.'))
        self.stdout.write(self.style.WARNING('Press Ctrl+C to stop\n'))
        
        # Run continuous scan
        try:
            while True:
                if scan_type == 'attendance':
                    result = camera_scanner.scan_student_id()
                    if result:
                        self._display_result(result)
                elif scan_type == 'visitor':
                    result = camera_scanner.scan_visitor_qr()
                    if result:
                        self._display_result(result)
                elif scan_type == 'both':
                    # Try attendance first, then visitor
                    result = camera_scanner.scan_student_id()
                    if not result or not result.get('success'):
                        result = camera_scanner.scan_visitor_qr()
                    if result:
                        self._display_result(result)
                
                import time
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nScanner stopped'))
        finally:
            camera_scanner.release_camera()
    
    def _display_result(self, result):
        """Display scan result"""
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(f" {result.get('message', 'Success')}"))
        else:
            self.stdout.write(self.style.ERROR(f" {result.get('error', 'Failed')}"))