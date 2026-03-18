"""
Diagnostikkscript: kartlegger hull i farled-nettverket.
Kjør fra sjovei-demo/-mappen: python diagnose_network.py
"""

import sys
from pathlib import Path
import networkx as nx
from routing import build_graph, snap_to_graph, geodesic_dist_nm
from nsr import get_quays_dict

FARLED_PATH = Path(__file__).parent / "data" / "farled.geojson"

# ── 1. Bygg graf ───────────────────────────────────────────────────────────────
print("\n=== 1. GRAFBYGGING ===")
graph, kdtree, node_list = build_graph(FARLED_PATH)

comps = sorted(nx.connected_components(graph), key=len, reverse=True)
print(f"\nAntall tilkoblede komponenter : {len(comps)}")
print(f"Største komponent             : {len(comps[0])} noder")
if len(comps) > 1:
    print(f"Nest største                  : {len(comps[1])} noder")
print(f"Totalt noder i grafen         : {graph.number_of_nodes()}")
print(f"Totalt kanter i grafen        : {graph.number_of_edges()}")

# Størrelsefordeling av komponenter
print("\nKomponentstørrelser (topp 15):")
for i, c in enumerate(comps[:15]):
    print(f"  Komponent {i+1:2d}: {len(c):5d} noder")
if len(comps) > 15:
    small = [len(c) for c in comps[15:]]
    print(f"  ... og {len(small)} komponenter med 1–{max(small)} noder (totalt {sum(small)} noder)")

# ── 2. Test spesifikke problematiske ruter ─────────────────────────────────────
print("\n=== 2. PROBLEMRUTER ===")

TEST_PAIRS = [
    # (fra_navn, fra_lat, fra_lon, til_navn, til_lat, til_lon)
    ("Brekstad kai",    63.6917, 9.6878,  "Levanger ferjekai", 63.7454, 11.2986),
    ("Bergen Strandkai", 60.3936, 5.3239, "Florø rutebåtkai",   61.5994, 5.0305),
    ("Trondheim ferje", 63.4326, 10.3967, "Kristiansund kystrutekai", 63.1129, 7.7273),
    ("Ålesund rutebåt", 62.4702, 6.1494, "Molde kai",           62.7356, 7.1568),
]

comp_map = {}  # node -> comp_index
for i, comp in enumerate(comps):
    for node in comp:
        comp_map[node] = i

for fra_n, fra_lat, fra_lon, til_n, til_lat, til_lon in TEST_PAIRS:
    print(f"\n  {fra_n} → {til_n}")
    fn = snap_to_graph(fra_lat, fra_lon, kdtree, node_list, max_dist_km=50)
    tn = snap_to_graph(til_lat, til_lon, kdtree, node_list, max_dist_km=50)

    if fn is None:
        print(f"    [FRA] Ingen node innen 50 km! Koordinat: ({fra_lat}, {fra_lon})")
        continue
    if tn is None:
        print(f"    [TIL] Ingen node innen 50 km! Koordinat: ({til_lat}, {til_lon})")
        continue

    snap_fra = geodesic_dist_nm(fra_lon, fra_lat, fn[0], fn[1])
    snap_til = geodesic_dist_nm(til_lon, til_lat, tn[0], tn[1])
    comp_fra = comp_map.get(fn, -1)
    comp_til = comp_map.get(tn, -1)

    print(f"    Fra snap: {snap_fra:.2f} nm til node {fn} (komponent {comp_fra})")
    print(f"    Til snap: {snap_til:.2f} nm til node {tn} (komponent {comp_til})")

    if comp_fra != comp_til:
        print(f"    ❌ ULIKE KOMPONENTER — ingen rute mulig!")
        # Finn nærmeste punkt mellom komponentene
        fra_nodes = list(comps[comp_fra])[:500]  # begrens søk
        til_nodes = list(comps[comp_til])[:500]
        min_gap = float("inf")
        gap_pair = None
        for f in fra_nodes:
            for t in til_nodes:
                d = geodesic_dist_nm(f[0], f[1], t[0], t[1])
                if d < min_gap:
                    min_gap = d
                    gap_pair = (f, t)
        if gap_pair:
            print(f"    Korteste avstand mellom komponentene: {min_gap:.2f} nm")
            print(f"    Mellom node {gap_pair[0]} og {gap_pair[1]}")
    else:
        try:
            path = nx.shortest_path(graph, fn, tn, weight="weight")
            dist = sum(graph[path[i]][path[i+1]]["weight"] for i in range(len(path)-1))
            print(f"    ✅ Rute funnet: {dist:.1f} nm via {len(path)} noder")
        except nx.NetworkXNoPath:
            print(f"    ❌ Ingen sti — samme komponent, men ikke tilkoblet?!")

