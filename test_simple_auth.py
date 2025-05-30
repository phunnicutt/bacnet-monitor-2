#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the simple authentication system
Tests both API key and session authentication
"""

import sys
import requests
import json
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = 'http://localhost:8080'
TEST_API_KEY = 'test_key_123'
ADMIN_API_KEY = 'admin_key_456'

def test_api_without_auth() -> bool:
    """Test API access without authentication (should fail if auth is enabled)."""
    print("Testing API access without authentication...")
    
    try:
        response = requests.get(f'{BASE_URL}/api/status')
        if response.status_code == 401:
            print("✓ API correctly requires authentication")
            return True
        elif response.status_code == 200:
            print("⚠ API allows access without authentication (AUTH_ENABLED=false)")
            return True
        else:
            print(f"✗ Unexpected response code: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("✗ Cannot connect to BACmon server. Is it running on localhost:8080?")
        return False

def test_api_with_key(api_key: str, expected_success: bool = True) -> bool:
    """Test API access with API key."""
    print(f"Testing API access with key: {api_key[:12]}...")
    
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(f'{BASE_URL}/api/status', headers=headers)
        
        if expected_success and response.status_code == 200:
            print("✓ API key authentication successful")
            data = response.json()
            if data.get('status') == 'success':
                print(f"✓ API response format correct: {data.get('data', {}).get('system_status')}")
                return True
            else:
                print(f"✗ Unexpected API response format: {data}")
                return False
        elif not expected_success and response.status_code == 401:
            print("✓ Invalid API key correctly rejected")
            return True
        else:
            print(f"✗ Unexpected response code: {response.status_code}")
            if response.text:
                print(f"Response: {response.text[:200]}")
            return False
    except requests.ConnectionError:
        print("✗ Cannot connect to BACmon server")
        return False
    except json.JSONDecodeError:
        print("✗ Invalid JSON response")
        return False

def test_admin_endpoint(api_key: str, expected_success: bool = True) -> bool:
    """Test admin endpoint access."""
    print(f"Testing admin endpoint with key: {api_key[:12]}...")
    
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(f'{BASE_URL}/auth/info', headers=headers)
        
        if expected_success and response.status_code == 200:
            print("✓ Admin endpoint access successful")
            data = response.json()
            if data.get('data', {}).get('current_status', {}).get('authenticated'):
                print("✓ Authentication status confirmed")
                return True
            else:
                print(f"✗ Authentication status not confirmed: {data}")
                return False
        elif not expected_success and response.status_code == 401:
            print("✓ Admin endpoint correctly requires proper permissions")
            return True
        else:
            print(f"✗ Unexpected response code: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("✗ Cannot connect to BACmon server")
        return False
    except json.JSONDecodeError:
        print("✗ Invalid JSON response")
        return False

def test_web_login() -> bool:
    """Test web-based login."""
    print("Testing web login functionality...")
    
    try:
        # Test login page access
        response = requests.get(f'{BASE_URL}/login')
        if response.status_code != 200:
            print(f"✗ Cannot access login page: {response.status_code}")
            return False
        
        print("✓ Login page accessible")
        
        # Test login with valid credentials
        session = requests.Session()
        login_data = {
            'username': 'test',
            'password': 'test123'
        }
        
        response = session.post(f'{BASE_URL}/login', data=login_data, allow_redirects=False)
        
        if response.status_code in [302, 303]:  # Redirect after successful login
            print("✓ Login successful (redirected)")
            
            # Test access to protected resource
            response = session.get(f'{BASE_URL}/')
            if response.status_code == 200:
                print("✓ Can access protected resources after login")
                return True
            else:
                print(f"✗ Cannot access protected resources after login: {response.status_code}")
                return False
        else:
            print(f"✗ Login failed: {response.status_code}")
            if response.text:
                print(f"Response: {response.text[:200]}")
            return False
            
    except requests.ConnectionError:
        print("✗ Cannot connect to BACmon server")
        return False

def test_auth_info_endpoint() -> bool:
    """Test the auth info endpoint."""
    print("Testing auth info endpoint...")
    
    try:
        headers = {'X-API-Key': TEST_API_KEY}
        response = requests.get(f'{BASE_URL}/auth/info', headers=headers)
        
        if response.status_code == 200:
            print("✓ Auth info endpoint accessible")
            data = response.json()
            
            if 'available_api_keys' in data.get('data', {}):
                print("✓ API keys information available")
                print(f"Available API keys: {list(data['data']['available_api_keys'].keys())}")
                return True
            else:
                print(f"✗ Expected auth info not found: {data}")
                return False
        else:
            print(f"✗ Auth info endpoint failed: {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("✗ Cannot connect to BACmon server")
        return False
    except json.JSONDecodeError:
        print("✗ Invalid JSON response")
        return False

def main():
    """Run all authentication tests."""
    print("BACmon Simple Authentication Test Suite")
    print("=" * 50)
    
    tests = [
        ("API without auth", test_api_without_auth),
        ("API with valid key", lambda: test_api_with_key(TEST_API_KEY, True)),
        ("API with invalid key", lambda: test_api_with_key('invalid_key', False)),
        ("Admin endpoint with user key", lambda: test_admin_endpoint(TEST_API_KEY, True)),
        ("Admin endpoint with admin key", lambda: test_admin_endpoint(ADMIN_API_KEY, True)),
        ("Web login", test_web_login),
        ("Auth info endpoint", test_auth_info_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                print(f"FAILED: {test_name}")
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All authentication tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Check BACmon configuration and server status.")
        sys.exit(1)

if __name__ == "__main__":
    main() 