#!/usr/bin/env python

import copy
from switchyard.lib.testing import *
from switchyard.lib.packet import *
from switchyard.lib.common import *
from switchyard.lib.address import *

def mk_arpresp(arpreqpkt, hwsrc, arphwsrc=None, arphwdst=None):
    # hwdst (hwsrc), ipsrc (ipdst), ipdst (ipsrc) come from arpreq

    if arphwsrc is None:
        arphwsrc = hwsrc
    if arphwdst is None:
        arphwdst = arpreqpkt.get_header(Arp).senderhwaddr
    ether = Ethernet()
    ether.src = EthAddr(hwsrc)
    ether.dst = arpreqpkt.get_header(Arp).senderhwaddr
    ether.ethertype = EtherType.ARP
    arp_reply = Arp()
    arp_reply.operation = ArpOperation.Reply
    arp_reply.senderprotoaddr = IPAddr(arpreqpkt.get_header(Arp).targetprotoaddr)
    arp_reply.targetprotoaddr = IPAddr(arpreqpkt.get_header(Arp).senderprotoaddr)
    arp_reply.senderhwaddr = EthAddr(arphwsrc)
    arp_reply.targethwaddr = EthAddr(arphwdst)
    return ether + arp_reply


def mk_ping(hwsrc, hwdst, ipsrc, ipdst, reply=False, ttl=64, payload=''):
    ether = Ethernet()
    ether.src = EthAddr(hwsrc)
    ether.dst = EthAddr(hwdst)
    ether.ethertype = EtherType.IP
    ippkt = IPv4()
    ippkt.srcip = IPAddr(ipsrc)
    ippkt.dstip = IPAddr(ipdst)
    ippkt.protocol = IPProtocol.ICMP
    ippkt.ttl = ttl
    ippkt.ipid = 0
    if reply:
        icmppkt = ICMP()
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt = ICMP()
        icmppkt.icmptype = ICMPType.EchoRequest
    icmppkt.icmpdata.sequence = 42
    icmppkt.icmpdata.data = payload
    return ether + ippkt + icmppkt 

