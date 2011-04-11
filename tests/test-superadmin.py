#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging

from openerp_libclient import rpc

logging.basicConfig(level=logging.DEBUG)

rpc.openSession(proto="http", host='localhost', port='8069', 
    user="admin", passwd="admin", superpass="admin", dbname="refdb")

pub_proxy = rpc.RpcCustomProxy('/common')
print "About this Server:"
print pub_proxy.about()
print

# Get a new proxy, for super-admin authentication
root_proxy = rpc.RpcCustomProxy('/common', auth_level='root')
print "OS times:", root_proxy.get_os_time()

#eof