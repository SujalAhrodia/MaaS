#! /bin/bash

ip=$(ip a s |grep 172.20.0.4/24)

if [ -z "$ip" ]
then
echo "I am not the master"
else
influxd backup -portable -database collectd ~/infdb_bak
echo "I am the master"
scp -r ~/infdb_bak root@192.168.123.95:~/
ssh root@192.168.123.95  'curl -i -XPOST http://localhost:8086/query --data-urlencode "q=DROP DATABASE collectd" | influxd restore -portable ~/infdb_bak'
sleep 5
echo Removing backup at slave
ssh root@192.168.123.95 'rm -rf ~/infdb_bak'
echo Removing backup at master
rm -rf ~/infdb_bak
fi
