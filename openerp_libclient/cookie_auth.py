# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014-2015 P. Christeas <xrg@hellug.gr>
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

import logging
import Cookie
from protocol_xmlrpc import AuthClient, ProtocolError


class CookieAuthClient(AuthClient):
    """Collect cookie from http response, repeat it at each request
    """
    def __init__(self):
        self._cookie_jar = {}
        self._log = logging.getLogger('RPC.CookieAuthClient')

    def putRequest(self, atype, realm, conn, host, handler):
        super(CookieAuthClient,self).putRequest(atype, realm, conn, host, handler)

        if atype == 'Cookie':
            for cookie in self._cookie_jar.values():
                if cookie['domain']:
                    raise NotImplementedError
                if cookie['path']:
                    if not (handler and handler.startswith(cookie['path'])):
                        continue
                # print "Sending Cookie: %s=%s" % (cookie.key, cookie.value)
                conn.putheader('Cookie', '%s=%s' % (cookie.key, cookie.value))
        return

    def parseResponse(self, resp, trans, url):
        super(CookieAuthClient,self).parseResponse(resp, trans, url)

        if 'set-cookie' in resp.msg:
            # print "set-cookie:", resp.msg['set-cookie']
            for k, cookie in Cookie.SimpleCookie(resp.msg['set-cookie']).items():
                #if cookie['expires']
                expired = False
                if cookie['max-age'] != '':
                    # print "max-age", repr(cookie['max-age'])
                    if not cookie['max-age']:
                        self._cookie_jar.pop(k, None)
                        continue
                self._cookie_jar[k] = cookie

            trans._auth_type = 'Cookie'

        return False
        if False:
            (atype,realm) = resp.msg.getheader('www-authenticate').split(' ',1)
            resp.read()
            if realm.startswith('realm="') and realm.endswith('"'):
                realm = realm[7:-1]

            if atype != 'Basic':
                raise ProtocolError(url, 403,
                                "Unknown authentication method: %s" % atype, resp.msg)
            
            #trans._auth_realm = realm
            return True
        return False


class CSRFCookieAuthClient(CookieAuthClient):
    """ This auth client will send the CSRF token as a HTTP header at every request
    """
    def __init__(self, header="X-CSRF-Token"):
         super(CSRFCookieAuthClient, self).__init__()
         self._token_header = header
         self._token = None

    def putRequest(self, atype, realm, conn, host, handler):
        super(CSRFCookieAuthClient, self).putRequest(atype, realm, conn, host, handler)
        if self._token:
            conn.putheader(self._token_header, self._token)

    def set_token(self, token):
        self._token = token

#eof
