#!/usr/bin/python

"""
Time Utilities
"""

import re
import types
import time
import datetime
import locale
import logging
from datetime import datetime, timedelta, tzinfo
import pytz
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Callable, Iterator, Match, Pattern, cast, Type, overload

from collections import namedtuple

# Import from the compatibility module instead of directly from bacpypes
from bacpypes_compat import set_bacpypes_version, get_debugging

# Initialize bacpypes version (default to bacpypes, will fall back to bacpypes3 if needed)
set_bacpypes_version(False)  # Use bacpypes by default

# Get debugging components
function_debugging, _, Logging = get_debugging()

# some debugging
_log = logging.getLogger(__name__)

# keep everything UTC if possible
UTC = pytz.utc

#   we are Eastern
LocalTimeZone = pytz.timezone('US/Eastern')

#
#   _FixedOffset
#

class _FixedOffset(tzinfo, Logging):
    """Fixed offset in minutes east from UTC."""

    _debug = 0
    
    def __init__(self, offset: int, name: str) -> None:
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt: Optional[datetime]) -> timedelta:
        return self.__offset

    def tzname(self, dt: Optional[datetime]) -> str:
        return self.__name

    def dst(self, dt: Optional[datetime]) -> timedelta:
        return timedelta(0)

    def __repr__(self) -> str:
        return '<FixedOffset %s>' % (self.__offset,)

#
#   AbsoluteTime
#

nowRE = re.compile("^now$", re.IGNORECASE)
todayRE = re.compile("^tod(a?(y?))$", re.IGNORECASE)
tomorrowRE = re.compile("^tom(o?(r?(r?(o?(w?)))))$", re.IGNORECASE)
yesterdayRE = re.compile("^yes(t?(e?(r?(d?(a?(y?))))))$", re.IGNORECASE)

