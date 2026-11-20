"""Prepara datos/raw: cotos (WFS MICOCYL), Mapa Forestal de la provincia y MDT25 (WCS IGN).

Uso: python src/descargas.py RUTA/MFE_41.shp   (el MFE25 de CyL se descarga a mano desde MITECO)
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import requests

RAW = Path(__file__).resolve().parents[1] / "datos" / "raw"
WFS = ("https://vps24geoserver.cesefor.com/geoserver/micologiacyl/ows?service=WFS&version=1.0.0"
       "&request=GetFeature&typeName=mico_cyl_zonas_reguladas&outputFormat=application%2Fjson"
       "&CQL_FILTER=c_clave_id%20LIKE%20%27%25SA-%25%27")
TESELA_MDT = 70000  # m; el WCS del IGN corta en 4096 px por lado (2800 px a 25 m)


def main(mfe_shp):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "cotos_sa.json").write_bytes(requests.get(WFS, timeout=120).content)

    mfe = gpd.read_file(mfe_shp, where="NUT3_NOM='Salamanca'", engine="pyogrio")
    mfe.to_file(RAW / "mfe25_salamanca.gpkg", driver="GPKG")
    x0, y0, x1, y1 = mfe.total_bounds
    print(f"MFE Salamanca: {len(mfe)} teselas, bbox {x0:.0f} {y0:.0f} {x1:.0f} {y1:.0f}")

    (RAW / "mdt25").mkdir(exist_ok=True)
    for xa in np.arange(np.floor(x0 / 1000) * 1000 - 1000, x1 + 1000, TESELA_MDT):
        for ya in np.arange(np.floor(y0 / 1000) * 1000 - 1000, y1 + 1000, TESELA_MDT):
            f = RAW / "mdt25" / f"mdt25_{xa:.0f}_{ya:.0f}.tif"
            if f.exists():
                continue
            r = requests.get("https://servicios.idee.es/wcs-inspire/mdt", timeout=300, params={
                "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage",
                "COVERAGEID": "Elevacion25830_25", "FORMAT": "image/tiff",
                "SUBSET": [f"x({xa:.0f},{xa + TESELA_MDT:.0f})", f"y({ya:.0f},{ya + TESELA_MDT:.0f})"]})
            r.raise_for_status()
            if not r.headers.get("Content-Type", "").startswith("image/"):
                raise RuntimeError(r.text[:300])
            f.write_bytes(r.content)
            print("MDT", f.name)


if __name__ == "__main__":
    main(sys.argv[1])
