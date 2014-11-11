import corr
import time
import struct
import numpy as np

ll = 4096

class Ledaspec(object):
    """docstring for Fpga"""
    def __init__(self, hostname):
        self.hostname = hostname
        self.fpga = corr.katcp_wrapper.FpgaClient(hostname)

    def primeSnap(self):
        """ Prime snap block """
        for ii in range(8):
            self.fpga.write_int('s64_xx%i_ctrl'%ii, 0)
            self.fpga.write_int('s64_yy%i_ctrl'%ii, 0)
            self.fpga.write_int('s64_xx%i_ctrl'%ii, 1)
            self.fpga.write_int('s64_yy%i_ctrl'%ii, 1)

    def readSnap(self, snap_id, n_bytes=ll*4*2):
        """ Read from a snap block """
        ctrl = snap_id + '_ctrl'
        bram = snap_id + '_bram'

        #print ctrl, bram
        #self.fpga.write_int(ctrl, 0)
        data = self.fpga.read(bram, n_bytes)
        #self.fpga.write_int(ctrl, 1)
        return data

    def unpackSpec(self, data, fmt='>%iQ'%ll):
        """ Unpack spectrum """
        b  = struct.unpack(fmt, data)
        bb = np.array(b)
        return bb

    def snapUnpack(self):
        xx_list = []
        yy_list = []
        
        for ii in range(8):
            # MAY 2014 MAPPING!
            #print ii
            x = self.readSnap('s64_xx%i'%(ii), ll * 4 * 2)
            y = self.readSnap('s64_yy%i'%(ii), ll * 4 * 2)
            xx_list.append(self.unpackSpec(x, '>%iQ'%ll))
            yy_list.append(self.unpackSpec(y, '>%iQ'%ll))

        return xx_list, yy_list

    def wait_for_acc(self):
        timeout = 6
        acc_init = self.fpga.read_int('acc_cnt')
        acc_new  = acc_init
        t1 = time.time()
        while acc_new <= acc_init:
            time.sleep(0.001)
            acc_new = self.fpga.read_int('acc_cnt')
            t2 = time.time()
            if t2 - t1 > 6:
                raise RuntimeError("Acc timeout: acc_cnt %i"%acc_init)

    def is_connected(self):
        return self.fpga.is_connected()

    def read_int(self, reg_id):
        return self.fpga.read_int(reg_id)
