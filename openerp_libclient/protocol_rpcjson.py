# -*- encoding: utf-8 -*-
##############################################################################
#
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

#.apidoc title: protocol_rpcjson - RPC-JSON protocol client implementation

"""
    This protocol is based on JSON-RPC (note the inverse name), but also with
    RESTful extensions and HTTP authentication.

"""

import gzip
# import errno
import socket
import json
import json_helpers

from xmlrpclib import ProtocolError
import errors
from interface import TCPConnection
import httplib

from protocol_xmlrpc import PersistentAuthTransport, SafePersistentAuthTransport, \
        BasicAuthClient

try:
    from cStringIO import StringIO
    __hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO
    __hush_pyflakes = [ StringIO ]

class JSON_add_transport:
    """ JSON-based Transport class

        RPC-JSON can reuse the Transport classes from xmlrpclib and protocol_xmlrpc,
        but it needs to override the marshalling functions, obviously.

        This class is a mix-in, so that it is used over PersistentAuthTransport or
        SafePersistentAuthTransport.
    """
    _content_type = "application/json"

    def _parse_response(self, response):
        """ read response from input file/socket, and parse it
            We are persistent, so it is important to only parse
            the right amount of input
        """

        respdata = StringIO()
        while not response.isclosed():
            rdata = response.read(1024)
            if not rdata:
                break
            respdata.write(rdata)
        respdata.seek(0)

        if response.msg.get('content-encoding') == 'gzip':
            rbuffer = gzip.GzipFile(mode='rb', fileobj=respdata)
        else:
            rbuffer = respdata

        try:
            return json.load(rbuffer, object_hook=json_helpers.json_hook)
        except Exception, e:
            raise errors.RpcProtocolException(unicode(e))

class JSONAuthTransport(JSON_add_transport,PersistentAuthTransport):
    pass

class JSONSecureAuthTransport(JSON_add_transport, SafePersistentAuthTransport):
    pass

class RpcJServerException(errors.RpcServerException):
    def __init__(self, json_res):
        self.code = json_res.get('message')
        self.type = json_res.get('origin')
        self.backtrace = json_res.get('traceback')
        self.args = ( json_res.get('message','Exception!'),
                        json_res.get('error',''))


