#!/usr/bin/env python
# Copyright (c) 2009, 2010 George Patterson

# Release under GPLv3
 
"""Transfer data between a serial port and one (or more) TCP
connections.
    options:
    -h, --help:     this help
    -p, --port=PORT: port, a number, default = /dev/arduino or can use
                        a numeric value or a device name such as /dev/ttyUSB0
    -b, --baud=BAUD: baudrate, default 38400
    -t, --tcp=PORT: TCP port number, (admin) default 1234
"""
# Operating Parameters:
#   - Entire server needs to be shutdown when changing planes in Flightgear.
#      This is because it's necessary to create flightgear as a server
#      as well as a client. Might be other ways to write this stuff.
#   - Currently there is no authentication nor classes for the admin
#      protocol. This will need to be changed before offical release.

from twisted.internet import reactor, protocol
from twisted.internet.serialport import SerialPort
#from zope.interface import implements
from twisted.internet import protocol, interfaces
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ClientFactory

#Added on 20100219
from twisted.internet.protocol import DatagramProtocol
from time import *

import serial #get the serial constants
import gc
import sys
import getopt
from FlightGear import FlightGear
from readlisp import *
from serial import Serial
import time

hostname="192.168.1.104"


# FIXME set serial buffer size? SEND_LIMIT

