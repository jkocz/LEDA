#!/usr/bin/env python

import sax
import time

s = sax.SaxController()

print "Switching every 15s. Press ctrl + C to interrupt"

while True:
    s.hold_sky()
    time.sleep(15)
    s.hold_cold()
    time.sleep(15)
    s.hold_hot()
    time.sleep(15)

s.close()

