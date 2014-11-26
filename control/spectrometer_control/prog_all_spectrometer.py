#!/usr/bin/env python
"""
prog_all_specrtometer.py
-----------------------
Program all ROACH boards with spectrometer firmware
"""

from multiprocessing import Process, JoinableQueue, Array
import subprocess
import time, sys, os
from corr import katcp_wrapper
import numpy as np

from leda_config import spectrometer_config as config
from ledaspec import Ledaspec

def db(x):
    return 10*np.log10(x)

def progdev_adc16(roach, q, boffile, gain):
    """ Run subprocess to reprogram and calibrate ADC """
    reg_gain = '0x2a=0x%i%i%i%i'%(gain, gain, gain, gain)
    sp = subprocess.Popen(["adc16_init.rb", roach, boffile, '-r', reg_gain], stdout=subprocess.PIPE)
    out, err = sp.communicate()
    q.put(out)
    return

def progdev_all(boffile, gain, verbose=True):
    """ Initialize all roach boards with boffile and gain settings """
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach = len(roachlist)

    print "Programming all roaches with %s"%boffile
    print "Gain value: %ix"%gain
    print "Please wait..."
    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for i in range(n_roach):
        p = Process(target=progdev_adc16, args=(roachlist[i], q, boffile, gain))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads
    for p in procs:
        p.join()

    # Print messages
    while q.empty() is False:
        qo = q.get()
        if verbose:
            print q.get()
    print "OK"

def init_registers(roach, q, reg_dict):
    """ Initialize roach registers via register:value dictionary """
    fpga = katcp_wrapper.FpgaClient(roach)

    allsystemsgo = True
    ts = time.time()
    time.sleep(0.1)
    while not fpga.is_connected() and allsystemsgo:
        time.sleep(0.1)
        tn = time.time()
        if tn - ts > 5:
            q_output = (roach , "TIMEOUT ERROR: cannot initialize %s"%roach )
            allsystems_go = False

    if allsystemsgo:
        for key in reg_dict:
            try:
                fpga.write_int(key, reg_dict[key])
            except RuntimeError:
                q_output = (roach , "WRITE_INT ERROR: cannot initialize %s"%roach)
                allsystemsgo = False

    if allsystemsgo:
        q_output = (roach , "%s registers initialized."%roach)

    fpga.stop()
    q.put(q_output)
    return

def issue_reset(roach, q):
    """ Send reset command to roach board """
    fpga = katcp_wrapper.FpgaClient(roach)

    allsystemsgo = True
    ts = time.time()
    time.sleep(0.1)
    while not fpga.is_connected() and allsystemsgo:
        time.sleep(0.1)
        tn = time.time()
        if tn - ts > 5:
            allsystems_go = False

    if allsystemsgo:
        try:
            fpga.write_int('rst', 0)
            fpga.write_int('rst', 1)
            fpga.write_int('rst', 0)
        except RuntimeError:
            allsystemsgo = False

    if allsystemsgo:
        q_output = (roach, True)
    else:
        q_output = (roach, False)

    fpga.stop()
    q.put(q_output)
    return

def init_registers_all(reg_dict, verbose=True):
    """ Initialize all roaches via register:value dictionary """
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach = len(roachlist)

    if verbose:
        print "Initializing all roaches with:"
        for key in reg_dict:
            print "%16s  %s"%(key, reg_dict[key])

    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for i in range(n_roach):
        p = Process(target=init_registers, args=(roachlist[i], q, reg_dict))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads
    for p in procs:
        p.join()

    # Print messages
    to_print = {}
    while q.empty() is False:
        rd = q.get()
        to_print[rd[0]] = rd[1]

    if verbose:
        for r in roachlist:
            print to_print[r]

        print "OK"

def issue_reset_all(verbose=True):
    """ Send reset command to all roaches"""
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach = len(roachlist)

    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for i in range(n_roach):
        p = Process(target=issue_reset, args=(roachlist[i], q))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads
    for p in procs:
        p.join()

    # Print messages
    to_print = {}
    while q.empty() is False:
        rd = q.get()
        to_print[rd[0]] = rd[1]

    all_reset = True
    for r in roachlist:
        if to_print[r] is False:
            print "ERROR: %s did not reset."%r
            all_reset = False

    if all_reset:
        if verbose:
            print "Reset OK"
    else:
        print "ERROR: not all board reset correctly."


