#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging

sys.path.insert(0, os.path.abspath('.'))
from openerp_libclient import rpc


logging.basicConfig(level=logging.DEBUG)
db_props = {}
db_props['scheme'] = 'http'
db_props['dbname'] = 'refdb'
db_props['host'] = 'localhost'
db_props['port'] = 8069
db_props['username'] = 'admin'
db_props['password'] = 'admin'

rpc.openSession(proto="socket", host='localhost', port='8070', 
    user="admin", passwd="admin", dbname="refdb")
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