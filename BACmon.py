#!/usr/bin/python

"""
BACnet LAN Monitor
"""

import sys
import socket
import time

from time import time as _time

# Import Redis client wrapper instead of direct Redis import
from redis_client import create_redis_client

# Import from the compatibility module instead of directly from bacpypes
from bacpypes_compat import set_bacpypes_version, get_debugging, get_console_logging
from bacpypes_compat import get_core, get_task, get_comm, get_udp, get_pdu
from bacpypes_compat import get_bvll, get_npdu, get_apdu

# Import the anomaly detection module
try:
    import anomaly_detection
    ANOMALY_DETECTION_AVAILABLE = True
except ImportError:
    ANOMALY_DETECTION_AVAILABLE = False

# Import metrics module for extended metrics collection
try:
    import metrics
    import enhanced_rate_monitoring
    EXTENDED_METRICS_AVAILABLE = True
except ImportError:
    EXTENDED_METRICS_AVAILABLE = False

# Initialize bacpypes version (default to bacpypes, will fall back to bacpypes3 if needed)
set_bacpypes_version(False)  # Use bacpypes by default

# Get debugging components
function_debugging, ModuleLogger, Logging = get_debugging()
ConsoleLogHandler = get_console_logging()

# Get core components
run, _ = get_core()
RecurringTask = get_task()

# Get communication components
PDU, Client, bind = get_comm()
UDPDirector = get_udp()

# Get PDU components
Address, LocalBroadcast = get_pdu()

# Get BVLL components
(BVLPDU, bvl_pdu_types, RegisterForeignDevice, DeleteForeignDeviceTableEntry,
 OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU,
 DistributeBroadcastToNetwork) = get_bvll()

# Get NPDU components
(NPDU, npdu_types, WhoIsRouterToNetwork, IAmRouterToNetwork,
 ICouldBeRouterToNetwork, RejectMessageToNetwork, RouterBusyToNetwork,
 RouterAvailableToNetwork, EstablishConnectionToNetwork,
 DisconnectConnectionToNetwork) = get_npdu()

# Get APDU components
(APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
 complex_ack_types, error_types, ConfirmedRequestPDU, UnconfirmedRequestPDU,
 SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU,
 WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest,
 UnconfirmedEventNotificationRequest,
 UnconfirmedCOVNotificationRequest) = get_apdu()

# version
__version__ = '1.0.0'

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   normally in __main__
#

if ('--debug' in sys.argv):
    indx = sys.argv.index('--debug')
    for i in range(indx+1, len(sys.argv)):
        ConsoleLogHandler(sys.argv[i])
    del sys.argv[indx:]

#
#   Configuration File
#

try:
    if _debug: _log.debug("configuration")

    # Python 3 ConfigParser import
    from configparser import ConfigParser

    BACMON_HOME = '/home/bacmon'
    BACMON_INI = BACMON_HOME + '/BACmon.ini'

    # make a device object from a configuration file
    config = ConfigParser()
    config.read(BACMON_INI)

    # load the parameters
    BACMON_ADDRESS = config.get('BACmon', 'address')
    if _debug: _log.debug("    - BACMON_ADDRESS: %r", BACMON_ADDRESS)

    BACMON_BBMD = config.get('BACmon', 'bbmd')
    if _debug: _log.debug("    - BACMON_BBMD: %r", BACMON_BBMD)

except Exception as err:
    sys.stderr.write("configuration error: %s\n" % (err,))
    sys.exit(1)

sys.path.append(BACMON_HOME)
from timeutil import AbsoluteTime, DeltaTime

# connection to Redis
r = None

# the address of the local BBMD(s)
bbmdAddresses = []

# counters
countTime = None
countIntervalParms = (('s', 1, 900), ('m', 60, 1440), ('h', 3600, 168))
countIntervals = []

# samples to get for checking rates
WINDOW_SIZE = 25

# Rate monitoring tasks
rate_tasks = []

