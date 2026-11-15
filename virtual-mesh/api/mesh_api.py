#!/usr/bin/env python3
"""
Mesh Network Telemetry & Control API
Provides REST endpoints for topology discovery, metric extraction, and fault injection.
Compatible with both network namespaces (virtual) and direct host interfaces (physical).
"""

import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mesh Telemetry & Fault Control API",
    description="Manages topology extraction and synthetic impairment across virtual and physical mesh nodes.",
    version="1.1.0",
)

MAC_PATTERN = r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"

# Mock base coordinates (Blacksburg, VA) for spatial visualization
BASE_LAT = 37.229572
BASE_LON = -80.413938
NODE_OFFSETS = {
    "vnode1": (0.000, 0.000),      # Center / Base
    "vnode2": (0.012, 0.010),      # Northeast
    "vnode3": (0.022, 0.018),      # Far Northeast
    "vnode4": (-0.010, 0.014),     # Southeast
    "vnode5": (-0.005, 0.026),     # East-Southeast
    "vnode6": (0.010, 0.035),      # Far East
    "pnode1": (0.000, 0.000),
    "pnode2": (0.012, 0.010),
    "pnode3": (-0.010, 0.014),
    "pnode4": (0.005, 0.028),
}

# --- Lightweight In-Memory Caches & Active Fault Registry ---
_NODE_MAC_CACHE: Dict[str, Dict[str, object]] = {}
_TOPO_CACHE: Dict[str, object] = {"timestamp": 0.0, "data": None}
_ACTIVE_FAULTS: Dict[Tuple[str, str], Dict[str, object]] = {}
TOPO_CACHE_TTL = 0.25  # 250 ms deduplication window for concurrent UI + KML polls


# --- Command Execution & Peer Resolution Helpers ---

def run_cmd(cmd: str, netns: Optional[str] = None) -> str:
    """Executes a command either in a specific namespace or on the local host."""
    if netns and netns != "host":
        full_cmd = f"sudo ip netns exec {netns} {cmd}"
    else:
        full_cmd = f"sudo {cmd}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()


def resolve_peer_endpoint(node_id: str, interface: str) -> Optional[Tuple[str, str]]:
    """
    Given e.g. ('vnode1', 'veth1-2'), returns ('vnode2', 'veth2-1') so bidirectional
    faults can be applied or cleared symmetrically across a virtual link.
    """
    match = re.match(r"^veth(\d+)-(\d+)$", interface.strip())
    if not match:
        return None
    src_num, dst_num = match.groups()
    if node_id == f"vnode{src_num}":
        return (f"vnode{dst_num}", f"veth{dst_num}-{src_num}")
    if node_id == f"vnode{dst_num}":
        return (f"vnode{src_num}", f"veth{src_num}-{dst_num}")
    return None


def get_available_namespaces() -> List[str]:
    """Finds all active vnode network namespaces."""
    out = run_cmd("ip netns list")
    namespaces = []
    for line in out.splitlines():
        name = line.split()[0]
        if name.startswith("vnode"):
            namespaces.append(name)
    return sorted(namespaces) or ["host"]


def get_node_mac_info(node_id: str) -> Dict[str, object]:
    """Extracts and caches all mesh/veth MAC addresses and the primary MAC for a node."""
    if node_id in _NODE_MAC_CACHE:
        return _NODE_MAC_CACHE[node_id]

    raw = run_cmd(
        "ip -o link show | awk '$2 !~ /^(lo|ctl0):/ {for(i=1;i<=NF;i++) if($i==\"link/ether\") print $(i+1)}'",
        netns=node_id,
    )
    macs = [m.strip().lower() for m in raw.splitlines() if re.match(r"^" + MAC_PATTERN + r"$", m.strip())]

    bat0_mac = run_cmd("cat /sys/class/net/bat0/address 2>/dev/null", netns=node_id).strip().lower()
    primary_mac = bat0_mac if re.match(r"^" + MAC_PATTERN + r"$", bat0_mac) else (macs[0] if macs else "")

    info = {"primary_mac": primary_mac, "all_macs": macs}
    if macs:
        _NODE_MAC_CACHE[node_id] = info
    return info


