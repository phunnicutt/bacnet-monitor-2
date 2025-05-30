#!/usr/bin/python

"""
BACpypes Compatibility Module

This module provides compatibility functions and imports for both bacpypes and bacpypes3 libraries.
The application will prefer bacpypes by default, but can fall back to bacpypes3 when necessary.
"""

import sys
import importlib.util
from typing import Any, Dict, List, Tuple, Optional, Union, Callable, Type, TypeVar, cast, Set

# Determine which BACpypes library is available
BACPYPES3_AVAILABLE = importlib.util.find_spec("bacpypes3") is not None
BACPYPES_AVAILABLE = importlib.util.find_spec("bacpypes") is not None

# Set default preference (can be overridden by configuration)
USE_BACPYPES3 = False

# Debug flag
_debug = 0

def set_bacpypes_version(use_bacpypes3: bool = False) -> None:
    """Set which BACpypes library version to use."""
    global USE_BACPYPES3
    
    if use_bacpypes3 and not BACPYPES3_AVAILABLE:
        raise ImportError("bacpypes3 requested but not available")
    if not use_bacpypes3 and not BACPYPES_AVAILABLE:
        if BACPYPES3_AVAILABLE:
            print("Warning: bacpypes not available, falling back to bacpypes3")
            use_bacpypes3 = True
        else:
            raise ImportError("Neither bacpypes nor bacpypes3 is available")
    
    USE_BACPYPES3 = use_bacpypes3

def get_debugging() -> Tuple[Callable, Any, Any]:
    """Import and return debugging modules from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.debugging import bacpypes_debugging as function_debugging
        from bacpypes3.debugging import ModuleLogger, LoggingFormatter, DebugContents
        return function_debugging, ModuleLogger, DebugContents
    else:
        from bacpypes.debugging import Logging, function_debugging, ModuleLogger, DebugContents
        return function_debugging, ModuleLogger, DebugContents

def get_console_logging() -> Any:
    """Import and return console logging handler from the appropriate library."""
    if USE_BACPYPES3:
        # In bacpypes3, the console logging functionality is implemented differently
        # We'll create a simple adapter that mimics the bacpypes ConsoleLogHandler
        import logging
        from bacpypes3.debugging import LoggingFormatter
        
        class ConsoleLogHandler(logging.StreamHandler):
            """A simple adapter that mimics the bacpypes ConsoleLogHandler behavior."""
            def __init__(self, loggerName: Optional[str] = None) -> None:
                logging.StreamHandler.__init__(self)
                
                # use the same formatter as bacpypes3
                self.setFormatter(LoggingFormatter())
                
                # attach to the logger
                if loggerName:
                    logger = logging.getLogger(loggerName)
                    logger.addHandler(self)
                    logger.setLevel(logging.DEBUG)
        
        return ConsoleLogHandler
    else:
        from bacpypes.consolelogging import ConsoleLogHandler
        return ConsoleLogHandler

def get_core() -> Tuple[Callable, Any]:
    """Import and return core components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.core import run, deferred
        return run, deferred
    else:
        from bacpypes.core import run, deferred
        return run, deferred

def get_task() -> Any:
    """Import and return task components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.task import RecurringTask
        return RecurringTask
    else:
        from bacpypes.task import RecurringTask
        return RecurringTask

def get_comm() -> Tuple[Any, Any, Any]:
    """Import and return communication components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.comm import Client, bind
        from bacpypes3.pdu import PDU
        return PDU, Client, bind
    else:
        from bacpypes.comm import PDU, Client, bind
        return PDU, Client, bind

def get_udp() -> Any:
    """Import and return UDP components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.ipv4 import IPv4DatagramServer
        return IPv4DatagramServer  # UDPDirector equivalent in bacpypes3
    else:
        from bacpypes.udp import UDPDirector
        return UDPDirector

def get_pdu() -> Tuple[Any, Any]:
    """Import and return PDU components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.pdu import Address, LocalBroadcast
        return Address, LocalBroadcast
    else:
        from bacpypes.pdu import Address, LocalBroadcast
        return Address, LocalBroadcast

