#!/usr/bin/env python
""" 
ipmi_check.py

Looks for IPMI hosts in /etc/hosts, and checks the power status via IPMI
"""

import os
import re
import subprocess
from threading import Thread
from Queue import Queue
from optparse import OptionParser

from ping_check import read_hosts

def impier(i, q):
    """ Worker thread that issues IPMI command 
    
    Arguments:
    i (int) Thread ID
    q (queue) Queue ID
    """
    while True:
        hostname = q.get()
        sp = subprocess.Popen(["ipmitool", "-H", "%s"%hostname, "-U", "ADMIN", "-P", "ADMIN", 
                               "power", "status"], stdout = subprocess.PIPE)
        out, err = sp.communicate()
        print "%s: %s"%(hostname, out.strip())
        q.task_done()

if __name__ == '__main__':
    hosts = read_hosts()
    ipmis = []
    for host in hosts:
      if host[1].endswith('ipmi'):
        ipmis.append(host[1])
    #print ipmis
    
    impis = [ipmis[0]]
    print "Running IPMI status check on all IPMI entries in /etc/hosts"
    print "%i IPMI entries in /etc/hosts"%len(ipmis)
    
    #Spawn thread pool
    num_threads = 8
    queue = Queue()
    for i in range(num_threads):
    
        worker = Thread(target=impier, args=(i, queue))
        worker.setDaemon(True)
        worker.start()
    #Place work in queue
    for ipmi in ipmis:
        queue.put(ipmi)
    #Wait until worker threads are done to exit    
    queue.join()
    
    print "Done."
