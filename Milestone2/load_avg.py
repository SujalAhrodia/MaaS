#!/bin/python

#LOGGING THE LOAD AVERAGES

import collectd
import subprocess 

def configer(confObj):
    collectd.info('config called')

def init_fun():
    collectd.info('my py module init called')

def reader():
    collectd.info('reader called')
    cmd = "uptime | awk '{print $9 $10 $11}'"
    # p2 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    collectd.info('poen called')

    # (out, err) = p2.communicate()
    # a,b,c = out.decode("utf-8").split('\n')[0].split(',')
    # a = float(a)
    # b = float(b)
    # c = float(c)
    a=0.01
    b=0.01
    c=0.01
    collectd.info('decoded ')

    # Dispatch value to collectd
    val = collectd.Values(type='load')
    val.plugin = 'load_avg'
    val.dispatch(values=[a, b, c])

collectd.register_config(configer)
collectd.register_init(init_fun)
collectd.register_read(reader)