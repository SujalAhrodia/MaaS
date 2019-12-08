#!/bin/usr/python3

import json
from subprocess import Popen
import os
import yaml

zones = {'1': ['zone1', '172.16.3.1'], '2': ['zone2', '172.16.3.2']}

filename = 'generated_files/same-t-1.json'

monitoring_basic_data = '''
#
# Config file for collectd(1).
# Please reach out to your system administrator for assistance in changing
# this file. Any unauthorised changes will not be supported.
#

Hostname  "{0}"

LoadPlugin syslog
LoadPlugin network
<Plugin "network">
    Server "{1}" "25826"
</Plugin>
'''

aggregation_plugin_data = '''
LoadPlugin aggregation
<Plugin aggregation>
  <Aggregation>
    Plugin "cpu"
    Type "cpu"
    GroupBy "Host"
    GroupBy "TypeInstance"
    CalculateNum true
    CalculateSum true
    CalculateAverage true
  </Aggregation>
</Plugin>
'''

cpu_plugin_data = '''
LoadPlugin cpu
<Plugin cpu>
  ReportByCpu true
  ReportByState true
  ValuesPercentage true
</Plugin>
'''

memory_plugin_data = '''
LoadPlugin memory
<Plugin memory>
       ValuesAbsolute true
       ValuesPercentage false
</Plugin>
'''

custom_plugin_data = '''
<LoadPlugin python>
    Interval 60
</LoadPlugin>
<Plugin python>
      ModulePath "/opt/custom_plugins"
      Import "load_avg"
</Plugin>
'''

inventory_header = '[tenant_vms]\n'

inventory_common_data = "ansible_connection=ssh ansible_ssh_user=root ansible_ssh_pass=root ansible_ssh_common_args='-o StrictHostKeyChecking=no'"

router_logging_sh = '''
count=$(sudo ip netns exec {0} iptables -nvL INPUT| grep TRAFFIC | awk '{{print $1}}')
echo $count
curl -i -XPOST 'http://{1}:8086/write?db=collectd' --data-binary 'trial,protocol=tcp value="'"$count"'"'
sudo ip netns exec {0} iptables -Z
'''

grafana_conf = '''
[server]
root_url = http://{0}:3000
'''


def gen_keepalived_conf(state, m_ip, s_ip, prio, virtual_ip):
    keepalived_conf = f'''
    vrrp_script chk_influx {{
        script "pidof influxd"
        interval 2
    }}

    vrrp_instance VI_1 {{

        interface eth0
        state {state}
        virtual_router_id 50
        unicast_src_ip {m_ip}

        unicast_peer {{

        {s_ip}
        }}

        priority {prio}


        track_script {{
            chk_influx
        }}

        virtual_ipaddress {{
            {virtual_ip} dev eth0
        }}
    }}
    '''
    return keepalived_conf

def gen_backup_sh(virtual_ip, peer_ip):
    backup_sh = f'''
    #! /bin/bash

    ip=$(ip a s |grep {virtual_ip})

    if [ -z "$ip" ]
    then
    echo "I am not the master"
    else
    influxd backup -portable -database collectd ~/infdb_bak
    echo "I am the master"
    scp -o StrictHostKeyChecking=no -r ~/infdb_bak root@{peer_ip}:~/
    ssh -o StrictHostKeyChecking=no root@{peer_ip}  'curl -i -XPOST http://localhost:8086/query --data-urlencode "q=DROP DATABASE collectd" | influxd restore -portable ~/infdb_bak'
    sleep 5
    echo Removing backup at slave
    ssh -o StrictHostKeyChecking=no root@{peer_ip} 'rm -rf ~/infdb_bak'
    echo Removing backup at master
    rm -rf ~/infdb_bak
    fi
    '''
    return backup_sh

