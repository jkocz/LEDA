#!/usr/bin/env python
"""
sax.py -- Switching assembly board control
Python class for control of the Switching Assembly boards at LEDA-OVRO. 
This script talks to the rabbit boards that directly controls the swtiching
assembly state to select between sky, noise, load.
"""

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import socket

class saxController(object):
    """ Python class for control of the switching assembly 
    
    Arguments:
    ip_addr (str, int): Rabbit IP address and port. 
    connect (bool):     Connect to socket on initialization. Defaults to True.
    verbose (bool):     Enable or disable verbose output. Defaults to True.
    debug (bool):       Enable debug output (more expections raised). Defaults to False.
    """
    
    def __init__(self, ip_addr = ('192.168.25.7', 1738), 
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
    
    def sendCmd(self, cmd):
        """ Send a command to the rabbit.
        
        Arguments: cmd (str): command to send.
        Returns 0 if unsuccessful, or 1 if successful
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
        return 1
    
    def close(self):
        """ Close socket connection"""
        self.socket.close()
        self.is_connected = False
        if self.verbose:
            print "Socket closed"
    
    def start(self):
        """ Send start command to rabbit.
        
        This will start the switching assembly stepping between
        15, 16 and 17 V in order to switch between sky, noise and load.
        """
        s = self.sendCmd('start')
        
        if s == 1:
            print "Switching assembly started."
        else:
            print "Error: Could not start assembly."
    
    def hold(self):
        """ Send start command to rabbit.
        
        This will instruct the switching assembly to hold its current
        voltage level (keep it fixed on sky / noise / load)
        """
        s = self.sendCmd('hold')
        
        if s == 1:
            print "Switching assembly HOLD on current voltage."
        else:
            print "Error: Could not HOLD."
    
    def stop(self, really=False):
        """ Send STOP command to rabbit.
        
        You probably don't want to do this. It will stick the rabbit into
        'manual' mode, which can only be gotten out of by manually pressing
        buttons on the rabbit in real life.
        
        Arguments: really (Bool): really, really stop the rabbit running.
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

