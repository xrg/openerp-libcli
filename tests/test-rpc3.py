#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openobject import rpc
import time
from datetime import datetime

db_props = {}
db_props['scheme'] = 'http'
db_props['dbname'] = 'refdb'
db_props['host'] = 'localhost'
db_props['port'] = 8069
db_props['user'] = 'admin'
db_props['passwd'] = 'admin'


def time2str(ddate):
    tdate = datetime.fromtimestamp(ddate)
    return tdate.strftime('%Y-%m-%d %H:%M:%S')
    
r = rpc.session.login(db_props)
if r != 0:
    raise Exception("Could not login!")

buildername="Full"
old = time.time() - 30*60
master_name = "foo"
master_incarnation = "foo123"

t = time.time()
print "time:", t
partner_obj = rpc.RpcProxy('software_dev.commit')
print "Getting buildids:"
ids = partner_obj.search([('buildername', '=', buildername),
                        ('complete', '=', False), 
                        '|', '|' , ('claimed_at','=', False), ('claimed_at', '<', time2str(old)),
                        '&', ('claimed_by_name', '=', master_name),
                        ('claimed_by_incarnation', '!=', master_incarnation)],
                        0, False, 'priority DESC, submitted_at')

print "Ids:", ids
print "Time:", time.time(), time.time() - t

#eof