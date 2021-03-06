#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Copyright © 2009, 2010 George Patterson All Rights"""
# Released under GPLv3
 
"""Code acts as glue code to translate data from a flight control system
    to FlightGear.
    
    options:
    -h, --help:     this help
    -H, --host:     hostname of the simulator machine
    -p, --port=PORT: port, a number, default = /dev/arduino or can use
                        a numeric value or a device name such as /dev/ttyUSB0
    -b, --baud=BAUD: baudrate, default 38400
    -t, --tcp=PORT: TCP port number, (admin) default 1234 (Not Implemented)
"""
# Operating Parameters:
# TO DO: Re-write this as the server is now mostly UDP connections!
#   - Entire server needs to be shutdown when changing planes in Flightgear.
#      This is because it's necessary to create flightgear as a server
#      as well as a client. Might be other ways to write this stuff.
#       - Negated after moving to UDP rather than TCP. (Not 100% sure though)
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

import geoResolve

import serial #get the serial constants
import gc
import sys
import getopt
try: 
  from FlightGear import FlightGear
except ImportError:
    print "No FlightGear module found. Continuing without it."
    #Will add personal website when it is ready...
    print "See http://www.flightgear.org for details"
from readlisp import *
from serial import Serial
import time

#hostaddress="192.168.1.100"
hostadress="127.0.0.1"


# FIXME set serial buffer size? SEND_LIMIT

