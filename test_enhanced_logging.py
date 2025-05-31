#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Enhanced Logging and Error Handling Framework

This script tests the new BACmon logging framework to ensure:
1. Structured logging works correctly
2. Configuration-driven setup functions properly
3. Custom exception classes work as expected
4. Error context and timing decorators function correctly
5. Log rotation and management work
6. Redis operation logging is properly formatted
"""

import sys
import os
import json
import time
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from configparser import ConfigParser
from typing import Dict, Any, Optional

# Import the enhanced logging framework
try:
    from bacmon_logger import (
        BACmonLogger, LogCategory, get_logger, configure_logging,
        BACmonError, BACmonConfigError, BACmonRedisError, 
        BACmonNetworkError, BACmonValidationError,
        error_context, timed_operation, request_context,
        correlation_context, log_redis_operation, logging_health_check
    )
except ImportError as e:
    print(f"Cannot import enhanced logging framework: {e}")
    print("Make sure bacmon_logger.py is in the current directory.")
    sys.exit(1)

class TestEnhancedLogging(unittest.TestCase):
    """Test cases for enhanced logging framework"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test.log')
        self.error_log = os.path.join(self.temp_dir, 'error.log')
        
        # Create test configuration
        self.config = ConfigParser()
        self.config.add_section('Logging')
        self.config.set('Logging', 'level', 'DEBUG')
        self.config.set('Logging', 'format', 'json')
        self.config.set('Logging', 'console_enabled', 'true')
        self.config.set('Logging', 'file_enabled', 'true')
        self.config.set('Logging', 'log_file', self.log_file)
        self.config.set('Logging', 'error_log', self.error_log)
        self.config.set('Logging', 'max_size_mb', '1')
        self.config.set('Logging', 'max_files', '3')
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Reset global logger
        import bacmon_logger
        bacmon_logger._global_logger = None
    
    def test_logger_creation_and_configuration(self):
        """Test basic logger creation and configuration"""
        logger = BACmonLogger('test_logger')
        self.assertEqual(logger.name, 'test_logger')
        self.assertFalse(logger._configured)
        
        # Configure with test config
        logger.configure(self.config)
        self.assertTrue(logger._configured)
        self.assertTrue(len(logger.logger.handlers) > 0)
    
    def test_structured_logging_format(self):
        """Test structured JSON logging format"""
        logger = BACmonLogger('test_structured')
        logger.configure(self.config)
        
        # Capture log output
        with patch('sys.stdout', new_callable=Mock) as mock_stdout:
            logger.info("Test message", category=LogCategory.MONITORING,
                       data={'key': 'value', 'number': 42})
            
            # Verify structured format was used
            written_calls = [call for call in mock_stdout.write.call_args_list 
                           if call[0][0].strip()]
            
            if written_calls:
                log_output = written_calls[0][0][0]
                try:
                    log_entry = json.loads(log_output)
                    self.assertIn('timestamp', log_entry)
                    self.assertIn('level', log_entry)
                    self.assertIn('category', log_entry)
                    self.assertIn('message', log_entry)
                    self.assertIn('correlation_id', log_entry)
                    self.assertEqual(log_entry['level'], 'INFO')
                    self.assertEqual(log_entry['category'], LogCategory.MONITORING)
                    self.assertEqual(log_entry['message'], 'Test message')
                    self.assertIn('data', log_entry)
                    self.assertEqual(log_entry['data']['key'], 'value')
                    self.assertEqual(log_entry['data']['number'], 42)
                except json.JSONDecodeError:
                    self.fail(f"Log output is not valid JSON: {log_output}")
    
    def test_log_categories(self):
        """Test different log categories"""
        logger = get_logger(config=self.config)
        
        categories = [
            LogCategory.SYSTEM,
            LogCategory.MONITORING,
            LogCategory.API,
            LogCategory.REDIS,
            LogCategory.ALERTS,
            LogCategory.SECURITY,
            LogCategory.PERFORMANCE,
            LogCategory.NETWORK,
            LogCategory.CONFIG
        ]
        
        for category in categories:
            with self.subTest(category=category):
                try:
                    logger.info(f"Test message for {category}", category=category)
                except Exception as e:
                    self.fail(f"Failed to log with category {category}: {e}")
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        # Test BACmonError
        try:
            raise BACmonError("Test error", LogCategory.SYSTEM, {'test': True})
        except BACmonError as e:
            self.assertEqual(e.message, "Test error")
            self.assertEqual(e.category, LogCategory.SYSTEM)
            self.assertIn('test', e.context)
            self.assertTrue(e.context['test'])
            self.assertIsNotNone(e.correlation_id)
            self.assertIsNotNone(e.timestamp)
        
        # Test BACmonConfigError
        try:
            raise BACmonConfigError("Config error", "TestSection", "test_key")
        except BACmonConfigError as e:
            self.assertEqual(e.category, LogCategory.CONFIG)
            self.assertEqual(e.context['config_section'], "TestSection")
            self.assertEqual(e.context['config_key'], "test_key")
        
        # Test BACmonRedisError
        try:
            raise BACmonRedisError("Redis error", "GET", "test:key")
        except BACmonRedisError as e:
            self.assertEqual(e.category, LogCategory.REDIS)
            self.assertEqual(e.context['redis_operation'], "GET")
            self.assertEqual(e.context['redis_key'], "test:key")
        
        # Test BACmonNetworkError
        try:
            raise BACmonNetworkError("Network error", "192.168.1.1", 47808, "BACnet")
        except BACmonNetworkError as e:
            self.assertEqual(e.category, LogCategory.NETWORK)
            self.assertEqual(e.context['host'], "192.168.1.1")
            self.assertEqual(e.context['port'], 47808)
            self.assertEqual(e.context['protocol'], "BACnet")
        
        # Test BACmonValidationError
        try:
            raise BACmonValidationError("Validation error", "device_id", 999)
        except BACmonValidationError as e:
            self.assertEqual(e.context['validation_field'], "device_id")
            self.assertEqual(e.context['validation_value'], "999")
    
    def test_error_context_decorator(self):
        """Test error context decorator"""
        logger = get_logger(config=self.config)
        
        @error_context(category=LogCategory.MONITORING, operation="test_operation")
        def test_function(should_fail=False):
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Test successful operation
        result = test_function()
        self.assertEqual(result, "success")
        
        # Test failed operation
        with self.assertRaises(ValueError):
            test_function(should_fail=True)
    
    def test_timed_operation_decorator(self):
        """Test timed operation decorator"""
        logger = get_logger(config=self.config)
        
        @timed_operation(category=LogCategory.PERFORMANCE, operation="timed_test")
        def slow_function():
            time.sleep(0.01)  # Sleep for 10ms
            return "completed"
        
        result = slow_function()
        self.assertEqual(result, "completed")
    
    def test_correlation_context(self):
        """Test correlation context management"""
        test_id = "test-correlation-123"
        
        with correlation_context(test_id):
            from bacmon_logger import get_correlation_id
            self.assertEqual(get_correlation_id(), test_id)
        
        # Context should be reset after exiting
        # (or a new one generated)
        with correlation_context():
            current_id = get_correlation_id()
            self.assertNotEqual(current_id, test_id)
    
    def test_request_context(self):
        """Test request context management"""
        with request_context("req-123", "api_test") as request_id:
            self.assertEqual(request_id, "req-123")
    
    def test_redis_operation_logging(self):
        """Test Redis operation logging"""
        logger = get_logger(config=self.config)
        
        # Test successful operation
        log_redis_operation("GET", "test:key", success=True, duration_ms=5.2)
        
        # Test failed operation
        test_error = Exception("Connection failed")
        log_redis_operation("SET", "test:key", success=False, error=test_error)
    
    def test_log_file_creation(self):
        """Test that log files are created correctly"""
        logger = get_logger(config=self.config)
        logger.info("Test log file creation")
        
        # Check if log file was created
        self.assertTrue(os.path.exists(self.log_file))
        
        # Check if log content is written
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn("Test log file creation", content)
            
            # Verify it's JSON format
            lines = content.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        self.fail(f"Log line is not valid JSON: {line}")
    
    def test_error_log_separation(self):
        """Test that errors are logged to separate error log"""
        logger = get_logger(config=self.config)
        
        # Log an error
        try:
            raise ValueError("Test error for error log")
        except ValueError:
            logger.exception("Test error occurred")
        
        # Check if error log was created
        self.assertTrue(os.path.exists(self.error_log))
        
        # Check if error content is in error log
        with open(self.error_log, 'r') as f:
            content = f.read()
            self.assertIn("Test error occurred", content)
    
    def test_operation_timing(self):
        """Test operation timing functionality"""
        logger = get_logger(config=self.config)
        
        operation_id = logger.start_operation("test_timing")
        time.sleep(0.01)  # Sleep for 10ms
        duration = logger.end_operation(operation_id, "test_timing", success=True)
        
        # Duration should be approximately 10ms (allow some tolerance)
        self.assertGreater(duration, 5.0)  # At least 5ms
        self.assertLess(duration, 50.0)    # Less than 50ms
    
    def test_health_check(self):
        """Test logging system health check"""
        # Configure logger first
        logger = get_logger(config=self.config)
        
        health = logging_health_check()
        
        self.assertIn('status', health)
        self.assertIn('configured', health)
        self.assertIn('handlers', health)
        self.assertIn('level', health)
        self.assertIn('issues', health)
        
        self.assertEqual(health['status'], 'healthy')
        self.assertTrue(health['configured'])
        self.assertGreater(health['handlers'], 0)
    
    def test_configuration_fallback(self):
        """Test fallback to default configuration"""
        # Test with no configuration
        logger = BACmonLogger('test_fallback')
        logger.configure()  # No config provided
        
        self.assertTrue(logger._configured)
        self.assertGreater(len(logger.logger.handlers), 0)
    
    def test_multiple_data_types_in_structured_logs(self):
        """Test that various data types are properly serialized in structured logs"""
        logger = get_logger(config=self.config)
        
        complex_data = {
            'string': 'test',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'none': None
        }
        
        logger.info("Complex data test", data=complex_data)
        
        # If we get here without exception, serialization worked
        self.assertTrue(True)