#
#   Check
#

@function_debugging
def Check(msg):
    """Make sure that 'msg' will be checked for validity."""
    if _debug: Check._debug("Check %r", msg)

    # add it to the local set of things to check
    r.sadd('check', msg)

#
#   CountInterval
#

class CountInterval(Logging):

    def __init__(self, label, modulus, maxLen):
        if _debug: CountInterval._debug("__init__ %r %r %r", label, modulus, maxLen)

        # save the parameters
        self.label = label
        self.modulus = modulus
        self.maxLen = maxLen

        # a cache of counters for each message
        self.cache = {}

        # last time this interval counted something
        self.lastInterval = 0

    def Count(self, msg):
        if _debug: CountInterval._debug("Count(%s) %r", self.label, msg)

        # build some special keys
        key = msg + ':' + self.label
        keyi = key + 'i'
        keyn = key + 'n'

        # trigger is set to start a new slot
        trigger = False

        # calculate the interval
        interval = countTime - (countTime % self.modulus)
        if _debug: CountInterval._debug("    - interval: %r", interval)

        # if the interval is not the same as the last one, flush the cache
        if (interval != self.lastInterval):
            for xkey, xcount in list(self.cache.items()):
                if _debug: CountInterval._debug("    - push flush: %r [%r, %r]", xkey, self.lastInterval, xcount)
                r.lpush(xkey, str([self.lastInterval, xcount]))
                r.ltrim(xkey, 0, self.maxLen - 1)
                r.delete(xkey + 'i')

            # reset and trigger a new slot
            self.cache = {}
            self.lastInterval = interval
            trigger = True
        else:
            if key in self.cache:
                if _debug: CountInterval._debug("    - key in cache")
                self.cache[key] = r.incr(keyn)
            else:
                # see if it can be gathered from the database
                lasti = r.get(keyi)
                if not lasti:
                    if _debug: CountInterval._debug("    - unseen key")
                    trigger = True
                else:
                    lasti = int(lasti)
                    if interval == lasti:
                        if _debug: CountInterval._debug("    - cache load from database")
                        # increment the database count and cache it
                        self.cache[key] = r.incr(keyn)
                    else:
                        # save the data before starting a new slot
                        count = int(r.get(keyn))
                        if _debug: CountInterval._debug("    - push database: %r [%r, %r]", key, lasti, count)

                        r.lpush(key, str([lasti, count]))
                        r.ltrim(key, 0, self.maxLen - 1)
                        trigger = True

        # if trigger has been set, start a new slot
        if trigger:
            if _debug: CountInterval._debug("    - trigger")
            self.cache[key] = 1
            r.set(keyi, interval)
            r.set(keyn, 1)

#
#   Count
#

@function_debugging
def Count(msg, family=None, packet_info=None):
    """Count the number of times 'msg' has been received and add the key to
    the 'family' of similar keys. Optionally includes additional packet information
    for extended metrics collection."""
    if _debug: Count._debug("Count %r family=%r packet_info=%r", msg, family, packet_info)

    # Pass it to each interval
    for inter in countIntervals:
        # Use the enhanced Count method if available and packet_info is provided
        if EXTENDED_METRICS_AVAILABLE and packet_info is not None and isinstance(inter, enhanced_rate_monitoring.EnhancedCountInterval):
            inter.Count(msg, packet_info)
        else:
            inter.Count(msg)

    # Count the total number of these messages
    if r.incr(msg) == 1:
        Check(msg)

        # Add the message to the family
        if family:
            r.sadd(family, msg)

    # Process packet information for metrics if available
    if EXTENDED_METRICS_AVAILABLE and packet_info is not None:
        # Get the metrics manager
        metrics_manager = metrics.get_metric_manager(r)
        
        # Process the packet
        metrics_manager.process_packet(msg, packet_info)

#
#   SampleRateTask
#

