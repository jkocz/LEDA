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

def pinger(i, q):
    """ Worker thread that pings given IP 
    
    Arguments:
    i (int) Thread ID
    q (queue) Queue ID
    """
    while True:
    	ip, hostname = q.get()
    	#print "Thread %s: Pinging %s" % (i, ip)
    	ret = subprocess.call("ping -c 1 %s" % ip,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)
    	if ret == 0:
        	# print "%s: is alive" % ip
            pass
    	else:
        	print "%s: did not respond" % hostname
    	q.task_done()

def read_hosts():
    """ Read contents of hosts file """
    hostfile = open('/etc/hosts')
    hostlines = hostfile.readlines()
    hostfile.close()
    
    hosts = []
    for host in hostlines:
        try:
            host = re.sub('\t', ' ', host).strip('\n').strip()
            
            if not ':' in host:
                host = host.split()
                if not host[0].startswith('#'):
                    hosts.append((host[0], host[1]))
        except:
            pass
    return hosts

if __name__ == '__main__':

        
    
    # Get IP addresses from hosts file      
    ips = read_hosts()
    print "Pinging all hosts in /etc/hosts"
    print "%i hosts in /etc/hosts"%len(ips)
    
    #Spawn thread pool
    num_threads = 8
    queue = Queue()
    for i in range(num_threads):
    
        worker = Thread(target=pinger, args=(i, queue))
        worker.setDaemon(True)
        worker.start()
    #Place work in queue
    for ip in ips:
        queue.put(ip)
    #Wait until worker threads are done to exit    
    queue.join()
    
    print "Done."
