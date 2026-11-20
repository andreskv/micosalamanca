# MicoSalamanca

Índice relativo diario de fructificación de *Boletus edulis*, *B. aereus*, *B. reticulatus*, *Amanita caesarea*, níscalo (*Lactarius deliciosus*) y seta de cardo (*Pleurotus eryngii*). Cubre los 14 cotos micológicos de Salamanca y el monte del resto de la provincia, para hoy y los 7 días siguientes, con celdas de unos 50 m.

## Uso

```
python src/descargas.py RUTA/MFE_41.shp   # una vez: cotos, Mapa Forestal de la provincia y MDT25 -> datos/raw/
pixi run habitat                         # una vez: hábitat por especie -> datos/habitat/
pixi run diario                          # cada día: Open-Meteo -> salida/index.html + salida/capas/
```

El MFE25 de Castilla y León se descarga a mano desde MITECO. El visor carga cada capa (especie y día) solo cuando la eliges; el mapa base (IGN) necesita conexión.

Método y fuentes: `docs/revision-bibliografica.md`.

GitHub Actions regenera el mapa cada mañana y lo publica en GitHub Pages.

Datos: cotos © MICOCYL / Junta de Castilla y León · MFE25 © MITECO (CC BY 4.0) · MDT25 © IGN (CC BY 4.0) · meteorología © Open-Meteo (CC BY 4.0) · mapa base © IGN.

Es un índice relativo, no una probabilidad. En los cotos necesitas permiso de recolección; fuera de ellos, la recolección es episódica (máximo 3 kg por persona y día, sin vender; Decreto 31/2017 de Castilla y León) y no vale en terrenos señalizados como reservados. No comas ninguna seta sin una identificación segura.
