#!/usr/bin/env python

from distutils.core import setup
import bottlerocket 

V =  bottlerocket.__version__

setup(name='bottlerocket',
      version=V,
      author='Rob Tandy',
      author_email='rob.tandy@gmail.com',
      url='https://github.com/robtandy/bottlerocket',
      long_description="""
      Bottlerocket instruments any code using the excellent bottle web 
      framework (http://www.bottlepy.org) to send timing information 
      to a running staggregator instance 
      (https://github.com/robtandy/staggregator) for aggregation and
      delivery to graphite.""",
      packages=['bottlerocket', 'bottlerocket.startup', 
          'bottlerocket.instrumentation'],
      scripts=['bin/bottlerocket'],
      install_requires=["pystaggregator >= 0.2.0", "bottle >= 0.10.0"],
)
