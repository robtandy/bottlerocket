"""
bottlestats

This module will monkey patch the bottle python (http://bottlepy.org/) web
framework to send statistics to pystaggregator 
(https://github.com/robtandy/pystaggregator).

The approach is to install a bottle plugin to wrap callbacks and take note
of any uncaught exceptions and reraise them.  This lets us know about 500
errors, or any http status attached to a raised HTTPResponse.

We also monkey patch the Router class to override match() so that we are
aware of any 404 errors that are raised.  Timing is handled by the bottle 
before_request and after_request hooks.

Lastly, to make this transparent to any other users of the bottle module,
the bottle.Bottle class is replaced with one that installs these hooks
and the Router upon initialization.  

"""
from bottle import response, request, install, Bottle, Router, app, HTTPError,\
    HTTPResponse, AppStack
import bottle
import time
import os
import sys
import platform
from pystaggregator.client import Timer, start

# get the host and port number of pystaggregator
url = os.environ.get('STAGGREGATOR_URL', 'http://localhost:5201/v1/stat')
key = os.environ.get('STAGGREGATOR_KEY', None)

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
bottle.Router = InstrumentedRouter

_Bottle = Bottle
class InstrumentedBottle(_Bottle):
    def __init__(self, catchall=True, autojson=True):
        _Bottle.__init__(self, catchall, autojson)
        self.add_hook('before_request', before_hook)
        self.add_hook('after_request', after_hook)
        
        self.install(exception_wrapper)
bottle.Bottle = InstrumentedBottle

# patch the current Bottle() object that bottle puts on the AppStack
# by default
app[-1] = InstrumentedBottle()

# start up pystaggregator client
start(url, key)

