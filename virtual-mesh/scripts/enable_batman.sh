#!/bin/bash
# Bind batman-adv (bat0) inside namespaces using B.A.T.M.A.N. V
set -e

sudo modprobe batman-adv

configure_node() {
    local NODE=$1
    shift
    local IFACES=("$@")

    echo "Configuring B.A.T.M.A.N. V on $NODE..."

    # Set routing algorithm to BATMAN_V BEFORE creating bat0
    sudo ip netns exec "$NODE" batctl routing_algo BATMAN_V

    for IFACE in "${IFACES[@]}"; do
        sudo ip netns exec "$NODE" ip link set "$IFACE" down
        sudo ip netns exec "$NODE" batctl meshif bat0 interface add "$IFACE"
        sudo ip netns exec "$NODE" ip link set "$IFACE" up
    done

    sudo ip netns exec "$NODE" ip link set bat0 up
}

configure_node vnode1 veth1-2 veth1-4 msh0
configure_node vnode2 veth2-1 veth2-3 veth2-4 veth2-5
configure_node vnode3 veth3-2 veth3-6
configure_node vnode4 veth4-1 veth4-2 veth4-5 msh0
configure_node vnode5 veth5-2 veth5-4 veth5-6
configure_node vnode6 veth6-3 veth6-5

echo "B.A.T.M.A.N. V setup complete"