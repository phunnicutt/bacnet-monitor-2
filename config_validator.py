#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BACmon Configuration Validation Framework

This module provides a robust validation framework for BACmon configuration settings.
It centralizes all validation logic and provides clear error messages and suggestions
when validation fails.
"""

import os
import re
import sys
import socket
import ipaddress
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

# Version
__version__ = '1.0.0'

# Define validation result type
ValidationResult = Tuple[bool, str]

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    
    def __init__(self, message: str, param_name: Optional[str] = None, suggestion: Optional[str] = None):
        self.message = message
        self.param_name = param_name
        self.suggestion = suggestion
        super().__init__(self.formatted_message())
    
    def formatted_message(self) -> str:
        """Format the error message with parameter name and suggestion if available."""
        msg = self.message
        if self.param_name:
            msg = f"Configuration error for '{self.param_name}': {msg}"
        if self.suggestion:
            msg = f"{msg}\nSuggestion: {self.suggestion}"
        return msg

class Validator:
    """Base validator class for configuration parameters."""
    
    def __init__(self, name: str, required: bool = True, default: Any = None, 
                 description: str = "", depends_on: Optional[List[str]] = None):
        self.name = name
        self.required = required
        self.default = default
        self.description = description
        self.depends_on = depends_on or []
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate the configuration value.
        
        Args:
            value: The value to validate
            config: The entire configuration dictionary for dependency validation
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check if required parameter is missing
        if self.required and value is None:
            return False, f"Required parameter '{self.name}' is missing"
        
        # Use default value if none provided and not required
        if value is None and not self.required:
            return True, f"Using default value: {self.default}"
        
        # Check dependencies
        if self.depends_on:
            for dep in self.depends_on:
                if dep not in config or config[dep] is None:
                    return False, f"Depends on '{dep}' which is missing or invalid"
        
        return True, "Valid"
    
    def __str__(self) -> str:
        req_str = "Required" if self.required else "Optional"
        return f"{self.name} ({req_str}): {self.description}"


class StringValidator(Validator):
    """Validator for string values."""
    
    def __init__(self, name: str, pattern: Optional[str] = None, min_length: int = 0, 
                 max_length: Optional[int] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.pattern = re.compile(pattern) if pattern else None
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Validate string type
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
            
        # Validate string length
        if len(value) < self.min_length:
            return False, f"String is too short (minimum length: {self.min_length})"
        
        if self.max_length is not None and len(value) > self.max_length:
            return False, f"String is too long (maximum length: {self.max_length})"
        
        # Validate pattern if specified
        if self.pattern and not self.pattern.match(value):
            return False, f"String does not match required pattern"
        
        return True, "Valid"


class IntegerValidator(Validator):
    """Validator for integer values."""
    
    def __init__(self, name: str, min_value: Optional[int] = None, 
                 max_value: Optional[int] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Try to convert to integer if it's a string
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                return False, f"Cannot convert '{value}' to an integer"
        
        # Validate integer type
        if not isinstance(value, int):
            return False, f"Expected integer but got {type(value).__name__}"
        
        # Validate range
        if self.min_value is not None and value < self.min_value:
            return False, f"Value {value} is less than minimum {self.min_value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"Value {value} is greater than maximum {self.max_value}"
        
        return True, "Valid"


class BooleanValidator(Validator):
    """Validator for boolean values."""
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Handle string boolean values
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', 'yes', '1', 'y'):
                return True, "Valid (parsed as True)"
            elif value_lower in ('false', 'no', '0', 'n'):
                return True, "Valid (parsed as False)"
            else:
                return False, f"Cannot interpret '{value}' as a boolean"
        
        # Validate boolean type
        if not isinstance(value, bool):
            return False, f"Expected boolean but got {type(value).__name__}"
        
        return True, "Valid"


class IPAddressValidator(Validator):
    """Validator for IP address values."""
    
    def __init__(self, name: str, allow_cidr: bool = False, ipv4_only: bool = True, **kwargs):
        super().__init__(name, **kwargs)
        self.allow_cidr = allow_cidr
        self.ipv4_only = ipv4_only
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        # Handle CIDR notation
        if '/' in value and self.allow_cidr:
            try:
                network = ipaddress.ip_network(value, strict=False)
                if self.ipv4_only and not isinstance(network, ipaddress.IPv4Network):
                    return False, "IPv6 addresses are not supported"
                return True, "Valid CIDR notation"
            except ValueError as e:
                return False, f"Invalid CIDR notation: {str(e)}"
        elif '/' in value and not self.allow_cidr:
            return False, "CIDR notation not allowed for this parameter"
        
        # Handle regular IP address
        try:
            ip = ipaddress.ip_address(value)
            if self.ipv4_only and not isinstance(ip, ipaddress.IPv4Address):
                return False, "IPv6 addresses are not supported"
            return True, "Valid IP address"
        except ValueError as e:
            return False, f"Invalid IP address: {str(e)}"


class DirectoryValidator(Validator):
    """Validator for directory paths."""
    
    def __init__(self, name: str, must_exist: bool = True, create_if_missing: bool = False,
                 require_write: bool = False, **kwargs):
        super().__init__(name, **kwargs)
        self.must_exist = must_exist
        self.create_if_missing = create_if_missing
        self.require_write = require_write
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        # Expand home directory if needed
        if '~' in value:
            value = os.path.expanduser(value)
        
        # Check if directory exists
        if not os.path.exists(value):
            if self.must_exist and not self.create_if_missing:
                return False, f"Directory '{value}' does not exist"
            elif self.create_if_missing:
                try:
                    os.makedirs(value, exist_ok=True)
                    return True, f"Directory '{value}' created"
                except OSError as e:
                    return False, f"Failed to create directory '{value}': {str(e)}"
        
        # Check if it's a directory
        if not os.path.isdir(value):
            return False, f"'{value}' is not a directory"
        
        # Check write permissions if required
        if self.require_write and not os.access(value, os.W_OK):
            return False, f"No write permission for directory '{value}'"
        
        return True, "Valid"


class ListValidator(Validator):
    """Validator for list values with item validation."""
    
    def __init__(self, name: str, item_validator: Validator, 
                 min_length: int = 0, max_length: Optional[int] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.item_validator = item_validator
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Handle space-separated string lists
        if isinstance(value, str):
            value = value.split()
        
        # Validate list type
        if not isinstance(value, (list, tuple)):
            return False, f"Expected list but got {type(value).__name__}"
        
        # Validate list length
        if len(value) < self.min_length:
            return False, f"List is too short (minimum length: {self.min_length})"
        
        if self.max_length is not None and len(value) > self.max_length:
            return False, f"List is too long (maximum length: {self.max_length})"
        
        # Validate each item
        invalid_items = []
        for i, item in enumerate(value):
            item_valid, item_message = self.item_validator.validate(item, config)
            if not item_valid:
                invalid_items.append(f"Item {i}: {item_message}")
        
        if invalid_items:
            return False, "List contains invalid items: " + "; ".join(invalid_items)
        
        return True, "Valid"


class CustomValidator(Validator):
    """Validator using a custom validation function."""
    
    def __init__(self, name: str, validation_func: Callable[[Any, Dict[str, Any]], ValidationResult], **kwargs):
        super().__init__(name, **kwargs)
        self.validation_func = validation_func
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        return self.validation_func(value, config)


class ConfigValidator:
    """
    Main configuration validator class.
    
    This class handles validation of the entire configuration dictionary
    using registered validators for each parameter.
    """
    
    def __init__(self):
        self.validators: Dict[str, Dict[str, Validator]] = {}
        self.section_descriptions: Dict[str, str] = {}
    
    def add_section(self, section: str, description: str = ""):
        """Add a configuration section."""
        if section not in self.validators:
            self.validators[section] = {}
            self.section_descriptions[section] = description
    
    def add_validator(self, section: str, validator: Validator):
        """Add a validator to a configuration section."""
        if section not in self.validators:
            self.add_section(section)
        
        self.validators[section][validator.name] = validator
    
    def validate_config(self, config: Dict[str, Dict[str, Any]]) -> Dict[str, List[Tuple[str, bool, str]]]:
        """
        Validate the complete configuration dictionary.
        
        Args:
            config: Configuration dictionary with sections
            
        Returns:
            Dictionary with validation results by section
        """
        results = {}
        
        # Prepare flat config for dependency checking
        flat_config = {}
        for section, params in config.items():
            for param, value in params.items():
                flat_key = f"{section}.{param}"
                flat_config[flat_key] = value
        
        # Validate each section and parameter
        for section, validators in self.validators.items():
            section_results = []
            
            # Check if section exists
            if section not in config:
                if any(v.required for v in validators.values()):
                    for name, validator in validators.items():
                        if validator.required:
                            section_results.append((
                                name, 
                                False, 
                                f"Required parameter in missing section '{section}'"
                            ))
                continue
            
            # Validate each parameter in the section
            for name, validator in validators.items():
                param_value = config[section].get(name)
                flat_key = f"{section}.{name}"
                
                is_valid, message = validator.validate(param_value, flat_config)
                section_results.append((name, is_valid, message))
                
                # Update flat config with default value if needed
                if param_value is None and not is_valid and validator.default is not None:
                    flat_config[flat_key] = validator.default
            
            results[section] = section_results
        
        return results
    
    def validate_config_file(self, config_file: str) -> Dict[str, List[Tuple[str, bool, str]]]:
        """
        Load and validate a configuration file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Dictionary with validation results by section
        """
        try:
            # Python 3 ConfigParser import
            from configparser import ConfigParser
            
            # Load configuration
            config_parser = ConfigParser()
            if not config_parser.read(config_file):
                raise ConfigValidationError(f"Cannot read configuration file: {config_file}")
            
            # Convert to dictionary
            config = {}
            for section in config_parser.sections():
                config[section] = {}
                for option in config_parser.options(section):
                    config[section][option] = config_parser.get(section, option)
            
            # Validate
            return self.validate_config(config)
            
        except Exception as e:
            raise ConfigValidationError(f"Error validating configuration file: {str(e)}")
    
    def format_results(self, results: Dict[str, List[Tuple[str, bool, str]]]) -> str:
        """Format validation results as a readable string."""
        output = []
        
        for section, section_results in results.items():
            output.append(f"[{section}]")
            if section in self.section_descriptions:
                output.append(f"  Description: {self.section_descriptions[section]}")
            
            valid_count = sum(1 for _, is_valid, _ in section_results if is_valid)
            total_count = len(section_results)
            output.append(f"  Status: {valid_count}/{total_count} parameters valid")
            
            for name, is_valid, message in section_results:
                status = "✓" if is_valid else "✗"
                output.append(f"  {status} {name}: {message}")
            
            output.append("")
        
        return "\n".join(output)
    
    def print_results(self, results: Dict[str, List[Tuple[str, bool, str]]]):
        """Print validation results to stdout."""
        print(self.format_results(results))
    
    def is_valid(self, results: Dict[str, List[Tuple[str, bool, str]]]) -> bool:
        """Check if all validation results are valid."""
        for section_results in results.values():
            for _, is_valid, _ in section_results:
                if not is_valid:
                    return False
        return True


class NetworkInterfaceValidator(Validator):
    """Validator for network interface names."""
    
    def __init__(self, name: str, allow_lo: bool = False, **kwargs):
        super().__init__(name, **kwargs)
        self.allow_lo = allow_lo
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        # Check if interface exists
        try:
            interfaces = os.listdir('/sys/class/net')
            if value not in interfaces:
                return False, f"Network interface '{value}' does not exist on this system"
            
            # Check for loopback interface
            if value == 'lo' and not self.allow_lo:
                return False, f"Loopback interface 'lo' is not allowed for BACnet communication"
            
            return True, "Valid network interface"
        except OSError:
            # If /sys/class/net is not available (non-Linux), skip this check
            return True, f"Network interface validation skipped (not on Linux)"


class BACnetAddressValidator(IPAddressValidator):
    """Validator specifically for BACnet addresses."""
    
    def __init__(self, name: str, **kwargs):
        # BACnet addresses should always be in CIDR notation
        super().__init__(name, allow_cidr=True, ipv4_only=True, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # BACnet address additional checks
        try:
            # Validate CIDR format (already done in super())
            ip_str, mask_str = value.split('/')
            mask_bits = int(mask_str)
            
            # Additional BACnet specific checks
            if mask_bits < 8:
                return False, f"BACnet subnet mask too small: /{mask_bits} (minimum /8 recommended)"
            
            # Check for reserved or special addresses
            ip = ipaddress.ip_address(ip_str)
            
            # Check for private network address (BACnet should typically use private addresses)
            private_ranges = [
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('192.168.0.0/16')
            ]
            
            in_private_range = any(ip in network for network in private_ranges)
            if not in_private_range:
                # This is just a warning, not an error
                return True, "Warning: BACnet address is not in a private IP range"
            
            return True, "Valid BACnet address"
        except ValueError as e:
            return False, f"Invalid BACnet address format: {str(e)}"


class BACnetBBMDValidator(ListValidator):
    """Validator for BBMD (BACnet/IP Broadcast Management Device) addresses."""
    
    def __init__(self, name: str, **kwargs):
        item_validator = IPAddressValidator(
            f"{name}_item",
            description="BBMD IP address",
            allow_cidr=False,
            ipv4_only=True
        )
        super().__init__(name, item_validator=item_validator, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Additional BBMD specific checks
        try:
            # Check if all BBMD addresses are on the same network as the BACnet address
            if 'BACmon.address' in config:
                bacnet_address = config['BACmon.address']
                if bacnet_address and '/' in bacnet_address:
                    bacnet_ip_str, bacnet_mask_str = bacnet_address.split('/')
                    bacnet_network = ipaddress.ip_network(f"{bacnet_ip_str}/{bacnet_mask_str}", strict=False)
                    
                    # Check each BBMD address
                    if isinstance(value, str):
                        bbmd_addresses = value.split()
                    else:
                        bbmd_addresses = value
                    
                    off_network_bbmds = []
                    for i, bbmd in enumerate(bbmd_addresses):
                        bbmd_ip = ipaddress.ip_address(bbmd)
                        if bbmd_ip not in bacnet_network:
                            off_network_bbmds.append(f"{bbmd} (item {i})")
                    
                    if off_network_bbmds:
                        return False, f"BBMD addresses not on the same network as BACnet address: {', '.join(off_network_bbmds)}"
            
            return True, "Valid BBMD addresses"
        except (ValueError, KeyError) as e:
            # Don't fail if we can't perform this check
            return True, f"Note: Could not verify BBMD network consistency: {str(e)}"


class HostnameValidator(Validator):
    """Validator for hostname or IP address."""
    
    def __init__(self, name: str, check_connection: bool = False, 
                 connection_port: Optional[int] = None, connection_timeout: float = 2.0, **kwargs):
        super().__init__(name, **kwargs)
        self.check_connection = check_connection
        self.connection_port = connection_port
        self.connection_timeout = connection_timeout
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        # Check if it's a valid IP address
        try:
            ipaddress.ip_address(value)
            # It's a valid IP address
        except ValueError:
            # Not an IP address, check if it's a valid hostname
            if not self._is_valid_hostname(value):
                return False, f"Invalid hostname: {value}"
        
        # Check connection if requested
        if self.check_connection and self.connection_port:
            if not self._check_connection(value, self.connection_port):
                return False, f"Could not connect to {value}:{self.connection_port}"
        
        return True, "Valid hostname or IP address"
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if a string is a valid hostname."""
        if len(hostname) > 255:
            return False
        
        # Check each label in the hostname
        for label in hostname.split('.'):
            if not label or len(label) > 63:
                return False
            if not all(c.isalnum() or c == '-' for c in label):
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
        
        return True
    
    def _check_connection(self, host: str, port: int) -> bool:
        """Attempt to connect to the host:port to verify it's reachable."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.connection_timeout)
            s.connect((host, port))
            s.close()
            return True
        except (socket.timeout, socket.error):
            return False


class RedisHostValidator(HostnameValidator):
    """Validator specifically for Redis hosts."""
    
    def __init__(self, name: str, **kwargs):
        # Default Redis port is 6379
        super().__init__(name, connection_port=6379, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Check if port is specified separately
        port = 6379  # Default Redis port
        if 'Redis.port' in config:
            try:
                port = int(config['Redis.port'])
            except (ValueError, TypeError):
                pass
        
        # Don't fail validation if we can't connect, just warn
        if self.check_connection:
            if not self._check_connection(value, port):
                return True, f"Warning: Could not connect to Redis at {value}:{port}"
        
        return True, f"Valid Redis host"


class PortValidator(IntegerValidator):
    """Validator for network port numbers."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, min_value=1, max_value=65535, **kwargs)


