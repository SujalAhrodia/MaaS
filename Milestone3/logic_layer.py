import json
import subprocess
import libvirt
from logging_logic import parse_input_json
from create_interface import attach_interface

replace_flag = False
filename = 'Testing.json'
tenant_list = []
zones = {'1': ['zone1', '172.16.3.1'], '2': ['zone2', '172.16.3.2']}

def get_tenant_vpc_file(Tenant_name):
    import glob
    import re
    list_of_files = glob.glob('generated_files/' + "*.json")
    for items in list_of_files:
        item = items.strip('.json')
        item = re.sub(r'-t-', '', item)
        item = re.sub(r'generated_files/', '', item)
        if Tenant_name == item[:-1]:
            return list_of_files[list_of_files.index(items)]
    return 0

def create_tenant_id():
    import glob
    list_of_files = glob.glob('generated_files/' + '*.json')
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
    print(z1_host, z1_subnet)
    #ansible_proc=subprocess.Popen('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0} z1_subnet={1} z2_host={2} z2_subnet={3} tid={4} z1_nid={5} z2_nid={6}"'.format(z1_host,z1_subnet,z2_host,z2_subnet,tenant_id,z1_network_id,z2_network_id),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()

def create_subnet_switch(sn, sn_id, tenant_id, flag):
    if not flag:
        return
    sn_octets = sn.split('.')
    prefix = '.'.join(s for s in sn_octets[:-1]) + '.'
    # gives '10.0.0.' from '10.0.0.0/24'
    print(prefix)
    last_octet = (4 * int(tenant_id[-1])) - 3
    z1_subnet = "99.0.0." + str(last_octet + 1)
    #ansible_proc=subprocess.Popen('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0} prefix={1} snid={2} z1_subnet={3}"'.format(tenant_id,prefix,sn_id,z1_subnet),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()

def list_vms():
    # Change for containers
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
    # Change for containers
    if not flag:
        return
    zone = zones[zone_id][0]
    #ansible_proc=subprocess.Popen('ansible-playbook {0} spawn_vm.yml --extra-vars "vmid={1} image=VM1"'.format(zone, vm_id),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()

def create_vpc(replace_flag, filename):
    tenant = filename[:-5]
    if not replace_flag:
        print('New tenant')
        sr_process = subprocess.Popen(
            'sudo ip netns list', stdout=subprocess.PIPE, shell=True)
        (sr_list, error) = sr_process.communicate()
        sr_list = sr_list.decode('utf-8').split('\n')
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
        if replace_flag:
            for key, cal in data['VPC'].items():
                regex_string = r'VM([0-9])+'
                total_number_of_vms = len(vpc_data.keys())
                if key in vpc_data.keys():
                    new_vm_id = int(re.match(regex_string, key).groups()[0]) + total_number_of_vms
                    new_vm_id = 'VM' + str(new_vm_id)
                    vpc_data.update({new_vm_id: data['VPC'][key]})
        else:
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
        # print(subnet_map)
        count = len(subnet_map.keys())
        print(count)
        for sn in subnets:
            if sn not in subnet_map.keys():
                count += 1
                sn_id = "sn" + (str(count))
                subnet_map.update({sn: sn_id})
            print('\t subnet map after updating the map with IDs in the loop: ', subnet_map)
            # count += 1
        print('\nTotal Subnets required:\n\t', subnet_map)
        print('\nTotal VMs required:\n\t', vpc_data)

        for sn, sn_id in subnet_map.items():
            sn_create_flag = False if tenant_id + sn_id in sr_list else True
            create_subnet_switch(sn, sn_id, tenant_id, sn_create_flag)

        state_data = {}
        for key, val in vpc_data.items():
            state_data[key] = [zones[val[0]][0], 0]
            state_data[key].extend([0 for i in range(len(subnet_map.keys()))])
        print(state_data)

    for key, val in vpc_data.items():
        vm_id = tenant_id + key
        create_vm_flag = False if vm_id in vm_list else True
        print("For the vm: ", vm_id, "Adding networks if needed: ", create_vm_flag)
        if not create_vm_flag:
            print(subnet_map.values)
            for subnet, _id in subnet_map.items():
                print(subnet)
                print('\tNetwork of the VM', val)
                print('\t Subnet map of all subnets', subnet_map)
                sn_octets = subnet.split('.')
                prefix = '.'.join(s for s in sn_octets[:-1])
                # subnet_id = prefix + '.0/24'
                s_ref = int(_id[-1]) + 1
                print(s_ref)
                try:
                    if prefix in str(state_data[key][s_ref]):
                        pass
                    else:
                        print(key, state_data[key])
                        state_data[key].insert(s_ref, 0)
                        print(key, state_data[key])
                except IndexError as e:
                    print(key, state_data[key])
                    state_data[key].insert(s_ref, 0)
                    print(key, state_data[key])

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
        with open('generated_files/vminventory.ini', 'w') as f:
            f.write(inventory_header)
            f.write(mgmt_ip + ' ' + inventory_common_data)
            f.write('\n[zone]\n')
            f.write(zone_ip + ' ansible_connection=ssh ansible_ssh_user=ece792 ansible_ssh_pass=' + zone_data[zone_name][1] + ' ansible_sudo_pass=' + zone_data[zone_name][1])
        i = 1
        print('\t State Data using which interfaces will be attached', state_data)

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
            virtual_ip = '172.17.0.' + str(int(tenant_id[-1]) + 1) + '/24'
            # cmd = 'ansible-playbook -i generated_files/vminventory.ini attach_interface.yml --extra-vars "dev_name={0} ip_addr={1} vmid={2} network_name={3} host={4} flag={5} gw_ip={6} virtual_ip={7}"'\
                # .format(dev_name, ip, vm_id, 'net_' + tenant_id + subnet_map[subnet_id], zones[vpc_data[key][0]][0], first_flag, gw_ip, virtual_ip)
            
            cmd = 'ansible-playbook -i generated_files/vminventory.ini attach_interface.yml --extra-vars "ip_net={0} ip_addr={1} vmid={2} tid={3} snid={4} virtual_ip={5}"'\
                  .format(prefix, ip,key, tenant_id , subnet_map[subnet_id], virtual_ip)
            
            print(cmd)
            os.system(cmd)
            i += 1
        state_data[key][1] = mgmt_ip
    print(state_data)
    print(mon_data)
    output_filename = 'generated_files/' + tenant + '-' + tenant_id + '.json'
    with open(output_filename, 'w') as f:
        output_data = {
            'Subnets': subnet_map,
            'VPC': state_data,
            'Monitoring': mon_data}
        f.write(json.dumps(output_data))
    print('File with name: ', output_filename, ' created for the tenant')
    parse_input_json(output_filename)
    return output_filename


if __name__ == '__main__':
    output_filename = create_vpc(replace_flag, filename)
