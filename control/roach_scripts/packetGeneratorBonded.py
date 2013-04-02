import corr, logging, sys, time, struct, binascii

#Set destination and source address for port0
dest_ip0  =192*(2**24) + 168*(2**16) + 6*(2**8) + 8 #192.168.2.45
dest_port0 = 4006
dest_mac0 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 120 #00:0f:53:0c:ff:78
#dest_mac0 = 27*(2**32) + 33*(2**24) + 216*(2**16) + 209*(2**8) + 105 #00:1b:21:d8:d1:69
fabric_port0 = 60000         
source_ip0 = 192*(2**24) + 168*(2**16) + 6*(2**8) + 106 #192.168.2.114

#Set destination and source address for port1
dest_ip1  =192*(2**24) + 168*(2**16) + 9*(2**8) + 8  #192.168.2.45
dest_port1 = 4009
#dest_mac1 = 27*(2**32) + 33*(2**24) + 216*(2**16) + 209*(2**8) + 105 #00:1b:21:d8:d1:69 
dest_mac1 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 121 #00:0f:53:0c:ff:79
fabric_port1 = 60001         
source_ip1 = 192*(2**24) + 168*(2**16) + 9*(2**8) + 109 #192.168.2.114

#Set destination and source address for port2
dest_ip2  =192*(2**24) + 168*(2**16) + 7*(2**8) + 8 #192.168.4.45
dest_port2 = 4007
#dest_mac2 = 104*(2**40) + 5*(2**32) + 202*(2**24) + 4*(2**16) + 135*(2**8) + 3 #68:05:ca:04:87:03
dest_mac2 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 84 #00:0f:53:0c:ff:54
fabric_port2 = 60002         
source_ip2 = 192*(2**24) + 168*(2**16) + 7*(2**8) + 107 #192.168.4.114

#Set destination and source address for port3
dest_ip3  =192*(2**24) + 168*(2**16) + 10*(2**8) + 8 #192.168.4.45
dest_port3 = 8511
#dest_mac3 = 104*(2**40) + 5*(2**32) + 202*(2**24) + 4*(2**16) + 135*(2**8) + 3 #68:05:ca:04:87:03
dest_mac3 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 85 #00:0f:53:0c:ff:55
fabric_port3 = 60003         
source_ip3 = 192*(2**24) + 168*(2**16) + 10*(2**8) + 110 #192.168.4.114

print 'source ip %i'%source_ip0

print 'dest ip %i'%dest_ip0
mac_base=(2<<40) + (2<<32)
ip_prefix='10. 0. 0.'

#Set configuration of system test Each port will output n_f_engine * n_x_engine packets per mcnt
n_f_engine = 4 #Per port 
n_x_engine = 1 #Per port

#Set the fid to start outputing from on each port, the port will send packets with fids from fid_shift to fid_shift + n_f_engine
fid_shift0=0
fid_shift1=0
fid_shift2=0
fid_shift3=0

#Set the xid to start outputing from on each port, the port will send packets with xids from xid_shift to xid_shift + n_x_engine
xid_shift0=0
xid_shift1=0
xid_shift2=0
xid_shift3=0

payload_length = 2 ** 10 # * 64 bits
output_speed = 3.2 #Gbits per second per port

output_port0 = 'ten_GbE_1'
output_port1 = 'ten_GbE_2'
output_port2 = 'ten_GbE_3'
output_port3 = 'ten_GbE_4'

boffile = 'gpucorr_txsim03r2_2012_Dec_13_1143.bof'

fpgas=[]

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    try:
        for f in fpgas: f.stop()
    except: pass
    raise
    exit()

