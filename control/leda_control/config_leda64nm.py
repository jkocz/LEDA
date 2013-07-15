
from configtools import *
import socket
servername = socket.gethostname()

# These are mainly just to be logged in the headers
corr_clockfreq     = 196.608
corr_nfft          = 8192
corr_headersize    = 4096
corr_headerversion = "1.0"
corr_telescope     = "LWA1"
corr_receiver      = "DIPOLE"
corr_instrument    = "LEDA"
corr_data_order    = "REG_TILE_TRIANGULAR_2x2"
corr_nbit_in       = 4
ndim               = 2
npol               = 2
#tsamp              = 41.66667

stands_file = getenv_warn('LEDA_STANDS_FILE',
                          "stands_leda64ovro_2013-07-15.txt")

headnodehost    = "ledagpu4"
serverhosts     = ["ledagpu3", "ledagpu4"]
roachhosts      = ['169.254.128.14', '169.254.128.13']
roachport       = 7147
boffile         = 'l64c_06052013.bof'
src_ip_starts   = [145, 149]
src_port_starts = [4010, 4014]
fid_starts      = [0, 4]
# Digital gain registers set to 1x
adc_gain        = 8  # Multiplier 1-15
adc_gain_bits   = adc_gain | (adc_gain << 4) | (adc_gain << 8) | (adc_gain << 12)
adc_gain_reg    = 0x2a
roach_registers = {adc_gain_reg: adc_gain_bits}

logpath = getenv_warn('LEDA_LOG_DIR', "/home/leda/logs")

ninput    = 64
nchan     = 600
ntime     = 8192
nstream   = 2
lowfreq   = 30.0
#bandwidth = 14.4
bufsize = ninput*nchan*ntime
upsize  = bufsize * 2
outsize = reg_tile_triangular_size(ninput, nchan)

dadapath = getenv_warn('PSRDADA_DIR', "/home/leda/software/psrdada/src")
bufkeys  = ["dada", "eada", # Captured
			"aada", "bada", # Unpacked
			"cada", "fada"] # Correlated
bufsizes = [bufsize]*nstream + [upsize]*nstream + [outsize]*nstream
bufcores = [1, 9,
			1, 9,
			1, 9]

capture_bufkeys     = ["dada", "eada"]
capture_logfiles    = [os.path.join(logpath,"udpdb."+bufkey) \
	                       for bufkey in capture_bufkeys]
capture_path        = os.path.join(getenv_warn('LEDA_DADA_DIR',
                                               "/home/leda/software/psrdada/leda/src"),
                                   "leda_udpdb_thread")
headerpath          = getenv_warn('LEDA_HEADER_DIR', "/home/leda/roach_scripts/")
capture_headerpaths = [os.path.join(headerpath,"header64%s.txt"%x) for x in ['a','b']]
if servername == "ledagpu3":
	capture_ips         = ["192.168.0.81", "192.168.0.113"]
	capture_ports       = [4005, 4008]
	subbands            = [3, 0]
	#centerfreqs         = [66.0, 80.4]
	#bandwidths          = [bandwidth, bandwidth]
elif servername == "ledagpu4":
	#capture_ips         = ["192.168.0.17", "192.168.0.49"]
	capture_ips         = ["192.168.0.17", "192.168.0.33"]
	capture_ports       = [4001, 4003]
	subbands            = [1, 2]
	#centerfreqs         = [37.2, 51.6]
	#bandwidths          = [bandwidth, bandwidth]
else:
	raise NameError("This server (%s) is not in the config file" % servername)

capture_ninputs     = [8] * nstream
capture_controlports = [12340,12341]
capture_cores       = [1, 10]

unpack_bufkeys      = ["aada", "bada"]
unpack_logfiles     = [os.path.join(logpath,"unpack."+bufkey) \
	                       for bufkey in unpack_bufkeys]
unpack_path         = os.path.join(getenv_warn('LEDA_DADA_DIR',
                                               "/home/leda/software/psrdada/leda/src"),
                                   "leda_dbupdb_paper")
unpack_cores        = [3, 11]

xengine_bufkeys     = ["cada", "fada"]
xengine_logfiles    = [os.path.join(logpath,"dbgpu."+bufkey) \
	                       for bufkey in xengine_bufkeys]
xengine_path        = os.path.join(getenv_warn('LEDA_XENGINE_DIR',
                                               "/home/leda/LEDA/xengine"),
                                   "leda_dbxgpu")
xengine_gpus        = [0, 2]
xengine_navg        = 25
xengine_cores       = [5, 12]
xengine_tp_ncycles  = 100

disk_logfiles       = [os.path.join(logpath,"dbdisk."+bufkey) \
	                       for bufkey in xengine_bufkeys]
disk_path           = os.path.join(getenv_warn('PSRDADA_DIR',
                                               "/home/leda/software/psrdada/src"),
                                   "dada_dbdisk")
disk_outpaths       = ["/data1/one", "/data2/one"]
disk_cores          = [7, 14]
