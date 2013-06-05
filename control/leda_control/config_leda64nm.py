
import sys

servername = sys.argv[1]

logpath = "/home/leda/logs"

ninput = 64
nchan  = 300
ntime  = 8192
bufsize = ninput*nchan*ntime
upsize  = bufsize * 2
outsize = reg_tile_triangular_size(ninput, nchan)

dadapath = "/home/leda/software/psrdada/src"
bufkeys  = ["dada", "adda", "aeda", "eada",
			"fada", "afda", "cada", "acda",
			"abda", "aada", "bcda", "bada"]
bufsizes = [bufsize]*4 + [outsize]*4 + [upsize]*4
bufcores = [1, 1, 9, 9,
			9, 1, 1, 9,
			1, 1, 9, 9]

# -----------------------
# Parameters for ledagpu4
# -----------------------
capture_bufkeys     = ["dada", "adda", "eada", "aeda"]
capture_logfiles    = [os.path.join(logpath,"udpdb."+bufkey) for bufkey in capture_bufkeys]
capture_path        = "/home/leda/software/psrdada/leda/src/leda_udpdb_thread"
headerpath          = "/home/leda/roach_scripts/"
capture_headerpaths = [os.path.join(headerpath,"header64%s.txt"%x) for x in ['a','b','c','d']]
if servername == "ledagpu3":
	capture_ips         = ["192.168.0.81", "192.168.0.97", "192.168.0.113", "192.168.0.129"]
	capture_ports       = [4005, 4006, 4008, 4007]
elif servername == "ledagpu4":
	capture_ips         = ["192.168.0.17", "192.168.0.65", "192.168.0.49", "192.168.0.33"]
	capture_ports       = [4001, 4004, 4003, 4002]
else:
	print "Unknown server", servername
	sys.exit(-1)
capture_ninputs     = [8] * 4
capture_controlports = [12340,12341,12342,12343]
capture_cores       = [1, 2, 15, 9]

unpack_bufkeys      = ["aada", "abda", "bada", "bcda"]
unpack_logfiles     = [os.path.join(logpath,"unpack."+bufkey) for bufkey in unpack_bufkeys]
unpack_path         = "/home/leda/software/psrdada/leda/src/leda_dbupdb_paper"
unpack_cores        = [3, 4, 10, 11]

xengine_bufkeys     = ["cada", "afda", "fada", "acda"]
xengine_logfiles    = [os.path.join(logpath,"dbgpu."+bufkey) for bufkey in xengine_bufkeys]
## TODO: This is the older leda_dbgpu code
#xengine_path        = "/home/leda/software/leda_ipp/leda_dbgpu"
xengine_path        = "/home/leda/LEDA/xengine/leda_dbxgpu"
xengine_gpus        = [0, 1, 2, 3]
xengine_navg        = 25
xengine_cores       = [5, 6, 12, 13]
xengine_tp_ncycles  = 100

disk_logfiles       = [os.path.join(logpath,"dbdisk."+bufkey) for bufkey in xengine_bufkeys]
disk_path           = "/home/leda/software/psrdada/src/dada_dbdisk"
disk_outpaths       = ["/data1/one", "/data2/two", "/data2/one", "/data1/two"]
disk_cores          = [7, 7, 14, 14]