class SampleRateTask(RecurringTask, Logging):

    def __init__(self, key, interval, maxValue, duration):
        if _debug: SampleRateTask._debug("__init__ %r", interval)
        RecurringTask.__init__(self)

        # save the parameters
        self.key = key
        self.interval = interval
        self.maxValue = maxValue
        self.duration = duration

        # the next check should be duration number of intervals ago
        now = int(_time())
        now = now - (now % interval)
        self.nextCheck = now - (interval * duration)

        # initialize alarm state
        activeTime = r.get(self.key + ':alarm')
        if activeTime:
            if _debug: SampleRateTask._debug("    - active since %r", activeTime)
            self.alarm = True
            self.alarmTime = int(activeTime)

            # don't bother checking before the alarm became active
            self.nextCheck = max(self.nextCheck, self.alarmTime)
        else:
            if _debug: SampleRateTask._debug("    - inactive")
            self.alarm = False
            self.alarmTime = None

        self.setCount = 0
        self.resetCount = 0

    def yield_samples(self, st, et):
        """Yield the samples beginning at start time st, ending at end time et, or zero if there aren't any."""
        if _debug: SampleRateTask._debug("yield_samples %r %r", st, et)
        global r, WINDOW_SIZE

        # gather some samples
        samples = r.lrange(self.key, 0, WINDOW_SIZE)

        # reverse the list and split
        samples.reverse()
        samples = [eval(s) for s in samples]

        # loop through them
        nt = st
        for t, v in samples:
            # sample might be too far in the past
            if t < nt:
                continue

            # might be some missing values, assume no packets
            while (nt < t) and (nt <= et):
                yield [nt, 0]
                nt += self.interval

            # don't present more samples than requested
            if nt > et:
                break

            # yield the sample
            yield [nt, v]
            nt += self.interval

    def process_task(self):
        """Check the values to see if it has exceeded maxValue."""
        if _debug: SampleRateTask._debug("ProcessTask")

        # test run
        now = int(_time())
        now = now - (now % self.interval)
        if _debug: SampleRateTask._debug("    - now: %r", now)

        tick = False
        for t, v in self.yield_samples(self.nextCheck, now):
            tick = True
            if self.alarm:
                self.set_mode(t, v)
            else:
                self.reset_mode(t, v)
        if tick:
            self.nextCheck = t + self.interval
        else:
            self.nextCheck = now

    def set_mode(self, t, v):
        """The alarm is active, attempt to reset."""
        if _debug: SampleRateTask._debug("set_mode %r %r", t, v)

        # check to see if the value dropped below the limit
        if (v <= self.maxValue):
            if _debug: SampleRateTask._debug("    - could be")

            self.resetCount += 1
            if (self.resetCount >= self.duration):
                if _debug: SampleRateTask._debug("    - cleared")

                # delete when it became active
                r.delete(self.key + ':alarm')

                # log it in history
                r.lpush(self.key + ':alarm-history', str([self.alarmTime, t]))

                self.alarm = False
                self.setCount = 0
                self.alarmTime = None

        elif self.resetCount:
            if _debug: SampleRateTask._debug("    - never mind")
            self.resetCount = 0

    def reset_mode(self, t, v):
        """The alarm is inactive, attempt to reset."""
        if _debug: SampleRateTask._debug("reset_mode %r %r", t, v)

        # check to see if the value exceeds the limit
        if (v > self.maxValue):
            if _debug: SampleRateTask._debug("    - could be")

            self.setCount += 1
            if (self.setCount >= self.duration):
                if _debug: SampleRateTask._debug("    - in alarm")
                self.alarm = True
                self.alarmTime = t
                self.resetCount = 0

                # save when this happened
                r.set(self.key + ':alarm', t)

                # notify everybody
                msgtxt = "-/" + self.key + "/Rate Exceeded"
                if r.sadd('critical-messages', msgtxt):
                    key, label = self.key.split(':')
                    msg = "%s : Rate of %r has exceeded %dpp%s for %s starting at %s" % \
                        ( socket.gethostname(), key
                        , self.maxValue, label
                        , DeltaTime(self.interval * self.duration)
                        , AbsoluteTime(t)
                        )
                    ### send msg as an SMS message
                    if _debug: SampleRateTask._debug("    - sms msg: %r", msg)

        elif self.setCount:
            if _debug: SampleRateTask._debug("    - never mind")
            self.setCount = 0

