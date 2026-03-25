"""
Sjøvei-kalkulator — Flask backend
Beregner korteste sjøvei mellom to norske kaier via offisielle farleder.
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, jsonify, request, render_template
import networkx as nx

from nsr import fetch_quays, get_quays_dict
from routing import build_graph, find_route

# ---------------------------------------------------------------------------
# App-konfigurasjon
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
FARLED_PATH = BASE_DIR / "data" / "farled.geojson"

app = Flask(__name__)
app.jinja_env.auto_reload = True

# Global state – lastes ved oppstart
_graph = None
_kdtree = None
_node_list = None
_quays_dict = {}
_shipyards = []
_ferries = []
_startup_error = None


def startup():
    """Laster farled-graf og kai-liste ved oppstart."""
    global _graph, _kdtree, _node_list, _quays_dict, _startup_error, _shipyards, _ferries

    # --- Farled-graf ---
    try:
        _graph, _kdtree, _node_list = build_graph(FARLED_PATH)
    except FileNotFoundError as e:
        _startup_error = str(e)
        print(f"\n[ADVARSEL] {e}\n", file=sys.stderr)
        return
    except Exception as e:
        _startup_error = f"Feil ved bygging av farled-graf: {e}"
        print(f"\n[FEIL] {_startup_error}\n", file=sys.stderr)
        return

    # --- NSR kaier ---
    try:
        _quays_dict = get_quays_dict(use_cache=True)
    except Exception as e:
        print(f"[ADVARSEL] Kunne ikke hente kaier fra NSR: {e}", file=sys.stderr)
        _quays_dict = {}

    # --- Shipyards ---
    try:
        shipyards_path = BASE_DIR / "data" / "shipyards.json"
        if shipyards_path.exists():
            with open(shipyards_path, 'r', encoding='utf-8') as f:
                _shipyards = json.load(f)
            print(f"Lastet {len(_shipyards)} verft fra JSON", file=sys.stderr)
        else:
            print("[INFO] Ingen shipyards.json funnet - verft ikke tilgjengelig", file=sys.stderr)
    except Exception as e:
        print(f"[ADVARSEL] Kunne ikke laste verft: {e}", file=sys.stderr)
        _shipyards = []

    # --- Ferries ---
    try:
        ferries_path = BASE_DIR / "data" / "ferries.json"
        if ferries_path.exists():
            with open(ferries_path, 'r', encoding='utf-8') as f:
                _ferries = json.load(f)
            print(f"Lastet {len(_ferries)} ferjer fra JSON", file=sys.stderr)
        else:
            print("[INFO] Ingen ferries.json funnet - ferjer ikke tilgjengelig", file=sys.stderr)
    except Exception as e:
        print(f"[ADVARSEL] Kunne ikke laste ferjer: {e}", file=sys.stderr)
        _ferries = []


# ---------------------------------------------------------------------------
# Endepunkter
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    """Sjekker om appen er klar."""
    if _startup_error:
        return jsonify({"ok": False, "error": _startup_error}), 503
    return jsonify({
        "ok": True,
        "nodes": _graph.number_of_nodes() if _graph else 0,
        "edges": _graph.number_of_edges() if _graph else 0,
        "quays": len(_quays_dict),
    })


@app.route("/api/quays")
def get_quays():
    """Returnerer liste over tilgjengelige kaier for dropdown."""
    quays = sorted(_quays_dict.values(), key=lambda q: q["stop_name"])
    return jsonify(quays)


@app.route("/api/shipyards")
def get_shipyards():
    """Returnerer liste over tilgjengelige verft for dropdown."""
    return jsonify(_shipyards)


@app.route("/api/ferries")
def get_ferries():
    """Returnerer liste over tilgjengelige ferjer for dropdown."""
    return jsonify(_ferries)


@app.route("/api/geocode")
def geocode():
    """Proxy til Kartverkets adresse- og stedsnavn-API."""
    import urllib.request, urllib.parse, concurrent.futures

    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    headers = {"User-Agent": "sjovei-poc/1.0"}

    def fetch_steder():
        # Relevante objekttyper (ikke individuelle adresser)
        TYPER = {"By", "Tettsted", "Tettsteddel", "Kommune", "Bydel", "Havn", "Sted",
                 "Annen administrativ inndeling", "Grend", "Småby", "Øy", "Øy i sjø",
                 "Fyrstasjon", "Fyr", "Odde", "Nes", "Bukt", "Sund", "Fjord"}
        url = (
            "https://ws.geonorge.no/stedsnavn/v1/sted?"
            + urllib.parse.urlencode({"sok": q, "treffPerSide": "8", "utkoordsys": "4258"})
        )
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=5
            ) as resp:
                data = json.loads(resp.read())
            out = []
            seen = set()
            for s in data.get("navn", []):
                if s.get("navneobjekttype") not in TYPER:
                    continue
                pt = s.get("representasjonspunkt", {})
                lat = pt.get("nord")
                lon = pt.get("\u00f8st")   # ø
                if not lat or not lon:
                    continue
                stedsnavn = s.get("stedsnavn", [])
                name = stedsnavn[0].get("skrivem\u00e5te", "") if stedsnavn else ""
                kommune = s.get("kommuner", [{}])[0].get("kommunenavn", "")
                if not name or name in seen:
                    continue
                seen.add(name)
                out.append({
                    "name": name,
                    "poststed": kommune,
                    "municipality": "",
                    "postcode": "",
                    "lat": lat, "lon": lon,
                    "is_sted": True,
                })
            return out
        except:
            return []

    def fetch_adresser():
        url = (
            "https://ws.geonorge.no/adresser/v1/sok?"
            + urllib.parse.urlencode({"sok": q, "treffPerSide": "5", "utkoordsys": "4258"})
        )
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=5
            ) as resp:
                data = json.loads(resp.read())
            out = []
            for a in data.get("adresser", []):
                pt = a.get("representasjonspunkt", {})
                if not pt.get("lat") or not pt.get("lon"):
                    continue
                out.append({
                    "name": a.get("adressetekst", ""),
                    "poststed": a.get("poststed", ""),
                    "municipality": a.get("kommunenavn", ""),
                    "postcode": a.get("postnummer", ""),
                    "lat": pt["lat"], "lon": pt["lon"],
                })
            return out
        except:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_steder  = ex.submit(fetch_steder)
        f_adresse = ex.submit(fetch_adresser)
        steder  = f_steder.result()
        adresse = f_adresse.result()

    return jsonify(steder + adresse)


@app.route("/api/route", methods=["POST"])
def route():
    """
    Beregner sjøvei mellom to kaier.

    Body (JSON):
      { "from_id": "...", "to_id": "..." }
    eller med koordinater direkte:
      { "from_lat": 60.1, "from_lon": 5.3, "to_lat": 61.6, "to_lon": 5.0,
        "from_name": "Fra", "to_name": "Til" }
    """
    if _startup_error:
        return jsonify({"error": _startup_error}), 503

    data = request.get_json(force=True)

    # Hent koordinater
    if "from_id" in data and "to_id" in data:
        from_q = _quays_dict.get(data["from_id"])
        to_q = _quays_dict.get(data["to_id"])
        if not from_q:
            return jsonify({"error": f"Ukjent kai-ID: {data['from_id']}"}), 400
        if not to_q:
            return jsonify({"error": f"Ukjent kai-ID: {data['to_id']}"}), 400
        from_lat, from_lon = from_q["lat"], from_q["lon"]
        to_lat, to_lon = to_q["lat"], to_q["lon"]
        from_name = from_q.get("stop_name", from_q["name"])
        to_name = to_q.get("stop_name", to_q["name"])
    else:
        from_lat = float(data["from_lat"])
        from_lon = float(data["from_lon"])
        to_lat = float(data["to_lat"])
        to_lon = float(data["to_lon"])
        from_name = data.get("from_name", "Fra")
        to_name = data.get("to_name", "Til")

    try:
        result = find_route(_graph, _kdtree, _node_list, from_lat, from_lon, to_lat, to_lon)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except nx.NetworkXNoPath:
        return jsonify({
            "error": "Ingen sjørute funnet mellom disse to kaiene. "
                     "Kan skyldes hull i farled-dataene."
        }), 404
    except Exception as e:
        return jsonify({"error": f"Rutingsfeil: {e}"}), 500

    return jsonify({
        "from_name": from_name,
        "to_name": to_name,
        "distance_nm": result["distance_nm"],
        "distance_km": round(result["distance_nm"] * 1.852, 1),
        "snap_dist_from_nm": result.get("snap_dist_from_nm"),
        "snap_dist_to_nm": result.get("snap_dist_to_nm"),
        "route_geojson": result["route_geojson"],
        "waypoints": result["waypoints"],
    })


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    startup()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