# ── 3. Geografisk dekning ──────────────────────────────────────────────────────
print("\n=== 3. GEOGRAFISK DEKNING ===")

# Finn bbox for hver av de 5 største komponentene
for i, comp in enumerate(comps[:5]):
    lons = [n[0] for n in comp]
    lats = [n[1] for n in comp]
    print(f"  Komponent {i+1}: lon [{min(lons):.2f} – {max(lons):.2f}], "
          f"lat [{min(lats):.2f} – {max(lats):.2f}], {len(comp)} noder")

# ── 4. NSR-kaier: hvor mange kan nås? ─────────────────────────────────────────
print("\n=== 4. NSR-KAI DEKNING ===")

try:
    quays = get_quays_dict(use_cache=True)
    print(f"Totalt {len(quays)} kaier i NSR-cache")

    main_comp = comps[0]
    reachable = 0
    unreachable = []

    for qid, q in quays.items():
        node = snap_to_graph(q["lat"], q["lon"], kdtree, node_list, max_dist_km=30)
        if node and node in main_comp:
            reachable += 1
        else:
            unreachable.append(q)

    pct = reachable / len(quays) * 100 if quays else 0
    print(f"Kaier som kan nås via hovedkomponent : {reachable}/{len(quays)} ({pct:.0f}%)")
    print(f"Kaier UTENFOR rutingsnettverket      : {len(unreachable)}")

    print("\nEksempler på kaier som IKKE kan rutes (første 20):")
    for q in unreachable[:20]:
        node = snap_to_graph(q["lat"], q["lon"], kdtree, node_list, max_dist_km=50)
        if node:
            comp_idx = comp_map.get(node, -1)
            snap_nm = geodesic_dist_nm(q["lon"], q["lat"], node[0], node[1])
            print(f"  - {q.get('stop_name', q['name']):<40s} snap={snap_nm:.2f}nm komp={comp_idx}")
        else:
            print(f"  - {q.get('stop_name', q['name']):<40s} ingen node innen 50km!")

except Exception as e:
    print(f"[FEIL] Kunne ikke analysere NSR-kaier: {e}")

# ── 5. Årsaksanalyse ───────────────────────────────────────────────────────────
print("\n=== 5. ÅRSAKSANALYSE ===")
print("""
Mulige årsaker til fragmentert farled-nettverk:

A) TOPOLOGISK BRUDD I KYSTVERKET-DATA
   - Linjer slutter nær hverandre men berører ikke (gap < snap-toleranse)
   - Snap-toleransen er nå 0.002 grader (~220m)

B) MANGLENDE FARLED-DATA FOR FJORDER
   - Trondheimsleia / Trondheimsfjorden mangler kanskje senterlinjer
   - Innaskjærs-led (biled) finnes ikke alltid digitalisert

C) DATASETT INNEHOLDER KUN DELER AV NETTET
   - Geonorge-nedlasting kan være ufullstendig (tile-basert?)
   - Kun Sør-Norge eller kun hovedled ble lastet ned?

D) GeoJSON-KONVERTERINGSFEIL
   - SOSI → GeoJSON-konvertering kan droppe features

E) FEIL DATASETT
   - Lastet ned arealavgrensning (polygoner) istedenfor senterlinjer?
""")

print("=== DIAGNOSE FERDIG ===\n")
