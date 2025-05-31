#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BACmon Configuration Helper

This module provides utilities for validating and generating BACmon configuration.
"""

import sys
import os
import re
import subprocess
from functools import reduce
from typing import Dict, Any, Optional, Tuple, List, Union

# Import the validation framework
try:
    from config_validator import create_bacmon_validator, ConfigValidationError
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False

# version
__version__ = '1.1.0'

# defaults
BACMON_HOME = '/home/bacmon'
BACMON_INI = BACMON_HOME + '/BACmon.ini'
BACMON_INTERFACE = 'eth0'
BACMON_ADDRESS = None
BACMON_BBMD = None
BACMON_LOGDIR = BACMON_HOME + '/logs'
BACMON_LOGDIRSIZE = 16106127360
BACMON_ROLLOVER = '1h'
BACMON_APACHEDIR = BACMON_HOME + '/apache2'
BACMON_STATICDIR = BACMON_HOME + '/static'
BACMON_TEMPLATEDIR = BACMON_HOME + '/template'

# configuration file template, INI format
CONFIG_FILE_TEMPLATE = """[BACmon]
interface: %(interface)s
address: %(address)s
bbmd: %(bbmd)s
logdir: %(logdir)s
logdirsize: %(logdirsize)s
rollover: %(rollover)s
apachedir: %(apachedir)s
staticdir: %(staticdir)s
templatedir: %(templatedir)s
"""

# apache site configuration file template
APACHE_FILE_TEMPLATE = """<VirtualHost *:80>
    ServerAdmin webmaster@localhost

    WSGIScriptAlias / %(home)s/BACmonWSGI.py

    ErrorLog %(apachedir)s/error.log

    # Possible values include: debug, info, notice, warn, error, crit,
    # alert, emerg.
    LogLevel warn

    CustomLog %(apachedir)s/access.log combined
</VirtualHost>"""

# rollover value pattern
rollover_re = re.compile("^[0-9]+[mhd]?$")
ipv4_address_re = re.compile("^[0-9]+.[0-9]+.[0-9]+.[0-9]+$")

#
#   bit_count
#

def bit_count(i):
    """ Count the number of bits turned on. """
    assert 0 <= i < 0x100000000
    i = i - ((i >> 1) & 0x55555555)
    i = (i & 0x33333333) + ((i >> 2) & 0x33333333)
    return (((i + (i >> 4) & 0xF0F0F0F) * 0x1010101) & 0xffffffff) >> 24


def validate_config_file(config_file: str, verbose: bool = True) -> Tuple[bool, str]:
    """
    Validate a BACmon configuration file using the validation framework.
    
    Args:
        config_file: Path to the configuration file
        verbose: Whether to print validation results
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not VALIDATION_AVAILABLE:
        return True, "Validation framework not available"
    
    try:
        validator = create_bacmon_validator()
        results = validator.validate_config_file(config_file)
        
        if verbose:
            validator.print_results(results)
        
        is_valid = validator.is_valid(results)
        message = validator.format_results(results)
        
        return is_valid, message
    except ConfigValidationError as e:
        if verbose:
            print(f"Error: {str(e)}")
        return False, str(e)


