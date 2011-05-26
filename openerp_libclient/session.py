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

from utils import Pool
from errors import RpcException, RpcNetworkException, RpcProtocolException, RpcNoProtocolException, RpcServerException
from interface import Connection, RPCNotifier
import logging
import sys

class AbstractAuthProxy(object):
    """Provides authentication source for connections
    """
    codename = 'abstract'
    def __init__(self, conn_params):
        self.uid = None
        self.dbname = conn_params.get('dbname', None)
    
class PasswdAuth(AbstractAuthProxy):
    codename = 'password'
    def __init__(self, conn_params):
        super(PasswdAuth, self).__init__(conn_params)
        self.user = conn_params['user']
        self.passwd = conn_params['passwd']
        self.superpass = conn_params.get('superpass', None)


class Session(object):
    #LoggedIn = 0
    #Exception = 2
    #InvalidCredentials = 3
    session_limit = 30
    conn_timeout = 30.0 # limit of seconds to wait for a free connection
    conn_expire = 600.0 # seconds after which a connection shall close
    proto_handlers = []
    """ A list of classes like [XmlRpcConnection, ...] that handle each protocol
    """
    auth_handlers = [ PasswdAuth, ]
    """ a list of handlers for authentication."""
    
    def __create_connection_int(self):
        assert self.__conn_klass, "Cannot create session connections before login"
        if len(self.connections) > self.session_limit:
            return None # but don't break the loop
        newconn = self.__conn_klass(self)
        assert isinstance(newconn, Connection)
        if not newconn.establish(self.conn_args, do_init=False):
            return None
        return newconn

    def _check_connection(self, conn):
        return conn.check()

    def __init__(self, notifier=None):
        self.state = False # = not ready
        self.conn_args = {} # as in host:port
        #self.password = None
        self.context = {}
        self.__conn_klass = None
        self.auth_proxy = None
        # self.allow_xmlrpc2 = True
        self.threads = []
        self.server_version = (None, )
        self.server_options = []
        self._notifier = notifier or RPCNotifier()
        self.connections = Pool(iter(self.__create_connection_int, NotImplemented),
                                self._check_connection)
        self._log = logging.getLogger('RPC.Session')

    ## @brief Calls the specified method
    # on the given object on the server. 
    #
    # If there is an error during the call it simply rises an exception. See 
    # execute() if you want exceptions to be handled by the notification mechanism.
    # @param obj Object name (string) that contains the method
    # @param method Method name (string) to call 
    # @param args Argument list for the given method
    def call(self, obj, method, args, auth_level='db', notify=True):
        if (not self.state) or (auth_level == 'db' and self.state !='login'):
            if notify:
                self._notifier.handleError("Not logged in")
            raise RpcException('Not logged in')
        conn = self.connections.borrow(self.conn_timeout)
        try:
            value = conn.call(obj, method, args, auth_level=auth_level)
        except RpcServerException, e:
            import inspect
            if notify:
                sframe = inspect.currentframe()
                sframe = sframe and sframe.f_back
                self._notifier.handleRemoteException("Failed to call %s/%s: %s", obj, method, e.args[0], exc_info=sys.exc_info(), frame_info=sframe)
            raise
        except Exception, e:
            if notify:
                self._notifier.handleException("Failed to call %s/%s", obj, method, exc_info=sys.exc_info())
            raise
        finally:
            self.connections.free(conn)
        return value

    def open(self, proto, **kwargs):
        """Open the session, login() to some server, doing trivial checks
        
            @param proto The protocol, like "socket", "http" etc.
            @param kwargs all rest arguments to the protocol are optional, so
                    put them in a dict. Some part of the dict will be used by
                    the authentication proxy, some by the connection(s)
                    If an 'auth' argument is passed, it will force authentication 
                    scheme.
        """
        
        if self.state:
            raise RuntimeError("Session already open()ed, please create a new one!")
        
        # first, create an auth proxy
        auth_kwd = kwargs.get('auth', False)
        for klass in self.auth_handlers:
            if auth_kwd and klass.codename != auth_kwd:
                continue
            try:
                nah = klass(kwargs)
                break
            except (ValueError, KeyError, AttributeError), e:
                self._log.debug("Error trying to use %s authentication" % klass.__name__, exc_info=True)
                pass
        else:
            raise ValueError("Cannot use authentication of %s type!" % (auth_kwd or 'any'))
        self.auth_proxy = nah
        
        # Then, try to establish one connection, check server and save.
        for pklass in self.proto_handlers:
            if pklass.codename != proto:
                continue
            try:
                conn = pklass(self)
                if self.state == 'open':
                    if conn.maybeUpgrade(kwargs):
                        self.connections.clear() # the previous one
                    else:
                        continue
                else:
                    conn.establish(kwargs, do_init=True)
            except RpcNetworkException, e:
                # we know that the server is useless here
                self._notifier.handleException(e.info, exc_info=sys.exc_info())
                raise
            except RpcNoProtocolException:
                self._log.warning("Cannot use %s protocol, continuing", pklass.name)
                continue
            except RpcProtocolException, exc:
                self._notifier.handleWarning("Cannot use %s protocol for %s: %s. Perhaps this is not the correct server URL.",
                    pklass.name, conn.prettyUrl(), exc.info, auto_close=True)
                continue
            except Exception, e:
                exc_info = sys.exc_info()
                self._notifier.handleException("Cannot connect to server: %s", e, exc_info=exc_info)
                raise
            self.connections.push_used(conn)
            self.__conn_klass = pklass  # reuse this class for all subsequent connections
            self.conn_args = conn.setupArgs(kwargs)
            self.state = 'open'
            self.connections.free(conn)
            # continue the loop, for "upgrade"
        if not self.state:
            self._notifier.handleError("No protocol could handle %s connection", proto)
            raise RpcException("Cannot open")
        return True


    def login(self):
        if not self.state:
            self._notifier.handleError("Not connected")
            raise RpcException('Not connnected')
        try:
            conn = self.connections.borrow(self.conn_timeout)
            res = conn.call( '/common', 'login', (), auth_level='login')
            if not res:
                self.state = 'nologin'
                self._notifier.handleError("Cannot login to %s", conn.prettyUrl())
            else:
                assert isinstance(res, int)
                self.state = 'login'
                self.auth_proxy.uid = res
                self._log.info("Logged in to %s", conn.prettyUrl())
            self.context = conn.call('/object', 'execute', ('res.users', 'context_get'), auth_level='db') or {}
            return res
        except Exception:
            self.state = 'nologin'
            self._notifier.handleException("Could not login", exc_info=sys.exc_info())
            raise
        finally:
            self.connections.free(conn)

    def reloadContext(self):
        """Reloads the session context
        
            Useful when some user parameters such as language are changed
        """
        conn = self.connections.borrow(self.conn_timeout)
        try:
            self.context = conn.call('/object', 'execute', ('res.users', 'context_get'), auth_level='db') or {}
        finally:
            self.connections.free(conn)

    def logged(self):
        """Returns whether the login function has been called and was successfull
        """
        return self.state == 'login'

    def logout(self):
        """Logs out of the server. """
        self.state = None
        self.auth_proxy = None
        self.connections.clear()

    #def copy(self):
        #new = Session()
        #new.open = self.open
        #new.url = self.url
        ## new.password = self.password
        #new.uid = self.uid
        #new.context = self.context
        #new.userName = self.userName
        #new.databaseName = self.databaseName
        #new.allow_xmlrpc2 = self.allow_xmlrpc2
        #new.server_options = self.server_options
        #return new
        
    def loop_once(self):
        """Perform any background operations, single-shot
        
        Call this function at regular intervals.
        For example, it may cleanup unused connections.
        @return True: call me back now, False: don't call again,
                or float: next time() it shall be called
        
        This function may block for short periods (rfc?)
        """
        # TODO
        return False

