#bind batman (bat0) inside namespaces

#!/usr/bin/env bash
set -e #safe exit on error

echo "[+] Loading batman-adv kernel module..."
sudo modprobe batman-adv

#binds interface to batman-adv, creates new virtual mesh interface (bat0)
echo "[+] Binding veth1-2 to batman-adv in vnode1..."
sudo ip netns exec vnode1 batctl dev add veth1-2
sudo ip netns exec vnode1 ip link set dev bat0 up

echo "[+] Binding veth2-1 to batman-adv in vnode2..."
sudo ip netns exec vnode2 batctl dev add veth 2-1
sudo ip netns exec vnode2 ip link set dev bat0 up

echo "[+] BATMAN-adv mesh routing initialized on virtual nodes"