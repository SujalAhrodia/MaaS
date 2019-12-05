#! /bin/bash

ip=$(ip a s |grep 192.168.123.2/24)

if [ -z "$ip" ]
then
echo "I am not the master"
else
influxd backup -portable -database collectd ~/infdb_bak
echo "I am the master"
scp -r ~/infdb_bak root@192.168.123.226:~/
ssh -o StrictHostKeyChecking=no root@192.168.123.226  'curl -i -XPOST http://localhost:8086/query --data-urlencode "q=DROP DATABASE collectd" | influxd restore -portable ~/infdb_bak'
sleep 5
echo Removing backup at slave
ssh root@192.168.123.226 'rm -rf ~/infdb_bak'
echo Removing backup at master
rm -rf ~/infdb_bak
fi
