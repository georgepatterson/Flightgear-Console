#!/usr/bin/env python
#
#       untitled.py
#       
#       Copyright 2010 George Patterson <gpatterson@len01>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.


from FlightGear import FlightGear
import time



def get_node(fg, node="/"):
    root = fg.telnet.ls(node)

    #print root[0]
    node_tree={"foo": "bar"}
    del node_tree["foo"]
    for idx, value in enumerate(root):
        value= "/%s" % (value.strip())
        
        print "DEBUG: Idx: ", idx, "Value:", value
        
        if value[-1:] == "/":
            #branch has been found..
            node_value="%s%s" % (node,value)
            node_value=node_value.replace("//","/")
            branch = get_node(fg, node_value)
            print node_value
        else:
            item_chunks = value.split("=");
            item_name= item_chunks[0].strip()

            #if idx==16:
            #    print "DEBUG: Idx: ", idx, "Value:", value
            #    print "Item chunks: ", item_chunks

            
            item_vals = item_chunks[1].split("\t");
            if idx==16:
                print "Item Vals: ", item_vals
                
            
            item_data_value = item_vals[1]
            item_data_type=item_vals[2]
            #print item_name, item_value
            node_item_name="%s%s" % (node, item_name)
            node_item_name=node_item_name.replace("//", "/")
            print "DEBUG: Node item name: %s Data Value : %s Data Type: %s" % (node_item_name, item_data_value,item_data_type)     

            node_tree = {node_item_name: (item_data_value,item_data_type) }

    print node_tree
    #return node_tree        

def main():
    fg = FlightGear('127.0.0.1', 5500)

    # Wait five seconds for simulator to settle down
    while 1:
        if fg['/sim/time/elapsed-sec'] > 5:
            break
        time.sleep(1.0)
        
    get_node(fg, "/controls")

    """
    For each branch,
        get details of the branch.
    
    """


    fg.quit()

if __name__ == '__main__':
    main()
