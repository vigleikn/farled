"""
Bygger en rutingsgraf fra Kystverkets farled-GeoJSON og beregner
korteste sjøvei mellom to koordinater via Dijkstra.
"""

import math
import json
from pathlib import Path
from typing import Union, List, Tuple, Set

import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, LineString
from pyproj import Geod
from scipy.spatial import KDTree

GEOD = Geod(ellps="WGS84")
NM_PER_METER = 1 / 1852


def geodesic_dist_nm(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Geodesisk distanse i nautiske mil mellom to punkter."""
    _, _, dist_m = GEOD.inv(lon1, lat1, lon2, lat2)
    return abs(dist_m) * NM_PER_METER



def _round_coord(lon: float, lat: float, decimals: int = 6) -> Tuple[float, float]:
    """Avrunder koordinat for bruk som node-nøkkel (unngår float-duplikater)."""
    return (round(lon, decimals), round(lat, decimals))


def _snap_endpoints(
    segments: List[Tuple[Tuple, Tuple, float]],
    endpoint_nodes: Set[Tuple],
    snap_tolerance_deg: float = 0.035,
) -> List[Tuple[Tuple, Tuple, float]]:
    """
    Slår sammen ENDEPUNKTER (første/siste punkt per LineString) som er nærmere
    enn snap_tolerance_deg grader. Intermediære noder langs linjen røres ikke,
    slik at ruter ikke kan hoppe mellom parallelle led.

    segments:       liste av (node1, node2, dist_nm)
    endpoint_nodes: sett av noder som er start/slutt-punkt i en LineString-feature
    Returnerer ny liste med endepunkter snappet mot hverandre.
    """
    # Bare snap endepunkter — ikke intermediære noder
    endpoints = list(endpoint_nodes)
    coords_array = [(lat, lon) for (lon, lat) in endpoints]
    tree = KDTree(coords_array)

    canonical = {}  # node -> canonical_node
    for i, node in enumerate(endpoints):
        if node in canonical:
            continue
        idxs = tree.query_ball_point(coords_array[i], snap_tolerance_deg)
        rep = endpoints[min(idxs)]
        for idx in idxs:
            if endpoints[idx] not in canonical:
                canonical[endpoints[idx]] = rep

    # Bygg nye segmenter — kun endepunktene kan endre seg
    snapped = []
    for n1, n2, dist in segments:
        c1 = canonical.get(n1, n1)
        c2 = canonical.get(n2, n2)
        if c1 != c2:
            snapped.append((c1, c2, dist))
    return snapped


def build_graph(geojson_path: Union[str, Path]) -> Tuple[nx.Graph, KDTree, List[Tuple]]:
    """
    Leser farled-GeoJSON og bygger en NetworkX-graf.

    Returnerer:
        graph      – NetworkX Graph med kanter vektet i nm
        kdtree     – scipy KDTree over alle noder (for rask snapping)
        node_list  – liste av (lon, lat) tupler i samme rekkefølge som KDTree
    """
    path = Path(geojson_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Farled-data ikke funnet: {path}\n"
            "Last ned 'Hovedled og Biled' fra https://kartkatalog.geonorge.no "
            "og legg filen her som data/farled.geojson\n"
            "Eller kjør: python download_farled.py"
        )

    print(f"Leser farled-data fra {path}...")
    gdf = gpd.read_file(path)
    print(f"  {len(gdf)} farled-features lastet")

    # Samle alle rå segmenter og registrer hvilke noder som er endepunkter
    raw_segments = []
    endpoint_nodes: Set[Tuple] = set()

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        if geom.geom_type == "LineString":
            lines = [geom]
        elif geom.geom_type == "MultiLineString":
            lines = list(geom.geoms)
        else:
            continue

        for line in lines:
            coords = list(line.coords)
            # Merk start- og slutt-punkt som endepunkter (disse kan snappes)
            endpoint_nodes.add(_round_coord(coords[0][0], coords[0][1]))
            endpoint_nodes.add(_round_coord(coords[-1][0], coords[-1][1]))

            for i in range(len(coords) - 1):
                lon1, lat1 = coords[i][0], coords[i][1]
                lon2, lat2 = coords[i + 1][0], coords[i + 1][1]
                n1 = _round_coord(lon1, lat1)
                n2 = _round_coord(lon2, lat2)
                if n1 != n2:
                    dist = geodesic_dist_nm(lon1, lat1, lon2, lat2)
                    raw_segments.append((n1, n2, dist))

    print(f"  {len(raw_segments)} segmenter ekstrahert — snapper endepunkter "
          f"(toleranse 0.035°, {len(endpoint_nodes)} endepunkter)...")

    # Snap kun endepunkter (start/slutt per linje) for å lukke topologi-hull
    # uten å lage snarveier mellom parallelle led
    snapped_segments = _snap_endpoints(raw_segments, endpoint_nodes, snap_tolerance_deg=0.035)

    graph = nx.Graph()
    for n1, n2, dist in snapped_segments:
        if graph.has_edge(n1, n2):
            # Behold korteste kant (unngå parallelle kanter med feil vekt)
            if dist < graph[n1][n2]["weight"]:
                graph[n1][n2]["weight"] = dist
        else:
            graph.add_edge(n1, n2, weight=dist)

    import networkx as nx_mod
    comps = sorted(nx_mod.connected_components(graph), key=len, reverse=True)
    print(f"  Graf etter snap: {graph.number_of_nodes()} noder, {graph.number_of_edges()} kanter, {len(comps)} komponenter")

    # Bro-bygging: koble isolerte komponenter til den største ved å legge til
    # en syntetisk kant mellom nærmeste node-par på tvers av komponenter.
    # Maks bro-lengde: 50 nm (kun brukt som fall-back der farled-data mangler).
    MAX_BRIDGE_NM = 50.0
    bridges_added = 0
    main_comp = set(comps[0])

    for small_comp in comps[1:]:
        small_nodes = list(small_comp)
        main_nodes = list(main_comp)

        # Bygg mini-KDTree over gjeldende main_comp for å finne nærmeste par
        main_coords = [(lat, lon) for (lon, lat) in main_nodes]
        mini_tree = KDTree(main_coords)

        best_dist = float("inf")
        best_pair = None
        for sn in small_nodes:
            dist_deg, idx = mini_tree.query([sn[1], sn[0]])
            mn = main_nodes[idx]
            dist_nm = geodesic_dist_nm(sn[0], sn[1], mn[0], mn[1])
            if dist_nm < best_dist:
                best_dist = dist_nm
                best_pair = (sn, mn)

        if best_pair and best_dist <= MAX_BRIDGE_NM:
            sn, mn = best_pair
            graph.add_edge(sn, mn, weight=best_dist, synthetic=True)
            main_comp = main_comp | small_comp
            bridges_added += 1
            print(f"  Bro lagt til: {best_dist:.1f} nm mellom {sn} og {mn}")
        else:
            print(f"  Ingen bro funnet for komponent med {len(small_comp)} noder "
                  f"(nærmeste: {best_dist:.1f} nm > {MAX_BRIDGE_NM} nm)")

    comps_after = list(nx_mod.connected_components(graph))
    print(f"  Graf etter bro-bygging: {graph.number_of_nodes()} noder, "
          f"{graph.number_of_edges()} kanter, {len(comps_after)} komponenter "
          f"({bridges_added} broer lagt til)")

    # Bygg KDTree for rask nearest-neighbour-søk
    node_list = list(graph.nodes())
    coords_array = [(lat, lon) for (lon, lat) in node_list]
    kdtree = KDTree(coords_array)

    return graph, kdtree, node_list


def snap_to_graph(
    lat: float,
    lon: float,
    kdtree: KDTree,
    node_list: List[Tuple],
    max_dist_km: float = 50.0,
) -> Union[Tuple[float, float], None]:
    """
    Finn nærmeste farled-node til koordinat (lat, lon).
    Returnerer (lon, lat)-tupel (node-ID) eller None hvis ingen funnet innenfor max_dist_km.
    """
    dist, idx = kdtree.query([lat, lon])

    # KDTree bruker euclidisk avstand i grader — grov sjekk
    # 1 grad ≈ 111 km; max_dist_km / 111 ≈ grader
    max_dist_deg = max_dist_km / 111.0
    if dist > max_dist_deg:
        return None

    return node_list[idx]


def compute_route(
    graph: nx.Graph,
    from_node: tuple,
    to_node: tuple,
) -> dict:
    """
    Kjør Dijkstra og returner rute-info som dict.

    Returnerer:
    {
        'distance_nm': float,
        'route_geojson': dict,   # GeoJSON LineString
        'waypoints': list,       # [(lon, lat), ...]
    }
    Kaster nx.NetworkXNoPath hvis ingen rute finnes.
    """
    path_nodes = nx.shortest_path(graph, from_node, to_node, weight="weight")

    # Summer distanse langs ruten
    total_nm = 0.0
    for i in range(len(path_nodes) - 1):
        total_nm += graph[path_nodes[i]][path_nodes[i + 1]]["weight"]

    # Bygg GeoJSON LineString (koordinater er (lon, lat))
    coords = [[lon, lat] for (lon, lat) in path_nodes]
    route_geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "distance_nm": round(total_nm, 2),
        },
    }

    return {
        "distance_nm": round(total_nm, 2),
        "route_geojson": route_geojson,
        "waypoints": coords,
    }


def find_route(
    graph: nx.Graph,
    kdtree: KDTree,
    node_list: List[Tuple],
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> dict:
    """
    Komplett ruting: snap koordinater → Dijkstra → returner resultat.
    """
    from_node = snap_to_graph(from_lat, from_lon, kdtree, node_list)
    if from_node is None:
        raise ValueError(
            f"Fra-koordinat ({from_lat}, {from_lon}) er for langt fra farled-nett"
        )

    to_node = snap_to_graph(to_lat, to_lon, kdtree, node_list)
    if to_node is None:
        raise ValueError(
            f"Til-koordinat ({to_lat}, {to_lon}) er for langt fra farled-nett"
        )

    snap_dist_from = geodesic_dist_nm(from_lon, from_lat, from_node[0], from_node[1])
    snap_dist_to = geodesic_dist_nm(to_lon, to_lat, to_node[0], to_node[1])

    result = compute_route(graph, from_node, to_node)
    result["snap_dist_from_nm"] = round(snap_dist_from, 3)
    result["snap_dist_to_nm"] = round(snap_dist_to, 3)
    return result
