#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for enhanced API validation and error handling

This script tests the improved JSON format standardization and error handling
in the BACmon API to ensure all validation functions work correctly.
"""

import sys
import requests
import json
from typing import Dict, List, Any, Optional, Tuple
import time

# Test configuration
BASE_URL = 'http://localhost:8080'
API_KEY = 'test_key_123'  # Test API key
HEADERS = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}

class APIValidationTester:
    """Test class for API validation and error handling."""
    
    def __init__(self, base_url: str, headers: Dict[str, str]):
        self.base_url = base_url
        self.headers = headers
        self.test_results = []
    
    def test_endpoint(self, endpoint: str, params: Dict[str, str] = None, 
                     expected_status: int = 200, expected_error_code: Optional[int] = None,
                     test_name: str = "") -> bool:
        """Test an API endpoint with given parameters."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"❌ {test_name}: Invalid JSON response")
                self.test_results.append((test_name, False, "Invalid JSON"))
                return False
            
            # Check response format
            required_fields = ['status', 'timestamp', 'version', 'code']
            for field in required_fields:
                if field not in data:
                    print(f"❌ {test_name}: Missing required field '{field}'")
                    self.test_results.append((test_name, False, f"Missing {field}"))
                    return False
            
            # Check status code
            if response.status_code != expected_status:
                print(f"❌ {test_name}: Expected status {expected_status}, got {response.status_code}")
                self.test_results.append((test_name, False, f"Wrong status {response.status_code}"))
                return False
            
            # Check error code if expected
            if expected_error_code is not None:
                if 'error_code' not in data:
                    print(f"❌ {test_name}: Expected error_code {expected_error_code}, but none found")
                    self.test_results.append((test_name, False, "Missing error_code"))
                    return False
                elif data['error_code'] != expected_error_code:
                    print(f"❌ {test_name}: Expected error_code {expected_error_code}, got {data['error_code']}")
                    self.test_results.append((test_name, False, f"Wrong error_code {data['error_code']}"))
                    return False
            
            # Success
            print(f"✅ {test_name}: PASSED")
            self.test_results.append((test_name, True, "OK"))
            return True
            
        except requests.RequestException as e:
            print(f"❌ {test_name}: Request failed - {e}")
            self.test_results.append((test_name, False, f"Request error: {e}"))
            return False
    
    def run_validation_tests(self) -> bool:
        """Run comprehensive validation tests."""
        print("🧪 Starting API Validation Tests\n")
        
        all_passed = True
        
        # Test 1: Valid API calls should work
        print("📋 Testing Valid API Calls:")
        valid_tests = [
            ("/api/alerts", {}, 200, None, "Valid alerts request"),
            ("/api/alerts", {"min_level": "warning"}, 200, None, "Valid alerts with min_level"),
            ("/api/extended_metrics", {"key": "test"}, 200, None, "Valid extended metrics"),
            ("/api/status", {}, 200, None, "Valid status request"),
        ]
        
        for endpoint, params, expected_status, error_code, test_name in valid_tests:
            if not self.test_endpoint(endpoint, params, expected_status, error_code, test_name):
                all_passed = False
        
        print()
        
        # Test 2: Parameter validation
        print("🔍 Testing Parameter Validation:")
        param_tests = [
            # Invalid parameters
            ("/api/alerts", {"invalid_param": "test"}, 400, 4001, "Invalid parameter name"),
            ("/api/extended_metrics", {"invalid": "test"}, 400, 4001, "Invalid parameter in metrics"),
            
            # Missing required parameters
            ("/api/extended_metrics", {}, 400, 4002, "Missing required key parameter"),
            
            # Invalid values
            ("/api/alerts", {"min_level": "invalid_level"}, 400, 4003, "Invalid alert level"),
            ("/api/extended_metrics", {"key": "test", "type": "invalid_type"}, 400, 4003, "Invalid metric type"),
            ("/api/extended_metrics", {"key": "test", "interval": "invalid"}, 400, 4003, "Invalid interval"),
            
            # Invalid pagination
            ("/api/alerts", {"limit": "-1"}, 400, 4005, "Negative limit"),
            ("/api/alerts", {"limit": "10000"}, 400, 4005, "Limit too high"),
            ("/api/alerts", {"offset": "-5"}, 400, 4005, "Negative offset"),
            ("/api/alerts", {"limit": "abc"}, 400, 4003, "Non-numeric limit"),
            
            # Invalid time ranges
            ("/api/monitoring", {"range": "invalid_range"}, 400, 4004, "Invalid time range"),
            ("/api/monitoring", {"start": "not_a_number"}, 400, 4003, "Invalid start timestamp"),
            ("/api/monitoring", {"start": "1000", "end": "500"}, 400, 4004, "Start after end"),
        ]
        
        for endpoint, params, expected_status, error_code, test_name in param_tests:
            if not self.test_endpoint(endpoint, params, expected_status, error_code, test_name):
                all_passed = False
        
        print()
        
        # Test 3: UUID validation
        print("🔑 Testing UUID Validation:")
        uuid_tests = [
            ("/api/alerts/invalid", {}, 400, 4003, "Invalid UUID format"),
            ("/api/alerts/123", {}, 400, 4003, "Short UUID"),
            ("/api/alerts//acknowledge", {}, 404, None, "Empty UUID"),
        ]
        
        for endpoint, params, expected_status, error_code, test_name in uuid_tests:
            # Use POST for acknowledge/resolve endpoints
            method = 'POST' if 'acknowledge' in endpoint or 'resolve' in endpoint else 'GET'
            if method == 'POST':
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.post(url, headers=self.headers, timeout=10)
                    # Check for proper error response
                    if response.status_code == expected_status:
                        print(f"✅ {test_name}: PASSED")
                        self.test_results.append((test_name, True, "OK"))
                    else:
                        print(f"❌ {test_name}: Expected status {expected_status}, got {response.status_code}")
                        self.test_results.append((test_name, False, f"Wrong status {response.status_code}"))
                        all_passed = False
                except requests.RequestException as e:
                    print(f"❌ {test_name}: Request failed - {e}")
                    self.test_results.append((test_name, False, f"Request error: {e}"))
                    all_passed = False
            else:
                if not self.test_endpoint(endpoint, params, expected_status, error_code, test_name):
                    all_passed = False
        
        return all_passed
    
    def test_response_format(self) -> bool:
        """Test that all responses follow the standardized format."""
        print("\n📊 Testing Response Format Standardization:")
        
        endpoints_to_test = [
            "/api/status",
            "/api/alerts", 
            "/api/extended_metrics?key=test",
            "/api/monitoring",
        ]
        
        all_passed = True
        
        for endpoint in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code != 200:
                    continue  # Skip non-200 responses for format test
                
                data = response.json()
                
                # Check required format fields
                required_fields = ['status', 'timestamp', 'version', 'code']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"❌ {endpoint}: Missing fields {missing_fields}")
                    all_passed = False
                else:
                    # Check field types
                    if (isinstance(data['status'], str) and
                        isinstance(data['timestamp'], int) and
                        isinstance(data['version'], str) and
                        isinstance(data['code'], int)):
                        print(f"✅ {endpoint}: Correct format")
                    else:
                        print(f"❌ {endpoint}: Incorrect field types")
                        all_passed = False
                        
            except Exception as e:
                print(f"❌ {endpoint}: Format test failed - {e}")
                all_passed = False
        
        return all_passed
    
    def print_summary(self) -> None:
        """Print test summary."""
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\n📋 Test Summary:")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("\n❌ Failed Tests:")
            for name, success, details in self.test_results:
                if not success:
                    print(f"  - {name}: {details}")

def main():
    """Main test function."""
    print("🚀 BACmon API Validation Test Suite")
    print("=" * 50)
    
    # Test server availability
    try:
        response = requests.get(f"{BASE_URL}/api/status", headers=HEADERS, timeout=5)
        if response.status_code == 401:
            print("❌ Authentication failed. Please check API key configuration.")
            print("Make sure BACmon server is running with authentication enabled.")
            sys.exit(1)
        elif response.status_code != 200:
            print(f"❌ Server returned status {response.status_code}")
            print("Make sure BACmon server is running and accessible.")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"❌ Cannot connect to BACmon server at {BASE_URL}")
        print(f"Error: {e}")
        print("Make sure BACmon server is running and accessible.")
        sys.exit(1)
    
    print(f"✅ BACmon server accessible at {BASE_URL}\n")
    
    # Run tests
    tester = APIValidationTester(BASE_URL, HEADERS)
    
    validation_passed = tester.run_validation_tests()
    format_passed = tester.test_response_format()
    
    tester.print_summary()
    
    # Exit with appropriate code
    if validation_passed and format_passed:
        print("\n🎯 All validation and format tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 