def snap_spec(roach, xarr, yarr, q):
    """ Snap spectra on a given roach """

    ants = {}
    roach_id = int(roach.lstrip("rofl"))
    rs = Ledaspec(roach)

    allsystemsgo = True
    ts = time.time()
    time.sleep(0.1)
    while not rs.fpga.is_connected() and allsystemsgo:
        time.sleep(0.1)
        tn = time.time()
        if tn - ts > 5:
            allsystems_go = False

    if allsystemsgo:
        try:
            for ii in [0, 8]:
                rs.fpga.write_int('ant_sel1', ii+0)
                rs.fpga.write_int('ant_sel2', ii+1)
                rs.fpga.write_int('ant_sel3', ii+2)
                rs.fpga.write_int('ant_sel4', ii+3)
                rs.fpga.write_int('ant_sel5', ii+4)
                rs.fpga.write_int('ant_sel6', ii+5)
                rs.fpga.write_int('ant_sel7', ii+6)
                rs.fpga.write_int('ant_sel8', ii+7)

                rs.primeSnap()
                rs.wait_for_acc()
                rs.primeSnap()
                rs.wait_for_acc()
                xx, yy = rs.snapUnpack()


                #print xx.shape, yy.shape

                try:
                    for jj in range(0, 8):
                        jz = jj + ii
                        for arr_idx in range(4096):
                            xarr[jz*4096 + arr_idx] = db(xx[jj][arr_idx])
                            yarr[jz*4096 + arr_idx] = db(yy[jj][arr_idx])
                except IndexError:
                    print "JJ, arr_idx", jj, arr_idx
                    print "len_xx, len_xarr", len(xx), len(xarr)
                    print "len_yy, len_yarr", len(yy), len(yarr)
                    allsystemsgo = False

        except RuntimeError:
            allsystemsgo = False

    if allsystemsgo:
        q_output = (roach, "OK: %s complete"%roach)
    else:
        q_output = (roach, "ERROR: couldn't grab spectrum")

    rs.fpga.stop()
    q.put(q_output)
    return

def snap_spec_all(verbose=False):
    """ Grab spectra for all ADC inputs """
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach = len(roachlist)

    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    xarrs  = [Array('f', range(4096 * 16)) for roach in roachlist]
    yarrs  = [Array('f', range(4096 * 16)) for roach in roachlist]
    ants = {}

    print "Snap cycle 1 of 1..."
    reg_dict = {
        'acc_len': 16384,
        'fft_shift': -1,
        'ant_sel1': 0,
        'ant_sel2': 1,
        'ant_sel3': 2,
        'ant_sel4': 3,
        'ant_sel5': 4,
        'ant_sel6': 5,
        'ant_sel7': 6,
        'ant_sel8': 7
    }

    init_registers_all(reg_dict, verbose=verbose)
    issue_reset_all(verbose=verbose)

    for i in range(n_roach):
        p = Process(target=snap_spec, args=(roachlist[i], xarrs[i], yarrs[i], q))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads
    for p in procs:
        p.join()

    # Print messages
    to_print = {}
    while q.empty() is False:
        rd = q.get()
        to_print[rd[0]] = rd[1]

    if verbose:
        for r in roachlist:
            print to_print[r]

    # Convert to python dict
    for ri in range(16):
        for ai in range(16):
            ant_idx   = ri * 16 + (ai + 1)
            sl_start = 4096 * ai
            sl_stop  = sl_start + 4096
            ants["%iA"%ant_idx] = xarrs[ri][sl_start:sl_stop]
            ants["%iB"%ant_idx] = yarrs[ri][sl_start:sl_stop]

    return ants



if __name__ == '__main__':
    #try:
    #    boffile = sys.argv[1]
    #    gain    = int(sys.argv[2])
    #except:
    #    print "Usage: adc16_initall.py boffile_name.bof gain"
    #    exit()

    #progdev_all(boffile, gain)

    boffile  = config.firmware
    gain     = 8
    reg_dict = {
        'acc_len': 16384,
        'fft_shift': -1,
        'ant_sel1': 0,
        'ant_sel2': 1,
        'ant_sel3': 2,
        'ant_sel4': 3,
        'ant_sel5': 4,
        'ant_sel6': 5,
        'ant_sel7': 6,
        'ant_sel8': 7
    }

    progdev_all(boffile, gain)
    init_registers_all(reg_dict)
    issue_reset_all()