def _scrape_single_node(node: str) -> Tuple[str, str]:
    """Worker function to fetch batctl originator output for one node."""
    return node, run_cmd("batctl o", netns=node)


# --- Pydantic Data Contracts ---

class ImpairmentRequest(BaseModel):
    node_id: str = Field(..., example="vnode1")
    interface: str = Field(..., example="veth1-2")
    loss_pct: Optional[int] = Field(0, ge=0, le=100)
    delay_ms: Optional[int] = Field(0, ge=0)
    jitter_ms: Optional[int] = Field(0, ge=0)
    bidirectional: Optional[bool] = Field(True)


class ClearImpairmentRequest(BaseModel):
    node_id: str = Field(..., example="vnode1")
    interface: str = Field(..., example="veth1-2")
    bidirectional: Optional[bool] = Field(True)


# --- API Endpoints ---

@app.get("/api/v1/nodes")
def list_nodes():
    """Lists all active nodes detected on the host."""
    nodes = get_available_namespaces()
    return {"count": len(nodes), "nodes": nodes}


@app.get("/api/v1/impairments")
def list_impairments():
    """Lists all currently active synthetic netem faults."""
    return {
        "count": len(_ACTIVE_FAULTS),
        "impairments": list(_ACTIVE_FAULTS.values()),
    }


@app.get("/api/v1/topology")
def get_topology():
    """
    Scrapes the mesh state concurrently across all nodes with TTL deduplication.
    Parses B.A.T.M.A.N. V throughput metrics (e.g., '( 10000.0)' or '( 10.0 MBit)').
    """
    now = time.monotonic()
    if _TOPO_CACHE["data"] is not None and (now - float(_TOPO_CACHE["timestamp"])) < TOPO_CACHE_TTL:
        return _TOPO_CACHE["data"]

    nodes_list = get_available_namespaces()

    for cached_node in list(_NODE_MAC_CACHE.keys()):
        if cached_node not in nodes_list:
            del _NODE_MAC_CACHE[cached_node]

    mac_to_node: Dict[str, str] = {}
    for node in nodes_list:
        info = get_node_mac_info(node)
        for mac in info["all_macs"]:  # type: ignore[attr-defined]
            mac_to_node[mac] = node

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(nodes_list)))) as pool:
        bat_outputs = dict(pool.map(_scrape_single_node, nodes_list))

    graph_nodes = []
    graph_links = []
    seen_links = set()

    pattern = (
        r"(\*?)\s*("
        + MAC_PATTERN
        + r")\s+[\d.]+s\s+\(?\s*([\d.]+)\s*(MBit|kBit)?\s*\)?\s+("
        + MAC_PATTERN
        + r")\s+\[\s*([^\]\s]+)\s*\]"
    )

    for node in nodes_list:
        offset = NODE_OFFSETS.get(node, (0.0, 0.0))
        primary_mac = _NODE_MAC_CACHE.get(node, {}).get("primary_mac", "")
        graph_nodes.append({
            "id": node,
            "mac": primary_mac,
            "lat": BASE_LAT + offset[0],
            "lon": BASE_LON + offset[1],
            "status": "online",
        })

        raw_out = bat_outputs.get(node, "")
        is_batman_v = "BATMAN_V" in raw_out or "throughput" in raw_out.lower()
        normalized = " ".join(raw_out.split())

        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            is_active, orig_mac, raw_val, unit, nexthop_mac, egress_if = match.groups()
            orig_mac = orig_mac.lower()
            target_node = mac_to_node.get(orig_mac, orig_mac)

            link_key = tuple(sorted([node, target_node]))
            if is_active.strip() == "*" and link_key not in seen_links and node != target_node:
                seen_links.add(link_key)

                val = float(raw_val)
                if is_batman_v or unit:
                    mbps = val / 1000.0 if (unit and unit.lower() == "kbit") else val
                    metric_type = "THROUGHPUT_MBIT"
                    metric_value = round(mbps, 2)
                    metric_display = f"{metric_value} MBit/s"
                    compat_score = min(255, int((mbps / 10.0) * 255))
                else:
                    metric_type = "TQ"
                    metric_value = int(val)
                    metric_display = f"{metric_value}/255"
                    compat_score = metric_value

                # Determine if this route is a direct 1-hop link or multi-hop failover path
                expected_direct_if = f"veth{node.replace('vnode', '')}-{target_node.replace('vnode', '')}"
                is_direct = (egress_if == expected_direct_if)

                graph_links.append({
                    "source": node,
                    "target": target_node,
                    "tq": compat_score,
                    "metric_value": metric_value,
                    "metric_type": metric_type,
                    "metric_display": metric_display,
                    "egress_interface": egress_if,
                    "is_direct": is_direct,
                    "is_active": True,
                })

    result = {
        "nodes": graph_nodes,
        "links": graph_links,
        "active_impairments": list(_ACTIVE_FAULTS.values()),
    }
    _TOPO_CACHE["timestamp"] = time.monotonic()
    _TOPO_CACHE["data"] = result
    return result


