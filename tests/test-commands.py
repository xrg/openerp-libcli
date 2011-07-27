#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging
import time
logging.basicConfig(level=logging.DEBUG)

from openerp_libclient import rpc, subscriptions

rpc.openSession(proto="http", host='localhost', port='8169', 
    user="admin", passwd="admin", dbname="test_bqi")
r = rpc.login()
if not r :
    raise Exception("Could not login! %r" % r)

class parrot(object):
    """ A (dead) object that will emulate a generic dispatcher
    
        Will parrot^H print the name of any method being called
    """
    
    def __init__(self):
        pass

    class _parrot_fn:
        def __init__(self, method):
            self._method = method
        
        def __call__(self, *args, **kwargs):
            args_str = ', '.join(map(repr, args))
            if kwargs:
                if args_str:
                    args_str += ','
                args_str += ','.join([ '%s=%r' % (k, v) for k, v in kwargs.items()])
            print "called: %s(%s)" % (self._method, args_str)
            return True
    
    def __getattr__(self, name):
        return self._parrot_fn(name)

OUR_ADDRESS = 'test-address-1:1'
OUR_NAME = 'test-commands'
OUR_INCARNATION = 'tc:%s' % os.getpid()

the_parrot = parrot()
def poll_commands():
    print "poll commands!"
    cmds_obj = rpc.RpcProxy('base.command.command')
    res = cmds_obj.pop_command(address_name=OUR_ADDRESS,
            agent_name=OUR_NAME, agent_incarnation=OUR_INCARNATION)
    # print "Command:", res
    
    if not res:
        return
    
    try:
        result = getattr(the_parrot, res['method'])(*(res['args']), **(res['kwargs']))
    except Exception, e:
        # FIXME! message, error formulating
        print "Exception:", e
        cmds_obj.push_error(res['id'], {'code': 100, 'message': str(e), 'error': e.args[0]})
    else:
        cmds_obj.push_result(res['id'], result)
        

addr_obj = rpc.RpcProxy('base.command.address')

try:
    addr_id = addr_obj.search([('name','=', OUR_ADDRESS)])
    if not addr_id:
        raise ValueError("Address not found")
    addr_id = addr_id[0]
    addr_obj.subscribe(addr_id, OUR_NAME, OUR_INCARNATION)
except Exception, e:
    print "Cannot subscribe:", e
    sys.exit(1)

st = subscriptions.SubscriptionThread(OUR_ADDRESS)
st.setCallback(poll_commands)
# st.start()

try:
    while True:
        poll_commands()
        time.sleep(30)
finally:
    addr_obj.unsubscribe(addr_id, OUR_NAME)