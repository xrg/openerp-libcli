#!/usr/bin/python
# -*- encoding: utf-8 -*-
from openerp_libclient import rpc
import threading

db_props = {}
db_props['proto'] = 'http'
db_props['dbname'] = 'test_bqi'
db_props['host'] = 'localhost'
db_props['port'] = 8169
db_props['user'] = 'admin'
db_props['passwd'] = 'admin'

rpc.openSession(**db_props)

if not rpc.login():
    raise Exception("Could not login!")

slow_obj = rpc.RpcProxy('test_orm.slow1')

def fun(slow_obj, name):
    res = slow_obj.do_slow([], context={})
    print "Finished %s" % name

num_calls = 70
print "Launching %d slow RPC calls:" % num_calls
thrs = []
for n in range(num_calls):
    # one call in sync, to test
    try:
        res = slow_obj.exists([1])
        print "Performed call while %d threads are alive" % len(thrs)
    except Exception, e:
        print "Cannot perform call with %d other threads: %s" %(len(thrs), e)
        break
    t = threading.Thread(target=fun, args=(slow_obj, "n%d" % n))
    thrs.append(t)
    t.daemon = True
    t.start()
    # and one more call to wait (take up a connection)
    
print "Threads started: %d waiting" % len(thrs)

for t in thrs:
    t.join()
print "Joined all threads"

#eof