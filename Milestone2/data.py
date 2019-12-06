#!/usr/bin/env python3

import subprocess

cmd = "uptime"
p2 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
(out, err) = p2.communicate()
out=out.split()[-3:]

with open('/opt/custom_plugins/sysdata.txt','w') as f:
    for i in out:
        f.write(i)