#
#   Monitor
#

class Monitor(Client, Logging):

    def confirmation(self, pdu):
        if _debug: Monitor._debug("confirmation %r", pdu)
        global countTime

        # extract packet information for metrics
        packet_info = None
        if EXTENDED_METRICS_AVAILABLE:
            packet_info = {
                'size': len(pdu.pduData) if hasattr(pdu, 'pduData') else 0,
                'protocol': 'bacnet'
            }

        # get the time, count the total number of packets received
        countTime = int(_time())
        Count('total', packet_info=packet_info)

        # update the source and destination
        pdu.pduSource = Address(pdu.pduSource)
        pdu.pduDestination = LocalBroadcast()

        # put in defaults
        pdu.pduExpectingReply = 0
        pdu.pduNetworkPriority = 0

        # count the number of packets from this device
        key = str(pdu.pduSource)
        Count(key, 'ip-traffic', packet_info)

        # check for empty packet
        if not pdu.pduData:
            if _debug: Monitor._debug("    - empty packet: %r", pdu)
            r.sadd('error-traffic', 'empty,' + str(pdu.pduSource) + ',empty packet - expected BVLL header')
            return

        # check for a BVLL header
        if (pdu.pduData[0:1] == b'\x81'):
            if _debug: Monitor._debug("    - BVLL header found")

            # decode the header
            try:
                xpdu = BVLPDU()
                xpdu.decode(pdu)
                pdu = xpdu
            except Exception as err:
                if _debug: Monitor._debug("    - bvll header decoding error: %r", err)
                r.sadd('error-traffic', 'bvll-header,' + str(pdu.pduSource) + ',' + str(err))
                return

            # look up the type
            atype = bvl_pdu_types.get(xpdu.bvlciFunction)
            if not atype:
                if _debug: Monitor._debug("    - unknown bvll function: %r", xpdu)
                r.sadd('error-traffic', 'bvll-type,' + str(pdu.pduSource) + ',' + str(xpdu.bvlciFunction))
                return

            # decode
            try:
                ypdu = atype()
                ypdu.decode(xpdu)
            except Exception as err:
                if _debug: Monitor._debug("    - bvll decoding error: %r", err)
                r.sadd('error-traffic', 'bvll-decoding,' + str(pdu.pduSource) + ',' + str(err))
                return
            if _debug: Monitor._debug("    - ypdu: %r", ypdu)

            # build a description of this packet
            key = ypdu.__class__.__name__ + ',' + str(ypdu.pduSource)
            if atype is ForwardedNPDU:
                # make sure this is from the BBMD
                if not (ypdu.pduSource in bbmdAddresses):
                    msgtxt = str(ypdu.pduSource) + "/" + key + "/Forwarded NPDU from non-BBMD"
                    if r.sadd('critical-messages', msgtxt):
                        msg = socket.gethostname() + " : Forwarded NPDU from " + str(ypdu.pduSource) + ", BBMD is " + ' or '.join(str(addr) for addr in bbmdAddresses)
                        ### send msg as an SMS message
                        if _debug: Monitor._debug("    - sms msg: %r", msg)

                # continue to count these in detail
                key += ',' + str(ypdu.bvlciAddress)

            elif atype is RegisterForeignDevice:
                key += ',' + str(ypdu.bvlciTimeToLive)
            elif atype is DeleteForeignDeviceTableEntry:
                key += ',' + str(ypdu.bvlciAddress)

            # count the number of this kind of BVLL message from this address
            Count(key, 'bvll-traffic', packet_info)

            # no more decoding for these PDUs
            if atype not in (OriginalUnicastNPDU, OriginalBroadcastNPDU, ForwardedNPDU, DistributeBroadcastToNetwork):
                return

            # continue with the rest of the stuff
            pdu = PDU(ypdu.pduData)
            if _debug: Monitor._debug("    - pdu: %r", pdu)

            # carry forward
            if atype is ForwardedNPDU:
                pdu.pduSource = ypdu.bvlciAddress
            else:
                pdu.pduSource = ypdu.pduSource
            pdu.pduDestination = ypdu.pduDestination
            pdu.pduExpectingReply = ypdu.pduExpectingReply
            pdu.pduNetworkPriority = ypdu.pduNetworkPriority

        else:
            if _debug: Monitor._debug("    - non-bvll packet")
            r.sadd('error-traffic', 'non-bvll,' + str(pdu.pduSource))
            return

        # check for empty packet
        if not pdu.pduData:
            if _debug: Monitor._debug("    - empty packet: %r", pdu)
            r.sadd('error-traffic', 'empty,' + str(pdu.pduSource) + ',empty packet - expected NPCI header')
            return

        # check for version number
        if (pdu.pduData[0:1] != b'\x01'):
            if _debug: Monitor._debug("    - not a version 1 packet: %r", pdu)
            r.sadd('error-traffic', 'version,' + str(pdu.pduSource) + ',not version 1 - ' + str(ord(pdu.pduData[0:1])))
            return

        # it's an NPDU
        try:
            npdu = NPDU()
            npdu.decode(pdu)
        except Exception as err:
            if _debug: Monitor._debug("    - NPDU decoding Error: %r", err)
            r.sadd('error-traffic', 'npdu-decoding,' + str(pdu.pduSource))
            return

        if _debug: Monitor._debug("    - npdu: %r", npdu)

        # application or network layer message
        if npdu.npduNetMessage is None:

            # decode as a generic APDU
            try:
                xpdu = APDU()
                xpdu.decode(npdu)
                apdu = xpdu
            except Exception as err:
                if _debug: Monitor._debug("    - decoding Error: %r", err)
                r.sadd('error-traffic', 'apdu-decoding,' + str(pdu.pduSource))
                return

            # "lift" the source and destination address
            if npdu.npduSADR:
                apdu.pduSource = npdu.npduSADR
            else:
                apdu.pduSource = npdu.pduSource
            if npdu.npduDADR:
                apdu.pduDestination = npdu.npduDADR
            else:
                apdu.pduDestination = npdu.pduDestination

            # make a more focused interpretation
            atype = apdu_types.get(apdu.apduType)
            if not atype:
                if _debug: Monitor._debug("    - unknown APDU type: %r", apdu.apduType)
                return

            # decode it as one of the basic types
            try:
                xpdu = apdu
                apdu = atype()
                apdu.decode(xpdu)
            except Exception as err:
                if _debug: Monitor._debug("    - decoding Error: %r", err)
                r.sadd('error-traffic', 'apdu-decoding,' + str(apdu.pduSource))
                return

            # decode it at the next level
            if isinstance(apdu, ConfirmedRequestPDU):
                atype = confirmed_request_types.get(apdu.apduService)
                if not atype:
                    if _debug: Monitor._debug("    - no confirmed request decoder: %r", apdu.apduService)
                    return

            elif isinstance(apdu, UnconfirmedRequestPDU):
                atype = unconfirmed_request_types.get(apdu.apduService)
                if not atype:
                    if _debug: Monitor._debug("    - no unconfirmed request decoder: %r", apdu.apduService)
                    return

            elif isinstance(apdu, SimpleAckPDU):
                atype = None

            elif isinstance(apdu, ComplexAckPDU):
                atype = complex_ack_types.get(apdu.apduService)
                if not atype:
                    if _debug: Monitor._debug("    - no complex ack decoder: %r", apdu.apduService)
                    return apdu

            elif isinstance(apdu, SegmentAckPDU):
                atype = None

            elif isinstance(apdu, ErrorPDU):
                atype = error_types.get(apdu.apduService)
                if not atype:
                    if _debug: Monitor._debug("    - no error decoder: %r", apdu.apduService)
                    return

            elif isinstance(apdu, RejectPDU):
                atype = None

            elif isinstance(apdu, AbortPDU):
                atype = None

            # deeper decoding
            try:
                if atype:
                    xpdu = apdu
                    apdu = atype()
                    apdu.decode(xpdu)
            except Exception as err:
                if _debug: Monitor._debug("    - decoding error: %r", err)
                return
            if _debug: Monitor._debug("    - apdu: %r", apdu)

            # build a description of this packet
            key = apdu.__class__.__name__ + ',' + str(apdu.pduSource)
            if atype is WhoIsRequest:
                if apdu.deviceInstanceRangeLowLimit is None:
                    key += ',*'
                else:
                    key += ',' + str(apdu.deviceInstanceRangeLowLimit)
                if apdu.deviceInstanceRangeHighLimit is None:
                    key += ',*'
                else:
                    key += ',' + str(apdu.deviceInstanceRangeHighLimit)
            elif atype is IAmRequest:
                key += ',' + str(apdu.iAmDeviceIdentifier[1])
            elif atype is WhoHasRequest:
                if apdu.object.objectIdentifier is not None:
                    key += ',' + apdu.object.objectIdentifier[0] + ',' + str(apdu.object.objectIdentifier[1])
                else:
                    key += ',*'
                if apdu.object.objectName is not None:
                    key += ',' + repr(apdu.object.objectName)
                else:
                    key += ',*'
            elif atype is IHaveRequest:
                key += ',' + apdu.deviceIdentifier[0] + ',' + str(apdu.deviceIdentifier[1])
                key += ',' + apdu.objectIdentifier[0] + ',' + str(apdu.objectIdentifier[1])
                key += ',' + repr(apdu.objectName)
            elif atype is UnconfirmedEventNotificationRequest:
                key += ',' + apdu.eventType
                if apdu.eventType == 'buffer-ready':
                    pass
                elif apdu.eventType == 'ack-notification':
                    pass
                elif (apdu.notifyType == 'alarm') or ((apdu.notifyType == 'event') and (apdu.eventType == 'change-of-state')):
                    key += ',' + ','.join((apdu.notifyType, apdu.eventType, apdu.fromState, apdu.toState))
            elif atype is UnconfirmedCOVNotificationRequest:
                    key += ',' + apdu.monitoredObjectIdentifier[0] + ',' + str(apdu.monitoredObjectIdentifier[1])

            # count the number of this kind of application layer message from this address
            Count(key, 'application-traffic', packet_info)

            # success
            return

        else:
            # make a more focused interpretation
            atype = npdu_types.get(npdu.npduNetMessage)
            if not atype:
                if _debug: Monitor._debug("    - no network layer decoder: %r", npdu.npduNetMessage)
                return

            # deeper decoding
            try:
                xpdu = npdu
                npdu = atype()
                npdu.decode(xpdu)
            except Exception as err:
                if _debug: Monitor._debug("    - network layer decoding error: %r", err)
                r.sadd('error-traffic', 'npdu-decoding,' + str(xpdu.pduSource))
                return
 
            # "lift" the source and destination address
            if xpdu.npduSADR:
                npdu.pduSource = xpdu.npduSADR
            else:
                npdu.pduSource = xpdu.pduSource
            if xpdu.npduDADR:
                npdu.pduDestination = xpdu.npduDADR
            else:
                npdu.pduDestination = xpdu.pduDestination
            if _debug: Monitor._debug("    - npdu: %r", npdu)

            # build a description of this packet
            key = npdu.__class__.__name__ + ',' + str(npdu.pduSource)
            if atype is WhoIsRouterToNetwork:
                key += ',' + str(npdu.wirtnNetwork)
            elif atype is IAmRouterToNetwork:
                key += ',' + ','.join(str(net) for net in npdu.iartnNetworkList)
            elif atype is ICouldBeRouterToNetwork:
                key += ',' + str(npdu.icbrtnNetwork)
                key += ',' + str(npdu.icbrtnPerformanceIndex)
            elif atype is RejectMessageToNetwork:
                key += ',' + str(npdu.rmtnRejectionReason)
                key += ',' + str(npdu.rmtnDNET)
            elif atype is RouterBusyToNetwork:
                key += ',' + ','.join(str(net) for net in npdu.rbtnNetworkList)
            elif atype is RouterAvailableToNetwork:
                key += ',' + ','.join(str(net) for net in npdu.ratnNetworkList)
            elif atype is EstablishConnectionToNetwork:
                key += ',' + str(npdu.ectnDNET)
                key += ',' + str(npdu.ectnTerminationTime)
            elif atype is DisconnectConnectionToNetwork:
                key += ',' + str(npdu.dctnDNET)

            # count the number of these application layer messages
            Count(key, 'network-traffic', packet_info)

            # success
            return

