## ECE 4805/4806 Major Design Experience (MDE)
**Group:** S27-48  
**Project Name:** Resilient Mesh Network Testbed for Mobile/Ad-Hoc Nodes  
**Sponsor:** Idaho National Labs (INL)  

## Team and Stakeholders

**Senior Design Team Members**  
* Alex Boulay: Project Lead and Testing
* Alex Parlow: Networkingg, Research, Physical Nodes
* Archer Snell: Physical Nodes and Hardware
* Camden Lippy: Budgeting and Testing
* Patrick Rooney: Scheduling, Fronted, Virtual Nodes
* Quentin Tran: Documentation

**Sponsor and Mentor**
* INL: Nicholas Kaminski, April Augustine
* Faculty Mentor: Dr. Joe Adams

---

## Project Overview

Swarm operations using Unmanned Aerial Vehicles (UAVs) in infrastructure-light or disaster environments rely on resilient mobile ad-hoc networks (MANETs). As nodes move, join, or abruptly drop due to power failure, jamming, or physical loss, the network must automatically detect topology changes and reroute traffic.

This project implements a hybrid physical/virtual ground-based testbed that emulates UAV swarm connectivity challenges without requiring flight. The system combines physical Raspberry Pi mobile nodes with software-emulated virtual nodes running inside Linux network namespaces, evaluating mesh protocol self-healing and measuring reconvergence metrics.

---

## System Architecture

The testbed consists of three primary subsystems:

1. **Physical Mesh Subsystem:** 4 battery-powered mobile ground carriers housing Raspberry Pis. Each node runs `batman-adv` (OSI Layer 2) over 2.4 GHz Wi-Fi (`wlan0`).
2. **Virtual Mesh Subsystem:** A Linux Emulation Host running up to 6 virtual nodes isolated inside network namespaces (`ip netns`). Virtual nodes execute independent `batman-adv` kernel instances connected via virtual Ethernet (`veth`) pairs, with link degradation managed by a dynamic Python `tc netem` orchestrator.
3. **Out-of-Band Control & Dashboard:** A isolated secondary network channel used by a central Test Controller to inject fault scenarios, collect telemetry timestamps without riding the mesh under test, and render a live remote topology map.

## License and Open Data
This project is open-source. All data, code, and project artifacts contain no proprietary or classified information in accordance with Virginia Tech MDE and INL policies.

## Running The Program

### Prerequisites
* Linux machine running Ubuntu 22.04 LTS or Debian 12
* `batman-adv`, `batctl`, `iproute2`, and Python 3.10+ installed  

If on windows, run wsl --install before running any powershell scripts.  

```bash
# 1. Load the batman-adv kernel module
sudo modprobe batman-adv

# 2. Set up virtual namespaces and veth pairs
sudo bash virtual-mesh/scripts/setup_namespaces.sh

# 3. Bind batman-adv inside namespaces
sudo bash virtual-mesh/scripts/enable_batman.sh

# 4. Verify virtual mesh originators
sudo ip netns exec vnode1 batctl n

# 5. Launch the dynamic link orchestrator
python3 virtual-mesh/orchestrator/orchestrator.py