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

import errno

ENONET = (errno.ECONNREFUSED, errno.ECONNRESET, errno.ECONNABORTED, errno.ENOENT)
class RpcException(Exception):
    """ Generic exception of the RPC layer
    """
    def __init__(self, info):
        self.code = None
        self.args = (info,)
        self.info = info
        self.backtrace = None

class RpcProtocolException(RpcException):
    """ Raised when the other side cannot speak the same protocol with us
    """
    def __init__(self, backtrace):
        self.code = None
        self.args = (backtrace,)
        if isinstance(backtrace, unicode):
            self.info = backtrace
        else:
            self.info = unicode( str(backtrace), 'utf-8' )
        self.backtrace = backtrace

class RpcNoProtocolException(RpcProtocolException):
    """Raised when protocol doesn't exist
    
        Typically, when the http server can't answer /xmlrpc[2] path
    """
    pass

class RpcServerException(RpcException):
    """ Raised by the other side, when server throws an exception
    """
    def __init__(self, code, backtrace):
        self.code = code
        if hasattr(code, 'split'):
            lines = code.split('\n')

            self.type = lines[0].split(' -- ')[0]
            msg = ''
            if len(lines[0].split(' -- ')) > 1:
                msg = lines[0].split(' -- ')[1]
            else:
                msg = lines[0]
            
            if len(lines) > 1:
                data = '\n'.join(lines[2:])
            else:
                data = backtrace
    
            self.args = ( msg, data )
        else:
            self.type = 'error'
            self.args = ('' , backtrace)

        self.backtrace = backtrace

    def __str__(self):
        if self.backtrace and '\n' in self.backtrace:
            bt = self.backtrace.split("\n")[-3:-2]
            bt = " ".join(bt)
        else:
            bt = self.backtrace
        return "<RpcServerException %s: '%s', '%s' >" % \
            (self.type, self.code, bt)

    def get_title(self):
        """ Title for the user window """
        if self.args and self.args[0] != self.backtrace:
            return self.args[0]
        return ''
    
    def get_details(self):
        """ Content of the user error window """
        if len(self.args) > 1 and self.args[1] != self.backtrace:
            return self.args[1]
        return ''

class RpcNetworkException(RpcException):
    """This means network has failed, server unreachable etc.
    
        It shall /not/ be used when the protocol fails. Only layers 1-3 here!
    """
    def __init__(self, info, errno=None):
        super(RpcNetworkException,self).__init__(info)
        self.code = errno

class Rpc2ServerException(RpcServerException):
    """ variant of RpcServerException for XML-RPC2
        
        It should be handled exactly like its parent. However, the parsing
        algorithm differs
        """
    def __init__(self, code, string):
        
        dic = { 'X-Exception': '', 'X-ExcOrigin': 'exception',
            'X-ExcOrigin': '', 'X-Traceback': '' }
        
        key = None
        for line in string.split('\n'):
            if line.startswith('\t'):
                dic[key] += '\n' + line[1:]
            else:
                nkey, rest = line.split(':', 1)
                assert nkey
                rest = rest.strip()
                dic[nkey] = rest
                key = nkey
        
        self.code = dic['X-Exception']
        self.type = dic['X-ExcOrigin']
        self.backtrace = dic['X-Traceback']
        self.args = ( dic.get('X-Exception','Exception!'), 
                        dic.get('X-ExcDetails',''))


#eof