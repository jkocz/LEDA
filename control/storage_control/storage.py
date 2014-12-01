"""
storage.py
----------

Helper utilities for controlling data on the storage server.
"""

import sys, os, shutil

from leda_config import storage_config

nfs_config = storage_config.nfs_config

def search_for(filestamp_start, config=nfs_config):
    """ Search ZFS for a given starting string, lists number of files

    This searches the 11 /storage/ledaovro[x]/data[y]/ directories for
    files that start with filestamp_start.
    """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    filestamp = filestamp_start

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            print cdir
            filelist = os.listdir(cdir)
            to_find = []
            for fname in filelist:
                if fname.startswith(filestamp):
                    to_find.append(fname)
            print host, sdir, len(to_find)

def search_and_destroy(filestamp_start, do_del=False, verbose=False, config=nfs_config):
    """ Search ZFS for a given starting string and delete matching files

    This searches the 11 /storage/ledaovro[x]/data[y]/ directories for
    files that start with filestamp_start and removes them.
    """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    filestamp = filestamp_start

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            filelist = os.listdir(cdir)
            to_delete = []
            for fname in filelist:
                if fname.startswith(filestamp):
                    to_delete.append(fname)
            print host, sdir, len(to_delete)

            # Only run this if we are deleting files!
            if do_del:
                for fname in to_delete:
                    if verbose:
                        print "Deleting %s"%os.path.join(cdir, fname)
                    os.remove(os.path.join(cdir, fname))

def destroy_invalid(do_del=False, verbose=False, config=nfs_config):
    """ Remove all files that do not have the correct number of bytes """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            filelist = os.listdir(cdir)
            to_delete = []
            for fname in filelist:
                if fname.endswith('.dada'):
                    if os.path.getsize(os.path.join(cdir, fname)) != config["file_bytes"]:
                        to_delete.append(fname)

            print host, sdir, len(to_delete)

            # Only run this if we are deleting files!
            if do_del:
                for fname in to_delete:
                    if verbose:
                        print "Deleting %s"%os.path.join(cdir, fname)
                    try:
                        os.remove(os.path.join(cdir, fname))
                    except IOError:
                        print "Warning: could not delete %s"%os.path.join(cdir, fname)

def destroy_above_offset(filestamp_start, offset_max, do_del=False, verbose=False, config=nfs_config):
    """ Delete files above a certain offset. For when obs run too long """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    offset_max = int(offset_max)

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            filelist = os.listdir(cdir)
            to_delete = []
            for fname in filelist:
                if fname.endswith('.dada') and fname.startswith(filestamp_start):
                    offset_cur = int(fname.split(".")[0].split("_")[1])
                    if offset_cur > offset_max:
                        to_delete.append(fname)

            print host, sdir, len(to_delete)

            # Only run this if we are deleting files!
            if do_del:
                for fname in to_delete:
                    if verbose:
                        print "Deleting %s"%os.path.join(cdir, fname)
                    try:
                        os.remove(os.path.join(cdir, fname))
                    except IOError:
                        print "Warning: could not delete %s"%os.path.join(cdir, fname)

def destroy_below_offset(filestamp_start, offset_min, do_del=False, verbose=False, config=nfs_config):
    """ Delete files below a certain offset. For when obs started too early """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    offset_min = int(offset_min)

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            filelist = os.listdir(cdir)
            to_delete = []
            for fname in filelist:
                if fname.endswith('.dada') and fname.startswith(filestamp_start):
                    offset_cur = int(fname.split(".")[0].split("_")[1])
                    if offset_cur <= offset_min:
                        to_delete.append(fname)

            print host, sdir, len(to_delete)

            # Only run this if we are deleting files!
            if do_del:
                for fname in to_delete:
                    if verbose:
                        print "Deleting %s"%os.path.join(cdir, fname)
                    try:
                        os.remove(os.path.join(cdir, fname))
                    except IOError:
                        print "Warning: could not delete %s"%os.path.join(cdir, fname)


def move_to_offsite_nfs(filestamp_start, do_move=False, verbose=False, config=nfs_config):
    """ Move files from /storage0 to /offsite (via NFS -- slow!)"""
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    fileroot_offsite = config["offsite"]
    filestamp = filestamp_start

    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            cdir_offsite = os.path.join(fileroot_offsite, host, sdir)
            filelist = os.listdir(cdir)
            to_move = []
            for fname in filelist:
                if fname.startswith(filestamp):
                    to_move.append(fname)
            print host, sdir, len(to_move)

            # Only run this if we are moving files!
            for fname in to_move:
                if verbose:
                    print "mv %s %s"%(os.path.join(cdir, fname), os.path.join(cdir_offsite, fname))
                if do_move:
                    shutil.move(os.path.join(cdir, fname), os.path.join(cdir_offsite, fname))

def move_to_offsite_bash(filestamp_start, bashfile_out, config=nfs_config):
    """ Create a bash script to move data from /storage to /offsite

    You need to then manually run this script on the storage server.
    Easiest way: copy it over to /nfs/ledastorage and then run on server.
    """
    fileroot, hostnames, subdirs = config["fileroot"], config["hostnames"], config["subdirs"]
    fileroot_offsite = config["offsite"]
    filestamp = filestamp_start

    to_move = []
    for host in hostnames:
        for sdir in subdirs:
            # Set current directory based on name
            cdir = os.path.join(fileroot, host, sdir)
            cdir_offsite = os.path.join(fileroot_offsite, host, sdir)
            filelist = os.listdir(cdir)

            for fname in filelist:
                if fname.startswith(filestamp):
                    to_move.append((host, sdir, fname))
            print host, sdir, len(to_move)

    # Write to file
    bfile = open(bashfile_out, 'w')
    ii = 0
    for (host, sdir, fname) in to_move:
        ii += 1
        eline = "echo \"(%i of %i) Moving %s -> /offsite\"  "%(ii, len(to_move), fname)
        cur_path = os.path.join(config["zfs_root"], host, sdir, fname)
        new_path = os.path.join(config["zfs_offsite"], host, sdir, fname)
        line = "mv %s %s"%(cur_path, new_path)
        bfile.write(eline + "\n")
        bfile.write(line + "\n")
    bfile.close()

