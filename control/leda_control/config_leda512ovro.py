
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

site_stands_file = getenv_warn('SITE_STANDS_FILE',
                               "site_stands_ovro.txt")
leda_stands_file = getenv_warn('LEDA_STANDS_FILE',
                               "leda_stands_ovro512.txt")

site_lat = 37.240391
site_lon = -118.28247

headnodehost    = "ledaovro"
webserverhost   = "ledaovro"
serverhosts     = ["ledaovro%i" % (i+1) for i in xrange(11)]
#serverhosts     = ["ledaovro1"]
#serverhosts     = ["ledaovro2"]
roachhosts      = ["rofl%i" % (i+1) for i in xrange(16)]
#roachhosts      = ["rofl%i" % i for i in [1, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14]]
#roachhosts      = ["rofl%i" % i for i in [1, 2, 3, 4, 5, 6,  8, 9, 10, 11, 12, 13, 14, 15, 16]]
roachport       = 7147
boffile         = 'leda512_actual_1s.bof'#'l512_dev_20130717.bof'
nroach      = len(roachhosts)
fids        = [i for i in xrange(nroach)]
src_ips     = [["192.168.40.%i" % (50 + i*2),
                "192.168.40.%i" % (51 + i*2)] \
	               for i in xrange(nroach)]
src_ports   = [4000, 4001]
dest_ips    = ["192.168.40.%i" % (10 + i) for i in xrange(11)]
dest_ports  = [4015, 4016]
fft_first_chan = 1246
fft_last_chan  = 1464
fft_gain_coef  = 1500<<7#None
have_adcs   = True#False
use_progdev = False#True
# Digital gain registers set to 1x
adc_gain        = 1  # Multiplier 1-15
adc_gain_bits   = adc_gain | (adc_gain << 4) | (adc_gain << 8) | (adc_gain << 12)
adc_gain_reg    = 0x2a
roach_registers = {adc_gain_reg: adc_gain_bits}
fft_shift_mask  = 0xFFFF#None

logpath = getenv_warn('LEDA_LOG_DIR', "/home/leda/logs")

ninput    = 512
nchan     = 109
ntime     = 8000 # Note: Exactly 1/3 sec with 24.0kHz chans
nstream   = 2
lowfreq   = 30.0
baseband_noutchan = 3
bufsize = ninput*nchan*ntime
upsize  = bufsize * 2
outsize = reg_tile_triangular_size(ninput, nchan)
#beamoutsize = ntime*nchan*npol*2*4
beamoutsize = ntime*nchan*2*4
basebandoutsize = ntime*baseband_noutchan*ninput*1

visports = [3142 + i for i in xrange(nstream)]

dadapath = getenv_warn('PSRDADA_DIR', "/home/leda/software/psrdada/src")
bufkeys  = ["dada", "eada", # Captured
            "aada", "bada", # Unpacked
            "cada", "fada", # Correlated
            "abda", "ebda", # Beamformed
            "acda", "ecda"] # Basebanded
bufsizes = [bufsize]*nstream + [upsize]*nstream + [outsize]*nstream \
    + [beamoutsize]*nstream + [basebandoutsize]*nstream
bufcores = [1, 9,
            1, 9,
            1, 9,
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

if servername == headnodehost or servername == webserverhost:
	pass
elif servername in serverhosts:
	server_id = int(servername[len("ledaovro"):])-1
	capture_ip    = "192.168.40.%i" % (10 + server_id)
	capture_ips   = [capture_ip, capture_ip]
	#capture_ports = [4000 + 2*server_id-1, 4000 + 2*server_id-0]
	capture_ports = [4015, 4016]
	#subbands      = [server_id*2+0, server_id*2+1]
	if server_id % 2 == 0:
		subbands = [server_id, server_id+len(serverhosts)]
	else:
		subbands = [server_id+len(serverhosts), server_id]
else:
	#raise NameError("This server (%s) is not in the config file" % servername)
	print "WARNING: This server (%s) is not recognised in the config file" % servername
	
capture_ninputs     = [16] * nstream
capture_controlports = [12340,12341]
capture_cores       = [1, 9]

unpack_bufkeys      = ["aada", "bada"]
unpack_logfiles     = [os.path.join(logpath,"unpack."+bufkey) \
	                       for bufkey in unpack_bufkeys]
unpack_path         = os.path.join(getenv_warn('LEDA_DADA_DIR',
                                               "/home/leda/software/psrdada/leda/src"),
                                   "leda_dbupdb_512")
unpack_cores        = [2, 10]
unpack_ncores       = 1

xengine_bufkeys     = ["cada", "fada"]
xengine_logfiles    = [os.path.join(logpath,"dbgpu."+bufkey) \
	                       for bufkey in xengine_bufkeys]
## TODO: This is the older leda_dbgpu code
#xengine_path        = "/home/leda/software/leda_ipp/leda_dbgpu"
xengine_path        = os.path.join(getenv_warn('LEDA_XENGINE_DIR',
                                               "/home/leda/LEDA/xengine"),
                                   "leda_dbxgpu")
xengine_gpus        = [0, 1]
#xengine_navg        = 25
xengine_navg        = 3 # Exactly 1 second
xengine_cores       = [4, 12]
xengine_tp_ncycles  = 100

disk_logfiles       = [os.path.join(logpath,"dbdisk."+bufkey) \
	                       for bufkey in xengine_bufkeys]
disk_path           = os.path.join(getenv_warn('PSRDADA_DIR',
                                               "/home/leda/software/psrdada/src"),
                                   "dada_dbdisk")
#disk_outpaths       = ["/data1/one", "/data1/two"]
disk_outpaths       = ["/data1/one", "/data2/one"]
disk_cores          = [5, 13]

# TODO: This is crap, fix it (problem is that no other exe is used from this dir!)
post_path           = os.path.join(getenv_warn('LEDA_REPO_DADA_DIR',
                                               "/home/leda/software/LEDA/dada"),
                                   "leda_dbpost.py")
post_logfiles       = [os.path.join(logpath,"dbpost."+bufkey) \
	                       for bufkey in xengine_bufkeys]

beam_bufkeys        = ["abda", "ebda"]
beam_logfiles       = [os.path.join(logpath,"dbbeam."+bufkey) \
	                       for bufkey in beam_bufkeys]
beam_path           = os.path.join(getenv_warn('LEDA_XENGINE_DIR',
                                               "/home/leda/LEDA/xengine"),
                                   "leda_dbbeam_gpu")
                                   #"leda_dbbeam")
beam_gpus           = [0, 1]
beam_cores          = [4, 12]

baseband_bufkeys    = ["acda", "ecda"]
baseband_logfiles   = [os.path.join(logpath,"dbbaseband."+bufkey) \
	                       for bufkey in baseband_bufkeys]
baseband_path       = os.path.join(getenv_warn('LEDA_XENGINE_DIR',
                                               "/home/leda/LEDA/xengine"),
                                   "leda_dbbaseband")
baseband_cores      = [4, 12]
