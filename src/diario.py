"""Índice relativo de fructificación para hoy y los 7 días siguientes, y mapa HTML autocontenido."""
import base64
import datetime as dt
import io
import json
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from pyproj import Transformer

from especies import ESPECIES, rampa, trapecio

RAIZ = Path(__file__).resolve().parents[1]
HAB = RAIZ / "datos" / "habitat"
SALIDA = RAIZ / "salida"
PASADO, FUTURO = 40, 8
PASO_PUNTOS = 6500.0   # m en 3857, ~5 km sobre el terreno
GRADIENTE_T = -0.0065  # °C/m, gradiente térmico estándar
SM_RANGO = (0.10, 0.25)  # m3/m3 a 9-27 cm, de suelo seco a húmedo [H]


def puntos_meteo(meta, id_coto):
    a, b, c, d, e, f = meta["transform"]
    filas, cols = np.nonzero(id_coto)
    xs, ys = c + (cols + 0.5) * a, f + (filas + 0.5) * e
    gx = np.arange(xs.min() - PASO_PUNTOS, xs.max() + PASO_PUNTOS, PASO_PUNTOS)
    gy = np.arange(ys.min() - PASO_PUNTOS, ys.max() + PASO_PUNTOS, PASO_PUNTOS)
    ocupado = set(zip(((xs - gx[0]) // PASO_PUNTOS).astype(int), ((ys - gy[0]) // PASO_PUNTOS).astype(int)))
    # cada caja con coto aporta sus cuatro esquinas, para que la interpolación cubra todo el coto
    nodos = np.array(sorted({(i + di, j + dj) for i, j in ocupado for di in (0, 1) for dj in (0, 1)}))
    px, py = gx[0] + nodos[:, 0] * PASO_PUNTOS, gy[0] + nodos[:, 1] * PASO_PUNTOS
    lon, lat = Transformer.from_crs(3857, 4326, always_xy=True).transform(px, py)
    return nodos, (float(gx[0]), float(gy[0])), lat, lon


def bilineal(nodos, origen, valores, x, y):
    """Misma interpolación que hace el HTML al tocar una celda; las 4 esquinas siempre existen."""
    nx, ny = nodos.max(axis=0) + 1
    g = np.full((nx, ny), np.nan, "float32")
    g[nodos[:, 0], nodos[:, 1]] = valores
    u, v = (x - origen[0]) / PASO_PUNTOS, (y - origen[1]) / PASO_PUNTOS
    i, j = np.floor(u).astype(int), np.floor(v).astype(int)
    du, dv = u - i, v - j
    return (g[i, j] * (1 - du) * (1 - dv) + g[i + 1, j] * du * (1 - dv)
            + g[i, j + 1] * (1 - du) * dv + g[i + 1, j + 1] * du * dv)


def open_meteo(lat, lon):
    out = []
    for i in range(0, len(lat), 40):
        for intento in range(5):
            r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=120, params=dict(
                latitude=",".join(f"{v:.4f}" for v in lat[i:i + 40]),
                longitude=",".join(f"{v:.4f}" for v in lon[i:i + 40]),
                daily="precipitation_sum,temperature_2m_mean,temperature_2m_min",
                hourly="soil_temperature_6cm,soil_moisture_9_to_27cm",
                past_days=PASADO, forecast_days=FUTURO, timezone="Europe/Madrid"))
            # los runners de GitHub comparten IP y Open-Meteo limita por IP
            if r.status_code != 429:
                break
            time.sleep(60 * (intento + 1))
        r.raise_for_status()
        j = r.json()
        out += j if isinstance(j, list) else [j]
        time.sleep(1)
    dias = out[0]["daily"]["time"]
    diario = lambda k: np.array([o["daily"][k] for o in out], dtype="float32")
    horario = lambda k: np.array([o["hourly"][k] for o in out], dtype="float32").reshape(len(out), len(dias), 24)
    return dict(
        dias=dias, elev=np.array([o["elevation"] for o in out], dtype="float32"),
        p=np.nan_to_num(diario("precipitation_sum")), t=diario("temperature_2m_mean"),
        tmin=diario("temperature_2m_min"),
        tsuelo=np.nanmean(horario("soil_temperature_6cm"), axis=2),
        sm=np.nanmean(horario("soil_moisture_9_to_27cm"), axis=2))


def ventana(x, d, n, f=np.nanmean):
    return f(x[:, max(0, d - n + 1):d + 1], axis=1)


def variables_punto(m, sp, d):
    p = ESPECIES[sp]
    return dict(
        lluvia=ventana(m["p"], d, p["dias_lluvia"], np.nansum),
        eventos=ventana((m["p"] >= 5).astype("float32"), d, p["dias_lluvia"], np.nansum),
        t=ventana(m["t"], d, p["dias_temp"]), tsuelo=ventana(m["tsuelo"], d, 10),
        tmin3=ventana(m["tmin"], d, 3, np.nanmin), sm=ventana(m["sm"], d, 7))


def factores(v, sp, doy, dz):
    """dz = elevación de la celda menos la del punto meteo: corrige temperaturas por altitud."""
    p = ESPECIES[sp]
    f_lluvia = rampa(v["lluvia"], *p["lluvia_mm"])
    if p["tormentas"]:
        f_lluvia = f_lluvia * (0.6 + 0.4 * np.minimum(1, v["eventos"] / 2))
    f_suelo = rampa(v["sm"], *SM_RANGO)
    t = v["t"] + GRADIENTE_T * dz
    return dict(
        temporada=np.full_like(t, trapecio(doy, *p["temporada"])),
        agua=np.sqrt(f_lluvia * f_suelo),
        temp=np.exp(-0.5 * ((t - p["t_opt"]) / p["t_sd"]) ** 2),
        helada=np.where(v["tmin3"] + GRADIENTE_T * dz < -1, 0.3, 1.0),  # [H]
        t_suelo=(rampa(v["tsuelo"] + GRADIENTE_T * dz, *p["t_suelo_min"])
                 if p["t_suelo_min"] else np.ones_like(t)))


def png_b64(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    meta = json.loads((HAB / "meta.json").read_text(encoding="utf-8"))
    hab = np.load(HAB / "habitat.npz")
    id_coto, elev = hab["id_coto"], hab["elev"]
    dentro = id_coto > 0
    filas, cols = np.nonzero(dentro)
    a, _, c, _, e, f = meta["transform"]
    cx, cy = c + (cols + 0.5) * a, f + (filas + 0.5) * e

    nodos, origen, plat, plon = puntos_meteo(meta, id_coto)
    print(f"{len(nodos)} puntos meteo; descargando Open-Meteo...")
    m = open_meteo(plat, plon)
    hoy = PASADO
    a_celdas = lambda valores: bilineal(nodos, origen, valores, cx, cy)

    # el HTML lee la altitud de un PNG de 8 bits en decenas de metros; uso la misma para que cuadren
    elev10 = np.clip(np.round(np.nan_to_num(elev) / 10), 0, 254).astype("uint8")
    dz = elev10[dentro] * 10.0 - a_celdas(m["elev"])
    capas, puntos, resumen = {}, {}, {}
    for sp in ESPECIES:
        H = np.round(hab[sp][dentro] * 100) / 100
        capas[sp], puntos[sp], resumen[sp] = [], [], []
        for d in range(hoy, hoy + FUTURO):
            fecha = dt.date.fromisoformat(m["dias"][d])
            v = variables_punto(m, sp, d)
            fac = factores({k: a_celdas(x) for k, x in v.items()}, sp, fecha.timetuple().tm_yday, dz)
            idx = H * np.prod(list(fac.values()), axis=0)
            img = np.full(id_coto.shape, 255, "uint8")
            img[dentro] = np.clip(np.round(idx * 100), 0, 100).astype("uint8")
            capas[sp].append(png_b64(img))
            puntos[sp].append({k: np.round(x, 3).tolist() for k, x in v.items()})
            resumen[sp].append([float(np.round(np.mean(idx[id_coto[dentro] == i + 1]) * 100, 1))
                                for i in range(len(meta["cotos"]))])

    datos = dict(
        generado=dt.datetime.now().strftime("%d/%m/%Y %H:%M"), dias=m["dias"][hoy:hoy + FUTURO],
        bounds=meta["bounds_latlon"], transform=meta["transform"], shape=meta["shape"],
        cotos=meta["cotos"], nombres=meta["nombres"], resumen=resumen,
        especies={k: {kk: vv for kk, vv in v.items()} for k, v in ESPECIES.items()},
        constantes=dict(paso=PASO_PUNTOS, origen=origen, gradiente=GRADIENTE_T, sm=SM_RANGO,
                        doy=[dt.date.fromisoformat(s).timetuple().tm_yday for s in m["dias"][hoy:hoy + FUTURO]]),
        puntos=dict(nodos=nodos.tolist(), elev=m["elev"].tolist(), valores=puntos),
        capas=capas,
        habitat={sp: png_b64(np.where(dentro, np.round(hab[sp] * 100), 255).astype("uint8")) for sp in ESPECIES},
        elev10=png_b64(elev10), id_coto=png_b64(id_coto),
        cotos_geojson=json.loads((HAB / "cotos.geojson").read_text(encoding="utf-8")))
    html = (RAIZ / "src" / "plantilla.html").read_text(encoding="utf-8")
    html = html.replace("/*LEAFLET_CSS*/", (RAIZ / "vendor" / "leaflet.css").read_text(encoding="utf-8"))
    html = html.replace("/*LEAFLET_JS*/", (RAIZ / "vendor" / "leaflet.js").read_text(encoding="utf-8"))
    html = html.replace("/*DATOS*/", "const DATOS = " + json.dumps(datos, ensure_ascii=False) + ";")
    SALIDA.mkdir(exist_ok=True)
    destino = SALIDA / "index.html"
    destino.write_text(html, encoding="utf-8")
    print(f"Mapa: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
    for sp in ESPECIES:
        mejor = sorted(zip(resumen[sp][0], meta["nombres"]), reverse=True)[:3]
        print(sp, "hoy, mejores cotos:", [(n, v) for v, n in mejor])


if __name__ == "__main__":
    main()
