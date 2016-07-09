#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time
from switchyard.lib.packet import *
from switchyard.lib.address import *
from switchyard.lib.common import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.my_interfaces= self.net.interfaces()
        self.my_ipaddr= [intf.ipaddr for intf in self.my_interfaces]
        self.ip_eth_map= {}
        self.wait_queue= {}
        self.delimiter= " "
        file_path = os.path.split(os.path.abspath(__file__))[0]
        #file_path= "./"
        #file_path= "examples/exercises/router/"
        self.ft_name= file_path + "/forwarding_table.txt"
        # build forwarding table from text file
        # only if text file is in the same directory
        # else throw error and exit
        if os.path.isfile(self.ft_name):
            self.forward_table= self.__loadForwardTable()
        else:
            print ("error: forwarding_table.txt is not found (in the same directory)")
            sys.exit(-1)
        # build forwarding table from net.interfaces
        for intf in self.my_interfaces:
            prefix = int(intf.ipaddr) & int(intf.netmask)
            self.forward_table.append([IPv4Address(prefix),intf.netmask,None,intf.name])

    # utility function to build forwarding table from text file 
    def __loadForwardTable(self):
        ft= []
        # read the content from the text file
        with open(self.ft_name,'r') as f:
            raw_ft= f.readlines()
        # create the forwarding table
        for r in raw_ft:
            if r.strip() != "":
                entry= r.strip().split(self.delimiter)
                ft.append([IPv4Address(entry[0]),IPv4Address(entry[1]),IPv4Address(entry[2]),entry[3]])
        return ft
    
    # utility function that examines the elements in waiting queue
    # check if number of ARP requests reaches the max limit 
    # send ARP request if max limit is not reached
    # drop packet otherwise
    def __checkWaitQueue(self): 
        del_cand = []
        for key in self.wait_queue:
            if time.time() - self.wait_queue[key][1] >= 1.0:
                if self.wait_queue[key][2] >= 5:
                    del_cand.append(key)
                else:
                    out_port = self.wait_queue[key][3]
                    senderhwaddr= self.net.interface_by_name(out_port).ethaddr
                    senderprotoaddr= self.net.interface_by_name(out_port).ipaddr
                    targetprotoaddr= key
                    self.net.send_packet(out_port,create_ip_arp_request(senderhwaddr, \
                            senderprotoaddr, targetprotoaddr))
                    self.wait_queue[key][1] = time.time()
                    self.wait_queue[key][2] += 1
        for entry in del_cand:
            del self.wait_queue[entry]

    # router_main
    def router_main(self):    
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            gotpkt = True
            try:
                dev,pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if not gotpkt:
                self.__checkWaitQueue()
            else:
                log_debug("Got a packet: {}".format(str(pkt)))
                # try to get ARP header
                arp= pkt.get_header(Arp)
                # check if ARP exists
                if arp:
                    # check if request ARP
                    if arp.operation == ArpOperation.Request:
                        # store IP/Ethernet MAC pairs
                        self.ip_eth_map[arp.senderprotoaddr]= arp.senderhwaddr
                        if arp.targetprotoaddr in self.my_ipaddr:
                            # get the Ethernet MAC address from the destinatiion IP address 
                            # and set it as the sender Ethernet MAC address
                            senderhwaddr= self.net.interface_by_ipaddr(arp.targetprotoaddr).ethaddr
                            targethwaddr= arp.senderhwaddr
                            senderprotoaddr= arp.targetprotoaddr
                            targetprotoaddr= arp.senderprotoaddr
                            self.net.send_packet(dev,create_ip_arp_reply(senderhwaddr,targethwaddr, \
                                                               senderprotoaddr,targetprotoaddr))
                    else:
                        # store the Ethernet MAC and IP address pair
                        # send the reply pkt if the sender is in waiting queue
                        self.ip_eth_map[arp.senderprotoaddr]= arp.senderhwaddr
                        if arp.senderprotoaddr in self.wait_queue:
                            out_port = self.wait_queue[arp.senderprotoaddr][3]
                            for p in self.wait_queue[arp.senderprotoaddr][0]:
                                if not p.get_header(Ethernet):
                                    p+= Ethernet()
                                p[Ethernet].src = self.net.interface_by_name(out_port).ethaddr
                                p[Ethernet].dst = arp.senderhwaddr
                                self.net.send_packet(out_port,p)
                            del self.wait_queue[arp.senderprotoaddr]
                
                # check the waiting queue    
                self.__checkWaitQueue()
                
                # get IP header
                ip = pkt.get_header(IPv4)
                if ip:
                    # drop if destination is one of the ipaddrs of router
                    if ip.dst in self.my_ipaddr: 
                        continue
                    # find the longest prefix
                    which_rt= None
                    max_prefix= 0
                    for f in self.forward_table:
                        netaddr= IPv4Network(str(f[0])+'/'+str(f[1]))
                        if ip.dst in netaddr:
                            prefix_len= netaddr.prefixlen
                            if prefix_len > max_prefix:
                                which_rt= f
                                max_prefix = prefix_len

                    # drop if no matching in the forward table
                    if which_rt is None:
                        continue
                    # decrement TTL by 1
                    ip.ttl -= 1
                    # find next hop
                    next_hop_ip = None
                    if which_rt[2]:
                        next_hop_ip = which_rt[2]
                    else:
                        next_hop_ip = ip.dst
                    # send pkt right away if ethaddr is already known in ARP table
                    if next_hop_ip in self.ip_eth_map:
                        if not pkt.get_header(Ethernet):
                            pkt+= Ethernet()
                        pkt[Ethernet].src = self.net.interface_by_name(which_rt[3]).ethaddr
                        pkt[Ethernet].dst = self.ip_eth_map[next_hop_ip]
                        self.net.send_packet(which_rt[3],pkt)
                    else:
                        # if ARP request of this ipaddr is already sent, put pkt into queue directly
                        if next_hop_ip in self.wait_queue:
                            self.wait_queue[next_hop_ip][0].append(pkt)
                        # send ARP request, put pkt into queue after sending
                        else:
                            senderhwaddr= self.net.interface_by_name(which_rt[3]).ethaddr
                            senderprotoaddr= self.net.interface_by_name(which_rt[3]).ipaddr
                            targetprotoaddr= next_hop_ip
                            self.net.send_packet(which_rt[3],create_ip_arp_request(senderhwaddr, \
                                    senderprotoaddr, targetprotoaddr))
                            # add a new entry to the wait queue in the below format:
                            # [[pkt list], most recent request time, num of retries, outport (name)]
                            self.wait_queue[next_hop_ip] = [[pkt], time.time(), 1.0, which_rt[3]]


def switchy_main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
