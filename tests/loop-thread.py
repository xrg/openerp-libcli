#!/usr/bin/python

from openerp_libclient.extra import loopthread
from time import sleep, ctime

def ping():
    print ctime(), ": Ping!"

t = loopthread.LoopThread(3.0, target=ping)
t.start()

sleep(10)
print ctime(), ": Trigger"
t.trigger()

sleep(5)
print ctime(), ": Stop"
t.stop()

print "Exit.."
sleep(5)
#eof