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

import sys
import logging
import gzip
import errno
import socket
from xmlrpclib import Transport,ProtocolError, ServerProxy, Fault
import errors
from interface import TCPConnection
import httplib

try:
    from cStringIO import StringIO
    __hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO
    __hush_pyflakes = [ StringIO ]

class _fileobject2(object):
    def __init__(self, fobj):
        self.__fobj = fobj
    def __getattr__(self, name):
        return getattr(self.__fobj, name)

    def read(self, size=-1):
        ret = self.__fobj.read(size)
        return ret
        
    def readline(self, size=-1):
        buf = self.__fobj._rbuf
        buf.seek(0, 2)  # seek end
        if buf.tell() > 0:
            # check if we already have it in our buffer
            buf.seek(0)
            bline = buf.readline(size)
            if bline.endswith('\n') or len(bline) == size:
                self.__fobj._rbuf = StringIO()
                self.__fobj._rbuf.write(buf.read())
                return bline
            del bline
        if size < 0:
            # Read until \n or EOF, whichever comes first
            rbufsize = max(self._rbufsize, self.default_bufsize)
            buf.seek(0, 2)  # seek end
            self.__fobj._rbuf = StringIO()  # reset _rbuf.  we consume it via buf.
            while True:
                try:
                    data = self._sock.recv(rbufsize)
                except IOError, err:
                    if err.errno in (errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK):
                        continue
                    self.__fobj._rbuf = buf
                    raise
                except Exception:
                    self.__fobj._rbuf = buf
                    raise
                if not data:
                    break
                nl = data.find('\n')
                if nl >= 0:
                    nl += 1
                    buf.write(data[:nl])
                    self.__fobj._rbuf.write(data[nl:])
                    data = None
                    break
                buf.write(data)
            return buf.getvalue()
        else:
            # Read until size bytes or \n or EOF seen, whichever comes first
            buf.seek(0, 2)  # seek end
            buf_len = buf.tell()
            if buf_len >= size:
                buf.seek(0)
                rv = buf.read(size)
                self._rbuf = StringIO()
                self.__fobj._rbuf.write(buf.read())
                return rv
            self._rbuf = StringIO()  # reset _rbuf.  we consume it via buf.
            while True:
                try:
                    data = self._sock.recv(self._rbufsize)
                except IOError, err:
                    if err.errno in (errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK):
                        continue
                    self._rbuf = buf
                    raise
                except Exception:
                    self._rbuf = buf
                    raise
                if not data:
                    break
                left = size - buf_len
                # did we just receive a newline?
                nl = data.find('\n', 0, left)
                if nl >= 0:
                    nl += 1
                    # save the excess data to _rbuf
                    self.__fobj._rbuf.write(data[nl:])
                    if buf_len:
                        buf.write(data[:nl])
                        break
                    else:
                        # Shortcut.  Avoid data copy through buf when returning
                        # a substring of our first recv().
                        return data[:nl]
                n = len(data)
                if n == size and not buf_len:
                    # Shortcut.  Avoid data copy through buf when
                    # returning exactly all of our first recv().
                    return data
                if n >= left:
                    buf.write(data[:left])
                    self.__fobj._rbuf.write(data[left:])
                    break
                buf.write(data)
                buf_len += n
                #assert buf_len == buf.tell()
            return buf.getvalue()

class HTTPResponse2(httplib.HTTPResponse):
    def __init__(self, sock, debuglevel=0, strict=0, method=None):
        self.fp = _fileobject2(sock.makefile('rb'))
        self.debuglevel = debuglevel
        self.strict = strict
        self._method = method

        self.msg = None

        # from the Status-Line of the response
        self.version = httplib._UNKNOWN # HTTP-Version
        self.status = httplib._UNKNOWN  # Status-Code
        self.reason = httplib._UNKNOWN  # Reason-Phrase

        self.chunked = httplib._UNKNOWN         # is "chunked" being used?
        self.chunk_left = httplib._UNKNOWN      # bytes left to read in current chunk
        self.length = httplib._UNKNOWN          # number of bytes left in response
        self.will_close = httplib._UNKNOWN      # conn will close at end of response

    
