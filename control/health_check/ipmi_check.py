#!/usr/bin/env python
""" 
ping_all.py

Pings all hosts in /etc/hosts, and reports which ones do not respond. 
"""

import os
import re
import subprocess
from threading import Thread
from Queue import Queue
from optparse import OptionParser

from ping_all import read_hosts

def impier(i, q):
    """ Worker thread that issues IPMI command 
    
    Arguments:
    i (IP address or hostname)
    q (queue)
    """
    while True:
    	hostname = q.get()
    	sp = subprocess.Popen(["ipmitool", "-H", "%s"%hostname, "-U", "ADMIN", "-P", "ADMIN", 
                               "power", "status"], stdout = subprocess.PIPE)
        out, err = sp.communicate()
        print "%s: %s"%(hostname, out.strip())
        #if ret == 0:
        #	# print "%s: is alive" % ip
        #    pass
    	#else:
        #	print "%s: did not respond"%hostname
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