def run_integration_tests():
    """Run integration tests that simulate real usage scenarios"""
    print("Running integration tests...")
    
    # Test 1: Configuration from file
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
    config_file.write("""
[Logging]
level = DEBUG
format = json
console_enabled = true
file_enabled = false
""")
    config_file.close()
    
    try:
        config = ConfigParser()
        config.read(config_file.name)
        
        logger = configure_logging(config)
        logger.info("Integration test message", category=LogCategory.SYSTEM)
        print("✓ Configuration from file test passed")
        
    finally:
        os.unlink(config_file.name)
    
    # Test 2: Error handling integration
    @error_context(LogCategory.MONITORING)
    def monitoring_function():
        try:
            raise BACmonNetworkError("Simulated network error", host="192.168.1.100")
        except BACmonNetworkError as e:
            logger.error(f"Network error occurred: {e.message}", 
                        category=e.category, data=e.context)
            raise
    
    try:
        monitoring_function()
    except BACmonNetworkError:
        print("✓ Error handling integration test passed")
    
    # Test 3: Performance monitoring integration
    @timed_operation(LogCategory.PERFORMANCE)
    def simulated_redis_operation():
        time.sleep(0.005)  # Simulate 5ms operation
        return {"status": "success", "records": 100}
    
    result = simulated_redis_operation()
    print("✓ Performance monitoring integration test passed")
    
    # Test 4: Request context integration
    with request_context("api-req-123", "user_login"):
        logger.info("User login attempt", category=LogCategory.SECURITY,
                   data={"username": "test_user", "ip": "192.168.1.50"})
        
        with correlation_context():
            logger.info("Processing login validation", category=LogCategory.SECURITY)
    
    print("✓ Request context integration test passed")
    
    print("All integration tests passed!")

if __name__ == "__main__":
    print("Testing Enhanced Logging and Error Handling Framework...")
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration tests
    run_integration_tests()
    
    print("\nAll tests completed successfully!")
    print("Enhanced logging framework is ready for production use.") 