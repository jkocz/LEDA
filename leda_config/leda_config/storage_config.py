"""
storage_config.py
-----------------

Configuration for storage server (hostname, IP, etc).
"""


hostname = 'ledastorage'

# NFS configuration on the headnode
nfs_config = {
              "fileroot"  : "/nfs/ledastorage",
              "hostnames" : ["ledaovro%i"%ii for ii in range(1,12)],
              "subdirs"   : ["data1/one", "data1/two"],
              "offsite"   : "/nfs/ledaoffsite",
              "longterm"  : "/nfs/longterm",
              "zfs_root"  : "/storage0/zfs_storage0",
              "zfs_offsite" : "/offsite/zfs_offsite",
              "zfs_longterm" : "/longterm/zfs_longterm",
              "file_bytes" : 1151881216
              }

