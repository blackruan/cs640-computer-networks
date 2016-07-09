### CS640 Computer Networks Lab 2

This project is to create the "brains" for a fully functional Internet IPv4 router.  The basic functions of an Internet router are to:

1. Respond to ARP (address resolution protocol) requests for addresses that are assigned to interfaces on the router.  (Remember that the purpose of ARP is to obtain the Ethernet MAC address associated with an IP address so that an Ethernet frame can be sent to another host over the link layer.)
2. Make ARP requests for IP addresses that have no known Ethernet MAC address.  A router will often have to send packets to other hosts, and needs Ethernet MAC addresses to do so.
3. Receive and forward packets that arrive on links and are destined to other hosts.  Part of the forwarding process is to perform address lookups ("longest prefix match" lookups) in the forwarding information base.  We will eventually just use "static" routing in our router, rather than implement a dynamic routing protocol like RIP or OSPF.
4. Respond to ICMP messages like echo requests ("pings").
5. Generate ICMP error messages when necessary, such as when an IP packet's TTL (time to live) value has been decremented to zero.

The goal of this router project is to accomplish items 1, 2 and 3 above.

Refer to the [router1](https://github.com/jsommers/switchyard/blob/master/examples/exercises/router/router1.rst) and [router2](https://github.com/jsommers/switchyard/blob/master/examples/exercises/router/router2.rst) on the [Switchyard Git Repository](https://github.com/jsommers/switchyard).
