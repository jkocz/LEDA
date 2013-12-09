#!/usr/bin/env python
from multiprocessing import Process, Array
import subprocess
import time
import numpy as np
import ujson as json
from pywt import dwt, idwt
from termcolor import colored, cprint
import matplotlib
matplotlib.use('PDF')
import pylab as plt

def plot64(data, offset):
    title = "Antpol %i-%i"%(offset+1, offset+64)
    print "Plotting ", title
    fig = plt.figure(figsize=(12,9))
    for rx in range(1, 65):
        plt.subplot(8, 8, rx)
        d = data[rx+offset-1]
        rms = np.average(np.abs(d))
        if rms <= 1.0:
            col = 'red' #Under 1-bit RMS (no input)
        elif rms <= 8.0:
            col = 'orange' #Under 3-bit RMS
        elif rms >= 2**5.5:
            col = 'black' #Over 5 1/2-bit RMS
        else:
            col = 'green'    
        plt.plot(d, color=col)
    plt.title(title)
    fig.canvas.set_window_title(title)

def grab_adc16(roach, arr, filter=False):
    """ Run subprocess to call adc16_dump_chans script """
    sp = subprocess.Popen(["adc16_dump_chans.rb", "-l", str(n_samples), roach], stdout=subprocess.PIPE)
    out, err = sp.communicate()
    data = np.fromstring(out, sep=' ', dtype='int')
    #print data.shape
    if filter:
        # Filter out low frequency stuff
        ca, cd = dwt(data, 'haar')
        cd = np.zeros_like(cd)
        data = idwt(ca,cd,'haar').astype('int')
    for i in range(len(arr)):
        arr[i] = data[i]
    return



if __name__ == '__main__':
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach, n_samples = len(roachlist), 512
    
    allsystemsgo = True
    fig = plt.figure(figsize=[12,9])
    ax = plt.subplot(111)
    im = ax.matshow(np.zeros([16,32]), interpolation="none", clim=[0,128])
    cbar = fig.colorbar(im, orientation="horizontal")
    ax.set_xticks([4*i for i in range(8)])
    ax.set_xticklabels([2*i+1 for i in range(8)])
    ax.set_yticks([i for i in range(16)])
    ax.set_yticklabels([16*i for i in range(16)])

    #plt.colorbar(orientation="horizontal")
    while allsystemsgo:
        # Create threads and shared memory
        procs = []
        arrs  = [Array('i', range(n_samples*32)) for roach in roachlist]
        for i in range(n_roach):
            p = Process(target=grab_adc16, args=(roachlist[i], arrs[i]))
            procs.append(p)
        # Start threads
        for p in procs:
            p.start()
        # Join threads      
        for p in procs:
            p.join()
            
        data = np.zeros([n_roach*32, n_samples])
        #plt.plot(arrs[0][::32])
        #plt.show()
        #exit()
        
        for i in range(len(arrs)):
            a = np.array(arrs[i][:]).reshape([n_samples, 32]).T
            data[32*i:32*i+32] = a 
        
        i = 1
        squares = []
        for row in data:
            rms = np.average(np.abs(data[i-1]))
            if rms <= 1.0:
                #cprint("%03d\t%02.2f\tNO_POW"%(i, rms), 'red')
                squares.append(1)
            elif rms <= 8.0:
                #cprint("%03d\t%02.2f\tLOW_POW"%(i, rms), 'yellow')
                squares.append(2)
            else:
                #cprint("%03d\t%02.2f\tOK"%(i, rms), 'green')
                squares.append(3)
            i += 1
        
        #squares = np.array(squares).reshape([16,32])  
        #cmap = matplotlib.colors.ListedColormap(['#94e5b7', '#57D68D', '#27AE60'])
        #ax = plt.subplot(111, aspect='equal')  
        #plt.pcolor(squares, edgecolors='k', cmap=cmap)
        #plt.xticks([i for i in range(32)])
        #plt.xlim(0,32)
        #plt.yticks([i for i in range(16)], [32*i for i in range(16)])
        
        rmsvals = []
        for row in data:
            rmsvals.append(np.std(row))
        rmsvals = np.array(rmsvals).reshape([16,32]) 
        
        im.set_data(rmsvals)
        
        plt.savefig('matrix.pdf')
        exit()
