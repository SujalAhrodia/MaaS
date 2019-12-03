count=$(sudo ip netns exec pns iptables -nvL INPUT| grep TRIAL | awk '{print $1}')
echo $count
curl -i -XPOST 'http://192.168.123.95:8086/write?db=collectd' --data-binary 'trial,protocol=tcp value="'"$count"'"'
sudo ip netns exec pns iptables -Z
