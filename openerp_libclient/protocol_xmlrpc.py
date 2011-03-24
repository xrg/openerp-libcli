# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2004-2009 TINY SPRL. (http://tiny.be) All Rights Reserved.
#    Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
#    Copyright (c) 2010 P. Christeas <p_christ@hol.gr>
#    Copyright (c) 2010-2011 OpenERP (http://www.openerp.com )
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################



session_counter = 0
class XmlRpcConnection(Connection):
    """@brief The XmlRpcConnection class implements Connection class for XML-RPC.

	The XML-RPC communication protocol is usually opened at port 8069 on the server.
    """
    name = "XML-RPCv1"
    def __init__(self, url, send_gzip=False):
        Connection.__init__(self, url)
        self.url += '/xmlrpc'
        self._ogws = {}
        self._send_gzip=send_gzip

    def copy(self):
        newob = Connection.copy(self)
        newob.url = self.url

    def gw(self,obj):
        """ Return the persistent gateway for some object
        """
        global session_counter
        if not self._ogws.has_key(obj):
            if self.url.startswith("https"):
                transport = tiny_socket.SafePersistentTransport(send_gzip=self._send_gzip)
            elif self.url.startswith("http"):
                transport = tiny_socket.PersistentTransport(send_gzip=self._send_gzip)
            else:
                transport = None
            self._ogws[obj] = xmlrpclib.ServerProxy(self.url + obj, transport=transport)
            
            session_counter = session_counter + 1
            if (session_counter % 100) == 0:
                self._log.debug("Sessions: %d", session_counter)
        
        return self._ogws[obj]

    def call(self, obj, method, args, auth_level='db'):
        remote = self.gw(obj)
        function = getattr(remote, method)
        try:
            if self.authorized:
                result = function(self.databaseName, self.uid, self.password, *args)
            else:
                result = function( *args )
        except socket.error, err:
            print "socket.error",err
            raise RpcProtocolException( err )
        except xmlrpclib.Fault, err:
            raise RpcServerException( err.faultCode, err.faultString )
        except Exception, e:
            print "Exception:",e
            raise
        return result


class XmlRpc2Connection(Connection):
    """@brief Connection class for the xml-rpc 2.0 OpenObject protocol

	This protocol is implemented at the same port as the xmlrpc 1.0, but has a
	different authentication mechanism.
    """
    name = "XML-RPCv2"
    def __init__(self, url, send_gzip=False):
        Connection.__init__(self, url)
        self.url += '/xmlrpc2'
        self._ogws = {}
        self.username = None
        self._authclient = None
        self._send_gzip = send_gzip
        
    def copy(self):
        newob = Connection.copy(self)
        newob.username = self.username
        newob.url = self.url
        newob._authclient = self._authclient
        # Note: we don't copy the _ogws, so that new connections
        # are launched (not reuse the persistent ones)
        
        return newob
        
    def gw(self, obj, auth_level, temp=False):
        """ Return the persistent gateway for some object
        
            If temp is specified, the proxy is a temporary one,
            not from cache. This is needed at the login, where the
            proxy could fail and need to be discarded.
        """
        global session_counter
        if temp or not self._ogws.has_key((obj,auth_level)):
            if self.url.startswith("https"):
                transport = tiny_socket.SafePersistentAuthTransport(send_gzip=self._send_gzip)
            elif self.url.startswith("http"):
                transport = tiny_socket.PersistentAuthTransport(send_gzip=self._send_gzip)
            else:
                transport = None
            
            path = self.url
            if not path.endswith('/'):
                path += '/'
            path += auth_level
            if auth_level == 'db':
                path += '/' + self.databaseName
            path += obj
            # self._log.debug("path: %s %s", path, obj)
            
            if temp and transport:
                transport.setAuthTries(1)
                
            if self._authclient and transport:
                transport.setAuthClient(self._authclient)
            
            nproxy = xmlrpclib.ServerProxy( path, transport=transport)
            
            session_counter = session_counter + 1
            if (session_counter % 100) == 0:
                self._log.debug("Sessions: %d", session_counter)
                
            if temp:
                if transport:
                    transport.setAuthTries(3)
                return nproxy
            
            self._ogws[(obj,auth_level)] = nproxy
        
        return self._ogws[(obj,auth_level)]

    def call(self, obj, method, args, auth_level='db'):
        remote = self.gw(obj, auth_level)
        function = getattr(remote, method)
        try:
            result = function( *args )
        except socket.error, err:
            self._log.error("socket error: %s" % err)
            self._log.debug("call %s.%s(%r)", obj, method, args)
            raise RpcProtocolException( err )
        except xmlrpclib.Fault, err:
            self._log.error( "xmlrpclib.Fault on %s/%s(%s): %s" % (obj,str(method), args[:2], err.faultString))
            raise Rpc2ServerException( err.faultCode, err.faultString )
        except Exception, e:
            self._log.exception("Exception:")
            raise
        return result

    def call2(self, obj, method, args, auth_level='db'):
        """ Variant of call(), with a temporary gateway, for login """
        remote = self.gw(obj, auth_level, temp=True)
        function = getattr(remote, method)
        try:
            result = function( *args )
            if result:
                # do cache the proxy, now that it's successful
                self._ogws[obj] = remote
        except socket.error, err:
            self._log.error("socket error: %s" % err)
            raise RpcProtocolException( err )
        except xmlrpclib.Fault, err:
            self._log.error( "xmlrpclib.Fault on %s/%s(%s): %s" % (obj,str(method), str(args[:2]), err))
            raise RpcServerException( err.faultCode, err.faultString )
        except tiny_socket.ProtocolError:
            raise # silently
        except Exception, e:
            self._log.exception("Exception:")
            raise
        return result

    def login(self, database, user, password):
        saved_creds = (self.databaseName, self.username, self.uid, self.password, self._authclient)
        try:
            self.databaseName = database
            self.username = user
            self.uid = None
            self.password = password
            self._authclient = tiny_socket.BasicAuthClient()
            self._authclient.addLogin("OpenERP User", user, password)
            res = self.call2( '/common', 'login', (database, user, password) )
            if not res:
                self.databaseName, self.username, self.uid, self.password, self._authclient = saved_creds
            return res
        except:
            self.databaseName, self.username, self.uid, self.password, self._authclient = saved_creds
            raise
