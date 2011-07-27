#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging

sys.path.insert(0, os.path.abspath('.'))
from openerp_libclient import rpc


logging.basicConfig(level=logging.DEBUG)
db_props = {}

rpc.openSession(proto="http", host='localhost', port='8169', 
    user="admin", passwd="admin", dbname="test_bqi")
r = rpc.login()
if not r :
    raise Exception("Could not login! %r" % r)


partner_obj = rpc.RpcProxy('res.partner')
print "Trying the old way:"
ids = partner_obj.search([('name','ilike','a')], False, False, 
            False, {}, True)

print "Ids:", ids

print "Now, trying the new way:"
ids = partner_obj.search([('name','ilike','a')],count=True)

print "Ids:", ids

#eof