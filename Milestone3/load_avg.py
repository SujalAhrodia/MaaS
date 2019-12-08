#!/usr/bin/env python3

#LOGGING THE LOAD AVERAGES

import collectd
import subprocess 
import os

def configer(confObj):
    collectd.info('config called')

def init_fun():
    collectd.info('my py module init called')

def reader():
    collectd.info('reader called')
    cmd = "uptime | awk '{print $9 $10 $11}'"
    collectd.info('cmd called')
    # os.system("uptime | awk '{print $8 $9 $10}' > /opt/custom_plugins/data.txt")
    out = ''
    with open('/opt/custom_plugins/sysdata.txt', 'r') as f:
        out = f.readline()
    # p2 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    collectd.info('poen called')
    # (out, err) = p2.communicate()
    a,b,c = out.split('\n')[0].split(',')
    a = float(a)
    b = float(b)
    c = float(c)
    collectd.info('decoded ')

    # Dispatch value to collectd
    val = collectd.Values(type='load')
    val.plugin = 'load_avg'
    val.dispatch(values=[a, b, c])

collectd.register_config(configer)
collectd.register_init(init_fun)
collectd.register_read(reader)