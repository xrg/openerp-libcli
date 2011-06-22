#!/usr/bin/python
# -*- coding: utf-8 -*-

import locale

import time
import _strptime as _strptime_module
from datetime import date as datetime_date
import re

#.apidoc skip: True

'''
TODO:
asctime() -- convert time tuple to string
    ctime() -- convert time in seconds to string
    mktime() -- convert local time tuple to seconds since Epoch
    strftime() -- convert time tuple to string according to format specification
    strptime()

    currency(val, symbol=True, grouping=False, international=False)
        Formats val according to the currency settings
        in the current locale.
    
    format(percent, value, grouping=False, monetary=False, *additional)
        Returns the locale-aware substitution of a %? specifier
        (percent).
        
        additional is for format strings which contain one or more
        '*' modifiers.
    
    format_string(f, val, grouping=False)
        Formats a string in the same way that the % formatting would use,
        but takes the current locale into account.
        Grouping is applied if the third parameter is true.
'''

class AbstractLocaleTime(object):
    """Stores and handles locale-specific information related to time.

    ATTRIBUTES:
        f_weekday -- full weekday names (7-item list)
        a_weekday -- abbreviated weekday names (7-item list)
        f_month -- full month names (13-item list; dummy value in [0], which
                    is added by code)
        a_month -- abbreviated month names (13-item list, dummy value in
                    [0], which is added by code)
        am_pm -- AM/PM representation (2-item list)
        LC_date_time -- format string for date/time representation (string)
        LC_date -- format string for date representation (string)
        LC_time -- format string for time representation (string)
        timezone -- daylight- and non-daylight-savings timezone representation
                    (2-item list of sets)
        lang -- Language used by instance (2-item tuple)
    """

    def __init__(self):
        raise NotImplementedError

class LangSet(object):
    """ An object to hold all language's locale information
        TODO: more than the date/time data
        
        Note: a LangSet always behaves like LC_ALL == LC_TIME == LC_*
    """
    def __init__(self):
        # the child class must have initalized a few things already
        assert isinstance(self.locale_time, (AbstractLocaleTime, _strptime_module.LocaleTime))
        self._regex_cache = {}
        self._time_re = _strptime_module.TimeRE(locale_time=self.locale_time)
    
    def getTimeRegex(self, fmt):
        """Return a compiled regular expression for time/date format fmt string
        """
        
        format_regex = self._regex_cache.get(fmt)

        if not format_regex:
            try:
                format_regex = self._time_re.compile(fmt)
            # KeyError raised when a bad format is found; can be specified as
            # \\, in which case it was a stray % but with a space after it
            except KeyError, err:
                bad_directive = err.args[0]
                if bad_directive == "\\":
                    bad_directive = "%"
                del err
                raise ValueError("'%s' is a bad directive in format '%s'" %
                                    (bad_directive, format))
            # IndexError only occurs when the format string is "%"
            except IndexError:
                raise ValueError("stray %% in format '%s'" % format)
            self._regex_cache[format] = format_regex

        return format_regex

