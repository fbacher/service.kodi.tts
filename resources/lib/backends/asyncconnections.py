# coding=utf-8
import http.client
import select
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from common import *

from common.logger import *
from common.monitor import Monitor

module_logger = BasicLogger.get_logger(__name__)

STOP_REQUESTED = False
STOPPABLE = False
DEBUG = False


class AbortRequestedException(Exception):
    pass


class StopRequestedException(Exception):
    pass


if not hasattr(http.client.HTTPResponse, 'fileno'):
    class ModHTTPResponse(http.client.HTTPResponse):

        def fileno(self):
            return self.fp.fileno()


    http.client.HTTPResponse = ModHTTPResponse


def StopConnection():
    global STOP_REQUESTED
    if not STOPPABLE:
        STOP_REQUESTED = False
        return
    if module_logger.isEnabledFor(DEBUG):
        module_logger.debug('StopConnection: User requested stop of connection')

    STOP_REQUESTED = True


def setStoppable(val):
    global STOPPABLE
    STOPPABLE = val


def resetStopRequest():
    global STOP_REQUESTED
    STOP_REQUESTED = False


class _AsyncHTTPResponse(http.client.HTTPResponse):
    _prog_callback = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _read_status(self):
        ## Do non-blocking checks for server response until something arrives.
        setStoppable(True)
        try:
            while True:
                sel = select.select([self.fp.fileno()], [], [], 0)
                if len(sel[0]) > 0:
                    break
                ## <--- Right here, check to see whether thread has requested to stop
                ##      Also check to see whether timeout has elapsed
                if Monitor.wait_for_abort(0.10) and self._logger.isEnabledFor(DEBUG):
                    self._logger.debug(
                        ' -- XBMC requested abort during wait for server response: '
                        'raising exception -- ')
                    raise AbortRequestedException('httplib.HTTPResponse._read_status')
                elif STOP_REQUESTED and self._logger.isEnabledFor(DEBUG):
                    self._logger.debug(
                        'Stop requested during wait for server response: raising '
                        'exception')
                    resetStopRequest()
                    raise StopRequestedException('httplib.HTTPResponse._read_status')

                if self._prog_callback:
                    if not self._prog_callback(-1):
                        resetStopRequest()
                        raise StopRequestedException('httplib.HTTPResponse._read_status')

            return http.client.HTTPResponse._read_status(self)
        finally:
            setStoppable(False)
            resetStopRequest()


AsyncHTTPResponse = _AsyncHTTPResponse


class Connection(http.client.HTTPConnection):
    response_class = AsyncHTTPResponse


class _Handler(urllib.request.HTTPHandler):

    def http_open(self, req):
        return self.do_open(Connection, req)


Handler = _Handler


# def createHandlerWithCallback(callback):
#    if getSetting('disable_async_connections',False):
#        return urllib2.HTTPHandler
#
#    class rc(AsyncHTTPResponse):
#        _prog_callback = callback
#
#    class conn(httplib.HTTPConnection):
#        response_class = rc
#
#    class handler(urllib2.HTTPHandler):
#        def http_open(self, req):
#            return self.do_open(conn, req)
#
#    return handler

def checkStop():
    if Monitor.is_abort_requested() and module_logger.isEnabledFor(DEBUG):
        module_logger.debug(
            ' -- XBMC requested abort during wait for connection to server: raising '
            'exception -- ')
        raise AbortRequestedException('socket[asyncconnections].create_connection')
    elif STOP_REQUESTED and module_logger.isEnabledFor(DEBUG):
        module_logger.debug(
            'Stop requested during wait for connection to server: raising exception')
        resetStopRequest()
        raise StopRequestedException('socket[asyncconnections].create_connection')


def waitConnect(sock, timeout):
    start = time.time()
    while time.time() - start < timeout:
        sel = select.select([], [sock], [], 0)
        if len(sel[1]) > 0:
            break
        checkStop()
        time.sleep(0.1)
    sock.setblocking(True)
    return sock


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                      source_address=None):
    setStoppable(True)
    try:
        return _create_connection(address, timeout=timeout, source_address=source_address)
    finally:
        setStoppable(False)
        resetStopRequest()


def _create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                       source_address=None):
    host, port = address
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        checkStop()
        af, socktype, proto, canonname, sa = res  # @UnusedVariable
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            if port == 443:  # SSL
                sock.connect(sa)
            else:
                sock.setblocking(False)
                err = sock.connect_ex(sa)
                waitConnect(sock, timeout)
            return sock

        except socket.error as _:
            err = _
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")


OLD_socket_create_connection = socket.create_connection


def setEnabled(enable=True):
    global OLD_socket_create_connection, AsyncHTTPResponse, Handler
    if enable:
        if module_logger.isEnabledFor(DEBUG):
            module_logger.debug('Asynchronous connections: Enabled')

        socket.create_connection = create_connection
        AsyncHTTPResponse = _AsyncHTTPResponse
        Handler = _Handler
    else:
        if module_logger.isEnabledFor(DEBUG):
            module_logger.debug('Asynchronous connections: Disabled')

        AsyncHTTPResponse = http.client.HTTPResponse
        Handler = urllib.request.HTTPHandler
        if OLD_socket_create_connection:
            socket.create_connection = OLD_socket_create_connection

# h = Handler()
# o = urllib2.build_opener(h)
# f = o.open(url)
# print f.read()
