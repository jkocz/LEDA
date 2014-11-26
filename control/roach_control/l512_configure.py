#!/usr/bin/env python
"""
l512_configure.py
-----------------

Configure ROACH f-engines @ LEDA OVRO
"""


from multiprocessing import Process, JoinableQueue
import subprocess
import time, sys, os
from corr import katcp_wrapper
import corr, time, numpy, struct, sys

from leda_config import arp_config as arp
from leda_config import roach_config


######################
## FUNCTION DEFS
#####################

def init_f_engine(roach, q, reg_dict, bram_dict, core_config):
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
        for cc in core_config:
            fpga.config_10gbe_core(cc[0], cc[1], cc[2], cc[3], cc[4])

        time.sleep(2)

        for key in reg_dict:
            try:
                fpga.write_int(key, reg_dict[key])
            except RuntimeError:
                q_output = (roach , "WRITE_INT ERROR: cannot initialize %s"%roach)
                allsystemsgo = False

        for key in bram_dict:
            try:
                fpga.write(key, bram_dict[key])
            except RuntimeError:
                q_output = (roach , "WRITE BRAM ERROR: cannot initialize %s"%roach)
                allsystemsgo = False

    if allsystemsgo:
        fpga.write_int('tenge_enable', 0)
        fpga.write_int('adc_rst', 3)
        q_output = (roach , "%s F-engine initialized."%roach)

    q.put(q_output)
    fpga.stop()
    return

def init_f_engine_all(reg_dicts, bram_dicts, core_configs):
    """ Initialize all roaches via register:value dictionary """

    print "Please wait, configuring F-engines..."

    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for k in reg_dicts.keys():
        p = Process(target=init_f_engine, args=(k, q, reg_dicts[k], bram_dicts[k], core_configs[k]))
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

    for k in reg_dicts.keys():
        print to_print[k]

    print "OK"

def read_10gbe_config(fpga):
    """ Read 10GbE core config from FPGA

    TODO : READ DESTINATION IPS
    """

    config = {}
    arp_config = fpga.get_10gbe_core_details('tenge_gbe00')
    arp_tb = [arp.int_to_mac(ss) for ss in  arp_config["arp"]]
    ip = arp.int_to_ip(arp_config["my_ip"])
    mac = arp.int_to_mac(arp_config["mymac"])
    config["gbe0_ip"]  = ip
    config["gbe0_mac"] = mac
    config["gbe0_arp"] = arp_tb
    config["gbe0_port_src"] = arp_config["fabric_port"]
    config["gbe0_port_dest"] = fpga.read_int("tenge_port1")
    config["gbe0_fid"] = fpga.read_int('tenge_header_fid')

    arp_config = fpga.get_10gbe_core_details('tenge_gbe01')
    arp_tb = [arp.int_to_mac(ss) for ss in  arp_config["arp"]]
    ip = arp.int_to_ip(arp_config["my_ip"])
    mac = arp.int_to_mac(arp_config["mymac"])
    config["gbe1_ip"]  = ip
    config["gbe1_mac"] = mac
    config["gbe1_arp"] = arp_tb
    config["gbe1_port_src"] = arp_config["fabric_port"]
    config["gbe1_port_dest"] = fpga.read_int("tenge_port2")
    config["gbe1_fid"] = fpga.read_int('tenge_header_fid')

    for ii in range(22):
        reg = 'tenge_ips_ip%i'% (ii + 1)
        config["gbe0_ip_dest%02i" % (ii + 1)] = arp.int_to_ip(fpga.read_int(reg))
        config["gbe1_ip_dest%02i" % (ii + 1)] = arp.int_to_ip(fpga.read_int(reg))

    return config

def print_10gbe_config(fpga):
    """ Read and print 10GbE core config from FPGA """
    cc = read_10gbe_config(fpga)
    print "\n%s: 10GbE core configuration " % fpga.host
    print "------------------------------------------------------"
    print "           | %18s | %18s |" % ("GBE00", "GBE01")
    print "%10s | %18s | %18s |" % ("MAC", cc["gbe0_mac"], cc["gbe1_mac"])
    print "%10s | %18s | %18s |" % ("IP", cc["gbe0_ip"], cc["gbe1_ip"])
    print "%10s | %18s | %18s |" % ("PORT SRC", cc["gbe0_port_src"], cc["gbe1_port_src"])
    print "%10s | %18s | %18s |" % ("PORT DEST", cc["gbe0_port_dest"], cc["gbe1_port_dest"])
    print "%10s | %18s | %18s |" % ("FID", cc["gbe0_fid"], cc["gbe1_fid"])
    print "------------------------------------------------------"

######################
## START OF MAIN
######################

if __name__ == "__main__":

    roach_array = roach_config.roach_list

    print_arp = False		# Print ARP config (debug only)
    print_ips = True		# Print destination IPs

    reg_dicts    = roach_config.reg_dicts
    core_configs = roach_config.core_configs
    bram_dicts   = roach_config.bram_dicts

    init_f_engine_all(reg_dicts, bram_dicts, core_configs)

    # Check that IPs are setup correctly
    # This is done in serial for improved sanity
    fpga_list = [corr.katcp_wrapper.FpgaClient('rofl%i' % ii) for ii in range(1,17)]
    time.sleep(1)

    for fpga in fpga_list:
        cc = read_10gbe_config(fpga)
        print_10gbe_config(fpga)

        # Explicitly check every entry in ARP table matches arp_config
        for jj in range(len(cc["gbe0_arp"])):
            try:
                assert cc["gbe0_arp"][jj] == arp.arp_table_str[jj]
                assert cc["gbe1_arp"][jj] == arp.arp_table_str[jj]
            except:
                print "ERROR: ARP TABLE IS NOT CORRECT ON %s" % fpga.host
                break
        for jj in range(22):
            try:
                dest_ip = arp.dest_ips_str[jj]
                assert cc["gbe0_ip_dest%02i" % (jj + 1)] == dest_ip
                assert cc["gbe1_ip_dest%02i" % (jj + 1)] == dest_ip
            except:
                print cc["gbe0_ip_dest%02i" % (jj + 1)], dest_ip
                print "ERROR: DEST IPS ARE NOT CORRECT ON %s" % fpga.host
                break

        fpga.stop()

    if print_arp:
        print "\nARP table:"
        ii = 0
        for aa in arp.arp_table_str:
            print "%03i | %s" % (ii, aa)
            ii += 1
    if print_ips:
        print "\nDestination IP addresses"
        print "------------------------"
        ii = 0
        for dd in arp.dest_ips_str:
           print "  %02i |  %s  |" % (ii, dd)
           ii += 1
        print "------------------------"

    print "\n Done. \n"
