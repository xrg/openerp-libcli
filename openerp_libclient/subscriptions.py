# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 P. Christeas <xrg@hellug.gr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#.apidoc title: Subscription Thread

""" Subscription utility

    This is based on Koo technology and requires the 'koo' module on the
    server side
"""

import threading
from . import rpc, errors
import time
import logging

class SubscriptionThread(threading.Thread):
    """ An asynchronous notification thread.
    
        Every time the expression fires at the server, the callback
        function will be called.
        
        Example::
        
            def frol(msg):
                print "Hello %s" % msg
            
            st = SubscriptionThread("foo:notify")
            st.setCallback(frol, "world!")
            st.start()
    """
    network_retry_delay = 10.0
    error_retry_delay = 5.0
    
    def __init__(self, expression, session=None):
        assert isinstance(expression, basestring)
        threading.Thread.__init__(self)
        self.daemon = True
        self.fn = None
        self.fn_args = None
        self.fn_kwargs = None
        self._must_stop = False
        self.session = session or rpc.default_session
        self.expression = expression
        self._logger = logging.getLogger('subscription')
    
    def setCallback(self, fn, *args, **kwargs):
        assert not self.fn, "Function cannot be set a second time"
        self.fn = fn
        self.fn_args = args
        self.fn_kwargs = kwargs
        
    def start(self):
        if not self.fn:
            raise RuntimeError("You have to setCallback before start()")
        threading.Thread.start(self)
        self._logger.debug("Started thread for %s -> %s()", self.expression, self.fn.__name__)
        
    def stop(self):
        self._logger.debug("Stopping")
        self._must_stop = True
    
    def run(self):
        while self.session.logged() and not self._must_stop:
            try:
                rpc.RpcCustomProxy('/subscription', session=self.session, auth_level='db').wait(self.expression)
                if self._must_stop:
                    # check again
                    break
                self.fn(*(self.fn_args), **(self.fn_kwargs))
            except errors.RpcNetworkException:
                self._logger.exception("RPC Network:")
                time.sleep(self.network_retry_delay)
            except Exception, e:
                self._logger.exception("Error")
                time.sleep(self.error_retry_delay)
