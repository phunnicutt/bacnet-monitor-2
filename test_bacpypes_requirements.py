#!/usr/bin/python

"""
Test BACpypes Requirements Compatibility

This script verifies that the versions specified in requirements.txt
are compatible with our compatibility layer.
"""

import sys
import pkg_resources

def check_package_version(package_name):
    """Check if a package is installed and get its version."""
    try:
        package = pkg_resources.get_distribution(package_name)
        print(f"{package_name}: {package.version} (installed)")
        return True, package.version
    except pkg_resources.DistributionNotFound:
        print(f"{package_name}: Not installed")
        return False, None

def main():
    """Main test function."""
    print("Testing BACpypes Requirements Compatibility")
    print("-" * 40)
    
    # Check BACpypes libraries
    bacpypes_available, bacpypes_version = check_package_version("bacpypes")
    bacpypes3_available, bacpypes3_version = check_package_version("bacpypes3")
    
    if not bacpypes_available and not bacpypes3_available:
        print("\nERROR: Neither bacpypes nor bacpypes3 is installed!")
        return False
        
    # Import our compatibility module to test it with installed versions
    try:
        print("\nTesting compatibility layer with installed versions...")
        from bacpypes_compat import set_bacpypes_version, get_debugging, get_console_logging
        
        # Test with regular bacpypes if available
        if bacpypes_available:
            print("\nTesting with bacpypes...")
            set_bacpypes_version(False)
            function_debugging, ModuleLogger, _ = get_debugging()
            ConsoleLogHandler = get_console_logging()
            print("Basic bacpypes imports succeeded!")
        
        # Test with bacpypes3 if available
        if bacpypes3_available:
            print("\nTesting with bacpypes3...")
            set_bacpypes_version(True)
            function_debugging, ModuleLogger, _ = get_debugging()
            ConsoleLogHandler = get_console_logging()
            print("Basic bacpypes3 imports succeeded!")
            
        print("\nAll compatibility tests passed!")
        return True
    except Exception as e:
        print(f"\nERROR: Compatibility layer test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 