class Serialport(protocol.Protocol):
    """Create a serial port connection and pass data from it to a
    known list of TCP ports."""
    
    def __init__(self, port, reactor, baudrate, hostname="localhost"):
        #LATER: self.admintcp_ports = []
        
        # the following commented out four lines of code might be 
        #   better being moved to the FGFS thread to run when the 
        #   udp packets are first received
        #from FlightGear import FlightGear
        #from readlisp import *
        #self.fg = FlightGear(hostname, 5500)
        #print "DEBUG: FG:", self.fg["/sim/aero"]
        
        self.fgfstcp_ports = []
        self.fg_host= None
        self.fg_port= None
        self.fg_instance= None
        self.state=0

        try:
           self.serial = SerialPort(self, reactor, port, baudrate)
        except serial.SerialException, reason:
            print reason
            print "Error: Arduino interface not found.\n"
            print "Please ensure that the FG Console is plugged into a working USB port and try running this program again.\n"
            print "The other possibibiliy is that the device name is not /dev/arduino. Please see documentation for details.\n"
            sys.exit(1)
        
        self.serial.registerProducer(self, True)
        self.serial_buffer=""
        self.paused = False
        self.log = None

        self.serial.write("(reset);");
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
        #print "SW: write data: %s:%d" % (data.strip(), len_data)
        if self.log:
            self.log.write(data)
        self.serial.write(data)


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

    def get_params(self, data):
        #params=get_params(data)
        
        len_data=len(data)
        print "SDR: write data: %s:%d" % (data, len_data)
        
        self.serial_buffer+=data
        print "SDR: buffer: %s" % (self.serial_buffer.strip())


        #remove possible serial test code from the data stream.

        stripBuffer=['(init)','(time out error)', '(read jackpot)',
                    '(error overflow)', '(unknown command)',
                    '\n', '\r'
                ]
        for term in stripBuffer:
            self.serial_buffer=self.serial_buffer.replace(term,"")

        #self.serial_buffer=self.serial_buffer.replace("(init)","")
        #self.serial_buffer=self.serial_buffer.replace("(time out error)", "")
        #self.serial_buffer=self.serial_buffer.replace("(read jackpot)", "")
        #self.serial_buffer=self.serial_buffer.replace("(error overflow)", "")
        #self.serial_buffer=self.serial_buffer.replace("(unknown command)", "")
        #self.serial_buffer=self.serial_buffer.replace("\n", "")
        #self.serial_buffer=self.serial_buffer.replace("\r", "")


        semi_pos=self.serial_buffer.find(";") # Our S-Expression are sent with a semi-colon(;) teminating the string
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
            process_pin=False
            
            for i in range(1, len(params)):
                if len(params[i])==2:
                    param=str(params[i][0])
                    val=params[i][1]
                    print "DEBUG: SPP Param: ***%s*** Val: %s" % (param, str(val))
                    
                    cmd=""
                    control_pos=""
                    if param[:3] == "adc":
                        if param=="adc1":
                            cmd="engine/throttle"
                            control_pos= (val-1)/1023.0
                            process_pin=True
                        elif str(param).strip()=="adc2":
                            cmd="engine[1]/throttle"
                            control_pos= (val-1)/1023.0
                            process_pin=True

                        elif str(param).strip()=="adc3":
                            cmd="engine/mixture"
                            control_pos= (val-1)/1023.0
                            process_pin=True
                        elif str(param).strip()=="adc4":
                            cmd="engine[1]/mixture"
                            control_pos= (val-1)/1023.0
                            process_pin=True
                        #elif str(param).strip() == "pin2":

                        #print "DEBUG: SPP Cmd: %s val: %f" % (cmd, control_pos)
                        #self.transport.write('Help ME!', (self.fg_host, self.fg_port))

                        if self.fg_instance != None:
                            #print "DEBUG: PP[ADC]: We have a transport instance"
                            
                            self.fg_instance.data_field_vals[cmd]=control_pos    
                        
                        try:
                            self.fg[cmd]=float(val)/1023.0
                        #except exceptions.AttributeError:
                        except AttributeError:
                            pass #do nothing
                    
                    if param[:3] == "pin":
                        pinNo=param[3:]
                        
                        if pinNo == "1":
                            print "DEBUG: Pin1 has been toggled... No Operation taken..."
                            #print "ERROR: Shouldn't be here"
                            #mesg="(pin7 %d);" % val
                            #print "DEBUG: Mesg: ", mesg
                            #self.serial.write(mesg);
                            #self.serial.write("(gear 1);");
                        elif pinNo == "2":
                            print "DEBUG: Pin2 has been toggled... No Operation taken..."
                            #mesg="(pin8 %d);" % val
                            #print "DEBUG: Mesg: ", mesg  
                            #self.serial.write(mesg)
                            #mesg="(pin9 %d);" % val
                            #print "DEBUG: Mesg: ", mesg  
                            #self.serial.write(mesg)

                        elif pinNo == "3":
                            cmd="controls/gear"
                            
                            if val==0:
                                control_pos=0
                            else: 
                                control_pos=1

                            #mesg="(pin7=%d);" % (control_pos)
                            mesg="(pin8=%d);" % (control_pos)
                            #mesg="(pin9=%d);" % (control_pos)
                            #mesg="(pin10=%d);" % (control_pos)

                            self.write(mesg)
                            
                            process_pin=True
                            #mesg="(pin11 %d);" % val
                            #print "SPP: DEBUG: Mesg: ", mesg  
                            #self.serial.write(mesg)
                            #print "DEBUG: Pin3 has been toggled... No Operation taken..."
                            #time.sleep(0.001)

                        if self.fg_instance != None and process_pin:
                            print "DEBUG: PP[PIN]: We have a transport instance" 

                            self.fg_instance.data_field_vals[cmd]=control_pos    

                    #try:
                    #    self.fg[cmd]=control_pos
                    #    #except exceptions.AttributeError:
                    #except AttributeError:
                    #    pass #do nothing
            #print "DEBUG: GRP: ", self.fg_instance.data_field_vals
            #print "DEBUG: GRP: ", self.fg_instance.data_fields_vals
            cmd=""
            if (self.fg_instance is None):
                print "FG Instance is not declared!!"
            else:
                for var in self.fg_instance.data_fields_label:
                    #print 'DEBUG: var:', var , "field ", self.fg_instance.data_field_vals[var]
                    cmd +=str(self.fg_instance.data_field_vals[var]) +"\t"

                cmd = cmd.strip()
                cmd=cmd + "\n"
                if process_pin is True:
                    #print 'DEBUG: cmd strip:', cmd
                    self.fg_instance.transport.write(cmd)
                


    def dataReceived(self, data):
        """Pass any received data to the list of AdminPorts."""
        #print "DR: Data: ***%s***" % data
        if data=="":
            print "No data here"
        else:
            result=self.get_params(data)
            #print "DEBUG: Result:", result
            if result != 0:
                self.process_params(result)            
                
                #for tcp_port in self.admintcp_ports:
                #    tcp_port.write(data)
                for tcp_port in self.fgfstcp_ports:
                    tcp_port.write(data)
                

