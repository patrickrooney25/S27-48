## Design Evolution & Architectural Decisions

Following client review and integration testing of the virtual mesh testbed, the geospatial visualization architecture was updated prior to feature freeze. All architectural decisions below are locked for the demonstration and final deliverable.

### 1. Transition from Google Earth Pro to Embedded Leaflet.js + GeoJSON
* **Previous Approach:** The FastAPI backend generated dynamic KML files (`/api/v1/live_mesh.kml`) polled every 1 second by an external Google Earth Pro desktop client via a KML `NetworkLink`.
* **Updated Approach:** Replaced the external KML viewer with a client-side **Leaflet.js** geospatial map embedded directly inside the web-based Mesh Control & Telemetry Console (`static/index.html`), backed by an RFC 7946 **GeoJSON** export endpoint (`/api/v1/topology.geojson`).
* **Rationale:**
  * **Close-Range Spatial Resolution (10–25 m Field Scale):** Google Earth Pro enforces a macro-scale camera altitude floor that caused nodes placed at realistic field-testing distances (10–15 m average, 25 m maximum) to overlap visually unless coordinates were artificially inflated to mile-wide spacing. Leaflet.js supports deep Web Mercator overzooming (`maxNativeZoom: 19`, `maxZoom: 22`, reaching ~0.03 m/px at $37.23^\circ\text{N}$), clearly separating nodes spaced 12–22 meters apart with a live metric scale bar and geodesic distance tooltips.
  * **Single-Pane-of-Glass Operations:** Embedding the live map alongside the `B.A.T.M.A.N. V` throughput table and fault-injection controller eliminates context-switching between desktop applications during live failover testing.
  * **Standards-Based Extensibility:** Exposing `/api/v1/topology.geojson` provides an industry-standard geospatial data format (`FeatureCollection` of `Point` nodes and `LineString` links with throughput/interface properties), enabling future ingestion by external GIS, simulation, or post-test analysis tools. Legacy KML endpoints (`/api/v1/live_mesh.kml` and `/api/v1/network_link.kml`) remain preserved for backward compatibility.

### 2. Routing Protocol Standardization (`B.A.T.M.A.N. V`)
* **Decision:** Standardized exclusively on the `B.A.T.M.A.N. V` routing algorithm (`CONFIG_BATMAN_ADV_BATMAN_V=y`) across all virtual network namespaces rather than maintaining dual `B.A.T.M.A.N. IV` / `V` parsing modes in the primary demo workflow.
* **Rationale:** `B.A.T.M.A.N. V` evaluates links via throughput estimation (`MBit/s`) and Echo Location Protocol (ELP) neighbor probing rather than Transmission Quality (`TQ`) packet counts, aligning directly with high-bandwidth link-degradation and failover demonstrations.

### 3. Known Limitations & Trade-Offs (Feature-Freeze Baseline)
In accordance with the post-integration feature freeze, the following constraints are documented rather than expanded:
* **External Tile Server Dependency:** The embedded Leaflet map fetches aerial imagery (Esri World Imagery) and dark street tiles (CartoDB Dark Matter) over HTTPS. In air-gapped or offline field environments without cached tiles, the basemap background will appear blank; however, all vector node markers, link status overlays, geodesic distance readouts, and metric scale bars remain fully operational.
  * *Alternative for Offline Deployments:* Pre-render local `.mbtiles` or XYZ raster tiles for the test site and serve them from a static `/tiles/{z}/{x}/{y}.png` route in FastAPI.
* **Static Coordinate Offsets in Virtual Mode:** Virtual namespaces (`vnode1`–`vnode6`) use fixed coordinate offsets (`NODE_OFFSETS` in `mesh_api.py`) modeled around Blacksburg, VA (`37.229572, -80.413938`) to emulate 12–22 m physical deployment spacing. Dynamic GPS telemetry ingestion is deferred to physical node integration.
* **2D Planar Visualization:** Unlike Google Earth Pro's 3D terrain engine, Leaflet renders a 2D top-down planar projection. Elevation differences between nodes are not visually modeled, which is acceptable for flat courtyard/field test topologies at 10–25 m scale.