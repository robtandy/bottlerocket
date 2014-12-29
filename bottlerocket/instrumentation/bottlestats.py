"""
bottlestats

This module will monkey patch the bottle python (http://bottlepy.org/) web
framework to send statistics to pystaggregator 
(https://github.com/robtandy/pystaggregator).

The approach is to install a bottle plugin to wrap callbacks and take note
of any uncaught exceptions and reraise them.  This lets us know about 500
errors, or any http status attached to a raised HTTPResponse.

See here: 
http://www.markbetz.net/2014/04/30/re-raising-exceptions-in-python/
regarding reraising (not wrapping) exceptions in python and preserving the
stack trace.  We simply use 'raise' not 'raise e' where e is our caught
exception.

We also monkey patch the Router class to override match() so that we are
aware of any 404 errors that are raised.  Timing is handled by the bottle 
before_request and after_request hooks.

Lastly, to make this transparent to any other users of the bottle module,
the bottle.Bottle class is replaced with one that installs these hooks
and the Router upon initialization.  

"""
import os

# first, importantly, figure out if we need to import gevent and
# monkey patch modules
if 'BOTTLEROCKET_GEVENT' in os.environ:
    to_patch = os.environ.get('BOTTLEROCKET_GEVENT').split(',')
    import gevent.monkey
    for func_name in to_patch:
        func = getattr(gevent.monkey, func_name)
        print('*** BOTTLEROCKET *** calling gevent.monkey.{}'.format(func_name))
        func()

import sys
import re
import platform
import config
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
config.name_prefix = namespace + '.' + my_hostname + '.http.' 

# get a list of all patterns if available
config.patterns = []
pattern_env = os.environ.get('BOTTLEROCKET_PATTERNS', '')
if os.path.exists(pattern_env):
    lines = [x.strip() for x in open(pattern_env).readlines()]
    for line in lines:
        name, pattern = line.split()
        config.patterns.append((name, re.compile(pattern)))

# patch bottlerocket    
import bottlerocket.patch.bottlepatch
    
# start up pystaggregator client, which starts lazily after this when
# first stat is sent
start(url, key)

