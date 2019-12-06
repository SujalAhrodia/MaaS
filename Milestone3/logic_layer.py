import json
import subprocess
import libvirt
from logging_logic import parse_input_json
from create_interface import attach_interface
import os

replace_flag = False
filename = 'Testing.json'
tenant_list = []
zones = {'1': ['zone1', '172.16.3.1'], '2': ['zone2', '172.16.3.2']}
print(zones)


def create_tenant_id():
    import glob
    list_of_files = glob.glob('*.json')
    count = 0
    for item in list_of_files:
        if '-t-' in item:
            count += 1
    return count + 1


def create_tenant_subnet_router(tenant_id, flag):
    if not flag:
        return
    last_octet = (4 * int(tenant_id[-1])) - 3
    z1_network_id = "99.0.0." + str(last_octet - 1) + "/30"
    z2_network_id = "100.0.0." + str(last_octet - 1) + "/30"
    z1_host = "99.0.0." + str(last_octet)
    z1_subnet = "99.0.0." + str(last_octet + 1)
    z2_host = "100.0.0." + str(last_octet)
    z2_subnet = "100.0.0." + str(last_octet + 1)
    # print(z1_host, z1_subnet)
    print('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0} z1_subnet={1} z2_host={2} z2_subnet={3} tid={4} z1_nid={5} z2_nid={6}"'.format(z1_host,z1_subnet,z2_host,z2_subnet,tenant_id,z1_network_id,z2_network_id))
    os.system('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0} z1_subnet={1} z2_host={2} z2_subnet={3} tid={4} z1_nid={5} z2_nid={6}"'.format(z1_host,z1_subnet,z2_host,z2_subnet,tenant_id,z1_network_id,z2_network_id))


def create_subnet_switch(sn, sn_id, tenant_id, flag):
    if not flag:
        return
    sn_octets = sn.split('.')
    prefix = '.'.join(s for s in sn_octets[:-1])
    # gives '10.0.0.' from '10.0.0.0/24'
    print(prefix)
    last_octet = (4 * int(tenant_id[-1])) - 3
    z1_subnet = "99.0.0." + str(last_octet + 1)
    print('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0} prefix={1} snid={2} z1_subnet={3}"'.format(tenant_id,prefix,sn_id,z1_subnet))
    os.system('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0} prefix={1} snid={2} z1_subnet={3}"'.format(tenant_id,prefix,sn_id,z1_subnet))


def list_vms():
    import libvirt
    vm_list = []
    for val in zones.values():
        ip = val[1]
        conn = libvirt.open('qemu+ssh://ece792@{0}/system'.format(ip))
        con = conn.listAllDomains()
        all_domains = []
        down_domains = conn.listDefinedDomains()
        for c in con:
            all_domains.append(c.name())
        vm_list.extend(set(all_domains) - set(down_domains))
    print(vm_list)
    return vm_list


def create_vm(vm_id, zone_id, flag):
    if not flag:
        return
    zone = zones[zone_id][0]
    print('ansible-playbook {0} spawn_vm.yml --extra-vars "vmid={1} image=VM1"'.format(zone, vm_id))
    os.system('ansible-playbook spawn_vm.yml --extra-vars "host={0} vmid={1} image=VM1"'.format(zone, vm_id))


def create_vpc(replace_flag, filename):
    tenant = filename[:-5]
    if not replace_flag:
        print('New tenant')
        sr_process = subprocess.Popen(
            'sudo ip netns list', stdout=subprocess.PIPE, shell=True)
        (sr_list, error) = sr_process.communicate()
        sr_list = sr_list.decode('utf-8').split('\n')
        # Add the logic to not create the tenant id if the tenant already exists
        tenant_id = "t-" + str(create_tenant_id())
        print(tenant_id, sr_list)
        create_sr_flag = False if tenant_id + "sr" in sr_list else True
        print(create_sr_flag)
        create_tenant_subnet_router(tenant_id, create_sr_flag)
        print('TENANT SR CREATED')
        vpc_data = []
        subnet_map = {}
        with open(filename) as json_file:
            data = json.load(json_file)
            vpc_data = data['VPC']
            mon_data = data['Monitoring']
            print(vpc_data)
            subnets = set()
            for val in vpc_data.values():
                for sn in val[1:]:
                    subnets.add(sn)
                    # adds unique subnets only
            count = 1
            for sn in subnets:
                sn_id = "sn" + (str(count))
                subnet_map.update({sn: sn_id})
                count += 1
            print(subnet_map)

        for sn, sn_id in subnet_map.items():
            sn_create_flag = False if tenant_id + sn_id in sr_list else True
            create_subnet_switch(sn, sn_id, tenant_id, sn_create_flag)

        state_data = {}
        for key, val in vpc_data.items():
            state_data[key] = [zones[val[0]][0], 0]
            state_data[key].extend([0 for i in range(len(subnet_map.keys()))])
        print(state_data)

        vm_list = list_vms()
        for key, val in vpc_data.items():
            vm_id = tenant_id + key
            create_vm_flag = False if vm_id in vm_list else True
            create_vm(vm_id, vpc_data[key][0], create_vm_flag)
            zone_ip = zones[vpc_data[key][0]][1]
            zone_name = zones[vpc_data[key][0]][0]
            mgmt_ip = get_vm_ip(zone_ip, vm_id)
            inventory_header = '[tenant_vms]\n'
            inventory_common_data = "ansible_connection=ssh ansible_ssh_user=root ansible_ssh_pass=root ansible_ssh_common_args='-o StrictHostKeyChecking=no'"
            zone_data = {'zone1': ['172.16.3.1', 'linux@1234'],
                    'zone2': ['172.16.3.2', 'linux@123']}
            print(zone_name)
            with open('vminventory.ini', 'w') as f:
                f.write(inventory_header)
                f.write(mgmt_ip + ' ' + inventory_common_data)
                f.write('\n[zone]\n')
                f.write(zone_ip + ' ansible_connection=ssh ansible_ssh_user=ece792 ansible_ssh_pass='+ zone_data[zone_name][1]+' ansible_sudo_pass='+zone_data[zone_name][1])
            i = 1
            for subnet in val[1:]:
                s_ref = int(subnet_map[subnet][-1]) + 1
                dev_name = 'eth' + str(i)
                count = 2
                for v in state_data.values():
                    if v[s_ref] != 0:
                        count += 1
                sn_octets = subnet.split('.')
                ip = '.'.join(s for s in sn_octets[:-1]) + '.' + str(count)
                # print(ip)
                state_data[key][s_ref] = ip
                # print(val)
                # print(zones[(val[0][-1])][0])
                # print(val[0])
                # zone_ip = zones[vpc_data[key][0]][1]
                first_flag = True if v[1] == 0 else False
                os.system('ansible-playbook -i vminventory.ini attach_interface.yml --extra-vars "dev_name={0} ip_addr={1} vmid={2} network_name={3} host={4}"'.format(dev_name, ip, vm_id,'net_'+tenant_id+subnet_map[subnet] , zones[vpc_data[key][0]][0]))
                state_data[key][1] = mgmt_ip
                i += 1
        print(state_data)
        print(mon_data)
        output_filename = tenant + '-' + tenant_id + '.json'
        with open(output_filename, 'a') as f:
            output_data = {
                'Subnets': subnet_map,
                'VPC': state_data,
                'Monitoring': mon_data}
            f.write(json.dumps(output_data))
        print('File with name: ', output_filename, ' created for the tenant')
        parse_input_json(output_filename)
        return output_filename


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

if __name__ == '__main__':
    output_filename = create_vpc(replace_flag, filename)