def parse_input_json(filename):
    print(filename)
    input_data = ''
    with open(filename, 'r') as f:
        input_data = json.loads(''.join(f.readlines()))
    subnet_map = input_data['Subnets']
    vpc_data = input_data['VPC']
    mon_data = input_data['Monitoring']
    tenant_name = filename.split('-')[0]
    tenant_name = tenant_name.split('/')[1]
    tenant_id = filename.split('-')[1] + '-' + filename.split('-')[2][:-5]
    if mon_data['flag']:
        ifdb_master = 'IFDB_' + tenant_id
        ifdb_slave = 'IFDB_' + tenant_id + '_bak'
        print(ifdb_master)
        print(ifdb_slave)
        vm_list = list_vms()
        if ifdb_master not in vm_list:
            command = 'ansible-playbook spawn_vm.yml --extra-vars "host={0} vmid={1} image=goldenIFDB"'\
                      .format('zone1', ifdb_master)
            print(command)
            # Run the inventory for creating the IFDB VMs
            os.system(command)
        if ifdb_slave not in vm_list:
            command = 'ansible-playbook spawn_vm.yml --extra-vars "host={0} vmid={1} image=goldenIFDB"'\
                      .format('zone2', ifdb_slave)
            print(command)
            # Run the inventory for creating the IFDB VMs
            os.system(command)
        inventory_file_name = 'generated_files/' + ifdb_master + '-inventory.ini'
        print(inventory_file_name)
        delete_the_file(inventory_file_name)
        inventory_file_handler = open(inventory_file_name, 'a')
        IFDB_IPs = find_ifdb_ip(ifdb_master, ifdb_slave)
        print(IFDB_IPs)
        virtual_ip = '192.168.123.' + str(int(tenant_id[-1]) + 1) + '/24'
        maas_data = ''
        with open('grafana/dashboards/MaaS.json', 'r') as f:
            maas_data = json.loads(''.join(f.readlines()))
        maas_data["panels"][0]["targets"][0]["tags"][0]["value"] = list(vpc_data['VPC'].keys())[0]
        maas_data["panels"][1]["targets"][0]["tags"][0]["value"] = list(vpc_data['VPC'].keys())[0]
        with open('grafana/dashboards/MaaS.json', 'w') as f:
            f.write(json.dumps(maas_data))
        stream = open('grafana/datasources/sample.yml', 'r')
        datasource = yaml.load(stream)
        stream.close()
        datasource['datasources'][0]['url'] = 'http://' + virtual_ip[:-3] + ':8086'
        stream = open('grafana/datasources/sample.yml', 'w')
        yaml.dump(datasource, stream)
        stream.close()
        temp = '[ip1]\n' +\
            IFDB_IPs[0] + ' ' + inventory_common_data + '\n' +\
            "[ip2]\n" +\
            IFDB_IPs[1] + ' ' + inventory_common_data + '\n'
        inventory_file_handler.write(temp)
        print(temp)
        inventory_file_handler.close()
        # keepalived_conf.format('MASTER', IFDB_IPs[0], IFDB_IPs[1], '102', virtual_ip)
        keepalived_conf = gen_keepalived_conf(state='MASTER', m_ip=IFDB_IPs[0],
                                              s_ip=IFDB_IPs[1], prio='102', virtual_ip=virtual_ip)
        # print(keepalived_conf)
        with open('generated_files/keepalived.conf', 'w') as f:
            f.write(keepalived_conf)
        # backup_sh.format(virtual_ip, IFDB_IPs[1])
        backup_sh = gen_backup_sh(virtual_ip=virtual_ip, peer_ip=IFDB_IPs[1])
        # print(backup_sh)
        with open('generated_files/backup.sh', 'w') as f:
            f.write(backup_sh)
        with open('grafana.ini', 'w') as f:
            f.write(grafana_conf.format(virtual_ip[:-3]))
        command = 'ansible-playbook -i {0} ifdbconf.yml --extra-vars "keepalived_conf={1} backup_sh={2}"'\
                  .format(inventory_file_name, 'generated_files/keepalived.conf', 'generated_files/backup.sh')
        print(command)
        # Run the play for starting keepalived on the Master
        vm_list = list_vms()
        if ifdb_master in vm_list:
            os.system(command)
        inventory_file_name = 'generated_files/' + ifdb_slave + '-inventory.ini'
        print(inventory_file_name)
        delete_the_file(inventory_file_name)
        inventory_file_handler = open(inventory_file_name, 'a')
        temp = '[ip1]\n' +\
            IFDB_IPs[1] + ' ' + inventory_common_data + '\n' +\
            "[ip2]\n" +\
            IFDB_IPs[0] + ' ' + inventory_common_data + '\n'
        print(temp)
        inventory_file_handler.write(temp)
        inventory_file_handler.close()
        # keepalived_conf.format('SLAVE', IFDB_IPs[1], IFDB_IPs[0], '101', virtual_ip)
        keepalived_conf = gen_keepalived_conf(state='SLAVE', m_ip=IFDB_IPs[1],
                                              s_ip=IFDB_IPs[0], prio='101', virtual_ip=virtual_ip)
        # print(keepalived_conf)
        with open('generated_files/keepalived.conf', 'w') as f:
            f.write(keepalived_conf)
        # backup_sh.format(virtual_ip, IFDB_IPs[0])
        backup_sh = gen_backup_sh(virtual_ip=virtual_ip, peer_ip=IFDB_IPs[0])
        # print(backup_sh)
        with open('generated_files/backup.sh', 'w') as f:
            f.write(backup_sh)
        command = 'ansible-playbook -i {0} ifdbconf.yml --extra-vars "keepalived_conf={1} backup_sh={2}"'\
                  .format(inventory_file_name, 'generated_files/keepalived.conf', 'generated_files/backup.sh')
        print(command)
        # Run the play for starting keepalived on the Slave
        vm_list = list_vms()
        if ifdb_slave in vm_list:
            os.system(command)
        vpc_data['IFDB'] = IFDB_IPs[0]
        vpc_data['IFDB_bak'] = IFDB_IPs[1]
        vpc_data['Virtual_IP'] = virtual_ip
        print(vpc_data)
        # Populate vpc_data with IFDB data + Virtual IPs
        ifdb_ip = vpc_data['Virtual_IP']
        vm_id_list = [item for item in vpc_data.keys() if 'VM' in item]
        for vm in vm_id_list:
            vm_collectd_file_name = 'generated_files/' + tenant_id + vm + '_collectd.conf'
            vm_ip = vpc_data[vm][1]
            delete_the_file(vm_collectd_file_name)
            collectd_file_handler = open(vm_collectd_file_name, 'a')
            # print(monitoring_basic_data.format(tenant_id + vm, ifdb_ip))
            collectd_file_handler.write(monitoring_basic_data
                                        .format(tenant_id + vm, ifdb_ip[:-3]))
            # print(aggregation_plugin_data)
            collectd_file_handler.write(aggregation_plugin_data)
            if mon_data['CPU']:
                # print(cpu_plugin_data)
                collectd_file_handler.write(cpu_plugin_data)
            if mon_data['Memory']:
                # print(memory_plugin_data)
                collectd_file_handler.write(memory_plugin_data)
            if mon_data['Interface']:
                # print('LoadPlugin interface')
                collectd_file_handler.write('LoadPlugin interface')
            if mon_data['Traffic_Monitoring']:
                print('Call the ansible script')
                router_logging_handler = open('generated_files/' + str(tenant_id) + 'router_logging.sh', 'w')
                router_logging_handler.write(router_logging_sh
                                             .format(tenant_id + 'sr',
                                                     ifdb_ip[:-3]))
                router_logging_handler.close()
                command = 'ansible-playbook router_logging.yml -i {0} --extra-vars "netns_name={1} router_sh={2}"'\
                    .format('inventory.ini',
                            tenant_id + 'sr',
                            'generated_files/' + str(tenant_id) + 'router_logging.sh')
                print(command)
                os.system(command)
                mon_data['Traffic_Monitoring'] = False
            if mon_data['Custom']['flag']:
                collectd_file_handler.write(custom_plugin_data)
            collectd_file_handler.close()
            inventory_file_name = 'generated_files/' + tenant_id + '-inventory.ini'
            delete_the_file(inventory_file_name)
            inventory_file_handler = open(inventory_file_name, 'a')
            inventory_file_handler.write(inventory_header)
            temp = vm_ip + ' ' + inventory_common_data + '\n'
            inventory_file_handler.write(temp)
            inventory_file_handler.close()
            if mon_data['Custom']['flag']:
                command = 'ansible-playbook setup_collectd.yml -i {0} --extra-vars "collectd_file={1} custom_file={2}"'\
                    .format(inventory_file_name, vm_collectd_file_name, mon_data['Custom']['file'])
            else:
                command = 'ansible-playbook setup_collectd.yml -i {0} --extra-vars "collectd_file={1} custom_file={2}"'\
                    .format(inventory_file_name, vm_collectd_file_name, "Fail")
            print(command)
            os.system(command)
    else:
        print('Tenant has chosen not to enable monitoring')
    with open(filename, 'w') as f:
        output_data = {
            'Subnets': subnet_map,
            'VPC': vpc_data,
            'Monitoring': mon_data}
        f.write(json.dumps(output_data))
    print('File with name: ', filename, ' created for the tenant')

def find_ifdb_ip(ifdb_master, ifdb_slave):
    # Change for Containers
    ifdb_mip = get_vm_ip('172.16.3.1', ifdb_master)
    ifdb_sip = get_vm_ip('172.16.3.2', ifdb_slave)
    return [ifdb_mip, ifdb_sip]

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

def delete_the_file(file_name):
    import os
    if os.path.exists(file_name):
        os.remove(file_name)
    return

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
    # print(vm_list)
    return vm_list

if __name__ == '__main__':
    parse_input_json(filename)
