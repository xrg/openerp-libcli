# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011 P. Christeas <xrg@hellug.gr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#.apidoc title: JSON helpers for binary payloads

""" These classes can be used at both client lib and the server
"""

from types import Binary
import datetime
import json
import base64

class JsonEncoder2(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Binary):
            return { '__binary__': True, 'payload': base64.encodestring(obj.data)}
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        return super(JsonEncoder2, self).default(obj)

def json_hook(dct):
    if '__binary__' in dct:
        if 'payload' in dct:
            return base64.decodestring(dct['payload'])
        else:
            # TODO
            return ValueError("JSON: binary objects must have a payload")
    else:
        return dct

#eof