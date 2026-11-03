#!/usr/bin/env python3
"""
Mesh Network Telemetry & Control API
Provides REST endpoints for topology discovery, metric extraction, and fault injection.
Compatible with both network namespaces (virtual) and direct host interfaces (physical).
"""

import os
import re
import subprocess
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mesh Telemetry & Fault Control API",
    description="Manages topology extraction and synthetic impairment across virtual and physical mesh nodes.",
    version="1.0.0",
)

MAC_PATTERN = r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"

# Mock base coordinates (Blacksburg, VA) for spatial visualization
BASE_LAT = 37.229572
BASE_LON = -80.413938
# Spread nodes across ~1-3 km so pins and link lines have clear visual separation
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


# --- Command Execution Helpers ---

def run_cmd(cmd: str, netns: Optional[str] = None) -> str:
    """Executes a command either in a specific namespace or on the local host."""
    if netns and netns != "host":
        full_cmd = f"sudo ip netns exec {netns} {cmd}"
    else:
        full_cmd = f"sudo {cmd}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()


def get_available_namespaces() -> List[str]:
    """Finds all active vnode network namespaces."""
    out = run_cmd("ip netns list")
    namespaces = []
    for line in out.splitlines():
        name = line.split()[0]
        if name.startswith("vnode"):
            namespaces.append(name)
    return sorted(namespaces) or ["host"]


def get_node_primary_mac(node_id: str) -> str:
    """Extracts the primary originator MAC address for a given node."""
    header = run_cmd("batctl o", netns=node_id)
    match = re.search(r"MainIF/MAC:\s*[^/]+/(" + MAC_PATTERN + r")", header)
    if match:
        return match.group(1).lower()

    # Fallback to first physical/veth MAC
    raw = run_cmd("ip -o link show | awk '$2 !~ /^(lo|bat)/ {print $17; exit}'", netns=node_id)
    return raw.strip().lower()


# --- Pydantic Data Contracts ---

class ImpairmentRequest(BaseModel):
    node_id: str = Field(..., example="vnode1")
    interface: str = Field(..., example="veth1-2")
    loss_pct: Optional[int] = Field(0, ge=0, le=100)
    delay_ms: Optional[int] = Field(0, ge=0)
    jitter_ms: Optional[int] = Field(0, ge=0)


class ClearImpairmentRequest(BaseModel):
    node_id: str = Field(..., example="vnode1")
    interface: str = Field(..., example="veth1-2")


# --- API Endpoints ---

@app.get("/api/v1/nodes")
def list_nodes():
    """Lists all active nodes detected on the host."""
    nodes = get_available_namespaces()
    return {"count": len(nodes), "nodes": nodes}


@app.get("/api/v1/topology")
def get_topology():
    """
    Scrapes the mesh state across all nodes and compiles a unified node/link graph.
    """
    nodes_list = get_available_namespaces()
    mac_to_node = {}

    for node in nodes_list:
        mac = get_node_primary_mac(node)
        if mac:
            mac_to_node[mac] = node

    graph_nodes = []
    graph_links = []
    seen_links = set()

    for node in nodes_list:
        offset = NODE_OFFSETS.get(node, (0.0, 0.0))
        graph_nodes.append({
            "id": node,
            "mac": get_node_primary_mac(node),
            "lat": BASE_LAT + offset[0],
            "lon": BASE_LON + offset[1],
            "status": "online",
        })

        bat_out = run_cmd("batctl o", netns=node)
        normalized = " ".join(bat_out.split())
        pattern = (
            r"(\*?)\s*("
            + MAC_PATTERN
            + r")\s+[\d.]+s\s+\(\s*(\d+)\s*\)\s+("
            + MAC_PATTERN
            + r")\s+\[\s*([^\]\s]+)\s*\]"
        )

        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            is_active, orig_mac, tq, nexthop_mac, egress_if = match.groups()
            orig_mac = orig_mac.lower()
            target_node = mac_to_node.get(orig_mac, orig_mac)

            link_key = tuple(sorted([node, target_node]))
            if is_active.strip() == "*" and link_key not in seen_links and node != target_node:
                seen_links.add(link_key)
                graph_links.append({
                    "source": node,
                    "target": target_node,
                    "tq": int(tq),
                    "egress_interface": egress_if,
                    "is_active": True,
                })

    return {
        "nodes": graph_nodes,
        "links": graph_links,
    }


@app.post("/api/v1/impair")
def apply_impairment(req: ImpairmentRequest):
    """
    Injects synthetic packet loss or latency on an interface using tc netem.
    """
    tc_params = []
    if req.delay_ms > 0:
        if req.jitter_ms > 0:
            tc_params.append(f"delay {req.delay_ms}ms {req.jitter_ms}ms")
        else:
            tc_params.append(f"delay {req.delay_ms}ms")
    if req.loss_pct > 0:
        tc_params.append(f"loss {req.loss_pct}%")

    run_cmd(f"tc qdisc del dev {req.interface} root 2>/dev/null", netns=req.node_id)

    if tc_params:
        cmd = f"tc qdisc add dev {req.interface} root netem {' '.join(tc_params)}"
        run_cmd(cmd, netns=req.node_id)

    return {
        "status": "applied",
        "node_id": req.node_id,
        "interface": req.interface,
        "rules": tc_params,
    }


@app.post("/api/v1/reset")
def clear_impairment(req: ClearImpairmentRequest):
    """
    Removes netem traffic control impairments from an interface.
    """
    run_cmd(f"tc qdisc del dev {req.interface} root 2>/dev/null", netns=req.node_id)
    return {"status": "cleared", "node_id": req.node_id, "interface": req.interface}


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
    Generates dynamic 3D KML displaying nodes and TQ-colored links.
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
            tq = link["tq"]
            style = "#goodLink" if tq >= 200 else ("#degradedLink" if tq >= 150 else "#poorLink")

            kml_parts.append(f"""
    <Placemark>
      <name>{src} to {tgt}</name>
      <description><![CDATA[<b>TQ:</b> {tq}/255<br/><b>Egress IF:</b> {link["egress_interface"]}]]></description>
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mesh_api:app", host="0.0.0.0", port=8000, reload=True)