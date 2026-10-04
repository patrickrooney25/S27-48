#shell script to create ip netns and veth pairs

#!/usr/bin/env bash

set -e # allows for safe exiting on an error

#creates independent, isolated virtual network namespaces
echo "[+] Creating network namespaces (vnode1, vnode2)..."
sudo ip netns add vnode1
sudo ip netns add vnode2

#creates virtual ethernet pair (creates cable)
#veth1-2 is End A, veth2-1 is End B
echo "[+] Creating virtual ethernet pair (veth1-2, veth2-1)..."
sudo ip link add veth1-2 type veth peer name veth2-1 

# takes End A and pushes it vnode1's private room
#takes End B and pushes it vnode2's private room
echo "[+] Moving veth ends into namespaces..."
sudo ip link set veth1-2 netns vnode1
sudo ip link set veth2-1 netns vnode2

#turns network ports on and sets up loopback interface for internal self communication
echo "[+] Bringing up loopback and veth interfaces..."
sudo ip netns exec vnode1 ip link set dev lo up
sudo ip netns exec vnode1 ip link set dev veth1-2 up

sudo ip netns exec vnode2 ip link set dev lo up
sudo ip netns exec vnode2 ip link set dev veth2-1 up

echo "[+] Success. vnode1 and vnode2 are created and connected."