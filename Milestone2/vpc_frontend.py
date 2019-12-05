#!/bin/usr/python3

vpc_data_format = {
    "VPC": {
        "VM1": ['1', "10.0.0.0/24"],
        "VM2": ['2', "11.0.0.0/24"],
        "VM3": ['1', "10.0.0.0/24"],
    }
}

service_data_format = {
    'Monitoring': {
        'CPU': True,
        'Memory': True,
        'Interface': False,
        'Traffic_Monitoring': True,
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
        item = items.strip('*.json')
        item = item.strip('-t-')
        if Tenant_name == item:
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
        return (0, 1)
    vpc_data = dict()
    vpc_data['VPC'] = dict()
    for key, value in vm_dict.items():
            vpc_data['VPC'][key] = value
    vpc_data['Monitoring'] = monitoring_dict
    import pprint
    pprint.pprint(vpc_data)
    with open(Tenant_name + '.json', 'a') as f:
        import json
        f.write(json.dumps(vpc_data))
    return (replace_flag, Tenant_name + '.json')


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
        print("Enter the following details for the vpc")
        try:
            number_of_vms = int(input("How many vms do you want to deploy? "))
        except ValueError:
            print('Input was not a number')
            return 1
        vm_dict = dict()
        for i in range(0, number_of_vms):
            vm_dict['VM{}'.format(i + 1)] = []
        for i in range(0, number_of_vms):
            print('\t Input the details for VM: {}'.format(i + 1))
            print('\t\t Choose between Zone 1 and 2 for deployment')
            Zone = input('\t\t 1/2: ')
            if Zone != '1' and Zone != '2':
                print('Undefined Input')
                return 1
            vm_dict['VM{}'.format(i + 1)].append(Zone)
            try:
                subnet_count = int(input("\t\t How many subnets is the VM connected to? "))
            except ValueError:
                print('Input was not a number')
                return 1
            for j in range(0, subnet_count):
                subnet = str(input("\t\t\t Enter the subnet(network) id: "))
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
                vm_dict['VM{}'.format(i + 1)].append(subnet)
        print('\n\n')
        print('Do you want to enable Monitoring services on your VMs?')
        Monitoring = input('\tY/N: ')
        if Monitoring.lower() == 'n':
            Monitoring = False
        elif Monitoring.lower() == 'y':
            Monitoring = True
        else:
            print("Undefined Input")
            return 1
        if Monitoring:
            print("For the monitoring service, please choose the features",
                  "you would like to implement")
            print("\tDo you want to enable CPU monitoring?")
            CPU = False if input("\t\tY/N: ").lower() != 'y' else True
            print("\tDo you want to enable Memory monitoring?")
            Memory = False if input("\t\tY/N: ").lower() != 'y' else True
            print("\tDo you want to enable Interface Traffic monitoring?")
            Interface = False if input("\t\tY/N: ").lower() != 'y' else True
            print("\tDo you want to enable Router Traffic monitoring?")
            Traffic_Monitoring = False if input("\t\tY/N: ").lower() != 'y' else True
            print("\tDo you want to Add a Custom monitoring script?")
            flag = False if input("\t\tY/N: ").lower() != 'y' else True
            print("\t\tEnter the filename for the custom script")
            file = str(input("\t\t\tScript name: "))
            if '.py' not in file:
                flag = False
                print('Script is not a python script. Rejecting and continuing...')
            mon_data = {
                'flag': Monitoring,
                'CPU': CPU,
                'Memory': Memory,
                'Interface': Interface,
                'Traffic_Monitoring': Traffic_Monitoring,
                'Custom': {
                    'flag': flag,
                    'file': file
                }
            }
        else:
            mon_data = {
                'flag': Monitoring
            }
        return (create_json_file(Tenant_name, vm_dict, mon_data, replace_flag))


if __name__ == '__main__':
    (replace_flag, filename) = main()
    if filename == 1:
        print("Error creating json. Try again")
    # print(out)
    print(replace_flag)
    print(filename)
    from logic_layer import create_vpc
    create_vpc(replace_flag, filename)
