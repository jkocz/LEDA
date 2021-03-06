
from configtools import *
import socket
servername = socket.gethostname()

# These are mainly just to be logged in the headers
corr_clockfreq     = 196.608
corr_nfft          = 8192
corr_headersize    = 4096
corr_headerversion = "1.0"
corr_telescope     = "LWA-OVRO"
corr_receiver      = "DIPOLE"
corr_instrument    = "LEDA"
corr_data_order    = "REG_TILE_TRIANGULAR_2x2"
corr_nbit_in       = 4
ndim               = 2
npol               = 2
#tsamp              = 41.66667

site_stands_file = getenv_warn('SITE_STANDS_FILE',
                               "site_stands_ovro.txt")
leda_stands_file = getenv_warn('LEDA_STANDS_FILE',
                               "leda_stands_ovro64.txt")

headnodehost    = "ledagpu5"
webserverhost   = "ledagpu5"
serverhosts     = ["ledagpu5", "ledagpu6"]
roachhosts      = ['169.254.128.64', '169.254.128.65']
roachport       = 7147
#boffile         = 'l64x8_06022013.bof'
boffile         = 'l64c_06052013.bof'
src_ip_starts   = [145, 161]
src_port_starts = [4010, 4020]
fid_starts      = [0, 4]
# Digital gain registers set to 1x
adc_gain        = 1  # Multiplier 1-15
adc_gain_bits   = adc_gain | (adc_gain << 4) | (adc_gain << 8) | (adc_gain << 12)
adc_gain_reg    = 0x2a
roach_registers = {adc_gain_reg: adc_gain_bits}
#gain_setting = 0x8888
#roach_registers = {gain_reg: gain_setting}
#roach_registers = {}

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
capture_headerpaths = [os.path.join(headerpath,"header64%s.txt"%x) \
	                       for x in ['a','b']]

if servername == serverhosts[0]:
	capture_ips         = ["192.168.40.5", "192.168.40.5"]
	capture_ports       = [4015, 4016]
	#subbands            = [1, 2]
	#capture_ips         = ["192.168.40.6", "192.168.40.5"]
	#capture_ports       = [4018, 4015]
	subbands            = [0, 1]
elif servername == serverhosts[1]:
	capture_ips         = ["192.168.40.6", "192.168.40.6"]
	capture_ports       = [4017, 4018]
	#subbands            = [3, 0]
	#capture_ips         = ["192.168.40.5", "192.168.40.6"]
	#capture_ports       = [4016, 4017]
	subbands            = [2, 3]
elif servername not in [headnodehost, webserverhost]:
	#raise NameError("This server (%s) is not in the config file" % servername)
	print "WARNING: This server (%s) is not recognised in the config file" % servername
	
capture_ninputs     = [8] * nstream
capture_controlports = [12340,12341]
capture_cores       = [1, 9]

unpack_bufkeys      = ["aada", "bada"]
unpack_logfiles     = [os.path.join(logpath,"unpack."+bufkey) \
	                       for bufkey in unpack_bufkeys]
unpack_path         = os.path.join(getenv_warn('LEDA_DADA_DIR',
                                               "/home/leda/software/psrdada/leda/src"),
                                   "leda_dbupdb_paper")
unpack_cores        = [2, 10]

xengine_bufkeys     = ["cada", "fada"]
xengine_logfiles    = [os.path.join(logpath,"dbgpu."+bufkey) \
	                       for bufkey in xengine_bufkeys]
## TODO: This is the older leda_dbgpu code
#xengine_path        = "/home/leda/software/leda_ipp/leda_dbgpu"
xengine_path        = os.path.join(getenv_warn('LEDA_XENGINE_DIR',
                                               "/home/leda/LEDA/xengine"),
                                   "leda_dbxgpu")
xengine_gpus        = [0, 1]
xengine_navg        = 25
xengine_cores       = [3, 11]
xengine_tp_ncycles  = 100

disk_logfiles       = [os.path.join(logpath,"dbdisk."+bufkey) \
	                       for bufkey in xengine_bufkeys]
disk_path           = os.path.join(getenv_warn('PSRDADA_DIR',
                                               "/home/leda/software/psrdada/src"),
                                   "dada_dbdisk")
#disk_outpaths       = ["/data1/one", "/data1/two"]
disk_outpaths       = ["/data1/one", "/data2/one"]
disk_cores          = [4, 12]
