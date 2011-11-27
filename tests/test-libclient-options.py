#!/usr/bin/python

from openerp_libclient.extra import options

import sys
import os
import logging

options.allow_include = 3
cfgpath = os.path.join(os.path.dirname(sys.argv[0]),"test-options.conf")

options.init(config=cfgpath, config_section=())

print "options are:"
print options.opts

#eof