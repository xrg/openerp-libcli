#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import os

import logging
import time
logging.basicConfig(level=logging.DEBUG)

from openerp_libclient import rpc, agent_commands

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
# OUR_NAME = 'test-commands'
# OUR_INCARNATION = 'tc:%s' % os.getpid()

the_parrot = parrot()

cmd_thread = agent_commands.CommandsThread(the_parrot, OUR_ADDRESS)
cmd_thread.start()

try:
    while True:
        print "."
        time.sleep(60)
finally:
    cmd_thread.stop()
