"""
roach_config.py
---------------

Configuration file for ROACH boards. This file sets up
the shared registers and the BRAM values required. So that
each board can have its own config, three main python
dictionaries are setup:

reg_dicts    = {
    'rofl1' : {...},
    'rofl2' : {...},
    ...}

core_configs = {...}
bram_dicts   = {...}

"""

import struct
import numpy

from leda_config import arp_config as arp

boffile = 'l512_actual_4t.py'   # Default firmware
gain    = 8                     # Default gain value

bofdict = {
    'rofl1'  : 'l512_actual_4t.bof',
    'rofl2'  : 'l512_actual_4t.bof',
    'rofl3'  : 'l512_actual_4t.bof',
    'rofl4'  : 'l512_actual_4t.bof',
    'rofl5'  : 'l512_actual_4t.bof',
    'rofl6'  : 'l512_actual_4t.bof',
    'rofl7'  : 'l512_p13_4t.bof',
    'rofl8'  : 'l512_actual_4t.bof',
    'rofl9'  : 'l512_actual_4t.bof',
    'rofl10' : 'l512_actual_4t.bof',
    'rofl11' : 'l512_actual_4t.bof',
    'rofl12' : 'l512_actual_4t.bof',
    'rofl13' : 'l512_actual_4t.bof',
    'rofl14' : 'l512_actual_4t.bof',
    'rofl15' : 'l512_actual_4t.bof',
    'rofl16' : 'l512_actual_4t.bof',
}

# SETUP QUANTIZATION GAIN SETTINGS
odata = numpy.ones(4096, 'l') * (1500 << 7) * 0.7
cstr = struct.pack('>4096l', *odata)

# Main BRAM dictionary for quant gains
bram_dict = {
    'fft_f1_coeff_eq0_coeffs' : cstr,
    'fft_f1_coeff_eq1_coeffs' : cstr,
    'fft_f1_coeff_eq2_coeffs' : cstr,
    'fft_f1_coeff_eq3_coeffs' : cstr,
    'fft_f1_coeff_eq4_coeffs' : cstr,
    'fft_f1_coeff_eq5_coeffs' : cstr,
    'fft_f1_coeff_eq6_coeffs' : cstr,
    'fft_f1_coeff_eq7_coeffs' : cstr,
    'fft_f2_coeff_eq0_coeffs' : cstr,
    'fft_f2_coeff_eq1_coeffs' : cstr,
    'fft_f2_coeff_eq2_coeffs' : cstr,
    'fft_f2_coeff_eq3_coeffs' : cstr,
    'fft_f2_coeff_eq4_coeffs' : cstr,
    'fft_f2_coeff_eq5_coeffs' : cstr,
    'fft_f2_coeff_eq6_coeffs' : cstr,
    'fft_f2_coeff_eq7_coeffs' : cstr,
    'fft_f3_coeff_eq0_coeffs' : cstr,
    'fft_f3_coeff_eq1_coeffs' : cstr,
    'fft_f3_coeff_eq2_coeffs' : cstr,
    'fft_f3_coeff_eq3_coeffs' : cstr,
    'fft_f3_coeff_eq4_coeffs' : cstr,
    'fft_f3_coeff_eq5_coeffs' : cstr,
    'fft_f3_coeff_eq6_coeffs' : cstr,
    'fft_f3_coeff_eq7_coeffs' : cstr,
    'fft_f4_coeff_eq0_coeffs' : cstr,
    'fft_f4_coeff_eq1_coeffs' : cstr,
    'fft_f4_coeff_eq2_coeffs' : cstr,
    'fft_f4_coeff_eq3_coeffs' : cstr,
    'fft_f4_coeff_eq4_coeffs' : cstr,
    'fft_f4_coeff_eq5_coeffs' : cstr,
    'fft_f4_coeff_eq6_coeffs' : cstr,
    'fft_f4_coeff_eq7_coeffs' : cstr
}

# Register dictionary, mainly 10GbE setup
# But also FFT shift
reg_dict = {
    'tenge_port1'    : arp.dest_port0,
    'tenge_port2'    : arp.dest_port1,
    'tenge_ips_ip1'  : arp.dest_ip0,
    'tenge_ips_ip2'  : arp.dest_ip1,
    'tenge_ips_ip3'  : arp.dest_ip2,
    'tenge_ips_ip4'  : arp.dest_ip3,
    'tenge_ips_ip5'  : arp.dest_ip4,
    'tenge_ips_ip6'  : arp.dest_ip5,
    'tenge_ips_ip7'  : arp.dest_ip6,
    'tenge_ips_ip8'  : arp.dest_ip7,
    'tenge_ips_ip9'  : arp.dest_ip8,
    'tenge_ips_ip10' : arp.dest_ip9,
    'tenge_ips_ip11' : arp.dest_ip10,
    'tenge_ips_ip12' : arp.dest_ip0,
    'tenge_ips_ip13' : arp.dest_ip1,
    'tenge_ips_ip14' : arp.dest_ip2,
    'tenge_ips_ip15' : arp.dest_ip3,
    'tenge_ips_ip16' : arp.dest_ip4,
    'tenge_ips_ip17' : arp.dest_ip5,
    'tenge_ips_ip18' : arp.dest_ip6,
    'tenge_ips_ip19' : arp.dest_ip7,
    'tenge_ips_ip20' : arp.dest_ip8,
    'tenge_ips_ip21' : arp.dest_ip9,
    'tenge_ips_ip22' : arp.dest_ip10,
    'tenge_header_fid'  : 0,
    'tenge_start_count' : 1246,
    'tenge_stop_count'  : 1464,
    'tenge_high_ch'     : 109,
    'fft_f1_fft_shift'  : 65535,
    'fft_f2_fft_shift'  : 65535,
    'fft_f3_fft_shift'  : 65535,
    'fft_f4_fft_shift'  : 65535,
}


# LOAD ARP CONFIG FROM ARP_CONFIG FILE
arp_table   = arp.arp_table
dest_port0  = arp.dest_port0
dest_port1  = arp.dest_port1
src_port0   = arp.src_port0
src_port1   = arp.src_port1
src_ip_base = arp.src_ip_base
mac_base0   = arp.mac_base0


# Customize configs for each ROACH board
reg_dicts    = {}
core_configs = {}
bram_dicts   = {}

for ii in range(1, 17):
    reg_dict['tenge_header_fid'] = ii

    reg_dicts["rofl%i" % ii] = reg_dict.copy()
    bram_dicts["rofl%i" % ii] = bram_dict.copy()

    core_config = [
        ('tenge_gbe00', mac_base0 + src_ip_base + (ii * 2),     src_ip_base + (ii * 2),     src_port0, arp_table),
        ('tenge_gbe01', mac_base0 + src_ip_base + (ii * 2) + 1, src_ip_base + (ii * 2) + 1, src_port1, arp_table)
    ]
    core_configs["rofl%i" % ii] = core_config