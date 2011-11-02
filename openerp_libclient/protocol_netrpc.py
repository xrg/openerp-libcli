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

try:
    from cStringIO import StringIO
    __hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO
    __hush_pyflakes = [ StringIO ]

import socket
import cPickle
import sys
from errors import RpcProtocolException, RpcServerException
from tools import ustr

from interface import TCPConnection
import session

class Myexception(Exception):
    def __init__(self, faultCode, faultString):
        self.faultCode = faultCode
        self.faultString = faultString
        self.args = (faultCode, faultString)

class mysocket:
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        # self.sock.settimeout(120)
        # prepare this socket for long operations: it may block for infinite
        # time, but should exit as soon as the net is down
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    def connect(self, host, port=False):
        #if not port:
            #protocol, buf = host.split('//')
            #host, port = buf.split(':')
        self.sock.connect((host, int(port)))
    def disconnect(self):
        # on Mac, the connection is automatically shutdown when the server disconnect.
        # see http://bugs.python.org/issue4397
        if sys.platform != 'darwin':
            self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    def mysend(self, msg, exception=False, traceback=None):
        msg = cPickle.dumps([msg,traceback])
        size = len(msg)
        self.sock.send('%8d' % size)
        self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent
    def myreceive(self):
        buf=''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if not chunk:
                raise RuntimeError, "socket connection broken"
            buf += chunk
        size = int(buf)
        buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            chunk = self.sock.recv(size-len(msg))
            if not chunk :
                raise RuntimeError, "socket connection broken"
            msg = msg + chunk
        res = cPickle.loads(msg)
        if isinstance(res[0],Exception):
            if exception:
                raise Myexception(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]

## @brief The SocketConnection class implements Connection for the OpenERP socket RPC protocol.
#
# The socket RPC protocol is usually opened at port 8070 on the server.
class SocketConnection(TCPConnection):
    name = "Net-RPC"
    codename = 'socket'

    def __init__(self, session):
        super(SocketConnection, self).__init__(session)

    def call(self, obj, method, args, auth_level='db'):
        try:
            s = mysocket()
            s.connect(self.host, self.port )
        except socket.error, err:
            raise RpcProtocolException( ustr(err.strerror) )
        try:
            # Remove leading slash (ie. '/object' -> 'object')
            obj = obj[1:]
            encodedArgs = tuple(self.unicodeToString( args ))
            apro = self._session.auth_proxy
            if auth_level == 'login':
                cargs = (obj, method, apro.dbname, apro.user, apro.passwd)
            elif auth_level == 'db':
                cargs = (obj, method, apro.dbname, apro.uid, apro.passwd)
            elif auth_level == 'root':
                cargs = (obj, method, apro.superpass)
            else:
                cargs = (obj, method)
            s.mysend( cargs + encodedArgs)
            result = s.myreceive()
        except socket.error, err:
            # print err.strerror
            raise RpcProtocolException( ustr(err.strerror) )
        except Myexception, err:
            faultCode = ustr( err.faultCode)
            faultString = ustr( err.faultString)
            raise RpcServerException( faultCode, faultString )
        finally:
            s.disconnect()
        return self.stringToUnicode( result )

session.Session.proto_handlers.append(SocketConnection)
# eof
