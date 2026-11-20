"""Índice relativo de fructificación para hoy y los 7 días siguientes, y mapa HTML con sus capas en teselas."""
import datetime as dt
import json
import shutil
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
PASO_PUNTOS = 10000.0  # m en 3857, ~7,5 km sobre el terreno; los modelos de Open-Meteo van a 7-11 km
GRADIENTE_T = -0.0065  # °C/m, gradiente térmico estándar
# la lluvia de los últimos días todavía no ha dado setas: actúa con ~1 mes de retraso [KA18]; 7 d [H]
RETRASO_LLUVIA = 7
SM_RANGO = (0.10, 0.25)  # m3/m3 a 9-27 cm, de suelo seco a húmedo [H]


def puntos_meteo(meta, mascara):
    a, b, c, d, e, f = meta["transform"]
    filas, cols = np.nonzero(mascara)
    xs, ys = c + (cols + 0.5) * a, f + (filas + 0.5) * e
    gx = np.arange(xs.min() - PASO_PUNTOS, xs.max() + PASO_PUNTOS, PASO_PUNTOS)
    gy = np.arange(ys.min() - PASO_PUNTOS, ys.max() + PASO_PUNTOS, PASO_PUNTOS)
    ocupado = set(zip(((xs - gx[0]) // PASO_PUNTOS).astype(int), ((ys - gy[0]) // PASO_PUNTOS).astype(int)))
    # cada caja con celdas visibles aporta sus cuatro esquinas, para que la interpolación las cubra todas
    nodos = np.array(sorted({(i + di, j + dj) for i, j in ocupado for di in (0, 1) for dj in (0, 1)}))
    px, py = gx[0] + nodos[:, 0] * PASO_PUNTOS, gy[0] + nodos[:, 1] * PASO_PUNTOS
    lon, lat = Transformer.from_crs(3857, 4326, always_xy=True).transform(px, py)
    return nodos, (float(gx[0]), float(gy[0])), lat, lon


def bilineal(nodos, origen, x, y):
    """Misma interpolación que hace el HTML al tocar una celda; las 4 esquinas siempre existen."""
    nx, ny = nodos.max(axis=0) + 1
    idx = np.full((nx, ny), -1)
    idx[nodos[:, 0], nodos[:, 1]] = np.arange(len(nodos))
    u, v = (x - origen[0]) / PASO_PUNTOS, (y - origen[1]) / PASO_PUNTOS
    i, j = np.floor(u).astype(int), np.floor(v).astype(int)
    du, dv = (u - i).astype("float32"), (v - j).astype("float32")
    esquinas = [(idx[i, j], (1 - du) * (1 - dv)), (idx[i + 1, j], du * (1 - dv)),
                (idx[i, j + 1], (1 - du) * dv), (idx[i + 1, j + 1], du * dv)]
    # 3 millones de celdas: calculo los pesos una vez y los reutilizo para cada variable
    return lambda valores: sum(np.asarray(valores, "float32")[k] * w for k, w in esquinas)


def open_meteo(lat, lon):
    out = []
    for i in range(0, len(lat), 40):
        for intento in range(6):
            try:
                r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=(20, 90), params=dict(
                    latitude=",".join(f"{v:.4f}" for v in lat[i:i + 40]),
                    longitude=",".join(f"{v:.4f}" for v in lon[i:i + 40]),
                    daily="precipitation_sum,temperature_2m_mean,temperature_2m_min",
                    hourly="soil_temperature_6cm,soil_moisture_9_to_27cm",
                    past_days=PASADO, forecast_days=FUTURO, timezone="Europe/Madrid"))
                # los runners de GitHub comparten IP y Open-Meteo limita por IP
                if r.status_code != 429:
                    break
            except requests.RequestException as err:
                # ya visto en Actions: timeout en el saludo TLS con api.open-meteo.com
                if intento == 5:
                    raise
                print(f"Open-Meteo falló ({type(err).__name__}), reintento {intento + 1}/5")
            time.sleep(30 * (intento + 1))
        r.raise_for_status()
        j = r.json()
        out += j if isinstance(j, list) else [j]
        time.sleep(5)
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
        lluvia=ventana(m["p"], d - RETRASO_LLUVIA, p["dias_lluvia"], np.nansum),
        eventos=ventana((m["p"] >= 5).astype("float32"), d - RETRASO_LLUVIA, p["dias_lluvia"], np.nansum),
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


def teselas(arr, nombre, vacio=255, lado=1024):
    """Ficheros [fila, col, ruta] de como mucho 1 MP: Safari en iOS no decodifica bien imágenes de más de ~5 MP."""
    lista = []
    for r0 in range(0, arr.shape[0], lado):
        for c0 in range(0, arr.shape[1], lado):
            t = arr[r0:r0 + lado, c0:c0 + lado]
            if (t == vacio).all():
                continue
            ruta = f"capas/{nombre}_{r0}_{c0}.png"
            Image.fromarray(t).save(SALIDA / ruta, format="PNG", compress_level=9)
            lista.append([r0, c0, ruta])
    return lista


def main():
    meta = json.loads((HAB / "meta.json").read_text(encoding="utf-8"))
    hab = np.load(HAB / "habitat.npz")
    id_coto, elev10, dentro = hab["id_coto"], hab["elev10"], hab["visible"]
    filas, cols = np.nonzero(dentro)
    a, _, c, _, e, f = meta["transform"]
    cx, cy = c + (cols + 0.5) * a, f + (filas + 0.5) * e

    nodos, origen, plat, plon = puntos_meteo(meta, dentro)
    print(f"{len(nodos)} puntos meteo; descargando Open-Meteo...")
    m = open_meteo(plat, plon)
    hoy = PASADO
    a_celdas = bilineal(nodos, origen, cx, cy)
    shutil.rmtree(SALIDA / "capas", ignore_errors=True)
    (SALIDA / "capas").mkdir(parents=True)

    # el HTML lee la altitud en decenas de metros de un PNG de 8 bits; uso la misma para que cuadren
    dz = elev10[dentro] * 10.0 - a_celdas(m["elev"])
    capas, puntos, resumen = {}, {}, {}
    for sp in ESPECIES:
        H = hab[sp][dentro] / 100
        capas[sp], puntos[sp], resumen[sp] = [], [], []
        for d in range(hoy, hoy + FUTURO):
            fecha = dt.date.fromisoformat(m["dias"][d])
            v = variables_punto(m, sp, d)
            fac = factores({k: a_celdas(x) for k, x in v.items()}, sp, fecha.timetuple().tm_yday, dz)
            idx = H * np.prod(list(fac.values()), axis=0)
            img = np.full(id_coto.shape, 255, "uint8")
            img[dentro] = np.clip(np.round(idx * 100), 0, 100).astype("uint8")
            capas[sp].append(teselas(img, f"{sp}_{d - hoy}"))
            puntos[sp].append({k: np.round(x, 3).tolist() for k, x in v.items()})
            resumen[sp].append([float(np.round(np.mean(idx[id_coto[dentro] == i + 1]) * 100, 1))
                                for i in range(len(meta["cotos"]))])

    datos = dict(
        generado=dt.datetime.now().strftime("%d/%m/%Y %H:%M"), dias=m["dias"][hoy:hoy + FUTURO],
        bounds=meta["bounds_latlon"], transform=meta["transform"], shape=meta["shape"],
        cotos=meta["cotos"], nombres=meta["nombres"], resumen=resumen,
        especies={k: {kk: vv for kk, vv in v.items()} for k, v in ESPECIES.items()},
        constantes=dict(retraso=RETRASO_LLUVIA, paso=PASO_PUNTOS, origen=origen, gradiente=GRADIENTE_T, sm=SM_RANGO,
                        doy=[dt.date.fromisoformat(s).timetuple().tm_yday for s in m["dias"][hoy:hoy + FUTURO]]),
        puntos=dict(nodos=nodos.tolist(), elev=m["elev"].tolist(), valores=puntos),
        capas=capas,
        habitat={sp: teselas(np.where(dentro, hab[sp], 255).astype("uint8"), f"h_{sp}") for sp in ESPECIES},
        elev10=teselas(np.where(dentro, elev10, 255).astype("uint8"), "elev10"),
        id_coto=teselas(id_coto, "id_coto", vacio=0),
        cotos_geojson=json.loads((HAB / "cotos.geojson").read_text(encoding="utf-8")))
    html = (RAIZ / "src" / "plantilla.html").read_text(encoding="utf-8")
    html = html.replace("/*LEAFLET_CSS*/", (RAIZ / "vendor" / "leaflet.css").read_text(encoding="utf-8"))
    html = html.replace("/*LEAFLET_JS*/", (RAIZ / "vendor" / "leaflet.js").read_text(encoding="utf-8"))
    html = html.replace("/*DATOS*/", "const DATOS = " + json.dumps(datos, ensure_ascii=False) + ";")
    destino = SALIDA / "index.html"
    destino.write_text(html, encoding="utf-8")
    capas_mb = sum(p.stat().st_size for p in (SALIDA / "capas").glob("*.png")) / 1e6
    print(f"Mapa: {destino} ({destino.stat().st_size / 1e6:.1f} MB + {capas_mb:.0f} MB en capas/)")
    for sp in ESPECIES:
        mejor = sorted(zip(resumen[sp][0], meta["nombres"]), reverse=True)[:3]
        print(sp, "hoy, mejores cotos:", [(n, v) for v, n in mejor])


if __name__ == "__main__":
    main()
