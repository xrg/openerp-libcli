#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openerp_libclient.extra.log_client import getTransportFromDSN, RemoteLogHandler

import logging


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

class MyLogHandler(RemoteLogHandler):
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


t = getTransportFromDSN(dict(proto='http', host='localhost', port='8069', 
                                superpass='admin'),
                        handler=MyLogHandler(use_color=True))
try:
    while True:
        t.process_next_logs()
except KeyboardInterrupt:
    pass

#eof
