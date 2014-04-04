import parser
import network_objects

def test(**kwargs):
    net_conf, net_parse = parser.parse_conf(filename='dhcpd.conf', return_parsed=True)
    lease_conf = parser.parse_leases(filename='dhcpd.leases')
    nets = network_objects.build_networks(net_conf)
    leases = network_objects.build_leases(lease_conf)
    return {'PARSED_NETWORKS':net_conf, 
            'PARSED_SECTIONS':net_parse, 
            'PARSED_LEASES':lease_conf, 
            'NETWORKS':nets, 
            'LEASES':leases}
