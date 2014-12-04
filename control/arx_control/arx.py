#!/usr/bin/env python
# PURPLE = UP (with board upside-down)
"""
arx.py -- Analog receiver board control
Python class for control of the ARX boards at LEDA-OVRO. This script
talks to the rabbit boards that directly control the attenuators and
other settings on the ARX boards.
"""

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import socket, time, sys, os
import numpy as np

from leda_config import arx_config

class ArxController(object):
    """ Python class for ARX control at LEDA-OVRO (via rabbit boards).
    
    Arguments:
        txAddr (str, int): Transmit IP address and port. 
        rxAddr (str, int): Receive IP address and port.
        nBoards (int):     Number of boards per rabbit. Default is 8 for LEDA-OVRO.
        connect (bool):    Connect to socket on initialization. Defaults to True. 
        sleep (float):     Time to sleep in seconds between commands. Default 0.03s
        verbose (bool):    Enable or disable verbose output.
        
    Notes:
        Only rx and tx address and port should require configuration. 
        A separate ArxController is needed for each ARX shelf.
        Each shelf has eight ARX boards, each board controls 16 signal paths.
        LEDA-OVRO has 4 shelves * 8 boards * 16 paths = 512 inputs.
        Earlier ARX setups at LEDA-OVRO had one rabbit controlling multiple ARX 
        shelves. This was really unreliable, so now we have one rabbit for each
        ARX shelf. 
    """
    
    splitFilter    = 0
    fullFilter     = 1
    reducedFilter  = 2
    signalChainOff = 3
    
    def __init__(self,
                 txAddr  = arx_config.arx1_txAddr,
                 rxAddr  = arx_config.rx_addr,
                 nBoards = 8,
                 connect = True,
                 sleep   = 0.03,
                 verbose = False):
        #self.nBoards = boards
        self.nBoards   = nBoards
        self.txAddr    = txAddr
        self.rxAddr    = rxAddr
        self.is_connected   = False
        if connect:
            self.connect()
        
        self.sleep = sleep
        self.lastCmdTime = 0
        self.verbose = verbose
    
    def __repr__(self):
        toprint = "### ARX controller\nTX address: "
        toprint += self.txAddr[0]
        toprint += ":"
        toprint += str(self.txAddr[1])
        toprint += "\nRX address: "
        toprint += self.rxAddr[0]
        toprint += ":"
        toprint += str(self.rxAddr[1])
        return toprint
        
    def connect(self):
        """ Connect to rabbit board via socket"""
        if not self.is_connected:
            self.txSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rxSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rxSocket.bind(self.rxAddr)
            self.rxSocket.settimeout(20)
            self.is_connected = True
        else:
            if self.verbose:
                print "Socket already connected."
    
    def close(self):
        """ Close socket connections to rabbit """
        if self.is_connected: 
            self.txSocket.close()
            self.rxSocket.close()
            self.is_connected = False
        else:
            if self.verbose:
                print "Socket already closed."
    
    def __del(self):
        """ Close socket connections to rabbit. """
        self.close()
    
    def _sendCommand(self, cmd, data):
        """ Send a generic command to the rabbit board """
        if not self.is_connected:
            self.connect()
        sleepTime = self.lastCmdTime + self.sleep - time.time()
        if sleepTime > 0:
            time.sleep(sleepTime)
        cmdStr = 'ASPMCS%s%9d%4d%6d%9d %s' % (cmd, 0, len(data), 0, 0, data)
        if self.verbose:
            print 'ASP TX: "%s"' % cmdStr
        self.txSocket.sendto(cmdStr, self.txAddr)
        try:
            response = self.rxSocket.recv(1024).rstrip('\x00')
            if self.verbose:
                print 'ASP RX: "%s"' % response
        except socket.timeout:
            response = None
            if self.verbose:
                print 'ASP RX timed out!'
        self.lastCmdTime = time.time()
        return response
    
    def initialize(self):
        """ Initialize connection to rabbit """
        if not self.is_connected:
            self.connect()
        
        #self._sendCommand('SHT', '')
        self._sendCommand('INI', '%02d' % self.nBoards)
        #self._sendCommand('FPW', '000111')
        #self._sendCommand('FPW', '000211')
    
    def shutdown(self):
        """ Send shutdown signal. 
        
        Sending the shutdown signal will turn everything off.
        """
        #self._sendCommand('FPW', '000100')
        #self._sendCommand('FPW', '000200')
        self._sendCommand('SHT', '')
    
    def powerFEE(self, xpol = True, ypol = None,  stand = 0):
        """ Turn power to antenna FEE on and off.
        
        Arguments:
            xpol (bool): Turn on Pol X?
            ypol (bool): Turn on Pol Y? If not set, xpol value is used
            stand (int): Stand number.  If set to zero, applied to all stands.
        """
        if ypol is None:
            ypol = xpol
        xCode = '11' if xpol else '00'
        yCode = '11' if ypol else '00'
        if stand == 0:
            for stand in xrange(1, 8 * self.nBoards + 1):
                self._sendCommand('FPW', '%03d1%s' % (stand, xCode))
                self._sendCommand('FPW', '%03d2%s' % (stand, yCode))
        else:
            self._sendCommand('FPW', '%03d1%s' % (stand, xCode))
            self._sendCommand('FPW', '%03d2%s' % (stand, yCode))
    
    def setFilter(self, filterNum, stand = 0):
        """ Configure ARX filters.
        
        Arguments:
            filternum (int): Filter number to enable. See notes for more.
            stand (int): Stand number.  If set to zero, applied to all stands.
            
        Notes:
            The possible filter values are:
            splitFilter    = 0      (Normal operation mode)
            fullFilter     = 1      
            reducedFilter  = 2      (Narrowband)
            signalChainOff = 3
        
        TODO: Check this does what I think it does.
        """
        if stand == 0:
            for stand in xrange(1, 8 * self.nBoards + 1):
                self._sendCommand('FIL', '%03d%02d' % (stand, filterNum))
        else:
            self._sendCommand('FIL', '%03d%02d' % (stand, filterNum))
    
    def setAT1(self, dB, stand = 0):
        """ Set level of first attenuator 
        
        Arguments:
            dB (int): Attenuation to apply, in decibels.
            stand (int): Stand number. If set to zero, applied to all stands.
        """
        if stand == 0:
            for stand in xrange(1, 8 * self.nBoards + 1):
                self._sendCommand('AT1', '%03d%02d' % (stand, dB / 2))
        else:
            self._sendCommand('AT1', '%03d%02d' % (stand, dB / 2))
    
    def setAT2(self, dB, stand = 0):
        """ Set level of second attenuator
        
        Arguments:
            dB (int): Attenuation to apply, in decibels.
            stand (int): Stand number. If set to zero, applied to all stands.
        """
        if stand == 0:
            for stand in xrange(1, 8 * self.nBoards + 1):
                self._sendCommand('AT2', '%03d%02d' % (stand, dB / 2))
        else:
            self._sendCommand('AT2', '%03d%02d' % (stand, dB / 2))
    
    def setATS(self, dB, stand = 0):
        """ Set attenuator level in split-band filter
        
        Arguments:
            dB (int): Attenuation to apply at each attenuator, in dB.
            stand (int): Stand number. If set to zero, applied to all stands.
        """
        if stand == 0:
            for stand in xrange(1, 8 * self.nBoards + 1):
                self._sendCommand('ATS', '%03d%02d' % (stand, dB / 2))
        else:
            self._sendCommand('ATS', '%03d%02d' % (stand, dB / 2))

