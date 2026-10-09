#bind batman (bat0) inside namespaces

#!/bin/bash
set -e #safe exit on error

#configure node 1
echo "Configuring batman-adv on vnode1..."
#take down veth 1-2  and 1-3to modify driver bindings
ip netns exec vnode1 ip link set veth1-2 down
ip netns exec vnode1 ip link set veth1-3 down
#attach v1-2 as a physical interface under bat0 mesh routing
ip netns exec vnode1 batctl meshif bat0 interface add veth1-2
ip netns exec vnode1 batctl meshif bat0 interface add veth1-3
#bring underlying veth interface back online to send/receive frames
ip netns exec vnode1 ip link set veth1-2 up
ip netns exec vnode1 ip link set veth1-3 up
#bring up bat0 virtual mesh interface inside vnode1 namespace
ip netns exec vnode1 ip link set bat0 up

#configure node 2
echo "Configuring batman-adv on vnode2..."
ip netns exec vnode2 ip link set veth2-1 down
ip netns exec vnode2 ip link set veth2-3 down
ip netns exec vnode2 batctl meshif bat0 interface add veth2-1
ip netns exec vnode2 batctl meshif bat0 interface add veth2-3
ip netns exec vnode2 ip link set veth2-1 up
ip netns exec vnode2 ip link set veth2-3 up
ip netns exec vnode2 ip link set bat0 up

#configure node 3
echo "Configuring batman-adv on vnode3..."
ip netns exec vnode3 ip link set veth3-1 down
ip netns exec vnode3 ip link set veth3-2 down
ip netns exec vnode3 batctl meshif bat0 interface add veth3-1
ip netns exec vnode3 batctl meshif bat0 interface add veth3-2
ip netns exec vnode3 ip link set veth3-1 up
ip netns exec vnode3 ip link set veth3-2 up
ip netns exec vnode3 ip link set bat0 up

echo "Batman-adv setup complete"
