#!/usr/bin/env python
"""Transfer data between a serial port and one (or more) TCP
connections.
    options:
    -h, --help:        this help
    -p, --port=PORT: port, a number, default = /dev/arduino or can use
                        anumeric value or a device name
    -b, --baud=BAUD: baudrate, default 38400
    -t, --tcp=PORT: TCP port number, (admin) default 1234
    -l, --log: log data streams to 'snifter-0', 'snifter-1'
    -L, --log_name=NAME: log data streams to '<NAME>-0', '<NAME>-1'
"""

import sys
import getopt
from twisted.internet import reactor, protocol
from twisted.internet.serialport import SerialPort
#from zope.interface import implements
from twisted.internet import protocol, interfaces
#import serial #get the serial constants
import gc

# FIXME set serial buffer size? SEND_LIMIT

class Serialport(protocol.Protocol):
    """Create a serial port connection and pass data from it to a
    known list of TCP ports."""
    
    def __init__(self, port, reactor, baudrate, log_name=None):
        self.admintcp_ports = []
        self.fgfstcp_ports = []
        #OLD self.serial = serialport.SerialPort(self, reactor, port, baudrate, rtscts=0)
        self.serial = SerialPort(self, reactor, port, baudrate)
        self.serial.registerProducer(self, True)
        self.paused = False
        self.log = None
        if log_name is not None:
            self.log = file('%s-0' % log_name, 'w')

    def add_admintcp(self, tcp_port):
        """Add a AdminPort to those receiving serial data."""
        if self.paused:
            tcp_port.transport.pauseProducing()
        self.admintcp_ports.append(tcp_port)

    def del_admintcp(self, tcp_port):
        """Remove a AdminPort from the those receiving serial data."""
        self.admintcp_ports.remove(tcp_port)

    def add_fgfstcp(self, tcp_port):
        """Add a AdminPort to those receiving serial data."""
        if self.paused:
            tcp_port.transport.pauseProducing()
        self.fgfstcp_ports.append(tcp_port)

    def del_fgfstcp(self, tcp_port):
        """Remove a AdminPort from the those receiving serial data."""
        self.fgfstcp_ports.remove(fgfstcp_port)


    def write(self, data):
        """Write data to the serial port."""
        gear_data=data[6:7]
        data= "(gear %s);\r" % (gear_data)
        self.serial.write(data)
        len_data=len(data)
        print "SW: write data: %s:%d" % (data.strip(), len_data)
        if self.log:
            self.log.write(data)

    def pauseProducing(self):
        """Pause producing event"""
        print "pause producing"
        self.paused = True
        for port in self.admintcp_ports:
            port.transport.pauseProducing()
        for port in self.fgfstcp_ports:
            port.transport.pauseProducing()
        

    def resumeProducing(self):
        """Resume producing event"""
        print "resume producing"
        self.paused = False
        for port in self.admintcp_ports:
            port.transport.resumeProducing()
        for port in self.fgfstcp_ports:
            port.transport.resumeProducing()

    def stopProducing(self):
        """Stop producing event"""
        print "Serial port has gone away. Shutting down..."
        reactor.stop()

    def dataReceived(self, data):
        """Pass any received data to the list of AdminPorts."""
        len_data=len(data)
        print "SDR: write data: %s:%d" % (data.strip(), len_data)
        
        for tcp_port in self.admintcp_ports:
            tcp_port.write(data)
        for tcp_port in self.fgfstcp_ports:
            tcp_port.write(data)
                
class AdminPort(protocol.Protocol):
    """Create a TCP server connection and pass data from it to the
    serial port."""

    def __init__(self, serial, log_name, index):
        """Add this AdminPort to the SerialPort."""
        self.serial = serial
        self.serial.add_admintcp(self)
        self.log = None
        if log_name is not None:
            self.log = file('%s-%d' % (log_name, index+1), 'w')

    def __del__(self):
        """Remove this AdminPort from the SerialPort."""
        pass
    
    def connectionLost(self, reason):
        self.serial.del_admintcp(self)

        return True

    def dataReceived(self, data):
        """Pass received data to the SerialPort."""
        len_data=len(data)
        print "ADR: write data: %s:%d" % (data.strip(), len_data)
        self.serial.write(data)

    def write(self, data):
        """Write data to the TCP port(s)."""
        self.transport.write(data)
        len_data=len(data)
        print "AAW: write data: %s:%d" % (data.strip(), len_data)
        if self.log is not None:
            self.log.write(data)


