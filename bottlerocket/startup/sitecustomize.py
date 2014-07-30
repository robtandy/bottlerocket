import os
import sys

# add bottlerocket to the search path
my_dir = os.path.dirname(__file__)
two_up = os.path.dirname(os.path.dirname(my_dir))

sys.path.insert(0, two_up)

#print sys.path

# import bottle stats
from bottlerocket.instrumentation import bottlestats

# proceed as normal from here
