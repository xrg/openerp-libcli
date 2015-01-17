# -*- coding: utf-8 -*-
##############################################################################
#
#    F3, Open Source Management Solution
#    Copyright (C) 2014 P. Christeas <xrg@hellug.gr>
#
##############################################################################

import logging
import json
import httplib
import gzip
from xmlrpclib import ProtocolError
from openerp_libclient import json_helpers
from openerp_libclient.session import Session

#.apidoc title: Side-Channel HTTP requests on F3 server

""" Just like the web-browser can read pages of the F3 server or use http_dyn_data
    providers, libclient applications can do requests beyond the RPC layer[1] and
    use these facilities, too.

    [1] security-wise, there is no point in restricting those client-side. An API
    user does always have access to the full HTTP layer.
"""

try:
    from cStringIO import StringIO
    __hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO
    __hush_pyflakes = [ StringIO ]

class SideChannel(object):
    """Out of band request, re-using libclient transport
    """
    _logger = logging.getLogger('RPC.side-channel')

    def __init__(self, session, base_path=""):
        assert isinstance(session, Session)
        self.__session = session
        self._base_path = base_path % session.conn_args


    def _request(self, trans, method, path, request_body):
        """
            @param trans a TCPTransport object
        """
        # issue XML-RPC request
        max_tries = getattr(trans, "_auth_tries", 3)
        tries = 0
        host = trans._http_host
        h = None

        while(tries < max_tries):
            resp = None
            if not h:
                h = trans.make_connection(host)

            tries += 1
            try:
                h.putrequest(method, path, skip_accept_encoding=1)
                trans.send_host(h, host)
                trans.send_user_agent(h)
            except httplib.CannotSendRequest:
                if h: h.close()
                continue

            if trans._auth_client:
                trans._auth_client.putRequest(trans._auth_type, trans._auth_realm,
                                              h, host, path)
            trans.send_content(h, request_body)

            try:
                resp = h.getresponse()
            except httplib.BadStatusLine, e:
                if e.line and e.line != "''": # BadStatusLine does a repr(line)
                    # something else, not a broken connection
                    raise
                if h: h.close()
                if resp: resp.close()
                continue

            try:
                if trans._auth_client:
                    aresp = trans._auth_client.parseResponse(resp, trans, host+path)
                    if resp.status == 401 and aresp:
                        continue

                if resp.status == 401:
                    raise ProtocolError(host+path, 403,
                                    'Server-incomplete authentication', resp.msg)
            except Exception:
                if resp: resp.close()
                raise

            return resp # as is, the whole object, open

        raise ProtocolError(host+path, 403, "No authentication",'')


    def _decode_response(self, response):
        if response.msg.get('content-encoding') == 'gzip':
            gzdata = StringIO()
            while not response.isclosed():
                rdata = response.read(1024)
                if not rdata:
                    break
                gzdata.write(rdata)
            gzdata.seek(0)
            rbuffer = gzip.GzipFile(mode='rb', fileobj=gzdata)
        elif response.msg.get('content-encoding'):
            raise NotImplementedError("Content-Encoding: %s" % response.msg.get('content-encoding'))
        else:
            rbuffer = response
        content_type = response.msg.get('content-type')
        if content_type == 'application/json':
            return json.load(rbuffer, object_hook=json_helpers.json_hook)
        else:
            #while not response.isclosed():
            #    rdata = response.read(1024)
            raise NotImplementedError("Unhandled content-type: %s" % content_type)
        return response.read()


    def request(self, path, params=None, data=None, request_type="JSON", callback=None):
        """ A complete HTTP request on this side-channel

            @param path string path, shall begin with '/'
            @param params dictionary of parameters, to be url-encoded (TODO)
            @param data raw data, to be encoded according to `request_type`
            @param request_type  {JSON|...} affects content-type and request method
            @param callback function(response) to be called instead of default processor

            This function, by default, will process the returned content according
            to its "Content-Type". Will raise an exception on 4xx or 5xx errors.
            If you want to manipulate the response, do provide a `callback`, where
            you can read the status and http headers.
        """
        self._logger.debug("request for %s", path)
        body = None
        content_type = 'text/plain'
        if params:
            # TODO
            raise NotImplementedError

        path = self._base_path + path

        if not data:
            method = 'GET'
        elif request_type == 'JSON':
            method = 'POST'
            content_type = 'application/json'
            body = json.dumps(data, cls=json_helpers.JsonEncoder2)
        else:
            raise NotImplementedError("Request type: %s" %request_type)

        resp = None
        saved_content_type = None
        try:
            conn = self.__session.connections.borrow(self.__session.conn_timeout)
            # override the transport , restore later
            saved_content_type = conn._transport._content_type
            conn._transport._content_type = content_type
            resp = self._request(conn._transport, method, path, body)

            if callback:
                return callback(resp)
            else:
                if resp.status == 204:
                    resp.read() # just in case there is content, in violation of RFC
                    return True
                elif resp.status != 200:
                    resp.read()
                    raise ProtocolError(conn.host + path,
                                resp.status, resp.reason, resp.msg )

                return self._decode_response(resp)
        finally:
            if conn and conn._transport:
                conn._transport._content_type = saved_content_type
            if resp: resp.close()
            self.__session.connections.free(conn)


#eof
