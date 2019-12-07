import json
import subprocess
import libvirt
from logging_logic import parse_input_json
import os
import re

replace_flag = True
filename = 'Testing.json'
tenant_list = []
zones = {'1': ['zone1', '172.16.3.1'], '2': ['zone2', '172.16.3.2']}


def get_tenant_vpc_file(Tenant_name):
    import glob
    import re
    list_of_files = glob.glob("*.json")
    for items in list_of_files:
        item = items.strip('.json')
        item = re.sub(r'-t-', '', item)
        if Tenant_name == item[:-1]:
            return list_of_files[list_of_files.index(items)]
    return 0


def create_tenant_id():
    import glob
    list_of_files = glob.glob('*.json')
    count = 0
    for item in list_of_files:
        if '-t-' in item:
            count += 1
    return count + 1


def create_tenant_subnet_router(tenant_id):
    last_octet = (4 * int(tenant_id[-1])) - 3
    z1_network_id = "99.0.0." + str(last_octet - 1) + "/30"
    z2_network_id = "100.0.0." + str(last_octet - 1) + "/30"
    z1_host = "99.0.0." + str(last_octet)
    z1_subnet = "99.0.0." + str(last_octet + 1)
    z2_host = "100.0.0." + str(last_octet)
    z2_subnet = "100.0.0." + str(last_octet + 1)
    # print(z1_host, z1_subnet)
    print('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0} z1_subnet={1} z2_host={2} z2_subnet={3} tid={4} z1_nid={5} z2_nid={6}"'.format(z1_host, z1_subnet, z2_host, z2_subnet, tenant_id, z1_network_id, z2_network_id))
    os.system('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0} z1_subnet={1} z2_host={2} z2_subnet={3} tid={4} z1_nid={5} z2_nid={6}"'.format(z1_host, z1_subnet, z2_host, z2_subnet, tenant_id, z1_network_id, z2_network_id))


def create_subnet_switch(sn, sn_id, tenant_id, flag):
    if not flag:
        return
    sn_octets = sn.split('.')
    prefix = '.'.join(s for s in sn_octets[:-1])
    # gives '10.0.0.' from '10.0.0.0/24'
    print(prefix)
    last_octet = (4 * int(tenant_id[-1])) - 3
    z1_subnet = "99.0.0." + str(last_octet + 1)
    print('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0} prefix={1} snid={2} z1_subnet={3}"'.format(tenant_id, prefix, sn_id, z1_subnet))
    os.system('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0} prefix={1} snid={2} z1_subnet={3}"'.format(tenant_id, prefix, sn_id, z1_subnet))


def list_vms():
    from pexpect import pxssh
    vm_list=[]
    vms=[]
    for val in zones.values():
        log=pxssh.pxssh(timeout=120)
        ip = val[1]
        pwd=''
        if ip == '172.16.3.1':
            pwd='linux@1234'
        else:
            pwd='linux@123'
        print(ip,pwd)
        log.login(ip,'ece792',pwd)
        log.sendline("sudo docker ps -a --filter status=running |awk 'NR!=1 {print $NF}'")
        log.sendline(pwd)
        log.prompt()
        vms.extend(log.before.decode('utf-8').split('\r\n'))
        for v in vms:
            if 't-' in v:
                vm_list.append(v)
        print(log.before)
        print(vm_list)
        log.logout()
    return vm_list


def create_vm(vm_id, zone_id, flag):
    if not flag:
        return
    zone = zones[zone_id][0]
    print('ansible-playbook spawn_container.yml --extra-vars "host={0} vmid={1}'.format(zone, vm_id))
    os.system('ansible-playbook spawn_container.yml --extra-vars "host={0} vmid={1}"'.format(zone, vm_id))


