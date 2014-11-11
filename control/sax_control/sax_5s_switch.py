#!/usr/bin/env python

import sax
import time

s = sax.SaxController()

print "Switching every 5s. Press ctrl + C to interrupt"

while True:
    s.hold_sky()
    time.sleep(5)
    s.hold_cold()
    time.sleep(5)
    s.hold_hot()
    time.sleep(5)

s.close()

