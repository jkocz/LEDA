#!/usr/bin/env python
"""
sax_epoch.py
------------

Return the current epoch of the switching assembly.
"""
import sax, time, datetime
import math

s = sax.SaxController()

# Wait for mid-second point
now   = time.time()
start = math.ceil(now) + 0.5
time.sleep(start - now)

for ii in range(3):
  status = s.status()
  print datetime.datetime.now(),
  print ": SAX state: %s" % status
  time.sleep(1)

s.close()

