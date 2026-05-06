from django.core.management.base import BaseCommand
from apps.firmware.mqtt_client import mqtt_client
import time
import signal
import sys


class Command(BaseCommand):
    help = 'Start MQTT client for device communication'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MQTT Client...'))
        
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('Shutting down MQTT Client...'))
            mqtt_client.disconnect()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Connect MQTT client
        if mqtt_client.connect():
            self.stdout.write(self.style.SUCCESS('MQTT Client connected successfully'))
        else:
            self.stdout.write(self.style.ERROR('MQTT Client connection failed'))
            sys.exit(1)
        
        # Keep running
        if options['daemon']:
            while True:
                time.sleep(1)
        else:
            self.stdout.write(self.style.WARNING('Press Ctrl+C to stop'))
            while True:
                time.sleep(1)