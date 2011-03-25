# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2004-2009 TINY SPRL. (http://tiny.be) All Rights Reserved.
#    Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
#    Copyright (c) 2010 P. Christeas <p_christ@hol.gr>
#    Copyright (c) 2010-2011 OpenERP (http://www.openerp.com )
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import Pyro.core

## @brief The PyroConnection class implements Connection for the Pyro RPC protocol.
#
# The Pyro protocol is usually opened at port 8071 on the server.
class PyroConnection(Connection):
    name = "Pyro"
    
    def __init__(self, url):
        Connection.__init__(self, url)
        self.url += '/rpc'
        self.proxy = Pyro.core.getProxyForURI( self.url )

    def singleCall(self, obj, method, *args):
        encodedArgs = self.unicodeToString( args )
        if self.authorized:
            result = self.proxy.dispatch( obj[1:], method, self.databaseName, self.uid, self.password, *encodedArgs )
        else:
            result = self.proxy.dispatch( obj[1:], method, *encodedArgs )
        return self.stringToUnicode( result )

    def call(self, obj, method, args=None, auth_level='db'):
        try:
            try:
                #import traceback
                #traceback.print_stack()
                #print "CALLING: ", obj, method, args
                result = self.singleCall( obj, method, *args )
            except (Pyro.errors.ConnectionClosedError, Pyro.errors.ProtocolError), x:
                # As Pyro is a statefull protocol, network errors
                # or server reestarts will cause errors even if the server
                # is running and available again. So if remote call failed 
                # due to network error or server restart, try to bind 
                # and make the call again.
                self.proxy = Pyro.core.getProxyForURI( self.url )
                result = self.singleCall( obj, method, *args )
        except (Pyro.errors.ConnectionClosedError, Pyro.errors.ProtocolError), err:
            raise RpcProtocolException( unicode( err ) )
        except Exception, err:
            if Pyro.util.getPyroTraceback(err):
                faultCode = err.message
                faultString = u''
                for x in Pyro.util.getPyroTraceback(err):
                    faultString += unicode( x, 'utf-8', errors='ignore' )
                raise RpcServerException( faultCode, faultString )
            raise
        return result
