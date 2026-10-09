#shell script to create ip netns and veth pairs

#!/usr/bin/env bash

set -e # allows for safe exiting on an error

#creates independent, isolated virtual network namespaces
echo "[+] Creating network namespaces (vnode1, vnode2)..."
sudo ip netns add vnode1
sudo ip netns add vnode2
sudo ip netns add vnode3

#creates virtual ethernet pair (creates cable)
#veth1-2 is End A, veth2-1 is End B
echo "[+] Creating virtual ethernet pairs for triangle topology"
sudo ip link add veth1-2 type veth peer name veth2-1 
sudo ip link add veth1-3 type veth peer name veth3-1
sudo ip link add veth2-3 type veth peer name veth3-2


echo "[+] Moving veth ends into target namespaces..."
#vnode1
sudo ip link set veth1-2 netns vnode1
sudo ip link set veth1-3 netns vnode1
#vnode2
sudo ip link set veth2-1 netns vnode2
sudo ip link set veth2-3 netns vnode2
#vnode3
sudo ip link set veth3-1 netns vnode3
sudo ip link set veth3-2 netns vnode3

#turns network ports on and sets up loopback interface for internal self communication
echo "[+] Bringing up loopback and veth interfaces..."
#vnode1
sudo ip netns exec vnode1 ip link set dev lo up
sudo ip netns exec vnode1 ip link set dev veth1-2 up
sudo ip netns exec vnode1 ip link set dev veth1-3 up
#vnode2
sudo ip netns exec vnode2 ip link set dev lo up
sudo ip netns exec vnode2 ip link set dev veth2-1 up
sudo ip netns exec vnode2 ip link set dev veth2-3 up
#vnode3
sudo ip netns exec vnode3 ip link set dev lo up
sudo ip netns exec vnode3 ip link set dev veth3-1 up
sudo ip netns exec vnode3 ip link set dev veth3-2 up

echo "[+] Success. vnode1, vnode2, and vnode3 are created and connected."