class ArxOVRO(object):
    """ ARX configurer class for LEDA-OVRO.
    
    Manages connection between the four ARX shelves at LEDA-OVRO.
    
    Arguments:
        txAddr (str, int): Transmit IP address and port. 
        rxAddr (str, int): Receive IP address and port.
        nBoards (int): Number of boards per rabbit. Default is 8 for LEDA-OVRO.
        sleep (float): Time to sleep in seconds between commands. Default 0.03s
        verbose (bool): Enable or disable verbose output.
    
    Notes:
        Essentially a wrapper of four ArxController() instances.
    """
    def __init__(self, verbose=False):
        arx1_txAddr = arx_config.arx1_txAddr
        arx2_txAddr = arx_config.arx2_txAddr
        arx3_txAddr = arx_config.arx3_txAddr
        arx4_txAddr = arx_config.arx4_txAddr
        rxAddr      = arx_config.rx_addr
        
        nBoards     = 8       # All shelves have 8 boards
        connect     = False   # Only one board can be connected to at once
        sleep       = 0.03    # Time to sleep in between commands
        
        # Create child ARX Controller instances
        self.current_connection = None
        self.arx1 = ArxController(arx1_txAddr, rxAddr, nBoards, connect, sleep, verbose)
        self.arx2 = ArxController(arx2_txAddr, rxAddr, nBoards, connect, sleep, verbose)
        self.arx3 = ArxController(arx3_txAddr, rxAddr, nBoards, connect, sleep, verbose)
        self.arx4 = ArxController(arx4_txAddr, rxAddr, nBoards, connect, sleep, verbose)
        self.arxlist = [self.arx1, self.arx2, self.arx3, self.arx4]
        
        # Setup lists for ARX setup storage
        self.at1_settings  = [10 for ii in range(256)]
        self.at2_settings  = [10 for ii in range(256)]
        self.ats_settings  = [30 for ii in range(256)]
        self.fee_settings  = [(False, False) for ii in range(256)]
        self.fil_settings  = [0 for ii in range(256)]
        self.bad_stands    = [0 for ii in range(256)]
        self.semi_stands   = [0 for ii in range(256)]
        
    
    def __repr__(self):
        toprint = "### LEDA-OVRO ARX CONTROLLER\n"
        toprint += "%s \n"%self.arx1.__repr__()
        toprint += "%s \n"%self.arx2.__repr__()
        toprint += "%s \n"%self.arx3.__repr__()
        toprint += "%s \n"%self.arx4.__repr__()
        return toprint
    
    def getStandSettings(self, stand_idx):
        """ Return a tuple of stand settings.
        
        returns:
            Tuple of (at1, at2, ats, fil, fee)
        """
        at1  = self.at1_settings[stand_idx]
        at2  = self.at2_settings[stand_idx]
        ats  = self.ats_settings[stand_idx]
        fil  = self.fil_settings[stand_idx]
        fee  = self.fee_settings[stand_idx]
        return at1, at2, ats, fil, fee
        
    def loadSettings(self, filename):
        """ Load ARXsettings from file 
        
        Arguments:
            filename (str): name of file to open
        """
        execfile(filename, self.__dict__)
        
    def saveSettings(self, filename):
        """ Save ARX settings to file 
        
        Arguments:
            filename (str): name of file to save as
        """
        f = open(filename, 'w')
        f.write("bad_stands = [%s]\n" \
                    % ", ".join([str(x) for x in self.bad_stands]))
        f.write("\n")
        f.write("semi_stands = [%s]\n" \
                    % ", ".join([str(x) for x in self.semi_stands]))
        f.write("\n")
        f.write("at1_settings = [%s]\n" \
                    % ", ".join([str(x) for x in self.at1_settings]))
        f.write("\n")
        f.write("at2_settings = [%s]\n" \
                    % ", ".join([str(x) for x in self.at2_settings]))
        f.write("\n")
        f.write("ats_settings = [%s]\n" \
                    % ", ".join([str(x) for x in self.ats_settings]))
        f.write("\n")
        f.write("fee_settings = [%s]\n" \
                    % ", ".join([str(x) for x in self.fee_settings]))
        f.write("\n")
        f.write("fil_settings = [%s]\n" \
                    % ", ".join([str(x) for x in self.fil_settings]))
        f.write("\n")
        f.close()

    def saveSettingsCsv(self, filename):
        """ Save ARX settings to tabbed CSV file

        filename (str): name of file
        """

        ids = range(1, 257)
        d = np.column_stack((ids, self.at1_settings, self.at2_settings, self.ats_settings,
                             self.fil_settings, self.fee_settings,
                             self.bad_stands, self.semi_stands))

        np.savetxt(filename, d, delimiter='\t',
                   header='ANT\tAT1\tAT2\t\ATS\tFIL\tFEE\tBAD\tSEMI')

    def loadSettingsCsv(self, filename, path=arx_config.arx_report_dir):
        """

        filename (str): name of file
        path (str): path to file
        """
        fp = os.path.join(path, filename)
        d = np.genfromtxt(fp, delimiter='\t', skip_header=1)

        self.at1_settings = d[:, 0]
        self.at2_settings = d[:, 1]
        self.ats_settings = d[:, 2]
        self.fil_settings = d[:, 3]
        self.fee_settings = d[:, 4]
        self.bad_stands   = d[:, 5]
        self.semi_stands  = d[:, 6]


    def applySettings(self, set_at1=True, set_at2=True, set_ats=True, set_fil=True, set_fee=True):
        """ Apply all settings to all ARX boards.
        
        Applies settings (as stored in self.*_settings lists).
        
        Arguments:
            set_at1 (bool): Set first attenuator. Default True.
            set_at2 (bool): Set second attenuator. Default True.
            set_ats (bool): Set split-level attenuator. Default True.
            set_fil (bool): Set filters. Default True.
            set_fee (bool): Set fee power. Default True.
        """
        arxlist = self.arxlist
        
        for ii in range(len(arxlist)):
            print "Applying to ARX %i..."%(ii+1)
            arxlist[ii].connect()
            arxlist[ii].initialize()
            print arxlist[ii]
            time.sleep(0.1)
            self.printHeader()
            
            for jj in range(64):
                stand_num = ii*64 + jj + 1
                stand_idx = stand_num - 1
                bd_stand  = jj + 1
                at1, at2, ats, fil, fee = self.getStandSettings(stand_idx)
                print "%5s |%4s |%4s |%4s |%4s | %6s"%(stand_num, at1, at2, ats, fil, fee)
                if set_at1:
                    arxlist[ii].setAT1(at1, bd_stand)
                if set_at2:
                    arxlist[ii].setAT2(at2, bd_stand)
                if set_ats:
                    arxlist[ii].setATS(ats, bd_stand)
                if set_fil:
                    arxlist[ii].setFilter(fil, bd_stand)
                if set_fee:
                    arxlist[ii].powerFEE(fee[0], fee[1], stand = bd_stand)
            #arxlist[ii].shutdown()
            arxlist[ii].close()
            time.sleep(0.1)
    
    def applySingle(self, stand, print_header=True):
        """ Apply settings to a single ARX path 
        
        Arguments:
            stand (int): Stand to apply settings to.
            print_header (bool): print table header. Defaults to True.
        """
        arxlist = self.arxlist
        arx_idx   = int(stand / 64)
        if arx_idx == 4:
            arx_idx = 3
        stand_idx = stand - 1
        bd_stand  = (stand_idx % 64) + 1
        
        at1, at2, ats, fil, fee = self.getStandSettings(stand_idx)
        
        arxlist[arx_idx].connect()
        arxlist[arx_idx].initialize()
        arxlist[arx_idx].setAT1(at1, bd_stand)
        arxlist[arx_idx].setAT2(at2, bd_stand)
        arxlist[arx_idx].setATS(ats, bd_stand)
        arxlist[arx_idx].setFilter(fil, bd_stand)
        arxlist[arx_idx].powerFEE(fee[0], fee[1], stand = bd_stand)
        #arxlist[arx_idx].shutdown()
        arxlist[arx_idx].close()
        
        if print_header:        
            self.printHeader()
        print "%5s |%4s |%4s |%4s |%4s | %6s"%(stand, at1, at2, ats, fil, fee)
        
    
        
    def listSettings(self, stand_num = None):
        """ prints the configured values for each stand 
        
        Arguments:
            stand_num (int): Stand ID to return settings for. If not set,
                             a list of all stand values will be returned.
                             NB: First stand is 1, not 0.
        """
        
        self.printHeader()
        if not stand_num:
            stand_ids = range(1, 256+1)
        else:
            stand_ids = [stand_num]
        for ii in stand_ids:
            at1, at2, ats, fil, fee = self.getStandSettings(ii - 1)
            print "%5s |%4s |%4s |%4s |%4s | %6s"%(ii, at1, at2, ats, fil, fee)
    
    def printHeader(self):
        """ Print table header to screen """
        print "STAND | AT1 | AT2 | ATS | FIL | FEE "
        print "------|-----|-----|-----|-----|----------"
    
    def setAT1(self, dB, stand=0):
        """ Set level of first attenuator
        
        Arguments:
            dB (int): Attenuation to apply, in decibels.
            stand (int): Stand number (from 1). If set to 0, applied to all stands.
        """
        if stand == 0:
            self.at1_settings = [dB for ii in range(256)]
        else:
            self.at1_settings[stand - 1] = dB
    
    def setAT2(self, dB, stand=0):
        """ Set level of second attenuator
        
        Arguments:
            dB (int): Attenuation to apply, in decibels.
            stand (int): Stand number. If set to zero, applied to all stands.
        """
        if stand == 0:
            self.at2_settings = [dB for ii in range(256)]
        else:
            self.at2_settings[stand - 1] = dB

    def setATS(self, dB, stand=0):
        """ Set level of split-level attenuator
        
        Arguments:
            dB (int): Attenuation to apply, in decibels.
            stand (int): Stand number. If set to zero, applied to all stands.
        """
        if stand == 0:
            self.ats_settings = [dB for ii in range(256)]
        else:
            self.ats_settings[stand - 1] = dB
        
    def setFilter(self, filterNum, stand = 0):
        """ Configure ARX filters.
        
        Arguments:
            filternum (int): Filter number to enable. See notes for more.
            stand (int): Stand number.  If set to zero, applied to all stands.
            
        Notes:
            The possible filter values are:
            splitFilter    = 0   (Normal operating mode)
            fullFilter     = 1
            reducedFilter  = 2   (Narrowband operating mode)
            signalChainOff = 3
        """
        if stand == 0:
            self.fil_settings = [filterNum for ii in range(256)]
        else:
            self.fil_settings[stand - 1] = filterNum
        
    def powerFEE(self, xpol = True, ypol = None,  stand = 0):
        """ Turn power to antenna FEE on and off.
        
        Arguments:
            xpol (bool): Turn on Pol X?
            ypol (bool): Turn on Pol Y? If not set, xpol value is used
            stand (int): Stand number.  If set to zero, applied to all stands.
        
        TODO: Implement!
        """
        if stand == 0:
            self.fee_settings = [(xpol, ypol) for ii in range(256)]
        else:
            self.fee_settings[stand - 1] = (xpol, ypol)

    def setFEE(self, xpol = True, ypol = None,  stand = 0):
        """ Alias for powerFEE() method """
        self.powerFEE(xpol, ypol, stand)
    
    def disableBadStands(self):
        """ Set bad stands to be turned off """
        print "Disabling stands marked as faulty..."
        for ii in range(len(self.at1_settings)):
            if self.bad_stands[ii] == 1 or self.semi_stands[ii] == 1:
                self.setFEE(False, False, ii+1)
                self.setFilter(3, ii+1)
                self.applySingle(ii+1, print_header=False)
    
if __name__ == '__main__':
    # Basic testing and examples
    txAddr = ('192.168.25.2', 1738)
    rxAddr = ('192.100.16.226', 1739)
    sleep = 0.03
    verbose = False
    
    # Create an ARX controller object
    a = ArxController(txAddr, rxAddr, sleep, verbose)
    #a.shutdown()
    a.initialize()
    
    # Configure ARX settings
    a.setAT1(10)      # Set first attenuator to 10  dB for all boards
    a.setAT2(10)      # Set second attenuator to 10 dB for all boards
    a.setFilter(1)    # Set filter to 1 for all boards (Full filter)
    a.powerFEE(True)  # Turn on all FEE boards
    #a.shutdown()
    a.close()
    
    # Test examples for ArxOVRO class
    a = arx.ArxOVRO()
    a.at1_settings = [10 for ii in range(256)]
    a.at2_settings = [10 for ii in range(256)]
    a.fee_settings = [1 for ii in range(256)]
    a.fee_settings = [(False, False) for ii in range(256)]
    a.fil_settings = [1 for ii in range(256)]
    a.listSettings()
