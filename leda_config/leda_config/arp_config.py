"""
arp_config.py
-------------

ARP table configuration for RAOCh2 boards. This has to be set manually to get the 40GbE working.

Last updated: November 2014
"""

def ip_address(ipaddr):
    """ Convert IP address to integer for ROACH programming """

    ipb = [int(ipbit) for ipbit in ipaddr.split('.')]
    assert len(ipb) == 4
    int_addr = ipb[0] * (2 ** 24) + ipb[1] * (2 ** 16) + ipb[2] * (2 ** 8) + ipb[3]

    return int_addr

def mac_address(macaddr):
    """ Convert IP address to integer for ROACH programming
    Address should be of form 00:01:02:03:04:05
    """

    m = [int(mb, 16) for mb in macaddr.split(':')]
    assert len(m) == 6
    int_addr = m[0] * (2 ** 40) + m[1] * (2 ** 32) + m[2] * (2 ** 24) + m[3] * (2 ** 16) + m[4] * (2 ** 8) + m[5]

    return int_addr

def int_to_ip(ipnum):
    """ Convert integer IP to regular string IP """
    o1 = int(ipnum / 16777216) % 256
    o2 = int(ipnum / 65536) % 256
    o3 = int(ipnum / 256) % 256
    o4 = int(ipnum) % 256
    return '%(o1)s.%(o2)s.%(o3)s.%(o4)s' % locals()

def int_to_mac(ipnum):
    """ Convert integer MAC to regular string MAC """
    o0 = int(ipnum / 2 ** 40) % 256
    o1 = int(ipnum / 2 ** 32) % 256
    o2 = int(ipnum / 2 ** 24) % 256
    o3 = int(ipnum / 2 ** 16) % 256
    o4 = int(ipnum / 2 ** 8) % 256
    o5 = int(ipnum) % 256
    return '%(o0)02x:%(o1)02x:%(o2)02x:%(o3)02x:%(o4)02x:%(o5)02x' % locals()


dest_ip0  = ip_address('192.168.40.10')
dest_ip1  = ip_address('192.168.40.11')
dest_ip2  = ip_address('192.168.40.12')
dest_ip3  = ip_address('192.168.40.13')
dest_ip4  = ip_address('192.168.40.14')
dest_ip5  = ip_address('192.168.40.15')
dest_ip6  = ip_address('192.168.40.16')
dest_ip7  = ip_address('192.168.40.17')
dest_ip8  = ip_address('192.168.40.18')
dest_ip9  = ip_address('192.168.40.19')
dest_ip10 = ip_address('192.168.40.20')

dest_mac0  = mac_address('00:02:c9:46:20:90')
dest_mac1  = mac_address('00:02:c9:ec:9b:10')
dest_mac2  = mac_address('00:02:c9:ec:9a:80')
dest_mac3  = mac_address('00:02:c9:46:20:00')
dest_mac4  = mac_address('00:02:c9:ec:9c:00')
dest_mac5  = mac_address('00:02:c9:ec:9c:40')
dest_mac6  = mac_address('00:02:c9:ec:97:A0')
dest_mac7  = mac_address('00:02:c9:ec:9c:A0')
dest_mac8  = mac_address('00:02:c9:46:19:50')
dest_mac9  = mac_address('00:02:c9:ec:9a:d0')
dest_mac10 = mac_address('00:02:c9:ec:9b:f0')

