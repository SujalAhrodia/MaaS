import paramiko

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
    alldata = ''
    stdin, stdout, stderr = ssh_client.exec_command(command)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            alldata = stdout.channel.recv(1024)
            while stdout.channel.recv_ready():
                alldata += stdout.channel.recv(1024)
            #print(str(alldata, 'utf8'))
    if isinstance(alldata, str):
        return alldata
    return alldata.decode('utf-8')


def close_ssh_conn(ssh_client):
    ssh_client.close()


def attach_interface(vm_id, tenant_id, subnet, ip, zone_id, route_flag):
    try:
        zone_ssh = create_ssh_conn(
            zones[zone_id][0], 'ece792', zones[zone_id][1])
        print(vm_id, zones[zone_id][0])
        cmd = "sudo virsh domifaddr "+vm_id+"|awk 'FNR==3 {print $4}'"
        print(cmd)
        addr = execute_command(zone_ssh, cmd).split('/')[0]
        print(addr)
        #execute_command(zone_ssh,'virsh attach-interface --domain {0} --model virtio --type network --config --live --source {1} --target {2}'.format(vm_id,'net_'+tenant_id+subnet,vm_id+subnet))
        mac = execute_command(zone_ssh, 'sudo virsh domiflist ' +
                              vm_id+' | grep '+vm_id+subnet+' | awk \'{print $5}\'')
        close_ssh_conn(zone_ssh)
        vm_ssh = create_ssh_conn(addr, 'root', 'root')
        dev_name = execute_command(vm_ssh, "ip -o  link | grep "+mac)
        print(mac, dev_name)
        dev_name = dev_name.split()[1][:-1]
        print(dev_name)
        execute_command(vm_ssh, "ip addr add "+ip+"/25 dev "+dev_name)
        execute_command(vm_ssh, "ip link set dev "+dev_name+" up")
        if route_flag:
            gw_ip = '.'.join(ip.split('.')[:-1]) + '.1'
            execute_command(vm_ssh, "ip route del default")
            execute_command(vm_ssh, "ip route add default dev " +
                            dev_name + "via " + gw_ip)
        close_ssh_conn(vm_ssh)
        return addr
    except Exception:
        return -1


if __name__ == '__main__':
    attach_interface('q3VM1', 'q3br_', 'net', '11.11.91.12', 'zone2')