def forwarding_arp_tests():
    s = Scenario("IP forwarding and ARP requester tests")
    s.add_interface('router-eth0', '10:00:00:00:00:01', '192.168.1.1', '255.255.255.0')
    s.add_interface('router-eth1', '10:00:00:00:00:02', '10.10.0.1', '255.255.0.0')
    s.add_interface('router-eth2', '10:00:00:00:00:03', '172.16.42.1', '255.255.255.252')
    s.add_file('forwarding_table.txt', '''172.16.0.0 255.255.0.0 192.168.1.2 router-eth0
172.16.128.0 255.255.192.0 10.10.0.254 router-eth1
172.16.64.0 255.255.192.0 10.10.1.254 router-eth1
10.100.0.0 255.255.0.0 172.16.42.2 router-eth2''')

    reqpkt = mk_ping("20:00:00:00:00:01", "10:00:00:00:00:01", '192.168.1.100','172.16.42.2', ttl=64)
    reqpkt2 = copy.deepcopy(reqpkt)
    reqpkt2.get_header(Ethernet).src = EthAddr("10:00:00:00:00:03")
    reqpkt2.get_header(Ethernet).dst = EthAddr("30:00:00:00:00:01")

    arpreq = create_ip_arp_request("10:00:00:00:00:03", "172.16.42.1", "172.16.42.2")
    arpresp = mk_arpresp(arpreq, "30:00:00:00:00:01") # , "10:00:00:00:00:03", "172.16.42.2", "172.16.42.1")

    arpreq2 = create_ip_arp_request("10:00:00:00:00:01", "192.168.1.1", "192.168.1.100")
    arpresp2 = mk_arpresp(arpreq2, "20:00:00:00:00:01") # , "10:00:00:00:00:01", "192.168.1.100", "192.168.1.1")

    resppkt = mk_ping("30:00:00:00:00:01", "10:00:00:00:00:03", '172.16.42.2', '192.168.1.100', reply=True, ttl=64)
    resppkt2 = copy.deepcopy(resppkt)
    resppkt2.get_header(Ethernet).src = EthAddr("10:00:00:00:00:01")
    resppkt2.get_header(Ethernet).dst = EthAddr("20:00:00:00:00:01")

    # arp for router-eth0 IP addr
    arpreq3 = create_ip_arp_request("30:00:00:00:00:01", "192.168.1.100", "192.168.1.1")
    arpresp3 = create_ip_arp_reply("10:00:00:00:00:01", "30:00:00:00:00:01", "192.168.1.1", "192.168.1.100")

    # create another reqpkt
    reqpkt4= mk_ping("20:00:00:00:00:01", "10:00:00:00:00:01", '192.168.1.100','172.16.129.2', ttl=64)
    reqpkt5= mk_ping("20:00:00:00:00:02", "10:00:00:00:00:01", '192.168.1.200','172.17.42.2', ttl=64)
    reqpkt6= mk_ping("20:00:00:00:00:01", "10:00:00:00:00:03", '192.168.1.100','2.2.2.2', ttl=64)
    reqpkt7= mk_ping("20:00:00:00:00:03", "10:00:00:00:00:02", '192.168.1.240','10.10.0.1', ttl=64)
    
    # arp for router-eth1 IP addr
    arpreq4 = create_ip_arp_request("10:00:00:00:00:02", "10.10.0.1", "10.10.0.254")
    
    ttlmatcher = '''lambda pkt: pkt.get_header(IPv4).ttl == 63'''

    """
    s.expect(PacketInputEvent("router-eth0", reqpkt, display=IPv4), 
             "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")
    s.expect(PacketOutputEvent("router-eth2", arpreq, display=Arp),
             "Router should send ARP request for 172.16.42.2 out router-eth2 interface")
    s.expect(PacketInputEvent("router-eth2", arpresp, display=Arp),
             "Router should receive ARP response for 172.16.42.2 on router-eth2 interface")
    s.expect(PacketOutputEvent("router-eth2", reqpkt2, display=IPv4, exact=False, predicates=[ttlmatcher]),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    s.expect(PacketInputEvent("router-eth2", resppkt, display=IPv4),
             "IP packet to be forwarded to 192.168.1.100 should arrive on router-eth2")
    s.expect(PacketOutputEvent("router-eth0", arpreq2, display=Arp),
             "Router should send ARP request for 192.168.1.100 out router-eth0")
    s.expect(PacketInputEvent("router-eth0", arpresp2, display=Arp),
             "Router should receive ARP response for 192.168.1.100 on router-eth0")
    s.expect(PacketOutputEvent("router-eth0", resppkt2, display=IPv4, exact=False, predicates=[ttlmatcher]),
             "IP packet should be forwarded to 192.168.1.100 out router-eth0")
    """

    # my test cases
    s.expect(PacketInputEvent("router-eth1", reqpkt7, display=IPv4),
             "IP packet to be forwarded to 10.10.0.1 should arrive on router-eth1")
    s.expect(PacketInputEvent("router-eth0", reqpkt, display=IPv4), 
             "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")
    s.expect(PacketOutputEvent("router-eth2", arpreq, display=Arp),
             "Router should send ARP request for 172.16.42.2 out router-eth2 interface")
    # no arp reply received within 1 second, resend arp request
    s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
    s.expect(PacketOutputEvent("router-eth2", arpreq, display=Arp),
             "Router should send ARP request for 172.16.42.2 out router-eth2 interface")
    # task 1 case: while waiting for arp reply, can deal with other arriving packet
    # note the source address pair is also stored while receiving this packet
    s.expect(PacketInputEvent("router-eth0", arpreq3, display=Arp), "ARP request for 192.168.1.1 should arrive on router-eth0")
    s.expect(PacketOutputEvent("router-eth0", arpresp3, display=Arp), "Router should send ARP response for 192.168.1.1 on router-eth0")
    # no arp reply within 1 second, resend arp request
    s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
    s.expect(PacketOutputEvent("router-eth2", arpreq, display=Arp),
             "Router should send ARP request for 172.16.42.2 out router-eth2 interface")
    # send to a no match destination
    s.expect(PacketInputEvent("router-eth0", reqpkt6, display=IPv4),
             "IP packet to be forwarded to 2.2.2.2 should arrive on router-eth0")
    # if a packet with the same next hop ip address arrives, of which the arp reply has not been received,
    # no identical arp request need to be sent
    s.expect(PacketInputEvent("router-eth0", reqpkt, display=IPv4), 
             "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")
    s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
    # send the arp request according to the timeout of the first packet
    s.expect(PacketOutputEvent("router-eth2", arpreq, display=Arp),
             "Router should send ARP request for 172.16.42.2 out router-eth2 interface")
    s.expect(PacketInputEvent("router-eth2", arpresp, display=Arp),
             "Router should receive ARP response for 172.16.42.2 on router-eth2 interface")
    # send both of the two packets out
    s.expect(PacketOutputEvent("router-eth2", reqpkt2, display=IPv4, exact=False, predicates=[ttlmatcher]),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    s.expect(PacketOutputEvent("router-eth2", reqpkt2, display=IPv4, exact=False, predicates=[ttlmatcher]),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    # send the packet immediately since the mapping is already in the arp table due to the previous
    # operations
    s.expect(PacketInputEvent("router-eth0", reqpkt, display=IPv4), 
             "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")
    s.expect(PacketOutputEvent("router-eth2", reqpkt2, display=IPv4, exact=False, predicates=[ttlmatcher]),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    # send to a no match destination
    s.expect(PacketInputEvent("router-eth1", reqpkt5, display=IPv4),
             "IP packet to be forwarded to 172.17.42.2 should arrive on router-eth1")
    # send to ip 172.16.129.2
    s.expect(PacketInputEvent("router-eth1", reqpkt4, display=IPv4),
             "IP packet to be forwarded to 172.16.129.2 should arrive on router-eth1")
    # send five requests
    s.expect(PacketOutputEvent("router-eth1", arpreq4, display=Arp),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    # loop 4 times
    for i in range(4):
        # wait for 1 second
        s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
        s.expect(PacketOutputEvent("router-eth1", arpreq4, display=Arp),
                 "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    # wait for 1 second
    s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
   
    # send five requests and send the same arp request before the last time out
    s.expect(PacketInputEvent("router-eth1", reqpkt4, display=IPv4),
             "IP packet to be forwarded to 172.16.129.2 should arrive on router-eth1")
    s.expect(PacketOutputEvent("router-eth1", arpreq4, display=Arp),
             "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    # loop 4 times
    for i in range(4):
        # wait for 1 second
        s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
        s.expect(PacketOutputEvent("router-eth1", arpreq4, display=Arp),
                 "IP packet should be forwarded to 172.16.42.2 out router-eth2")
    s.expect(PacketInputEvent("router-eth1", reqpkt4, display=IPv4),
             "IP packet to be forwarded to 172.16.129.2 should arrive on router-eth1")
    # wait for 1 second
    s.expect(PacketInputTimeoutEvent(1.0), "No packet received in 1.0 second")
 
    # send again after 5 trials
    s.expect(PacketInputEvent("router-eth1", reqpkt4, display=IPv4),
             "IP packet to be forwarded to 172.16.129.2 should arrive on router-eth1")
    s.expect(PacketOutputEvent("router-eth1", arpreq4, display=Arp),
             "IP packet should be forwarded to 10.10.0.254 out router-eth1")
    return s

scenario = forwarding_arp_tests()
