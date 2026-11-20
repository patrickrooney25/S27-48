#!/usr/bin/env bash
# Shell script to emulate two physical gateway Pis (pnode1, pnode2)

set -e # allows for safe exiting on an error

# Creates independent, isolated virtual network namespaces
echo "[+] Creating network namespaces (pnode1, pnode2)..."
sudo ip netns add pnode1
sudo ip netns add pnode2

# Creates virtual ethernet pairs (creates cable)
echo "[+] Creating virtual ethernet pairs..."
# Stand-in for the 802.11s wireless link between the two Pis
sudo ip link add pw1 type veth peer name pw2
# Wired links from each Pi to br-mesh (stand-in for laptop eth1 / eth2)
sudo ip link add pe1 type veth peer name pe1-ns
sudo ip link add pe2 type veth peer name pe2-ns

echo "[+] Moving veth ends into target namespaces and renaming them..."
# pnode1
sudo ip link set pw1 netns pnode1 name wlan1
sudo ip link set pe1-ns netns pnode1 name eth0
# pnode2
sudo ip link set pw2 netns pnode2 name wlan1
sudo ip link set pe2-ns netns pnode2 name eth0

echo "[+] Attaching pnode cables to br-mesh (not isolated)..."
sudo ip link set pe1 mtu 1532
sudo ip link set pe2 mtu 1532
sudo ip link set pe1 master br-mesh
sudo ip link set pe2 master br-mesh
sudo ip link set pe1 up
sudo ip link set pe2 up

# MTU 1532 leaves room for the batman-adv header (same as the Pi doc)
echo "[+] Setting MTU on pnode interfaces..."
sudo ip netns exec pnode1 ip link set dev eth0 mtu 1532
sudo ip netns exec pnode1 ip link set dev wlan1 mtu 1532
sudo ip netns exec pnode2 ip link set dev eth0 mtu 1532
sudo ip netns exec pnode2 ip link set dev wlan1 mtu 1532

# Turns network ports on and sets up loopback interface
echo "[+] Bringing up loopback and interfaces..."
# pnode1
sudo ip netns exec pnode1 ip link set dev lo up
sudo ip netns exec pnode1 ip link set dev eth0 up
sudo ip netns exec pnode1 ip link set dev wlan1 up
# pnode2
sudo ip netns exec pnode2 ip link set dev lo up
sudo ip netns exec pnode2 ip link set dev eth0 up
sudo ip netns exec pnode2 ip link set dev wlan1 up

echo "[+] Setting up B.A.T.M.A.N. V on pnode1..."
sudo ip netns exec pnode1 batctl routing_algo BATMAN_V
sudo ip netns exec pnode1 ip link set eth0 down
sudo ip netns exec pnode1 batctl meshif bat0 interface add eth0
sudo ip netns exec pnode1 ip link set eth0 up
sudo ip netns exec pnode1 ip link set wlan1 down
sudo ip netns exec pnode1 batctl meshif bat0 interface add wlan1
sudo ip netns exec pnode1 ip link set wlan1 up
sudo ip netns exec pnode1 ip link set bat0 up

echo "[+] Setting up B.A.T.M.A.N. V on pnode2..."
sudo ip netns exec pnode2 batctl routing_algo BATMAN_V
sudo ip netns exec pnode2 ip link set eth0 down
sudo ip netns exec pnode2 batctl meshif bat0 interface add eth0
sudo ip netns exec pnode2 ip link set eth0 up
sudo ip netns exec pnode2 ip link set wlan1 down
sudo ip netns exec pnode2 batctl meshif bat0 interface add wlan1
sudo ip netns exec pnode2 ip link set wlan1 up
sudo ip netns exec pnode2 ip link set bat0 up

echo "[+] Success. pnode1 and pnode2 are created and joined to the mesh."
echo "[+] Check with: sudo ip netns exec vnode1 batctl o"