def exit_clean():
    print 'Disabling output...',
    sys.stdout.flush()
    exit()

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('packetGenerator.py <ROACH_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-d', '--dest_ip', dest='dest_ip', type = 'int', default = dest_ip0,
        help='Set destination ip.')  
    p.add_option('-p', '--dest_port', dest='dest_port', type = 'int', default = dest_port0,
        help='Set destination port.')  
    p.add_option('-b', '--boffile', dest='bof', type='str', default=boffile,
        help='Specify the bof file to load.')  
    p.add_option('-f', '--n_f_engine', dest='n_f_engine', type='int', default=n_f_engine,
        help='Specify the number of f engines to simulate.')  
    p.add_option('-x', '--n_x_engine', dest='n_x_engine', type='int', default=n_x_engine,
        help='Specify the number of x engines.') 
    p.add_option('-l', '--payload_length', dest='payload_length', type='int', default=payload_length,
        help='Specify the payload length.')
    p.add_option ('-s', '--output_speed', dest='output_speed', type='float', default=output_speed,
        help='Specify the speed to output on each 10Gbit ethernet port, do not make higher than 6.35.')
    opts, args = p.parse_args(sys.argv[1:])

    if args==[]:
        print 'Please specify a ROACH board. \nExiting.'
        exit()
    else:
        roach = args[0]
    if opts.bof != '':
        boffile = opts.bof
    if opts.bof > 6.35:
        opts.bof = 6.35

    try:
        lh=corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(roach)
        logger.addHandler(lh)
        logger.setLevel(10)

        print('Connecting to server %s... '%(roach)),
        fpga = corr.katcp_wrapper.FpgaClient(roach, logger=logger)
        fpgas.append(fpga)
        time.sleep(1)

        if fpga.is_connected():
            print 'ok\n'
        else:
            print 'ERROR connecting to server %s.\n'%(roach)
            exit_fail()

            print '------------------------'
        print 'Programming FPGA...',
        sys.stdout.flush()
        fpga.progdev(boffile)
        #time.sleep(10)
        print 'ok'
        
        print '---------------------------'
        
        print 'Port 0 linkup: ',
        sys.stdout.flush()
        gbe0_link=bool(fpga.read_int('led_up'))
        print gbe0_link
        if not gbe0_link:
            print 'There is no cable plugged into port0. Please plug a cable into all ports to continue demo. Exiting.'
            exit_clean()
        
        for i in range(1,4):
            print 'Port %i linkup: '%i,
            sys.stdout.flush()
            gbe0_link=bool(fpga.read_int('led_up%i'%i))
            print gbe0_link
            if not gbe0_link:
                print 'There is no cable plugged into port%i. Please plug a cable into all ports to continue demo. Exiting.'%i
                exit_clean()

        print 'Configuring transmitter cores...',
        sys.stdout.flush()

        #Configure 10GbE cores and install tgtap drivers.
        print ('Configuring the 10GbE cores...'),
        arp_table = [dest_mac0 for i in range(256)]
        fpga.config_10gbe_core('ten_GbE_1', mac_base+source_ip0, source_ip0, fabric_port0, arp_table)

        arp_table = [dest_mac1 for i in range(256)]
        fpga.config_10gbe_core('ten_GbE_2', mac_base+source_ip1, source_ip1, fabric_port1, arp_table)

        arp_table = [dest_mac2 for i in range(256)]
        fpga.config_10gbe_core('ten_GbE_3', mac_base+source_ip2, source_ip2, fabric_port2, arp_table)

        arp_table = [dest_mac3 for i in range(256)]
        fpga.config_10gbe_core('ten_GbE_4', mac_base+source_ip3, source_ip3, fabric_port3, arp_table)


        #fpga.tap_start('tap0',output_port0,mac_base+source_ip0,source_ip0,fabric_port0)
        #fpga.tap_start('tap1',output_port1,mac_base+source_ip1,source_ip1,fabric_port1)
        #fpga.tap_start('tap2',output_port2,mac_base+source_ip2,source_ip2,fabric_port2)
        #fpga.tap_start('tap3',output_port3,mac_base+source_ip3,source_ip3,fabric_port3)
        print 'done'

        print '---------------------------'
        print 'Setting-up packet parameters...',
        sys.stdout.flush()
        pkt_period = int(opts.output_speed * 10)
        print 'pkt_period = %i'%pkt_period
        fpga.write_int('tx_efficiency_32_7',pkt_period)
        fpga.write_int('bram_len',payload_length)
        print 'done'
        
        print "mcnt1 = %i"%struct.unpack('I',struct.pack('i',fpga.read_int('mcnt1')))
        print "mcnt = %i"%struct.unpack('I',struct.pack('i',fpga.read_int('mcnt')))

        print 'Setting-up header parameters...',
        sys.stdout.flush()
        fpga.write_int('N_F_Engine',opts.n_f_engine - 1)
        fpga.write_int('N_X_Engine',opts.n_x_engine - 1)
        fpga.write_int('FID_shift', fid_shift3 * (2**24) + fid_shift2 * (2**16) + fid_shift1 * (2**8) + fid_shift0)
        fpga.write_int('XID_shift', xid_shift3 * (2**24) + xid_shift2 * (2**16) + xid_shift1 * (2**8) + xid_shift0)
        print 'done'

        print 'Setting-up destination addresses...',
        sys.stdout.flush()
        fpga.write_int('tx_dest_ip',dest_ip0)
        fpga.write_int('tx_dest_port',dest_port0)
        fpga.write_int('tx_dest_ip1',dest_ip1)
        fpga.write_int('tx_dest_port1',dest_port1)
        fpga.write_int('tx_dest_ip2',dest_ip2)
        fpga.write_int('tx_dest_port2',dest_port2)
        fpga.write_int('tx_dest_ip3',dest_ip3)
        fpga.write_int('tx_dest_port3',dest_port3)
        print 'done'
        
        sys.stdout.flush()
        
        #BRAM codes controls what data gets added to the packet, all codes are 32 bits long and must be on 32 bit boundaries
        #Set struct.pack('4B',0,0,0,255) to add the message counter (should be at offset 0)
        #Set struct.pack('4B',0,0,0,0) to add data from bram_data
        #Set struct.pack('4B',128,0,0,0) to add data from bram_data and set end of packet flag
        #For each 32 bits in BRAM data codes 64 bits of data is added to the packet
        print 'setting Bram codes... ',
        fpga.write('bram_data_codes',struct.pack('4B',0,0,0,255), offset=0)
        fpga.write('bram_data_codes',struct.pack('B'*4,128,0,0,0), offset=payload_length*4)
        print 'ok'
        
        #Set the data that will be added to the packet, for each 32 bits in BRAM codes which is set to ('4B',0,0,0,0) or '4B',128,0,0,0)
        #the corresponding 32 bits in bram_data_msb and bram_data_lsb will be concatenated add added to the packet
        print 'adding test data',
        fpga.write('bram_data_msb',struct.pack('4B',15,15,15,15),offset=4)
        fpga.write('bram_data_lsb',struct.pack('4B',15,15,15,15),offset=4)
        fpga.write('bram_data_msb',struct.pack('4B',15,15,15,15),offset=8)
        fpga.write('bram_data_lsb',struct.pack('4B',15,15,15,15),offset=8)
        
        print 'checking Bram codes...'
        print 'first 32b = ',
        print struct.unpack('B'*4,fpga.read('bram_data_codes',4, offset=0))
        print 'closing 32b = ',
        print struct.unpack('B'*4,fpga.read('bram_data_codes',4 , offset=(payload_length)*4))

        print 'Enabling output...',
        sys.stdout.flush()
        # gbe_enable controls which ports are sending packets with 4 bits corresponding to each port, set as 1111 (base_2) = 15 (base_10)
        # to send on all four ports. THe bits in gbe_enable correspond to (port0,port1,port2,port3) in that order
        fpga.write_int('gbe_enable',12)
        #Enable to start sending packets
        fpga.write_int('tx_enable',1)
        print 'done'
        count = 0
        while True:
            #the diff values validate that all data is being added to the packets (ie you have not set the data rate too high)
            #This only works when port0 is activated, then if any of the diff values are > 0 that means that that port is not
            #able to handle the data rate and some packets are being sent with missing data
            if (count % 10000000 == 0):
                print 'diff_0_%i = %i'%(count,fpga.read_int('val_ack_diff'))
                print 'diff_1_%i = %i'%(count,fpga.read_int('val_ack_diff1'))
                print 'diff_2_%i = %i'%(count,fpga.read_int('val_ack_diff2'))
                print 'diff_3_%i = %i'%(count,fpga.read_int('val_ack_diff3'))
                pass
            count +=1

    except KeyboardInterrupt:
        fpga.write_int('tx_enable',0)
        fpga.stop()
        exit_clean()
    except:
        exit_fail()

    exit_clean()