def load_config(config_file: str = BACMON_INI, validate: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Load a BACmon configuration file and optionally validate it.
    
    Args:
        config_file: Path to the configuration file
        validate: Whether to validate the configuration
        
    Returns:
        Configuration dictionary with sections
        
    Raises:
        ConfigValidationError: If validation fails and validate is True
    """
    try:
        # Python 3 ConfigParser import
        from configparser import ConfigParser
        
        # Load configuration
        config_parser = ConfigParser()
        if not config_parser.read(config_file):
            raise Exception(f"Cannot read configuration file: {config_file}")
        
        # Convert to dictionary
        config = {}
        for section in config_parser.sections():
            config[section] = {}
            for option in config_parser.options(section):
                config[section][option] = config_parser.get(section, option)
        
        # Validate if requested and framework is available
        if validate and VALIDATION_AVAILABLE:
            validator = create_bacmon_validator()
            results = validator.validate_config_file(config_file)
            
            if not validator.is_valid(results):
                error_message = validator.format_results(results)
                raise ConfigValidationError(f"Configuration validation failed:\n{error_message}")
        
        return config
    except Exception as e:
        if isinstance(e, ConfigValidationError):
            raise
        else:
            raise Exception(f"Error loading configuration file: {str(e)}")


def get_config_value(config: Dict[str, Dict[str, Any]], section: str, option: str, default: Any = None) -> Any:
    """
    Get a value from the configuration dictionary.
    
    Args:
        config: Configuration dictionary
        section: Section name
        option: Option name
        default: Default value if option is not found
        
    Returns:
        Configuration value or default
    """
    try:
        return config[section][option]
    except KeyError:
        return default


def save_config(config: Dict[str, Dict[str, Any]], config_file: str = BACMON_INI, validate: bool = True) -> bool:
    """
    Save a configuration dictionary to a file.
    
    Args:
        config: Configuration dictionary
        config_file: Path to the configuration file
        validate: Whether to validate the configuration before saving
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ConfigValidationError: If validation fails and validate is True
    """
    try:
        # Validate if requested and framework is available
        if validate and VALIDATION_AVAILABLE:
            validator = create_bacmon_validator()
            results = validator.validate_config(config)
            
            if not validator.is_valid(results):
                error_message = validator.format_results(results)
                raise ConfigValidationError(f"Configuration validation failed:\n{error_message}")
        
        # Python 3 ConfigParser import
        from configparser import ConfigParser
        
        # Create configuration parser
        config_parser = ConfigParser()
        
        # Add sections and options
        for section, options in config.items():
            config_parser.add_section(section)
            for option, value in options.items():
                config_parser.set(section, option, str(value))
        
        # Write to file
        with open(config_file, 'w') as f:
            config_parser.write(f)
        
        return True
    except Exception as e:
        if isinstance(e, ConfigValidationError):
            raise
        else:
            sys.stderr.write(f"Error saving configuration file: {str(e)}\n")
            return False


#
#   __main__
#

if __name__ == "__main__":
    try:
        sys.stdout.write("BACmon Configuration Helper, %s\n" % (__version__,))

        if len(sys.argv) > 1 and sys.argv[1] == "--validate":
            # Just validate an existing configuration file
            if len(sys.argv) > 2:
                config_file = sys.argv[2]
            else:
                config_file = BACMON_INI
            
            is_valid, message = validate_config_file(config_file)
            
            if is_valid:
                sys.stdout.write("Configuration is valid.\n")
                sys.exit(0)
            else:
                sys.stderr.write("Configuration validation failed:\n")
                sys.stderr.write(message + "\n")
                sys.exit(1)

        # building a dict of parameters to pass to the template
        config_parameters = {'home': BACMON_HOME}

        # figure out what interface to use
        interfaces = []
        for fn in os.listdir('/sys/class/net'):
            if fn == 'lo': continue
            interfaces.append(fn)

        if not interfaces:
            sys.stdout.write("No network interfaces found, using 'eth0'.\n")
            BACMON_INTERFACE = 'eth0'
        elif len(interfaces) == 1:
            BACMON_INTERFACE = interfaces[0]
        else:
            # prompt for a selection
            sys.stdout.write("The following interfaces were found:\n")
            for i, fn in enumerate(interfaces):
                sys.stdout.write("    %d: %s\n" % (i, fn))
            i = input("Select the interface to use (0-%d): " % (len(interfaces)-1))
            if i and i.isdigit() and int(i) >= 0 and int(i) < len(interfaces):
                BACMON_INTERFACE = interfaces[int(i)]
        sys.stdout.write("Using %s\n" % (BACMON_INTERFACE,))

        # get the configuration as presented by /sbin/ifconfig
        process = subprocess.Popen(['/sbin/ifconfig'], stdout=subprocess.PIPE)
        ifconfig_data = process.stdout.read().decode('utf-8')

        address = None
        address_ip, address_network = None, None

        # first, look for the configuration specific to BACMON_INTERFACE
        address_pattern = re.compile(r'inet addr:(\d+\.\d+\.\d+\.\d+)')
        mask_pattern = re.compile(r'Mask:(\d+\.\d+\.\d+\.\d+)')

        address = '10.0.0.95/24'
        sys.stdout.write("Using address: %s\n" % (address,))
        address_ip, mask_bits = address.split('/')

        # convert the ip address to a list of integers
        address_octets = [int(x) for x in address_ip.split('.')]
        if len(address_octets) != 4:
            sys.stderr.write("Error: Not an IPv4 address.\n")
            sys.exit(1)

        # convert to an integer
        address_int = reduce(lambda a, b: (a << 8) + b, address_octets)

        # figure out the network
        mask_bits = int(mask_bits)
        if (mask_bits < 0) or (mask_bits > 32):
            sys.stderr.write("Error: Not a valid netmask.\n")
            sys.exit(1)
        network_int = address_int & ~((1 << (32 - mask_bits)) - 1)

        # build the broadcast address
        bbmd_int = network_int | ((1 << (32 - mask_bits)) - 1)

        # convert back to ip address format
        bbmd_octets = [ ((bbmd_int >> i) & 0xFF) for i in (24, 16, 8, 0) ]
        bbmd = '.'.join(str(i) for i in bbmd_octets)

        # start with the given BBMD
        config_parameters['bbmd'] = bbmd
        if mask_bits > 24:
            sys.stdout.write("Small subnet, using %s\n" % (bbmd,))
        else:
            sys.stdout.write("Using %s as the BBMD\n" % (bbmd,))
            bbmd_ip = input("Press <ENTER> to accept or enter another address: ")
            if bbmd_ip:
                bbmd = bbmd_ip

        # make sure this is an IP address
        bbmd_octets = [int(x) for x in bbmd.split('.')]
        if len(bbmd_octets) != 4:
            sys.stderr.write("Error: Not an IPv4 address\n")
            sys.exit(1)

        # reduce to an integer, check for validity
        bbmd_int = reduce(lambda a, b: (a << 8) + b, bbmd_octets)
        if (bbmd_int & network_int) != network_int:
            sys.stderr.write("Warning: broadcast address not on the same network.\n")

        config_parameters['interface'] = BACMON_INTERFACE
        config_parameters['address'] = address

        # ask about the rollover
        rollover = BACMON_ROLLOVER
        while True:
            sys.stdout.write("\nRollover? [%s] " % (rollover,))
            ans = sys.stdin.readline()[:-1]
            if ans:
                rollover = ans

            if not rollover_re.match(rollover):
                sys.stderr.write("Invalid rollover format\n")
                continue

            # acceptable rollover value provided
            break

        # save the parameter
        config_parameters['rollover'] = rollover

        # ask about the log directory
        logdir = BACMON_LOGDIR
        sys.stdout.write("\nLog directory? [%s] " % (logdir,))
        ans = sys.stdin.readline()[:-1]
        if ans:
            logdir = ans

        # save the parameter
        config_parameters['logdir'] = logdir

        # ask about the log directory
        logdirsize = BACMON_LOGDIRSIZE
        sys.stdout.write("\nLog directory size? [%s] " % (logdirsize,))
        ans = sys.stdin.readline()[:-1]
        if ans:
            logdirsize = ans

        # save the parameter
        config_parameters['logdirsize'] = logdirsize

        # ask about the static directory
        apachedir = BACMON_APACHEDIR
        sys.stdout.write("\nApache log directory? [%s] " % (apachedir,))
        ans = sys.stdin.readline()[:-1]
        if ans:
            apachedir = ans

        # save the parameter
        config_parameters['apachedir'] = apachedir

        # ask about the static directory
        staticdir = BACMON_STATICDIR
        sys.stdout.write("\nStatic directory? [%s] " % (staticdir,))
        ans = sys.stdin.readline()[:-1]
        if ans:
            staticdir = ans

        # save the parameter
        config_parameters['staticdir'] = staticdir

        # ask about the template directory
        templatedir = BACMON_TEMPLATEDIR
        sys.stdout.write("\nTemplate directory? [%s] " % (templatedir,))
        ans = sys.stdin.readline()[:-1]
        if ans:
            templatedir = ans

        # save the parameter
        config_parameters['templatedir'] = templatedir

        # now generate the INI file
        config_file = open("bacmon_ini", 'w')
        config_file.write(CONFIG_FILE_TEMPLATE % config_parameters)
        config_file.close()

        # now generate the apache site file
        apache_file = open("bacmon_apache_wsgi", 'w')
        apache_file.write(APACHE_FILE_TEMPLATE % config_parameters)
        apache_file.close()

        # Validate the generated configuration if validation framework is available
        if VALIDATION_AVAILABLE:
            sys.stdout.write("\nValidating generated configuration...\n")
            
            # Create a config dictionary for validation
            config = {
                "BACmon": {
                    "interface": config_parameters['interface'],
                    "address": config_parameters['address'],
                    "bbmd": config_parameters['bbmd'],
                    "logdir": config_parameters['logdir'],
                    "logdirsize": config_parameters['logdirsize'],
                    "rollover": config_parameters['rollover'],
                    "apachedir": config_parameters['apachedir'],
                    "staticdir": config_parameters['staticdir'],
                    "templatedir": config_parameters['templatedir']
                }
            }
            
            validator = create_bacmon_validator()
            results = validator.validate_config(config)
            
            if validator.is_valid(results):
                sys.stdout.write("Configuration is valid.\n")
            else:
                sys.stderr.write("Warning: Generated configuration has validation issues:\n")
                sys.stderr.write(validator.format_results(results) + "\n")

    except Exception as err:
        sys.stderr.write("an error has occurred: %s\n" % (err,))
        sys.exit(1)

