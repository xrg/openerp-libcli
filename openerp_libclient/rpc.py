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

## @brief The Database class handles queries that don't require a previous login, served by the db server object
class Database(object):
    ## @brief Obtains the list of available databases from the given URL. None if there 
    # was an error trying to fetch the list.
    def list(self, url):
        try:
            return self.call( url, 'list' )
        except Exception,e:
            logging.getLogger('RPC.Database').exception("db list exc:")
            return -1

    ## @brief Calls the specified method
    # on the given object on the server. If there is an error
    # during the call it simply rises an exception
    def call(self, url, method, *args):
        con = createConnection( url )
        if method in [ 'db_exist', 'list', 'list_lang', 'server_version']:
            authl = 'pub'
        else:
            authl = 'root'
        return con.call( '/db', method, args, auth_level=authl)

    ## @brief Same as call() but uses the notify mechanism to notify 
    # exceptions.
    def execute(self, url, method, *args):
        res = False
        try:
            res = self.call(url, method, *args)
        except socket.error, msg:
            Notifier.notifyWarning('', _('Could not contact server!') )
        return res

database = Database()

default_session = None

def openSession(**kwargs):
    global default_session
    default_session = session.Session()
    default_session.open(**kwargs)

def login():
    global default_session
    return default_session.login()

## @brief The RpcProxy class allows wrapping a server object only by giving it's name.
# 
# For example: 
# obj = RpcProxy('ir.values')
class RpcProxy(object):
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
    def __init__(self, proxy, func_name):
        self.proxy = proxy
        self.func = func_name

    def __call__(self, *args, **kwargs):
        if kwargs:
            if 'exec_dict' not in self.proxy.session.server_options:
                # There is no safe way to convert back to positional arguments,
                # so just report that to caller.
                raise RpcException("The server we are connected doesn't support keyword arguments.")
            return self.proxy.session.call('/object', 'exec_dict', 
                                (self.proxy.resource, self.func, list(args), kwargs))
        return self.proxy.session.call('/object', 'execute', 
                            (self.proxy.resource, self.func ) + args )

#eof