#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the BACmon configuration validation framework.
"""

import os
import sys
import unittest
import tempfile
from typing import Dict, Any

# Import the validation framework
from config_validator import (
    ConfigValidator, ConfigValidationError, create_bacmon_validator,
    NetworkInterfaceValidator, BACnetAddressValidator, BACnetBBMDValidator,
    RedisHostValidator, PortValidator, RedisDatabaseValidator, RedisPasswordValidator, 
    RedisTimeoutValidator
)

class TestConfigValidator(unittest.TestCase):
    """Test cases for the configuration validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = create_bacmon_validator()
        
        # Sample valid configuration
        self.valid_config = {
            "BACmon": {
                "interface": "eth0",
                "address": "192.168.1.100/24",
                "bbmd": "192.168.1.1",
                "logdir": "/tmp/bacmon/logs",
                "logdirsize": "16106127360",
                "rollover": "1h",
                "apachedir": "/tmp/bacmon/apache",
                "staticdir": "/tmp/bacmon/static",
                "templatedir": "/tmp/bacmon/template"
            },
            "Redis": {
                "host": "localhost",
                "port": "6379",
                "db": "0",
                "socket_timeout": "5",
                "socket_connect_timeout": "5",
                "health_check_interval": "30"
            }
        }
        
        # Prepare a flat config for individual validator tests
        self.flat_config = {}
        for section, params in self.valid_config.items():
            for param, value in params.items():
                self.flat_config[f"{section}.{param}"] = value
    
    def test_bacnet_address_validator(self):
        """Test the BACnet address validator."""
        validator = BACnetAddressValidator("address")
        
        # Valid addresses
        self.assertTrue(validator.validate("192.168.1.100/24", self.flat_config)[0])
        self.assertTrue(validator.validate("10.0.0.1/8", self.flat_config)[0])
        self.assertTrue(validator.validate("172.16.0.1/16", self.flat_config)[0])
        
        # Invalid addresses
        self.assertFalse(validator.validate("192.168.1.100", self.flat_config)[0])  # No CIDR
        self.assertFalse(validator.validate("192.168.1.100/33", self.flat_config)[0])  # Invalid mask
        self.assertFalse(validator.validate("192.168.1.300/24", self.flat_config)[0])  # Invalid IP
        self.assertFalse(validator.validate("not-an-ip/24", self.flat_config)[0])  # Not an IP
        
        # Public IP warning
        result = validator.validate("8.8.8.8/24", self.flat_config)
        self.assertTrue(result[0])  # Valid but with warning
        self.assertIn("Warning", result[1])  # Should contain a warning
    
    def test_bacnet_bbmd_validator(self):
        """Test the BACnet BBMD validator."""
        validator = BACnetBBMDValidator("bbmd")
        
        # Valid BBMD settings
        self.assertTrue(validator.validate("192.168.1.1", self.flat_config)[0])
        self.assertTrue(validator.validate("192.168.1.1 192.168.1.2", self.flat_config)[0])
        self.assertTrue(validator.validate(["192.168.1.1", "192.168.1.2"], self.flat_config)[0])
        
        # Invalid BBMD settings
        self.assertFalse(validator.validate("", self.flat_config)[0])  # Empty
        self.assertFalse(validator.validate("not-an-ip", self.flat_config)[0])  # Not an IP
        
        # Check network consistency
        test_config = self.flat_config.copy()
        test_config["BACmon.address"] = "10.0.0.1/8"
        result = validator.validate("192.168.1.1", test_config)
        self.assertFalse(result[0])  # Different network
        self.assertIn("not on the same network", result[1])
    
    def test_redis_host_validator(self):
        """Test the Redis host validator."""
        validator = RedisHostValidator("host", check_connection=False)  # Don't check connection for tests
        
        # Valid hosts
        self.assertTrue(validator.validate("localhost", self.flat_config)[0])
        self.assertTrue(validator.validate("127.0.0.1", self.flat_config)[0])
        self.assertTrue(validator.validate("redis-server", self.flat_config)[0])
        
        # Invalid hosts
        self.assertFalse(validator.validate("invalid-host-name-with-illegal-character$", self.flat_config)[0])
        self.assertFalse(validator.validate("too-long." + "a" * 70 + ".com", self.flat_config)[0])
    
    def test_redis_port_validator(self):
        """Test the Redis port validator."""
        validator = PortValidator("port")
        
        # Valid ports
        self.assertTrue(validator.validate(6379, self.flat_config)[0])
        self.assertTrue(validator.validate("6379", self.flat_config)[0])
        self.assertTrue(validator.validate(1, self.flat_config)[0])
        self.assertTrue(validator.validate(65535, self.flat_config)[0])
        
        # Invalid ports
        self.assertFalse(validator.validate(0, self.flat_config)[0])
        self.assertFalse(validator.validate(65536, self.flat_config)[0])
        self.assertFalse(validator.validate("not-a-port", self.flat_config)[0])
    
    def test_redis_database_validator(self):
        """Test the Redis database validator."""
        validator = RedisDatabaseValidator("db")
        
        # Valid databases
        self.assertTrue(validator.validate(0, self.flat_config)[0])
        self.assertTrue(validator.validate("0", self.flat_config)[0])
        self.assertTrue(validator.validate(15, self.flat_config)[0])
        
        # Invalid databases
        self.assertFalse(validator.validate(-1, self.flat_config)[0])
        self.assertFalse(validator.validate(16, self.flat_config)[0])
        self.assertFalse(validator.validate("not-a-db", self.flat_config)[0])
    
    def test_redis_timeout_validator(self):
        """Test the Redis timeout validator."""
        validator = RedisTimeoutValidator("timeout")
        
        # Valid timeouts
        self.assertTrue(validator.validate(0, self.flat_config)[0])  # Infinite
        self.assertTrue(validator.validate("5", self.flat_config)[0])
        self.assertTrue(validator.validate(60, self.flat_config)[0])
        
        # Warnings but still valid
        result = validator.validate(0.05, self.flat_config)
        self.assertTrue(result[0])
        self.assertIn("Warning", result[1])  # Should contain a warning about short timeout
        
        result = validator.validate(600, self.flat_config)
        self.assertTrue(result[0])
        self.assertIn("Warning", result[1])  # Should contain a warning about long timeout
        
        # Invalid timeouts
        self.assertFalse(validator.validate(-1, self.flat_config)[0])
        self.assertFalse(validator.validate("not-a-timeout", self.flat_config)[0])
    
    def test_full_config_validation(self):
        """Test validation of the complete configuration."""
        results = self.validator.validate_config(self.valid_config)
        
        # The overall validation should pass
        self.assertTrue(self.validator.is_valid(results))
        
        # Introduce errors and check validation fails
        invalid_config = self.valid_config.copy()
        invalid_config["BACmon"] = self.valid_config["BACmon"].copy()
        invalid_config["BACmon"]["address"] = "invalid-address"
        
        results = self.validator.validate_config(invalid_config)
        self.assertFalse(self.validator.is_valid(results))
    
    def test_config_file_validation(self):
        """Test validation of a configuration file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("[BACmon]\n")
            temp_file.write("interface = eth0\n")
            temp_file.write("address = 192.168.1.100/24\n")
            temp_file.write("bbmd = 192.168.1.1\n")
            temp_file.write("logdir = /tmp/bacmon/logs\n")
            temp_file.write("logdirsize = 16106127360\n")
            temp_file.write("rollover = 1h\n")
            temp_file.write("apachedir = /tmp/bacmon/apache\n")
            temp_file.write("staticdir = /tmp/bacmon/static\n")
            temp_file.write("templatedir = /tmp/bacmon/template\n")
            temp_file.write("\n")
            temp_file.write("[Redis]\n")
            temp_file.write("host = localhost\n")
            temp_file.write("port = 6379\n")
            temp_file.write("db = 0\n")
            
            temp_file_path = temp_file.name
        
        try:
            # Test validation
            results = self.validator.validate_config_file(temp_file_path)
            self.assertTrue(self.validator.is_valid(results))
            
            # Test with an invalid file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as invalid_file:
                invalid_file.write("[BACmon]\n")
                invalid_file.write("interface = eth0\n")
                invalid_file.write("address = invalid-address\n")  # Invalid address
                
                invalid_file_path = invalid_file.name
            
            try:
                results = self.validator.validate_config_file(invalid_file_path)
                self.assertFalse(self.validator.is_valid(results))
            finally:
                os.unlink(invalid_file_path)
            
        finally:
            os.unlink(temp_file_path)

    def test_bacmon_validation():
        """Test BACmon configuration validation."""
        validator = create_bacmon_validator()
        
        # Valid configuration
        config = {
            "BACmon": {
                "interface": "eth0",
                "address": "192.168.1.100/24",
                "bbmd": "192.168.1.1",
                "logdir": "/tmp/logs",
                "logdirsize": "16106127360",
                "rollover": "1h",
                "apachedir": "/tmp/apache",
                "staticdir": "/tmp/static",
                "templatedir": "/tmp/template"
            }
        }
        results = validator.validate_config(config)
        
        # All values should be valid
        assert validator.is_valid(results)
        
        # Test invalid interface
        config["BACmon"]["interface"] = ""
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Reset interface and test invalid address
        config["BACmon"]["interface"] = "eth0"
        config["BACmon"]["address"] = "invalid-address"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)

    def test_redis_validation():
        """Test Redis configuration validation."""
        validator = create_bacmon_validator()
        
        # Valid configuration
        config = {
            "Redis": {
                "host": "localhost",
                "port": "6379",
                "db": "0",
                "socket_timeout": "5.0",
                "socket_connect_timeout": "5.0"
            }
        }
        results = validator.validate_config(config)
        
        # All values should be valid
        assert validator.is_valid(results)
        
        # Test invalid port
        config["Redis"]["port"] = "invalid"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid db
        config["Redis"]["port"] = "6379"
        config["Redis"]["db"] = "-1"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)

    def test_rate_monitoring_validation():
        """Test rate monitoring configuration validation."""
        validator = create_bacmon_validator()
        
        # Valid configuration
        config = {
            "RateMonitoring": {
                "total_rate": "total:s, 1, 20, 30",
                "ip_specific_rate": "192.168.1.100:s, 1, 10, 30",
                "scan_interval": "10000"
            }
        }
        results = validator.validate_config(config)
        
        # All values should be valid
        assert validator.is_valid(results)
        
        # Test invalid rate threshold format
        config["RateMonitoring"]["total_rate"] = "total:s, 1, 20"  # missing duration
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid scan interval
        config["RateMonitoring"]["total_rate"] = "total:s, 1, 20, 30"
        config["RateMonitoring"]["scan_interval"] = "invalid"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)

    def test_enhanced_detection_validation():
        """Test enhanced anomaly detection configuration validation."""
        validator = create_bacmon_validator()
        
        # Valid configuration with enhanced detection
        config = {
            "RateMonitoring": {
                "total_rate": "total:s, 1, 20, 30",
                "use_enhanced_detection": "true",
                "sensitivity": "1.5",
                "spike_sensitivity": "2.5",
                "z_threshold": "3.0",
                "trend_threshold": "0.2",
                "hour_granularity": "2"
            }
        }
        results = validator.validate_config(config)
        
        # All values should be valid
        assert validator.is_valid(results)
        
        # Test invalid sensitivity (out of range)
        config["RateMonitoring"]["sensitivity"] = "0.05"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid spike sensitivity (out of range)
        config["RateMonitoring"]["sensitivity"] = "1.5"
        config["RateMonitoring"]["spike_sensitivity"] = "0.5"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid z_threshold (out of range)
        config["RateMonitoring"]["spike_sensitivity"] = "2.5"
        config["RateMonitoring"]["z_threshold"] = "0.5"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid trend_threshold (out of range)
        config["RateMonitoring"]["z_threshold"] = "3.0"
        config["RateMonitoring"]["trend_threshold"] = "1.5"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test invalid hour_granularity (out of range)
        config["RateMonitoring"]["trend_threshold"] = "0.2"
        config["RateMonitoring"]["hour_granularity"] = "24"
        results = validator.validate_config(config)
        assert not validator.is_valid(results)
        
        # Test multiple parameter validation
        config["RateMonitoring"] = {
            "total_rate": "total:s, 1, 20, 30",
            "use_enhanced_detection": "true",
            "sensitivity": "1.5",
            "spike_sensitivity": "2.5",
            "z_threshold": "3.0",
            "trend_threshold": "0.2",
            "hour_granularity": "2"
        }
        results = validator.validate_config(config)
        assert validator.is_valid(results)

    def test_rate_monitoring_section_required_rates():
        """Test that at least one rate threshold is required in RateMonitoring section."""
        validator = create_bacmon_validator()
        
        # Valid configuration with at least one rate
        config = {
            "RateMonitoring": {
                "total_rate": "total:s, 1, 20, 30",
                "scan_interval": "10000"
            }
        }
        results = validator.validate_config(config)
        assert validator.is_valid(results)
        
        # Invalid configuration with no rates
        config = {
            "RateMonitoring": {
                "scan_interval": "10000",
                "use_enhanced_detection": "true",
                "sensitivity": "1.5"
            }
        }
        results = validator.validate_config(config)
        assert not validator.is_valid(results)

if __name__ == '__main__':
    unittest.main() 