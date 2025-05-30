#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for BACmon REST API endpoints

This script tests the enhanced REST API functionality to ensure
all new endpoints work correctly and return properly formatted responses.
"""

import sys
import logging
import requests
import json
import time
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_api_endpoints')

class BACmonAPITester:
    """Test class for BACmon REST API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:9090"):
        """Initialize the API tester with base URL."""
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: Dict[str, bool] = {}
    
    def test_endpoint(self, endpoint: str, method: str = 'GET', 
                     params: Optional[Dict[str, Any]] = None,
                     expected_status: int = 200) -> bool:
        """
        Test a single API endpoint.
        
        Args:
            endpoint: The endpoint path (e.g., '/api/status')
            method: HTTP method ('GET', 'POST', etc.)
            params: Query parameters for GET or form data for POST
            expected_status: Expected HTTP status code
            
        Returns:
            True if test passed, False otherwise
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, data=params, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return False
            
            # Check status code
            if response.status_code != expected_status:
                logger.error(f"❌ {endpoint}: Expected status {expected_status}, got {response.status_code}")
                return False
            
            # Try to parse JSON response
            try:
                data = response.json()
                
                # Check for standardized response format
                if 'status' in data and 'timestamp' in data and 'version' in data:
                    if data['status'] == 'success' and 'data' in data:
                        logger.info(f"✅ {endpoint}: Success with standardized format")
                        return True
                    elif data['status'] == 'error' and 'error' in data:
                        logger.info(f"✅ {endpoint}: Error response with standardized format")
                        return True
                    else:
                        logger.warning(f"⚠️ {endpoint}: Unexpected response structure")
                        return False
                else:
                    # Legacy response format (might be OK for some endpoints)
                    logger.info(f"✅ {endpoint}: Success with legacy format")
                    return True
                    
            except json.JSONDecodeError:
                if response.headers.get('content-type') == 'text/csv':
                    logger.info(f"✅ {endpoint}: Success with CSV format")
                    return True
                else:
                    logger.error(f"❌ {endpoint}: Invalid JSON response")
                    return False
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {endpoint}: Request failed - {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all API endpoint tests."""
        logger.info("Starting BACmon REST API endpoint tests...")
        
        # Test enhanced core endpoints
        tests = [
            # System status and health
            ('/api/status', 'GET', None, 200),
            
            # Monitoring data
            ('/api/monitoring', 'GET', None, 200),
            ('/api/monitoring', 'GET', {'interval': 'm', 'limit': '10'}, 200),
            ('/api/monitoring', 'GET', {'range': '1h'}, 200),
            
            # Traffic analysis
            ('/api/traffic', 'GET', None, 200),
            ('/api/traffic', 'GET', {'type': 'ip'}, 200),
            ('/api/traffic', 'GET', {'type': 'error'}, 200),
            ('/api/traffic', 'GET', {'type': 'invalid'}, 400),  # Should return error
            
            # Device information
            ('/api/devices', 'GET', None, 200),
            ('/api/devices', 'GET', {'include_undefined': 'true'}, 200),
            
            # Anomaly detection (might return 503 if not available)
            ('/api/anomalies', 'GET', None, [200, 503]),
            
            # Export functionality
            ('/api/export', 'GET', {'format': 'json', 'type': 'monitoring'}, 200),
            ('/api/export', 'GET', {'format': 'csv', 'type': 'monitoring'}, 200),
            ('/api/export', 'GET', {'format': 'invalid'}, 400),  # Should return error
            
            # Enhanced existing endpoints
            ('/api/alerts', 'GET', None, 200),
            ('/api/alerts/history', 'GET', {'max': '50'}, 200),
            ('/api/metrics', 'GET', None, 200),
            ('/api/extended_metrics', 'GET', {'key': 'test-key'}, [200, 400]),  # Might not exist
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            endpoint, method, params, expected_status = test
            
            # Handle multiple acceptable status codes
            if isinstance(expected_status, list):
                result = False
                for status in expected_status:
                    if self.test_endpoint(endpoint, method, params, status):
                        result = True
                        break
            else:
                result = self.test_endpoint(endpoint, method, params, expected_status)
            
            self.test_results[endpoint] = result
            if result:
                passed += 1
        
        # Summary
        logger.info(f"\n=== TEST SUMMARY ===")
        logger.info(f"Passed: {passed}/{total} tests")
        logger.info(f"Success rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.warning("⚠️ Some tests failed. Check the logs above for details.")
            return False

def test_response_format():
    """Test the standardized response format specifically."""
    logger.info("\n=== Testing Response Format ===")
    
    tester = BACmonAPITester()
    
    # Test a simple endpoint
    try:
        response = requests.get(f"{tester.base_url}/api/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields
            required_fields = ['status', 'timestamp', 'version', 'code']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                logger.error(f"❌ Missing required fields: {missing_fields}")
                return False
            
            # Check data structure
            if data['status'] == 'success' and 'data' in data:
                logger.info("✅ Response format is correct")
                
                # Check timestamp is recent (within last minute)
                now = int(time.time())
                if abs(now - data['timestamp']) > 60:
                    logger.warning("⚠️ Timestamp seems old")
                
                return True
            elif data['status'] == 'error' and 'error' in data:
                logger.info("✅ Error response format is correct")
                return True
            else:
                logger.error("❌ Invalid response structure")
                return False
        else:
            logger.error(f"❌ API endpoint returned status {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Failed to test response format: {e}")
        return False

def check_server_availability(base_url: str = "http://localhost:9090") -> bool:
    """Check if the BACmon server is running."""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            logger.info("✅ BACmon server is running")
            return True
        else:
            logger.error(f"❌ BACmon server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Cannot connect to BACmon server at {base_url}: {e}")
        logger.error("Please ensure the BACmon WSGI server is running on port 9090")
        return False

if __name__ == "__main__":
    # Check if server is available
    if not check_server_availability():
        sys.exit(1)
    
    # Test response format
    if not test_response_format():
        logger.error("Response format test failed")
        sys.exit(1)
    
    # Run all endpoint tests
    tester = BACmonAPITester()
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All API tests completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some API tests failed")
        sys.exit(1) 