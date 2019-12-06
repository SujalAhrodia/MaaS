#!/bin/usr/python3

import json
from subprocess import Popen

filename = 'Testing-t-1.json'

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

inventory_header = '[tenant_vms]\n'

inventory_common_data = 'ansible_connection=ssh ansible_ssh_user=root ansible_ssh_pass=root'

router_logging_sh = '''
count=$(sudo ip netns exec {0} iptables -nvL INPUT| grep TRAFFIC | awk '{{print $1}}')
echo $count
curl -i -XPOST 'http://{1}:8086/write?db=collectd' --data-binary 'trial,protocol=tcp value="'"$count"'"'
sudo ip netns exec {0} iptables -Z
'''


def gen_keepalived_conf(state, m_ip, s_ip, prio, virtual_ip):
    keepalived_conf = f'''
    vrrp_script chk_influx {{
        script "pidof influxd"
        script "pidof grafana-server"
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

    ip=$(ip a s |grep {virtual_ip}/24)

    if [ -z "$ip" ]
    then
    echo "I am not the master"
    else
    influxd backup -portable -database collectd ~/infdb_bak
    echo "I am the master"
    scp -r ~/infdb_bak root@{peer_ip}:~/
    ssh root@{peer_ip}  'curl -i -XPOST http://localhost:8086/query --data-urlencode "q=DROP DATABASE collectd" | influxd restore -portable ~/infdb_bak'
    sleep 5
    echo Removing backup at slave
    ssh root@{peer_ip} 'rm -rf ~/infdb_bak'
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
    vpc_data = input_data['VPC']
    mon_data = input_data['Monitoring']
    # monitoring_data = mon_data['flag']
    # print(monitoring_data)
    tenant_name = filename.split('-')[0]
    # print(Tenant_name)
    # tenant_file = get_tenant_vpc_file(tenant_name)
    # print(tenant_file)
    # if tenant_file == 0:
        # return 'Tenant File Not found. Looking for {}.json'.format(tenant_name)
    # with open(tenant_file, 'r') as f:
        # vpc_data = json.loads(''.join(f.readlines()))
    # print(vpc_data)
    tenant_id = filename.split('-')[1] + '-' + filename.split('-')[2][:-5]
    if mon_data['flag']:
        ifdb_master = 'IFDB_' + tenant_id
        ifdb_slave = 'IFDB_' + tenant_id + '_bak'
        print(ifdb_master)
        print(ifdb_slave)
        command = 'ansible-playbook {0} spawn_vm.yml --extra-vars "vmid={0} image=goldenIFDB"'\
                  .format('zone1', ifdb_master)
        print(command)
        # Run the inventory for creating the IFDB VMs
        # q = Popen(command,
        #           shell=True)
        # (output, err) = q.communicate()
        # q.wait()
        command = 'ansible-playbook {0} spawn_vm.yml --extra-vars "vmid={0} image=goldenIFDB"'\
                  .format('zone2', ifdb_slave)
        print(command)
        # Run the inventory for creating the IFDB VMs
        # q = Popen(command,
        #           shell=True)
        # (output, err) = q.communicate()
        # q.wait()
        inventory_file_name = ifdb_master + '-inventory.ini'
        print(inventory_file_name)
        delete_the_file(inventory_file_name)
        inventory_file_handler = open(inventory_file_name, 'a')
        IFDB_IPs = ['192.168.123.13', '192.168.123.14']  # find_ifdb_ip(ifdb_master, ifdb_slave)
        virtual_ip = '192.168.123.' + str(int(tenant_id[-1]) + 1) + '/24'
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
        with open('keepalived.conf', 'w') as f:
            f.write(keepalived_conf)
        # backup_sh.format(virtual_ip, IFDB_IPs[1])
        backup_sh = gen_backup_sh(virtual_ip=virtual_ip, peer_ip=IFDB_IPs[1])
        # print(backup_sh)
        with open('backup.sh', 'w') as f:
            f.write(backup_sh)
        command = 'ansible-playbook -i {0} ifdbconf.yml --extra-vars "keepalived_conf={1} backup_sh={2}"'\
                  .format(inventory_file_name, 'keepalived.conf', 'backup.sh')
        print(command)
        # Run the play for starting keepalived on the Master
        # q = Popen(command,
        #           shell=True)
        # (output, err) = q.communicate()
        # q.wait()
        delete_the_file(inventory_file_name)
        inventory_file_name = ifdb_slave + '-inventory.ini'
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
        with open('keepalived.conf', 'w') as f:
            f.write(keepalived_conf)
        # backup_sh.format(virtual_ip, IFDB_IPs[0])
        backup_sh = gen_backup_sh(virtual_ip=virtual_ip, peer_ip=IFDB_IPs[0])
        # print(backup_sh)
        with open('backup.sh', 'w') as f:
            f.write(backup_sh)
        command = 'ansible-playbook -i {0} ifdbconf.yml --extra-vars "keepalived_conf={1} backup_sh={2}"'\
                  .format(inventory_file_name, 'keepalived.conf', 'backup.sh')
        print(command)
        # Run the play for starting keepalived on the Slave
        # q = Popen(command,
        #           shell=True)
        # (output, err) = q.communicate()
        # q.wait()
        delete_the_file(inventory_file_name)
        vpc_data['IFDB'] = IFDB_IPs[0]
        vpc_data['IFDB_bak'] = IFDB_IPs[1]
        vpc_data['Virtual IP'] = virtual_ip
        print(vpc_data)
        # Populate vpc_data with IFDB data + Virtual IPs
        ifdb_ip = vpc_data['Virtual IP']
        vm_id_list = [item for item in vpc_data.keys() if 'VM' in item]
        inventory_file_name = tenant_id + '-inventory.ini'
        delete_the_file(inventory_file_name)
        inventory_file_handler = open(inventory_file_name, 'a')
        inventory_file_handler.write(inventory_header)
        for vm in vm_id_list:
            vm_collectd_file_name = tenant_id + vm + '_collectd.conf'
            vm_ip = vpc_data[vm][1]
            delete_the_file(vm_collectd_file_name)
            collectd_file_handler = open(vm_collectd_file_name, 'a')
            # print(monitoring_basic_data.format(tenant_id + vm, ifdb_ip))
            collectd_file_handler.write(monitoring_basic_data
                                        .format(tenant_id + vm, ifdb_ip))
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
                # q = Popen('sudo ip netns exec {} iptables -A INPUT -p tcp -m comment --comment "TRAFFIC" -j ACCEPT'
                #           .format(tenant_id + 'sr'),
                #           shell=True)
                # (output, err) = q.communicate()
                # q.wait()
                delete_the_file('router_logging.sh')
                router_logging_handler = open('router_logging.sh', 'a')
                router_logging_handler.write(router_logging_sh
                                             .format(tenant_id + 'sr',
                                                     ifdb_ip))
                router_logging_handler.close()
                print('ansible-playbook router_logging.yml -i {0} --extra-vars netns_name={1}'
                      .format('inventory.ini',
                              tenant_id + 'sr'))
                # q = Popen('ansible-playbook router_logging.yml -i {0} --extra-vars netns_name={1}'
                #           .format('inventory.ini',
                #                   tenant_id + 'sr'),
                #           shell=True)
                # (output, err) = q.communicate()
                # q.wait()
                # print(output)
                mon_data['Traffic_Monitoring'] = False
            collectd_file_handler.close()
            temp = vm_ip + ' ' + inventory_common_data + '\n'
            inventory_file_handler.write(temp)
            inventory_file_handler.close()
            print('ansible-playbook setup_collectd.yml -i {0} --extra-vars collectd_file={1}'
                      .format(inventory_file_name, vm_collectd_file_name))
            # p = Popen('ansible-playbook setup_collectd.yml -i {0} --extra-vars collectd_file={1}'
            #           .format(inventory_file_name, vm_collectd_file_name),
            #           shell=True)
            # (output, err) = p.communicate()
            # p.wait()
            # print(output)
    else:
        print('Tenant has chosen not to enable monitoring')


def find_ifdb_ip(ifdb_master, ifdb_slave):
    from create_interface import create_ssh_conn, execute_command, close_ssh_conn
    zones = {'zone1': ['172.16.3.1', 'linux@1234'],
             'zone2': ['172.16.3.2', 'linux@123']}
    ifdb_m_conn = create_ssh_conn(zones['zone1'][0], 'ece792', zones['zone1'][1])
    cmd = "sudo virsh domifaddr " + ifdb_master + "|awk 'FNR==3 {print $4}'"
    print(cmd)
    m_ip = execute_command(ifdb_m_conn, cmd).split('/')[0]
    ifdb_s_conn = create_ssh_conn(zones['zone2'][0], 'ece792', zones['zone2'][1])
    cmd = "sudo virsh domifaddr " + ifdb_slave + "|awk 'FNR==3 {print $4}'"
    print(cmd)
    s_ip = execute_command(ifdb_s_conn, cmd).split('/')[0]
    return [m_ip, s_ip]

def delete_the_file(file_name):
    import os
    if os.path.exists(file_name):
        os.remove(file_name)
    return


if __name__ == '__main__':
    parse_input_json(filename)