def get_bvll() -> Tuple[Any, Dict[int, Any], Any, Any, Any, Any, Any, Any]:
    """Import and return BVLL components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.bvll import BVLPDU, RegisterForeignDevice, DeleteForeignDeviceTableEntry
        from bacpypes3.bvll import OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU
        from bacpypes3.bvll import DistributeBroadcastToNetwork
        
        # In bacpypes3, we need to manually create the bvl_pdu_types dictionary
        bvl_pdu_types: Dict[int, Any] = {
            0x00: OriginalUnicastNPDU,
            0x01: OriginalBroadcastNPDU,
            0x02: ForwardedNPDU,
            0x03: RegisterForeignDevice,
            0x04: DeleteForeignDeviceTableEntry,
            0x05: DistributeBroadcastToNetwork,
        }
        
        return (BVLPDU, bvl_pdu_types, RegisterForeignDevice, 
                DeleteForeignDeviceTableEntry, OriginalUnicastNPDU, 
                OriginalBroadcastNPDU, ForwardedNPDU, DistributeBroadcastToNetwork)
    else:
        from bacpypes.bvll import BVLPDU, bvl_pdu_types, RegisterForeignDevice
        from bacpypes.bvll import DeleteForeignDeviceTableEntry
        from bacpypes.bvll import OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU
        from bacpypes.bvll import DistributeBroadcastToNetwork
        
        return (BVLPDU, bvl_pdu_types, RegisterForeignDevice, 
                DeleteForeignDeviceTableEntry, OriginalUnicastNPDU, 
                OriginalBroadcastNPDU, ForwardedNPDU, DistributeBroadcastToNetwork)

def get_npdu() -> Tuple[Any, Dict[int, Any], Any, Any, Any, Any, Any, Any, Any, Any]:
    """Import and return NPDU components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.npdu import NPDU, WhoIsRouterToNetwork, IAmRouterToNetwork
        from bacpypes3.npdu import ICouldBeRouterToNetwork, RejectMessageToNetwork
        from bacpypes3.npdu import RouterBusyToNetwork, RouterAvailableToNetwork
        from bacpypes3.npdu import EstablishConnectionToNetwork, DisconnectConnectionToNetwork
        
        # In bacpypes3, we need to manually create the npdu_types dictionary
        npdu_types: Dict[int, Any] = {
            0x00: WhoIsRouterToNetwork,
            0x01: IAmRouterToNetwork,
            0x02: ICouldBeRouterToNetwork,
            0x03: RejectMessageToNetwork,
            0x04: RouterBusyToNetwork,
            0x05: RouterAvailableToNetwork,
            0x06: EstablishConnectionToNetwork,
            0x07: DisconnectConnectionToNetwork,
        }
        
        return (NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
                ICouldBeRouterToNetwork, RejectMessageToNetwork,
                RouterBusyToNetwork, RouterAvailableToNetwork,
                EstablishConnectionToNetwork, DisconnectConnectionToNetwork)
    else:
        from bacpypes.npdu import NPDU, npdu_types
        from bacpypes.npdu import WhoIsRouterToNetwork, IAmRouterToNetwork
        from bacpypes.npdu import ICouldBeRouterToNetwork, RejectMessageToNetwork
        from bacpypes.npdu import RouterBusyToNetwork, RouterAvailableToNetwork
        from bacpypes.npdu import EstablishConnectionToNetwork, DisconnectConnectionToNetwork
        
        return (NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
                ICouldBeRouterToNetwork, RejectMessageToNetwork,
                RouterBusyToNetwork, RouterAvailableToNetwork,
                EstablishConnectionToNetwork, DisconnectConnectionToNetwork)

def get_apdu() -> Tuple[Any, Dict[int, Any], Dict[int, Any], Dict[int, Any], Dict[int, Any], Dict[int, Any], Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]:
    """Import and return APDU components from the appropriate library."""
    if USE_BACPYPES3:
        from bacpypes3.apdu import APDU, ConfirmedRequestPDU, UnconfirmedRequestPDU
        from bacpypes3.apdu import SimpleAckPDU, ComplexAckPDU, SegmentAckPDU
        from bacpypes3.apdu import ErrorPDU, RejectPDU, AbortPDU
        from bacpypes3.apdu import WhoIsRequest, IAmRequest, WhoHasRequest
        from bacpypes3.apdu import IHaveRequest, UnconfirmedEventNotificationRequest
        from bacpypes3.apdu import UnconfirmedCOVNotificationRequest
        
        # In bacpypes3, we need to manually create these dictionaries
        from bacpypes3.pdu import PDUData
        
        # Using simplified dictionaries for compatibility
        apdu_types: Dict[int, Any] = {
            0: ConfirmedRequestPDU,
            1: UnconfirmedRequestPDU,
            2: SimpleAckPDU,
            3: ComplexAckPDU,
            4: SegmentAckPDU,
            5: ErrorPDU,
            6: RejectPDU,
            7: AbortPDU
        }
        
        confirmed_request_types: Dict[int, Any] = {
            0: None,  # placeholder
            8: WhoIsRequest,
            # other types can be added as needed
        }
        
        unconfirmed_request_types: Dict[int, Any] = {
            0: IAmRequest,
            1: IHaveRequest,
            2: UnconfirmedEventNotificationRequest,
            3: UnconfirmedCOVNotificationRequest,
            # other types can be added as needed
        }
        
        complex_ack_types: Dict[int, Any] = {}  # placeholder
        error_types: Dict[int, Any] = {}  # placeholder
        
        return (APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
                complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
                SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
                WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
                UnconfirmedEventNotificationRequest, UnconfirmedCOVNotificationRequest)
    else:
        from bacpypes.apdu import APDU, apdu_types, confirmed_request_types
        from bacpypes.apdu import unconfirmed_request_types, complex_ack_types, error_types
        from bacpypes.apdu import ConfirmedRequestPDU, UnconfirmedRequestPDU
        from bacpypes.apdu import SimpleAckPDU, ComplexAckPDU, SegmentAckPDU
        from bacpypes.apdu import ErrorPDU, RejectPDU, AbortPDU
        from bacpypes.apdu import WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest
        from bacpypes.apdu import UnconfirmedEventNotificationRequest
        from bacpypes.apdu import UnconfirmedCOVNotificationRequest
        
        return (APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
                complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
                SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
                WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
                UnconfirmedEventNotificationRequest, UnconfirmedCOVNotificationRequest) 