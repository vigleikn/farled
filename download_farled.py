"""
Last ned Kystverkets farled-data (Hovedled og Biled) fra Geonorge
og konverter til GeoJSON.

Bruker Geonorge nedlastings-API (bestilling + henting).

Kjøres én gang:
    python download_farled.py
"""

import os
import sys
import json
import zipfile
import time
from pathlib import Path
import urllib.request
import urllib.error

DATA_DIR = Path(__file__).parent / "data"
GML_FILE = DATA_DIR / "Samferdsel_0000_Norge_4258_HovedledBiled_GML.gml"
OUT_FILE = DATA_DIR / "farled.geojson"

# Geonorge metadata UUID for "Hovedled og Biled" (Kystverket)
DATASET_UUID = "8ff1538a-a93c-4391-8d6f-3555fc37819c"

ORDER_URL   = "https://nedlasting.geonorge.no/api/order"
STATUS_URL  = "https://nedlasting.geonorge.no/api/order/{ref}"

ORDER_BODY = {
    "email": "",
    "orderLines": [{
        "metadataUuid": DATASET_UUID,
        "areas": [{"code": "0000", "type": "landsdekkende", "name": "Hele landet"}],
        "projections": [{"code": "4258"}],
        "formats": [{"name": "GML"}],
    }],
}


def _post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "sjovei-poc/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sjovei-poc/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def download_gml() -> Path:
    """Bestiller og laster ned farled GML fra Geonorge. Returnerer sti til GML-fil."""

    print("Bestiller farled-data fra Geonorge (GML format, Hele landet)...")
    order = _post_json(ORDER_URL, ORDER_BODY)
    ref = order["referenceNumber"]
    print(f"  Ordre-referanse: {ref}")

    # Hent fil-URL (kan komme med det samme eller etter litt venting)
    files = order.get("files", [])
    for _ in range(10):
        if files:
            break
        time.sleep(3)
        order = _get_json(STATUS_URL.format(ref=ref))
        files = order.get("files", [])

    if not files:
        raise RuntimeError("Ingen filer ble gjort tilgjengelig etter venting. Prøv igjen.")

    file_info = files[0]
    download_url = file_info["downloadUrl"]
    filename = file_info["name"]
    print(f"  Laster ned: {filename}")

    DATA_DIR.mkdir(exist_ok=True)
    zip_path = DATA_DIR / filename

    req = urllib.request.Request(download_url, headers={"User-Agent": "sjovei-poc/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(f"\r  {pct}% ({downloaded // 1024} KB)", end="", flush=True)
    print()

    # Pakk ut GML
    with zipfile.ZipFile(zip_path) as zf:
        gmls = [n for n in zf.namelist() if n.endswith(".gml")]
        if not gmls:
            raise RuntimeError(f"Ingen GML-filer i {zip_path}")
        zf.extract(gmls[0], DATA_DIR)
        gml_path = DATA_DIR / gmls[0]

    os.unlink(zip_path)
    print(f"  GML hentet: {gml_path.name}")
    return gml_path


def convert_to_geojson(gml_path: Path) -> None:
    """Konverterer GML til GeoJSON (WGS84). Krever geopandas."""
    import geopandas as gpd
    import warnings
    warnings.filterwarnings("ignore")

    print("Konverterer GML → GeoJSON...")
    gdf = gpd.read_file(gml_path)
    print(f"  {len(gdf)} farled-features (CRS: {gdf.crs})")
    print(f"  Farledtyper: {gdf['farledtype'].value_counts().to_dict()}")

    gdf_wgs = gdf.to_crs("EPSG:4326")
    gdf_wgs[["farledtype", "farlednavn", "farlednummer", "geometry"]].to_file(
        OUT_FILE, driver="GeoJSON"
    )
    size_kb = OUT_FILE.stat().st_size // 1024
    print(f"  Lagret: {OUT_FILE} ({size_kb} KB)")


def main():
    print("=" * 60)
    print("  Sjøvei-kalkulator — Farled data setup")
    print("=" * 60)

    if OUT_FILE.exists():
        size_kb = OUT_FILE.stat().st_size // 1024
        print(f"\nFarled-data finnes allerede: {OUT_FILE} ({size_kb} KB)")
        ans = input("Last ned på nytt? [j/N]: ").strip().lower()
        if ans != "j":
            print("Avbrutt.")
            return

    try:
        # Sjekk om GML allerede finnes (kan brukes direkte uten ny nedlasting)
        if GML_FILE.exists():
            print(f"\nFant eksisterende GML-fil: {GML_FILE.name}")
            gml_path = GML_FILE
        else:
            gml_path = download_gml()

        convert_to_geojson(gml_path)
        print("\nFerdig! Start appen med:  python app.py")

    except urllib.error.URLError as e:
        print(f"\nNettverksfeil: {e}")
        print("Sjekk internettforbindelsen og prøv igjen.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFeil: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
