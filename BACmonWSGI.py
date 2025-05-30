#!/usr/bin/python

"""
BACnet LAN Monitor WSGI
"""

import sys
import os
import calendar
import datetime
import socket
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Callable, cast, Type, Sequence, IO
import json
from datetime import datetime, timedelta

# monkeypatch to avoid a really slow getfqdn call
try:
    # Python 3
    import http.server as BaseHTTPServer
    from http.client import responses as http_responses
    from urllib.parse import parse_qs, urlencode
except ImportError:
    # Python 2
    import BaseHTTPServer
    from httplib import responses as http_responses
    from urllib import urlencode
    from urlparse import parse_qs

BaseHTTPServer.BaseHTTPRequestHandler.address_string = \
    lambda self: str(self.client_address[0])

import bottle
import redis

# Import from the compatibility module instead of directly from bacpypes
from bacpypes_compat import set_bacpypes_version, get_debugging, get_console_logging

# Initialize bacpypes version (default to bacpypes, will fall back to bacpypes3 if needed)
set_bacpypes_version(False)  # Use bacpypes by default

# Get debugging components
function_debugging, ModuleLogger, _ = get_debugging()
ConsoleLogHandler = get_console_logging()

from collections import defaultdict
from time import time as _time

# version
__version__ = '1.0.0'

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# Import the anomaly detection module if available
try:
    import anomaly_detection
    ANOMALY_DETECTION_AVAILABLE = True
except ImportError:
    ANOMALY_DETECTION_AVAILABLE = False

# Import the alert manager
import alert_manager
from datetime import datetime

# Import the simple authentication module
try:
    from simple_auth import get_auth_manager, require_auth, require_admin, login_required, create_test_user_session, get_api_keys_info
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    # Create dummy decorators if auth is not available
    def require_auth(permission='read'):
        def decorator(func):
            return func
        return decorator
    
    def require_admin():
        def decorator(func):
            return func
        return decorator
    
    def login_required(func):
        return func

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
    BACMON_INTERFACE = config.get('BACmon', 'interface')
    if _debug: _log.debug("    - BACMON_INTERFACE: %r", BACMON_INTERFACE)

    BACMON_ADDRESS = config.get('BACmon', 'address')
    if _debug: _log.debug("    - BACMON_ADDRESS: %r", BACMON_ADDRESS)

    BACMON_BBMD = config.get('BACmon', 'bbmd')
    if _debug: _log.debug("    - BACMON_BBMD: %r", BACMON_BBMD)

    BACMON_LOGDIR = config.get('BACmon', 'logdir')
    if _debug: _log.debug("    - BACMON_LOGDIR: %r", BACMON_LOGDIR)

    BACMON_ROLLOVER = config.get('BACmon', 'rollover')
    if _debug: _log.debug("    - BACMON_ROLLOVER: %r", BACMON_ROLLOVER)

    BACMON_STATICDIR = config.get('BACmon', 'staticdir')
    if _debug: _log.debug("    - BACMON_STATICDIR: %r", BACMON_STATICDIR)

    BACMON_TEMPLATEDIR = config.get('BACmon', 'templatedir')
    if _debug: _log.debug("    - BACMON_TEMPLATEDIR: %r", BACMON_TEMPLATEDIR)

except Exception as err:
    sys.stderr.write("configuration error: %s\n" % (err,))
    sys.exit(1)

sys.path.append(BACMON_HOME)
bottle.TEMPLATE_PATH.append(BACMON_TEMPLATEDIR)

from XHTML import *
from timeutil import AbsoluteTime, SmartTimeFormat

# connection to redis
try:
    from redis_client import RedisClient, create_redis_client
    r = create_redis_client()
except ImportError:
    # Fall back to direct Redis connection if client wrapper is not available
    r = redis.Redis('localhost')

#
#   MapTime
#

@function_debugging
def MapTime(when: int) -> int:
    return calendar.timegm(datetime.datetime.fromtimestamp(when).timetuple()) * 1000

#
#   TrendDivs
#

@function_debugging
def TrendDivs(key: str, body: Element) -> None:
    """Create the divs for each of the intervals for the key and append them to the body."""

    now = int(_time())
    countIntervals: List[Tuple[str, int, int, str]] = \
        ( ('s', 1, 900, "%H:%M:%S")
        , ('m', 60, 1440, "%H:%M")
        , ('h', 3600, 168, "%d-%B %H:%M")
        )
    for label, modulus, maxLen, dateFormat in countIntervals:
        keyLabel = key + ':' + label
        alarmTime = r.get(keyLabel + ":alarm")
        if alarmTime:
            p = P(B("Rate limit exceeded since " + str(AbsoluteTime(int(alarmTime)))))
            body.append(p)
        if r.type(keyLabel + ":alarm-history") != 'none':
            p = P("Alarm History ", A("[H]",href="/alarm-history/" + keyLabel) )
            body.append(p)

        data = r.lrange(keyLabel, 0, -1)
        if not data:
            p = P("No '%s' data." % (label,))
            body.append(p)
            continue
        data.reverse()

        divID = "plot" + label
        div = DIV("", id_=divID, style="width:1024px;height:250px;")
        body.append(div)

        # make a placeholder for selected time ranges
        selID = "plot" + label + "sel"
        body.append(P(SPAN("No selection", id_=selID), A("[L]", href="/log", id_=selID + "a"), style="width:1024px;text-align:center;font-size:75%;"))

        edge = now - (now % modulus)
        startTime = MapTime(edge - (modulus * maxLen))
        endTime = MapTime(edge)

        d = []
        next = 0
        for datum in data:
            ts, count = eval(datum)
            
            # put in a zero for gaps
            if (next != 0) and (ts != next):
                while (next < ts):
                    xts = MapTime(next)
                    d.append("[%d, 0]" % (xts,))
                    next += modulus

            # remap the timestamp to javascript local time
            xts = MapTime(ts)
            d.append("[%d, %d]" % (xts, count))
            next = ts + modulus

        script = SCRIPT("""
            $(function () {
                var d = [ { color: "#700", label: "%(label)s", data: [%(data)s]} ];

                var flotDiv = $("#%(divID)s");

                $.plot(flotDiv, d, { xaxis: { mode: "time", min: %(startTime)d, max: %(endTime)d }, selection: { mode: "x" } });

                flotDiv.bind("plotselected", function (event, ranges) {
                    var fromDate = new Date(ranges.xaxis.from);
                    var toDate = new Date(ranges.xaxis.to);
                    $("#%(selID)s").text(
                        $.strftime("%(dateFormat)s", fromDate, true) + " ... " + $.strftime("%(dateFormat)s", toDate, true)
                        );
                    var linkRef = "/log?b=" + $.strftime("%(dtf)s", fromDate, true) + "&e=" + $.strftime("%(dtf)s", toDate, true);
                    $("#%(selID)sa").attr("href", linkRef);
                });
            });
            """ % { 'label':     "pp" + label
                ,   'data':      ', '.join(d)
                ,   'divID':     divID
                ,   'startTime': startTime
                ,   'endTime':   endTime
                ,   'selID':     selID
                ,   'dateFormat':dateFormat
                ,   'dtf':       "%d-%b-%Y %H:%M:%S"
                })
        body.append(script)

#
#   MessageTable
#

@function_debugging
def MessageTable(msgSetName: str, msgSet: Set) -> TABLE:
    msgList = list(msgSet)
    msgList.sort()
    msgTable = [msg.split('/') for msg in msgList]

    msgCount: Dict[str, int] = defaultdict(int)
    for msgRow in msgTable:
        msgCount[msgRow[0]] += 1

    table = TABLE()

    thead = THEAD()
    table.append(thead)
    thead.append(TH("Address"), TH("Message"), TH("Clear"))

    tbody = TBODY()
    table.append(tbody)
    for msg, msgRow in zip(msgList, msgTable):
        tr = TR()
        table.append(tr)

        devAddr = msgRow[0]
        if devAddr in msgCount:
            tr.append(TD(devAddr, rowspan=msgCount[devAddr], valign="top"))
            del msgCount[devAddr]

        tr.append(TD(msgRow[2]))
        tr.append(TD(
            A("[C]", href="/clear/"+msgSetName+','+msg.replace('/','\\')
                )
            ))

    return table

#
#   TrafficTable
#

@function_debugging
def TrafficTable(msgSetName: str, msgSet: Set) -> TABLE:
    """Build a table that references trending."""
    if _debug: TrafficTable._debug("TrafficTable %r %r", msgSetName, msgSet)

    # make a list out of the set, sort it, and split it
    msgList = list(msgSet)
    msgList.sort()
    msgTable = [msg.split(',') for msg in msgList]

    maxLen = 0
    msgCount: Dict[str, int] = defaultdict(int)
    for msgRow in msgTable:
        msgCount[msgRow[0]] += 1
        maxLen = max(maxLen, len(msgRow))

    table = TABLE()

    thead = THEAD()
    table.append(thead)
    if msgSetName == 'ip-traffic':
        thead.append(TH("Address"), TH("Trend"), TH("Clear"))
    else:
        thead.append(TH("Message"), TH("Address"), TH("Parameters", colspan=maxLen-2), TH("Trend"), TH("Clear"))

    tbody = TBODY()
    table.append(tbody)
    for msg, msgRow in zip(msgList, msgTable):
        tr = TR()
        tbody.append(tr)

        devAddr = msgRow[0]
        if devAddr in msgCount:
            tr.append(TD(devAddr, rowspan=msgCount[devAddr], valign="top"))
            del msgCount[devAddr]

        for m in msgRow[1:]:
            tr.append(TD(m))
        for i in range(maxLen - len(msgRow)):
            tr.append(TD())

        tr.append(TD(A(r.get(msg), href="/trend/" + msg), align="right"))
        tr.append(TD(A("[C]", href="/clear/"+msgSetName+','+msg)))

    return table

#
#   ErrorTable
#

@function_debugging
def ErrorTable(msgSetName: str, msgSet: Set) -> TABLE:
    msgList = list(msgSet)
    msgList.sort()
    msgTable = [msg.split(',') for msg in msgList]

    msgCount: Dict[str, int] = defaultdict(int)
    for msgRow in msgTable:
        msgCount[msgRow[0]] += 1

    table = TABLE()

    thead = THEAD()
    table.append(thead)
    thead.append(TH("Error"), TH("Address"), TH("Message"), TH("Clear"))

    tbody = TBODY()
    table.append(tbody)
    for msg, msgRow in zip(msgList, msgTable):
        tr = TR()
        table.append(tr)

        errorType = msgRow[0]
        if errorType in msgCount:
            tr.append(TD(errorType, rowspan=msgCount[errorType], valign="top"))
            del msgCount[errorType]

        tr.append(TD(msgRow[1]))
        if len(msgRow) == 3:
            tr.append(TD(msgRow[2]))
        else:
            tr.append(TD())
        tr.append(TD(
            A("[C]", href="/clear/"+msgSetName+','+msg
                )
            ))

    return table

#
#   AlarmHistory
#

@function_debugging
def AlarmHistory(key: str) -> Union[TABLE, P]:
    data = r.lrange(key + ":alarm-history", 0, -1)
    if not data:
        return P("No '%s' alarm history." % (key,))
    data.reverse()
    alarmHistory = [eval(s) for s in data]

    table = TABLE()

    thead = THEAD()
    table.append(thead)
    thead.append(TH("Active"), TH("Clear"))

    tbody = TBODY()
    table.append(tbody)
    for activeTime, clearTime in alarmHistory:
        tr = TR()
        table.append(tr)

        activeTime = AbsoluteTime(activeTime)
        tr.append(TD(str(activeTime)))

        clearTime = AbsoluteTime(clearTime)
        tr.append(TD(SmartTimeFormat(clearTime, activeTime)))

    return table

