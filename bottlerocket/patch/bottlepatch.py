from bottle import response, request, install, Bottle, Router, app, HTTPError,\
    HTTPResponse, AppStack

import bottle
import time
import bottlerocket.instrumentation.config as config
from pystaggregator.client import Timer, start

config_patterns = config.patterns
config_name_prefix = config.name_prefix

BOTTLE_MINOR_VERSION = int(bottle.__version__.split('.')[1])

def before_hook():
    t = Timer()
    request._bottlerocket_timer = t
    t.start()

def after_hook():
    status = request._bottlerocket_status

    
    # check to see if we are using the short form name or long form name with
    # a pattern
    match = 'unmatched'
    for pname, pattern in config_patterns:
        m = pattern.search(request.path)
        if m:
            match = pname
            break
    
    if len(config_patterns) > 0:   # we are using the pattern name style
        name = config_name_prefix + match + '.' + request.method + \
                '.' + str(status) + '.duration'
    else:
        name = config_name_prefix + request.method + '.' + str(status) + \
                '.duration'
    request._bottlerocket_timer.end(name)

# install this bottle plugin to run callbacks per usual and capture
# any exceptions that may arise.  Save them in the thread local request
def exception_wrapper(callback):
    def wrapper(*args, **kwargs):
        try:
            request._bottlerocket_status = 200
            retval = callback(*args, **kwargs)
            
            if isinstance(retval, HTTPResponse):
                # capture the status code here, as HTTPResponses cn be raised
                # or returned, remember
                request._bottlerocket_status = retval.status_code
            elif response.status_code != 200:
                # it was set using the response.status property and needs to
                # be captured
                request._bottlerocket_status = response.status_code
            return retval
        except HTTPResponse as e:
            request._bottlerocket_status = e.status_code
            raise
        except Exception as e:
            request._bottlerocket_status = 500
            
            if BOTTLE_MINOR_VERSION < 12:
                # we need to call it because prior to 0.12.0, exceptions
                # raised in the callback don't call the after_request hook
                after_hook()
            raise
    return wrapper



# Subclass bottle.Router because we need to capture any routing exceptions
_Router = Router
class InstrumentedRouter(_Router):
    def match(self, environ):
        try:
            retval = _Router.match(self, environ)
        except HTTPError as e:
            request._bottlerocket_status = e.status_code
            if BOTTLE_MINOR_VERSION < 12:
                # we need to call it because prior to 0.12.0, exceptions
                # raised in match don't call hooks
                before_hook()
                after_hook()
            raise
        return retval
bottle.Router = InstrumentedRouter

_Bottle = Bottle
class InstrumentedBottle(_Bottle):
    def __init__(self, catchall=True, autojson=True):
        _Bottle.__init__(self, catchall, autojson)

        if BOTTLE_MINOR_VERSION >= 12:
            # >= 0.12.0 way of adding hooks
            self.add_hook('before_request', before_hook)
            self.add_hook('after_request', after_hook)
        else:
            self.hook('before_request')(before_hook)
            self.hook('after_request')(after_hook)
        
        self.install(exception_wrapper)


bottle.Bottle = InstrumentedBottle

# replace the Bottle() object that bottle puts on the AppStack by default
app[-1] = InstrumentedBottle()

print('*** BOTTLEROCKET *** patched bottle.py')
