# Example: Connect to a fg_con server
#Expected syntax in both direction as follows:
"""parameters (example:
    gear        0|1
    altitude    any integer
    gear-pos    0|1

parameters are separated by pipes (|);
"""

import socket
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 5555)) # fgfs generic port (user defined)
#junk= s.recv(1024)

done=0;
while done==0:
    s.send("0|400|0")
    #print s.recv(40)
    time.sleep(0.5)

    #s.send("0|600|0")
    #print s.recv(40)
    time.sleep(0.5)

    #s.send("0|800|0")
    #print s.recv(40)
    time.sleep(0.5)

    #s.send("1|1200|0\n")
    #print s.recv(40)
    time.sleep(0.5)
    
    #print s.recv(40)
    s.send("1|1500|1\n")
    done=1
    
s.close()
