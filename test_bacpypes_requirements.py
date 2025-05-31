#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for BACpypes requirements verification

This script verifies that the BACpypes libraries are correctly installed
and compatible with Python 3.9.2. It checks versions, dependencies,
and basic functionality of both bacpypes and bacpypes3 libraries.
"""

import sys
import logging
import importlib
import platform
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_bacpypes_requirements')

def check_python_version() -> bool:
    """Check if Python version is compatible."""
    logger.info("Testing Python version compatibility...")
    
    python_version = platform.python_version()
    major, minor, patch = python_version.split('.')
    
    logger.info(f"Python version: {python_version}")
    logger.info(f"Python implementation: {platform.python_implementation()}")
    
    # Check if version is 3.9 or higher (required for bacpypes 0.19.0)
    if int(major) >= 3 and int(minor) >= 9:
        logger.info("✓ Python version is compatible with latest BACpypes libraries")
        return True
    else:
        logger.error(f"✗ Python {python_version} may not be compatible with latest BACpypes")
        return False

def check_library_installation(library_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if a library is installed and get its version."""
    try:
        module = importlib.import_module(library_name)
        version = getattr(module, '__version__', 'Unknown')
        
        # Get module file location
        module_file = getattr(module, '__file__', 'Unknown')
        
        logger.info(f"✓ {library_name} is installed")
        logger.info(f"  Version: {version}")
        logger.info(f"  Location: {module_file}")
        
        return True, version, module_file
    except ImportError as e:
        logger.warning(f"✗ {library_name} is not installed: {e}")
        return False, None, None

def test_bacpypes_imports() -> bool:
    """Test basic imports from bacpypes."""
    logger.info("Testing bacpypes imports...")
    
    try:
        # Test critical imports from bacpypes
        from bacpypes.debugging import bacpypes_debugging, ModuleLogger
        from bacpypes.consolelogging import ConsoleLogHandler
        from bacpypes.core import run, deferred
        from bacpypes.task import RecurringTask
        from bacpypes.comm import PDU, Client, bind
        from bacpypes.udp import UDPDirector
        from bacpypes.pdu import Address, LocalBroadcast
        from bacpypes.bvll import BVLPDU, bvl_pdu_types
        from bacpypes.npdu import NPDU, npdu_types
        from bacpypes.apdu import APDU, ConfirmedRequestPDU
        
        logger.info("✓ All critical bacpypes imports successful")
        return True
    except ImportError as e:
        logger.error(f"✗ bacpypes import failed: {e}")
        return False

def test_bacpypes3_imports() -> bool:
    """Test basic imports from bacpypes3."""
    logger.info("Testing bacpypes3 imports...")
    
    try:
        # Test only the modules that actually exist in bacpypes3
        from bacpypes3.debugging import bacpypes_debugging as function_debugging
        from bacpypes3.debugging import ModuleLogger, LoggingFormatter
        from bacpypes3.comm import Client, bind
        from bacpypes3.pdu import PDU, Address, LocalBroadcast
        from bacpypes3.ipv4 import IPv4DatagramServer
        from bacpypes3.npdu import NPDU, WhoIsRouterToNetwork
        from bacpypes3.apdu import APDU, ConfirmedRequestPDU
        
        logger.info("✓ All available bacpypes3 modules imported successfully")
        
        # Note: bacpypes3 doesn't have bvll, core, or task modules
        # These are handled through the compatibility layer
        logger.info("  Note: core and task functionality accessed via compatibility layer")
        
        return True
    except ImportError as e:
        logger.error(f"✗ bacpypes3 import failed: {e}")
        return False