class HTTP11(httplib.HTTP):
    _http_vsn = 11
    _http_vsn_str = 'HTTP/1.1'

    def is_idle(self):
        return self._conn and self._conn._HTTPConnection__state == httplib._CS_IDLE

    def _setup(self,conn):
        conn.response_class = HTTPResponse2
        httplib.HTTP._setup(self, conn)

    def connect(self):
        ret = super(HTTP11, self).connect()
        self.sock.setsockopt(socket.SO_KEEPALIVE, True)
        return ret

try:
    if sys.version_info[0:2] < (2,6):
            # print "No https for python %d.%d" % sys.version_info[0:2]
        raise AttributeError()

    class HTTPS(httplib.HTTPS):
        _http_vsn = 11
        _http_vsn_str = 'HTTP/1.1'

        def is_idle(self):
            return self._conn and self._conn._HTTPConnection__state == httplib._CS_IDLE
            # Still, we have a problem here, because we cannot tell if the connection is
            # closed.

        def _setup(self,conn):
            conn.response_class = HTTPResponse2
            httplib.HTTPS._setup(self, conn)
    
        def connect(self):
            ret = super(HTTPS, self).connect()
            self.sock.setsockopt(socket.SO_KEEPALIVE, True)
            return ret

except AttributeError:
    # if not in httplib, define a class that will always fail.
    class HTTPS():
        def __init__(self,*args):
            raise NotImplementedError( "your version of httplib doesn't support HTTPS" )

class PersistentTransport(Transport):
    """Handles an HTTP transaction to an XML-RPC server, persistently."""

    def __init__(self, use_datetime=0, send_gzip=False):
        Transport.__init__(self)
        self._use_datetime = use_datetime
        self._http_conn = None
        self._http_host = None
        self._log = logging.getLogger('RPC.Transport')
        self._send_gzip = send_gzip
        # print "Using persistent transport"

    def make_connection(self, host):
        if self._http_conn and not self._http_conn.is_idle():
            # Here, we need to discard a busy or broken connection.
            # It might be the case that another thread is using that
            # connection, so it makes more sense to let the garbage
            # collector clear it.
            self._http_conn = None
        # create a HTTP connection object from a host descriptor
        if (not self._http_conn) or (self._http_host != host):
            host, extra_headers, x509 = self.get_host_info(host)
            self._http_conn = HTTP11(host)
            self._log.info("New connection to %s", host)
            self._http_host = host

        return self._http_conn

    def get_host_info(self, host):
        host, extra_headers, x509 = Transport.get_host_info(self,host)
        if extra_headers == None:
            extra_headers = []

        extra_headers.append( ( 'Connection', 'keep-alive' ))

        return host, extra_headers, x509

    def _parse_response(self, response):
        """ read response from input file/socket, and parse it
            We are persistent, so it is important to only parse
            the right amount of input
        """

        p, u = self.getparser()

        if response.msg.get('content-encoding') == 'gzip':
            gzdata = StringIO()
            while not response.isclosed():
                rdata = response.read(1024)
                if not rdata:
                    break
                gzdata.write(rdata)
            gzdata.seek(0)
            rbuffer = gzip.GzipFile(mode='rb', fileobj=gzdata)
            while True:
                respdata = rbuffer.read()
                if not respdata:
                    break
                try:
                    p.feed(respdata)
                except Exception, e:
                    raise errors.RpcProtocolException(unicode(e))
        else:
            while not response.isclosed():
                rdata = response.read(1024)
                if not rdata:
                    break
                if self.verbose:
                    print "body:", repr(response)
                try:
                    p.feed(rdata)
                except Exception, e:
                    raise errors.RpcProtocolException(unicode(e))
                if len(rdata)<1024:
                    break

        p.close()
        return u.close()

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        for ttry in (1, 2):
            try:
                h = self.make_connection(host)
                if verbose:
                    h.set_debuglevel(1)

                self.send_request(h, handler, request_body)
            except httplib.CannotSendRequest:
                # try once more..
                if h: h.close()
                continue
            break

        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        resp = None
        try:
            resp = h._conn.getresponse()
            # TODO: except BadStatusLine, e:

            errcode, errmsg, headers = resp.status, resp.reason, resp.msg
            if errcode != 200:
                raise ProtocolError( host + handler, errcode, errmsg, headers )

            self.verbose = verbose

            return self._parse_response(resp)
        finally:
            if resp: resp.close()

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/xml")

        if self._send_gzip and len(request_body) > 512:
            buffer = StringIO()
            output = gzip.GzipFile(mode='wb', fileobj=buffer)
            output.write(request_body)
            output.close()
            buffer.seek(0)
            request_body = buffer.getvalue()
            connection.putheader('Content-Encoding', 'gzip')

        connection.putheader("Content-Length", str(len(request_body)))
        connection.putheader("Accept-Encoding",'gzip')
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler, skip_accept_encoding=1)

