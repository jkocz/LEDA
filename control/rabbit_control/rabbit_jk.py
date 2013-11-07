

import socket

if __name__ == "__main__":
    
    print "Creating socket"
    #sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    host = "192.168.25.7"
    #host = "192.168.25.8" # WRONG
    port = 3023
    #port = 3022 # WRONG
    print "Connecting..."
    sock.connect((host, port))
    print "Sending 'hold'..."
    sock.sendto('hold', (host, port))
    print "Successful!"
    sock.close()
