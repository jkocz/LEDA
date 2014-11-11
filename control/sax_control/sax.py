#!/usr/bin/env python
"""
sax.py -- Switching assembly board control
Python class for control of the Switching Assembly boards at LEDA-OVRO. 
This script talks to the rabbit boards that directly controls the swtiching
assembly state to select between sky, noise, load.
"""

"""
Command interface for new SAX assembly (November 2014)
------------------------------------------------------
Programmed address: 192.168.25.7:3023
1. "start":  On power up the Rabbit is in it's bit cycling mode.  The states
change on the rising edge of the interrupt.  It is not necessary to issue the
start command at system power up.

2. "hold_a":  Set the control lines to A0 = 0, A1 = 0.

3. "hold_b":  Set the control lines to A0 = 1, A1 = 0.

4. "hold_c":  Set the control lines to A0 = 0, A1 = 1.

5. "off"   :  Set the control lines to A0 = 1, A1 = 1.

6. "set_waits n n n":  Set the length of time to remain in each of the states.
At power up the states switch at 1 pps intervals.  For example, if you send the
command "set_waits 1 2 3" the rabbit will stay in state A for 1 second, state B
for 2 seconds and state 3 for 3 seconds.

7. "state":  returns the current state of output bits ("a', "b" or "c").

In addition to the changes in the command syntax I've made changes to the code
that stores the state of the rabbit when is it put into any of the hold or off
states.  When the "start" command is issued after a hold it will return to the
last state it was in when the hold or off commands were issued.
------------------------------------------------------
"""

# TODO: Implement 'state' request command

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import socket
import time

from leda_config import sax_config

class SaxController(object):
    """ Python class for control of the switching assembly 
    
    Parameters
    ----------
    ip_addr : (str, int)
        Rabbit IP address and port. 
    connect : (bool)   
        Connect to socket on initialization. Defaults to True.
    verbose : (bool)   
        Enable or disable verbose output. Defaults to True.
    debug   : (bool)   
        Enable debug output (more expections raised). Defaults to False.
    """
    
    def __init__(self, ip_addr = (sax_config.host, sax_config.port), 
                 connect = True, verbose = False, debug = False):
                 
        self.host = ip_addr[0]
        self.port = ip_addr[1]
        self.debug   = debug
        self.verbose = verbose
        self.socket = socket.socket()
        self.is_connected = False
        
        if connect:
            self.connect()
    
    def connect(self):
        """ Connect to Rabbit board via socket """
        if self.is_connected:
            print "Already connected on %s:%s"%(self.host, self.port)
        else:
            print "Connecting to %s:%s"%(self.host, self.port)
            try:
                self.socket.connect((self.host, self.port))
                self.is_connected = True
            except:
                print "Error: could not connect."
                if self.debug:
                   raise
    
    def sendCmd(self, cmd, return_response=False):
        """ Send a command to the rabbit.
        
        Parameters
        ---------- 
        cmd : (str) 
            command to send. Returns 0 if unsuccessful, or 1 if successful
        return_response : bool
            return the rabbit's response instead of 0 / 1. Defaults to False.
        """
        if not self.is_connected:
            self.connect()
            if not self.is_connected:
                print "Error: Socket cannot connect."
                if self.debug:
                    raise
                else:
                    return 0

        ret = self.socket.sendall(cmd)
        if self.verbose:
            print "Sent", ret, "bytes"
            print "Receiving..."
        ret = self.socket.recv(512)
        if self.verbose:
            print "Received:", ret
        if return_response:
            return ret
        else:
            return 1
    
    def close(self):
        """ Close socket connection"""
        self.socket.close()
        time.sleep(1)
        self.is_connected = False
        if self.verbose:
            print "Socket closed"
    
    def start(self):
        """ Send start command to rabbit.
        
        Notes
        -----
        This will start the switching assembly stepping between
        15, 16 and 17 V in order to switch between sky, noise and load.
        Switching is triggered by the 1PPS.
        """
        s = self.sendCmd('start')
        
        if s == 1:
            print "1PPS triggered switching started."
        else:
            print "Error: Could not start assembly."
    
    def start_switching(self):
        """ Send start command to rabbit.
        
        This will start the switching assembly stepping between
        15, 16 and 17 V in order to switch between sky, noise and load.
        """
        self.start()
    
    def hold(self):
        """ Send HOLD command to rabbit.
        
        This will instruct the switching assembly to hold at 15 V (sky/ant).
        
        Notes
        -----
        Deprecated in favor of hold_sky, hold_hot and hold_cold methods.
        """
        self.hold_sky()
            
    def hold_sky(self):
        """ Send start command to rabbit.
        
        This will instruct the switching assembly to hold its current
        voltage level (keep it fixed on sky / noise / load)
        """
        #s = self.sendCmd('hold_sky')
        s = self.sendCmd('hold_c')
        
        if s == 1:
            print "Switching assembly HOLD on SKY voltage (15 V)."
        else:
            print "Error: Could not HOLD."
            
    def hold_hot(self):
        """ Send HOLD_HOT command to rabbit.
        
        This will instruct the switching assembly to hold at 17 V (hot/diode)
        """
        #s = self.sendCmd('hold_hot')
        s = self.sendCmd('hold_b')
        
        if s == 1:
            print "Switching assembly HOLD on HOT voltage (17 V)."
        else:
            print "Error: Could not HOLD."

    def hold_cold(self):
        """ Send start command to rabbit.
        
        This will instruct the switching assembly to hold at 16 V (cold/load)
        """
        #s = self.sendCmd('hold_cold')
        s = self.sendCmd('hold_a')
        
        if s == 1:
            print "Switching assembly HOLD on COLD voltage (16 V)."
        else:
            print "Error: Could not HOLD."
    
    def status(self):
        """ Return current switching state """
        s = self.sendCmd('state', return_response=True)
         
        if s[0] == 'a':
           return 'sky'
        elif s[0] == 'b':
           return 'diode'
        elif s[0] == 'c':
           return 'load'
        else:
           return s
    
    def set_waits(self, nsecs_a, nsecs_b, nsecs_c):
        s = self.sendCmd('set_waits %i %i %i' % (nsecs_a, nsecs_b, nsecs_c))
        if s == 1:
            print "Set switching intervals to %i, %i, %i secs" % \
                (nsecs_a, nsecs_b, nsecs_c)
        else:
            print "Error: Failed to set switching intervals."
    
    def stop(self, really=False):
        """ Send STOP command to rabbit.
        
        You probably don't want to do this. It will stick the rabbit into
        'manual' mode, which can only be gotten out of by manually pressing
        buttons on the rabbit in real life.
        
        Parameters
        ---------- 
        really : (Bool)
            really, really stop the rabbit running.
        """
        if not really:
            print "WARNING: ARE YOU SURE? THIS WILL PUT THE RABBIT INTO"
            print "MANUAL MODE. YOU CANNOT EXIT THIS MODE REMOTELY."
            print "RUN THIS WITH ARGUMENT really=True IF YOU ARE SURE."
            print "COMMAND NOT SENT."
        else:
            s = self.sendCmd('stop')
            
            if s == 1:
                print "Switching assembly STOP."
            else:
                print "Error: Could not STOP."                    