def create_vpc(replace_flag, filename):
    tenant = filename[:-5]
    if not replace_flag:
        print('New tenant')
    if replace_flag:
        print('Returning Tenant')
    sr_process = subprocess.Popen(
        'sudo ip netns list', stdout=subprocess.PIPE, shell=True)
    (sr_list, error) = sr_process.communicate()
    sr_list = sr_list.decode('utf-8')
    # Add the logic to not create the tenant id if the tenant already exists
    if replace_flag:
        existing_tenant_file = get_tenant_vpc_file(tenant)
        if existing_tenant_file == 0:
            tenant_id = "t-" + str(create_tenant_id())
            replace_flag = False
        else:
            tenant_id = "t-" + existing_tenant_file.split('-')[-1][:-5]
    elif not replace_flag:
        tenant_id = "t-" + str(create_tenant_id())
    print('Tenant ID: ', tenant_id)
    # print(sr_list)
    print('\tSR ID: ', tenant_id + "sr")
    sr_id = tenant_id + "sr"
    create_sr_flag = False if re.search(sr_id, sr_list) else True
    if create_sr_flag:
        print('\tShould the SR be created?', create_sr_flag)
        create_tenant_subnet_router(tenant_id)
        print('\tTenant SR created')
    else:
        print('\tShould the SR be created?', create_sr_flag)
        print('\tTenant SR Already Exists')
    vpc_data = {}
    subnet_map = {}
    if replace_flag:
        with open(existing_tenant_file, 'r') as stat_file:
            data = json.load(stat_file)
            # {'VM1': ['zone1', 0, 0, 0, 0], 'VM2': ['zone1', 0, 0, 0, 0]}
            temp_dict = data['VPC']
            # print(temp_dict)
            for key in temp_dict.keys():
                del temp_dict[key][1]
                temp_dict[key][0] = temp_dict[key][0][-1]
            vpc_data.update(temp_dict)
            subnet_map = data['Subnets']
            print('\nExisting Subnet List:\n\t', subnet_map)
            print('Existing VM List:\n\t', vpc_data)
    with open(filename) as json_file:
        data = json.load(json_file)
        # print(data['VPC'])
        vpc_data.update(data['VPC'])
        mon_data = data['Monitoring']
        # print(vpc_data)
        subnets = set(subnet_map.keys())
        for val in vpc_data.values():
            for sn in val[1:]:
                if '/' in sn:
                    # if sn in subnet_map.keys():
                    # pass
                    # else:
                    subnets.add(sn)
                # adds unique subnets only
        # print(subnet_ma)
        count = 1
        for sn in subnets:
            if sn in subnet_map.keys():
                count += 1
                continue
            sn_id = "sn" + (str(count))
            subnet_map.update({sn: sn_id})
            count += 1
        print('\nTotal Subnets required:\n\t', subnet_map)
        print('\nTotal VMs required:\n\t', vpc_data)

    for sn, sn_id in subnet_map.items():
        sn_create_flag = False if tenant_id + sn_id in sr_list else True
        print('\t\tDoes Subnet with network: ', sn, 'need to be created?: ', sn_create_flag)
        create_subnet_switch(sn, sn_id, tenant_id, sn_create_flag)

    state_data = {}
    vm_list = list_vms()
    for key, val in vpc_data.items():
        # key is the vm id
        # value added is the list of VMS
        state_data[key] = [zones[val[0]][0], 0]
        if not replace_flag:
            state_data[key].extend([0 for i in range(len(subnet_map.keys()))])
        elif replace_flag:
            vm_id = tenant_id + key
            data = ''
            with open(existing_tenant_file, 'r') as f:
                data = json.load(f)
            print(data)
            print(vm_id)
            if vm_id in vm_list:
                management_ip = data['VPC'][key][1]
                state_data[key][1] = management_ip
                state_data[key].append(vpc_data[key][1])
            else:
                state_data[key].extend([0 for i in range(len(subnet_map.keys()))])
        print(state_data)
    print('\nMid Run State Data:\n\t', state_data)

    for key, val in vpc_data.items():
        vm_id = tenant_id + key
        print(vm_id)
        print(vm_list)
        create_vm_flag = False if vm_id in vm_list else True
        print("\t\tDoes a VM with ID: ", vm_id, "need to be spawned? ", create_vm_flag)
        create_vm(vm_id, vpc_data[key][0], create_vm_flag)
        zone_ip = zones[vpc_data[key][0]][1]
        zone_name = zones[vpc_data[key][0]][0]
        mgmt_ip = get_vm_ip(zone_ip,vm_id)
        print(mgmt_ip)
        #subprocess.check_output("sudo docker inspect -f {{'{{.NetworkSettings.IPAddress}}'}} {0} ".format(vm_id),shell=True).decode('utf-8').split('\n')[0]
        inventory_header = '[tenant_vms]\n'
        inventory_common_data = "ansible_connection=ssh ansible_ssh_user=root ansible_ssh_pass=root ansible_ssh_common_args='-o StrictHostKeyChecking=no'"
        zone_data = {'zone1': ['172.16.3.1', 'linux@1234'],
                     'zone2': ['172.16.3.2', 'linux@123']}
        #print(zone_name)
        with open('vminventory.ini', 'w') as f:
            f.write('[zone]\n')
            f.write(zone_ip + ' ansible_connection=ssh ansible_ssh_user=ece792 ansible_ssh_pass=' + zone_data[zone_name][1] + ' ansible_sudo_pass=' + zone_data[zone_name][1])
        i = 1
        if not create_vm_flag:
            for subnet in val[1:]:
                print(subnet)
                print(subnet_map)
                sn_octets = subnet.split('.')
                prefix = '.'.join(s for s in sn_octets[:-1])
                subnet_id = prefix + '.0/24'
                s_ref = int(subnet_map[subnet_id][-1]) + 1
                print(s_ref,key)
                print(state_data)
                if prefix == state_data[key][s_ref]:
                    pass
                else:
                    state_data[key].insert(s_ref, 0)
        for subnet in val[1:]:
            print(subnet)
            print(subnet_map)
            sn_octets = subnet.split('.')
            prefix = '.'.join(s for s in sn_octets[:-1])
            subnet_id = prefix + '.0/24'
            s_ref = int(subnet_map[subnet_id][-1]) + 1
            print(state_data)
            if state_data[key][s_ref] != 0:
                continue
            dev_name = 'eth' + str(i)
            count = 2
            for v in state_data.values():
                if v[s_ref] != 0:
                    count += 1
            sn_octets = subnet.split('.')
            ip = '.'.join(s for s in sn_octets[:-1]) + '.' + str(count)
            state_data[key][s_ref] = ip
            first_flag = True if v[1] == 0 else False
            gw_ip = '.'.join(ip.split('.')[:-1]) + '.1'
            cmd = 'ansible-playbook -i vminventory.ini attach_interface.yml --extra-vars "ip_net={0} ip_addr={1} vmid={2} tid={3} snid={4}"'.format(prefix, ip,key, tenant_id , subnet_map[subnet_id])
            print(cmd)
            os.system(cmd)
            i += 1
        state_data[key][1] = mgmt_ip
    print(state_data)
    print(mon_data)
    output_filename = tenant + '-' + tenant_id + '.json'
    with open(output_filename, 'w') as f:
        output_data = {
            'Subnets': subnet_map,
            'VPC': state_data,
            'Monitoring': mon_data}
        f.write(json.dumps(output_data))
    print('File with name: ', output_filename, ' created for the tenant')
    parse_input_json(output_filename)
    return output_filename

def get_vm_ip(zone_ip,vm_id):
    from pexpect import pxssh
    import re
    mgm_ip=''
    log=pxssh.pxssh()
    pwd=''
    if zone_ip == '172.16.3.1':
        pwd='linux@1234'
    else:
        pwd='linux@123'
    print(zone_ip,pwd)
    log.login(zone_ip,'ece792',pwd)
    log.sendline("sudo docker inspect -f {{'{{.NetworkSettings.IPAddress}}'}} {0}".format(vm_id))
    log.sendline(pwd)
    log.prompt()
    ip=log.before.decode('utf-8')
    ip=ip.split('\r\n')
    for i in ip:
        if re.match('\d+\.\d+\.\d+\.\d+',i):
            mgm_ip=i
    print(mgm_ip)
    log.logout()
    return mgm_ip

if __name__ == '__main__':
    filename='NewTenant.json'
    output_filename = create_vpc(replace_flag, filename)