class Serialport(protocol.Protocol):
    """Create a serial port connection and pass data from it to a
    known list of TCP ports."""
    
    def __init__(self, port, reactor, baudrate, log_name=None):
        self.admintcp_ports = []
        #from FlightGear import FlightGear
        #from readlisp import *

        #self.fg = FlightGear(hostname, 5500)
        #print "DEBUG: FG:", self.fg["/sim/aero"]
        
        self.fgfstcp_ports = []
        self.fg_host= None
        self.fg_port= None
        self.fg_instance= None

        #The following doesn't work. :-/
        try:
           self.serial = SerialPort(self, reactor, port, baudrate)
        except serial.SerialException:
            print "Error: Arduino interface not found.\n"
            print "Please ensure that the FG Console is plugged into a working USB port and try running this program again.\n"
            print "The other possibibiliy is that the device name is not /dev/arduino. Please see documentation for details.\n"
            sys.exit(0)
        
        self.serial.registerProducer(self, True)
        self.serial_buffer=""
        self.paused = False
        self.log = None
        if log_name is not None:
            self.log = file('%s-0' % log_name, 'w')

        #self.serial.write("(ver);");
        #self.serial.write("(gear 1);");
        

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
        #gear_data=data[6:7]
        #data= "(gear %s);\r" % (gear_data)
        
        len_data=len(data)
        print "SW: write data: %s:%d" % (data.strip(), len_data)
        if self.log:
            self.log.write(data)
        self.serial.write(data)

    #def pauseProducing(self):
    #    """Pause producing event"""
    #    print "pause producing"
    #    self.paused = True
    #    for port in self.admintcp_ports:
    #        port.transport.pauseProducing()
    #    for port in self.fgfstcp_ports:
    #        port.transport.pauseProducing()
        

    #def resumeProducing(self):
    #    """Resume producing event"""
    #    print "resume producing"
    #    self.paused = False
    #    for port in self.admintcp_ports:
    #        port.transport.resumeProducing()
    #    for port in self.fgfstcp_ports:
    #        port.transport.resumeProducing()

    def stopProducing(self):
        """Stop producing event"""
        print "Serial port has gone away. Shutting down..."
        reactor.stop()

    def get_params(self, data):
        #params=get_params(data)
        
        len_data=len(data)
        #print "SDR: write data: %s:%d" % (data, len_data)
        
        self.serial_buffer+=data

        #remove the serial test code from the data stream.
        self.serial_buffer=self.serial_buffer.replace("(init)","")
        self.serial_buffer=self.serial_buffer.replace("(time out error)","")
        self.serial_buffer=self.serial_buffer.replace("(read jackpot)","")
        self.serial_buffer=self.serial_buffer.replace("(error overflow)","")
        self.serial_buffer=self.serial_buffer.replace("(unknown command)","")
        self.serial_buffer=self.serial_buffer.replace("\n","")
        self.serial_buffer=self.serial_buffer.replace("\r","")

        #print "SDR: buffer: %s" % (self.serial_buffer.strip())

        semi_pos=self.serial_buffer.find(";")
        if semi_pos > -1:
            
            data_chunks=self.serial_buffer.split(";")
            s_string=data_chunks[0]
            #print "DEBUG: data chunks: ", data_chunks
            self.serial_buffer=self.serial_buffer[semi_pos+1:]

            
            lisp_result= readlisp(s_string)
            #print "DEBUG: Lisp Result:", lisp_result
            #print "DEBUG: Lisp length:", len(lisp_result);
            #print "DEBUG TYPE:", type(lisp_result[1])
            
            return lisp_result
        else:
            return 0
    
    def process_params(self, params):
        print "DEBUG SPP: params:", params

        if params != "":
            cmd_arr=[]
            for i in range(1, len(params)):
                if len(params[i])==2:
                    param=str(params[i][0])
                    val=params[i][1]
                    #print "DEBUG: SPP Param: ***%s*** Val: %s" % (param, str(val))
                    
                    cmd=""
                    control_pos=""
                    if param[:3] == "adc":
                        if param=="adc1":
                            cmd="/controls/engines/engine/throttle"
                            control_pos= (val-1)/1023.0
                            if val>1000:
                                self.serial.write("(pin10 1);");
                            else:
                                self.serial.write("(pin10 0);");
                            
                                
                        elif str(param).strip()=="adc2":
                            cmd="/controls/engines/engine[1]/throttle"
                            control_pos= (val-1)/1023.0
                            cmd_str="0.0\t"+str(control_pos)+"\t1\t1\n"
                            print "DEBUG: cmd str:", cmd_str
                            self.fg_instance.transport.write(cmd_str)
                        elif str(param).strip()=="adc3":
                            cmd="/controls/engines/engine/prop-pitch"
                            control_pos= (val-1)/1023.0
                        elif str(param).strip()=="adc4":
                            cmd="/controls/engines/engine[1]/prop-pitch"
                            control_pos= (val-1)/1023.0
                            
                        #elif str(param).strip() == "pin2":

                        #print "DEBUG: SPP Cmd: %s val: %f" % (cmd, control_pos)
                        #self.transport.write('Help ME!', (self.fg_host, self.fg_port))

                        if self.fg_instance != None:
                            print "DEBUG: PP: We have a transport instance" 
                            #self.fg_instance.transport.write("0.75\t0.5\t1\t1\n")
                            
                        
                        try:
                            self.fg[cmd]=float(val)/1023.0
                        #except exceptions.AttributeError:
                        except AttributeError:
                            pass #do nothing
                    
                    if param[:3] == "pin":
                        pinNo=param[3:]
                        
                        if pinNo == "1":
                            #print "ERROR: Shouldn't be here"
                            mesg="(pin7 %d);" % val
                            print "DEBUG: Mesg: ", mesg
                            self.serial.write(mesg);
                            #self.serial.write("(gear 1);");
                        elif pinNo == "2":
                            mesg="(pin8 %d);" % val
                            print "DEBUG: Mesg: ", mesg  
                            self.serial.write(mesg)
                            mesg="(pin9 %d);" % val
                            print "DEBUG: Mesg: ", mesg  
                            self.serial.write(mesg)

                        #elif pinNo == "3":
                        #    mesg="(pin11 %d);" % val
                        #    print "SPP: DEBUG: Mesg: ", mesg  
                        #    self.serial.write(mesg)
                        #    #print "DEBUG: Pin3 has been toggled... No Operation taken..."
                        #time.sleep(0.001)

                    #try:
                    #    self.fg[cmd]=control_pos
                    #    #except exceptions.AttributeError:
                    #except AttributeError:
                    #    pass #do nothing


    def dataReceived(self, data):
        """Pass any received data to the list of AdminPorts."""
        print "DR: Data: ***%s***" % data
        if data=="":
            print "No data here"
        else:
            result=self.get_params(data)
            if result != 0:
                self.process_params(result)
            
                
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

