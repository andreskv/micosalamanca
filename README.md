# MicoSalamanca

Índice relativo diario de fructificación de *Boletus edulis*, *B. aereus*, *B. reticulatus* y *Amanita caesarea* en los 14 cotos micológicos de Salamanca. Cubre hoy y los 7 días siguientes, con celdas de unos 50 m.

## Uso

```
pixi run habitat   # una vez: cotos + MFE25 + MDT25 -> datos/habitat/
pixi run diario    # cada día: Open-Meteo -> salida/index.html
```

`salida/index.html` es un único fichero autocontenido. Las capas y Leaflet van dentro; solo el mapa base (IGN) necesita conexión.

Método y fuentes: `docs/revision-bibliografica.md`.

GitHub Actions regenera el mapa cada mañana y lo publica en GitHub Pages.

Datos: cotos © MICOCYL / Junta de Castilla y León · MFE25 © MITECO (CC BY 4.0) · MDT25 © IGN (CC BY 4.0) · meteorología © Open-Meteo (CC BY 4.0) · mapa base © IGN.

Es un índice relativo, no una probabilidad. Necesitas permiso de recolección en cada coto. No comas ninguna seta sin una identificación segura.
