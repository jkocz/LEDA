#!/usr/bin/env python

# 192.168.25.7 3023

import sax
#s = sax.SaxController(("192.168.25.7", "3023"))
"""
for port in xrange(0, 10000):
    print "Trying to connect via port", port
    s = sax.SaxController(("192.168.25.7", "1738"))
    if s.is_connected:
        print "CONNECTED! Port =", port
        break
"""
#s = sax.SaxController(("192.168.25.7", 3023), verbose=True, debug=True)
#s = sax.SaxController(("192.168.25.7", 1738), verbose=True, debug=True)
#s = sax.SaxController(verbose=True, debug=True)
s = sax.SaxController()
#s.sendCmd("state")
#s.hold_sky()
s.close()

