import paramiko
import os

zones = {'zone1': ['172.16.3.1', 'linux@1234'],
         'zone2': ['172.16.3.2', 'linux@123']}


def create_ssh_conn(ip, user, pwd):
    '''
    SSH Handler to creat an SSHClient object

    Args:   ip (string)
            user (string)
            pwd (string)

    Returns: client (object) : paramiko client object
    '''
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=pwd)
    return client


def execute_command(ssh_client, command):
    '''
    SSH Handler to execute
    '''
    import time
    alldata = ''
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print('Executed the command')
    alldata = ''.join(stdout.readlines())
    print(stdout.readlines())
    print(stderr.readlines())
    print(alldata)
    while not stdout.channel.exit_status_ready() and not stdout.channel.recv_ready():
        time.sleep(1)
    print('done with the sleeping')
    # alldata = ''.join(stdout.readlines())
    if isinstance(alldata, str):
        # print(alldata)
        return alldata
    # print(alldata)
    return alldata.decode('utf-8')


def close_ssh_conn(ssh_client):
    ssh_client.close()


def get_vm_mac(zone_ip, vmid, network_name):
    import libvirt
    from xml.dom import minidom
    vm_mac = ''
    conn = libvirt.open('qemu+ssh://ece792@{0}/system'.format(zone_ip))
    con = conn.listDomainsID()
    dom = ''
    print(network_name)
    for c in con:
        if vmid == conn.lookupByID(c).name():
            dom = conn.lookupByID(c)
            doc = minidom.parseString(dom.XMLDesc(0))
            for node in doc.getElementsByTagName('devices'):
                i_nodes = node.getElementsByTagName('interface')
                print(i_nodes)
                for i_node in i_nodes:
                    print(i_node.getAttribute('type'))
                    macs = i_node.getElementsByTagName('mac')
                    source = i_node.getElementsByTagName('source')
                    print(macs)
                    print(source)
                    for src in source:
                        net_source = src.getAttribute('network')
                        print(net_source)
                        for mac in macs:
                            vm_mac = mac.getAttribute("address")
                            print('found a mac')
                            print(src.getAttribute('network'))
                            print(vm_mac)
    return vm_mac


def get_vm_ip(zone_ip, vmid):
    import libvirt
    vm_ip = ''
    conn = libvirt.open('qemu+ssh://ece792@{0}/system'.format(zone_ip))
    con = conn.listDomainsID()
    dom = ''
    for c in con:
        if vmid == conn.lookupByID(c).name():
            dom = conn.lookupByID(c)
    vm = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
    for val in vm.values():
        vm_ip = val['addrs'][0]['addr']
    return vm_ip


def attach_interface(vm_id, tenant_id, subnet, ip, zone_id, route_flag):
    try:
        print(vm_id, zones[zone_id][0])
        # cmd = "virsh domifaddr "+vm_id+"|awk 'FNR==3 {print $4}'"
        # print(cmd)
        addr = get_vm_ip(zones[zone_id][0], vm_id)
        print(addr)
        os.system("ansible {3} -m shell -a 'virsh attach-interface --domain {0} --type network --source {1} --model virtio --config --live --target {2}'".format(vm_id,'net_'+tenant_id+subnet,vm_id+subnet, zone_id))
        mac = get_vm_mac(zones[zone_id][0], vm_id, 'net_'+tenant_id+subnet)
        print(mac)
        vm_ssh = create_ssh_conn(addr, 'root', 'root')
        dev_name = execute_command(vm_ssh, "ip -o  link | grep " + mac)
        print(dev_name)
        dev_name = dev_name.split()[1][:-1]
        print(dev_name)
        execute_command(vm_ssh, "ip addr add "+ip+"/25 dev " + dev_name)
        execute_command(vm_ssh, "ip link set dev "+dev_name+" up")
        if route_flag:
            gw_ip = '.'.join(ip.split('.')[:-1]) + '.1'
            execute_command(vm_ssh, "ip route del default")
            execute_command(vm_ssh, "ip route add default dev " +
                            dev_name + "via " + gw_ip)
        close_ssh_conn(vm_ssh)
        return addr
    except Exception as e:
        print(e)
        return -1


if __name__ == '__main__':
    attach_interface('t-1VM1', 't-1', 'sn1', '10.0.0.2', 'zone1', True)
