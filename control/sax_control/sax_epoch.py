#!/usr/bin/env python
"""
sax_epoch.py
------------

Return the current epoch of the switching assembly.
"""
import sax, time, datetime

s = sax.SaxController()

for ii in range(3):
  status = s.status()
  print datetime.datetime.now(),
  print ": SAX state: %s" % status
  time.sleep(1)

s.close()

