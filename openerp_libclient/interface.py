# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2004-2009 TINY SPRL. (http://tiny.be) All Rights Reserved.
#    Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
#    Copyright (c) 2010 P. Christeas <p_christ@hol.gr>
#    Copyright (c) 2010-2011 OpenERP (http://www.openerp.com )
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import re
from dict_tools import dict_filter
from errors import RpcProtocolException, RpcServerException, RpcNetworkException
import traceback

"""This module provides the essential interface classes
"""

class Connection(object):
    """ The Connection class provides an abstract interface for a RPC protocol
    """
    name = "Unknown"
    codename = "baseclass"
    _version_re = re.compile(r'([0-9]{1,2}(?:[\.0-9]+))')

    def __init__(self, session):
        assert session
        self._log = logging.getLogger('RPC.Connection')
        self._remotelog = logging.getLogger('RPC.Remote')
        self._session = session

    def check(self):
        """ Checks if the connection is sane, alive
            @return True or False
        """
        return True

    def establish(self, kwargs, do_init=False):
        raise NotImplementedError()

    def _establish_int(self):
        """ setup the connection, get the trivial data.
        """
        sv = self.call('/db', 'server_version', args=(), auth_level='pub')
        vm = self._version_re.match(sv)
        if not vm:
            raise ValueError("Invalid format of server's version: %s" %  sv)
        self._session.server_version = tuple(map(int, vm.group(1).split('.')))
        self._log.info("Connected to a server ver: %s" % (self._session.server_version,))
        try:
            server_options = self.call('/common', 'get_options', args=(), auth_level='pub')
            if not isinstance(server_options, (list, tuple)):
                raise TypeError("server options are %s, expected list" % type(server_options))
            self._log.debug("got server options: %s", ', '.join(server_options))
            self._session.server_options = server_options
        except RpcServerException, e:
            # an older server, doesn't know about options. Never mind.
            self._log.info("Could not get server's options: %s", e.get_title())
            self._session.server_options = []
        except Exception, e:
            self._log.warning("Could not get server's options:", exc_info=True)
            self._session.server_options = []

    def setupArgs(self, kwargs):
        """ Filter the dict of arguments passed to session.open() for persistency

            When session.open() is called, it may contain a dict of several keywords,
            not all of which are meaningful to subsequent connection.
            We have to tell Session which ones to keep, for subsequent connections
            to use.
            @return a dict, subset of kwargs
        """
        return {}

    def call(self, path, method, args=None, auth_level='db' ):
        """ Perform an RPC call on path/method

            @param auth_level indicates which set of authenticators to
            use from the proxy. Can be 'pub', 'db' or 'root' so far.
        """
        raise NotImplementedError()

    def get_security(self):
        """ Retrieve info about security of connection
            TODO: ssl info.
            
            No, it won't call the cops.
        """
        return None

    def maybeUpgrade(self, kwargs):
        """ Called on a session that already has a connection
            @return True if we shall replace previous connections, False if we
                    have nothing better to do.

            @note This may want to peek at the session.server_options or version
            to determine if we need to upgrade
        """
        return False

    def stringToUnicode(self, result):
        if isinstance(result, str):
            return unicode( result, 'utf-8' )
        elif isinstance(result, list):
            return [self.stringToUnicode(x) for x in result]
        elif isinstance(result, tuple):
            return tuple([self.stringToUnicode(x) for x in result])
        elif isinstance(result, dict):
            newres = {}
            for i in result.keys():
                newres[i] = self.stringToUnicode(result[i])
            return newres
        else:
            return result

    def unicodeToString(self, result):
        if isinstance(result, unicode):
            return result.encode( 'utf-8' )
        elif isinstance(result, list):
            return [self.unicodeToString(x) for x in result]
        elif isinstance(result, tuple):
            return tuple([self.unicodeToString(x) for x in result])
        elif isinstance(result, dict):
            newres = {}
            for i in result.keys():
                newres[i] = self.unicodeToString(result[i])
            return newres
        else:
            return result

    def prettyUrl(self):
        return "%s://" % self.codename

class TCPConnection(Connection):
    """ A few shorthands, common to all TCP/IP connections
    """

    def __init__(self, session):
        super(TCPConnection, self).__init__(session)
        self.host = self._session.conn_args.get('host', None)
        self.port = self._session.conn_args.get('port', None)

    def establish(self, kwargs, do_init=False):
        if 'host' in kwargs:
            self.host = kwargs['host']
        if 'port' in kwargs:
            self.port = kwargs['port']

        if do_init:
            self._establish_int()
        return True

    def setupArgs(self, kwargs):
        return dict_filter(kwargs, ['host', 'port', 'dbname'])

    def prettyUrl(self):
        try:
            user = self._session.auth_proxy.user
            if user:
                user += '@'
        except AttributeError:
            user = ''
        return "%s://%s%s:%s/" % (self.codename, user, self.host, self.port)

class RPCNotifier(object):
    """ This class is responsible for producing notifications when RPC fails

        Notifications from this class shall be used whenever the user has to
        be alerted about something (eg. with an exception dialog)
        Override it to add your handlers!

        Messages in 'msg' arguments shall be provided in C locale, and the
        subclass is expected to translate them using its favourite framework.
    """

    def __init__(self):
        self.logger = logging.getLogger('RPC')

    def handleException(self, msg, *args, **kwargs):
        """
            @param exc must be a tuple of exception information, from sys.exc_info(), or None
        """
        exc_info = None
        if 'exc_info' in kwargs:
            exc_info = kwargs['exc_info']
            if exc_info[0] == RpcNetworkException:
                self.logger.log(logging.ERROR, msg, *args) # no traceback
                return
        self.logger.log(logging.ERROR, msg, *args, exc_info=exc_info)

    def handleRemoteException(self, msg, *args, **kwargs):
        """
            @param exc must be a tuple of exception information, from sys.exc_info(), or None
        """
        exc_info = kwargs.get('exc_info', False)
        self.logger.log(logging.ERROR, msg, *args)
        if kwargs.get('frame_info'):
            self.logger.error("Local Traceback (most recent call last):\n%s", ''.join(traceback.format_stack(kwargs['frame_info'], 8)))
        if exc_info:
            self.logger.error("Remote %s", exc_info[1].backtrace)

    def handleError(self, msg, *args):
        self.logger.error(msg, *args)

    def handleWarning(self, msg, *args, **kwargs):
        """ Issue a warning to user.
        Some properties can be specified in kwargs, sugh as:
            auto_close: display in an asynchronous way and return immediately to caller.
        """
        self.logger.warning(msg, *args)

    def userAlert(self, msg, *args):
        """Tell the user that something happened and continue
        """
        self.logger.info(msg, *args)

#eof