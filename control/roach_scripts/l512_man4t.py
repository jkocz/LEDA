#!/usr/bin/env python

import time
import struct
import sys

import corr
import numpy

from leda_config import arp_config as arp

roach_array = ['rofl%i' % ii for ii in range(1,17)]

gbe0 = 'gbe0'
gbe1 = 'gbe1'

i = 0

for roach in roach_array:

    # roach2 = roach_array(i);
    print('Connecting to server %s on port... ' % roach),
    fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

    time.sleep(1)

    if fpga.is_connected():
        print 'ok\n'
    else:
        print 'ERROR\n'

    #fpga.progdev('l512_dev_20130717.bof')

    print '------------------------'
    print 'Enable 10gbe core...\n',

    fpga.config_10gbe_core('tenge_gbe00', arp.mac_base0 + arp.src_ip_base + (i * 2),
                           arp.src_ip_base + (i * 2), arp.src_port0, arp.arp_table)
    fpga.config_10gbe_core('tenge_gbe01', arp.mac_base0 + arp.src_ip_base + (i * 2) + 1,
                           arp.src_ip_base + (i * 2) + 1, arp.src_port1, arp.arp_table)
    #fpga.tap_start(gbe0,'tenge_gbe00',mac_base0+src_ip_base+(i*2),src_ip_base+(i*2),src_port0)
    #fpga.tap_start(gbe1,'tenge_gbe01',mac_base0+src_ip_base+(i*2)+1,src_ip_base+(i*2)+1,src_port1)

    time.sleep(2)

    print '------------------------\n'
    print 'Setting-up packet core...\n',
    sys.stdout.flush()

    fpga.write_int('tenge_port1',  arp.dest_port0)
    fpga.write_int('tenge_port2',  arp.dest_port1)

    fpga.write_int('tenge_ips_ip1',  arp.dest_ip0)
    fpga.write_int('tenge_ips_ip2',  arp.dest_ip1)
    fpga.write_int('tenge_ips_ip3',  arp.dest_ip2)
    fpga.write_int('tenge_ips_ip4',  arp.dest_ip3)
    fpga.write_int('tenge_ips_ip5',  arp.dest_ip4)
    fpga.write_int('tenge_ips_ip6',  arp.dest_ip5)
    fpga.write_int('tenge_ips_ip7',  arp.dest_ip6)
    fpga.write_int('tenge_ips_ip8',  arp.dest_ip7)
    fpga.write_int('tenge_ips_ip9',  arp.dest_ip8)
    fpga.write_int('tenge_ips_ip10', arp.dest_ip9)
    fpga.write_int('tenge_ips_ip11', arp.dest_ip10)
    fpga.write_int('tenge_ips_ip12', arp.dest_ip0)
    fpga.write_int('tenge_ips_ip13', arp.dest_ip1)
    fpga.write_int('tenge_ips_ip14', arp.dest_ip2)
    fpga.write_int('tenge_ips_ip15', arp.dest_ip3)
    fpga.write_int('tenge_ips_ip16', arp.dest_ip4)
    fpga.write_int('tenge_ips_ip17', arp.dest_ip5)
    fpga.write_int('tenge_ips_ip18', arp.dest_ip6)
    fpga.write_int('tenge_ips_ip19', arp.dest_ip7)
    fpga.write_int('tenge_ips_ip20', arp.dest_ip8)
    fpga.write_int('tenge_ips_ip21', arp.dest_ip9)
    fpga.write_int('tenge_ips_ip22', arp.dest_ip10)

    fpga.write_int('tenge_header_fid', i)

    fpga.write_int('tenge_start_count', 1246);
    fpga.write_int('tenge_stop_count', 1464);
    fpga.write_int('tenge_high_ch', 109);

    fpga.write_int('fft_f1_fft_shift', 65535);
    fpga.write_int('fft_f2_fft_shift', 65535);
    fpga.write_int('fft_f3_fft_shift', 65535);
    fpga.write_int('fft_f4_fft_shift', 65535);

    odata = numpy.ones(4096, 'l') * (1500 << 7) * 0.7
    cstr = struct.pack('>4096l', *odata)

    fpga.write('fft_f1_coeff_eq0_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq1_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq2_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq3_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq4_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq5_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq6_coeffs', cstr)
    fpga.write('fft_f1_coeff_eq7_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq0_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq1_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq2_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq3_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq4_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq5_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq6_coeffs', cstr)
    fpga.write('fft_f2_coeff_eq7_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq0_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq1_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq2_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq3_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq4_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq5_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq6_coeffs', cstr)
    fpga.write('fft_f3_coeff_eq7_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq0_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq1_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq2_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq3_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq4_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq5_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq6_coeffs', cstr)
    fpga.write('fft_f4_coeff_eq7_coeffs', cstr)

    print '------------------------\n'
    print 'Resetting counter...\n',
    fpga.write_int('tenge_enable', 0)
    fpga.write_int('adc_rst', 3)
    #fpga.write_int('adc_rst', 0)
    #fpga.write_int('enable', 1)
    print 'done'
    i += 1