class RedisPasswordValidator(StringValidator):
    """Validator for Redis password."""
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # No specific rules for Redis passwords, but we could add security recommendations
        if len(value) < 8:
            return True, "Warning: Redis password is short and might not be secure"
        
        return True, "Valid Redis password"


class RedisDatabaseValidator(IntegerValidator):
    """Validator for Redis database numbers."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, min_value=0, max_value=15, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Redis typically supports 16 databases (0-15)
        return True, "Valid Redis database number"


class RedisTimeoutValidator(IntegerValidator):
    """Validator for Redis timeout values."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, min_value=0, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Convert to float if needed
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return False, f"Cannot convert '{value}' to a float"
        
        if value <= 0:
            return False, "Timeout must be greater than 0"
        
        return True, "Valid"


class RateThresholdValidator(Validator):
    """Validator for rate monitoring threshold configurations."""
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        # Parse the rate threshold configuration
        try:
            # Expected format: "key, interval, max_value, duration"
            parts = [part.strip() for part in value.split(',')]
            
            if len(parts) != 4:
                return False, f"Invalid format. Expected 'key, interval, max_value, duration' but got '{value}'"
            
            # Validate key
            key = parts[0]
            if not key:
                return False, "Rate monitoring key cannot be empty"
            
            # Validate interval (must be positive integer)
            interval = int(parts[1])
            if interval <= 0:
                return False, f"Interval must be a positive integer but got {interval}"
            
            # Validate max_value (must be positive integer)
            max_value = int(parts[2])
            if max_value <= 0:
                return False, f"Max value must be a positive integer but got {max_value}"
            
            # Validate duration (must be positive integer)
            duration = int(parts[3])
            if duration <= 0:
                return False, f"Duration must be a positive integer but got {duration}"
            
            return True, "Valid"
            
        except ValueError as e:
            return False, f"Invalid rate threshold configuration: {str(e)}"


