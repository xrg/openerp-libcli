#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openobject import rpc

db_props = {}
db_props['scheme'] = 'http'
db_props['dbname'] = 'refdb'
db_props['host'] = 'localhost'
db_props['port'] = 8069
db_props['user'] = 'admin'
db_props['passwd'] = 'admin'



r = rpc.session.login(db_props)
if r != 0:
    raise Exception("Could not login!")


commit_obj = rpc.RpcProxy('software_dev.commit')
print "Trying the old way:"
ids = commit_obj.search([], 0, 0, 
            False, {})
print ids

res = commit_obj.read(ids)
print len(res)

#eof