import re
import os
import subprocess
import json
import datetime


def get_current(cmd):
    ret_list = subprocess.check_output(cmd, shell=True)
    ret_list = ret_list.split('\n')
    return ret_list


def get_defined_containers():
    # returns all containers requested by all tenants. These containers will be monitored
    list_files = subprocess.Popen('ls *.json', stdout=subprocess.PIPE,shell=True)
    (out,error)=list_files.communicate()
    print(out,error)
    list_files=out
    print(list_files)
    if list_files:
        list_files = list_files.split('\n')
        cont_list = []
        cont = ''
        for l in list_files:
            if l:
                with open(l) as f:
                    data = json.load(f)
                    #print(data)
                    if data:
                        vm = data['VPC']
                        for k, v in vm.items():
                            if v[0] == 'zone2':
                                tid = re.match(r'.*-(t-\d+).json', l).group(1)
                                cont = tid+k
                                # print(cont)
                        cont_list.append(cont)
                f.close()
        return cont_list
    else:
        return []

if __name__ == '__main__':
    while True:
        want_cont = get_defined_containers()
        if want_cont:
            running_cont = get_current(
                "sudo docker ps -a --filter status=running |awk 'NR!=1 {print $NF}'")
            # print(want_cont,running_cont)
            for a in want_cont:
                if a not in running_cont:
                    msg = a + " was down. Bringing it up...\n"
                    print(msg)
                    os.system("sudo docker container start "+a)
                    if 't' in a:
                        os.system("sudo docker exec "+a+" service ssh start")
                        os.system("sudo docker exec "+a+" service collectd start")
                    elif 'ifdb' in a:
                        os.system("sudo docker exec "+a+" service ssh start")
                        os.system("sudo docker exec "+a+" service influxdb start")
                        os.system("sudo docker exec "+a +
                                  " service  grafana-server start")
                    print("Done")
                    f = open("self_heal.log",'a+')
                    f.write(datetime.datetime.now().strftime(
                        "%H:%M:%S-%d/%m/%Y") + ' ' + msg)
        else:
            break