#
#   Home Page
#

@bottle.route('/')
@bottle.view('basic')
@function_debugging
def welcome() -> Dict[str, Any]:
    """Welcome page."""
    if _debug: welcome._debug("welcome")

    content = DIV(
        H2("BACmon - Enhanced BACnet LAN Monitor"),
        P("Welcome to the enhanced BACnet network monitoring system."),
        
        # Featured Dashboard Section
        DIV(
            H3("🌟 Main Dashboard", style="color: #2563eb; margin-top: 2rem;"),
            P("Experience our beautiful, modern monitoring dashboard with real-time data visualization."),
            DIV(
                A("Launch Dashboard", 
                  href="/dashboard", 
                  style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 10px 0;"),
                style="margin: 1rem 0;"
            ),
            style="background: rgba(37, 99, 235, 0.05); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #2563eb; margin: 1.5rem 0;"
        ),
        
        P("Use the navigation menu to access different monitoring features:"),
        UL(
            LI(B("Dashboard"), " - Beautiful real-time monitoring with charts and analytics"),
            LI(B("Enhanced Monitoring"), " - Access API Console, Rate Monitoring, and Alert systems"),
            LI(B("Traffic Analysis"), " - View traffic categorized by IP, BVLL, Network, and Application layers"),
            LI(B("Messages"), " - Monitor Critical, Alert, and Warning messages"),
            LI(B("Admin Tools"), " - System information, flush operations, and authentication")
        ),
        
        # Quick Links Section
        DIV(
            H3("Quick Access"),
            DIV(
                A("Main Dashboard", href="/dashboard", style="margin-right: 15px; color: #2563eb; font-weight: 600;"),
                A("API Console", href="/api-dashboard", style="margin-right: 15px; color: #06b6d4;"),
                A("Rate Monitor", href="/rate-monitoring", style="margin-right: 15px; color: #10b981;"),
                A("System Info", href="/info", style="color: #f59e0b;")
            ),
            style="margin-top: 2rem; padding: 1rem; background: #f8fafc; border-radius: 8px;"
        )
    )

    # Get authentication context
    context = get_template_context()
    
    return {
        'title': 'Welcome to BACmon',
        'body': content,
        **context
    }

#
#   Static Files
#

@bottle.route('/static/:filename')
@function_debugging
def static_file(filename: str) -> Any:
    if _debug: static_file._debug("static_file %r", filename)

    return bottle.static_file(filename, BACMON_STATICDIR)

@bottle.route('/static/js/:filename')
@function_debugging
def js_file(filename: str) -> Any:
    if _debug: js_file._debug("js_file %r", filename)

    return bottle.static_file(filename, BACMON_STATICDIR + '/js')

#
#   Help
#

@bottle.route('/help')
@bottle.view('help')
@function_debugging
def help() -> Dict[str, Any]:
    if _debug: help._debug("help")

    return {}

#
#   Authentication Routes
#

@bottle.route('/login')
@bottle.view('login')
@function_debugging
def login_get() -> Dict[str, Any]:
    """Display login page."""
    if _debug: login_get._debug("login_get")
    
    # Check if already logged in
    if AUTH_AVAILABLE:
        auth = get_auth_manager(r)
        session_token = bottle.request.get_cookie('session_token')
        if session_token and auth.validate_session(session_token):
            bottle.redirect('/')
    
    return {
        'error': None,
        'message': None,
        'username': '',
        'show_test_credentials': os.getenv('AUTH_SHOW_TEST_CREDS', 'true').lower() == 'true'
    }

@bottle.route('/login', method='POST')
@bottle.view('login')
@function_debugging
def login_post() -> Dict[str, Any]:
    """Handle login form submission."""
    if _debug: login_post._debug("login_post")
    
    username = bottle.request.forms.get('username', '').strip()
    password = bottle.request.forms.get('password', '').strip()
    
    # Simple test credentials for development
    test_users = {
        'test': {'password': 'test123', 'permissions': ['read', 'write']},
        'admin': {'password': 'admin123', 'permissions': ['read', 'write', 'admin']},
        'readonly': {'password': 'readonly123', 'permissions': ['read']}
    }
    
    if username in test_users and test_users[username]['password'] == password:
        if AUTH_AVAILABLE:
            # Create session
            auth = get_auth_manager(r)
            session_token = auth.create_session(username, test_users[username]['permissions'])
            
            # Set session cookie
            bottle.response.set_cookie(
                'session_token', 
                session_token, 
                httponly=True, 
                secure=False,  # Set to True in production with HTTPS
                max_age=auth.session_timeout
            )
        
        # Redirect to home page
        bottle.redirect('/')
    else:
        # Login failed
        return {
            'error': 'Invalid username or password',
            'message': None,
            'username': username,
            'show_test_credentials': os.getenv('AUTH_SHOW_TEST_CREDS', 'true').lower() == 'true'
        }

@bottle.route('/logout')
@function_debugging
def logout() -> None:
    """Handle logout."""
    if _debug: logout._debug("logout")
    
    if AUTH_AVAILABLE:
        # Invalidate session
        session_token = bottle.request.get_cookie('session_token')
        if session_token:
            auth = get_auth_manager(r)
            auth.invalidate_session(session_token)
    
    # Clear session cookie
    bottle.response.delete_cookie('session_token')
    
    # Redirect to login page
    bottle.redirect('/login')

@bottle.route('/auth/info')
@function_debugging
def auth_info() -> Dict[str, Any]:
    """Display authentication information for testing."""
    if _debug: auth_info._debug("auth_info")
    
    if not AUTH_AVAILABLE:
        return create_api_response(error="Authentication not available", code=503)
    
    # Get current auth status
    auth_status = {
        'authenticated': False,
        'user_id': None,
        'permissions': [],
        'auth_type': None
    }
    
    auth = get_auth_manager(r)
    
    # Check session
    session_token = bottle.request.get_cookie('session_token')
    if session_token:
        session_data = auth.validate_session(session_token)
        if session_data:
            auth_status.update({
                'authenticated': True,
                'user_id': session_data['user_id'],
                'permissions': session_data['permissions'],
                'auth_type': 'session'
            })
    
    # Check API key
    api_key = bottle.request.get_header('X-API-Key')
    if api_key:
        key_data = auth.validate_api_key(api_key)
        if key_data:
            auth_status.update({
                'authenticated': True,
                'permissions': key_data['permissions'],
                'auth_type': 'api_key',
                'key_name': key_data['name']
            })
    
    # Get available API keys info (for testing)
    api_keys_info = get_api_keys_info()
    
    return create_api_response({
        'auth_enabled': auth.enabled,
        'current_status': auth_status,
        'available_api_keys': api_keys_info,
        'test_credentials': {
            'test': 'test123 (read/write)',
            'admin': 'admin123 (admin)',
            'readonly': 'readonly123 (read-only)'
        }
    })

#
#   Test
#

@bottle.route('/test')
@function_debugging
def test() -> str:
    if _debug: test._debug("test")

    return str(list(bottle.request.GET.keys()))

#
#   Log Files
#

@bottle.route('/log')
@bottle.view('basic')
def log_file_index() -> Dict[str, Any]:
    body = DIV()

    selected = False
    selBegin = bottle.request.GET.get('b', '')
    if selBegin:
        selected = True
        selBegin = int(AbsoluteTime(selBegin))
    else:
        selBegin = 0
    selEnd = bottle.request.GET.get('e', '')
    if selEnd:
        selected = True
        selEnd = int(AbsoluteTime(selEnd))
    else:
        selEnd = 2147483647
    if selected:
        body.append(P("Selected ", B(AbsoluteTime(selBegin))
            , " thru ", B(AbsoluteTime(selEnd))
            ))

    first = True
    walking = os.walk(BACMON_LOGDIR)
    for root, dirs, files in walking:
        files.sort()
        for f in files:
            fname = root + '/' + f
            fstat = os.stat(fname)

            sTime = int(fname.split('.')[-1])
            eTime = int(fstat.st_mtime)
            if (sTime > selEnd) or (eTime < selBegin):
                continue

            startTime = AbsoluteTime(sTime)
            endTime = AbsoluteTime(eTime)
            fileSize = int(fstat.st_size)

            if first:
                first = False
                table = TABLE()
                body.append(table)

                table.append(
                    THEAD(TR( TH("File")
                    ,   TH("Start")
                    ,   TH("End")
                    ,   TH("Size", align="right")
                    )))

            tr = TR()
            table.append(tr)
            tr.append(TD(A("[F]", href="/log/" + f)))
            tr.append(TD(str(startTime)))
            tr.append(TD(SmartTimeFormat(endTime, startTime)))
            tr.append(TD(fileSize, align="right"))

    if first:
        if selected:
            body.append(P("No capture log files for that time range."))
        else:
            body.append(P("No capture log files."))

    return {'title': 'Packet Capture Log Files', 'body':body}

@bottle.route('/log/:filename')
def log_file(filename: str) -> Any:
    # the file name looks like daemonlogger.pcap.1272641091
    fname = filename.split('.')

    # make it look like server.1272641091.pcap
    fname = '.'.join((socket.gethostname(), fname[2], fname[1]))

    # set the response headers
    bottle.response.set_header('Content-Type', 'application/x-libpcap-capture')
    bottle.response.set_header('Content-Disposition', 'attachment; filename=' + fname)

    # now send the file
    return bottle.static_file(filename, BACMON_LOGDIR)

#
#   Traffic Pages
#

@bottle.route('/ip-traffic')
@bottle.view('basic')
def ip_messages() -> Dict[str, Any]:
    msgSet = r.smembers('ip-traffic')
    if not msgSet:
        return {'title': "IP Traffic", 'body': "No IP traffic."}

    return {'title': "IP Traffic", 'body':TrafficTable('ip-traffic', msgSet)}

@bottle.route('/bvll-traffic')
@bottle.view('basic')
def bvll_messages() -> Dict[str, Any]:
    msgSet = r.smembers('bvll-traffic')
    if not msgSet:
        return {'title': "BVLL Traffic", 'body': "No BVLL traffic."}

    return {'title': "BVLL Traffic", 'body':TrafficTable('bvll-traffic', msgSet)}

@bottle.route('/network-traffic')
@bottle.view('basic')
def network_messages() -> Dict[str, Any]:
    msgSet = r.smembers('network-traffic')
    if not msgSet:
        return {'title': "Network Layer Traffic", 'body': "No network layer traffic."}

    return {'title': "Network Layer Traffic", 'body':TrafficTable('network-traffic', msgSet)}

@bottle.route('/application-traffic')
@bottle.view('basic')
def application_messages() -> Dict[str, Any]:
    msgSet = r.smembers('application-traffic')
    if not msgSet:
        return {'title': "Application Layer Traffic", 'body': "No application layer traffic."}

    return {'title': "Application Layer Traffic", 'body':TrafficTable('application-traffic', msgSet)}

@bottle.route('/error-traffic')
@bottle.view('basic')
def error_traffic() -> Dict[str, Any]:
    msgSet = r.smembers('error-traffic')
    if not msgSet:
        return {'title': "Error Traffic", 'body': "No encoding/decoding error traffic."}

    return {'title': "Error Traffic", 'body':ErrorTable('error-traffic', msgSet)}

#
#   Who-Is and I-Am Merged
#

@bottle.route('/who-is-i-am-merged')
@bottle.view('basic')
def who_is_i_am_merged() -> Dict[str, Any]:
    msgSet = r.smembers('application-traffic')
    if not msgSet:
        return {'title': "Who-Is/I-Am Merged", 'body': "No application layer traffic."}

    # make a list out of the set, sort it, and split it
    msgList = list(msgSet)
    msgList.sort()

    # mash together the Who-Is and I-Am messages
    mashup: Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for msg in msgList:
        msgRow = msg.split(',')
        count = r.get(msg)

        if (msgRow[0] == 'WhoIsRequest'):
            try:
                addr = msgRow[1]
                lolimit = int(msgRow[2])
                hilimit = int(msgRow[3])
            except Exception as e:
                continue

            if (lolimit == hilimit):
                if lolimit in mashup:
                    mashup[lolimit][0][addr] = count
                else:
                    mashup[lolimit] = [{addr:count}, {}]

        elif (msgRow[0] == 'IAmRequest'):
            try:
                addr = msgRow[1]
                devid = int(msgRow[2])
            except Exception as e:
                continue

            if devid in mashup:
                mashup[devid][1][addr] = count
            else:
                mashup[devid] = [{}, {addr:count}]

    mashitems = list(mashup.items())
    mashitems.sort()

    table = TABLE()

    thead = THEAD()
    table.append(thead)
    thead.append(TH("DeviceID"), TH("Who-Is"), TH("I-Am"), TH("Count"))

    tbody = TBODY()
    table.append(tbody)

    for devid, value in mashitems:
        tbody.append(TR(TD(devid)))

        whoIsItems = list(value[0].items())
        whoIsItems.sort()
        for whoIsAddr, whoIsCount in whoIsItems:
            tbody.append(TR(TD(), TD(whoIsAddr), TD(), TD(whoIsCount, style="text-align: right")))

        iAmItems = list(value[1].items())
        iAmItems.sort()
        for iAmAddr, iAmCount in iAmItems:
            tbody.append(TR(TD(), TD(), TD(iAmAddr), TD(iAmCount, style="text-align: right")))

    return {'title': "Who-Is/I-Am Merged", 'body':table}

#
#   Messages
#

@bottle.route('/critical-messages')
@bottle.view('basic')
def zino_critical() -> Dict[str, Any]:
    errorSet = r.smembers('critical-messages')
    if not errorSet:
        return {'title': "Critical Errors", 'body':P("No critical errors.")}

    return {'title': "Critical Errors", 'body':MessageTable('critical-messages', errorSet)}

@bottle.route('/alert-messages')
@bottle.view('basic')
def zino_alert() -> Dict[str, Any]:
    errorSet = r.smembers('alert-messages')
    if not errorSet:
        return {'title': "Alerts", 'body':P("No alerts.")}

    return {'title': "Alerts", 'body':MessageTable('alert-messages', errorSet)}

@bottle.route('/warning-messages')
@bottle.view('basic')
def zino_warning() -> Dict[str, Any]:
    errorSet = r.smembers('warning-messages')
    if not errorSet:
        return {'title': "Warnings", 'body':P("No warnings.")}

    return {'title': "Warnings", 'body':MessageTable('warning-messages', errorSet)}

@bottle.route('/undefined-devices')
@bottle.view('basic')
def zino_undefined() -> Dict[str, Any]:
    errorSet = r.smembers('undefined-devices')
    if not errorSet:
        return {'title': "Undefined Devices", 'body':P("No undefined devices.")}

    errorList = list(errorSet)
    errorList.sort()

    table = TABLE()
    for error in errorList:
        tr = TR()
        table.append(tr)
        for item in error.split('/'):
            tr.append(TD(item))
            tr.append(TD(A("[C]", href="/clear/undefined-devices,"+item)))

    return {'title': "Undefined Devices", 'body':table}

#
#
#

@bottle.route('/trend/:key')
@bottle.view('basic')
def trend_key(key: str) -> Dict[str, Any]:
    body = DIV()
    TrendDivs(key, body)
    return {'title': key, 'body':body}

#
#
#

@bottle.route('/alarm-history/:key')
@bottle.view('basic')
def alarm_history(key: str) -> Dict[str, Any]:
    return {'title': "Alarm History " + key, 'body':AlarmHistory(key)}

#
#
#

@bottle.route('/clear/:key')
@bottle.view('basic')
def clear_key(key: str) -> Dict[str, Any]:
    try:
        # split the message set and the key
        msgSet, subkey = key.split(',', 1)
        subkey = subkey.replace('\\', '/')

        # remove it from the set and delete the counter
        if not r.srem(msgSet, subkey):
            raise RuntimeError("Subkey '%s' not in message set '%s'." % (subkey, msgSet))

        # this might be a counter of the number of these
        if r.delete(subkey):
            for label in ('s', 'm', 'h'):
                key = subkey + ':' + label
                keyi = key + 'i'
                keyn = key + 'n'
                r.delete(key)
                r.delete(keyi)
                r.delete(keyn)

        # redirect back to the message set page
        bottle.redirect("/"+msgSet)

    except Exception as err:
        errorDiv = DIV()
        errorDiv.append(P("An error has occurred:"))
        errorDiv.append(P(B(str(err))))
        return {'title': "Clear", 'body': errorDiv}

#
#   Database Information
#

@bottle.route('/info')
@bottle.view('basic')
@require_admin()
def info_page() -> Dict[str, Any]:
    info = r.info()
    items = info.items()
    items = sorted(items)

    table = TABLE()

    # add the daemon version
    daemon_version = r.get('daemon_version')
    if daemon_version:
        tr = TR(TD("daemon_version"), TD(B(daemon_version)))
        table.append(tr)

    startup_time = r.get('startup_time')
    if startup_time:
        tr = TR(TD("startup_time"), TD(B(AbsoluteTime(int(startup_time)))))
        table.append(tr)

    flush_time = r.get('flush_time')
    if flush_time:
        tr = TR(TD("flush_time"), TD(B(AbsoluteTime(int(flush_time)))))
        table.append(tr)

    # add our version
    wsgi_version = __version__
    if wsgi_version:
        tr = TR(TD("wsgi_version"), TD(B(wsgi_version)))
        table.append(tr)

    # add the rest of the redis information items
    for k, v in items:
        tr = TR()
        table.append(tr)
        
        tr.append(TD(k), TD(B(v)))

    return {'title': "Database Information", 'body': table}

#
#   Flush
#

@bottle.route('/flush')
@bottle.view('basic')
@require_admin()
def flush_get() -> Dict[str, Any]:
    body = DIV()
    p = P("Are you sure you want to flush the database?")
    body.append(p)

    form = FORM( method="POST", action='/flush' )
    form.append(INPUT(type="checkbox", name='ack'))
    form.append(INPUT(type="submit", value=" Go "))
    body.append(form)

    flush_time = r.get('flush_time')
    if not flush_time:
        p = P("There is no record of when it was last flushed.")
    else:
        p = P("Last flushed ", AbsoluteTime(int(flush_time)))
    body.append(p)

    return {'title':"Database Flush", 'body':body}

@bottle.route('/flush', method='POST')
@bottle.view('basic')
@require_admin()
def flush_post() -> Dict[str, Any]:
    ack = bottle.request.POST.get('ack', None)
    if ack == 'on':
        r.flushdb()
        p = P("Flushed.")

        # log when the database was flushed
        r.set('flush_time', int(_time()))
    else:
        p = P("Flush request canceled. ", B(ack))

    return {'title': "Database Flush", 'body': p}

#
#   Template Cache Clear
#

@bottle.route('/clear-template')
@bottle.view('basic')
def clear_template() -> Dict[str, Any]:
    bottle.TEMPLATES.clear()
    return {'title': "Clear Template Cache", 'body': "Template cache cleared."}

#
#   Process a time range string into start and end timestamps
#

@function_debugging
def process_time_range(timerange: str) -> Tuple[int, int]:
    """
    Process a time range string and return start and end timestamps.
    
    Args:
        timerange: String like '1h', '6h', '12h', '24h', '7d'
        
    Returns:
        Tuple of (start_timestamp, end_timestamp)
    """
    now = int(_time())
    
    if timerange == '1h':
        return now - 3600, now
    elif timerange == '6h':
        return now - 21600, now
    elif timerange == '12h':
        return now - 43200, now
    elif timerange == '24h':
        return now - 86400, now
    elif timerange == '7d':
        return now - 604800, now
    else:
        # Default to last hour
        return now - 3600, now

#
#   Get available monitoring keys
#

@function_debugging
def get_monitoring_keys() -> List[str]:
    """
    Get list of available rate monitoring keys.
    
    Returns:
        List of key strings
    """
    keys = []
    
    # Get all keys with :s, :m, or :h suffix (which are rate monitoring keys)
    for suffix in ['s', 'm', 'h']:
        pattern = f'*:{suffix}'
        matched_keys = r.keys(pattern)
        
        # Add base keys without suffix
        for key in matched_keys:
            # Convert bytes to string and remove suffix
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            base_key = key_str.rsplit(':', 1)[0]
            if base_key not in keys:
                keys.append(base_key)
    
    return sorted(keys)

#
#   Get samples for a key with optional time filtering
#

@function_debugging
def get_key_samples(key: str, start_time: int, end_time: int) -> List[Dict[str, Any]]:
    """
    Get samples for a key within a time range.
    
    Args:
        key: The monitoring key (e.g., 'total')
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        List of sample dictionaries
    """
    samples = []
    intervals = ['s', 'm', 'h']
    
    # Find the most appropriate interval based on time range
    interval_idx = 0
    time_diff = end_time - start_time
    
    if time_diff > 86400:  # More than a day
        interval_idx = 2  # Use hourly data
    elif time_diff > 7200:  # More than 2 hours
        interval_idx = 1  # Use minute data
    
    # Get data for the selected interval
    interval = intervals[interval_idx]
    key_with_interval = f"{key}:{interval}"
    
    # Get raw data
    data = r.lrange(key_with_interval, 0, -1)
    if not data:
        return []
    
    # Process the data
    data.reverse()
    for datum in data:
        try:
            ts, count = eval(datum)
            if start_time <= ts <= end_time:
                time_str = AbsoluteTime(ts)
                samples.append({
                    'timestamp': ts,
                    'value': count,
                    'time_str': time_str,
                    'is_anomaly': False,
                    'status': 'Normal'
                })
        except Exception as e:
            if _debug: _log.debug(f"Error processing sample {datum}: {e}")
    
    return samples

#
#   Get anomaly data for a key
#

@function_debugging
def get_anomaly_data(key: str, samples: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Get anomaly data for a key.
    
    Args:
        key: The monitoring key
        samples: List of sample dictionaries
        
    Returns:
        Tuple of (anomalies, anomaly_type_data, time_distribution_data, anomaly_chart_data)
    """
    anomalies = []
    anomaly_type_counts = {}
    hour_distribution = [0] * 24
    
    # Check if we have anomaly detection and history available
    anomaly_detector = None
    if ANOMALY_DETECTION_AVAILABLE:
        # Try to find an existing detector in Redis
        detector_data = r.get(f"{key}:anomaly_detector")
        if detector_data:
            try:
                # This is just a placeholder - in a real implementation,
                # we would deserialize the detector from Redis
                pass
            except Exception as e:
                if _debug: _log.debug(f"Error deserializing detector: {e}")
    
    # Check alarm history for this key
    alarm_history_key = f"{key}:alarm-history"
    if r.type(alarm_history_key) != b'none':
        history_data = r.lrange(alarm_history_key, 0, -1)
        
        for entry in history_data:
            try:
                start_ts, end_ts = eval(entry)
                
                # Create a basic anomaly entry
                anomaly = {
                    'timestamp': start_ts,
                    'end_timestamp': end_ts,
                    'time_str': AbsoluteTime(start_ts),
                    'end_time_str': AbsoluteTime(end_ts) if end_ts else 'Ongoing',
                    'value': None,  # Will be filled in if we find a matching sample
                    'types': ['threshold'],  # Default to threshold violation
                    'score': 0.8  # Default score
                }
                
                # Find the matching sample to get the value
                for sample in samples:
                    if sample['timestamp'] == start_ts:
                        anomaly['value'] = sample['value']
                        sample['is_anomaly'] = True
                        sample['status'] = 'Anomaly'
                        break
                
                # If we didn't find a value in samples, skip this anomaly
                if anomaly['value'] is None:
                    continue
                
                # Update anomaly type counts
                for atype in anomaly['types']:
                    if atype in anomaly_type_counts:
                        anomaly_type_counts[atype] += 1
                    else:
                        anomaly_type_counts[atype] = 1
                
                # Update hour distribution
                hour = datetime.fromtimestamp(start_ts).hour
                hour_distribution[hour] += 1
                
                anomalies.append(anomaly)
            except Exception as e:
                if _debug: _log.debug(f"Error processing alarm history entry {entry}: {e}")
    
    # If we have the anomaly detection module and anomaly history
    if ANOMALY_DETECTION_AVAILABLE:
        # Check for enhanced anomaly history
        enhanced_history_key = f"{key}:enhanced_anomaly_history"
        enhanced_history = r.get(enhanced_history_key)
        
        if enhanced_history:
            try:
                history_data = json.loads(enhanced_history)
                
                for entry in history_data:
                    # Extract data from the history entry
                    ts = entry.get('timestamp')
                    value = entry.get('value')
                    result = entry.get('result', {})
                    
                    # Create a more detailed anomaly entry
                    anomaly = {
                        'timestamp': ts,
                        'time_str': AbsoluteTime(ts),
                        'value': value,
                        'types': result.get('anomaly_types', ['unknown']),
                        'score': result.get('anomaly_score', 0.5)
                    }
                    
                    # Update anomaly type counts
                    for atype in anomaly['types']:
                        if atype in anomaly_type_counts:
                            anomaly_type_counts[atype] += 1
                        else:
                            anomaly_type_counts[atype] = 1
                    
                    # Update hour distribution
                    hour = datetime.fromtimestamp(ts).hour
                    hour_distribution[hour] += 1
                    
                    # Mark the sample as an anomaly
                    for sample in samples:
                        if abs(sample['timestamp'] - ts) < 60:  # Within a minute
                            sample['is_anomaly'] = True
                            sample['status'] = 'Anomaly'
                            break
                    
                    anomalies.append(anomaly)
            except Exception as e:
                if _debug: _log.debug(f"Error processing enhanced anomaly history: {e}")
    
    # Sort anomalies by timestamp (most recent first)
    anomalies.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Prepare chart data
    anomaly_chart_data = {
        'timestamps': [a['timestamp'] for a in anomalies],
        'values': [a['value'] for a in anomalies],
        'anomalyTypes': [a['types'] for a in anomalies]
    }
    
    # Time distribution data
    time_distribution_data = {
        'hourDistribution': hour_distribution
    }
    
    return anomalies, anomaly_type_counts, time_distribution_data, anomaly_chart_data

#
#   Rate monitoring dashboard
#

@bottle.route('/rate-monitoring')
@bottle.view('rate_monitoring')
@function_debugging
def rate_monitoring() -> Dict[str, Any]:
    """
    Enhanced rate monitoring dashboard with visualization.
    """
    # Get request parameters
    key = bottle.request.query.get('key', 'total')
    timerange = bottle.request.query.get('timerange', '1h')
    
    # Process time range
    start_time, end_time = process_time_range(timerange)
    
    # Get available keys
    available_keys = get_monitoring_keys()
    if not available_keys:
        available_keys = ['total']
    
    # If key is not in available keys, default to first key
    if key not in available_keys and available_keys:
        key = available_keys[0]
    
    # Get samples for the selected key
    samples = get_key_samples(key, start_time, end_time)
    
    # Get anomaly data
    anomalies, anomaly_type_counts, time_distribution_data, anomaly_chart_data = get_anomaly_data(key, samples)
    
    # Prepare chart data
    rate_chart_data = {
        'timestamps': [s['timestamp'] for s in samples],
        'values': [s['value'] for s in samples],
        'anomalies': [i for i, s in enumerate(samples) if s['is_anomaly']],
        'thresholds': []
    }
    
    # Check if there's a threshold configuration for this key
    threshold_key = f"{key}:threshold"
    threshold_config = r.get(threshold_key)
    if threshold_config:
        try:
            threshold_value = int(threshold_config)
            rate_chart_data['thresholds'] = [threshold_value]
        except Exception as e:
            if _debug: _log.debug(f"Error parsing threshold config: {e}")
    
    # Prepare anomaly details for tooltips
    rate_chart_data['anomalyDetails'] = {}
    for i, s in enumerate(samples):
        if s['is_anomaly']:
            # Find matching anomaly
            for a in anomalies:
                if a['timestamp'] == s['timestamp']:
                    rate_chart_data['anomalyDetails'][i] = {
                        'types': a['types'],
                        'score': a['score']
                    }
                    break
    
    # Prepare summary data
    summary = {
        'total_samples': len(samples),
        'total_anomalies': len(anomalies),
        'status': 'Normal',
        'status_color': 'green',
        'last_anomaly_time': 'None'
    }
    
    # Check current alarm status
    current_alarm = r.get(f"{key}:alarm")
    if current_alarm:
        summary['status'] = 'In Alarm'
        summary['status_color'] = 'red'
    
    # Get last anomaly time
    if anomalies:
        summary['last_anomaly_time'] = anomalies[0]['time_str']
    
    # Convert data to JSON for template
    rate_chart_data_json = json.dumps(rate_chart_data)
    anomaly_chart_data_json = json.dumps(anomaly_chart_data)
    anomaly_type_data_json = json.dumps(anomaly_type_counts)
    time_distribution_data_json = json.dumps(time_distribution_data)
    
    # Return data for template
    return {
        'title': f'Rate Monitoring: {key}',
        'key': key,
        'timerange': timerange,
        'available_keys': available_keys,
        'recent_samples': samples[-10:] if len(samples) > 10 else samples,
        'anomalies': anomalies[:20],  # Show only the 20 most recent anomalies
        'summary': summary,
        'rate_chart_data': rate_chart_data_json,
        'anomaly_chart_data': anomaly_chart_data_json,
        'anomaly_type_data': anomaly_type_data_json,
        'time_distribution_data': time_distribution_data_json,
        'body': ""
    }

#
#   Anomaly summary page
#

@bottle.route('/anomaly-summary')
@bottle.view('basic')
@function_debugging
def anomaly_summary() -> Dict[str, Any]:
    """
    Summary of all anomalies across different keys.
    """
    # Get all keys with anomalies
    keys_with_anomalies = []
    for key in get_monitoring_keys():
        alarm_history_key = f"{key}:alarm-history"
        if r.type(alarm_history_key) != b'none':
            keys_with_anomalies.append(key)
    
    # Build summary table
    body = DIV()
    h1 = H1("Anomaly Summary")
    body.append(h1)
    
    if not keys_with_anomalies:
        p = P("No anomalies detected.")
        body.append(p)
        return {'title': 'Anomaly Summary', 'body': str(body)}
    
    # Create summary table
    table = TABLE(CLASS="data-table")
    thead = THEAD()
    table.append(thead)
    tr = TR()
    thead.append(tr)
    tr.append(TH("Key"))
    tr.append(TH("Total Anomalies"))
    tr.append(TH("Current Status"))
    tr.append(TH("Last Anomaly"))
    tr.append(TH("Actions"))
    
    tbody = TBODY()
    table.append(tbody)
    
    for key in keys_with_anomalies:
        tr = TR()
        tbody.append(tr)
        
        # Key name
        tr.append(TD(key))
        
        # Total anomalies
        alarm_history = r.lrange(f"{key}:alarm-history", 0, -1)
        tr.append(TD(str(len(alarm_history))))
        
        # Current status
        current_alarm = r.get(f"{key}:alarm")
        if current_alarm:
            tr.append(TD("In Alarm", style="color: red; font-weight: bold;"))
        else:
            tr.append(TD("Normal", style="color: green;"))
        
        # Last anomaly
        if alarm_history:
            try:
                start_ts, _ = eval(alarm_history[0])
                tr.append(TD(AbsoluteTime(start_ts)))
            except Exception as e:
                tr.append(TD("Error"))
        else:
            tr.append(TD("None"))
        
        # Actions
        tr.append(TD(A("View Details", href=f"/rate-monitoring?key={key}")))
    
    body.append(table)
    
    p = P(B("Note: "), "For enhanced visualization of rate monitoring data with anomaly detection, visit the ", 
           A("Rate Monitoring Dashboard", href="/rate-monitoring"), ".")
    body.append(p)
    
    return {'title': 'Anomaly Summary', 'body': str(body)}

#
#   Anomaly detail page
#

@bottle.route('/anomaly-detail/:key/:timestamp')
@bottle.view('basic')
@function_debugging
def anomaly_detail(key: str, timestamp: str) -> Dict[str, Any]:
    """
    Detailed view of a specific anomaly.
    """
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return {'title': 'Error', 'body': str(P("Invalid timestamp."))}
    
    body = DIV()
    h1 = H1(f"Anomaly Detail: {key}")
    body.append(h1)
    
    # Find the anomaly
    found = False
    
    # Check alarm history
    alarm_history_key = f"{key}:alarm-history"
    if r.type(alarm_history_key) != b'none':
        history_data = r.lrange(alarm_history_key, 0, -1)
        
        for entry in history_data:
            try:
                start_ts, end_ts = eval(entry)
                if start_ts == timestamp_int:
                    found = True
                    
                    # Display basic info
                    info_div = DIV(CLASS="chart-info")
                    body.append(info_div)
                    
                    info_div.append(P(B("Anomaly Type: "), "Threshold Violation"))
                    info_div.append(P(B("Start Time: "), AbsoluteTime(start_ts)))
                    info_div.append(P(B("End Time: "), AbsoluteTime(end_ts) if end_ts else "Ongoing"))
                    
                    # Get samples around this time
                    window_start = start_ts - 300  # 5 minutes before
                    window_end = end_ts + 300 if end_ts else start_ts + 3600  # 5 minutes after or 1 hour if ongoing
                    
                    samples = get_key_samples(key, window_start, window_end)
                    
                    # Create a small visualization
                    if samples:
                        # Find the anomaly value
                        anomaly_value = None
                        for s in samples:
                            if s['timestamp'] == start_ts:
                                anomaly_value = s['value']
                                break
                        
                        if anomaly_value is not None:
                            info_div.append(P(B("Value: "), str(anomaly_value)))
                        
                        # Create a simple chart div using Flot (for compatibility)
                        chart_div = DIV(id="detail-plot", style="width:800px;height:300px;")
                        body.append(chart_div)
                        
                        # Prepare data for the chart
                        chart_data = []
                        normal_data = []
                        anomaly_data = []
                        
                        for s in samples:
                            t = s['timestamp']
                            v = s['value']
                            
                            js_time = MapTime(t)
                            
                            if t >= start_ts and (end_ts is None or t <= end_ts):
                                anomaly_data.append(f"[{js_time}, {v}]")
                            else:
                                normal_data.append(f"[{js_time}, {v}]")
                        
                        if normal_data:
                            chart_data.append('{ color: "#700", label: "Normal", data: [%s] }' % ', '.join(normal_data))
                        
                        if anomaly_data:
                            chart_data.append('{ color: "#f00", label: "Anomaly", data: [%s] }' % ', '.join(anomaly_data))
                        
                        # Add the chart script
                        script = SCRIPT("""
                        $(function () {
                            var d = [ %s ];
                            $.plot($("#detail-plot"), d, { 
                                xaxis: { mode: "time" },
                                grid: { hoverable: true }
                            });
                            
                            $("#detail-plot").bind("plothover", function (event, pos, item) {
                                if (item) {
                                    var x = item.datapoint[0];
                                    var y = item.datapoint[1];
                                    
                                    // Convert timestamp to readable time
                                    var date = new Date(x);
                                    var timeStr = $.strftime("%%Y-%%m-%%d %%H:%%M:%%S", date, true);
                                    
                                    $("#tooltip").html(timeStr + ": " + y)
                                        .css({top: item.pageY+5, left: item.pageX+5})
                                        .fadeIn(200);
                                } else {
                                    $("#tooltip").hide();
                                }
                            });
                            
                            $("<div id='tooltip'></div>").css({
                                position: "absolute",
                                display: "none",
                                border: "1px solid #fdd",
                                padding: "2px",
                                "background-color": "#fee",
                                opacity: 0.80
                            }).appendTo("body");
                        });
                        """ % ', '.join(chart_data))
                        body.append(script)
                    
                    # Add a back link
                    body.append(P(A("Back to Rate Monitoring", href=f"/rate-monitoring?key={key}")))
                    break
            except Exception as e:
                if _debug: _log.debug(f"Error processing alarm history entry {entry}: {e}")
    
    # Check enhanced anomaly history if available
    if not found and ANOMALY_DETECTION_AVAILABLE:
        enhanced_history_key = f"{key}:enhanced_anomaly_history"
        enhanced_history = r.get(enhanced_history_key)
        
        if enhanced_history:
            try:
                history_data = json.loads(enhanced_history)
                
                for entry in history_data:
                    ts = entry.get('timestamp')
                    if ts == timestamp_int:
                        found = True
                        
                        # Display enhanced info
                        info_div = DIV(CLASS="chart-info")
                        body.append(info_div)
                        
                        value = entry.get('value')
                        result = entry.get('result', {})
                        
                        anomaly_types = result.get('anomaly_types', ['unknown'])
                        anomaly_score = result.get('anomaly_score', 0.5)
                        
                        info_div.append(P(B("Anomaly Types: "), ', '.join(anomaly_types)))
                        info_div.append(P(B("Anomaly Score: "), f"{anomaly_score:.2f}"))
                        info_div.append(P(B("Timestamp: "), AbsoluteTime(ts)))
                        info_div.append(P(B("Value: "), str(value)))
                        
                        # Add detailed information if available
                        detector_results = result.get('detector_results', {})
                        if detector_results:
                            info_div.append(H3("Detector Results"))
                            
                            for detector, det_result in detector_results.items():
                                if det_result.get('is_anomaly'):
                                    info_div.append(P(B(f"{detector}: "), "Anomaly detected"))
                                    
                                    # Add specific detector details
                                    if detector == 'threshold' and 'consecutive_count' in det_result:
                                        info_div.append(P(B("Consecutive Count: "), str(det_result['consecutive_count'])))
                                    
                                    if detector == 'statistical' and 'z_score' in det_result:
                                        info_div.append(P(B("Z-Score: "), f"{det_result['z_score']:.2f}"))
                                    
                                    if detector == 'trend' and 'trend' in det_result:
                                        info_div.append(P(B("Trend Coefficient: "), f"{det_result['trend']:.2f}"))
                                    
                                    if detector == 'time_aware' and 'time_context' in det_result:
                                        time_ctx = det_result['time_context']
                                        info_div.append(P(B("Time Context: "), time_ctx.get('time_str', '')))
                        
                        # Add a back link
                        body.append(P(A("Back to Rate Monitoring", href=f"/rate-monitoring?key={key}")))
                        break
            except Exception as e:
                if _debug: _log.debug(f"Error processing enhanced anomaly history: {e}")
    
    if not found:
        body.append(P("Anomaly not found."))
        body.append(P(A("Back to Rate Monitoring", href=f"/rate-monitoring?key={key}")))
    
    return {'title': f'Anomaly Detail: {key}', 'body': str(body)}

#
#   Alerts
#

@bottle.route('/alerts')
def alerts_dashboard() -> Dict[str, Any]:
    """Display the alerts dashboard with active alerts and history."""
    # Get the alert manager
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    # Get active alerts by severity
    active_alerts = manager.get_active_alerts()
    
    # Sort alerts by timestamp (newest first) and format for display
    sorted_alerts = sorted(active_alerts, key=lambda a: a.timestamp, reverse=True)
    formatted_alerts = []
    
    for alert in sorted_alerts:
        # Map severity level to Bootstrap classes
        level_classes = {
            alert_manager.AlertLevel.DEBUG: "bg-debug",
            alert_manager.AlertLevel.INFO: "bg-info",
            alert_manager.AlertLevel.WARNING: "bg-warning",
            alert_manager.AlertLevel.ALERT: "bg-alert", 
            alert_manager.AlertLevel.CRITICAL: "bg-critical",
            alert_manager.AlertLevel.EMERGENCY: "bg-emergency"
        }
        
        formatted_alerts.append({
            'uuid': alert.uuid,
            'key': alert.key,
            'message': alert.message,
            'entity': alert.entity,
            'level': alert.level,
            'level_str': alert_manager.AlertLevel.to_string(alert.level).upper(),
            'level_class': level_classes.get(alert.level, "bg-secondary"),
            'time_str': datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'acknowledged': alert.acknowledged,
            'resolved': alert.resolved,
            'details': alert.details
        })
    
    # Get alert history
    alert_history = manager.get_alert_history(max_results=50)
    formatted_history = []
    
    for alert in alert_history:
        level_classes = {
            alert_manager.AlertLevel.DEBUG: "bg-debug",
            alert_manager.AlertLevel.INFO: "bg-info",
            alert_manager.AlertLevel.WARNING: "bg-warning",
            alert_manager.AlertLevel.ALERT: "bg-alert", 
            alert_manager.AlertLevel.CRITICAL: "bg-critical",
            alert_manager.AlertLevel.EMERGENCY: "bg-emergency"
        }
        
        formatted_history.append({
            'uuid': alert.uuid,
            'key': alert.key,
            'message': alert.message,
            'entity': alert.entity,
            'level': alert.level,
            'level_str': alert_manager.AlertLevel.to_string(alert.level).upper(),
            'level_class': level_classes.get(alert.level, "bg-secondary"),
            'time_str': datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'details': alert.details
        })
    
    # Get maintenance windows
    maintenance_windows = []
    for window in manager.maintenance_windows:
        maintenance_windows.append({
            'name': window.name,
            'start_time': window.start_time,
            'end_time': window.end_time,
            'start_time_str': datetime.fromtimestamp(window.start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time_str': datetime.fromtimestamp(window.end_time).strftime('%Y-%m-%d %H:%M:%S'),
            'entity_patterns': window.entity_patterns,
            'key_patterns': window.key_patterns,
            'active': window.is_active()
        })
    
    # Count alerts by severity
    warning_count = sum(1 for a in active_alerts if a.level == alert_manager.AlertLevel.WARNING)
    alert_count = sum(1 for a in active_alerts if a.level == alert_manager.AlertLevel.ALERT)
    critical_count = sum(1 for a in active_alerts if a.level >= alert_manager.AlertLevel.CRITICAL)
    
    # Add Bootstrap and custom scripts
    scripts = [
        '//cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js',
        '//cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
        '//cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/js/all.min.js'
    ]
    
    # Add Bootstrap and custom styles
    stylesheets = [
        '//cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
        '//cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
    ]
    
    return {
        'title': "BACmon Alerts",
        'active_alerts': formatted_alerts,
        'alert_history': formatted_history,
        'maintenance_windows': maintenance_windows,
        'active_count': len(active_alerts),
        'warning_count': warning_count,
        'critical_count': critical_count,
        'resolved_count': len(alert_history),
        'scripts': scripts,
        'stylesheets': stylesheets
    }

@bottle.route('/alerts/details/<uuid>')
def alert_details(uuid: str) -> Dict[str, Any]:
    """Get detailed information about a specific alert."""
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    # Try to find the alert in active alerts
    alert = next((a for a in manager.active_alerts.values() if a.uuid == uuid), None)
    
    # If not found in active alerts, check history
    if not alert:
        alert = next((a for a in manager.alert_history if a.uuid == uuid), None)
    
    if not alert:
        bottle.response.status = 404
        return {'error': 'Alert not found'}
    
    # Map severity level to Bootstrap classes
    level_classes = {
        alert_manager.AlertLevel.DEBUG: "bg-debug",
        alert_manager.AlertLevel.INFO: "bg-info",
        alert_manager.AlertLevel.WARNING: "bg-warning",
        alert_manager.AlertLevel.ALERT: "bg-alert", 
        alert_manager.AlertLevel.CRITICAL: "bg-critical",
        alert_manager.AlertLevel.EMERGENCY: "bg-emergency"
    }
    
    return {
        'uuid': alert.uuid,
        'key': alert.key,
        'message': alert.message,
        'entity': alert.entity,
        'source': alert.source,
        'level': alert.level,
        'level_str': alert_manager.AlertLevel.to_string(alert.level).upper(),
        'level_class': level_classes.get(alert.level, "bg-secondary"),
        'time_str': datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'acknowledged': alert.acknowledged,
        'resolved': alert.resolved,
        'notifications_sent': alert.notifications_sent,
        'details': alert.details
    }

@bottle.route('/alerts/acknowledge', method='POST')
def acknowledge_alert() -> Dict[str, str]:
    """Acknowledge an alert."""
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    uuid = bottle.request.forms.get('uuid')
    if not uuid:
        bottle.response.status = 400
        return {'error': 'Missing alert UUID'}
    
    success = manager.acknowledge_alert(uuid)
    if not success:
        bottle.response.status = 404
        return {'error': 'Alert not found'}
    
    # Redirect back to alerts page
    bottle.redirect('/alerts')

@bottle.route('/alerts/resolve', method='POST')
def resolve_alert() -> Dict[str, str]:
    """Resolve an alert."""
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    uuid = bottle.request.forms.get('uuid')
    if not uuid:
        bottle.response.status = 400
        return {'error': 'Missing alert UUID'}
    
    success = manager.resolve_alert(uuid)
    if not success:
        bottle.response.status = 404
        return {'error': 'Alert not found'}
    
    # Redirect back to alerts page
    bottle.redirect('/alerts')

@bottle.route('/alerts/maintenance', method='POST')
def create_maintenance() -> Dict[str, str]:
    """Create a new maintenance window."""
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    # Get form data
    name = bottle.request.forms.get('name')
    start_time_str = bottle.request.forms.get('start_time')
    end_time_str = bottle.request.forms.get('end_time')
    entity_patterns_str = bottle.request.forms.get('entity_patterns', '')
    
    if not all([name, start_time_str, end_time_str]):
        bottle.response.status = 400
        return {'error': 'Missing required fields'}
    
    # Parse datetime values
    try:
        start_time = datetime.fromisoformat(start_time_str).timestamp()
        end_time = datetime.fromisoformat(end_time_str).timestamp()
    except ValueError:
        bottle.response.status = 400
        return {'error': 'Invalid date format'}
    
    # Parse entity patterns
    entity_patterns = [p.strip() for p in entity_patterns_str.split(',') if p.strip()]
    
    # Create the maintenance window
    window = alert_manager.MaintenanceWindow(
        name=name,
        start_time=int(start_time),
        end_time=int(end_time),
        entity_patterns=entity_patterns
    )
    
    manager.add_maintenance_window(window)
    
    # Redirect back to alerts page
    bottle.redirect('/alerts')

@bottle.route('/alerts/maintenance/delete', method='POST')
def delete_maintenance() -> Dict[str, str]:
    """Delete a maintenance window."""
    r = get_redis_client()
    manager = alert_manager.get_alert_manager(r)
    
    name = bottle.request.forms.get('name')
    if not name:
        bottle.response.status = 400
        return {'error': 'Missing maintenance window name'}
    
    success = manager.remove_maintenance_window(name)
    if not success:
        bottle.response.status = 404
        return {'error': 'Maintenance window not found'}
    
    # Redirect back to alerts page
    bottle.redirect('/alerts')

@bottle.route('/api/alerts', method='GET')
def api_get_alerts() -> Dict[str, Any]:
    """API endpoint to get active alerts."""
    try:
        r = get_redis_client()
        manager = alert_manager.get_alert_manager(r)
        
        min_level_str = bottle.request.query.get('min_level', 'warning')
        min_level = alert_manager.AlertLevel.from_string(min_level_str)
        
        alerts = manager.get_active_alerts(min_level=min_level)
        formatted_alerts = [alert.to_dict() for alert in alerts]
        
        return create_api_response({
            'alerts': formatted_alerts,
            'count': len(formatted_alerts),
            'min_level': min_level_str
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return create_api_response(error=f"Alert retrieval error: {str(e)}", code=500)

@bottle.route('/api/alerts/history', method='GET')
def api_get_alert_history() -> Dict[str, Any]:
    """API endpoint to get alert history."""
    try:
        r = get_redis_client()
        manager = alert_manager.get_alert_manager(r)
        
        min_level_str = bottle.request.query.get('min_level', 'warning')
        min_level = alert_manager.AlertLevel.from_string(min_level_str)
        
        max_results = int(bottle.request.query.get('max', '100'))
        
        alerts = manager.get_alert_history(min_level=min_level, max_results=max_results)
        formatted_alerts = [alert.to_dict() for alert in alerts]
        
        return create_api_response({
            'alerts': formatted_alerts,
            'count': len(formatted_alerts),
            'min_level': min_level_str,
            'max_results': max_results
        })
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        return create_api_response(error=f"Alert history error: {str(e)}", code=500)

@bottle.route('/api/alerts/<uuid>', method='GET')
def api_get_alert(uuid: str) -> Dict[str, Any]:
    """API endpoint to get a specific alert."""
    try:
        r = get_redis_client()
        manager = alert_manager.get_alert_manager(r)
        
        # Try to find the alert in active alerts
        alert = next((a for a in manager.active_alerts.values() if a.uuid == uuid), None)
        
        # If not found in active alerts, check history
        if not alert:
            alert = next((a for a in manager.alert_history if a.uuid == uuid), None)
        
        if not alert:
            return create_api_response(error='Alert not found', code=404)
        
        return create_api_response(alert.to_dict())
    except Exception as e:
        logger.error(f"Error getting alert {uuid}: {e}")
        return create_api_response(error=f"Alert retrieval error: {str(e)}", code=500)

@bottle.route('/api/alerts/<uuid>/acknowledge', method='POST')
def api_acknowledge_alert(uuid: str) -> Dict[str, Any]:
    """API endpoint to acknowledge an alert."""
    try:
        r = get_redis_client()
        manager = alert_manager.get_alert_manager(r)
        
        success = manager.acknowledge_alert(uuid)
        if not success:
            return create_api_response(error='Alert not found', code=404)
        
        return create_api_response({
            'success': True, 
            'uuid': uuid, 
            'status': 'acknowledged'
        })
    except Exception as e:
        logger.error(f"Error acknowledging alert {uuid}: {e}")
        return create_api_response(error=f"Alert acknowledgment error: {str(e)}", code=500)

@bottle.route('/api/alerts/<uuid>/resolve', method='POST')
def api_resolve_alert(uuid: str) -> Dict[str, Any]:
    """API endpoint to resolve an alert."""
    try:
        r = get_redis_client()
        manager = alert_manager.get_alert_manager(r)
        
        success = manager.resolve_alert(uuid)
        if not success:
            return create_api_response(error='Alert not found', code=404)
        
        return create_api_response({
            'success': True, 
            'uuid': uuid, 
            'status': 'resolved'
        })
    except Exception as e:
        logger.error(f"Error resolving alert {uuid}: {e}")
        return create_api_response(error=f"Alert resolution error: {str(e)}", code=500)

@bottle.route('/extended_metrics')
@bottle.view('extended_metrics')
def extended_metrics_dashboard():
    """Render the extended metrics dashboard."""
    # Get all available metric keys
    metric_keys = []
    try:
        # Get redis connection
        redis_client = get_redis_client()
        
        # Get all keys
        all_keys = redis_client.keys('*:*:*')
        
        # Extract unique metric keys
        for key in all_keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            parts = key_str.split(':')
            if len(parts) >= 2 and parts[-1] not in ('s', 'm', 'h', 'i'):
                # Skip internal keys and interval markers
                continue
            
            # Extract the metric key (everything before the last two parts)
            metric_key = ':'.join(parts[:-2]) if len(parts) > 2 else parts[0]
            if metric_key and metric_key not in metric_keys:
                metric_keys.append(metric_key)
    except Exception as e:
        logger.error(f"Error getting metric keys: {e}")
    
    return {'metric_keys': metric_keys}

@bottle.route('/api/extended_metrics')
def api_extended_metrics():
    """API endpoint for extended metrics data."""
    try:
        # Get request parameters
        key = bottle.request.query.get('key')
        metric_type = bottle.request.query.get('type') or 'count'
        interval = bottle.request.query.get('interval') or 's'
        
        # Validate parameters
        if not key:
            return create_api_response(error='Missing metric key parameter', code=400)
        
        # Get redis connection
        redis_client = get_redis_client()
        
        # Build Redis key
        redis_key = f"{key}:{metric_type}:{interval}"
        
        # Get time series data
        raw_data = redis_client.lrange(redis_key, 0, 1000)
        
        # Process the data
        time_series = []
        for item in raw_data:
            try:
                # Parse the sample
                item_data = eval(item.decode('utf-8') if isinstance(item, bytes) else item)
                timestamp = item_data[0]
                
                # Handle different value formats
                value = item_data[1]
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    # Try to parse JSON
                    try:
                        import json
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                
                time_series.append({
                    'timestamp': timestamp,
                    'value': value
                })
            except Exception as e:
                logger.error(f"Error processing metric data: {e}")
                continue
        
        # Sort by timestamp (newest first)
        time_series.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Get current value (most recent)
        current = time_series[0]['value'] if time_series else None
        
        # Calculate statistics
        statistics = calculate_metric_statistics(time_series, metric_type)
        
        # Get threshold values
        thresholds = get_metric_thresholds(key, metric_type)
        
        # Return the data
        return create_api_response({
            'key': key,
            'metric_type': metric_type,
            'interval': interval,
            'time_series': time_series,
            'current': current,
            'statistics': statistics,
            'thresholds': thresholds
        })
    except Exception as e:
        logger.error(f"Error retrieving extended metrics: {e}")
        return create_api_response(error=f"Extended metrics error: {str(e)}", code=500)

@bottle.route('/api/metrics/:key')
def api_metrics(key: str) -> Dict[str, Any]:
    """API endpoint to get metrics data for a specific key."""
    try:
        # Check if metrics.py is available
        try:
            import metrics
            metrics_available = True
        except ImportError:
            metrics_available = False
            
        # Prepare response data
        response_data = {
            'key': key,
            'metrics_available': metrics_available
        }
        
        if not metrics_available:
            # Return basic data if extended metrics are not available
            response_data['count'] = {
                'current': int(r.get(key) or 0)
            }
            
            # Get time series data
            for label in ['s', 'm', 'h']:
                samples = []
                raw_samples = r.lrange(f"{key}:{label}", 0, 50)
                if raw_samples:
                    samples = [eval(s.decode('utf-8')) for s in raw_samples]
                    samples.reverse()
                    response_data[f'samples_{label}'] = samples
                    
            return create_api_response(response_data)
        
        # Get metrics manager
        metrics_manager = metrics.get_metric_manager(r)
        
        # Get current values for all metric types
        for metric_type in [
            metrics.MetricType.COUNT,
            metrics.MetricType.SIZE,
            metrics.MetricType.PROTOCOL,
            metrics.MetricType.ERROR_RATE,
            metrics.MetricType.RESPONSE_TIME,
            metrics.MetricType.CONNECTION
        ]:
            # Get current value
            current_value = metrics_manager.get_metric_value(key, metric_type)
            
            # Get time series data
            samples = []
            raw_samples = r.lrange(f"{key}:{metric_type}:s", 0, 50)  # Get last 50 samples
            if raw_samples:
                for sample in raw_samples:
                    try:
                        timestamp, value = eval(sample.decode('utf-8'))
                        samples.append([timestamp, json.loads(value) if isinstance(value, str) else value])
                    except Exception as e:
                        if _debug: _log.debug("Error parsing sample: %s", e)
                
                samples.reverse()  # Most recent first
            
            # Add to response
            response_data[metric_type] = {
                'current': current_value,
                'samples': samples
            }
        
        return create_api_response(response_data)
    except Exception as e:
        logger.error(f"Error getting metrics for key {key}: {e}")
        return create_api_response(error=f"Metrics error: {str(e)}", code=500)

@bottle.route('/api/metrics')
def api_metrics_list() -> Dict[str, Any]:
    """API endpoint to get a list of all available metrics."""
    try:
        # Get all message sets
        message_sets = []
        for key in r.keys("*"):
            key = key.decode('utf-8')
            if ":" not in key and "-" not in key and "." not in key:
                count = int(r.get(key) or 0)
                message_sets.append({
                    'key': key,
                    'count': count
                })
        
        return create_api_response({
            'metrics': sorted(message_sets, key=lambda x: x['key']),
            'total_count': len(message_sets)
        })
    except Exception as e:
        logger.error(f"Error getting metrics list: {e}")
        return create_api_response(error=f"Metrics list error: {str(e)}", code=500)

#
# REST API Enhancement - Standardized Response System
#

def create_api_response(data: Any = None, error: Optional[str] = None, 
                       status: str = 'success', code: int = 200,
                       version: str = __version__) -> Dict[str, Any]:
    """
    Create a standardized API response format.
    
    Args:
        data: The response data payload
        error: Error message if applicable
        status: Response status ('success', 'error', 'warning')
        code: HTTP status code
        version: API version
        
    Returns:
        Standardized response dictionary
    """
    response = {
        'status': status,
        'timestamp': int(_time()),
        'version': version,
        'code': code
    }
    
    if error:
        response['error'] = error
        response['status'] = 'error'
    else:
        response['data'] = data
    
    bottle.response.status = code
    bottle.response.content_type = 'application/json'
    return response

def get_redis_client() -> Any:
    """Get Redis client instance for API operations."""
    return r

def parse_time_range(request_args: Dict[str, str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse time range parameters from request.
    
    Args:
        request_args: Dictionary of request parameters
        
    Returns:
        Tuple of (start_time, end_time) in seconds since epoch
    """
    start_time = None
    end_time = None
    
    # Check for explicit timestamps
    if 'start' in request_args:
        try:
            start_time = int(request_args['start'])
        except ValueError:
            pass
    
    if 'end' in request_args:
        try:
            end_time = int(request_args['end'])
        except ValueError:
            pass
    
    # Check for relative time ranges
    if 'range' in request_args:
        now = int(_time())
        range_str = request_args['range'].lower()
        
        if range_str == '1h':
            start_time = now - 3600
        elif range_str == '6h':
            start_time = now - 21600
        elif range_str == '24h':
            start_time = now - 86400
        elif range_str == '7d':
            start_time = now - 604800
        elif range_str == '30d':
            start_time = now - 2592000
        
        if start_time:
            end_time = now
    
    return start_time, end_time

def get_pagination_params(request_args: Dict[str, str]) -> Tuple[int, int]:
    """
    Parse pagination parameters from request.
    
    Args:
        request_args: Dictionary of request parameters
        
    Returns:
        Tuple of (offset, limit)
    """
    offset = 0
    limit = 100  # Default limit
    
    if 'offset' in request_args:
        try:
            offset = max(0, int(request_args['offset']))
        except ValueError:
            pass
    
    if 'limit' in request_args:
        try:
            limit = min(1000, max(1, int(request_args['limit'])))  # Max 1000, min 1
        except ValueError:
            pass
    
    return offset, limit

#
# Enhanced Core API Endpoints
#

@bottle.route('/api/status', method='GET')
@require_auth('read')
def api_system_status() -> Dict[str, Any]:
    """API endpoint to get system status and health information."""
    try:
        # Get Redis client
        redis_client = get_redis_client()
        
        # Test Redis connection
        redis_available = False
        redis_info = {}
        try:
            redis_client.ping()
            redis_available = True
            redis_info = {
                'connected': True,
                'db_size': redis_client.dbsize(),
                'memory_usage': redis_client.info().get('used_memory', 0),
                'version': redis_client.info().get('redis_version', 'unknown')
            }
        except Exception as e:
            redis_info = {'connected': False, 'error': str(e)}
        
        # Get system information
        system_info = {
            'daemon_version': redis_client.get('daemon_version'),
            'startup_time': redis_client.get('startup_time'),
            'current_time': int(_time())
        }
        
        # Get monitoring statistics
        monitoring_keys = get_monitoring_keys()
        stats = {
            'total_keys': len(monitoring_keys),
            'active_monitoring': len([key for key in monitoring_keys if redis_client.exists(key)])
        }
        
        # Check for active alerts
        alert_count = 0
        try:
            manager = alert_manager.get_alert_manager(redis_client)
            alert_count = len(manager.get_active_alerts())
        except Exception:
            pass
        
        # Compile status data
        status_data = {
            'system': system_info,
            'redis': redis_info,
            'monitoring': stats,
            'alerts': {'active_count': alert_count},
            'services': {
                'redis': redis_available,
                'anomaly_detection': ANOMALY_DETECTION_AVAILABLE,
                'alerts': True  # Alert system is always available
            }
        }
        
        return create_api_response(status_data)
    
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return create_api_response(error=f"System status error: {str(e)}", code=500)

@bottle.route('/api/monitoring', method='GET')
@require_auth('read')
def api_monitoring_data() -> Dict[str, Any]:
    """API endpoint to get real-time monitoring data."""
    try:
        # Get request parameters
        request_args = dict(bottle.request.query)
        keys_filter = request_args.get('keys', '').split(',') if request_args.get('keys') else None
        interval = request_args.get('interval', 's')  # Default to seconds
        start_time, end_time = parse_time_range(request_args)
        offset, limit = get_pagination_params(request_args)
        
        # Get monitoring keys
        all_keys = get_monitoring_keys()
        
        # Filter keys if specified
        if keys_filter:
            keys = [key for key in all_keys if any(f in key for f in keys_filter if f)]
        else:
            keys = all_keys
        
        # Apply pagination to keys
        keys = keys[offset:offset + limit]
        
        # Collect monitoring data
        monitoring_data = {}
        for key in keys:
            try:
                # Get current value
                current_value = r.get(key)
                current_count = int(current_value) if current_value else 0
                
                # Get time series data
                redis_key = f"{key}:{interval}"
                samples = get_key_samples(key, start_time or 0, end_time or int(_time()))
                
                monitoring_data[key] = {
                    'current': current_count,
                    'interval': interval,
                    'samples': samples[-100:],  # Limit to last 100 samples
                    'sample_count': len(samples)
                }
                
            except Exception as e:
                if _debug: _log.debug(f"Error getting data for key {key}: {e}")
                monitoring_data[key] = {
                    'error': str(e),
                    'current': 0,
                    'samples': []
                }
        
        response_data = {
            'keys': list(monitoring_data.keys()),
            'total_available': len(all_keys),
            'interval': interval,
            'data': monitoring_data
        }
        
        if start_time or end_time:
            response_data['time_range'] = {
                'start': start_time,
                'end': end_time
            }
        
        return create_api_response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting monitoring data: {e}")
        return create_api_response(error=f"Monitoring data error: {str(e)}", code=500)

@bottle.route('/api/traffic', method='GET')
@require_auth('read')
def api_traffic_analysis() -> Dict[str, Any]:
    """API endpoint to get network traffic analysis data."""
    try:
        # Get request parameters
        request_args = dict(bottle.request.query)
        traffic_type = request_args.get('type', 'all')  # all, ip, bvll, network, application, error
        start_time, end_time = parse_time_range(request_args)
        
        # Define traffic categories
        traffic_categories = {
            'ip': 'ip-messages',
            'bvll': 'bvll-messages', 
            'network': 'network-messages',
            'application': 'application-messages',
            'error': 'error-messages'
        }
        
        traffic_data = {}
        
        if traffic_type == 'all':
            categories_to_fetch = traffic_categories.keys()
        elif traffic_type in traffic_categories:
            categories_to_fetch = [traffic_type]
        else:
            return create_api_response(error=f"Invalid traffic type: {traffic_type}", code=400)
        
        for category in categories_to_fetch:
            redis_key = traffic_categories[category]
            
            try:
                # Get message set
                messages = r.smembers(redis_key)
                message_list = [msg.decode('utf-8') if isinstance(msg, bytes) else msg for msg in messages]
                
                # Get recent samples for this category
                samples = []
                for interval in ['s', 'm', 'h']:
                    sample_key = f"{redis_key}:{interval}"
                    raw_samples = r.lrange(sample_key, 0, 50)
                    if raw_samples:
                        for sample in raw_samples:
                            try:
                                timestamp, count = eval(sample.decode('utf-8'))
                                if not start_time or (timestamp >= start_time):
                                    if not end_time or (timestamp <= end_time):
                                        samples.append({
                                            'timestamp': timestamp,
                                            'count': count,
                                            'interval': interval
                                        })
                            except Exception:
                                continue
                
                # Sort samples by timestamp
                samples.sort(key=lambda x: x['timestamp'], reverse=True)
                
                traffic_data[category] = {
                    'messages': message_list[:100],  # Limit to 100 recent messages
                    'message_count': len(message_list),
                    'samples': samples[:50],  # Limit to 50 recent samples
                    'current_rate': samples[0]['count'] if samples else 0
                }
                
            except Exception as e:
                if _debug: _log.debug(f"Error getting traffic data for {category}: {e}")
                traffic_data[category] = {
                    'error': str(e),
                    'messages': [],
                    'message_count': 0,
                    'samples': [],
                    'current_rate': 0
                }
        
        response_data = {
            'traffic_type': traffic_type,
            'categories': list(categories_to_fetch),
            'data': traffic_data
        }
        
        if start_time or end_time:
            response_data['time_range'] = {
                'start': start_time,
                'end': end_time
            }
        
        return create_api_response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting traffic analysis: {e}")
        return create_api_response(error=f"Traffic analysis error: {str(e)}", code=500)

@bottle.route('/api/devices', method='GET')
@require_auth('read')
def api_devices_info() -> Dict[str, Any]:
    """API endpoint to get BACnet device information."""
    try:
        # Get request parameters
        request_args = dict(bottle.request.query)
        include_undefined = request_args.get('include_undefined', 'false').lower() == 'true'
        
        # Get device-related message sets
        device_data = {}
        
        # Get Who-Is/I-Am data
        try:
            who_is_messages = r.smembers('who-is-messages')
            i_am_messages = r.smembers('i-am-messages')
            
            device_data['who_is'] = {
                'messages': [msg.decode('utf-8') if isinstance(msg, bytes) else msg 
                           for msg in who_is_messages],
                'count': len(who_is_messages)
            }
            
            device_data['i_am'] = {
                'messages': [msg.decode('utf-8') if isinstance(msg, bytes) else msg 
                           for msg in i_am_messages],
                'count': len(i_am_messages)
            }
            
        except Exception as e:
            if _debug: _log.debug(f"Error getting Who-Is/I-Am data: {e}")
            device_data['who_is'] = {'messages': [], 'count': 0, 'error': str(e)}
            device_data['i_am'] = {'messages': [], 'count': 0, 'error': str(e)}
        
        # Get undefined devices if requested
        if include_undefined:
            try:
                undefined_messages = r.smembers('undefined-devices')
                device_data['undefined'] = {
                    'messages': [msg.decode('utf-8') if isinstance(msg, bytes) else msg 
                               for msg in undefined_messages],
                    'count': len(undefined_messages)
                }
            except Exception as e:
                if _debug: _log.debug(f"Error getting undefined devices: {e}")
                device_data['undefined'] = {'messages': [], 'count': 0, 'error': str(e)}
        
        # Get device discovery rates
        discovery_rates = {}
        for message_type in ['who-is-messages', 'i-am-messages']:
            try:
                recent_samples = r.lrange(f"{message_type}:s", 0, 10)
                if recent_samples:
                    latest = eval(recent_samples[0].decode('utf-8'))
                    discovery_rates[message_type.replace('-messages', '')] = {
                        'timestamp': latest[0],
                        'rate': latest[1]
                    }
            except Exception:
                discovery_rates[message_type.replace('-messages', '')] = {
                    'timestamp': 0,
                    'rate': 0
                }
        
        response_data = {
            'devices': device_data,
            'discovery_rates': discovery_rates,
            'include_undefined': include_undefined
        }
        
        return create_api_response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting device information: {e}")
        return create_api_response(error=f"Device information error: {str(e)}", code=500)

@bottle.route('/api/anomalies', method='GET')
@require_auth('read')
def api_anomalies_data() -> Dict[str, Any]:
    """API endpoint to get anomaly detection data."""
    try:
        if not ANOMALY_DETECTION_AVAILABLE:
            return create_api_response(error="Anomaly detection not available", code=503)
        
        # Get request parameters
        request_args = dict(bottle.request.query)
        key = request_args.get('key')
        severity = request_args.get('severity', 'all')  # all, low, medium, high
        start_time, end_time = parse_time_range(request_args)
        offset, limit = get_pagination_params(request_args)
        
        anomaly_data = {}
        
        if key:
            # Get anomaly data for specific key
            try:
                samples = get_key_samples(key, start_time or 0, end_time or int(_time()))
                if samples:
                    anomalies, baseline, thresholds, stats = get_anomaly_data(key, samples)
                    
                    # Filter by severity if specified
                    if severity != 'all':
                        severity_map = {'low': 1, 'medium': 2, 'high': 3}
                        severity_threshold = severity_map.get(severity, 1)
                        anomalies = [a for a in anomalies if a.get('severity', 1) >= severity_threshold]
                    
                    # Apply pagination
                    anomalies = anomalies[offset:offset + limit]
                    
                    anomaly_data[key] = {
                        'anomalies': anomalies,
                        'baseline': baseline,
                        'thresholds': thresholds,
                        'statistics': stats,
                        'total_anomalies': len(anomalies)
                    }
                else:
                    anomaly_data[key] = {
                        'anomalies': [],
                        'baseline': {},
                        'thresholds': {},
                        'statistics': {},
                        'total_anomalies': 0
                    }
                    
            except Exception as e:
                if _debug: _log.debug(f"Error getting anomaly data for {key}: {e}")
                anomaly_data[key] = {'error': str(e)}
        else:
            # Get anomaly summary for all keys
            monitoring_keys = get_monitoring_keys()
            for monitoring_key in monitoring_keys[offset:offset + limit]:
                try:
                    samples = get_key_samples(monitoring_key, start_time or 0, end_time or int(_time()))
                    if samples:
                        anomalies, _, _, _ = get_anomaly_data(monitoring_key, samples)
                        
                        # Filter by severity
                        if severity != 'all':
                            severity_map = {'low': 1, 'medium': 2, 'high': 3}
                            severity_threshold = severity_map.get(severity, 1)
                            anomalies = [a for a in anomalies if a.get('severity', 1) >= severity_threshold]
                        
                        anomaly_data[monitoring_key] = {
                            'anomaly_count': len(anomalies),
                            'latest_anomaly': anomalies[0] if anomalies else None,
                            'severity_distribution': {
                                'low': len([a for a in anomalies if a.get('severity', 1) == 1]),
                                'medium': len([a for a in anomalies if a.get('severity', 1) == 2]),
                                'high': len([a for a in anomalies if a.get('severity', 1) == 3])
                            }
                        }
                except Exception as e:
                    if _debug: _log.debug(f"Error getting anomaly summary for {monitoring_key}: {e}")
                    anomaly_data[monitoring_key] = {'error': str(e)}
        
        response_data = {
            'key': key,
            'severity_filter': severity,
            'data': anomaly_data
        }
        
        if start_time or end_time:
            response_data['time_range'] = {
                'start': start_time,
                'end': end_time
            }
        
        return create_api_response(response_data)
    
    except Exception as e:
        logger.error(f"Error getting anomaly data: {e}")
        return create_api_response(error=f"Anomaly data error: {str(e)}", code=500)

@bottle.route('/api/export', method='GET')
@require_auth('read')
def api_export_data() -> Any:
    """API endpoint to export monitoring data in various formats."""
    try:
        # Get request parameters
        request_args = dict(bottle.request.query)
        export_format = request_args.get('format', 'json').lower()  # json, csv
        data_type = request_args.get('type', 'monitoring')  # monitoring, alerts, traffic, devices
        keys = request_args.get('keys', '').split(',') if request_args.get('keys') else None
        start_time, end_time = parse_time_range(request_args)
        
        if export_format not in ['json', 'csv']:
            return create_api_response(error="Invalid export format. Use 'json' or 'csv'", code=400)
        
        # Collect data based on type
        export_data = []
        
        if data_type == 'monitoring':
            monitoring_keys = get_monitoring_keys()
            if keys:
                monitoring_keys = [key for key in monitoring_keys if any(k in key for k in keys)]
            
            for key in monitoring_keys:
                samples = get_key_samples(key, start_time or 0, end_time or int(_time()))
                for sample in samples:
                    export_data.append({
                        'key': key,
                        'timestamp': sample.get('timestamp'),
                        'value': sample.get('value'),
                        'type': 'monitoring'
                    })
        
        elif data_type == 'alerts':
            try:
                manager = alert_manager.get_alert_manager(r)
                alerts = manager.get_alert_history(max_results=1000)
                for alert in alerts:
                    alert_dict = alert.to_dict()
                    alert_dict['type'] = 'alert'
                    export_data.append(alert_dict)
            except Exception as e:
                if _debug: _log.debug(f"Error exporting alerts: {e}")
        
        # Format output
        if export_format == 'csv':
            import csv
            import io
            
            if not export_data:
                return create_api_response(error="No data to export", code=404)
            
            # Create CSV
            output = io.StringIO()
            fieldnames = list(export_data[0].keys()) if export_data else []
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(export_data)
            
            csv_content = output.getvalue()
            output.close()
            
            # Set response headers for CSV download
            bottle.response.content_type = 'text/csv'
            bottle.response.headers['Content-Disposition'] = f'attachment; filename="bacmon_export_{data_type}_{int(_time())}.csv"'
            return csv_content
        
        else:  # JSON format
            return create_api_response({
                'export_type': data_type,
                'format': export_format,
                'record_count': len(export_data),
                'data': export_data
            })
    
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return create_api_response(error=f"Export error: {str(e)}", code=500)

def calculate_metric_statistics(time_series, metric_type):
    """Calculate statistics for the metric data."""
    if not time_series:
        return {'min': None, 'max': None, 'avg': None}
    
    # Extract values based on metric type
    values = []
    for item in time_series:
        value = item['value']
        
        if metric_type == 'count':
            values.append(float(value) if value is not None else 0)
        elif metric_type == 'size':
            if isinstance(value, dict):
                values.append(float(value.get('avg', 0)) if value.get('avg') is not None else 0)
            else:
                values.append(float(value) if value is not None else 0)
        elif metric_type == 'protocol':
            if isinstance(value, dict):
                values.append(float(value.get('total', 0)) if value.get('total') is not None else 0)
            else:
                values.append(float(value) if value is not None else 0)
        elif metric_type == 'error_rate':
            if isinstance(value, dict):
                values.append(float(value.get('rate', 0)) if value.get('rate') is not None else 0)
            else:
                values.append(float(value) if value is not None else 0)
        elif metric_type == 'response_time':
            if isinstance(value, dict):
                values.append(float(value.get('avg', 0)) if value.get('avg') is not None else 0)
            else:
                values.append(float(value) if value is not None else 0)
        elif metric_type == 'connection':
            if isinstance(value, dict):
                values.append(float(value.get('active', 0)) if value.get('active') is not None else 0)
            else:
                values.append(float(value) if value is not None else 0)
        else:
            # Generic handling
            if isinstance(value, dict) and 'value' in value:
                values.append(float(value['value']) if value['value'] is not None else 0)
            elif isinstance(value, (int, float)):
                values.append(float(value))
            else:
                values.append(0)
    
    # Calculate statistics
    if not values:
        return {'min': None, 'max': None, 'avg': None}
    
    return {
        'min': min(values),
        'max': max(values),
        'avg': sum(values) / len(values)
    }

def get_metric_thresholds(key, metric_type):
    """Get thresholds for the metric type."""
    # Default thresholds based on metric type
    default_thresholds = {
        'count': 20,
        'size': {'avg': 2000, 'max': 10000},
        'error_rate': 5.0,
        'response_time': {'avg': 500, 'p95': 1000},
        'connection': {'new': 50, 'active': 200}
    }
    
    # Try to get actual thresholds from configuration
    try:
        # Check if there's a SampleRateTask for this key
        from enhanced_rate_monitoring import EnhancedSampleRateTask
        import importlib
        
        # Try to import metrics module to get constants
        metrics_module = importlib.import_module('metrics')
        MetricType = getattr(metrics_module, 'MetricType', None)
        
        # Check if the BACmon module has tasks available
        import BACmon
        if hasattr(BACmon, 'rate_tasks'):
            for task in BACmon.rate_tasks:
                # Check if it's an EnhancedSampleRateTask
                if hasattr(task, 'enhanced_task') and task.enhanced_task.key == key:
                    # Check if the task has thresholds for this metric type
                    if hasattr(task.enhanced_task, 'thresholds') and MetricType:
                        metric_type_const = getattr(MetricType, metric_type.upper(), None)
                        if metric_type_const and metric_type_const in task.enhanced_task.thresholds:
                            return task.enhanced_task.thresholds[metric_type_const]
                # Check if it's a regular SampleRateTask
                elif hasattr(task, 'key') and task.key == key:
                    # For regular tasks, only return thresholds for count metrics
                    if metric_type == 'count':
                        return task.maxValue
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not get thresholds from tasks: {e}")
    
    # Return default thresholds if no specific thresholds found
    return default_thresholds.get(metric_type, 10)

#
# Extended Metrics Dashboard Routes
#

@bottle.route('/api-dashboard')
@bottle.view('api_dashboard')
@function_debugging
def api_dashboard() -> Dict[str, Any]:
    """API Dashboard page."""
    if _debug: api_dashboard._debug("api_dashboard")
    
    context = get_template_context()
    return context

@bottle.route('/dashboard')
@bottle.view('dashboard')
@function_debugging
def main_dashboard() -> Dict[str, Any]:
    """Main BACmon Dashboard page."""
    if _debug: main_dashboard._debug("main_dashboard")
    
    context = get_template_context()
    context['version'] = __version__
    return context

@bottle.route('/metrics')
@bottle.view('basic')
def metrics_dashboard() -> Dict[str, Any]:
    """Display a list of all available metrics."""
    body = DIV()
    body.append(H1("Available Metrics"))
    
    # Get all message sets
    message_sets = set()
    for key in r.keys("*"):
        key = key.decode('utf-8')
        if ":" not in key and "-" not in key and "." not in key:
            message_sets.add(key)
    
    # Create a table of message sets
    table = TABLE(Class="table table-striped")
    table.append(THEAD(TR(TH("Message Set"), TH("Count"), TH("Actions"))))
    tbody = TBODY()
    
    for msg_set in sorted(message_sets):
        count = len(r.smembers(msg_set))
        row = TR()
        row.append(TD(A(msg_set, href="/" + msg_set)))
        row.append(TD(str(count)))
        row.append(TD(A("View Extended Metrics", href="/metrics/" + msg_set, Class="btn btn-primary btn-sm")))
        tbody.append(row)
    
    table.append(tbody)
    body.append(table)
    
    return {'title': 'BACmon Extended Metrics', 'body': body}

@bottle.route('/metrics/:key')
@bottle.view('extended_metrics')
def extended_metrics(key: str) -> Dict[str, Any]:
    """Display the extended metrics dashboard for a specific key."""
    # Check if the key exists
    if not r.exists(key):
        bottle.abort(404, f"Metric key '{key}' not found")
    
    return {'key': key}

#
#   __main__
#

if __name__ == "__main__":

    try:
        if _debug: _log.debug("running")

        bottle.run(host='', port=9090)

    except Exception as e:
        if _debug: _log.exception("an error has occurred: %s", e)
        sys.exit(1)
    finally:
        if _debug: _log.debug("finally")
        sys.exit(0)

else:
    application = bottle.default_app()

def get_template_context() -> Dict[str, Any]:
    """Get common template context including authentication status."""
    context = {}
    
    if AUTH_AVAILABLE:
        auth = get_auth_manager(r)
        session_token = bottle.request.get_cookie('session_token')
        if session_token:
            session_data = auth.validate_session(session_token)
            if session_data:
                context['auth_user'] = session_data['user_id']
                context['auth_permissions'] = session_data['permissions']
    
    return context