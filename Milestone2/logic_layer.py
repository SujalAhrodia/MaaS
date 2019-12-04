import json
import subprocess

replace_flag=False
filename='Testing.json'
tenant=filename[:-5]
tenant_list=[]

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
    z1_host="99.0.0."+str(last_octet)+"/30"
    z1_subnet="99.0.0."+str(last_octet+1)+"/30"
    z2_host="100.0.0."+str(last_octet)+"/30"
    z2_subnet="100.0.0."+str(last_octet+1)+"/30"
    print(z1_host,z1_subnet)
    #ansible_proc=subprocess.Popen('ansible-playbook -i inventory.ini tenant_router.yml --extra-vars z1_host={0},z1_subnet={1},z2_host={2},z2_subnet={3},tid={4}'.format(z1_host,z1_subnet,z2_host,z2_subnet,tenant_id),stdout=subprocess.PIPE,shell=True)
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
            print(subnet_map)
            
        for sn,sn_id in subnet_map.items():
            create_subnet_switch(sn,sn_id)
            create_vxlan_bridge(key,val)
        
        for key,val in vpc_data:
            create_vm(key,val)


if __name__=='__main__':
    create_vpc(replace_flag,tenant)