class RpcJsonConnection(TCPConnection):
    """ JSON-based RPC connection class

        Usually opened at port 8069 on the server.

        Unlike the XML-RPC connection classes, this doesn't need to keep
        proxy objects, or "gateways" to the server. Instead, it will simple
        issue HTTP requests for every RPC call needed, over a persistent
        Transport instance. With the same TCP connection, same authentication
        (negotiation), it can work over different url paths (end-objects).
    """

    name = "RPC-JSON"
    codename = 'http'
    _TransportClass = JSONAuthTransport

    def __init__(self, session):
        super(RpcJsonConnection, self).__init__(session)
        self._transport = None
        self._authclient = None
        self._req_counter = 1

    def _prepare_transport(self):
        update = False
        if not self._authclient:
            self._authclient = BasicAuthClient()
            update = True
        if not self._authclient.hasRealm("OpenERP User"):
            self._authclient.addLogin("OpenERP User", self._session.auth_proxy.user, self._session.auth_proxy.passwd)
            update = True
        if not self._authclient.hasRealm("OpenERP Admin") \
                and self._session.auth_proxy.superpass:
            self._authclient.addLogin("OpenERP Admin", 'root', self._session.auth_proxy.superpass)
        if update:
            self._transport.setAuthClient(self._authclient)

    def establish(self, kwargs, do_init=False):
        if 'host' in kwargs:
            self.host = kwargs['host']
        if 'port' in kwargs:
            self.port = kwargs['port']
        send_gzip = True
        self._transport = self._TransportClass(send_gzip=send_gzip)
        uri = '%s:%s' % (self.host, self.port)
        self._prepare_transport()
        self._transport.make_connection(uri)
        if do_init:
            self._establish_int()

        return True

    def _do_request(self, path, method, args, kwargs=None):
        """ Request, including the marshalling of parameters

            Also decode possible Exceptions to the appropriate RpcException
            classes

            @param path a list of path components
        """
        try:
            url = '/json/' + '/'.join(map(str, path))
            req_id = str(self._req_counter)
            self._req_counter += 1
            # self._log.debug("path: %s", url)
            req_struct = { "version": "1.1",
                "id": req_id,
                "method": str(method),
                }

            if not kwargs:
                req_struct["params"] = list(args)
            else:
                req_struct['params'] = kwargs.copy()
                if args:
                    req_struct['params'].update(dict(enumerate(args)))
            req_body = json.dumps(req_struct, cls=json_helpers.JsonEncoder2)
            # makes it little more readable:
            req_body += "\n"
            del req_struct
            host = '%s:%s' % (self.host, self.port)
            res = self._transport.request(host, url, req_body)
            if res.get('version') not in ('1.0', '1.1', '1.2'):
                raise errors.RpcProtocolException("Invalid JSON version: %s" % \
                        res.get('version', '<unknown>'))
            if res.get('id') != req_id:
                raise errors.RpcProtocolException("Protocol Out of order: %r != %r" %\
                        (res.get('id'), req_id))
            if res.get('error'):
                raise RpcJServerException(res['error'])

        except socket.error, err:
            if err.errno in errors.ENONET:
                raise errors.RpcNetworkException(err.strerror, err.errno)
            self._log.error("socket error: %s" % err)
            self._log.debug("call %s/%s(%r)", '/'.join(path), method, args)
            raise errors.RpcProtocolException( err )
        except httplib.InvalidURL, err:
            raise errors.RpcNoProtocolException(err.args[0])
        except httplib.HTTPException, err:
            self._log.exception("HTTP Exception:")
            raise errors.RpcProtocolException(err.args[0])
        except ProtocolError, err:
            if err.errcode == 404:
                raise errors.RpcNoProtocolException(err.errmsg)
            raise errors.RpcProtocolException(err.errmsg)
        except errors.RpcException:
            raise
        except TypeError:
            # may come from marshalling, so it's useful to dump the arguments
            self._log.exception("Exception:")
            self._log.debug("Arguments: %r", args)
            raise
        except Exception:
            self._log.exception("Exception:")
            raise

        return res.get('result', None)

    def call(self, obj, method, args, auth_level='db'):
        """ Call a remote function of the OpenERP server

            @param obj the service class
            @param method the method
            @param args a list of positional arguments
            @param auth_level the authentication "level", a string
        """
        path = []
        if auth_level in ('db', 'login'):
            path += ['db',self._session.auth_proxy.dbname]
        else:
            path.append(auth_level)
        if obj.startswith('/'):
            path.append(obj[1:])
        else:
            path.append(obj)

        if auth_level == 'login':
            self._prepare_transport()
            self._transport.setAuthTries(2)
            try:
                apr = self._session.auth_proxy
                args = (apr.dbname, apr.user, apr.passwd)
                result = self._do_request(path, method, args)
            except Exception:
                self._authclient = None # reset it
                raise
            finally:
                self._transport.setAuthTries(3)
        else:
            if auth_level == 'db':
                self._transport._auth_realm = "OpenERP User"
            elif auth_level == 'root':
                self._transport._auth_realm = "OpenERP Admin"
            result = self._do_request(path, method, args)
        return result

    def call_orm(self, model, method, args, kwargs):
        """ Call a remote ORM function, with arguments and possibly keywords

            @param model the ORM model, like res.users
            @param method the method, eg. 'read'
            @param args positional arguments, in a list
            @param kwargs keyword arguments (a dict)

            @returns the pure result of the call, or raises RpcException
        """
        path = ['orm', self._session.auth_proxy.dbname, model]
        self._transport._auth_realm = "OpenERP User"
        result = self._do_request(path, method, args=args, kwargs=kwargs)

        return result


class RpcJsonSConnection(RpcJsonConnection):
    """Implement RPC-JSON connection over HTTPS (secure)

        Usually opened at port 8071 on the server.
    """
    name = "RPC-JSONS"
    codename = 'https'
    _TransportClass = JSONSecureAuthTransport

import session
session.Session.proto_handlers.insert(0, RpcJsonConnection)
session.Session.proto_handlers.insert(0, RpcJsonSConnection)

#eof