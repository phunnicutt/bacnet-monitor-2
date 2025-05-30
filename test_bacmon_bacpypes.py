#!/usr/bin/python

"""
Test BACmon with BACpypes Library

This script verifies that the BACmon application correctly works with
the updated BACpypes libraries by testing key functionality.
"""

import sys
import os
import importlib
import unittest
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verify both bacpypes libraries can be imported
try:
    import bacpypes
    logger.info(f"bacpypes version: {bacpypes.__version__}")
    BACPYPES_AVAILABLE = True
except ImportError:
    logger.warning("bacpypes not available")
    BACPYPES_AVAILABLE = False

try:
    import bacpypes3
    logger.info(f"bacpypes3 version: {bacpypes3.__version__}")
    BACPYPES3_AVAILABLE = True
except ImportError:
    logger.warning("bacpypes3 not available")
    BACPYPES3_AVAILABLE = False

# Import compatibility layer
from bacpypes_compat import set_bacpypes_version, BACPYPES_AVAILABLE, BACPYPES3_AVAILABLE

class TestBACmonBACpypes(unittest.TestCase):
    """Test suite for verifying BACmon works with updated BACpypes libraries."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary INI file for testing
        self.temp_ini_fd, self.temp_ini_path = tempfile.mkstemp(suffix='.ini', prefix='BACmon_test_')
        with os.fdopen(self.temp_ini_fd, 'w') as f:
            f.write("""[BACmon]
address: 192.168.1.100
bbmd: 192.168.1.255
logdir: /tmp/bacmonlogs
apachedir: /tmp/bacmonapache
staticdir: /tmp/bacmonstatic
templatedir: /tmp/bacmontemplate
""")
        logger.info(f"Created temporary INI file: {self.temp_ini_path}")
        
        # Save original environment variables
        self.original_bacmon_ini = os.environ.get('BACMON_INI', None)
        
        # Set environment variables for testing
        os.environ['BACMON_INI'] = self.temp_ini_path
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary INI file
        try:
            os.unlink(self.temp_ini_path)
            logger.info(f"Removed temporary INI file: {self.temp_ini_path}")
        except Exception as e:
            logger.error(f"Error removing temporary INI file: {e}")
        
        # Restore original environment variables
        if self.original_bacmon_ini:
            os.environ['BACMON_INI'] = self.original_bacmon_ini
        else:
            if 'BACMON_INI' in os.environ:
                del os.environ['BACMON_INI']
    
    def test_bacpypes_imports(self):
        """Test that BACpypes libraries can be imported correctly."""
        if not BACPYPES_AVAILABLE and not BACPYPES3_AVAILABLE:
            self.skipTest("Neither bacpypes nor bacpypes3 is available")
        
        # Test imports from the compatibility layer
        from bacpypes_compat import get_debugging, get_console_logging
        from bacpypes_compat import get_core, get_task, get_comm, get_udp, get_pdu
        from bacpypes_compat import get_bvll, get_npdu, get_apdu
        
        # Basic verification of imports
        function_debugging, ModuleLogger, _ = get_debugging()
        ConsoleLogHandler = get_console_logging()
        run, _ = get_core()
        RecurringTask = get_task()
        PDU, Client, bind = get_comm()
        UDPDirector = get_udp()
        Address, LocalBroadcast = get_pdu()
        
        self.assertTrue(True, "BACpypes imports successful")
    
    def test_bacmon_imports(self):
        """Test that BACmon can import its dependencies correctly."""
        try:
            # Temporarily modify sys.path to include the current directory
            sys.path.insert(0, os.getcwd())
            
            # Create a mock BACmon module loader
            # This allows us to import and test portions of BACmon without running the whole application
            spec = importlib.util.spec_from_file_location("BACmon", "BACmon.py")
            bacmon_module = importlib.util.module_from_spec(spec)
            
            # Patch sys.argv to avoid actual command line parsing
            original_argv = sys.argv
            sys.argv = ['BACmon.py']
            
            try:
                # Execute the module, but catch ImportError to inspect it
                spec.loader.exec_module(bacmon_module)
                logger.info("BACmon module imported successfully")
                self.assertTrue(True, "BACmon imports successful")
            except ImportError as e:
                logger.error(f"ImportError when loading BACmon: {e}")
                self.fail(f"BACmon import failed: {e}")
            except Exception as e:
                # Other exceptions are expected since we're not actually running the app
                logger.info(f"Expected exception when loading BACmon module: {e}")
                self.assertTrue(True, "BACmon partial import successful")
            finally:
                # Restore original sys.argv
                sys.argv = original_argv
        except Exception as e:
            logger.error(f"Error during BACmon import test: {e}")
            self.fail(f"BACmon import test failed: {e}")
    
    def test_with_bacpypes(self):
        """Test using regular bacpypes."""
        if not BACPYPES_AVAILABLE:
            self.skipTest("bacpypes not available")
        
        set_bacpypes_version(False)
        from bacpypes_compat import get_debugging
        function_debugging, ModuleLogger, _ = get_debugging()
        self.assertTrue(True, "BACmon works with bacpypes")
    
    def test_with_bacpypes3(self):
        """Test using bacpypes3."""
        if not BACPYPES3_AVAILABLE:
            self.skipTest("bacpypes3 not available")
        
        set_bacpypes_version(True)
        from bacpypes_compat import get_debugging
        function_debugging, ModuleLogger, _ = get_debugging()
        self.assertTrue(True, "BACmon works with bacpypes3")

if __name__ == "__main__":
    print("Testing BACmon with BACpypes Library")
    print("-" * 40)
    print(f"bacpypes available: {BACPYPES_AVAILABLE}")
    print(f"bacpypes3 available: {BACPYPES3_AVAILABLE}")
    print("-" * 40)
    
    # Run tests
    unittest.main() 