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

#.apidoc title: Type extensions to all RPC protocols

import xmlrpclib
#import base64

class Binary(xmlrpclib.Binary):
    """ placeholder class for binary payloads, based on xmlrpclib
    """
    def __init__(self, source):
        # TODO source could also be a stream
        if isinstance(source, basestring):
            self.data = source
        else:
            raise TypeError(type(source))

def is_binary(obj):
    # check for any baseclass
    return isinstance(obj, xmlrpclib.Binary)

#eof