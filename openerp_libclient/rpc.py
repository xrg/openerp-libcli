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
import session
import protocols
__hush_pyflakes = [ protocols, ]
from errors import RpcProtocolException, RpcException

#.apidoc title: rpc - Object-like RPC interface to server

""" RPC module provides convenience classes, that give direct access to OpenERP objects

It is based on the older RPC proxy implementations of openerp-client and koo
"""

default_session = None

def openSession(**kwargs):
    """ open a session as the default one
    """
    global default_session
    default_session = session.Session()
    default_session.open(**kwargs)

def login():
    """ Login the default session
    """
    global default_session
    return default_session.login()

class RpcProxy(object):
    """ The RpcProxy class allows wrapping a server object only by giving it's name.
    
    For example:
    @code obj = RpcProxy('ir.values')
    """
    def __init__(self, resource, session=None):
        global default_session
        self.resource = resource
        self.session = session or default_session
        self.__attrs = {}

    def __getattr__(self, name):
        if not name in self.__attrs:
            self.__attrs[name] = RpcFunction(self, name)
        return self.__attrs[name]
    

class RpcFunction(object):
    """ emulate a server-side method call
    
        These objects are initialized through RpcProxy. You'd never need to
        initialize them explicitly.
    """
    def __init__(self, proxy, func_name):
        self.proxy = proxy
        self.func = func_name

    def __call__(self, *args, **kwargs):
        return self.proxy.session.call_orm(self.proxy.resource, self.func, list(args), kwargs)

class RpcCustomProxy(object):
    """ A lower-level proxy, for custom RPC methods
    """
    
    def __init__(self, path, session=None, auth_level='pub', notify=True):
        global default_session
        self.path = path
        self.session = session or default_session
        self.auth_level = auth_level
        self.notify = notify
        self.__attrs = {}

    def __getattr__(self, name):
        if not name in self.__attrs:
            self.__attrs[name] = RpcCustomFunction(self, name)
        return self.__attrs[name]

class RpcCustomFunction(object):
    def __init__(self, proxy, func_name):
        self.proxy = proxy
        self.func = func_name

    def __call__(self, *args):
        return self.proxy.session.call(self.proxy.path, self.func, args,
                        auth_level=self.proxy.auth_level, notify=self.proxy.notify)

#eof