def test_compatibility_layer() -> bool:
    """Test the compatibility layer imports and functions."""
    logger.info("Testing BACmon compatibility layer...")
    
    try:
        # Test compatibility layer import
        from bacpypes_compat import (
            set_bacpypes_version, BACPYPES_AVAILABLE, BACPYPES3_AVAILABLE,
            get_debugging, get_console_logging, get_core, get_task,
            get_comm, get_udp, get_pdu, get_bvll, get_npdu, get_apdu
        )
        
        logger.info("✓ Compatibility layer imports successful")
        logger.info(f"  bacpypes available: {BACPYPES_AVAILABLE}")
        logger.info(f"  bacpypes3 available: {BACPYPES3_AVAILABLE}")
        
        # Test switching between versions
        if BACPYPES_AVAILABLE:
            set_bacpypes_version(False)  # Use bacpypes
            logger.info("✓ Successfully set to use bacpypes")
            
        if BACPYPES3_AVAILABLE:
            set_bacpypes_version(True)   # Use bacpypes3
            logger.info("✓ Successfully set to use bacpypes3")
            
        # Reset to default (bacpypes)
        if BACPYPES_AVAILABLE:
            set_bacpypes_version(False)
            logger.info("✓ Reset to default bacpypes configuration")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Compatibility layer import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Compatibility layer test failed: {e}")
        return False

def verify_latest_versions() -> Dict[str, bool]:
    """Verify that installed versions are the latest available."""
    logger.info("Verifying installed versions are latest...")
    
    results = {}
    
    # Expected latest versions (as of verification date)
    expected_versions = {
        'bacpypes': '0.19.0',
        'bacpypes3': '0.0.102'
    }
    
    for library, expected_version in expected_versions.items():
        installed, version, _ = check_library_installation(library)
        
        if installed and version:
            if version == expected_version:
                logger.info(f"✓ {library} {version} is the latest version")
                results[library] = True
            else:
                logger.warning(f"! {library} {version} may not be the latest (expected {expected_version})")
                results[library] = False
        else:
            logger.error(f"✗ {library} is not installed")
            results[library] = False
    
    return results

def check_dependencies() -> bool:
    """Check that all required dependencies are available."""
    logger.info("Checking dependencies...")
    
    required_deps = ['six', 'pytz']
    optional_deps = ['lxml', 'simplejson']
    
    all_good = True
    
    for dep in required_deps:
        installed, version, _ = check_library_installation(dep)
        if not installed:
            logger.error(f"✗ Required dependency {dep} is missing")
            all_good = False
        else:
            logger.info(f"✓ Required dependency {dep} {version} is available")
    
    for dep in optional_deps:
        installed, version, _ = check_library_installation(dep)
        if installed:
            logger.info(f"✓ Optional dependency {dep} {version} is available")
        else:
            logger.warning(f"! Optional dependency {dep} is not installed")
    
    return all_good

def run_comprehensive_test() -> bool:
    """Run all verification tests."""
    logger.info("Starting comprehensive BACpypes requirements verification...")
    logger.info("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Python version compatibility
    if not check_python_version():
        all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test 2: Library installations
    bacpypes_installed, bacpypes_version, _ = check_library_installation('bacpypes')
    bacpypes3_installed, bacpypes3_version, _ = check_library_installation('bacpypes3')
    
    if not (bacpypes_installed or bacpypes3_installed):
        logger.error("✗ Neither bacpypes nor bacpypes3 is installed!")
        all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test 3: Library imports
    if bacpypes_installed:
        if not test_bacpypes_imports():
            all_tests_passed = False
    
    if bacpypes3_installed:
        if not test_bacpypes3_imports():
            all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test 4: Compatibility layer
    if not test_compatibility_layer():
        all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test 5: Version verification
    version_results = verify_latest_versions()
    if not all(version_results.values()):
        logger.warning("Some libraries may not be at the latest version")
        # Don't fail the test for this, just warn
    
    logger.info("-" * 40)
    
    # Test 6: Dependencies
    if not check_dependencies():
        all_tests_passed = False
    
    logger.info("=" * 60)
    
    if all_tests_passed:
        logger.info("SUCCESS: All BACpypes requirements verification tests passed!")
        logger.info("The system is ready for BACnet operations with Python 3.9.2")
    else:
        logger.error("FAILURE: Some BACpypes requirements verification tests failed!")
        logger.error("Please address the issues above before proceeding")
    
    return all_tests_passed

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 