@app.post("/api/v1/impair")
def apply_impairment(req: ImpairmentRequest):
    """
    Injects synthetic packet loss or latency on an interface using tc netem.
    Optionally applies symmetrically to the peer interface when bidirectional=True.
    """
    tc_params = []
    if req.delay_ms and req.delay_ms > 0:
        if req.jitter_ms and req.jitter_ms > 0:
            tc_params.append(f"delay {req.delay_ms}ms {req.jitter_ms}ms")
        else:
            tc_params.append(f"delay {req.delay_ms}ms")
    if req.loss_pct and req.loss_pct > 0:
        tc_params.append(f"loss {req.loss_pct}%")

    targets = [(req.node_id, req.interface)]
    if req.bidirectional:
        peer = resolve_peer_endpoint(req.node_id, req.interface)
        if peer and peer not in targets:
            targets.append(peer)

    applied_targets = []
    for n_id, iface in targets:
        run_cmd(f"tc qdisc del dev {iface} root 2>/dev/null", netns=n_id)
        if tc_params:
            cmd = f"tc qdisc add dev {iface} root netem {' '.join(tc_params)}"
            run_cmd(cmd, netns=n_id)
            _ACTIVE_FAULTS[(n_id, iface)] = {
                "node_id": n_id,
                "interface": iface,
                "loss_pct": req.loss_pct,
                "delay_ms": req.delay_ms,
                "rules": tc_params,
                "applied_at": time.time(),
            }
            applied_targets.append(f"{n_id}:{iface}")
        else:
            _ACTIVE_FAULTS.pop((n_id, iface), None)

    _TOPO_CACHE["data"] = None

    return {
        "status": "applied",
        "node_id": req.node_id,
        "interface": req.interface,
        "bidirectional": req.bidirectional,
        "targets": applied_targets,
        "rules": tc_params,
    }


@app.post("/api/v1/reset")
def clear_impairment(req: ClearImpairmentRequest):
    """
    Removes netem traffic control impairments from an interface (and its peer if bidirectional=True).
    """
    targets = [(req.node_id, req.interface)]
    if req.bidirectional:
        peer = resolve_peer_endpoint(req.node_id, req.interface)
        if peer and peer not in targets:
            targets.append(peer)

    cleared_targets = []
    for n_id, iface in targets:
        run_cmd(f"tc qdisc del dev {iface} root 2>/dev/null", netns=n_id)
        _ACTIVE_FAULTS.pop((n_id, iface), None)
        cleared_targets.append(f"{n_id}:{iface}")

    _TOPO_CACHE["data"] = None

    return {
        "status": "cleared",
        "node_id": req.node_id,
        "interface": req.interface,
        "bidirectional": req.bidirectional,
        "targets": cleared_targets,
    }


