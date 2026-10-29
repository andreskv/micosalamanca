"""Capa estática de hábitat por especie sobre los cotos micológicos de Salamanca."""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy.ndimage import uniform_filter

from especies import ESPECIES, HOSPEDADORES, rampa, trapecio

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "datos" / "raw"
OUT = RAIZ / "datos" / "habitat"
PIXEL = 65.0  # m en EPSG:3857, ~49 m sobre el terreno a 41° N

# El acotados.json de MICOCYL trae los acentos rotos y le faltan dos nombres.
NOMBRES = {
    "SA-50002": "Miranda de Azán", "SA-50003": "El Bodón - Fuenteguinaldo",
    "SA-50004": "Berrocal de Huebra", "SA-50005": "Ribera de Cañedo",
    "SA-50007": "Aldeatejada - Carrascal de Barregas", "SA-50008": "Larrodrigo",
    "SA-50009": "Pedraza de Alba", "SA-50010": "Calzada de Don Diego (2)",
    "SA-50011": "Calzada de Don Diego", "SA-50012": "Membribe de la Sierra",
    "SA-50013": "Parada de Arriba - Galindo y Perahuy",
    "SA-50014": "Carrascal de Barregas", "SA-50015": "Morille",
    "PMSA-50001": "Parque Micológico Sierras de Francia, Béjar, Quilamas y El Rebollar",
}


def malla(cotos):
    x0, y0, x1, y1 = cotos.to_crs(3857).total_bounds
    x0, y0, x1, y1 = x0 - 1000, y0 - 1000, x1 + 1000, y1 + 1000
    ancho, alto = int(np.ceil((x1 - x0) / PIXEL)), int(np.ceil((y1 - y0) / PIXEL))
    return from_origin(x0, y1, PIXEL, PIXEL), (alto, ancho)


def topografia(transform, shape):
    """Elevación, northness y TPI calculados a 25 m nativos y agregados después a la malla."""
    mos, t25 = merge(sorted((RAW / "mdt25").glob("*.tif")))
    z = mos[0].astype("float32")
    z[z <= -100] = np.nan
    gy, gx = np.gradient(np.nan_to_num(z, nan=np.nanmean(z)), 25.0)
    # aspecto hacia donde mira la ladera; northness = cos(aspecto) (D29: nunca grados)
    pendiente = np.hypot(gx, gy)
    north = np.where(pendiente > 0.02, gy / np.maximum(pendiente, 1e-6), 0).astype("float32")
    tpi = (z - uniform_filter(np.nan_to_num(z, nan=0), size=21)).astype("float32")  # ventana ~500 m
    salida = []
    for banda in (z, north, tpi):
        dst = np.full(shape, np.nan, "float32")
        reproject(banda, dst, src_transform=t25, src_crs=25830, dst_transform=transform,
                  dst_crs=3857, resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
        salida.append(dst)
    return salida


def hospedador(mfe, especie):
    w = HOSPEDADORES[especie]
    p = ESPECIES[especie]
    h = sum(mfe[f"Especie{i}"].map(w).fillna(0) * mfe[f"O{i}"].fillna(0) / 100 for i in (1, 2, 3))
    h = h.clip(0, 1) * trapecio(mfe["FCCARB"].fillna(0), *p["dosel"])
    if p["jara"]:
        jaral = mfe["FormArbust"].fillna("").str.contains("Cistus|Jaral", regex=True)
        h = np.where(jaral, np.maximum(h, p["jara"]), h)
    return np.asarray(h, dtype="float32")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cotos = gpd.read_file(RAW / "cotos_sa.json").set_crs(25830, allow_override=True)
    cotos["nombre"] = cotos.c_clave_id.map(NOMBRES)
    cotos = cotos.sort_values("c_clave_id").reset_index(drop=True)
    transform, shape = malla(cotos)

    c3857 = cotos.to_crs(3857)
    id_coto = rasterize(((g, i + 1) for i, g in enumerate(c3857.geometry)), out_shape=shape,
                        transform=transform, dtype="uint8")
    cotos.to_crs(4326)[["c_clave_id", "nombre", "geometry"]].to_file(OUT / "cotos.geojson", driver="GeoJSON")

    mfe = gpd.read_file(RAW / "mfe25_cotos_sa.gpkg").to_crs(3857)
    z, north, tpi = topografia(transform, shape)

    capas = {}
    for sp, p in ESPECIES.items():
        host = rasterize(zip(mfe.geometry, hospedador(mfe, sp)), out_shape=shape,
                         transform=transform, dtype="float32", fill=0)
        alt = trapecio(np.nan_to_num(z, nan=0), *p["altitud"])
        if p["insolacion"]:
            topo = 1 - p["insolacion"] * (np.nan_to_num(north) + 1) / 2
        else:
            # vaguadas algo más húmedas que lomas en el verano mediterráneo [H]
            topo = 0.85 + 0.15 * rampa(-np.nan_to_num(tpi), -10, 10)
        capas[sp] = np.where(id_coto > 0, host * alt * topo, 0).astype("float32")

    oeste, norte = transform.c, transform.f
    este, sur = oeste + shape[1] * PIXEL, norte - shape[0] * PIXEL
    lon0, lat0 = Transformer.from_crs(3857, 4326, always_xy=True).transform(oeste, sur)
    lon1, lat1 = Transformer.from_crs(3857, 4326, always_xy=True).transform(este, norte)
    np.savez_compressed(OUT / "habitat.npz", id_coto=id_coto, elev=z, north=north, tpi=tpi, **capas)
    meta = dict(transform=list(transform)[:6], shape=shape, crs="EPSG:3857",
                bounds_latlon=[[lat0, lon0], [lat1, lon1]], cotos=list(cotos.c_clave_id),
                nombres=list(cotos.nombre))
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    for sp in capas:
        v = capas[sp][id_coto > 0]
        print(f"{sp:12s} H medio {v.mean():.2f}  celdas H>0.5: {(v > 0.5).mean():.0%}")
    print("malla", shape, "celdas en coto", int((id_coto > 0).sum()))


if __name__ == "__main__":
    main()
