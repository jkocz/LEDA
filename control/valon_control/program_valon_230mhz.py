#!/usr/bin/env python

from valon_synth import *

if __name__ == "__main__":
    synth = Synthesizer("/dev/ttyUSB0")
    print "Freq:    ", synth.get_frequency(SYNTH_A)
    print "Ref:     ", "external" if synth.get_ref_select()==1 else "internal"
    print "Ref freq:", synth.get_reference()
    
    synth.set_frequency(SYNTH_A, 230.0)
    print "Freq:    ", synth.get_frequency(SYNTH_A)
    synth.flash() 
     
    #ref = "external"
    #ref = "internal"
    #synth.set_ref_select(1 if ref=="external" else 0)
    #synth.flash()