class SafePersistentTransport(PersistentTransport):
    """Handles an HTTPS transaction to an XML-RPC server."""

    # FIXME: mostly untested

    def make_connection(self, host):
        if self._http_conn and not self._http_conn.is_idle():
            # Here, we need to discard a busy or broken connection.
            # It might be the case that another thread is using that
            # connection, so it makes more sense to let the garbage
            # collector clear it.
            self._http_conn = None
        # create a HTTPS connection object from a host descriptor
        # host may be a string, or a (host, x509-dict) tuple
        if (not self._http_conn) or (self._http_host != host):
            host, extra_headers, x509 = self.get_host_info(host)
            self._http_conn = HTTPS(host, None, **(x509 or {}))
            self._http_host = host
            self._log.info("New connection to %s", host)
        return self._http_conn


class AuthClient(object):
    def getAuth(self, atype, realm):
        raise NotImplementedError("Cannot authenticate for %s" % atype)

    def resolveFailedRealm(self, realm):
        """ Called when, using a known auth type, the realm is not in cache
        """
        raise NotImplementedError("Cannot authenticate for realm %s" % realm)

import base64
class BasicAuthClient(AuthClient):
    def __init__(self):
        self._realm_dict = {}
        self._log = logging.getLogger('BasicAuthClient')

    def getAuth(self, atype, realm):
        if atype != 'Basic' :
            return super(BasicAuthClient,self).getAuth(atype, realm)

        if not self._realm_dict.has_key(realm):
            self._log.debug("realm dict: %r", self._realm_dict)
            self._log.debug("missing key: \"%s\"" % realm)
            self.resolveFailedRealm(realm)
        return 'Basic '+ self._realm_dict[realm]

    def addLogin(self, realm, username, passwd):
        """ Add some known username/password for a specific login.
            This function should be called once, for each realm
            that we want to authenticate against
        """
        assert realm
        auths = base64.encodestring(username + ':' + passwd)
        if auths[-1] == "\n":
            auths = auths[:-1]
        self._realm_dict[realm] = auths

    def hasRealm(self, realm):
        return realm in self._realm_dict

    def resetLogin(self, realm):
        """ When some login fails, initially, we need to reset the
            failed credentials, so that they are no more used.
        """
        if self._realm_dict.has_key(realm):
            del self._realm_dict[realm]

class addAuthTransport:
    """ Intermediate class that authentication algorithm to http transport
    """

    def setAuthClient(self, authobj):
        """ Set the authentication client object.
            This method must be called before any request is issued, that
            would require http authentication
        """
        assert isinstance(authobj, AuthClient)
        self._auth_client = authobj

    def setAuthTries(self, tries):
        self._auth_tries = int(tries)

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        max_tries = getattr(self, "_auth_tries", 3)
        tries = 0
        atype = None
        realm = None
        h = None

        while(tries < max_tries):
            if not h:
                h = self.make_connection(host)
                if verbose:
                    h.set_debuglevel(1)

            tries += 1
            try:
                self.send_request(h, handler, request_body)
                self.send_host(h, host)
                self.send_user_agent(h)
            except httplib.CannotSendRequest:
                if h: h.close()
                continue

            if atype:
                # This line will bork if self.setAuthClient has not
                # been issued. That is a programming error, fix your code!
                auths = self._auth_client.getAuth(atype, realm)
                h.putheader('Authorization', auths)
            self.send_content(h, request_body)

            resp = h._conn.getresponse()
            #  except BadStatusLine, e:

            if resp.status == 401:
                if 'www-authenticate' in resp.msg:
                    (atype,realm) = resp.msg.getheader('www-authenticate').split(' ',1)
                    resp.read()
                    if realm.startswith('realm="') and realm.endswith('"'):
                        realm = realm[7:-1]
                    # print "Resp:", resp.version,resp.isclosed(), resp.will_close
                    #print "Want to do auth %s for realm %s" % (atype, realm)
                    if atype != 'Basic':
                        raise ProtocolError(host+handler, 403,
                                        "Unknown authentication method: %s" % atype, resp.msg)
                    continue # with the outer while loop
                else:
                    raise ProtocolError(host+handler, 403,
                                'Server-incomplete authentication', resp.msg)

            if resp.status != 200:
                raise ProtocolError( host + handler,
                    resp.status, resp.reason, resp.msg )

            self.verbose = verbose

            #try:
            #    sock = h._conn.sock
            #except AttributeError:
            #    sock = None

            return self._parse_response(resp)

        raise ProtocolError(host+handler, 403, "No authentication",'')

