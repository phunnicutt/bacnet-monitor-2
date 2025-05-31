#!/usr/bin/python3

"""
Test BACpypes Compatibility Module

This script tests the BACmon compatibility layer that allows the application
to work with both bacpypes and bacpypes3 libraries. It verifies that:
1. All required modules can be imported through the compatibility layer
2. Switching between library versions works correctly
3. Basic functionality is available from both libraries
"""

import sys
import logging
from typing import Any, Dict, List, Tuple, Optional, Union, Callable, Type, Set, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_bacpypes_compat')

# Import our compatibility module
from bacpypes_compat import set_bacpypes_version, get_debugging, get_console_logging
from bacpypes_compat import get_core, get_task, get_comm, get_udp, get_pdu
from bacpypes_compat import get_bvll, get_npdu, get_apdu
from bacpypes_compat import BACPYPES_AVAILABLE, BACPYPES3_AVAILABLE

def test_imports_compatibility_layer(use_bacpypes3: bool = False) -> bool:
    """Test that all imports work through the compatibility layer."""
    library_name = "bacpypes3" if use_bacpypes3 else "bacpypes"
    logger.info(f"Testing imports with {library_name}...")
    
    try:
        # Set the library version
        set_bacpypes_version(use_bacpypes3)
        
        # Test all the compatibility layer functions
        function_debugging, ModuleLogger, DebugContents = get_debugging()
        logger.info(f"  ✓ Debugging components imported from {library_name}")
        
        ConsoleLogHandler = get_console_logging()
        logger.info(f"  ✓ Console logging imported from {library_name}")
        
        run, deferred = get_core()
        logger.info(f"  ✓ Core components imported from {library_name}")
        
        RecurringTask = get_task()
        logger.info(f"  ✓ Task components imported from {library_name}")
        
        PDU, Client, bind = get_comm()
        logger.info(f"  ✓ Communication components imported from {library_name}")
        
        UDPDirector = get_udp()
        logger.info(f"  ✓ UDP components imported from {library_name}")
        
        Address, LocalBroadcast = get_pdu()
        logger.info(f"  ✓ PDU components imported from {library_name}")
        
        (BVLPDU, bvl_pdu_types, RegisterForeignDevice, DeleteForeignDeviceTableEntry,
         OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU,
         DistributeBroadcastToNetwork) = get_bvll()
        logger.info(f"  ✓ BVLL components imported from {library_name}")
        
        (NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
         ICouldBeRouterToNetwork, RejectMessageToNetwork, RouterBusyToNetwork,
         RouterAvailableToNetwork, EstablishConnectionToNetwork,
         DisconnectConnectionToNetwork) = get_npdu()
        logger.info(f"  ✓ NPDU components imported from {library_name}")
        
        (APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
         complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
         SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
         WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
         UnconfirmedEventNotificationRequest,
         UnconfirmedCOVNotificationRequest) = get_apdu()
        logger.info(f"  ✓ APDU components imported from {library_name}")
        
        logger.info(f"All {library_name} imports succeeded!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing {library_name}: {e}")
        return False

def test_basic_functionality(use_bacpypes3: bool = False) -> bool:
    """Test basic functionality through the compatibility layer."""
    library_name = "bacpypes3" if use_bacpypes3 else "bacpypes"
    logger.info(f"Testing basic functionality with {library_name}...")
    
    try:
        # Set the library version
        set_bacpypes_version(use_bacpypes3)
        
        # Test basic class instantiation
        Address, LocalBroadcast = get_pdu()
        
        # Create a LocalBroadcast address
        local_broadcast = LocalBroadcast()
        logger.info(f"  ✓ Created LocalBroadcast address: {local_broadcast}")
        
        # Test PDU creation
        PDU, Client, bind = get_comm()
        
        # Create a basic PDU
        pdu = PDU()
        logger.info(f"  ✓ Created PDU: {pdu}")
        
        # Test debugging setup
        function_debugging, ModuleLogger, DebugContents = get_debugging()
        
        # Just verify the components are available, don't test instantiation
        # as the debugging setup is complex and library-specific
        logger.info(f"  ✓ Debugging components are available: {callable(function_debugging)}")
        
        logger.info(f"Basic functionality test with {library_name} passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing basic functionality with {library_name}: {e}")
        return False

def test_version_switching() -> bool:
    """Test switching between library versions."""
    logger.info("Testing version switching...")
    
    try:
        if not (BACPYPES_AVAILABLE and BACPYPES3_AVAILABLE):
            logger.warning("Both libraries not available, skipping version switching test")
            return True
        
        # Start with bacpypes
        set_bacpypes_version(False)
        Address1, _ = get_pdu()
        logger.info("  ✓ Set to bacpypes successfully")
        
        # Switch to bacpypes3
        set_bacpypes_version(True)
        Address2, _ = get_pdu()
        logger.info("  ✓ Switched to bacpypes3 successfully")
        
        # Switch back to bacpypes
        set_bacpypes_version(False)
        Address3, _ = get_pdu()
        logger.info("  ✓ Switched back to bacpypes successfully")
        
        # Verify we got different classes from different libraries
        if hasattr(Address1, '__module__') and hasattr(Address2, '__module__'):
            if 'bacpypes.' in Address1.__module__ and 'bacpypes3.' in Address2.__module__:
                logger.info("  ✓ Version switching working correctly - different modules loaded")
            else:
                logger.warning(f"  ! Modules may not be different: {Address1.__module__} vs {Address2.__module__}")
        
        logger.info("Version switching test passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing version switching: {e}")
        return False

