#!/usr/bin/env python3
# automates link degradation for batman nodes running inside Linux network namespaces

import csv
import os
import re
import subprocess
import sys
import time

# ==========================================
# EXPERIMENT CONFIGURATION
# ==========================================
# Monitored Endpoints: Measure route from SRC to DST
SRC = 1  # Namespace: vnode1
DST = 6  # Namespace: vnode6

# Targeted Physical Link for Fault Injection:
# Degrades the link between vnode1 and vnode2 to trigger reroute through vnode4
DEG_A = 1
DEG_B = 2

# Phase durations (in seconds)
BASELINE_S = 30
DEGRADE_S = 120
RECOVER_S = 120

# Loss sweep levels
LOSS_LEVELS = [10, 30, 50, 100]

# Directory to save logs
OUTPUT_DIR = "TQ_EXPS"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MAC address regex pattern
MAC_PATTERN = r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"


def run_cmd(cmd):
    """Executes a bash command and returns stdout."""
    print(f"[EXEC] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and "No such file or directory" not in result.stderr:
        err = result.stderr.strip()
        if err:
            print(f"[ERROR] {err}")
    return result.stdout.strip()


def apply_degradation(netns, interface, delay_ms=0, loss_pct=0, jitter_ms=0):
    """Applies synthetic latency and loss using tc netem."""
    tc_args = []
    if delay_ms > 0:
        if jitter_ms > 0:
            tc_args.append(f"delay {delay_ms}ms {jitter_ms}ms")
        else:
            tc_args.append(f"delay {delay_ms}ms")
    if loss_pct > 0:
        tc_args.append(f"loss {loss_pct}%")

    if not tc_args:
        print(f"[INFO] No degradation parameters specified for {interface}.")
        return

    params = " ".join(tc_args)
    # Clear existing qdisc to avoid conflicts
    run_cmd(f"sudo ip netns exec {netns} tc qdisc del dev {interface} root 2>/dev/null")
    # Apply new rule
    run_cmd(f"sudo ip netns exec {netns} tc qdisc add dev {interface} root netem {params}")
    print(f"[SUCCESS] Applied tc netem ({params}) on {interface} in {netns}")


def clear_degradation(netns, interface):
    """Clears tc netem queue discipline on an interface."""
    run_cmd(f"sudo ip netns exec {netns} tc qdisc del dev {interface} root 2>/dev/null")


def degrade_link(a, b, loss_pct=0, delay_ms=0, jitter_ms=0):
    """Applies symmetrical degradation between two nodes."""
    apply_degradation(f"vnode{a}", f"veth{a}-{b}", delay_ms=delay_ms, loss_pct=loss_pct, jitter_ms=jitter_ms)
    apply_degradation(f"vnode{b}", f"veth{b}-{a}", delay_ms=delay_ms, loss_pct=loss_pct, jitter_ms=jitter_ms)


def clear_link(a, b):
    """Clears degradation between two nodes symmetrically."""
    clear_degradation(f"vnode{a}", f"veth{a}-{b}")
    clear_degradation(f"vnode{b}", f"veth{b}-{a}")


def get_target_mac(target_node):
    """
    Returns the primary originator MAC for a target node.
    Batman-adv uses the MAC of the node's primary underlying interface.
    """
    # Ask batman-adv directly what the primary interface / originator MAC is for this node
    header = run_cmd(f"sudo ip netns exec vnode{target_node} batctl o")
    match = re.search(r"MainIF/MAC:\s*[^/]+/(" + MAC_PATTERN + r")", header)
    if match:
        return match.group(1).lower()

    # Fallback to the first non-lo, non-bat interface
    mac = run_cmd(
        f"sudo ip netns exec vnode{target_node} ip -o link show | awk '$2 !~ /^(lo|bat)/ {{print $17; exit}}'"
    )
    return mac.strip().lower()


def read_active_quality(netns, target_mac):
    """
    Parses batctl o for the active next-hop, TQ, and egress interface.
    Handles multi-line wrapping in batctl output.
    """
    output = run_cmd(f"sudo ip netns exec {netns} batctl o")
    
    # Normalize whitespaces so wrapped lines merge cleanly
    normalized = " ".join(output.split())

    # Look for active routes marked with '*'
    # Example format: * <orig_mac> <last-seen>s (<TQ>) <nexthop> [ <outgoing_if> ]
    pattern = (
        r"\*\s*(" + MAC_PATTERN + r")\s+[\d.]+s\s+\(\s*(\d+)\s*\)\s+(" + MAC_PATTERN + r")\s+\[\s*([^\]\s]+)\s*\]"
    )

    for match in re.finditer(pattern, normalized, re.IGNORECASE):
        orig, tq, nexthop, outgoing_if = match.groups()
        if orig.lower() == target_mac.lower():
            return int(tq), nexthop.lower(), outgoing_if

    return None, "none", "unknown"


def run_experiment(loss_pct):
    """Runs a 3-phase degradation cycle and writes metric updates to CSV."""
    filename = os.path.join(OUTPUT_DIR, f"tq_loss_{loss_pct}pct.csv")
    total_s = BASELINE_S + DEGRADE_S + RECOVER_S
    target_mac = get_target_mac(DST)

    print(f"\n==========================================")
    print(f"Starting Run: {loss_pct}% Loss on Link vnode{DEG_A} <-> vnode{DEG_B}")
    print(f"Monitoring Path: vnode{SRC} -> vnode{DST} (MAC: {target_mac})")
    print(f"==========================================")

    # Clean up state before starting
    clear_link(DEG_A, DEG_B)
    curr_loss = 0
    start = time.time()

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["time_s", "TQ", "loss_pct", "nexthop", "outgoing_if"])

        elapsed = 0
        while elapsed < total_s:
            # Phase 2: Inject Loss
            if elapsed >= BASELINE_S and curr_loss == 0 and elapsed < (BASELINE_S + DEGRADE_S):
                degrade_link(DEG_A, DEG_B, loss_pct=loss_pct)
                curr_loss = loss_pct

            # Phase 3: Recovery / Clear Loss
            if elapsed >= (BASELINE_S + DEGRADE_S) and curr_loss != 0:
                clear_link(DEG_A, DEG_B)
                curr_loss = 0

            # Measure & log
            tq, nexthop, outgoing_if = read_active_quality(f"vnode{SRC}", target_mac)
            writer.writerow([round(elapsed, 1), tq, curr_loss, nexthop, outgoing_if])
            file.flush()

            time.sleep(1)
            elapsed = time.time() - start

    # Settle down link
    clear_link(DEG_A, DEG_B)
    print(f"[SUCCESS] Saved data to {filename}")


def export_data():
    for loss in LOSS_LEVELS:
        run_experiment(loss)


if __name__ == "__main__":
    print("--- Starting 6-Node TQ Experiment ---")
    export_data()
    print("--- All Experiments Complete ---")