class PersistentAuthTransport(addAuthTransport,PersistentTransport):
    pass

class SafePersistentAuthTransport(addAuthTransport,SafePersistentTransport):
    pass

session_counter = 0
class XmlRpcConnection(TCPConnection):
    """@brief The XmlRpcConnection class implements Connection class for XML-RPC.

        The XML-RPC communication protocol is usually opened at port 8069 on the server.
    """
    name = "XML-RPCv1"
    codename = 'http'
    _TransportClass = PersistentTransport

    def __init__(self, session):
        super(XmlRpcConnection, self).__init__(session)
        self._ogws = {}
        self._transport = None

    def _prepare_transport(self):
        """Feed the transport with any local data
            Hook for XML-RPC2
        """
        pass

    def establish(self, kwargs, do_init=True):
        if 'host' in kwargs:
            self.host = kwargs['host']
        if 'port' in kwargs:
            self.port = kwargs['port']
        send_gzip = 'xmlrpc-gzip' in self._session.server_options
        self._transport = self._TransportClass(send_gzip=send_gzip)
        uri = '%s:%s' % (self.host, self.port)
        self._prepare_transport()
        self._transport.make_connection(uri)
        if do_init:
            self._establish_int()
        if do_init:
            # Check after server initial query, again
            send_gzip = ('xmlrpc-gzip' in self._session.server_options)
            if send_gzip:
                self._transport._send_gzip = True
                self._log.debug("Going gzip for %s..", self.prettyUrl())
        return True


    def gw(self,obj):
        """ Return the persistent gateway for some object
        """
        global session_counter
        assert self._transport
        if not self._ogws.has_key(obj):
            url = '%s://%s:%s/xmlrpc%s' % (self.codename, self.host, self.port, obj)
            self._ogws[obj] = ServerProxy(url, transport=self._transport)
            
            session_counter = session_counter + 1
            if (session_counter % 100) == 0:
                self._log.debug("Sessions: %d", session_counter)
        
        return self._ogws[obj]

    def call(self, obj, method, args, auth_level='db'):
        remote = self.gw(obj)
        function = getattr(remote, method)
        try:
            apro = self._session.auth_proxy
            if auth_level == 'login':
                cargs = (apro.dbname, apro.user, apro.passwd)
            elif auth_level == 'db':
                cargs = (apro.dbname, apro.uid, apro.passwd)
            else:
                cargs = ()
            cargs += tuple(args)
            result = function( *cargs )
        except socket.error, err:
            if err.errno in errors.ENONET:
                raise errors.RpcNetworkException(err.strerror, err.errno)
            self._log.error("socket error: %s" % err)
            self._log.debug("call %s.%s(%r)", obj, method, args)
            raise errors.RpcProtocolException( err )
        except ProtocolError, err:
            if err.errcode == 404:
                raise errors.RpcNoProtocolException(err.errmsg)
            raise errors.RpcProtocolException(err.errmsg)
        except Fault, err:
            raise errors.RpcServerException( err.faultCode, err.faultString )
        except errors.RpcException:
            raise
        except Exception:
            self._log.exception("Exception:")
            raise
        return result

class XmlRpcSConnection(XmlRpcConnection):
    """@brief The XmlRpcConnection class implements Connection class for XML-RPC.

        The XML-RPC communication protocol is usually opened at port 8069 on the server.
    """
    name = "XML-RPCSv1"
    codename = 'https'
    _TransportClass = SafePersistentTransport