class FilterNotifier(RPCNotifier):
    """ A notifier that passes each message through a filter
    
        self._filter_fn is a function that takes the notification
        message and returns another string. If it returns empty, no
        notification will happen.
    """
    _filter_fn = lambda a: a
    
    def handleException(self, msg, *args, **kwargs):
        msg = self._filter_fn(msg)
        if not msg:
            return
        return super(FilterNotifier, self).handleException(msg, *args, **kwargs)

    def handleRemoteException(self, msg, *args, **kwargs):
        msg = self._filter_fn(msg)
        import traceback
        if not msg:
            return
        exc_info = kwargs.get('exc_info', False)
        self.logger.log(logging.ERROR, msg, *args)
        if kwargs.get('frame_info'):
            err2 = "Local Traceback (most recent call last):\n"
            err2 += ''.join(traceback.format_stack(kwargs['frame_info'], 8))
            err2 = self._filter_fn(err2)
            if err2:
                self.logger.error(err2)
        if exc_info:
            err2 = "Remote %s" % exc_info[1].backtrace
            err2 = self._filter_fn(err2)
            if err2:
                self.logger.error(err2)

    def handleError(self, msg, *args):
        msg = self._filter_fn(msg)
        if not msg:
            return
        return super(FilterNotifier, self).handleError(msg, *args)

    def handleWarning(self, msg, *args, **kwargs):
        msg = self._filter_fn(msg)
        if not msg:
            return
        return super(FilterNotifier, self).handleWarning(msg, *args, **kwargs)

    def userAlert(self, msg, *args):
        msg = self._filter_fn(msg)
        if not msg:
            return
        return super(FilterNotifier, self).userAlert(msg, *args)

#eof