#class TelnetFactory(protocol.clientFactory):
    #"""Factory to create Telnet interface to Flightgear protocol instances, an instanced SerialPort must be passed in."""
    #protocol = EchoClient
     
    #def clientConnectionFailed(self, connector, reason):
        #print "Connection failed - goodbye!"
        #reactor.stop()
     
    #def clientConnectionLost(self, connector, reason):
        #print "Connection lost - goodbye!"
        #reactor.stop()
 
    #def __init__(self, serial):
        #self.serial = serial


"""
Create a TCP server connection and pass data from it to the
serial port."""
class FGFSPort(protocol.Protocol):

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
            
 


class FGFS_OUT(DatagramProtocol):
    """ This is the side where the data is sent from the flight simulator.

    It is connected to port 6001.  
    """

    """
    Data chunk order
        Gear/position_norm
        Gear[1]/position_norm
        Gear[2]/position_norm
        Engine/running
        
    """

    def __init__(self, serial):
        self.data_chunks_label={}
        self.data_chunks_label[0] = "gear/postion-norm"
        self.data_chunks_label[1] = "gear[1]/postion-norm"
        self.data_chunks_label[2] = "gear[2]/postion-norm"
        self.data_chunks_label[3] = "engine/running"
        self.data_chunks_label[4] = "engine/mp-osi"
        self.data_chunks_label[5] = "engine[1]/mp-osi"
        
        self.serial=serial
        print self.data_chunks_label
        self.gear_pos= ("","","")
        self.engine_running=("")
        #self.gear_pos[0]=""
        self.data_chunks_vals={}
        for i in range(len(self.data_chunks_label)):
            self.data_chunks_vals[self.data_chunks_label[i]] =""

        print "DEBUG: ", self.data_chunks_vals 
        
        
    def datagramReceived(self, data, (host, port)):
        #print "received %r from %s:%d" % (data, host, port)
        #self.transport.write(data, (host, port))
        data=data.strip()
        data_chunks=data.split("\t")

        print "DEBUG: [dR] Data Chunks:", data_chunks
        #sys.exit()

        for i in range(len(self.data_chunks_label)):
            #print self.data_chunks_label[i], data_chunks[i] #, data_chunks[1], data_chunks[2],data_chunks[3]
            old_val=self.data_chunks_vals[self.data_chunks_label[i]]
            if ( old_val =="" or old_val != data_chunks[i]):
                self.data_chunks_vals[self.data_chunks_label[i]]= data_chunks[i]

                print "VALUE CHANGED!: [%d]" % (i), self.data_chunks_label[i], ":", old_val, "->", self.data_chunks_vals[self.data_chunks_label[i]]
                if (i==3):
                    mesg="(pin10 %s);" %  self.data_chunks_vals[self.data_chunks_label[i]]
                    self.serial.write(mesg)

                value= self.data_chunks_vals[self.data_chunks_label[i]]
                value=value.strip()
                if (i==4):
                    print "DEBUG: [dR] Value:", value
                    if (value>="40"):
                        mesg="(pin7 1);" #%  self.data_chunks_vals[self.data_chunks_label[i]]
                        print "DEBUG: Mesg: ", mesg
                        self.serial.write(mesg)
                    else:
                        self.serial.write("(pin7 0);")
                        
                if (i==5):
                    if (value>="40"):
                        mesg="(pin8 1);" #%  self.data_chunks_vals[self.data_chunks_label[i]]
                        print "DEBUG: [dR] Mesg: ", mesg
                        self.serial.write(mesg)
                    else:
                        mesg="(pin8 0);"
                        print "DEBUG: Mesg: ", mesg
                        self.serial.write(mesg)

            #self.transport.write()
            #sys.exit()
    

