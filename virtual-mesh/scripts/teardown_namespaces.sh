#clean up namespaces, control veths, and kill background processes

#!/usr/bin/env bash

echo "[-] Deleting network namespaces (also removes the veths inside them)..."
sudo ip netns del vnode1 2>/dev/null || true
sudo ip netns del vnode2 2>/dev/null || true
sudo ip netns del vnode3 2>/dev/null || true
sudo ip netns del vnode4 2>/dev/null || true
sudo ip netns del vnode5 2>/dev/null || true
sudo ip netns del vnode6 2>/dev/null || true

echo "[-] Removing leftover control veths (root side)..."
sudo ip link del vc1 2>/dev/null || true
sudo ip link del vc2 2>/dev/null || true
sudo ip link del vc3 2>/dev/null || true
sudo ip link del vc4 2>/dev/null || true
sudo ip link del vc5 2>/dev/null || true
sudo ip link del vc6 2>/dev/null || true

echo "[-] Removing control bridge br-ctrl..."
sudo ip link del br-ctrl 2>/dev/null || true

echo "[-] Removing leftover mesh veths (root side)..."
sudo ip link del vm1 2>/dev.null || true
sudo ip link del vm4 2>/dev.null || true

echo "[-] Removing mesh bridge br-mesh..."
sudo ip link del br-mesh 2>/dev/null || true

echo "[+] Cleanup complete. Environment reset!"