class C_LocaleTime(AbstractLocaleTime):
    def __init__(self):
        self.lang = (None, None)
        self.am_pm = ['am', 'pm']
        self.f_month = ['', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        self.LC_date = '%m/%d/%y'
        self.a_weekday = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        self.f_weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        self.LC_date_time = '%a %b %d %H:%M:%S %Y'
        self.timezone = (frozenset(['utc', 'eet', 'gmt']), frozenset(['eest']))
        self.a_month = ['', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        self.LC_time = '%H:%M:%S'
        self.LC_tznames = ('UTC', None)

class C_LangSet(LangSet):
    def __init__(self):
        self.locale_time = C_LocaleTime()
        super(C_LangSet, self).__init__()
        
class Current_LangSet(LangSet):
    """ Take the language out of process'es locale
    """
    def __init__(self):
        self.locale_time = _strptime_module.LocaleTime()
        self.locale_time.LC_tznames = time.tzname
        super(Current_LangSet, self).__init__()

class LangLoader(object):
    def __init__(self):
        self._lc_cache = {}

    def loadLang(self, lc):
        """Initialize a language, keeping a cache if needed
        """
        def _get_tuple(llc):
            if isinstance(llc, tuple):
                return llc
            if llc and '.' in llc:
                return tuple(llc.split('.', 1))
            else:
                return (llc, None)

        if lc not in self._lc_cache:
            if lc == 'C' or lc == (None, None):
                self._lc_cache[lc] = C_LangSet()
            elif _get_tuple(lc) == locale.getlocale(locale.LC_ALL):
                self._lc_cache[lc] = Current_LangSet()
            else:
                raise KeyError("Cannot use %s locale" % (lc,))
        return self._lc_cache[lc]

lang_loader = LangLoader()

def strptime(data_string, format="%a %b %d %H:%M:%S %Y", lang=None):
    """Return a time struct based on the input string and the format string."""
    
    global lang_loader
    # This code has been copied from python's _strptime module.
    if lang is False:
        lang = 'C'
    elif lang is None:
        lang = locale.getlocale(locale.LC_TIME) or 'C'

    if isinstance(lang, (basestring, tuple)):
        lang = lang_loader.loadLang(lang)

    locale_time = lang.locale_time
    format_regex = lang.getTimeRegex(format)
    assert format_regex

    found = format_regex.match(data_string)
    if not found:
        raise ValueError("time data %r does not match format %r" %
                         (data_string, format))
    if len(data_string) != found.end():
        raise ValueError("unconverted data remains: %s" %
                          data_string[found.end():])
    year = 1900
    month = day = 1
    hour = minute = second = fraction = 0
    tz = -1
    # Default to -1 to signify that values not known; not critical to have,
    # though
    week_of_year = -1
    week_of_year_start = -1
    # weekday and julian defaulted to -1 so as to signal need to calculate
    # values
    weekday = julian = -1
    found_dict = found.groupdict()
    for group_key in found_dict.iterkeys():
        # Directives not explicitly handled below:
        #   c, x, X
        #      handled by making out of other directives
        #   U, W
        #      worthless without day of the week
        if group_key == 'y':
            year = int(found_dict['y'])
            # Open Group specification for strptime() states that a %y
            #value in the range of [00, 68] is in the century 2000, while
            #[69,99] is in the century 1900
            if year <= 68:
                year += 2000
            else:
                year += 1900
        elif group_key == 'Y':
            year = int(found_dict['Y'])
        elif group_key == 'm':
            month = int(found_dict['m'])
        elif group_key == 'B':
            month = locale_time.f_month.index(found_dict['B'].lower())
        elif group_key == 'b':
            month = locale_time.a_month.index(found_dict['b'].lower())
        elif group_key == 'd':
            day = int(found_dict['d'])
        elif group_key == 'H':
            hour = int(found_dict['H'])
        elif group_key == 'I':
            hour = int(found_dict['I'])
            ampm = found_dict.get('p', '').lower()
            # If there was no AM/PM indicator, we'll treat this like AM
            if ampm in ('', locale_time.am_pm[0]):
                # We're in AM so the hour is correct unless we're
                # looking at 12 midnight.
                # 12 midnight == 12 AM == hour 0
                if hour == 12:
                    hour = 0
            elif ampm == locale_time.am_pm[1]:
                # We're in PM so we need to add 12 to the hour unless
                # we're looking at 12 noon.
                # 12 noon == 12 PM == hour 12
                if hour != 12:
                    hour += 12
        elif group_key == 'M':
            minute = int(found_dict['M'])
        elif group_key == 'S':
            second = int(found_dict['S'])
        elif group_key == 'f':
            s = found_dict['f']
            # Pad to always return microseconds.
            s += "0" * (6 - len(s))
            fraction = int(s)
        elif group_key == 'A':
            weekday = locale_time.f_weekday.index(found_dict['A'].lower())
        elif group_key == 'a':
            weekday = locale_time.a_weekday.index(found_dict['a'].lower())
        elif group_key == 'w':
            weekday = int(found_dict['w'])
            if weekday == 0:
                weekday = 6
            else:
                weekday -= 1
        elif group_key == 'j':
            julian = int(found_dict['j'])
        elif group_key in ('U', 'W'):
            week_of_year = int(found_dict[group_key])
            if group_key == 'U':
                # U starts week on Sunday.
                week_of_year_start = 6
            else:
                # W starts week on Monday.
                week_of_year_start = 0
        elif group_key == 'Z':
            # Since -1 is default value only need to worry about setting tz if
            # it can be something other than -1.
            found_zone = found_dict['Z'].lower()
            for value, tz_values in enumerate(locale_time.timezone):
                if found_zone in tz_values:
                    # Deal with bad locale setup where timezone names are the
                    # same and yet time.daylight is true; too ambiguous to
                    # be able to tell what timezone has daylight savings
                    if (time.tzname[0] == time.tzname[1] and
                       time.daylight and found_zone not in ("utc", "gmt")):
                        break
                    else:
                        tz = value
                        break
    # If we know the week of the year and what day of that week, we can figure
    # out the Julian day of the year.
    if julian == -1 and week_of_year != -1 and weekday != -1:
        week_starts_Mon = True if week_of_year_start == 0 else False
        julian = _strptime_module._calc_julian_from_U_or_W(year, week_of_year, weekday,
                                            week_starts_Mon)
    # Cannot pre-calculate datetime_date() since can change in Julian
    # calculation and thus could have different value for the day of the week
    # calculation.
    if julian == -1:
        # Need to add 1 to result since first day of the year is 1, not 0.
        julian = datetime_date(year, month, day).toordinal() - \
                  datetime_date(year, 1, 1).toordinal() + 1
    else:  # Assume that if they bothered to include Julian day it will
           # be accurate.
        datetime_result = datetime_date.fromordinal((julian - 1) + datetime_date(year, 1, 1).toordinal())
        year = datetime_result.year
        month = datetime_result.month
        day = datetime_result.day
    if weekday == -1:
        weekday = datetime_date(year, month, day).weekday()
    return (time.struct_time((year, month, day,
                              hour, minute, second,
                              weekday, julian, tz)), fraction)

def strptime_time(data_string, format="%a %b %d %H:%M:%S %Y", lang=None):
    return strptime(data_string, format, lang=lang)[0]
    
__strftime_regex = re.compile('%([aAbBcdHIjmMpSUwWxXyYZ%])')

def strftime(format, t=None, lang=None):
    global lang_loader
    # This code has been copied from python's _strptime module.
    if lang is False:
        lang = 'C'
    elif lang is None:
        lang = locale.getlocale(locale.LC_TIME) or 'C'

    if isinstance(lang, (basestring, tuple)):
        lang = lang_loader.loadLang(lang)

    locale_time = lang.locale_time
    if t is None:
        t = time.localtime()

    def _srepl(mobj):
        f = mobj.group(1)
        if f == "a":  #  Locale¢s abbreviated weekday name.
            return locale_time.a_weekday[t.tm_wday].title()
        elif f == "A":  #  Locale¢s full weekday name.
            return locale_time.f_weekday[t.tm_wday].title()
        elif f == "b":  #  Locale¢s abbreviated month name.
            return locale_time.a_month[t.tm_mon].title()
        elif f == "B":  #  Locale¢s full month name.
            return locale_time.f_month[t.tm_mon].title()
        elif f == "c":  #  Locale¢s appropriate date and time representation.
            return __strftime_regex.sub(_srepl, locale_time.LC_date_time)
        elif f == "d":  #  Day of the month as a decimal number [01,31].
            return '%02d' % t.tm_mday
        elif f == "H":  #  Hour (24-hour clock) as a decimal number [00,23].
            return '%02d' % t.tm_hour
        elif f == "I":  #  Hour (12-hour clock) as a decimal number [01,12].
            return '%02d' % ((t.tm_hour % 12) or 12)
        elif f == "j":  #  Day of the year as a decimal number [001,366].
            return '%03d' % t.tm_yday
        elif f == "m":  #  Month as a decimal number [01,12].
            return '%02d' % t.tm_mon
        elif f == "M":  #  Minute as a decimal number [00,59].
            return '%02d' % t.tm_min
        elif f == "p":  #  Locale¢s equivalent of either AM or PM.
            return locale_time.am_pm[int(t.tm_hour / 12)]
        elif f == "S":  #  Second as a decimal number [00,61].  (2)
            return '%02d' % t.tm_sec
        elif f == "U":  #  Week number of the year (Sunday as the first day of the week)
                        # as a decimal number [00,53]. All days in a new year preceding
                        # the first Sunday are considered to be in week 0.
            return '%02d' % ((t.tm_yday + 6 - (t.tm_wday-6) % 7 ) / 7 )
        elif f == "w":  #  Weekday as a decimal number [0(Sunday),6].
            return '%1d' % (t.tm_wday + 1)
        elif f == "W":  #  Week number of the year (Monday as the first day of the week) 
                        # as a decimal number [00,53]. All days in a new year preceding 
                        # the first Monday are considered to be in week 0.
            return '%02d' % ( (t.tm_yday + 6 - t.tm_wday) / 7)
        elif f == "x":  #  Locale¢s appropriate date representation.
            return __strftime_regex.sub(_srepl, locale_time.LC_date)
        elif f == "X":  #  Locale¢s appropriate time representation.
            return __strftime_regex.sub(_srepl, locale_time.LC_time)
        elif f == "y":  #  Year without century as a decimal number [00,99].
            return '%02d' % (t.tm_year % 100)
        elif f == "Y":  #  Year with century as a decimal number.
            return '%d' % t.tm_year
        elif f == "Z":  #  Time zone name (no characters if no time zone exists).
            if t.tm_isdst in (0,1):
                return locale_time.LC_tznames[t.tm_isdst] or ''
            else:
                return ''
        elif f == "%":  #  A literal '%' character.
            return '%'
        else:
            raise ValueError("Invalid format specifier: '%s'"  % f)

    return __strftime_regex.sub(_srepl, format)

#eof