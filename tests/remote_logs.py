#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openerp_libclient.protocol_xmlrpc import PersistentAuthTransport, BasicAuthClient

import re
import logging

class RLogRecord(object):
    """ A simplified logging.LogRecord case
    """
    
    def __init__(self, name, level, msg, exc_text=None):
        self.name = name
        self.level = level
        self.levelname = logging.getLevelName(level)
        self.msg = msg
        self.exc_text = exc_text

class MyLogParser(object):
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

logging.DEBUG_RPC = logging.DEBUG - 2
logging.addLevelName(logging.DEBUG_RPC, 'DEBUG_RPC')
logging.DEBUG_SQL = logging.DEBUG_RPC - 2
logging.addLevelName(logging.DEBUG_SQL, 'DEBUG_SQL')

logging.TEST = logging.INFO - 5
logging.addLevelName(logging.TEST, 'TEST')

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, _NOTHING, DEFAULT = range(10)
#The background is set with 40 plus the number of the color, and the foreground with 30
#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[%dm"
BOLD_COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"
COLOR_PATTERN = "%s%s%%s%s" % (COLOR_SEQ, COLOR_SEQ, RESET_SEQ)
BOLD_COLOR_PATTERN = "%s%s%%s%s" % (BOLD_COLOR_SEQ, BOLD_COLOR_SEQ, RESET_SEQ)

COLOR_MAPPING = {
    logging.DEBUG_SQL: (WHITE, MAGENTA, True),
    logging.DEBUG_RPC: (BLUE, WHITE, True),
    logging.DEBUG: (BLUE, DEFAULT, True),
    logging.INFO: (GREEN, DEFAULT, True),
    logging.TEST: (WHITE, BLUE, True),
    logging.WARNING: (YELLOW, DEFAULT, True),
    logging.ERROR: (RED, DEFAULT, True),
    logging.CRITICAL: (WHITE, RED, True),
}

class MyLogHandler(object):
    def __init__(self, use_color=False):
        self.use_color = use_color

    def handle(self, rec):
        ln = False
        lname = rec.levelname
        if self.use_color:
            ln = COLOR_MAPPING.get(rec.level, False)
                
            if ln:
                fg_color, bg_color, bold = ln
                if bold:
                    lname = BOLD_COLOR_PATTERN % (30 + fg_color, 40 + bg_color, lname)
                else:
                    lname = COLOR_PATTERN % (30 + fg_color, 40 + bg_color, lname)
        print "%s:%s:%s" % (lname, rec.name, rec.msg)
        if rec.exc_text:
            # no formatting yet
            print rec.exc_text

class RemoteLogTransport(PersistentAuthTransport):
    """ Reuse the RPC code for plain HTTP requests
    """
    def __init__(self, host, port):
        PersistentAuthTransport.__init__(self)
        self.log_handler = MyLogHandler(use_color=True)
        self.log_offset = None
        self.hostport = '%s:%s' % (host, port)
        
    def getparser(self):
        p = u = MyLogParser(self.log_handler)
        return p, u

    def send_content(self, connection, request_body):
        if not request_body:
            connection.putheader("Content-Length",'0')
            connection.putheader("Accept-Encoding",'gzip')
            connection.endheaders()
            return
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
        connection.putrequest("GET", handler, skip_accept_encoding=1)

    def _parse_response(self, response):
        """ override parent to catch some headers
        """
        if 'X-Log-LastPos' in response.msg:
            self.log_offset = int(response.msg.get('X-Log-LastPos'))
        return PersistentAuthTransport._parse_response(self, response)

    def process_next_logs(self):
        """Wait (blocking) and process next batch of log records
        
        OpenERP server sends log records in time-based batches. This
        function will wait for the next ones to arrive, and then handle
        them
        """
        parms = '/_logs?limit=50&wait=1'
        if self.log_offset:
            parms += '&offset=%d' % self.log_offset
        self.request(self.hostport, parms, None, verbose=False)

ba = BasicAuthClient()

t = RemoteLogTransport('localhost', 8169)
t.setAuthClient(ba)

ba.addLogin('OpenERP Admin', 'root', 'admin')

try:
    while True:
        t.process_next_logs()
except KeyboardInterrupt:
    pass

#eof
