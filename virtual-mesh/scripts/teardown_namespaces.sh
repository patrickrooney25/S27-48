#clean up namespaces and kill background processes

#!/usr/bin/env bash

echo "[-] Deleting network namespaces..."
sudo ip netns del vnode1 2>/dev/null || true
sudo ip netns del vnode2 2>/dev/null || true
sudo ip netns del vnode3 2>/dev/null || true
sudo ip netns del vnode4 2>/dev/null || true
sudo ip netns del vnode5 2>/dev/null || true
sudo ip netns del vnode6 2>/dev/null || true

echo "[-] Removing leftover veth pairs..."
sudo ip link del veth1-2 2>/dev/null || true

echo "[+] Cleanup complete. Environment reset!"