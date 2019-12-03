#!/bin/usr/python3

import json
from subprocess import Popen

mock_input_data = {
    'Tenant1': {
        'Monitoring': True,
        'CPU': True,
        'Memory': True,
        'Interface': False,
        'Traffic Monitoring': True,
        'Custom': {
            'flag': True,
            'file': 'filename'
        }
    }
}


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


def parse_input_json(input_data):
    monitoring_data = list(input_data.values())[0]
    # print(monitoring_data)
    tenant_name = list(input_data.keys())[0]
    # print(Tenant_name)
    tenant_file = get_tenant_vpc_file(tenant_name)
    # print(tenant_file)
    if tenant_file == 0:
        return 'Tenant File Not found. Looking for {}.json'.format(tenant_name)
    with open(tenant_file, 'r') as f:
        tenant_vpc_data = json.loads(''.join(f.readlines()))
    print(tenant_vpc_data)
    tenant_id = tenant_vpc_data[tenant_name]
    ifdb_ip = tenant_vpc_data['Virtual IP']
    vm_id_list = [item for item in tenant_vpc_data.keys() if 'vm' in item]
    # print(tenant_id)
    # print(ifdb_ip)
    # print(vm_id_list)
    if monitoring_data['Monitoring']:
        inventory_file_name = tenant_id + '-inventory.ini'
        delete_the_file(inventory_file_name)
        inventory_file_handler = open(inventory_file_name, 'a')
        inventory_file_handler.write(inventory_header)
        for vm in vm_id_list:
            vm_collectd_file_name = tenant_id + vm + '_collectd.conf'
            vm_ip = tenant_vpc_data[vm][1]
            delete_the_file(vm_collectd_file_name)
            collectd_file_handler = open(vm_collectd_file_name, 'a')
            # print(monitoring_basic_data.format(tenant_id + vm, ifdb_ip))
            collectd_file_handler.write(monitoring_basic_data
                                        .format(tenant_id + vm, ifdb_ip))
            # print(aggregation_plugin_data)
            collectd_file_handler.write(aggregation_plugin_data)
            if monitoring_data['CPU']:
                # print(cpu_plugin_data)
                collectd_file_handler.write(cpu_plugin_data)
            if monitoring_data['Memory']:
                # print(memory_plugin_data)
                collectd_file_handler.write(memory_plugin_data)
            if monitoring_data['Interface']:
                # print('LoadPlugin interface')
                collectd_file_handler.write('LoadPlugin interface')
            if monitoring_data['Traffic Monitoring']:
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
                q = Popen('ansible-playbook router_logging.yml -i {0} --extra-vars netns_name={1}'
                          .format('inventory.ini',
                                  tenant_id + 'sr'),
                          shell=True)
                (output, err) = q.communicate()
                q.wait()
                print(output)
                monitoring_data['Traffic Monitoring'] = False
            collectd_file_handler.close()
            temp = vm_ip + ' ' + inventory_common_data + '\n'
            inventory_file_handler.write(temp)
            inventory_file_handler.close()
            p = Popen('ansible-playbook setup_collectd.yml -i {0} --extra-vars collectd_file={1}'
                      .format(inventory_file_name, vm_collectd_file_name),
                      shell=True)
            (output, err) = p.communicate()
            p.wait()
            print(output)
    else:
        print('Tenant has chosen not to enable monitoring')


def get_tenant_vpc_file(Tenant_name):
    import glob
    list_of_files = glob.glob("*.json")
    for items in list_of_files:
        if Tenant_name in items:
            return list_of_files[list_of_files.index(items)]
    return 0


def delete_the_file(file_name):
    import os
    if os.path.exists(file_name):
        os.remove(file_name)
    return


if __name__ == '__main__':
    parse_input_json(mock_input_data)