class ScanIntervalValidator(IntegerValidator):
    """Validator for rate monitoring scan interval."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, min_value=1000, max_value=60000, **kwargs)
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        # Validate it's in a reasonable range (1-60 seconds in milliseconds)
        value_int = int(value)
        if value_int < 1000:
            return False, f"Scan interval too small: {value_int}ms (minimum 1000ms)"
        if value_int > 60000:
            return False, f"Scan interval too large: {value_int}ms (maximum 60000ms)"
        
        return True, "Valid"


class RateMonitoringValidator(Validator):
    """Validator for RateMonitoring section."""
    
    def __init__(self, name: str = "RateMonitoring", **kwargs):
        super().__init__(name, **kwargs)
        
        # Add validators for scan interval
        self.add_field_validator(
            "scan_interval", 
            IntegerValidator("scan_interval", min_value=1000, max_value=60000)
        )
        
        # Add validators for enhanced detection options
        self.add_field_validator(
            "use_enhanced_detection",
            BooleanValidator("use_enhanced_detection")
        )
        
        # Add validators for sensitivity parameters
        self.add_field_validator(
            "sensitivity",
            FloatValidator("sensitivity", min_value=0.1, max_value=10.0)
        )
        
        self.add_field_validator(
            "spike_sensitivity",
            FloatValidator("spike_sensitivity", min_value=1.0, max_value=10.0)
        )
        
        self.add_field_validator(
            "z_threshold",
            FloatValidator("z_threshold", min_value=1.0, max_value=10.0)
        )
        
        self.add_field_validator(
            "trend_threshold",
            FloatValidator("trend_threshold", min_value=0.05, max_value=1.0)
        )
        
        self.add_field_validator(
            "hour_granularity",
            IntegerValidator("hour_granularity", min_value=1, max_value=12)
        )
        
        # Dynamic validator for rate monitoring thresholds
        self.add_pattern_validator(
            r".*_rate$",
            RateThresholdValidator("rate_threshold")
        )
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        """Validate the RateMonitoring section."""
        is_valid, message = super().validate(value, config)
        
        # Check that at least one rate threshold is defined
        if is_valid and not any(k.endswith('_rate') for k in value):
            is_valid = False
            message = "At least one rate threshold must be defined in [RateMonitoring]"
        
        return is_valid, message


class RedisOptimizationValidator(SectionValidator):
    """Validator for RedisOptimization section."""
    
    def __init__(self, name: str = "RedisOptimization", **kwargs):
        super().__init__(name, **kwargs)
        
        # Basic optimization settings
        self.add_field_validator(
            "enabled",
            BooleanValidator("enabled", default=True)
        )
        
        # Compression settings
        self.add_field_validator(
            "compression_enabled",
            BooleanValidator("compression_enabled", default=True)
        )
        
        self.add_field_validator(
            "compression_level",
            IntegerValidator("compression_level", min_value=1, max_value=9, default=6)
        )
        
        self.add_field_validator(
            "min_compression_size",
            IntegerValidator("min_compression_size", min_value=50, max_value=10000, default=100)
        )
        
        # Cleanup settings
        self.add_field_validator(
            "auto_cleanup_enabled",
            BooleanValidator("auto_cleanup_enabled", default=True)
        )
        
        self.add_field_validator(
            "cleanup_interval_seconds",
            IntegerValidator("cleanup_interval_seconds", min_value=300, max_value=86400, default=3600)
        )
        
        # Memory management
        self.add_field_validator(
            "max_memory_usage_mb",
            IntegerValidator("max_memory_usage_mb", min_value=128, max_value=32768, default=1024)
        )
        
        self.add_field_validator(
            "enable_memory_monitoring",
            BooleanValidator("enable_memory_monitoring", default=True)
        )
        
        # Performance settings
        self.add_field_validator(
            "batch_size",
            IntegerValidator("batch_size", min_value=100, max_value=10000, default=1000)
        )
        
        self.add_field_validator(
            "pipeline_operations",
            BooleanValidator("pipeline_operations", default=True)
        )
        
        # Retention policy validators (optional custom settings)
        self.add_pattern_validator(
            r".*_retention$",
            RetentionPolicyValidator("retention_policy")
        )


class RetentionPolicyValidator(Validator):
    """Validator for custom retention policy configurations."""
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        if not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        
        try:
            # Expected format: "pattern, duration_hours, resolution_seconds, aggregation_func"
            parts = [part.strip().strip('"') for part in value.split(',')]
            
            if len(parts) != 4:
                return False, f"Invalid format. Expected 'pattern, duration_hours, resolution_seconds, aggregation_func' but got '{value}'"
            
            # Validate pattern
            pattern = parts[0]
            if not pattern:
                return False, "Pattern cannot be empty"
            
            # Validate duration_hours (must be positive number)
            duration_hours = float(parts[1])
            if duration_hours <= 0:
                return False, f"Duration must be positive but got {duration_hours}"
            
            # Validate resolution_seconds (must be positive integer)
            resolution_seconds = int(parts[2])
            if resolution_seconds <= 0:
                return False, f"Resolution must be positive but got {resolution_seconds}"
            
            # Validate aggregation function
            aggregation_func = parts[3]
            valid_funcs = ['avg', 'max', 'min', 'sum', 'count', 'first', 'last', 'remove']
            if aggregation_func not in valid_funcs:
                return False, f"Invalid aggregation function '{aggregation_func}'. Valid options: {', '.join(valid_funcs)}"
            
            return True, "Valid"
            
        except ValueError as e:
            return False, f"Invalid retention policy configuration: {str(e)}"


class FloatValidator(Validator):
    """Validator for float values with optional range checking."""
    
    def __init__(self, name: str, min_value: Optional[float] = None, 
                 max_value: Optional[float] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, config: Dict[str, Any]) -> ValidationResult:
        is_valid, message = super().validate(value, config)
        if not is_valid or value is None:
            return is_valid, message
        
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return False, f"Expected float but got {type(value).__name__}"
        
        if self.min_value is not None and float_value < self.min_value:
            return False, f"Value {float_value} is below minimum {self.min_value}"
        
        if self.max_value is not None and float_value > self.max_value:
            return False, f"Value {float_value} is above maximum {self.max_value}"
        
        return True, "Valid"


# Helper function to create a validator for the BACmon.ini file
def create_bacmon_validator() -> ConfigValidator:
    """Create and configure a validator for BACmon configuration."""
    validator = ConfigValidator()
    
    # BACmon section
    bacmon_validator = SectionValidator("BACmon")
    bacmon_validator.add_field_validator("interface", NonEmptyStringValidator("interface"))
    bacmon_validator.add_field_validator("address", IPCIDRValidator("address"))
    bacmon_validator.add_field_validator("bbmd", IPAddressListValidator("bbmd"))
    bacmon_validator.add_field_validator("logdir", DirectoryPathValidator("logdir"))
    bacmon_validator.add_field_validator("logdirsize", IntegerValidator("logdirsize", min_value=1048576))
    bacmon_validator.add_field_validator("rollover", RolloverValidator("rollover"))
    bacmon_validator.add_field_validator("apachedir", DirectoryPathValidator("apachedir"))
    bacmon_validator.add_field_validator("staticdir", DirectoryPathValidator("staticdir"))
    bacmon_validator.add_field_validator("templatedir", DirectoryPathValidator("templatedir"))
    
    validator.add_section_validator(bacmon_validator)
    
    # Redis section
    redis_validator = RedisValidator()
    validator.add_section_validator(redis_validator)
    
    # RedisOptimization section (optional)
    redis_optimization_validator = RedisOptimizationValidator()
    redis_optimization_validator.required = False  # Make this section optional
    validator.add_section_validator(redis_optimization_validator)
    
    # RateMonitoring section
    rate_monitoring_validator = RateMonitoringValidator()
    validator.add_section_validator(rate_monitoring_validator)
    
    return validator


# Simple command line interface
if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "/home/bacmon/BACmon.ini"
    
    try:
        validator = create_bacmon_validator()
        results = validator.validate_config_file(config_file)
        validator.print_results(results)
        
        if not validator.is_valid(results):
            sys.exit(1)
    except ConfigValidationError as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 