#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openerp_libclient import rpc
from openerp_libclient.extra import options
import logging

print "Will initialize all options and logging"
options.init() # just the plain defaults, no config file

log = logging.getLogger('main')
log.info("Init. Connecting...")

rpc.openSession(**options.connect_dsn)

if not rpc.login():
    raise Exception("Could not login!")
log.info("Connected.")

# -----8<---- cut here ----8<----
# Now, perform a trivial request
request_obj = rpc.RpcProxy('res.request')
req_to, req_from = request_obj.request_get() # custom function

log.info("Have %d pending requests (sent %d ones)", len(req_to), len(req_from))

if req_to:
    res = request_obj.read(req_to[0], ['name', 'act_from', 'date_sent', 'state'])
    if res:
        print
        print "From: %s" % res['act_from'][1]
        print "Date: %s" % res['date_sent']
        print "State: %s" % res['state']
        print "Subject: %s" % res['name']
    else:
        log.warning("Could not read request id #%d", req_to[0])

#eof