# Fix escape sequences by using raw strings where needed
dbre = re.compile(r"""^
(?P<year>\d+) - (?P<month>\d+) - (?P<day>\d+)     # all three pieces required
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE)

# '6/21/2006 16:03:36.157234'

user1re = re.compile(r"""^
( (?P<month>\d+) / (?P<day>\d+) (/ (?P<year>\d+))?    # month and day required, year optional
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE)

# '21-Jun-2006 16:03:36.157234'

user2re = re.compile(r"""^
( (?P<day>\d+)                          # day and month required, year optional
    - (?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
    (- (?P<year>\d+))?
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE | re.IGNORECASE)

# 'Jun 21 2006 16:03:36.157234'

user3re = re.compile(r"""^
( (?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
    ((\s+)? (?P<day>\d+))?              # month required,  day and year optional
    ((\s+)? (?P<year>\d+))?
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE | re.IGNORECASE)

# 'Wed, 21 Jun 2006 16:03:36 GMT'

webre = re.compile(r"""^
(?P<dow>(sun|mon|tue|wed|thu|fri|sat))
[,]
\s+
(?P<day>\d+)
(?:\s+|[-])
(?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
(?:\s+|[-])
(?P<year>\d+)
\s+
(?P<hour>\d+)
:(?P<minute>\d+)
:(?P<second>\d+)
\s+
GMT
$""", re.VERBOSE | re.IGNORECASE)

# YYYY-MM-DDTHH:MM:SS+HH:MM

isore = re.compile(r"""^
(?P<year>\d+) - (?P<month>\d+) - (?P<day>\d+)     # all three pieces required
T
(?P<hour>\d+)
:
(?P<minute>\d+)
:
(?P<second>\d+)
([.](?P<microsecond>\d+))?
( (?P<z>Z) |
  (?P<offhour>[ +-]\d+):(?P<offminute>\d+)        # GMT offset (signed)
)?
$""", re.VERBOSE)

dayNames = ['sun','mon','tue','wed','thu','fri','sat']
monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

# Add these regular expressions that were referenced but not defined
isodate_re = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
mdyfmt_re = re.compile(r'\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2}')
mdy_re = re.compile(r'\d{1,2}/\d{1,2}/\d{4}')

# Type variable for datetime types
DateTimeT = TypeVar('DateTimeT', bound=datetime)

class AbsoluteTime(datetime, Logging):

    _debug = 0
    
    @classmethod
    def __new__(cls, *args: Any, **kwargs: Any) -> 'AbsoluteTime':
        if AbsoluteTime._debug: AbsoluteTime._debug("__new__ %r %r", args, kwargs)
        
        # if the first argument is a string, try to evaluate it
        if args and isinstance(args[0], str):
            if isodate_re.match(args[0]):
                if AbsoluteTime._debug: AbsoluteTime._debug("    - ISO date time", args[0])
                dt = datetime.strptime(args[0], "%Y-%m-%d %H:%M:%S")
                year, month, day = dt.year, dt.month, dt.day
                hour, minute, second = dt.hour, dt.minute, dt.second
                d = {'microsecond':0}
                if 'tzinfo' in kwargs:
                    d['tzinfo'] = kwargs['tzinfo']
                # build a new argument list
                args = (year, month, day, hour, minute, second)
            elif mdyfmt_re.match(args[0]) or mdy_re.match(args[0]):
                dt = datetime.strptime(args[0], "%m/%d/%Y %H:%M:%S")
                year, month, day = dt.year, dt.month, dt.day
                hour, minute, second = dt.hour, dt.minute, dt.second
                d = {'microsecond':0}
                if 'tzinfo' in kwargs:
                    d['tzinfo'] = kwargs['tzinfo']
                # build a new argument list
                args = (year, month, day, hour, minute, second)
        
        # make a new date value, the normal way
        elif not args and 'now' in kwargs:
            d = {'microsecond':0}
            if kwargs['now']:
                return cast(AbsoluteTime, datetime.now())
            elif 'tzinfo' in kwargs:
                d['tzinfo'] = kwargs['tzinfo']
                return cast(AbsoluteTime, datetime.now(d['tzinfo']))
            return cast(AbsoluteTime, datetime.now())
        elif len(args) == 1 and isinstance(args[0], int):
            # from seconds
            dt = datetime.fromtimestamp(args[0])
            if 'tzinfo' in kwargs:
                dt = kwargs['tzinfo'].localize(dt)
            return cast(AbsoluteTime, dt)
        
        # assume the parameters are correct
        if not kwargs:
            if len(args) >= 3:
                year, month, day = args[0:3]
                d: Dict[str, Any] = {}
                if len(args) >= 4: d['hour'] = args[3]
                if len(args) >= 5: d['minute'] = args[4]
                if len(args) >= 6: d['second'] = args[5]
                if len(args) >= 7: d['microsecond'] = args[6]
            else:
                # go with today
                year, month, day = map(int, datetime.now().strftime("%Y %m %d").split())
                d = {'hour':0, 'minute':0, 'second':0, 'microsecond':0}
        else:
            if 'tz' in kwargs:
                d = {'tzinfo': kwargs['tz']}
                del kwargs['tz']
            else:
                d = {}
            if 'epoch' in kwargs:
                t = datetime.fromtimestamp(kwargs['epoch'])
                year, month, day = t.year, t.month, t.day
                d['hour'], d['minute'], d['second'] = t.hour, t.minute, t.second
                if 'microsecond' in kwargs:
                    d['microsecond'] = kwargs['microsecond']
                else:
                    d['microsecond'] = t.microsecond
            else:
                year, month, day = kwargs['year'], kwargs['month'], kwargs['day']
                if 'hour' in kwargs: d['hour'] = kwargs['hour']
                if 'minute' in kwargs: d['minute'] = kwargs['minute']
                if 'second' in kwargs: d['second'] = kwargs['second']
                if 'microsecond' in kwargs: d['microsecond'] = kwargs['microsecond']
        
        # now forward the creation along
        return cast(AbsoluteTime, datetime.__new__(cls, year, month, day, **d))

    def __str__(self) -> str:
        """Return a string version of the time as if it was local time."""
        # start with the normal stuff
        rslt = self.astimezone(LocalTimeZone).strftime("%d-%b-%Y %H:%M:%S")
        
        # return the result
        return rslt

    def __add__(self, secs: Union[int, float, timedelta]) -> 'AbsoluteTime':
        AbsoluteTime._debug("__add__ %r", secs)
        
        if isinstance(secs, int):
            # simple addition
            return cast(AbsoluteTime, datetime.__add__(self, timedelta(seconds=secs)))
        elif isinstance(secs, float):
            # seconds and microseconds
            t = int(secs)
            m = int((secs - t) * 1000000.0)
            return cast(AbsoluteTime, datetime.__add__(self, timedelta(seconds=t, microseconds=m)))
        else:
            return cast(AbsoluteTime, datetime.__add__(self, secs))
    
    def __sub__(self, secs: Union[int, float, timedelta]) -> 'AbsoluteTime':
        AbsoluteTime._debug("__sub__ %r", secs)
        
        if isinstance(secs, int):
            # simple subtraction
            return cast(AbsoluteTime, datetime.__sub__(self, timedelta(seconds=secs)))
        elif isinstance(secs, float):
            # seconds and microseconds
            t = int(secs)
            m = int((secs - t) * 1000000.0)
            return cast(AbsoluteTime, datetime.__sub__(self, timedelta(seconds=t, microseconds=m)))
        else:
            return cast(AbsoluteTime, datetime.__sub__(self, secs))

    def strftime(self, *args: Any) -> str:
        AbsoluteTime._debug("strftime %r", args)
        
        # make sure it is localized
        if not self.tzinfo:
            AbsoluteTime._debug("    - apply directly")
            return datetime.strftime(self, *args)
        elif self.tzinfo is not LocalTimeZone:
            return self.astimezone(LocalTimeZone).strftime(*args)
        return super().strftime(*args[0])

    def gmtime(self) -> time.struct_time:
        """ Return the tuple (like time.gmtime()) as if it was UTC. """
        AbsoluteTime._debug("gmtime")
        rslt = datetime.utctimetuple(self)
        AbsoluteTime._debug("    - rslt: %r", rslt)

        return rslt

    def utctime(self) -> float:
        """ Return the time like time.time() and include microseconds. Note 
        that time.mktime() RETURNS IT IN THE LOCAL TIME ZONE, therefore,
        time.mktime(time.gmtime(x)) != x.  Sheesh! """
        now = time.mktime(self.astimezone(LocalTimeZone).timetuple())
        now += self.microsecond / 1000000.0
        return now

    def __int__(self) -> int:
        return int(self.utctime())
        
    def __float__(self) -> float:
        return self.utctime()
        
    def datetime(self) -> datetime:
        """Return a true datetime object, not one of me."""
        AbsoluteTime._debug("datetime")
        
        return datetime(*self.utctimetuple()[:6], microsecond=self.microsecond)

    def dbstr(self) -> str:
        """ Return a formatted string for a database, make sure it's UTC. """
        return "%04d-%02d-%02d %02d:%02d:%02d" % self.utctimetuple()[:6]

    def webstr(self) -> str:
        """ Return a formatted string for an HTTP header, make sure it's UTC. """
        return time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", self.gmtime())

    def sameDayAs(self, other: datetime) -> bool:
        """ Return true iff the two dates are on the same day. Used to simplify
        the presentation of timestamps if the context is relatively clear. """
        thisday = self.astimezone(LocalTimeZone).timetuple()[0:3]
        thatday = other.astimezone(LocalTimeZone).timetuple()[0:3]
        return thisday == thatday

#
#   DeltaTime
#

deltare = re.compile(r"""^
( (?P<days>\d+) (?:\s+|-) (?:days?,\s+)? )?     # days are optional and must be separated by a dash or whitespace
( ( (?P<hours>\d+) : )? (?P<minutes>\d+) : )?   # if hours are given, minutes must also be
(?P<seconds>\d+)                                # seconds are required
([.] (?P<microseconds>\d+) )?                   # microseconds are optional
$""", re.VERBOSE)

class DeltaTime(timedelta):

    @classmethod
    def __new__(cls, *args: Any, **kwargs: Any) -> 'DeltaTime':
        DeltaTime._debug("__new__ %r %r", args, kwargs)
        
        # check for a string
        if args and isinstance(args[0], str):
            args = args[1:]
            
        # deep copy the dictionary
        dict = {}
        for k, v in list(kwargs.items()):
            dict[k] = v
            
        # now forward the creation along
        return cast(DeltaTime, timedelta.__new__(cls, *args, **dict))

    def __int__(self) -> int:
        return (self.days * 86400) + self.seconds
        
    def __float__(self) -> float:
        return (self.days * 86400.0) + self.seconds + (self.microseconds / 1000000.0)

#
#   SmartTimeFormat
#

@function_debugging
def SmartTimeFormat(when: datetime, wrt: datetime) -> str:
    """Format the time 'when' with respect to the time 'wrt'."""
    SmartTimeFormat._debug("SmartTimeFormat %r %r", when, wrt)

    # check the time zone
    if when.tzinfo == UTC:
        when = when.astimezone(LocalTimeZone)
        SmartTimeFormat._debug("    - when remapped: %r", when)
    if wrt.tzinfo == UTC:
        wrt = wrt.astimezone(LocalTimeZone)
        SmartTimeFormat._debug("    - wrt remapped: %r", wrt)

    # look for matching days
    dfmt = None
    if (when.month != wrt.month) or (when.day != wrt.day) or (when.year != wrt.year):
        dfmt = "%d-%b-%Y"
#   if (when.year != wrt.year):
#       dfmt += "-%Y"    

    # look for non-zero time
    tfmt = None
    if (when.hour != 0) or (when.minute != 0) or (when.second != 0):
        tfmt = "%H:%M"
    if (when.second != 0):
        tfmt += ":%S"

    # build the format string
    if dfmt:
        if tfmt:
            fmt = dfmt + ' ' + tfmt
        else:
            fmt = dfmt
    else:
        if tfmt:
            fmt = tfmt
        else:
            # default for 00:00:00 on same day
#           fmt = "%d-%b"
            fmt = "%d-%b-%Y"
    SmartTimeFormat._debug("    - fmt: %r", fmt)

    # format the time
    rslt = when.strftime(fmt)
    SmartTimeFormat._debug("    - rslt: %r", rslt)

    return rslt

#
#   For these function definitions, see:
#
#       <http://www.phys.uu.nl/~vgent/calendar/isocalendar.htm>
#
#   The ISO calendar year consists either of 52 weeks (i.e. 364 days, the
#   "short" years) or 53 weeks (i.e. 371 days, the "long" years).
#

def _g(y: int) -> int:
    return (y - 100) // 400 - (y - 102) // 400

def _h(y: int) -> int:
    return (y - 200) // 400 - (y - 199) // 400

def _f(y: int) -> int:
    return 5 * y + 12 - 4 * ((y // 100) - (y // 400)) + _g(y) + _h(y)

def isLongYear(y: int) -> bool:
    """True iff the year has 53 ISO calendar weeks."""
    return (_f(y) % 28) < 5

def isShortYear(y: int) -> bool:
    """True iff the year has 52 ISO calendar weeks."""
    return (_f(y) % 28) > 4

#
#   OrdinalBase
#

class OrdinalBase(Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalBase._debug("toOrdinal %r", when)
        raise NotImplementedError("%s.toOrdinal() not implemented" % (self.__class__.__name__,))

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalBase._debug("fromOrdinal %r", when)
        raise NotImplementedError("%s.fromOrdinal() not implemented" % (self.__class__.__name__,))

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalBase._debug("toRange %r scale=%r", when, scale)
        raise NotImplementedError("%s.toOrdinal() not implemented" % (self.__class__.__name__,))

#
#   OrdinalHour
#

class OrdinalHour(OrdinalBase, Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalHour._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        secs = time.mktime(when.timetuple())

        return (int(secs) // 3600)

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalHour._debug("fromOrdinal %r", when)

        when_dt = LocalTimeZone.localize(datetime.fromtimestamp(when * 3600))
        return AbsoluteTime(when_dt)

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalHour._debug("toRange %r scale=%r", when, scale)

        # the datetime objects constructed by fromtimestamp() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime.fromtimestamp(when * 3600))
        end = LocalTimeZone.localize(datetime.fromtimestamp((when + scale) * 3600))

        # now morph these into AbsoluteTime objects for more features
        start_time = AbsoluteTime(start)
        end_time = AbsoluteTime(end)

        return (start_time, end_time)

# there is only one
OrdinalHour = OrdinalHour()

#
#   OrdinalDay
#

class OrdinalDay(OrdinalBase, Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalDay._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return when.toordinal()

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalDay._debug("fromOrdinal %r", when)

        when_dt = LocalTimeZone.localize(datetime.fromordinal(when))
        return AbsoluteTime(when_dt)

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalDay._debug("toRange %r scale=%r", when, scale)

        # the datetime objects constructed by fromordinal() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime.fromordinal(when))
        end = LocalTimeZone.localize(datetime.fromordinal(when + scale))

        # now morph these into AbsoluteTime objects for more features
        start_time = AbsoluteTime(start)
        end_time = AbsoluteTime(end)

        return (start_time, end_time)

# there is only one
OrdinalDay = OrdinalDay()

#
#   OrdinalWeek
#
#   The first week (ordinal 0) is the first week of 1-Jan-1970, but starts
#   earlier since that is a Thursday and ISO calendar weeks start on a Monday.
#

_ordinalBaseDate = datetime(1969, 12, 29)
_ordinalBase = _ordinalBaseDate.toordinal()

class OrdinalWeek(OrdinalBase, Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalWeek._debug("toOrdinal %r", when)

        return (OrdinalDay.toOrdinal(when) - _ordinalBase) // 7

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalWeek._debug("fromOrdinal %r", when)

        when_ord = when * 7 + _ordinalBase
        when_dt = LocalTimeZone.localize(datetime.fromordinal(when_ord))
        return AbsoluteTime(when_dt)

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalWeek._debug("toRange %r scale=%r", when, scale)

        # calculate the ISO ordinal number for the day
        wstart = when * 7 + _ordinalBase

        # see OrdinalDayRange for naive datetimes
        start = LocalTimeZone.localize(datetime.fromordinal(wstart))
        end = LocalTimeZone.localize(datetime.fromordinal(wstart + (7 * scale)))

        # now morph these into AbsoluteTime objects for more features
        start_time = AbsoluteTime(start)
        end_time = AbsoluteTime(end)

        return (start_time, end_time)

# there is only one
OrdinalWeek = OrdinalWeek()

#
#   OrdinalMonth
#

class OrdinalMonth(OrdinalBase, Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalMonth._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return (when.year * 12) + (when.month - 1)

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalMonth._debug("fromOrdinal %r", when)

        year, month = when // 12, (when % 12) + 1
        when_dt = LocalTimeZone.localize(datetime(year, month, 1))
        return AbsoluteTime(when_dt)

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalMonth._debug("toRange %r scale=%r", when, scale)

        # special calculations for larger scales
        thisWhen, nextWhen = when, when + scale

        # split the number into components
        thisYear, thisMonth = thisWhen // 12, (thisWhen % 12) + 1
        nextYear, nextMonth = nextWhen // 12, (nextWhen % 12) + 1

        # the datetime objects constructed by fromordinal() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime(thisYear, thisMonth, 1))
        end = LocalTimeZone.localize(datetime(nextYear, nextMonth, 1))

        # now morph these into AbsoluteTime objects for more features
        start_time = AbsoluteTime(start)
        end_time = AbsoluteTime(end)

        return (start_time, end_time)

# there is only one
OrdinalMonth = OrdinalMonth()

#
#   OrdinalYear
#

class OrdinalYear(OrdinalBase, Logging):

    def toOrdinal(self, when: datetime) -> int:
        OrdinalYear._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return when.year

    def fromOrdinal(self, when: int) -> AbsoluteTime:
        OrdinalYear._debug("fromOrdinal %r", when)

        when_dt = LocalTimeZone.localize(datetime(when, 1, 1))
        return AbsoluteTime(when_dt)

    def toRange(self, when: int, scale: int = 1) -> Tuple[AbsoluteTime, AbsoluteTime]:
        OrdinalYear._debug("toRange %r scale=%r", when, scale)

        # the datetime objects naive, they have no tzinfo, and
        # therefore need to be localized
        start = LocalTimeZone.localize(datetime(when, 1, 1))
        end = LocalTimeZone.localize(datetime(when + scale, 1, 1))

        # now morph these into AbsoluteTime objects for more features
        start_time = AbsoluteTime(start)
        end_time = AbsoluteTime(end)

        return (start_time, end_time)

# there is only one
OrdinalYear = OrdinalYear()

