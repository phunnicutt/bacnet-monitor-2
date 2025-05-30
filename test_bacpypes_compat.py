#!/usr/bin/python

"""
Test BACpypes Compatibility Module
"""

import sys
from typing import Any, Dict, List, Tuple, Optional, Union, Callable, Type, Set, cast

# Import our compatibility module
from bacpypes_compat import set_bacpypes_version, get_debugging, get_console_logging
from bacpypes_compat import get_core, get_task, get_comm, get_udp, get_pdu
from bacpypes_compat import get_bvll, get_npdu, get_apdu
from bacpypes_compat import BACPYPES_AVAILABLE, BACPYPES3_AVAILABLE

# Function to test the compatibility layer
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
    test_bacpypes_compat() 