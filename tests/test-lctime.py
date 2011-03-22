#!/usr/bin/python
# -*- coding: utf-8 -*-

from time_lc import strptime, strftime
print strptime('Tue Jun 18 18:23:07 2001', lang='C')
import locale
locale.setlocale(locale.LC_ALL,'el_GR.UTF-8')
print strptime('Τρι Ιούν 18 18:23:07 2001', lang='el_GR.UTF-8')

print "Strftime tests:"
print strftime("%a %b %d %H:%M:%S %Y", lang="C")
print strftime("%a %b %d %H:%M:%S %Y")
print strftime("%c or %x or %X")

test_exs = [ ('a',' Locale’s abbreviated weekday name.'),
	('A',' Locale’s full weekday name.'),
	('b',' Locale’s abbreviated month name.'),
	('B',' Locale’s full month name.'),
	('c',' Locale’s appropriate date and time representation.'),
	('d',' Day of the month as a decimal number [01,31].'),
	('H',' Hour (24-hour clock) as a decimal number [00,23].'),
	('I',' Hour (12-hour clock) as a decimal number [01,12].'),
	('j',' Day of the year as a decimal number [001,366].'),
	('m',' Month as a decimal number [01,12].'),
	('M',' Minute as a decimal number [00,59].'),
	('p',' Locale’s equivalent of either AM or PM.  (1)'),
	('S',' Second as a decimal number [00,61].  (2)'),
	('U',' Week number of the year (Sunday as the first day of the week)'),
	('w',' Weekday as a decimal number [0(Sunday),6].'),
	('W',' Week number of the year (Monday as the first day of the week)'),
	('x',' Locale’s appropriate date representation.'),
	('X',' Locale’s appropriate time representation.'),
	('y',' Year without century as a decimal number [00,99].'),
	('Y',' Year with century as a decimal number.'),
	('Z',' Time zone name (no characters if no time zone exists).') ]

from time import strftime as time_strftime
print "Pat.    | native     | ours    | description"
print "----------------------------------------------"
for pat, descr in test_exs:
    nat = time_strftime('%' + pat)
    ours = strftime('%' + pat)
    
    print "%%%s %s | %10s | %10s | %s" % \
	( pat,(nat == ours) and 'OK  ' or 'FAIL' ,nat, ours , descr)
	

for yr in range(2000,2015):
    for mo in (1,2,6,8,11):
	for dy in range(1,24):
	    tim = strptime('%04d-%02d-%02d' % (yr, mo, dy), '%Y-%m-%d', lang='C')[0]
	    nat = time_strftime('%W', tim)
	    ours = strftime('%W', tim)
	    if nat != ours:
		print "Nat/ours %d/%d/%d:" % (yr, mo,dy), nat, ours
	    
	    nat = time_strftime('%U', tim)
	    ours = strftime('%U', tim)
	    if nat != ours:
		print "Nat/ours U %d/%d/%d:" % (yr, mo,dy), nat, ours
	
    