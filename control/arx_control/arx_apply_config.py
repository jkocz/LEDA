#!/usr/bin/env python
""" arx_apply_config.py -- apply ARX configuration file """

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import sys
import arx

if __name__ == "__main__":
    try:
        config_file = sys.argv[1]
    except:
        print "Usage: ./arx_apply_config.py filename"
        exit()
        
    a = arx.ArxOVRO(verbose=False)
    a.loadSettings(config_file)
    a.listSettings()
    a.applySettings()