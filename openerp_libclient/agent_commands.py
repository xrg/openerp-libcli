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

#.apidoc title: Commands agent

""" Commands agent utility is a class that will listen the openerp-server for
    remote commands and dispatch them to an object, accordingly


    Since this is based on the 'subscription' technology, it requires the 'koo'
    module on the server side.
"""

from . import subscriptions
from . import rpc, errors
import logging
import time
import threading

import os, sys

class CommandFailureException(Exception):
    def __init__(self, msg, error, code=100):
        """ A custom failure exception (recoverable)
        
            @param msg A short message (title) of the exception, like "Error!"
            @param error A text description, like "The spam has failed to be hamed"
        """
        self.args = (msg, error)
        self.code = code

class CommandsThread(subscriptions.SubscriptionThread):
    """ A commands thread, waiting for the server to issue a command
    """
    def __init__(self, obj, address_name, agent_name=None, agent_incarnation=None, session=None):
        """
            @param obj The object that will receive the commands. Anything sent
                by the server should have a corresponding callable attribute
                (aka. class method) in that object
            @param address_name the address of the command (mandatory)
            @param agent_name a symbolic name of this program
                (automatically set to the process name)
            @param agent_incarnation a unique name of this instance
        """

        if not agent_name:
            agent_name = sys.argv[0].rsplit(os.sep,1)[-1].split('.',1)[0]
        if not agent_incarnation:
            agent_incarnation = '%s-%s' %(agent_name, os.getpid())

        subscriptions.SubscriptionThread.__init__(self,
                expression='command on: %s' % address_name, session=session)
        self._obj = obj
        self._address = address_name
        self._agent_name = agent_name
        self._agent_incarnation = agent_incarnation
        self._addr_id = None
        self._logger = logging.getLogger('command_agent')
        self._cmds_obj = None
        
    def start(self):
        threading.Thread.start(self)
        self._logger.debug("Started thread for %s -> %r", self.expression, self._obj)


    def stop(self):
        subscriptions.SubscriptionThread.stop(self)
        if self._addr_id:
            try:
                addr_obj = rpc.RpcProxy('base.command.address', session=self.session)
                addr_obj.unsubscribe(self._addr_id, self._agent_name)
            except Exception:
                self._logger.warning("Could not unsubscribe", exc_info=True)

    def run(self):
        try:
            addr_obj = rpc.RpcProxy('base.command.address', session=self.session)
            aid = addr_obj.search([('name','=', self._address)])
            if not aid:
                self._logger.warning('Address "%s" not found in server', self._address)
                return
            self._addr_id = aid[0]
            addr_obj.subscribe(self._addr_id, self._agent_name, self._agent_incarnation)
            self._cmds_obj = rpc.RpcProxy('base.command.command', session=self.session)
        except Exception:
            self._logger.exception("Could not subscribe")
            return

        while self.session.logged() and not self._must_stop:
            try:
                if self._poll_commands():
                    continue # fast loop
            except Exception:
                self._logger.exception("Error while polling:")

            try:
                rpc.RpcCustomProxy('/subscription', session=self.session, auth_level='db').wait(self.expression)
                if self._must_stop:
                    # check again
                    break
            except errors.RpcNetworkException:
                self._logger.exception("RPC Network:")
                time.sleep(self.network_retry_delay)
            except Exception, e:
                self._logger.exception("Error")
                time.sleep(self.error_retry_delay)

    def _poll_commands(self):
        """ Polls the server for requested commands and dispatches them as appropriate

            @return True if commands were found, False if queue empty
        """

        self._logger.debug("poll commands!")
        res = self._cmds_obj.pop_command(address_name=self._address,
                agent_name=self._agent_name, agent_incarnation=self._agent_incarnation)
        # print "Command:", res

        if not res:
            return False

        try:
            fn = getattr(self._obj, res['method'])
        except AttributeError, e:
            self._cmds_obj.push_failure(res['id'], {'code': 100, 'message': str(e), 'error': e.args[0]})

        try:
            result = fn(*(res['args']), **(res['kwargs']))
        except CommandFailureException, e:
            self._cmds_obj.push_exception(res['id'], {'code': e.code, 'message': e.args[0], 'error': e.args[1]})
        except errors.RpcException:
            # this will happen id fn() contains forward-RPC calls to the server,
            # and these fail.
            self._logger.error("RPC Exception: %s", e)
            try:
                # the RPC layer may already be borken
                self._cmds_obj.push_exception(res['id'], {'code': e.code, 'message': e.args[0], 'error': e.args[1]})
            except Exception:
                pass
            return False
        except Exception, e:
            self._logger.error("Exception: %s", e)
            try:
                self._cmds_obj.push_exception(res['id'], {'code': 100, 'message': str(e), 'error': e.args[0]})
            except Exception:
                self._logger.exception("Could not even push exception to cmd #%d!", res['id'])
        else:
            self._cmds_obj.push_result(res['id'], result)

        return True

#eof
