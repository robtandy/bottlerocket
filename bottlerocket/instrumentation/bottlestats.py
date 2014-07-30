from bottle import response, request, install, Bottle, Router, app, HTTPError,\
    HTTPResponse
import time
import os
import sys
import platform
from pystaggregator.client import Timer, connect

# get the host and port number of pystaggregator
host = os.environ.get('PYSTAGGREGATOR_HOST', 'localhost')
port = os.environ.get('PYSTAGGREGATOR_PORT', 5201)

# get our namespace for stats
if not 'BOTTLEROCKET_NAMESPACE' in os.environ:
    sys.stderr.write('BOTTLEROCKET_NAMESPACE environment variable not set.')
    sys.exit(1)
namespace = os.environ['BOTTLEROCKET_NAMESPACE']

# hostname also forms part of the stat name
my_hostname = platform.node() if len(platform.node()) > 0 else 'unknown_host'

# all stats begin with this prefix
name_prefix = namespace + '.' + my_hostname + '.http.' 

def before_hook():
    t = Timer()
    request._bottlerocket_timer = t
    t.start()

def after_hook():
    status = request._bottlerocket_exception_status
    if status is None:
        status = response.status_code

    name = name_prefix + request.method + '.' + str(status) + '.duration'
    request._bottlerocket_timer.end(name)

# Subclass bottle.Router because we need to capture any routing exceptions
_Router = Router
class InstrumentedRouter(_Router):
    def match(self, environ):
        try:
            retval = _Router.match(self, environ)
            request._bottlerocket_exception_status = None
        except HTTPError as e:
            request._bottlerocket_exception_status = e.status_code
            raise e
        
        return retval
Router = InstrumentedRouter

_Bottle = Bottle
class InstrumentedBottle(_Bottle):
    def __init__(self, catchall=True, autojson=True):
        Bottle.__init__(self, catchall, autojson)
        self.add_hook('before_request', before_hook)
        self.add_hook('after_request', after_hook)
Bottle = _Bottle

# install this bottle plugin to run callbacks per usual and capture
# any exceptions that may arrise.  Save them in 
def exception_wrapper(callback):
    def wrapper(*args, **kwargs):
        try:
            request._bottlerocket_exception_status = None
            body = callback(*args, **kwargs)
            return body
        except HTTPResponse as e:
            request._bottlerocket_exception_status = e.status_code
            raise e
        except Exception as e:
            request._bottlerocket_exception_status = 500
            raise e
    return wrapper
install(exception_wrapper)

# patch the current Bottle() object that bottle puts on the AppStack
# by default
app[-1].add_hook('before_request', before_hook)
app[-1].add_hook('after_request', after_hook)
app[-1].router = Router()

namespace = os.environ['BOTTLEROCKET_NAMESPACE']
# connect to pystaggregator
connect(host, port)

