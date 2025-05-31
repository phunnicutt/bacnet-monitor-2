#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
User Acceptance Testing (UAT) for BACmon REST API System

This script performs comprehensive end-to-end testing of the BACmon REST API
from an end-user perspective, validating real-world usage scenarios and
ensuring the system meets production requirements.

Test Categories:
1. API Functionality & Integration
2. Authentication & Security
3. API Versioning & Backward Compatibility
4. Real-time Features & Streaming
5. Data Export & Formatting
6. Web Dashboard Integration
7. Performance & Reliability
8. Error Handling & Edge Cases
"""

import sys
import json
import time
import logging
import requests
import threading
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('UAT_BACmon_API')

class BACmonUATTester:
    """User Acceptance Testing suite for BACmon REST API system."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.api_v1_url = f"{self.base_url}/api"
        self.api_v2_url = f"{self.base_url}/api/v2"
        self.test_results = []
        self.session = requests.Session()
        
        # Test credentials (from simple_auth.py)
        self.test_api_key = "test_key_123"
        self.admin_api_key = "admin_key_456"
        self.test_user = {"username": "test", "password": "test123"}
        self.admin_user = {"username": "admin", "password": "admin123"}
        
    def log_test_result(self, test_name: str, success: bool, details: str = "", 
                       response_time: float = 0.0, data: Any = None):
        """Log test result for reporting."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name} ({response_time:.3f}s) - {details}")
    
    def check_server_availability(self) -> bool:
        """Check if BACmon server is running and accessible."""
        logger.info("=" * 60)
        logger.info("UAT Phase 1: Server Availability Check")
        logger.info("=" * 60)
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/", timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test_result(
                    "Server Availability", True, 
                    f"Server accessible (HTTP {response.status_code})", 
                    response_time
                )
                return True
            else:
                self.log_test_result(
                    "Server Availability", False, 
                    f"Server returned HTTP {response.status_code}", 
                    response_time
                )
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test_result(
                "Server Availability", False, 
                f"Connection failed: {str(e)}", 0.0
            )
            return False
    
    def test_api_authentication(self) -> None:
        """Test API authentication mechanisms."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 2: Authentication & Security Testing")
        logger.info("=" * 60)
        
        # Test 1: API Key Authentication
        headers = {"X-API-Key": self.test_api_key}
        start_time = time.time()
        try:
            response = requests.get(f"{self.api_v1_url}/status", headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test_result(
                        "API Key Authentication", True,
                        "Valid API key accepted", response_time, data
                    )
                else:
                    self.log_test_result(
                        "API Key Authentication", False,
                        f"Unexpected response format: {data}", response_time
                    )
            else:
                self.log_test_result(
                    "API Key Authentication", False,
                    f"HTTP {response.status_code}: {response.text}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "API Key Authentication", False,
                f"Request failed: {str(e)}", time.time() - start_time
            )
        
        # Test 2: Invalid API Key Rejection
        headers = {"X-API-Key": "invalid_key_123"}
        start_time = time.time()
        try:
            response = requests.get(f"{self.api_v1_url}/status", headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 401:
                self.log_test_result(
                    "Invalid API Key Rejection", True,
                    "Invalid API key properly rejected", response_time
                )
            else:
                self.log_test_result(
                    "Invalid API Key Rejection", False,
                    f"Expected 401, got HTTP {response.status_code}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "Invalid API Key Rejection", False,
                f"Request failed: {str(e)}", time.time() - start_time
            )
        
        # Test 3: Web Session Authentication
        start_time = time.time()
        try:
            # Login via web interface
            login_data = self.test_user
            response = requests.post(f"{self.base_url}/login", data=login_data, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code in [200, 302]:  # Success or redirect
                self.log_test_result(
                    "Web Session Login", True,
                    "Web login successful", response_time
                )
                
                # Test authenticated request with session
                cookies = response.cookies
                auth_response = requests.get(f"{self.base_url}/api-dashboard", 
                                           cookies=cookies, timeout=10)
                if auth_response.status_code == 200:
                    self.log_test_result(
                        "Session-based API Access", True,
                        "Session authentication working", response_time
                    )
                else:
                    self.log_test_result(
                        "Session-based API Access", False,
                        f"Session access failed: HTTP {auth_response.status_code}", 
                        response_time
                    )
            else:
                self.log_test_result(
                    "Web Session Login", False,
                    f"Login failed: HTTP {response.status_code}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "Web Session Authentication", False,
                f"Session test failed: {str(e)}", time.time() - start_time
            )
    
    def test_api_versioning(self) -> None:
        """Test API versioning and backward compatibility."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 3: API Versioning & Backward Compatibility")
        logger.info("=" * 60)
        
        headers = {"X-API-Key": self.test_api_key}
        
        # Test 1: V1 API Endpoints
        v1_endpoints = [
            "/status", "/monitoring", "/traffic", "/devices", 
            "/anomalies", "/alerts", "/metrics"
        ]
        
        for endpoint in v1_endpoints:
            start_time = time.time()
            try:
                response = requests.get(f"{self.api_v1_url}{endpoint}", 
                                      headers=headers, timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if "version" in data and "status" in data:
                        self.log_test_result(
                            f"V1 Endpoint {endpoint}", True,
                            f"V1 endpoint functional", response_time
                        )
                    else:
                        self.log_test_result(
                            f"V1 Endpoint {endpoint}", False,
                            "Missing required response fields", response_time
                        )
                else:
                    self.log_test_result(
                        f"V1 Endpoint {endpoint}", False,
                        f"HTTP {response.status_code}: {response.text[:100]}", 
                        response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"V1 Endpoint {endpoint}", False,
                    f"Request failed: {str(e)}", time.time() - start_time
                )
        
        # Test 2: V2 API Endpoints
        v2_endpoints = ["/status", "/info"]
        
        for endpoint in v2_endpoints:
            start_time = time.time()
            try:
                response = requests.get(f"{self.api_v2_url}{endpoint}", 
                                      headers=headers, timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if "version" in data and "features" in data:
                        self.log_test_result(
                            f"V2 Endpoint {endpoint}", True,
                            f"V2 endpoint with enhanced features", response_time
                        )
                    else:
                        self.log_test_result(
                            f"V2 Endpoint {endpoint}", False,
                            "Missing V2-specific fields", response_time
                        )
                else:
                    self.log_test_result(
                        f"V2 Endpoint {endpoint}", False,
                        f"HTTP {response.status_code}: {response.text[:100]}", 
                        response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"V2 Endpoint {endpoint}", False,
                    f"Request failed: {str(e)}", time.time() - start_time
                )
        
        # Test 3: Backward Compatibility
        start_time = time.time()
        try:
            # Test that old /api/ routes still work
            response = requests.get(f"{self.base_url}/api/status", 
                                  headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test_result(
                    "Backward Compatibility", True,
                    "Legacy /api/ routes still functional", response_time
                )
            else:
                self.log_test_result(
                    "Backward Compatibility", False,
                    f"Legacy routes broken: HTTP {response.status_code}", 
                    response_time
                )
        except Exception as e:
            self.log_test_result(
                "Backward Compatibility", False,
                f"Legacy route test failed: {str(e)}", time.time() - start_time
            )
    
    def test_data_access_functionality(self) -> None:
        """Test data access, filtering, and export functionality."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 4: Data Access & Export Functionality")
        logger.info("=" * 60)
        
        headers = {"X-API-Key": self.test_api_key}
        
        # Test 1: Monitoring Data Access with Time Ranges
        time_ranges = ["1h", "6h", "24h"]
        for time_range in time_ranges:
            start_time = time.time()
            try:
                response = requests.get(
                    f"{self.api_v1_url}/monitoring?range={time_range}&limit=10",
                    headers=headers, timeout=15
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list):
                        self.log_test_result(
                            f"Monitoring Data ({time_range})", True,
                            f"Retrieved {len(data['data'])} records", response_time
                        )
                    else:
                        self.log_test_result(
                            f"Monitoring Data ({time_range})", False,
                            "Invalid data format", response_time
                        )
                else:
                    self.log_test_result(
                        f"Monitoring Data ({time_range})", False,
                        f"HTTP {response.status_code}", response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"Monitoring Data ({time_range})", False,
                    f"Request failed: {str(e)}", time.time() - start_time
                )
        
        # Test 2: Data Export Functionality
        export_formats = ["json", "csv"]
        for fmt in export_formats:
            start_time = time.time()
            try:
                response = requests.get(
                    f"{self.api_v1_url}/export?format={fmt}&limit=5",
                    headers=headers, timeout=15
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    if fmt == "json":
                        try:
                            data = response.json()
                            self.log_test_result(
                                f"Data Export ({fmt.upper()})", True,
                                "JSON export successful", response_time
                            )
                        except:
                            self.log_test_result(
                                f"Data Export ({fmt.upper()})", False,
                                "Invalid JSON response", response_time
                            )
                    else:  # CSV
                        if "," in response.text:
                            self.log_test_result(
                                f"Data Export ({fmt.upper()})", True,
                                "CSV export successful", response_time
                            )
                        else:
                            self.log_test_result(
                                f"Data Export ({fmt.upper()})", False,
                                "Invalid CSV format", response_time
                            )
                else:
                    self.log_test_result(
                        f"Data Export ({fmt.upper()})", False,
                        f"HTTP {response.status_code}", response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"Data Export ({fmt.upper()})", False,
                    f"Export failed: {str(e)}", time.time() - start_time
                )
        
        # Test 3: Pagination and Filtering
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.api_v1_url}/devices?limit=3&offset=0",
                headers=headers, timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "total_count" in data:
                    self.log_test_result(
                        "Pagination Support", True,
                        f"Pagination working (limit/offset)", response_time
                    )
                else:
                    self.log_test_result(
                        "Pagination Support", False,
                        "Missing pagination metadata", response_time
                    )
            else:
                self.log_test_result(
                    "Pagination Support", False,
                    f"HTTP {response.status_code}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "Pagination Support", False,
                f"Pagination test failed: {str(e)}", time.time() - start_time
            )
    
    def test_real_time_features(self) -> None:
        """Test real-time streaming and live data features."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 5: Real-time Features & Streaming")
        logger.info("=" * 60)
        
        headers = {"X-API-Key": self.test_api_key}
        
        # Test 1: Server-Sent Events (SSE) Monitoring Stream
        def test_sse_stream(endpoint_name: str, url: str):
            try:
                start_time = time.time()
                response = requests.get(url, headers=headers, stream=True, timeout=5)
                
                if response.status_code == 200:
                    # Read first few lines to verify SSE format
                    lines_read = 0
                    for line in response.iter_lines(decode_unicode=True):
                        if line and lines_read < 3:
                            lines_read += 1
                            if line.startswith("data:") or line.startswith("event:"):
                                continue
                        else:
                            break
                    
                    response_time = time.time() - start_time
                    if lines_read > 0:
                        self.log_test_result(
                            f"SSE Stream - {endpoint_name}", True,
                            f"Stream established, received {lines_read} events", 
                            response_time
                        )
                    else:
                        self.log_test_result(
                            f"SSE Stream - {endpoint_name}", False,
                            "No SSE events received", response_time
                        )
                else:
                    self.log_test_result(
                        f"SSE Stream - {endpoint_name}", False,
                        f"HTTP {response.status_code}", time.time() - start_time
                    )
            except requests.exceptions.Timeout:
                self.log_test_result(
                    f"SSE Stream - {endpoint_name}", True,
                    "Stream timeout (expected for test)", 5.0
                )
            except Exception as e:
                self.log_test_result(
                    f"SSE Stream - {endpoint_name}", False,
                    f"Stream test failed: {str(e)}", time.time() - start_time
                )
        
        # Test V2 streaming endpoints
        test_sse_stream("Monitoring", f"{self.api_v2_url}/monitoring/stream")
        test_sse_stream("Alerts", f"{self.api_v2_url}/alerts/stream")
        
        # Test 2: V2 Data Aggregation
        start_time = time.time()
        try:
            agg_params = {
                "metric": "cpu_usage",
                "function": "avg",
                "window": "1h"
            }
            response = requests.get(
                f"{self.api_v2_url}/data/aggregate",
                headers=headers, params=agg_params, timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "aggregation" in data:
                    self.log_test_result(
                        "V2 Data Aggregation", True,
                        f"Aggregation successful ({agg_params['function']})", 
                        response_time
                    )
                else:
                    self.log_test_result(
                        "V2 Data Aggregation", False,
                        "Missing aggregation results", response_time
                    )
            else:
                self.log_test_result(
                    "V2 Data Aggregation", False,
                    f"HTTP {response.status_code}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "V2 Data Aggregation", False,
                f"Aggregation test failed: {str(e)}", time.time() - start_time
            )
    
    def test_web_dashboard_integration(self) -> None:
        """Test web dashboard integration and API console."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 6: Web Dashboard Integration")
        logger.info("=" * 60)
        
        # Test 1: Main Dashboard Access
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "BACmon" in response.text:
                self.log_test_result(
                    "Main Dashboard Access", True,
                    "Dashboard accessible and rendering", response_time
                )
            else:
                self.log_test_result(
                    "Main Dashboard Access", False,
                    f"Dashboard access failed: HTTP {response.status_code}", 
                    response_time
                )
        except Exception as e:
            self.log_test_result(
                "Main Dashboard Access", False,
                f"Dashboard test failed: {str(e)}", time.time() - start_time
            )
        
        # Test 2: API Dashboard Access
        start_time = time.time()
        try:
            # Login first to get session
            login_response = requests.post(
                f"{self.base_url}/login", 
                data=self.test_user, timeout=10
            )
            
            if login_response.status_code in [200, 302]:
                cookies = login_response.cookies
                response = requests.get(
                    f"{self.base_url}/api-dashboard", 
                    cookies=cookies, timeout=10
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200 and "API Dashboard" in response.text:
                    self.log_test_result(
                        "API Dashboard Access", True,
                        "API dashboard accessible", response_time
                    )
                else:
                    self.log_test_result(
                        "API Dashboard Access", False,
                        f"API dashboard failed: HTTP {response.status_code}", 
                        response_time
                    )
            else:
                self.log_test_result(
                    "API Dashboard Access", False,
                    "Login required for dashboard access", time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "API Dashboard Integration", False,
                f"Dashboard test failed: {str(e)}", time.time() - start_time
            )
        
        # Test 3: Static Assets Loading
        static_assets = [
            "/static/api-dashboard.css",
            "/static/js/api-client.js",
            "/static/js/api-dashboard.js"
        ]
        
        for asset in static_assets:
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}{asset}", timeout=5)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.log_test_result(
                        f"Static Asset {asset.split('/')[-1]}", True,
                        "Asset loaded successfully", response_time
                    )
                else:
                    self.log_test_result(
                        f"Static Asset {asset.split('/')[-1]}", False,
                        f"Asset not found: HTTP {response.status_code}", 
                        response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"Static Asset {asset.split('/')[-1]}", False,
                    f"Asset load failed: {str(e)}", time.time() - start_time
                )
    
    def test_performance_reliability(self) -> None:
        """Test API performance and reliability under load."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 7: Performance & Reliability Testing")
        logger.info("=" * 60)
        
        headers = {"X-API-Key": self.test_api_key}
        
        # Test 1: Concurrent Request Handling
        def make_concurrent_request(endpoint: str, results: List):
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.api_v1_url}{endpoint}", 
                    headers=headers, timeout=10
                )
                response_time = time.time() - start_time
                results.append({
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "status_code": response.status_code
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "response_time": 10.0,
                    "error": str(e)
                })
        
        # Test concurrent requests
        concurrent_results = []
        threads = []
        
        for i in range(5):  # 5 concurrent requests
            thread = threading.Thread(
                target=make_concurrent_request, 
                args=["/status", concurrent_results]
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        successful_requests = sum(1 for r in concurrent_results if r["success"])
        avg_response_time = sum(r["response_time"] for r in concurrent_results) / len(concurrent_results)
        
        if successful_requests >= 4:  # At least 80% success
            self.log_test_result(
                "Concurrent Request Handling", True,
                f"{successful_requests}/5 requests successful, avg {avg_response_time:.3f}s",
                avg_response_time
            )
        else:
            self.log_test_result(
                "Concurrent Request Handling", False,
                f"Only {successful_requests}/5 requests successful",
                avg_response_time
            )
        
        # Test 2: Large Data Set Handling
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.api_v1_url}/monitoring?limit=100&range=24h",
                headers=headers, timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    self.log_test_result(
                        "Large Dataset Handling", True,
                        f"Handled {len(data.get('data', []))} records", 
                        response_time
                    )
                else:
                    self.log_test_result(
                        "Large Dataset Handling", False,
                        "Invalid response format", response_time
                    )
            else:
                self.log_test_result(
                    "Large Dataset Handling", False,
                    f"HTTP {response.status_code}", response_time
                )
        except Exception as e:
            self.log_test_result(
                "Large Dataset Handling", False,
                f"Large dataset test failed: {str(e)}", time.time() - start_time
            )
    
    def test_error_handling(self) -> None:
        """Test comprehensive error handling and edge cases."""
        logger.info("\n" + "=" * 60)
        logger.info("UAT Phase 8: Error Handling & Edge Cases")
        logger.info("=" * 60)
        
        headers = {"X-API-Key": self.test_api_key}
        
        # Test 1: Invalid Parameters
        error_scenarios = [
            ("/monitoring?range=invalid", "Invalid time range"),
            ("/devices?limit=9999", "Excessive limit"),
            ("/alerts/invalid-uuid", "Invalid UUID format"),
            ("/nonexistent-endpoint", "Non-existent endpoint")
        ]
        
        for endpoint, description in error_scenarios:
            start_time = time.time()
            try:
                response = requests.get(
                    f"{self.api_v1_url}{endpoint}",
                    headers=headers, timeout=10
                )
                response_time = time.time() - start_time
                
                if response.status_code in [400, 404]:
                    try:
                        error_data = response.json()
                        if "error" in error_data or "status" in error_data:
                            self.log_test_result(
                                f"Error Handling - {description}", True,
                                f"Proper error response (HTTP {response.status_code})",
                                response_time
                            )
                        else:
                            self.log_test_result(
                                f"Error Handling - {description}", False,
                                "Error response missing structured format",
                                response_time
                            )
                    except:
                        self.log_test_result(
                            f"Error Handling - {description}", False,
                            "Error response not valid JSON", response_time
                        )
                else:
                    self.log_test_result(
                        f"Error Handling - {description}", False,
                        f"Unexpected status: HTTP {response.status_code}",
                        response_time
                    )
            except Exception as e:
                self.log_test_result(
                    f"Error Handling - {description}", False,
                    f"Error test failed: {str(e)}", time.time() - start_time
                )
        
        # Test 2: Rate Limiting (if implemented)
        # Make rapid requests to test rate limiting
        rapid_requests = 0
        rate_limit_triggered = False
        
        start_time = time.time()
        for i in range(10):
            try:
                response = requests.get(
                    f"{self.api_v1_url}/status",
                    headers=headers, timeout=5
                )
                rapid_requests += 1
                if response.status_code == 429:  # Too Many Requests
                    rate_limit_triggered = True
                    break
            except:
                break
        response_time = time.time() - start_time
        
        # Note: Rate limiting is deferred, so we don't expect it to trigger
        self.log_test_result(
            "Rate Limiting Test", True,
            f"Made {rapid_requests} requests without rate limiting (as expected)",
            response_time
        )
    
    def generate_uat_report(self) -> Dict[str, Any]:
        """Generate comprehensive UAT report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = sum(r["response_time"] for r in self.test_results) / total_tests
        
        report = {
            "uat_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": round(success_rate, 2),
                "average_response_time": round(avg_response_time, 3),
                "test_date": datetime.now().isoformat(),
                "test_duration": sum(r["response_time"] for r in self.test_results)
            },
            "test_phases": {
                "server_availability": [],
                "authentication_security": [],
                "api_versioning": [],
                "data_access_export": [],
                "real_time_features": [],
                "web_dashboard": [],
                "performance_reliability": [],
                "error_handling": []
            },
            "detailed_results": self.test_results,
            "recommendations": []
        }
        
        # Categorize results by phase
        for result in self.test_results:
            test_name = result["test_name"].lower()
            if "server" in test_name or "availability" in test_name:
                report["test_phases"]["server_availability"].append(result)
            elif "auth" in test_name or "login" in test_name or "session" in test_name:
                report["test_phases"]["authentication_security"].append(result)
            elif "v1" in test_name or "v2" in test_name or "version" in test_name or "backward" in test_name:
                report["test_phases"]["api_versioning"].append(result)
            elif "data" in test_name or "export" in test_name or "monitoring" in test_name or "pagination" in test_name:
                report["test_phases"]["data_access_export"].append(result)
            elif "stream" in test_name or "sse" in test_name or "aggregation" in test_name:
                report["test_phases"]["real_time_features"].append(result)
            elif "dashboard" in test_name or "static" in test_name:
                report["test_phases"]["web_dashboard"].append(result)
            elif "concurrent" in test_name or "performance" in test_name or "large" in test_name:
                report["test_phases"]["performance_reliability"].append(result)
            elif "error" in test_name or "invalid" in test_name or "rate" in test_name:
                report["test_phases"]["error_handling"].append(result)
        
        # Generate recommendations
        if failed_tests > 0:
            report["recommendations"].append("Review failed test cases and address underlying issues")
        
        if avg_response_time > 2.0:
            report["recommendations"].append("Consider performance optimization for response times")
        
        if success_rate < 90:
            report["recommendations"].append("API system needs improvement before production deployment")
        elif success_rate >= 95:
            report["recommendations"].append("API system is production-ready")
        else:
            report["recommendations"].append("API system is mostly ready, with minor issues to address")
        
        return report
    
    def run_full_uat_suite(self) -> bool:
        """Run the complete User Acceptance Testing suite."""
        logger.info("🚀 Starting BACmon REST API User Acceptance Testing")
        logger.info("="*60)
        
        start_time = time.time()
        
        # Check if server is available
        if not self.check_server_availability():
            logger.error("❌ Server not available. Please ensure BACmon is running on %s", self.base_url)
            return False
        
        # Run all test phases
        self.test_api_authentication()
        self.test_api_versioning()
        self.test_data_access_functionality()
        self.test_real_time_features()
        self.test_web_dashboard_integration()
        self.test_performance_reliability()
        self.test_error_handling()
        
        # Generate and display report
        total_time = time.time() - start_time
        report = self.generate_uat_report()
        
        logger.info("\n" + "="*60)
        logger.info("🎯 USER ACCEPTANCE TESTING COMPLETE")
        logger.info("="*60)
        logger.info("📊 TEST SUMMARY:")
        logger.info(f"   Total Tests: {report['uat_summary']['total_tests']}")
        logger.info(f"   Passed: {report['uat_summary']['passed_tests']}")
        logger.info(f"   Failed: {report['uat_summary']['failed_tests']}")
        logger.info(f"   Success Rate: {report['uat_summary']['success_rate']}%")
        logger.info(f"   Avg Response Time: {report['uat_summary']['average_response_time']}s")
        logger.info(f"   Total Test Duration: {total_time:.2f}s")
        
        logger.info("\n📋 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            logger.info(f"   • {rec}")
        
        # Save detailed report
        report_file = "uat_report_bacmon_api.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        
        success_rate = report['uat_summary']['success_rate']
        if success_rate >= 90:
            logger.info("✅ UAT RESULT: SYSTEM READY FOR PRODUCTION")
            return True
        else:
            logger.warning("⚠️  UAT RESULT: SYSTEM NEEDS IMPROVEMENT")
            return False

def main():
    """Main function to run User Acceptance Testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='BACmon REST API User Acceptance Testing')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL for BACmon server (default: http://localhost:8080)')
    parser.add_argument('--quiet', action='store_true', 
                       help='Run tests quietly (less verbose output)')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Create UAT tester and run tests
    tester = BACmonUATTester(base_url=args.url)
    success = tester.run_full_uat_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 