class AdminPort(protocol.Protocol):
    """Create a TCP server connection and pass data from it to the
    serial port."""

    def __init__(self, serial, index):
        """Add this AdminPort to the SerialPort."""
        self.serial = serial
        self.serial.add_admintcp(self)
        self.log = None


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

    def __init__(self, serial):
        self.serial = serial
        self.index = 0

    def buildProtocol(self, addr):
        """Build a AdminPort, passing in the instanced SerialPort."""
        p = AdminPort(self.serial, self.index)
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
Create a UDP server connection and pass data from it to the
serial port."""
class FGFSPort(protocol.Protocol):
    def __init__(self, serial, index):
        #Expected number of chunks... May not be used.
        self.num_of_chunks=3
        self.old_chunks= {}
        self.fgfs_params=["gear", "altitude", "landing-pos"]
        
        """Add this AdminPort to the SerialPort."""
        self.serial = serial
        self.serial.add_fgfstcp(self)
        self.log = None
        

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

    def __init__(self, serial, hostname):
        self.data_fields_label={}
        
        self.data_fields_label[0] = "gear/postion-norm"
        self.data_fields_label[1] = "gear[1]/postion-norm"
        self.data_fields_label[2] = "gear[2]/postion-norm"
        self.data_fields_label[3] = "engine/running"
        self.data_fields_label[4] = "engine/mp-osi"
        self.data_fields_label[5] = "engine[1]/mp-osi"
        
        self.serial=serial
        print "DEBUG: ",self.data_fields_label
        self.gear_pos= ("","","")
        self.engine_running=("")
        #self.gear_pos[0]=""
        self.data_chunks_vals={}
        for i in range(len(self.data_fields_label)):
            self.data_chunks_vals[self.data_fields_label[i]] =""

        #print "DEBUG: FGOUT Data Fields", self.data_chunks_vals 
        
        
    def datagramReceived(self, data, (host, port)):
        #print "received %r from %s:%d" % (data, host, port)
        #self.transport.write(data, (host, port))
        data=data.strip()
        data_chunks=data.split("\t")

        print "DEBUG: [dR] Data Chunks:", data_chunks
        #sys.exit()

        for i in range(len(self.data_fields_label)):
            #print self.data_chunks_label[i], data_chunks[i] #, data_chunks[1], data_chunks[2],data_chunks[3]
            old_val=self.data_chunks_vals[self.data_fields_label[i]]
            if ( old_val =="" or old_val != data_chunks[i]):
                self.data_chunks_vals[self.data_fields_label[i]]= data_chunks[i]

                #print "VALUE CHANGED!: [%d]" % (i), self.data_fields_label[i], ":", old_val, "->", self.data_chunks_vals[self.data_fields_label[i]]
                if (i==3):
                    mesg="(pin10=%s);" %  self.data_chunks_vals[self.data_fields_label[i]]
                    self.serial.write(mesg)

                value= self.data_chunks_vals[self.data_fields_label[i]]
                value=value.strip()
                if (i==4):
                    #print "DEBUG: [dR] Value:", value
                    if (value>="40"):
                        pin_val=1
                    else:
                        pin_val=0
                        
                    mesg="(pin7=%d);" % (pin_val) #%  self.data_chunks_vals[self.data_chunks_label[i]]
                    print "DEBUG: Mesg: ", mesg
                    self.serial.write(mesg)
                    #else:
                    #    self.serial.write("(pin7 0);")
                        
                if (i==5):
                    if (value>="40"):
                        mesg="(pin8=1);" #%  self.data_chunks_vals[self.data_chunks_label[i]]
                        #print "DEBUG: [dR] Mesg: ", mesg
                        self.serial.write(mesg)
                    else:
                        mesg="(pin8=0);"
                        #print "DEBUG: Mesg: ", mesg
                        self.serial.write(mesg)

            #self.transport.write()
            #sys.exit()
    

class FGFS_IN(DatagramProtocol):
    """ This sections needs to be written.

    The output protocol xml file needs to be written... to define the properties.
    
    # Properties used:-
        TO BE DONE
    """
    def __init__(self, serial, hostname):
        self.host=hostname
        self.port=6001

        self.data_fields_label = [
                "engine/throttle",
                "engine[1]/throttle",
                "engine/mixture",
                "engine[1]/mixture",
                "controls/gear"
            ]

        self.serial=serial
        print "DEBUG: FGIN Data Fields:", self.data_fields_label
        #self.gear_pos= ("", "", "")
        self.engine_running=("")
        #self.gear_pos[0]=""
        self.data_field_vals={}
        self.temp=""
        
        for i in range(len(self.data_fields_label)):
            self.data_field_vals[self.data_fields_label[i]] =""

        print "DEBUG: FGIN Data Field Values:", self.data_field_vals 

    def startProtocol(self):
        #self.serial.fg_host=hostname
        #self.serial.fg_port=port

        self.serial.fg_instance=self
        #self.host="192.168.1.100"
        #self.host=hostname
        self.port=6001
        self.transport.connect(self.host, self.port)
        print "DEBUG: HOST: ", self.host
        pass 

    def endProtocol(self):
        self.serial.fg_host=""
        self.serial.fg_port=""

        self.serial.fg_instance=None
        pass #is this required??
        
    def datagramReceived(self, data, (host, port)):
        print "sent %r to %s:%d" % (data, host, port)

        #if self.temp != data or self.temp=="":
        #    self.transport.write(data, (host, port))
        #    self.temp=data
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
        print "Data:", data

""" Display the usage parameters 
"""
def usage(text=None):
    print sys.stderr, """Syntax: %s [options]\n%s""" % (sys.argv[0], __doc__)
    #print sys.stderr, "Uses tty /dev/arduino with baudrate of 38400 and opens port 6000"
    if text:
        print >>sys.stderr, text

def main():
    """Parse the command line and run the UI"""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:b:tH:",
            [ "help", "port=", "baud=", "tcp=", "host=" ])
    except getopt.GetoptError, e:
        usage(e)
        sys.exit(2)
        
    tty_port = '/dev/arduino'
    baudrate = 38400
    udp_port = 6000
    hostaddress="127.0.0.1"

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(1)
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
        elif o in ("-H", "--host"):
            # Should check that the hostname is resolvable and that the ip address is pingable.
            #       Do not assume that the port is open by connecting to it directly.
            hostname = a
            if geoResolve.ipFormatChk(hostname) is False: #possible host name was passed instead...
                hostaddress= geoResolve.resolveAddress(hostname)
                print "Host Address: ", hostaddress 

        elif o in ("-t", "--tcp"):
            try:
                tcp_port = int(a)
            except ValueError:
                usage("Bad TCP port %r" % a)

    try:
        serial_port = Serialport(reactor, tty_port, baudrate)
    except serial.SerialException:
        print "Serial port not found... Please check connections and try again"
    else:
        #admin_port_factory = AdminPortFactory(serial_port)
        #fgfs_port_factory = FGFSPortFactory(serial_port)

        #telnet_factory=TelnetFactory(serial_port)
        #reactor.connectTCP("localhost", 5500, telnet_factory)
        #reactor.listenUDP(6000, FGFS_INFactory(serial_port))
        
        #The flightgear Generic protocol requires half duplex port for transferring data,
        #   otherwise you need to have the same number of data fields being send in both directions. :-/
        #  Direction below is from the perspective of Flightgear.
        #  Note: UDP doesn't require a factory...
        #reactor.listenUDP(udp_port, FGFS_OUT(serial_port, hostaddress) )
        #reactor.listenUDP((udp_port+1), FGFS_IN(serial_port, "127.0.0.1") )
        #reactor.listenUDP(0, FGFS_IN(serial_port, "127.0.0.1") )
        #reactor.listenTCP(tcp_port, admin_port_factory)
        
        #reactor.listenTCP(5555, fgfs_port_factory)
        
        print "Listening to Flightgear UDP port(OUT: %d IN: %d) and 5555" % ( udp_port, udp_port+1 )

        reactor.run()

if __name__ == "__main__":
    main()
