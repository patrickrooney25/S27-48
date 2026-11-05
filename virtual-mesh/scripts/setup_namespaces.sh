#shell script to create ip netns and veth pairs

#!/usr/bin/env bash

set -e # allows for safe exiting on an error

#creates independent, isolated virtual network namespaces
echo "[+] Creating network namespaces (vnode1, vnode2)..."
sudo ip netns add vnode1
sudo ip netns add vnode2
sudo ip netns add vnode3
sudo ip netns add vnode4
sudo ip netns add vnode5
sudo ip netns add vnode6

#creates virtual ethernet pairs (creates cable)
echo "[+] Creating virtual ethernet pairs matching proposed topology"
sudo ip link add veth1-2 type veth peer name veth2-1 
sudo ip link add veth1-4 type veth peer name veth4-1 

sudo ip link add veth2-3 type veth peer name veth3-2 
sudo ip link add veth2-4 type veth peer name veth4-2 
sudo ip link add veth2-5 type veth peer name veth5-2 

sudo ip link add veth3-6 type veth peer name veth6-3

sudo ip link add veth4-5 type veth peer name veth5-4 

sudo ip link add veth6-5 type veth peer name veth5-6

echo "[+] Moving veth ends into target namespaces..."
#vnode1
sudo ip link set veth1-2 netns vnode1
sudo ip link set veth1-4 netns vnode1
#vnode2
sudo ip link set veth2-1 netns vnode2
sudo ip link set veth2-3 netns vnode2
sudo ip link set veth2-4 netns vnode2
sudo ip link set veth2-5 netns vnode2
#vnode3
sudo ip link set veth3-2 netns vnode3
sudo ip link set veth3-6 netns vnode3
#vnode4
sudo ip link set veth4-1 netns vnode4
sudo ip link set veth4-2 netns vnode4
sudo ip link set veth4-5 netns vnode4
#vnode5
sudo ip link set veth5-2 netns vnode5
sudo ip link set veth5-4 netns vnode5
sudo ip link set veth5-6 netns vnode5
#vnode6
sudo ip link set veth6-3 netns vnode6
sudo ip link set veth6-5 netns vnode6

#turns network ports on and sets up loopback interface for internal self communication
echo "[+] Bringing up loopback and veth interfaces..."
#vnode1
sudo ip netns exec vnode1 ip link set dev lo up
sudo ip netns exec vnode1 ip link set dev veth1-2 up
sudo ip netns exec vnode1 ip link set dev veth1-4 up
#vnode2
sudo ip netns exec vnode2 ip link set dev lo up
sudo ip netns exec vnode2 ip link set dev veth2-1 up
sudo ip netns exec vnode2 ip link set dev veth2-3 up
sudo ip netns exec vnode2 ip link set dev veth2-4 up
sudo ip netns exec vnode2 ip link set dev veth2-5 up
#vnode3
sudo ip netns exec vnode3 ip link set dev lo up
sudo ip netns exec vnode3 ip link set dev veth3-2 up
sudo ip netns exec vnode3 ip link set dev veth3-6 up
#vnode4
sudo ip netns exec vnode4 ip link set dev lo up
sudo ip netns exec vnode4 ip link set dev veth4-1 up
sudo ip netns exec vnode4 ip link set dev veth4-2 up
sudo ip netns exec vnode4 ip link set dev veth4-5 up
#vnode5
sudo ip netns exec vnode5 ip link set dev lo up
sudo ip netns exec vnode5 ip link set dev veth5-2 up
sudo ip netns exec vnode5 ip link set dev veth5-4 up
sudo ip netns exec vnode5 ip link set dev veth5-6 up
#vnode6
sudo ip netns exec vnode6 ip link set dev lo up
sudo ip netns exec vnode6 ip link set dev veth6-3 up
sudo ip netns exec vnode6 ip link set dev veth6-5 up

echo "[+] Success. vnode1-vnode6 are created and connected."

echo "[+] Creating control bridge br-ctrl (10.10.0.1/24)..."
sudo ip link add br-ctrl type bridge
sudo ip addr add 10.10.0.1/24 dev br-ctrl
sudo ip link set br-ctrl up

echo "[+] Attaching each vnode to br-ctrl..."
for N in {1..6}; do
    #create veth control cable for nodes to attach to br-ctrl 
    #(br-ctrl <- vc# <-> vc#-ns -> node#)
    sudo ip link add vc$N type veth peer name vc$N-ns
    
    #attatch root end (vc#) into bridge and turn on 
    sudo ip link set vc$N master br-ctrl
    sudo ip link set vc$N up

    #attach other end (vc#-ns) to node so plug can be inside namepsace
    #rename to ctl0 (control intferface 0) so all nodes can be connected simply to one root
    sudo ip link set vc$N-ns netns vnode$N name ctl0

    #give it an address (10.10.0.11 .. 10.10.0.16) and turn it on
    sudo ip netns exec vnode$N ip addr add 10.10.0.$((10 + N))/24 dev ctl0
    sudo ip netns exec vnode$N ip link set dev ctl0 up
done

echo "[+] Success. vnode1-vnode6 are connected to control bridge ctl0."

echo "[+] Creating mesh bridge br-mesh (layer 2 only, no IP)..."
sudo ip link add br-mesh type bridge
sudo ip link set br-mesh up

echo "[+] Attaching gateway vnodes (1 & 4) to br-mesh..."
for N in 1 4; do
    #create veth mesh cable for nodes to attach to br-mesh
    #(br-mesh <- vm# <-> vm#-ns -> node#)
    sudo ip link add vm$N type veth peer name vm$N-ns
    
    #attatch root end (vm#) into bridge and turn on 
    sudo ip link set vm$N master br-mesh
    #isolate so v1 & v4 dont communicate through the bridge
    sudo bridge link set dev vm$N isolated on 
    sudo ip link set vm$N up

    #attach other end (vm#-ns) to node so plug can be inside namepsace
    #rename to ctl0 so all nodes can be connected simply to one root
    sudo ip link set vm$N-ns netns vnode$N name msh0
    sudo ip netns exec vnode$N ip link set dev msh0 up
done

echo "[+] Success. Gateway nodes are connected to the mesh bridge."