rofl1_mac0  = mac_address('02:02:c0:a8:28:32')
rofl1_mac1  = mac_address('02:02:c0:a8:28:33')
rofl2_mac0  = mac_address('02:02:c0:a8:28:34')
rofl2_mac1  = mac_address('02:02:c0:a8:28:35')
rofl3_mac0  = mac_address('02:02:c0:a8:28:36')
rofl3_mac1  = mac_address('02:02:c0:a8:28:37')
rofl4_mac0  = mac_address('02:02:c0:a8:28:38')
rofl4_mac1  = mac_address('02:02:c0:a8:28:39')
rofl5_mac0  = mac_address('02:02:c0:a8:28:3a')
rofl5_mac1  = mac_address('02:02:c0:a8:28:3b')
rofl6_mac0  = mac_address('02:02:c0:a8:28:3c')
rofl6_mac1  = mac_address('02:02:c0:a8:28:3d')
rofl7_mac0  = mac_address('02:02:c0:a8:28:3e')
rofl7_mac1  = mac_address('02:02:c0:a8:28:3f')
rofl8_mac0  = mac_address('02:02:c0:a8:28:40')
rofl8_mac1  = mac_address('02:02:c0:a8:28:41')
rofl9_mac0  = mac_address('02:02:c0:a8:28:42')
rofl9_mac1  = mac_address('02:02:c0:a8:28:43')
rofl10_mac0 = mac_address('02:02:c0:a8:28:44')
rofl10_mac1 = mac_address('02:02:c0:a8:28:45')
rofl11_mac0 = mac_address('02:02:c0:a8:28:46')
rofl11_mac1 = mac_address('02:02:c0:a8:28:47')
rofl12_mac0 = mac_address('02:02:c0:a8:28:48')
rofl12_mac1 = mac_address('02:02:c0:a8:28:49')
rofl13_mac0 = mac_address('02:02:c0:a8:28:4a')
rofl13_mac1 = mac_address('02:02:c0:a8:28:4b')
rofl14_mac0 = mac_address('02:02:c0:a8:28:4c')
rofl14_mac1 = mac_address('02:02:c0:a8:28:4d')
rofl15_mac0 = mac_address('02:02:c0:a8:28:4e')
rofl15_mac1 = mac_address('02:02:c0:a8:28:4f')
rofl16_mac0 = mac_address('02:02:c0:a8:28:50')
rofl16_mac1 = mac_address('02:02:c0:a8:28:51')

dest_macff  = mac_address('ff:ff:ff:ff:ff:ff')


######################
#  CREATE ARP TABLE  #
######################
arp_table = [dest_macff for i in range(256)]

arp_table[10] = dest_mac0
arp_table[11] = dest_mac1
arp_table[12] = dest_mac2
arp_table[13] = dest_mac3
arp_table[14] = dest_mac4
arp_table[15] = dest_mac5
arp_table[16] = dest_mac6
arp_table[17] = dest_mac7
arp_table[18] = dest_mac8
arp_table[19] = dest_mac9
arp_table[20] = dest_mac10

arp_table[50] = rofl1_mac0
arp_table[51] = rofl1_mac1
arp_table[52] = rofl2_mac0
arp_table[53] = rofl2_mac1
arp_table[54] = rofl3_mac0
arp_table[55] = rofl3_mac1
arp_table[56] = rofl4_mac0
arp_table[57] = rofl4_mac1
arp_table[58] = rofl5_mac0
arp_table[59] = rofl5_mac1
arp_table[60] = rofl6_mac0
arp_table[61] = rofl6_mac1
arp_table[62] = rofl7_mac0
arp_table[63] = rofl7_mac1
arp_table[64] = rofl8_mac0
arp_table[65] = rofl8_mac1
arp_table[66] = rofl9_mac0
arp_table[67] = rofl9_mac1
arp_table[68] = rofl10_mac0
arp_table[69] = rofl10_mac1
arp_table[70] = rofl11_mac0
arp_table[71] = rofl11_mac1
arp_table[72] = rofl12_mac0
arp_table[73] = rofl12_mac1
arp_table[74] = rofl13_mac0
arp_table[75] = rofl13_mac1
arp_table[76] = rofl14_mac0
arp_table[77] = rofl14_mac1
arp_table[78] = rofl15_mac0
arp_table[79] = rofl15_mac1
arp_table[80] = rofl16_mac0
arp_table[81] = rofl16_mac1

arp_table_str = [int_to_mac(aa) for aa in arp_table]

dest_ips = [dest_ip0, dest_ip1, dest_ip2, dest_ip3, dest_ip4, dest_ip5,
            dest_ip6, dest_ip7, dest_ip8, dest_ip9, dest_ip10,
            dest_ip0, dest_ip1, dest_ip2, dest_ip3, dest_ip4, dest_ip5,
            dest_ip6, dest_ip7, dest_ip8, dest_ip9, dest_ip10]

dest_ips_str = [int_to_ip(dd) for dd in dest_ips]


dest_port0 = 4015
dest_port1 = 4016

src_port0 = 4000
src_port1 = 4001

src_ip_base = 192 * (2 ** 24) + 168 * (2 ** 16) + 40 * (2 ** 8) + 50
mac_base0   = (2 << 40) + (2 << 32)

gbe0     = 'gbe0'
gbe1     = 'gbe1'