class AdminPortFactory(protocol.ServerFactory):
    """Factory to create AdminPort protocol instances, an instanced
    SerialPort must be passed in."""

    def __init__(self, serial, log_name=None):
        self.serial = serial
        self.log_name = log_name
        self.index = 0

    def buildProtocol(self, addr):
        """Build a AdminPort, passing in the instanced SerialPort."""
        p = AdminPort(self.serial, self.log_name, self.index)
        self.index += 1
        p.factory = self
        return p

class FGFSPort(protocol.Protocol):
    """Create a TCP server connection and pass data from it to the
    serial port."""

    def __init__(self, serial, log_name, index):
        #Expected number of chunks... May not be used.
        self.num_of_chunks=3
        self.old_chunks= {}
        self.fgfs_params=["gear", "altitude", "landing-pos"]
        
        """Add this AdminPort to the SerialPort."""
        self.serial = serial
        self.serial.add_fgfstcp(self)
        self.log = None
        
        if log_name is not None:
            self.log = file('%s-%d' % (log_name, index+1), 'w')

    def __del__(self):
        """Remove this AdminPort from the SerialPort."""
        self.serial.del_fgfstcp(self)
        
    def connectionLost(self, reason):
        self.serial.del_fgfstcp(self)

        return True


    def dataReceived(self, data):
        """Pass received data to the SerialPort."""
        len_data=len(data)
        print "FDR: got data: %s:%d" % (data.strip(), len_data)
        data=data.strip()
        chunks=data.split("|")
        """ for each chunk:
        
        """
        new_data=""
        chunk={"gear":0, "altitude":0, "landing-pos":-1 }
        print "DEBUG: Old Chunks: ", self.old_chunks
        for idx,item in enumerate(self.fgfs_params):
            print idx, item

            chunk[idx]=chunks[idx]

            if ((item in self.old_chunks) is False) or self.old_chunks[item] != chunk[item]:
                try:
                    print "DEBUG: Difference found: %s: %s => %s" % (item,  self.old_chunks[item], chunk[item])
                except KeyError, e:
                    print "DEBUG: Difference found: %s: N/A => %s" % (item, chunk[item])
                    pass
                self.old_chunks[item]=chunk[idx]
                
                new_data=new_data+"(%s: 1);\n" % (item)
        print "DEBUG: New Chunks: ", self.old_chunks
        len_data=len(new_data)
        print "FDR: sent data: %s:%d" % (new_data.strip(), len_data)
                
        self.serial.write(new_data)

    def write(self, data):
        """Write data to the TCP port."""
        self.transport.write(data)
        len_data=len(data)
        print "FAW: write data: %s:%d" % (data.strip(), len_data)
        if self.log is not None:
            self.log.write(data)
            
 


class FGFSPortFactory(protocol.ServerFactory):
    """Factory to create AdminPort protocol instances, an instanced
    SerialPort must be passed in."""

    def __init__(self, serial, log_name=None):
        self.serial = serial
        self.log_name = log_name
        self.index = 0

    def buildProtocol(self, addr):
        """Build a FGFSPort, passing in the instanced SerialPort."""
        p = FGFSPort(self.serial, self.log_name, self.index)
        self.index += 1
        p.factory = self
        return p
        

def usage(text=None):
    print sys.stderr, """Syntax: %s [options]\n%s""" % (sys.argv[0], __doc__)
    print sys.stderr, "Uses tty /dev/arduino with baudrate of 38400 and opens port 1234"
    if text:
        print >>sys.stderr, text

def main():
    """Parse the command line and run the UI"""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:b:t:lL:",
	        ["help", "port=", "baud=", "tcp=", "log", "log_name="])
    except getopt.GetoptError, e:
        usage(e)
        sys.exit(2)
        
    tty_port = '/dev/arduino'
    baudrate = 38400
    tcp_port = 1234
    log_name = None

    
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-p", "--port"):
            try:
                tty_port = int(a)
            except ValueError:
                tty_port = a
        elif o in ("-b", "--baud"):
            try:
                baudrate = int(a)
            except ValueError:
                usage("Bad baud rate %r" % a)
        elif o in ("-t", "--tcp"):
            try:
                tcp_port = int(a)
            except ValueError:
                usage("Bad TCP port %r" % a)
        elif o in ("-l", "--log"):
            log_name = 'snifter'
        elif o in ("-L", "--log_name"):
            log_name = a
    
    serial_port = Serialport(reactor, tty_port, baudrate, log_name)

    admin_port_factory = AdminPortFactory(serial_port, log_name)
    fgfs_port_factory = FGFSPortFactory(serial_port, log_name)

    reactor.listenTCP(tcp_port, admin_port_factory)
    reactor.listenTCP(5555, fgfs_port_factory)

    print "Listening to admin port on %d and 5555" % ( tcp_port )

    reactor.run()

if __name__ == "__main__":
    main()
