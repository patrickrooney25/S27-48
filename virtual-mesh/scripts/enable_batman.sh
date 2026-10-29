#bind batman (bat0) inside namespaces

#!/bin/bash
set -e #safe exit on error

#configure node 1
echo "Configuring batman-adv on vnode1..."
#take down veth 1-2  and 1-4 to modify driver bindings
ip netns exec vnode1 ip link set veth1-2 down
ip netns exec vnode1 ip link set veth1-4 down
#attach v1-2 as a physical interface under bat0 mesh routing
ip netns exec vnode1 batctl meshif bat0 interface add veth1-2
ip netns exec vnode1 batctl meshif bat0 interface add veth1-4
#bring underlying veth interface back online to send/receive frames
ip netns exec vnode1 ip link set veth1-2 up
ip netns exec vnode1 ip link set veth1-4 up
#bring up bat0 virtual mesh interface inside vnode1 namespace
ip netns exec vnode1 ip link set bat0 up

#configure node 2
echo "Configuring batman-adv on vnode2..."
ip netns exec vnode2 ip link set veth2-1 down
ip netns exec vnode2 ip link set veth2-3 down
ip netns exec vnode2 ip link set veth2-4 down
ip netns exec vnode2 ip link set veth2-5 down
ip netns exec vnode2 batctl meshif bat0 interface add veth2-1
ip netns exec vnode2 batctl meshif bat0 interface add veth2-3
ip netns exec vnode2 batctl meshif bat0 interface add veth2-4
ip netns exec vnode2 batctl meshif bat0 interface add veth2-5
ip netns exec vnode2 ip link set veth2-1 up
ip netns exec vnode2 ip link set veth2-3 up
ip netns exec vnode2 ip link set veth2-4 up
ip netns exec vnode2 ip link set veth2-5 up
ip netns exec vnode2 ip link set bat0 up

#configure node 3
echo "Configuring batman-adv on vnode3..."
ip netns exec vnode3 ip link set veth3-2 down
ip netns exec vnode3 ip link set veth3-6 down
ip netns exec vnode3 batctl meshif bat0 interface add veth3-2
ip netns exec vnode3 batctl meshif bat0 interface add veth3-6
ip netns exec vnode3 ip link set veth3-2 up
ip netns exec vnode3 ip link set veth3-6 up
ip netns exec vnode3 ip link set bat0 up

#configure node 4
echo "Configuring batman-adv on vnode4..."
ip netns exec vnode4 ip link set veth4-1 down
ip netns exec vnode4 ip link set veth4-2 down
ip netns exec vnode4 ip link set veth4-5 down
ip netns exec vnode4 batctl meshif bat0 interface add veth4-1
ip netns exec vnode4 batctl meshif bat0 interface add veth4-2
ip netns exec vnode4 batctl meshif bat0 interface add veth4-5
ip netns exec vnode4 ip link set veth4-1 up
ip netns exec vnode4 ip link set veth4-2 up
ip netns exec vnode4 ip link set veth4-5 up
ip netns exec vnode4 ip link set bat0 up

#configure node 5
echo "Configuring batman-adv on vnode5..."
ip netns exec vnode5 ip link set veth5-2 down
ip netns exec vnode5 ip link set veth5-4 down
ip netns exec vnode5 ip link set veth5-6 down
ip netns exec vnode5 batctl meshif bat0 interface add veth5-2
ip netns exec vnode5 batctl meshif bat0 interface add veth5-4
ip netns exec vnode5 batctl meshif bat0 interface add veth5-6
ip netns exec vnode5 ip link set veth5-2 up
ip netns exec vnode5 ip link set veth5-4 up
ip netns exec vnode5 ip link set veth5-6 up
ip netns exec vnode5 ip link set bat0 up

#configure node 6
echo "Configuring batman-adv on vnode6..."
ip netns exec vnode6 ip link set veth6-3 down
ip netns exec vnode6 ip link set veth6-5 down
ip netns exec vnode6 batctl meshif bat0 interface add veth6-3
ip netns exec vnode6 batctl meshif bat0 interface add veth6-5
ip netns exec vnode6 ip link set veth6-3 up
ip netns exec vnode6 ip link set veth6-5 up
ip netns exec vnode6 ip link set bat0 up

echo "Batman-adv setup complete"
