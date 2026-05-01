# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/8/4 21:18
@Function: 
@version :  1.0
@Desc    :  None
"""
from ipaddress import ip_network, ip_address


def get_available_ips(start_ip, end_ip, cidr):
    """
    :param start_ip: 192.168.1.1
    :param end_ip: 192.168.1.100
    :param cidr: 192.168.1.0/24
    :return:
    """
    subnet = ip_network(cidr)
    start_ip = ip_address(start_ip)
    end_ip = ip_address(end_ip)
    all_hosts = list(subnet.hosts())
    available_ips_in_range = [ip for ip in all_hosts if start_ip <= ip <= end_ip]
    data = {
        "all_count": len(all_hosts),
        "available_count": len(available_ips_in_range),
        "available_ips": [str(i) for i in available_ips_in_range],
        "all_ips": [str(i) for i in all_hosts]
    }
    return data
