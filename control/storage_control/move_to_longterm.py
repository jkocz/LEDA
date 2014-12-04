#!/usr/bin/env python
"""
move_to_longterm.py
-------------------

Move data to longterm storage
"""

import os
import sys
from datetime import datetime
from storage import *

def bash_to_longterm(filestamp_start, bashfile_out, config=nfs_config):
    """ Create a bash script to move data from /storage to /longterm

    You need to then manually run this script on the storage server.
    Easiest way: copy it over to /nfs/ledastorage and then run on server.
    """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    fileroot_longterm = config["longterm"]
    filestamp = filestamp_start

    to_move = []
    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            cdir_offsite = os.path.join(fileroot_longterm, host, sdir)
            filelist = os.listdir(cdir)

            for fname in filelist:
                if fname.startswith(filestamp):
                    to_move.append((host, sdir, fname))
            print host, sdir, len(to_move)

    # Write to file
    bfile = open(bashfile_out, 'w')
    cfile = open('create_dirs.sh', 'r')
    for line in cfile.readlines():
        bfile.write(line)

    ii = 0
    for (host, sdir, fname) in to_move:
        ii += 1
        eline = "echo \"(%i of %i) Moving %s -> /longterm\"  "%(ii, len(to_move), fname)
        cur_path = os.path.join(config["zfs_root"], host, sdir, fname)
        new_path = os.path.join(config["zfs_longterm"], host, sdir, fname)
        line = "mv %s %s"%(cur_path, new_path)
        bfile.write(eline + "\n")
        bfile.write(line + "\n")
    bfile.close()

def ssh_zfs(cmd, server=storage_config.hostname):
    """ Run an ssh command on the ZFS server """
    os.system('ssh %s %s' % (server, cmd))

def scp_zfs(filename, dest_dir='/tmp', server=storage_config.hostname):
    """ SCP a (small_ file over to the /tmp directory """
    dp = os.path.join(dest_dir, filename)
    scp_cmd =  'scp %s %s:%s' % (filename, server, dp)
    print scp_cmd
    os.system(scp_cmd)

def exec_bash_zfs(bashfile):
    """
    Run bash file on ZFS server via ssh / scp
    """
    scp_zfs(bashfile)
    #ssh_zfs('chmod a+x /tmp/%s' % bashfile)
    ssh_zfs('bash /tmp/%s' % bashfile)

if __name__ == '__main__':
    try:
        date_to_move = sys.argv[1]
    except:
        print "Usage: ./move_to_longterm.py <date YYYY-MM-DD>"
        exit()

    bashfile_out    = 'move_to_longterm.sh'

    bash_to_longterm(date_to_move, bashfile_out)

    t1 = datetime.now()
    exec_bash_zfs(bashfile_out)

    tt = datetime.now() - t1
    print "Elapsed time: %s" % tt
