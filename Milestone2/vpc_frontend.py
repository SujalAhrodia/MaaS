#!/bin/usr/python3

vpc_data_format = {
    "TenantName": {
        "VPC": True,
        "Zone1": {
            "VM1": ["10.0.0.0/24"],
            "VM2": ["11.0.0.0/24"],
        },
        "Zone2": {
            "VM3": ["10.0.0.0/24"],
        }
    }
}

service_data_format = {
    'TenantName': {
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


def get_tenant_vpc_file(Tenant_name):
    import glob
    list_of_files = glob.glob("*.json")
    for items in list_of_files:
        if Tenant_name in items:
            return list_of_files[list_of_files.index(items)]
    return 0


def create_tenant_id():
    import glob
    list_of_files = glob.glob('*.json')
    count = 0
    for item in list_of_files:
        if '-t' in item:
            count += 1
    return count + 1


def create_json_file(Tenant_name, vm_dict, monitoring_dict, replace_flag):
    if replace_flag:
        print('Unsupported deployment ATM')
        return 1
    vpc_data = dict()
    vpc_data['VPC'] = dict()
    for key, value in vm_dict.items():
            vpc_data['VPC'][key] = value
    vpc_data['Monitoring'] = dict()
    import pprint
    pprint.pprint(vpc_data)
    with open(Tenant_name + '.json', 'a') as f:
        import json
        f.write(json.dumps(vpc_data))
    return 0


def main():
    Tenant_name = input("Please enter your vpc deployment name (Tenant Name):")
    tenant_file = get_tenant_vpc_file(Tenant_name)
    replace_flag = False
    Monitoring = False
    if tenant_file != 0:
        print("A file with this name already exists.\n",
              "Are you modifying the deployment?")
        replace_flag = str(input("Y/N:"))
        if replace_flag.lower() == 'n':
            print("Please rerun with a different Tenant Name")
            return 1
        elif replace_flag.lower() == 'y':
            replace_flag = True
        else:
            print("Undefined Input")
            return 1
    else:
        VPC = True
        print("Enter the following details for the vpc")
        try:
            number_of_vms = int(input("How many vms do you want to deploy? "))
        except ValueError:
            print('Input was not a number')
            return 1
        vm_dict = dict()
        for i in range(0, number_of_vms):
            vm_dict['VM{}'.format(i)] = []
        for i in range(0, number_of_vms):
            print('\t Input the details for VM: {}'.format(i + 1))
            print('\t\t Choose between Zone 1 and 2 for deployment')
            Zone = input('\t\t 1/2: ')
            if Zone != '1' and Zone != '2':
                print('Undefined Input')
                return 1
            vm_dict['VM{}'.format(i)].append(Zone)
            try:
                subnet_count = int(input("\t\t How many subnets is the VM connected to? "))
            except ValueError:
                print('Input was not a number')
                return 1
            for j in range(0, subnet_count):
                subnet = str(input("\t\t\t Enter the subnet id: "))
                if '/' not in subnet:
                    print("No Mask found")
                    return 1
                subnet_last_octet = subnet.split('.')[3].split('/')
                if subnet_last_octet[0] != '0':
                    print('Subnet not supported')
                    return 1
                if subnet_last_octet[1] != '24':
                    print('Subnet not supported')
                    return 1
                vm_dict['VM{}'.format(i)].append(subnet)
        print('\n\n')
        print('Do you want to enable Monitoring services on your VMs?')
        Monitoring = input('\tY/N: ')
        Monitoring_dict = dict()
        if Monitoring.lower() == 'n':
            Monitoring = False
        elif Monitoring.lower() == 'y':
            Monitoring = True
        else:
            print("Undefined Input")
            return 1
        return (create_json_file(Tenant_name, vm_dict, Monitoring_dict, replace_flag))


if __name__ == '__main__':
    out = main()
    if out == 1:
        print("Error creating json. Try again")
    print(out)
