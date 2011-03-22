#!/usr/bin/python
# -*- coding: utf-8 -*-

from time_lc import strptime
print strptime('Tue Jun 18 18:23:07 2001', lang='C')
import locale
locale.setlocale(locale.LC_ALL,'el_GR.UTF-8')
print strptime('Τρι Ιούν 18 18:23:07 2001', lang='el_GR.UTF-8')