#
#   __main__
#

try:
    _log.debug("initialization")

    # address of the BBMD relative to the server location
    bbmdAddresses = []
    for addr in BACMON_BBMD.split():
        bbmdAddresses.append(Address(addr))

    # create the count intervals
    for parms in countIntervalParms:
        countIntervals.append(CountInterval(*parms))

    # connect to redis
    try:
        # Read Redis configuration from BACmon.ini if available
        redis_config = {}
        if config.has_section('Redis'):
            if config.has_option('Redis', 'host'):
                redis_config['host'] = config.get('Redis', 'host')
            if config.has_option('Redis', 'port'):
                redis_config['port'] = config.getint('Redis', 'port')
            if config.has_option('Redis', 'db'):
                redis_config['db'] = config.getint('Redis', 'db')
            if config.has_option('Redis', 'password'):
                redis_config['password'] = config.get('Redis', 'password')
            if config.has_option('Redis', 'socket_timeout'):
                redis_config['socket_timeout'] = config.getfloat('Redis', 'socket_timeout')
            if config.has_option('Redis', 'socket_connect_timeout'):
                redis_config['socket_connect_timeout'] = config.getfloat('Redis', 'socket_connect_timeout')
        
        # Create Redis client with configuration
        r = create_redis_client(redis_config)
        
        if _debug: _log.debug("    - Redis connection established")
    except Exception as e:
        _log.exception("Redis connection error: %s", e)
        sys.stderr.write("Redis connection error: %s\n" % (e,))
        sys.exit(1)

    # bind a monitor to a socket (should use BACMON_ADDRESS)
    bind(Monitor(), UDPDirector(('', 47808)))

    # Configure rate monitoring tasks from configuration
    scan_interval = 10000  # Default scan interval (10 seconds in ms)
    use_enhanced_detection = False  # Default to standard detection
    
    if config.has_section('RateMonitoring'):
        if _debug: _log.debug("Configuring rate monitoring from config file")
        
        # Get scan interval if specified
        if config.has_option('RateMonitoring', 'scan_interval'):
            scan_interval = config.getint('RateMonitoring', 'scan_interval')
            if _debug: _log.debug("    - Using scan interval: %d ms", scan_interval)
        
        # Check if enhanced detection is enabled
        if config.has_option('RateMonitoring', 'use_enhanced_detection'):
            use_enhanced_detection = config.getboolean('RateMonitoring', 'use_enhanced_detection')
            if use_enhanced_detection and not ANOMALY_DETECTION_AVAILABLE:
                if _debug: _log.debug("    - Enhanced detection requested but module not available, falling back to standard detection")
                use_enhanced_detection = False
            elif use_enhanced_detection:
                if _debug: _log.debug("    - Using enhanced anomaly detection")
        
        # Create rate monitoring tasks from config
        for option in config.options('RateMonitoring'):
            # Skip the scan_interval and use_enhanced_detection options
            if option in ('scan_interval', 'use_enhanced_detection'):
                continue
                
            try:
                # Parse the rate configuration (key, interval, max_value, duration)
                value = config.get('RateMonitoring', option)
                parts = [part.strip() for part in value.split(',')]
                
                if len(parts) != 4:
                    sys.stderr.write(f"Invalid rate monitoring configuration for {option}: {value}\n")
                    continue
                
                key = parts[0]
                interval = int(parts[1])
                max_value = int(parts[2])
                duration = int(parts[3])
                
                if _debug: _log.debug("    - Creating rate task: %s (%d, %d, %d)", 
                                      key, interval, max_value, duration)
                
                # Create and install the task based on detection mode
                if use_enhanced_detection and ANOMALY_DETECTION_AVAILABLE:
                    # Create enhanced detection task
                    task_config = {
                        'window_size': 60,
                        'sensitivity': config.getfloat('RateMonitoring', 'sensitivity', fallback=1.0),
                        'spike_sensitivity': config.getfloat('RateMonitoring', 'spike_sensitivity', fallback=2.0),
                        'z_threshold': config.getfloat('RateMonitoring', 'z_threshold', fallback=3.0),
                        'trend_threshold': config.getfloat('RateMonitoring', 'trend_threshold', fallback=0.2),
                        'hour_granularity': config.getint('RateMonitoring', 'hour_granularity', fallback=1)
                    }
                    
                    # Create enhanced task using anomaly detection module
                    task = anomaly_detection.create_enhanced_rate_task(
                        key, interval, max_value, duration, task_config
                    )
                    
                    # Set Redis client
                    task.set_redis_client(r)
                    
                    # Wrap the enhanced task to match RecurringTask interface
                    class EnhancedTaskWrapper(RecurringTask):
                        def __init__(self, enhanced_task):
                            super().__init__()
                            self.enhanced_task = enhanced_task
                            
                        def process_task(self):
                            return self.enhanced_task.process_task()
                    
                    # Create and install the wrapped task
                    wrapped_task = EnhancedTaskWrapper(task)
                    wrapped_task.install_task(scan_interval)
                    rate_tasks.append(wrapped_task)
                else:
                    # Create standard SampleRateTask
                    task = SampleRateTask(key, interval, max_value, duration)
                    task.install_task(scan_interval)
                    rate_tasks.append(task)
                
            except Exception as e:
                sys.stderr.write(f"Error configuring rate task {option}: {str(e)}\n")
    else:
        # No rate monitoring configuration, use default
        if _debug: _log.debug("Using default rate monitoring configuration")
        default_task = SampleRateTask("total:s", 1, 20, 30)
        default_task.install_task(scan_interval)
        rate_tasks.append(default_task)

    # log when the server started up and its version
    r.set_startup_time()
    r.set_daemon_version(__version__)
    
    _log.debug("running")

    # Initialize the extended rate monitoring system if available
    if EXTENDED_METRICS_AVAILABLE:
        try:
            # Replace countIntervals with enhanced versions
            if _debug: _log.debug("Initializing enhanced rate monitoring")
            
            # Create a backup of the original intervals
            original_intervals = countIntervals.copy()
            
            # Initialize with enhanced intervals
            enhanced_intervals = enhanced_rate_monitoring.initialize_with_existing_intervals(
                original_intervals, 
                r
            )
            
            # Replace the original intervals
            countIntervals = enhanced_intervals
            
            if _debug: _log.debug("Enhanced rate monitoring initialized successfully")
        except Exception as e:
            if _debug: _log.debug("Error initializing enhanced rate monitoring: %r", e)

    run()
except Exception as e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")