class XmlRpc2Connection(XmlRpcConnection):
    """@brief Connection class for the xml-rpc 2.0 OpenObject protocol

        This protocol is implemented at the same port as the xmlrpc 1.0, but has a
        different authentication mechanism.
    """
    name = "XML-RPCv2"
    codename = 'http'
    _TransportClass = PersistentAuthTransport
    
    def __init__(self, session):
        super(XmlRpc2Connection, self).__init__(session)
        self._authclient = None


    def _prepare_transport(self):
        update = False
        if not self._authclient:
            self._authclient = BasicAuthClient()
            update = True
        if not self._authclient.hasRealm("OpenERP User"):
            self._authclient.addLogin("OpenERP User", self._session.auth_proxy.user, self._session.auth_proxy.passwd)
            update = True
        if update:
            self._transport.setAuthClient(self._authclient)

    def gw(self, obj, auth_level):
        """ Return the persistent gateway for some object
        
            If temp is specified, the proxy is a temporary one,
            not from cache. This is needed at the login, where the
            proxy could fail and need to be discarded.
        """
        global session_counter
        if auth_level == 'login':
            self._prepare_transport()
        if not self._ogws.has_key((obj,auth_level)):
            url = '%s://%s:%s/xmlrpc2/' % (self.codename, self.host, self.port)
            
            if auth_level in ('db', 'login'):
                url += 'db/' + self._session.auth_proxy.dbname
            else:
                url += auth_level
            url += obj
            self._log.debug("path: %s for %s", url, obj)
            nproxy = ServerProxy( url, transport=self._transport)
            
            session_counter = session_counter + 1
            if (session_counter % 100) == 0:
                self._log.debug("Sessions: %d", session_counter)
                
            self._ogws[(obj,auth_level)] = nproxy
        
        return self._ogws[(obj,auth_level)]

    def call(self, obj, method, args, auth_level='db'):
        remote = self.gw(obj, auth_level)
        function = getattr(remote, method)
        try:
            if auth_level == 'login':
                self._transport.setAuthTries(2)
                try:
                    apr = self._session.auth_proxy
                    args = (apr.dbname, apr.user, apr.passwd)
                    result = function(*args)
                except Exception:
                    self._authclient = None # reset it
                    raise
                finally:
                    self._transport.setAuthTries(3)
            else:
                result = function( *args )
        except socket.error, err:
            if err.errno in errors.ENONET:
                raise errors.RpcNetworkException(err.strerror, err.errno)
            self._log.error("socket error: %s" % err)
            self._log.debug("call %s.%s(%r)", obj, method, args)
            raise errors.RpcProtocolException( err )
        except ProtocolError, err:
            if err.errcode == 404:
                raise errors.RpcNoProtocolException(err.errmsg)
            raise errors.RpcProtocolException(err.errmsg)
        except Fault, err:
            self._log.error( "xmlrpclib.Fault on %s/%s(%s): %s" % (obj,str(method), args[:2], err.faultString))
            raise errors.Rpc2ServerException( err.faultCode, err.faultString )
        except errors.RpcException:
            raise
        except Exception:
            self._log.exception("Exception:")
            raise
        return result

    def call2(self, obj, method, args, auth_level='db'): # must go!
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
            raise errors.RpcProtocolException( err )
        except Fault, err:
            self._log.error( "xmlrpclib.Fault on %s/%s(%s): %s" % (obj,str(method), str(args[:2]), err))
            raise errors.RpcServerException( err.faultCode, err.faultString )
        except ProtocolError:
            raise # silently
        except Exception:
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
            res = self.call2( '/common', 'login', (database, user, password) )
            if not res:
                self.databaseName, self.username, self.uid, self.password, self._authclient = saved_creds
            return res
        except:
            self.databaseName, self.username, self.uid, self.password, self._authclient = saved_creds
            raise

class XmlRpc2SConnection(XmlRpc2Connection):
    """XML-RPC v2, with SSL
    """
    name = "XML-RPCSv2"
    codename = 'https'
    _TransportClass = SafePersistentAuthTransport

import session
session.Session.proto_handlers.append(XmlRpc2Connection)
session.Session.proto_handlers.append(XmlRpcConnection)
session.Session.proto_handlers.append(XmlRpc2SConnection)
session.Session.proto_handlers.append(XmlRpcSConnection)
#eof