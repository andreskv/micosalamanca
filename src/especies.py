"""Reglas por especie. Cada número lleva la clave de su fuente en docs/revision-bibliografica.md.

[H] = heurística mía apoyada en fuente cualitativa; no hay umbral publicado para Salamanca.
"""
import numpy as np


def trapecio(x, a, b, c, d):
    """0 fuera de [a, d], 1 en [b, c], lineal entre medias."""
    x = np.asarray(x, dtype="float32")
    return np.clip(np.minimum((x - a) / (b - a), (d - x) / (d - c)), 0, 1)


def rampa(x, lo, hi):
    return np.clip((np.asarray(x, dtype="float32") - lo) / (hi - lo), 0, 1)


# Peso de cada árbol hospedador (0-1) según el campo Especie1..3 del MFE25.
HOSPEDADORES = {
    "edulis": {  # [MP12][AP11][SC23]
        "Quercus pyrenaica": 1.0, "Castanea sativa": 1.0, "Pinus sylvestris": 0.9,
        "Pinus pinaster": 0.6, "Quercus faginea": 0.6, "Quercus ilex": 0.4,
        "Quercus suber": 0.4, "Betula spp.": 0.6, "Pinus nigra": 0.5,
    },
    "aereus": {  # [MICO-V][H]
        "Quercus pyrenaica": 1.0, "Castanea sativa": 1.0, "Quercus suber": 0.8,
        "Quercus ilex": 0.7, "Quercus faginea": 0.6, "Pinus pinaster": 0.2,
    },
    "reticulatus": {  # [MICO-V][SC23][H]
        "Quercus pyrenaica": 1.0, "Castanea sativa": 1.0, "Quercus faginea": 0.8,
        "Quercus ilex": 0.5, "Quercus suber": 0.5, "Pinus pinaster": 0.2,
    },
    "caesarea": {  # [TUL][AMJC][RDB][H]
        "Castanea sativa": 1.0, "Quercus suber": 1.0, "Quercus pyrenaica": 0.9,
        "Quercus ilex": 0.8, "Quercus faginea": 0.6, "Arbutus unedo": 0.4,
        "Pinus pinaster": 0.3,
    },
}

ESPECIES = {
    "edulis": dict(
        nombre="Boletus edulis", comun="Hongo, boleto",
        # Temporada otoñal en CyL: septiembre-noviembre [KA18][AL17]
        temporada=(230, 260, 320, 350),
        altitud=(600, 850, 1600, 1900),       # [H]
        dias_lluvia=26, lluvia_mm=(20, 80),   # ventana de 26 d [BL26]; umbrales [H]
        dias_temp=20, t_opt=13.0, t_sd=4.0,   # óptimo 13 °C en 20 d [BL26]
        t_suelo_min=None,
        dosel=(5, 30, 100, 101),              # necesita árbol o jara [MP12][AP11]
        jara=0.5,                             # Cistus ladanifer en el oeste de CyL [AP11]
        tormentas=False,
        insolacion=0.0,
    ),
    "aereus": dict(
        nombre="Boletus aereus", comun="Hongo negro",
        temporada=(150, 180, 280, 310),       # verano-principio de otoño [MICO-V]
        altitud=(300, 500, 1050, 1300),       # termófilo [H]
        dias_lluvia=20, lluvia_mm=(15, 60),   # 15-20 d previos y nº de tormentas [MICO-V]
        tormentas=True,
        dias_temp=20, t_opt=19.0, t_sd=4.0,   # [H]
        t_suelo_min=None,
        dosel=(5, 30, 100, 101),
        jara=0.0,
        insolacion=0.0,
    ),
    "reticulatus": dict(
        nombre="Boletus reticulatus", comun="Hongo de verano",
        temporada=(135, 165, 275, 305),       # [MICO-V]
        altitud=(400, 600, 1350, 1650),       # [H]
        dias_lluvia=20, lluvia_mm=(15, 60),   # [MICO-V]
        tormentas=True,
        dias_temp=20, t_opt=17.0, t_sd=4.0,   # [H]
        t_suelo_min=None,
        dosel=(5, 30, 100, 101),
        jara=0.0,
        insolacion=0.0,
    ),
    "caesarea": dict(
        nombre="Amanita caesarea", comun="Oronja, amanita de los césares",
        temporada=(170, 200, 300, 325),       # VI-X [RDB]; picos tras tormentas de agosto y lluvias de septiembre [GUA]
        altitud=(200, 400, 1050, 1250),       # 200-800 m en Italia [TUL]; ampliado [H]
        dias_lluvia=20, lluvia_mm=(20, 70),   # [GUA][H]
        tormentas=False,
        dias_temp=20, t_opt=20.0, t_sd=4.0,   # termófila [AMJC][RDB][H]
        t_suelo_min=(13.0, 17.0),             # suelo cálido [H]
        dosel=(10, 25, 70, 95),               # bosque claro y soleado [RDB][AMJC]
        jara=0.0,
        insolacion=0.25,                      # solanas y levante [AMJC]
    ),
}