@app.post("/api/v1/reset_all")
def reset_all_impairments():
    """
    Emergency demo reset: clears all netem rules across every veth interface on all namespaces.
    """
    nodes = get_available_namespaces()
    for node in nodes:
        ifaces_raw = run_cmd("ls /sys/class/net", netns=node)
        for iface in ifaces_raw.split():
            if iface.startswith("veth"):
                run_cmd(f"tc qdisc del dev {iface} root 2>/dev/null", netns=node)

    _ACTIVE_FAULTS.clear()
    _TOPO_CACHE["data"] = None

    return {"status": "all_cleared", "nodes_reset": nodes}


@app.get("/api/v1/network_link.kml")
def get_kml_network_link():
    """
    Returns the Network Link wrapper file for Google Earth Pro (1-second polling).
    """
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <NetworkLink>
    <name>Live Mesh Telemetry</name>
    <flyToView>0</flyToView>
    <Link>
      <href>http://localhost:8000/api/v1/live_mesh.kml</href>
      <refreshMode>onInterval</refreshMode>
      <refreshInterval>1</refreshInterval>
    </Link>
  </NetworkLink>
</kml>
"""
    return Response(content=kml_content, media_type="application/vnd.google-earth.kml+xml")


@app.get("/api/v1/live_mesh.kml")
def get_live_mesh_kml():
    """
    Generates dynamic 3D KML displaying nodes and throughput/TQ-colored links.
    """
    topo = get_topology()
    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        '    <name>Mesh Nodes and Links</name>',
        '    <Style id="goodLink"><LineStyle><color>ff00ff00</color><width>4</width></LineStyle></Style>',
        '    <Style id="degradedLink"><LineStyle><color>ff00a5ff</color><width>4</width></LineStyle></Style>',
        '    <Style id="poorLink"><LineStyle><color>ff0000ff</color><width>3</width></LineStyle></Style>',
    ]

    node_coords = {}
    for node in topo["nodes"]:
        lat, lon = node["lat"], node["lon"]
        node_coords[node["id"]] = (lat, lon)
        kml_parts.append(f"""
    <Placemark>
      <name>{node["id"]}</name>
      <description><![CDATA[<b>Node ID:</b> {node["id"]}<br/><b>MAC:</b> {node["mac"]}]]></description>
      <Point>
        <coordinates>{lon},{lat},0</coordinates>
      </Point>
    </Placemark>""")

    for link in topo["links"]:
        src = link["source"]
        tgt = link["target"]
        if src in node_coords and tgt in node_coords:
            p1 = node_coords[src]
            p2 = node_coords[tgt]

            if link.get("metric_type") == "THROUGHPUT_MBIT":
                mbps = link["metric_value"]
                style = "#goodLink" if mbps >= 5.0 else ("#degradedLink" if mbps >= 2.0 else "#poorLink")
                metric_label = f"<b>Throughput:</b> {link['metric_display']}"
            else:
                tq = link.get("metric_value", link.get("tq", 0))
                style = "#goodLink" if tq >= 200 else ("#degradedLink" if tq >= 150 else "#poorLink")
                metric_label = f"<b>TQ:</b> {link.get('metric_display', f'{tq}/255')}"

            kml_parts.append(f"""
    <Placemark>
      <name>{src} to {tgt}</name>
      <description><![CDATA[{metric_label}<br/><b>Egress IF:</b> {link["egress_interface"]}]]></description>
      <styleUrl>{style}</styleUrl>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{p1[1]},{p1[0]},0 {p2[1]},{p2[0]},0</coordinates>
      </LineString>
    </Placemark>""")

    kml_parts.append('  </Document>\n</kml>')
    return Response(
        content="\n".join(kml_parts),
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# --- Mount Static Dashboard UI ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mesh_api:app", host="0.0.0.0", port=8000, reload=True)