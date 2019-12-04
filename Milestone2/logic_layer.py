import json
import subprocess
import libvirt

replace_flag=False
filename='Testing.json'
tenant=filename[:-5]
tenant_list=[]
zones={'1':['zone1','176.16.3.1'],'2':['zone2','176.16.3.2']}

def create_tenant_id():
    import glob
    list_of_files = glob.glob('*.json')
    count = 0
    for item in list_of_files:
        if '-t-' in item:
            count += 1
    return count + 1

def create_tenant_subnet_router(tenant_id,flag):
    if not flag:
        return
    last_octet=(4*int(tenant_id[-1]))-3
    z1_network_id = "99.0.0." + str(last_octet - 1) + "/30"
    z2_network_id = "100.0.0." + str(last_octet - 1) + "/30"
    z1_host="99.0.0."+str(last_octet)
    z1_subnet="99.0.0."+str(last_octet+1)
    z2_host="100.0.0."+str(last_octet)
    z2_subnet="100.0.0."+str(last_octet+1)
    print(z1_host,z1_subnet)
    #ansible_proc=subprocess.Popen('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars "z1_host={0},z1_subnet={1},z2_host={2},z2_subnet={3},tid={4},z1_nid={5},z2_nid={6}"'.format(z1_host,z1_subnet,z2_host,z2_subnet,tenant_id,z1_network_id,z2_network_id),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()

def create_subnet_switch(sn,sn_id,tenant_id,flag):
    if not flag:
        return
    sn_octets=sn.split('.')
    prefix='.'.join(s for s in sn_octets[:-1]) + '.'
    #gives '10.0.0.' from '10.0.0.0/24'
    print(prefix)
    last_octet=(4*int(tenant_id[-1]))-3
    z1_subnet="99.0.0."+str(last_octet+1)
    #ansible_proc=subprocess.Popen('ansible-playbook -i inventory.ini subnet_switch.yml --extra-vars "tid={0},prefix={1},snid={2},z1_subnet={3}"'.format(tenant_id,prefix,sn_id,z1_subnet),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()
    

def list_vms():
    import libvirt
    conn = libvirt.open('qemu:///system')
    return conn.listDefinedDomains()


def create_vm(vm_id, zone_id, flag):
    if not flag:
        return
    zone = zones[zone_id][0]
    #ansible_proc=subprocess.Popen('ansible-playbook {0} spawn_vm.yml --extra-vars "vmid={1}"'.format(zone, vm_id),stdout=subprocess.PIPE,shell=True)
    #(out,error)=ansible_proc.communicate()

def create_vpc(replace_flag,tenant):
    if not replace_flag:
        print('New tenant')
        sr_process=subprocess.Popen('sudo ip netns list',stdout=subprocess.PIPE,shell=True)
        (sr_list,error)=sr_process.communicate()
        sr_list=sr_list.decode('utf-8').split('\n')
        tenant_id="t-"+str(create_tenant_id())
        print(tenant_id,sr_list)
        create_sr_flag=False if tenant_id+"sr" in sr_list else True
        print(create_sr_flag)
        create_tenant_subnet_router(tenant_id,create_sr_flag)
        print('TENANT SR CREATED')
        vpc_data=[]
        subnet_map={}
        with open(filename) as json_file:
            data = json.load(json_file)
            vpc_data = data['VPC']
            mon_data = data['Monitoring']
            print(vpc_data)
            subnets = set()
            for val in vpc_data.values():
                for sn in val[1:]:
                    subnets.add(sn)
                    #adds unique subnets only
            count = 1
            for sn in subnets:
                sn_id = "sn"+(str(count))
                subnet_map.update({sn: sn_id})
                count += 1
            #print(subnet_map)
            
        for sn,sn_id in subnet_map.items():
            sn_create_flag = False if tenant_id + sn_id in sr_list else True
            create_subnet_switch(sn,sn_id,tenant_id,sn_create_flag)
        
        state_data={}
        for key,val in vpc_data.items():
            state_data[key]=[zones[val[0]][0],0]
            state_data[key].extend([0 for i in range(len(subnet_map.keys()))])
        print(state_data)

        for key,val in vpc_data.items():
            vm_id=tenant_id+key
            vm_list=list_vms()
            create_vm_flag=False if vm_id in vm_list else True
            create_vm(vm_id,vpc_data[key][0],create_vm_flag)
            for subnet in val[1:]:
                s_ref=int(subnet_map[subnet][-1])+1
                count=2
                for val in state_data.values():
                    if val[s_ref]!=0:
                        count+=1
                sn_octets=subnet.split('.')
                prefix='.'.join(s for s in sn_octets[:-1]) + '.'
                ip=subnet+str(count)







if __name__=='__main__':
    create_vpc(replace_flag,tenant)
