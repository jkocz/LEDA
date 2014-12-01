#!/usr/bin/env python
# List observations and their sizes

from glob import glob
from os.path import basename, join

from leda_config.storage_config import nfs_config

NUM_BANDS = 22
FILE_SIZE = 1.0728 # Size of a single dada file

if __name__ == '__main__':

    print nfs_config["fileroot"]
    gg = glob(join(nfs_config["fileroot"],'ledaovro1/data1/one/????-??-??-*'))

    timestamps = [basename(filename).split('_')[0] for filename in gg]
    total = 0

    for t in sorted(set(timestamps)):
        num_files = timestamps.count(t)
        data_size = num_files * NUM_BANDS * FILE_SIZE
        print "%s\t% 6d GB\t(%d ints)" % (t, data_size, num_files)
        total += data_size
    print "Total: %.2f GB" % total
