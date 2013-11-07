

import socket

if __name__ == "__main__":
    
    print "Creating socket"
    #sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock = socket.socket()
    
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    host = "192.168.25.7"
    #host = "192.168.25.8" # WRONG
    port = 3023
    #port = 3022 # WRONG
    print "Connecting..."
    sock.connect((host, port))
    
    #print "Sending 'hold'..."
    #print sock.sendto('hold', (host, port))
    
    print "Sending 'hold'..."
    #ret = sock.send('hold')
    ret = sock.sendall('hold')
    print "  Sent", ret, "bytes"
    
    print "Receiving..."
    ret = sock.recv(512)
    print "Received:", ret
    
    #print "Successful!"
    """
    ret, addr = sock.recvfrom(512)
    print "Received:"
    print addr
    print ret
    """
    sock.close()
    print "Done"