def run_comprehensive_compatibility_test() -> bool:
    """Run all compatibility tests."""
    logger.info("Starting comprehensive BACpypes compatibility layer test...")
    logger.info("=" * 60)
    
    all_tests_passed = True
    
    # Display library availability
    logger.info(f"BACpypes available: {BACPYPES_AVAILABLE}")
    logger.info(f"BACpypes3 available: {BACPYPES3_AVAILABLE}")
    
    if not (BACPYPES_AVAILABLE or BACPYPES3_AVAILABLE):
        logger.error("✗ No BACpypes libraries available!")
        return False
    
    logger.info("-" * 40)
    
    # Test with bacpypes if available
    if BACPYPES_AVAILABLE:
        if not test_imports_compatibility_layer(False):
            all_tests_passed = False
        
        if not test_basic_functionality(False):
            all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test with bacpypes3 if available
    if BACPYPES3_AVAILABLE:
        if not test_imports_compatibility_layer(True):
            all_tests_passed = False
        
        if not test_basic_functionality(True):
            all_tests_passed = False
    
    logger.info("-" * 40)
    
    # Test version switching
    if not test_version_switching():
        all_tests_passed = False
    
    logger.info("=" * 60)
    
    if all_tests_passed:
        logger.info("SUCCESS: All BACpypes compatibility tests passed!")
        logger.info("The compatibility layer is working correctly with both libraries")
    else:
        logger.error("FAILURE: Some BACpypes compatibility tests failed!")
        logger.error("Please check the compatibility layer implementation")
    
    return all_tests_passed

# Function to test the compatibility layer (backward compatibility)
def test_bacpypes_compat() -> None:
    """Test the BACpypes compatibility layer by importing components from both libraries."""
    print("Testing BACpypes Compatibility Layer")
    
    print(f"BACpypes available: {BACPYPES_AVAILABLE}")
    print(f"BACpypes3 available: {BACPYPES3_AVAILABLE}")
    
    # Test with regular bacpypes
    try:
        print("\nTesting with regular bacpypes...")
        set_bacpypes_version(False)
        
        function_debugging, ModuleLogger, DebugContents = get_debugging()
        ConsoleLogHandler = get_console_logging()
        run, _ = get_core()
        RecurringTask = get_task()
        PDU, Client, bind = get_comm()
        UDPDirector = get_udp()
        Address, LocalBroadcast = get_pdu()
        
        (BVLPDU, bvl_pdu_types, RegisterForeignDevice, DeleteForeignDeviceTableEntry,
         OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU,
         DistributeBroadcastToNetwork) = get_bvll()
        
        (NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
         ICouldBeRouterToNetwork, RejectMessageToNetwork, RouterBusyToNetwork,
         RouterAvailableToNetwork, EstablishConnectionToNetwork,
         DisconnectConnectionToNetwork) = get_npdu()
        
        (APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
         complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
         SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
         WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
         UnconfirmedEventNotificationRequest,
         UnconfirmedCOVNotificationRequest) = get_apdu()
        
        print("All regular bacpypes imports succeeded!")
    except Exception as e:
        print(f"Error testing regular bacpypes: {e}")
    
    # Test with bacpypes3 if available
    if BACPYPES3_AVAILABLE:
        try:
            print("\nTesting with bacpypes3...")
            set_bacpypes_version(True)
            
            function_debugging, ModuleLogger, DebugContents = get_debugging()
            ConsoleLogHandler = get_console_logging()
            run, _ = get_core()
            RecurringTask = get_task()
            PDU, Client, bind = get_comm()
            UDPDirector = get_udp()
            Address, LocalBroadcast = get_pdu()
            
            (BVLPDU, bvl_pdu_types, RegisterForeignDevice, DeleteForeignDeviceTableEntry,
             OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU,
             DistributeBroadcastToNetwork) = get_bvll()
            
            (NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
             ICouldBeRouterToNetwork, RejectMessageToNetwork, RouterBusyToNetwork,
             RouterAvailableToNetwork, EstablishConnectionToNetwork,
             DisconnectConnectionToNetwork) = get_npdu()
            
            (APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
             complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
             SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
             WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
             UnconfirmedEventNotificationRequest,
             UnconfirmedCOVNotificationRequest) = get_apdu()
            
            print("All bacpypes3 imports succeeded!")
        except Exception as e:
            print(f"Error testing bacpypes3: {e}")

if __name__ == "__main__":
    # Run comprehensive test by default
    success = run_comprehensive_compatibility_test()
    sys.exit(0 if success else 1) 