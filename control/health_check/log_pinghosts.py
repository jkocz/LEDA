#!/usr/bin/env python

"""
Ping response check for all hosts listed in /etc/hosts
Prints a single line containing a timestamp and a series of tab-separated values

E.g., 2014-11-19T03:01:41     41960.626169    hp48port,ledaovro6-ipmi
"""

import re
import subprocess
import datetime
import ephem # For Julian date
from async import AsyncCaller

def read_hosts():
    """ Parse contents of system hosts file into list of (ip, hostname) pairs """
    with open('/etc/hosts', 'r') as hostfile:
        hostlines = hostfile.readlines()
    hosts = []
    for hostline in hostlines:
        hostline = re.sub('\t', ' ', hostline).strip('\n').strip()
        if hostline == '':
            continue
        if not ':' in hostline: # Skip IPv6 entries
            host_cols = hostline.split()
            if not host_cols[0].startswith('#'):
                hosts.append((host_cols[0], host_cols[1]))
    return hosts

def ping(ip):
    ret = subprocess.call("ping -c 1 %s" % ip,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)
    if ret == 0: # Host responded
        return True
    else: # Host didn't respond
        return False

if __name__ == "__main__":
    
    ips_hosts = read_hosts()
    #print ips_hosts
    async = AsyncCaller()
    for ip, host in ips_hosts:
        async(ping)(ip)
    responses = async.wait()
    down_hosts = []
    for (ip, hostname), response in zip(ips_hosts, responses):
        if not response:
            down_hosts.append(hostname)
            
    utc = datetime.datetime.utcnow()
    utc_str = utc.strftime("%Y-%m-%dT%H:%M:%S")
    dublin_jd = float(ephem.Date(utc))
    """
    print '#' + '\t'.join(['UTC',
                           'DUBLIN_JD',
                           'DOWN_HOSTS'])
    """
    print '\t'.join([utc_str,
                     '%.6f' % dublin_jd,
                     ','.join(down_hosts)])
