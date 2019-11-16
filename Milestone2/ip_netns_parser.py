#!/bin/usr/python3

from subprocess import check_output

# out = check_output("sudo ip netns list", shell=True)

# print(out.decode('utf-8'))

_list = [item.split()[0] for item in check_output("sudo ip netns list", shell=True)
                                        .decode('utf-8')
                                        .split('\n')[:-1]]
# print(_list)

sample_user_data = {
                    'number_of_vms': 1,
                    'number_of_subnets': 1,
                   }
generated_data = {
                   'tenant_id': 1,
                   'subnet_id': 1,
                 }

if 't{0}sr'.format(generated_data['tenant_id']) in _list:
    print('Subnet Router for the tenant exists')
    if 't{0}sn{1}'.format(generated_data['tenant_id'],generated_data['subnet_id']) in _list:
        print('Tenant Router for requested subnet exists')
    else:
        print('Tenant router needs to be created')
else:
    print('This appears to be a brand new tenant')
