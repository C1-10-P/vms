#!/usr/bin/env python
"""
Complete API Testing Script for VMS
Run: python test_api.py
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "user"
PASSWORD = "password"

class VMSTestClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.access_token = None
        self.refresh_token = None
        self.test_results = []
    
    def log(self, endpoint, method, status, message=""):
        icon = "✅" if 200 <= status < 300 else "❌"
        self.test_results.append({
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "success": 200 <= status < 300,
            "message": message
        })
        print(f"{icon} {method} {endpoint} -> {status} {message}")
    
    def login(self):
        """Step 1: Login to get tokens"""
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION TESTS")
        print("="*60)
        
        response = requests.post(
            f"{self.base_url}/auth/login/",
            json={"username": USERNAME, "password": PASSWORD}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access')
            self.refresh_token = data.get('refresh')
            self.log("/auth/login/", "POST", response.status_code, "Login successful")
            return True
        else:
            self.log("/auth/login/", "POST", response.status_code, "Login failed")
            return False
    
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def test_current_user(self):
        """Test getting current user"""
        response = requests.get(
            f"{self.base_url}/auth/me/",
            headers=self.get_headers()
        )
        self.log("/auth/me/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def test_users_list(self):
        """Test listing users"""
        response = requests.get(
            f"{self.base_url}/users/",
            headers=self.get_headers()
        )
        self.log("/users/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_create_attendance(self):
        """Test creating attendance record"""
        # First get a student and class
        students_response = requests.get(
            f"{self.base_url}/attendance/",
            headers=self.get_headers()
        )
        
        if students_response.status_code == 200:
            data = {
                "student_id": "REG001",  # Adjust based on your data
                "class_code": "TIE4101",
                "verification_method": "qr"
            }
            
            response = requests.post(
                f"{self.base_url}/attendance/checkin/",
                json=data,
                headers=self.get_headers()
            )
            self.log("/attendance/checkin/", "POST", response.status_code)
            return response.json() if response.status_code == 200 else None
        return None
    
    def test_attendance_list(self):
        """Test listing attendance records"""
        response = requests.get(
            f"{self.base_url}/attendance/",
            headers=self.get_headers(),
            params={"limit": 10}
        )
        self.log("/attendance/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_attendance_summary(self):
        """Test attendance summary"""
        response = requests.get(
            f"{self.base_url}/attendance/summary/",
            headers=self.get_headers()
        )
        self.log("/attendance/summary/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def test_visitor_checkin(self):
        """Test visitor check-in"""
        data = {
            "first_name": "Test",
            "last_name": "Visitor",
            "phone_number": "+254712345678",
            "national_id": f"TEST{datetime.now().timestamp()}",
            "purpose": "meeting",
            "organization": "Test Company"
        }
        
        response = requests.post(
            f"{self.base_url}/visitors/checkin/",
            json=data,
            headers=self.get_headers()
        )
        self.log("/visitors/checkin/", "POST", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def test_visitor_list(self):
        """Test listing visitors"""
        response = requests.get(
            f"{self.base_url}/visitors/",
            headers=self.get_headers(),
            params={"status": "active"}
        )
        self.log("/visitors/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_visitor_tracking(self):
        """Test visitor tracking"""
        response = requests.get(
            f"{self.base_url}/visitors/tracking/",
            headers=self.get_headers()
        )
        self.log("/visitors/tracking/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_zones_list(self):
        """Test listing access zones"""
        response = requests.get(
            f"{self.base_url}/zones/",
            headers=self.get_headers()
        )
        self.log("/zones/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_zone_occupancy(self):
        """Test zone occupancy"""
        response = requests.get(
            f"{self.base_url}/zones/1/occupancy/",
            headers=self.get_headers()
        )
        self.log("/zones/{id}/occupancy/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def test_devices_list(self):
        """Test listing devices"""
        response = requests.get(
            f"{self.base_url}/devices/",
            headers=self.get_headers()
        )
        self.log("/devices/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_device_health(self):
        """Test device health"""
        response = requests.get(
            f"{self.base_url}/devices/health/",
            headers=self.get_headers()
        )
        self.log("/devices/health/", "GET", response.status_code)
        return response.json() if response.status_code == 200 else []
    
    def test_device_heartbeat(self):
        """Test sending device heartbeat"""
        data = {
            "node_uuid": "test-node-001",
            "status": "online",
            "battery": 85,
            "uptime": 3600
        }
        
        response = requests.post(
            f"{self.base_url}/devices/heartbeat/",
            json=data,
            headers=self.get_headers()
        )
        self.log("/devices/heartbeat/", "POST", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def test_report_generate(self):
        """Test report generation"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        data = {
            "report_type": "attendance",
            "format": "json",
            "start_date": week_ago.isoformat(),
            "end_date": today.isoformat()
        }
        
        response = requests.post(
            f"{self.base_url}/reports/generate/",
            json=data,
            headers=self.get_headers()
        )
        self.log("/reports/generate/", "POST", response.status_code)
        return response.json() if response.status_code == 200 else None
    
    def run_all_tests(self):
        """Run all API tests"""
        if not self.login():
            print("\n❌ Login failed. Cannot proceed with tests.")
            return
        
        print("\n" + "="*60)
        print("👤 USER TESTS")
        print("="*60)
        self.test_current_user()
        self.test_users_list()
        
        print("\n" + "="*60)
        print("📚 ATTENDANCE TESTS")
        print("="*60)
        self.test_attendance_list()
        self.test_attendance_summary()
        self.test_create_attendance()
        
        print("\n" + "="*60)
        print("👋 VISITOR TESTS")
        print("="*60)
        self.test_visitor_list()
        self.test_visitor_checkin()
        self.test_visitor_tracking()
        
        print("\n" + "="*60)
        print("🏢 ACCESS ZONE TESTS")
        print("="*60)
        self.test_zones_list()
        self.test_zone_occupancy()
        
        print("\n" + "="*60)
        print("🔌 DEVICE TESTS")
        print("="*60)
        self.test_devices_list()
        self.test_device_health()
        self.test_device_heartbeat()
        
        print("\n" + "="*60)
        print("📊 REPORT TESTS")
        print("="*60)
        self.test_report_generate()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%\n")
        
        if failed > 0:
            print("Failed endpoints:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  - {r['method']} {r['endpoint']} (Status: {r['status']})")
        
        return self.test_results

if __name__ == "__main__":
    client = VMSTestClient()
    results = client.run_all_tests()