# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2010-2011 OpenERP (http://www.openerp.com )
#    Author (blame me): P. Christeas <xrg@openerp.com>
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

from openerp_libclient.protocol_xmlrpc import PersistentAuthTransport, \
        SafePersistentAuthTransport, BasicAuthClient, ProtocolError

import re
import logging
import time
import socket

#.apidoc title: log_client - Remote Logs client interface

try:
    from cStringIO import StringIO
    __hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO
    __hush_pyflakes = [ StringIO ]


class RLogRecord(object):
    """ A simplified logging.LogRecord case
    """

    def __init__(self, name, level, msg, exc_text=None):
        self.name = name
        self.level = level
        self.levelname = logging.getLevelName(level)
        self.msg = msg
        self.exc_text = exc_text

class MachineLogParser(object):
    """Parse a text stream of 'machine-formatted' logs
    """
    bqi_re = re.compile(r'([^\>\|]+)(\|[^\>]+)?\> (.*)$')

    def __init__(self, handler):
        self.handler = handler
        self._buffer = ''
        self._log_rec = None

    def feed(self, data):
        # TODO
        self._buffer += data
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            if not line:
                self.end_record()
                continue

            if line.startswith('+ '):
                assert self._log_rec
                self._log_rec.msg += '\n' + line[2:]
            elif line.startswith(':@'):
                # Exception text follows
                assert self._log_rec
                assert not self._log_rec.exc_text
                self._log_rec.exc_text = line[3:]
            elif line.startswith(':+ '):
                assert self._log_rec
                assert self._log_rec.exc_text
                self._log_rec.exc_text += '\n' + line[3:]
            else:
                self.end_record()
                mr = self.bqi_re.match(line)
                if not mr:
                    raise RuntimeError("Stray line %r in log output!" % line)
                blog = mr.group(1)
                blevel = mr.group(2) or '|20'
                try:
                    blevel = int(blevel[1:])
                except ValueError:
                    # bqi_rest.append('Strange level %r' % blevel)
                    pass
                bmsg = mr.group(3)
                self._log_rec = RLogRecord(blog, blevel, bmsg)
        # end while

    def end_record(self):
        if self._log_rec:
            self.handler.handle(self._log_rec)
        self._log_rec = None

    def close(self):
        self.end_record()

class RemoteLogHandler(object):
    def handle(self, rec):
        raise NotImplementedError


class _logTransportMixin(object):
    """ Reuse the RPC code for plain HTTP requests
    """
    batch_limit = 50    # max messages to fetch in one request

    def __init__(self, host, port, handler):
        assert getattr(handler, 'handle', False)
        self.log_handler = handler
        self.log_offset = None
        self.hostport = '%s:%s' % (host, port)
        self.sock_errors = 0

    def _check_return_type(self, resp):
        if resp.msg.get('content-type', False).split(';')[0] != 'text/x-log':
            self._log.warning("Response contains wrong content-type: %s", resp.msg.get('content-type','<empty>'))

    def getparser(self):
        p = u = MachineLogParser(self.log_handler)
        return p, u

    def send_request(self, connection, handler, request_body):
        connection.putrequest("GET", handler, skip_accept_encoding=1)

    def _parse_response(self, response):
        """ override parent to catch some headers
        """
        if 'X-Log-LastPos' in response.msg:
            self.log_offset = int(response.msg.get('X-Log-LastPos'))
        return super(_logTransportMixin, self)._parse_response(response)

    def process_next_logs(self):
        """Wait (blocking) and process next batch of log records

        OpenERP server sends log records in time-based batches. This
        function will wait for the next ones to arrive, and then handle
        them
        """
        parms = '/_logs?limit=%s&wait=1' % self.batch_limit
        if self.log_offset:
            parms += '&offset=%d' % self.log_offset
        try:
            self.request(self.hostport, parms, None, verbose=False)
            self.sock_errors = 0
        except socket.error, err:
            # an error in the TCP layer. May be transient
            self._log.error("socket error: %s" % err)
            self.sock_errors += 1
            if self.sock_errors < 3:
                # wait before trying again
                time.sleep(1.0)
            elif self.sock_errors < 10:
                time.sleep(5.0)
            else:
                self.sock_errors = 0
                raise
        except ProtocolError, err:
            if err.errcode == 204:
                pass
            else:
                raise

class RemoteLogTransport(_logTransportMixin, PersistentAuthTransport):
    def __init__(self, host, port, handler):
        PersistentAuthTransport.__init__(self)
        _logTransportMixin.__init__(self, host, port, handler)

class SafeRemoteLogTransport(_logTransportMixin, SafePersistentAuthTransport):
    def __init__(self, host, port, handler):
        SafePersistentAuthTransport.__init__(self)
        _logTransportMixin.__init__(self, host, port, handler)

def getTransportFromDSN(dsn, handler):
    """Prepares a remote log transport instance, from DSN parameters

    @param dsn a dict of connection parameters, like the session.open() kwargs
    @param handler a RemoteLogHandler instance
    """
    if dsn['proto'] == 'http':
        t = RemoteLogTransport(host=dsn['host'], port=dsn['port'], handler=handler)
    elif dsn['proto'] == 'https':
        t = SafeRemoteLogTransport(host=dsn['host'], port=dsn['port'], handler=handler)
    else:
        raise ValueError("Cannot handle %s protocol for remote logs" % dsn['proto'])

    ba = BasicAuthClient()
    t.setAuthClient(ba)
    if dsn.get('superpass', False):
        ba.addLogin('OpenERP Admin', 'root', dsn['superpass'])

    return t

#eof
