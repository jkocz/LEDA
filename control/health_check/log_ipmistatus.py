#!/usr/bin/env python

"""
IPMI power status check for all IPMI hosts listed in /etc/hosts
Prints a single line containing a timestamp and a series of tab-separated values

E.g., 2014-11-19T03:22:28     41960.640602    ON      ON      ON ...
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

def query_ipmi_power(hostname):
    sp = subprocess.Popen(["ipmitool", "-H", "%s"%hostname,
                           "-U", "ADMIN", "-P", "ADMIN", 
                           "power", "status"],
                          stdout = subprocess.PIPE)
    out, err = sp.communicate()
    out = out.strip()
    if out == "Chassis Power is on":
        return 'ON'
    elif out == "Chassis Power is off":
        return 'OFF'
    else:
        return 'ERROR'

if __name__ == "__main__":
    
    ips_hosts = read_hosts()
    ips_hosts = [h for h in ips_hosts if h[1].endswith('ipmi')]
    
    async = AsyncCaller()
    for ip, host in ips_hosts:
        async(query_ipmi_power)(host)
    statuses = async.wait()
            
    utc = datetime.datetime.utcnow()
    utc_str = utc.strftime("%Y-%m-%dT%H:%M:%S")
    dublin_jd = float(ephem.Date(utc))
    
    """
    print '#' + '\t'.join(['UTC',
                           'DUBLIN_JD',
                           'IPMI_PWR_STATES'])
    """
    print '\t'.join([utc_str,
                     '%.6f' % dublin_jd,
                     '\t'.join(statuses)])
    
