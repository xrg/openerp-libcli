#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging

from openerp_libclient import rpc

logging.basicConfig(level=logging.DEBUG)

rpc.openSession(proto="http", host='localhost', port='8069', 
    user="admin", passwd="admin", dbname="refdb")
r = rpc.login()
if not r :
    raise Exception("Could not login! %r" % r)


ira_obj = rpc.RpcProxy('ir.attachment')
ira_obj.search_read([], fields=['index_content'])


#eof