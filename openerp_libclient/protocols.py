# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
# Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
# Copyright (c) 2010 P. Christeas <p_christ@hol.gr>
# Copyright (c) 2010 OpenERP (http://www.openerp.com )
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import logging

#.apidoc title: protocols - Loader of client protocols

"""
Protocol Implementations
=========================

The API used internally in the protocol implementations is described here.
However, you should normally not need to interface that API directly, ie.
you should call Session's functions instead of protocol's.
"""

try:
    import protocol_netrpc
    __hush_pyflakes = [ protocol_netrpc, ]
except ImportError:
    logging.getLogger('RPC').warning("Net-RPC won't be available")

try:
    import protocol_xmlrpc
    __hush_pyflakes = [ protocol_xmlrpc, ]
except ImportError:
    logging.getLogger('RPC').warning("XML-RPC won't be available")

try:
    import protocol_rpcjson
    __hush_pyflakes = [ protocol_rpcjson, ]
except ImportError:
    logging.getLogger('RPC').warning("RPC-JSON won't be available")
