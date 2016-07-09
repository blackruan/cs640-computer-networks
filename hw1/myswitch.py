#!/usr/bin/env python3

'''
Ethernet learning switch in Python: HW3.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.common import *
import time as t

def switchy_main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    forwardTable= {}
    timeTable= {}
    cand= []
    timeout= 30

    while True:
        try:
            dev,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        # reset table entries after timeout
        currentTime= t.time()
        for e in timeTable:
            if currentTime - timeTable[e] >= timeout:
                cand.append(e)
        for e in cand:
            del forwardTable[e]
            del timeTable[e]
        cand= []

        log_debug("In {} received packet {} on {}".format(net.name, packet, dev))
        forwardTable[packet[0].src]= dev
        timeTable[packet[0].src]= t.time()
        if packet[0].dst in mymacs:
            log_debug("Packet intended for me")
        else:
            if packet[0].dst in forwardTable and packet[0].dst != "ff:ff:ff:ff:ff:ff":
                log_debug("Send packet {} to {}".format(packet,forwardTable[packet[0].dst]))
                net.send_packet(forwardTable[packet[0].dst], packet)
            else:
                for intf in my_interfaces:
                    if dev != intf.name:
                        log_debug("Flooding packet {} to {}".format(packet, intf.name))
                        net.send_packet(intf.name, packet)
    net.shutdown()
