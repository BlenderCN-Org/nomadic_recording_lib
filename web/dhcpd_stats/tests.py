import parser
import network_objects

def test():
    net_conf = parser.parse_conf(filename='dhcpd.conf')
    lease_conf = parser.parse_leases(filename='dhcpd.leases')
    nets = network_objects.build_networks(net_conf)
    leases = network_objects.build_leases(lease_conf)
    return {'PARSED_NETWORKS':net_conf, 
            'PARSED_LEASES':lease_conf, 
            'NETWORKS':nets, 
            'LEASES':leases}