class FGFS_IN(DatagramProtocol):
    """ This sections needs to be written.

    The output protocol xml file needs to be written... to define the properties.
    
    # Properties used:-
        TO BE DONE
    """
    def __init__(self, serial):

        self.data_chunks_label = [
                    "engine/thottle",
                    "engine[1]/thottle",
                    "engine/fuel-condition",
                    "engine[1]/fuel-condition",
                    "/controls/gear"
                ]

        self.serial=serial
        print "DEBUG: FGOUT: ", self.data_chunks_label
        self.gear_pos= ("", "", "")
        self.engine_running=("")
        #self.gear_pos[0]=""
        self.data_chunks_vals={}
        for i in range(len(self.data_chunks_label)):
            self.data_chunks_vals[self.data_chunks_label[i]] =""

        #print "DEBUG: ", self.data_chunks_vals 

    def startProtocol(self):
        #self.serial.fg_host=hostname
        #self.serial.fg_port=port

        self.serial.fg_instance=self
        self.host="192.168.1.100"
        self.port=6001
        self.transport.connect(self.host, self.port)
        pass #Is this required???

    def endProtocol(self):
        self.serial.fg_host=""
        self.serial.fg_port=""

        self.serial.fg_instance=None
        pass #is this required??
        
    def datagramReceived(self, data, (host, port)):
        print "received %r from %s:%d" % (data, host, port)
        #self.transport.write(data, (host, port))
        
        #self.serial.fg_host=hostname
        #self.serial.fg_port=port
        #self.serial.fg_instance=self


        """
        data_chunks=data.split("\t")

        for i in range(len(self.data_chunks_label)):
            #print self.data_chunks_label[i], data_chunks[i] #, data_chunks[1], data_chunks[2],data_chunks[3]
            old_val=self.data_chunks_vals[self.data_chunks_label[i]]
            if ( old_val =="" or old_val != data_chunks[i]):
                self.data_chunks_vals[self.data_chunks_label[i]]= data_chunks[i]

                print "VALUE CHANGED!:", self.data_chunks_label[i], ":", old_val, "->", self.data_chunks_vals[self.data_chunks_label[i]].strip()
                if (i==3):
                    mesg="(pin11 %s);" %  self.data_chunks_vals[self.data_chunks_label[i]]
                    print "DEBUG: Mesg: ", mesg
                    self.serial.write(mesg)
                #if (i==

        """

    def write(self, data):
        print data

def usage(text=None):
    print sys.stderr, """Syntax: %s [options]\n%s""" % (sys.argv[0], __doc__)
    print sys.stderr, "Uses tty /dev/arduino with baudrate of 38400 and opens port 1234"
    if text:
        print >>sys.stderr, text

def main():
    """Parse the command line and run the UI"""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:b:t",
            ["help", "port=", "baud=", "tcp="])
    except getopt.GetoptError, e:
        usage(e)
        sys.exit(2)
        
    tty_port = '/dev/arduino'
    baudrate = 38400
    udp_port = 6000
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

    try:
        serial_port = Serialport(reactor, tty_port, baudrate, log_name)
    except serial.SerialException:
        print "Serial port not found... Please check connections and try again"
    else:
        #admin_port_factory = AdminPortFactory(serial_port, log_name)
        #fgfs_port_factory = FGFSPortFactory(serial_port, log_name)

        #telnet_factory=TelnetFactory(serial_port)

        #reactor.connectTCP("localhost", 5500, telnet_factory)
        #reactor.listenUDP(6000, FGFS_INFactory(serial_port))
        
        #The flightgear Generic protocol requires half duplex port for transferring data,
        #   otherwise you need to have the same number of data fields being send in both directions. :-/
        #  Direction below is from the perspective of Flightgear.
        #  Note: UDP doesn't require a factory...
        reactor.listenUDP(udp_port, FGFS_OUT(serial_port) )
        reactor.listenUDP((udp_port+1), FGFS_IN(serial_port) )
        #reactor.listenTCP(tcp_port, admin_port_factory)
        #reactor.listenTCP(5555, fgfs_port_factory)
        
        print "Listening to Flightgear UDP port(OUT: %d IN: %d) and 5555" % ( udp_port, udp_port+1 )

        reactor.run()

if __name__ == "__main__":
    main()
