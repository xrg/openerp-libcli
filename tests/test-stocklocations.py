#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging

from openerp_libclient import rpc

logging.basicConfig(level=logging.DEBUG)

rpc.openSession(proto="http", host='localhost', port='8169', 
    user="admin", passwd="admin", superpass="admin", dbname="test_bqi")

# Get a new proxy, for super-admin authentication
root_proxy = rpc.RpcCustomProxy('/common', auth_level='root')
ost1 = root_proxy.get_os_time()
print "OS times:", ost1

rpc.login()
stock_loc_obj = rpc.RpcProxy('stock.location')

for i in range(100):
    #loc_ids = stock_loc_obj.search([])
    #locations = stock_loc_obj.read(loc_ids)
    locations = stock_loc_obj.search_read([])
    if i < 2:
        for sl in locations:
            print "loc: %(name)s \treal: %(stock_real)s Virtual: %(stock_virtual)s" % sl
    else:
        print "again:", i, len(locations)
 
ost2 = root_proxy.get_os_time()

print "Os times: ", ost2[0] - ost1[0], ost2[1] - ost1[1], ost2[2] - ost1[2]

#eof
