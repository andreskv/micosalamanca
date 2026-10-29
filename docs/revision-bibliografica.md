# Revisión bibliográfica: qué predice la fructificación de boletus y oronja

Base del índice de `src/especies.py` y `src/diario.py`. Cada regla del código lleva entre corchetes la clave de la fuente de esta tabla. **[H]** marca una heurística mía: la dirección del efecto tiene apoyo bibliográfico, pero el número concreto no sale de un estudio sobre estas especies en Salamanca.

Fecha de la revisión: 29-oct-2026.

## 1. Lo que dice la literatura, en cinco ideas

1. **En clima mediterráneo, el agua manda.** En pinares de Soria y Cataluña, la precipitación de finales de verano y principio de otoño es el principal motor de la producción de setas [AL17][CO19]. La humedad del suelo predice igual de bien que la lluvia (r = 0,63–0,72) [OL20]. La lluvia actúa con alrededor de un mes de retraso, mientras que la humedad del suelo actúa en el mismo mes [KA18].
2. **La temperatura tiene un óptimo, no un umbral.** En *B. edulis*, la fructificación es máxima con una media de unos 13 °C en los 20 días previos y crece de forma lineal con la lluvia acumulada en 26 días [BL26]. Al principio de la temporada, el calor limita la producción; al final la favorece, porque alarga la temporada [KA18].
3. **Las especies de verano dependen de tormentas.** En los rebollares de CyL, *B. aereus* y *B. reticulatus* responden a la cantidad de lluvia, a la temperatura y al **número de episodios lluviosos en los 15–20 días anteriores** [MICO-V].
4. **El hábitat fija el techo.** *B. edulis* es micorrícico de pino silvestre, rebollo, castaño y otros árboles [MP12][SC23], y en el oeste de CyL también de jara (*Cistus ladanifer*) [AP11]. La producción de *B. edulis* depende mucho del área basimétrica de la masa [MP12]. La oronja es termófila: prefiere bosque claro y soleado de castaño, alcornoque, encina o roble sobre suelo silíceo bien drenado [AMJC][RDB][TUL].
5. **La productividad del año anterior también cuenta.** El NDVI del año previo correlaciona con la cosecha (r = 0,41–0,60) [OL20]. Todavía no lo uso (ver §4).

## 2. De la literatura a las reglas del índice

Índice = Hábitat × Temporada × Agua × Temperatura del aire × Temperatura del suelo × Helada, de 0 a 100.

| Variable | Cómo la calculo | Fuente |
|---|---|---|
| Árbol hospedador | Pesos por especie arbórea (Especie1–3 del MFE25) ponderados por su ocupación (O1–O3, %) | [MP12][AP11][SC23][AMJC][TUL] + pesos [H] |
| Dosel | Trapecio sobre la fracción de cabida cubierta arbórea (FCCARB). La oronja prefiere 25–70 % | [RDB][AMJC] + cortes [H] |
| Jaral | *B. edulis* recibe 0,5 en teselas con *Cistus* | [AP11] + valor [H] |
| Altitud | Trapecio por especie desde el MDT25 | [TUL] para la oronja; resto [H]. [AL17] no encuentra efecto de la altitud en pinar, así que el trapecio es ancho |
| Ladera | Northness (no grados) para la solana de la oronja; TPI de ~500 m para las vaguadas en los boletus | [AMJC] + [H] |
| Temporada | Trapecio por día del año | [KA18][AL17][MICO-V][RDB][GUA] |
| Lluvia | Suma de 26 días (*B. edulis*) o 20 días (resto), en rampa entre dos umbrales | Ventanas: [BL26][MICO-V]. Umbrales en mm: [H] |
| Tormentas | Las especies de verano reciben un factor 0,6 + 0,4 × mín(1, días ≥ 5 mm / 2) | [MICO-V] + forma [H] |
| Humedad del suelo | Media de 7 días a 9–27 cm (Open-Meteo), en rampa de 0,10 a 0,25 m³/m³. Se combina con la lluvia mediante media geométrica | [OL20][KA18] + rampa [H] |
| Temperatura del aire | Gaussiana sobre la media de 20 días, corregida por altitud (−6,5 °C/km). Óptimos: *edulis* 13 °C; *reticulatus* 17 °C, *aereus* 19 °C y *caesarea* 20 °C | 13 °C: [BL26]. El resto: [H], por la termofilia [MICO-V][RDB][AMJC] |
| Temperatura del suelo | Solo en la oronja: rampa de 13 a 17 °C (media de 10 días a 6 cm) | [H] |
| Helada | Factor 0,3 si la mínima de 3 días baja de −1 °C | [H]; en [BL26] el seguimiento termina «con la primera helada fuerte» |

## 3. Lo que este índice NO es

- **No es una probabilidad calibrada.** No hay series públicas de fructificación con fecha y coordenada en estos cotos. Las parcelas de CESEFOR/Junta (las que usan [MP12][OL20]) son de Soria y no están abiertas.
- **Los umbrales [H] son la parte débil.** El estudio de los 13 °C [BL26] es un preprint sobre hayedos de Alemania. Lo uso por ser el único que estima la ventana diaria, pero su trasferencia a rebollares salmantinos está sin comprobar.
- **No se ha validado.** Solo hay un contraste cualitativo del hábitat con dos zonas boleteras conocidas, y las dos dan valores altos. Hace falta una prueba retrospectiva con fechas y lugares reales de recolección.

## 4. Variables que he dejado fuera, y por qué

| Variable | Motivo | Cuándo entraría |
|---|---|---|
| Humedad de suelo por satélite (Copernicus SWI/SSM 1 km, Sentinel-1) | En el catálogo STAC de CDSE el último dato disponible es del 15-sep-2026: unas 6 semanas de retraso. Además, la descarga exige cuenta de CDSE | Si bajara el retraso, o como capa de contraste del modelo de Open-Meteo |
| NDVI del año anterior | Predictor probado [OL20], pero cambia entre años, no entre días | Cuando quieras distinguir un año bueno de uno malo, o un monte vigoroso de otro |
| Área basimétrica | Fuerte en *B. edulis* [MP12], pero no hay capa continua pública a esta escala (el IFN es por parcelas) | Con LiDAR PNOA |
| *B. pinophilus* | No lo pediste. Los pinares ocupan unas 21.000 ha dentro de los cotos | Una entrada más en `especies.py` |

## 5. Fuentes

| Clave | Referencia | Tipo |
|---|---|---|
| AL17 | Alday JG, Martínez de Aragón J, de-Miguel S, Bonet JA (2017). Mushroom biomass and diversity are driven by different spatio-temporal scales along Mediterranean elevation gradients. *Sci Rep* 7:45824. doi:10.1038/srep45824 | Artículo |
| AP11 | Alonso Ponce R et al. (2011). Rockroses and *Boletus edulis* ectomycorrhizal association: realized niche and climatic suitability in Spain. *Fungal Ecol* 4:224–232. doi:10.1016/j.funeco.2010.10.002 | Artículo |
| BL26 | Brejon Lamartinière E, Hoffman JI (2025, v2 2026). Predicting porcini: a decade of sporocarp monitoring reveals the meteorological triggers of *Boletus edulis* fruiting in central European beech forests. *bioRxiv*. doi:10.64898/2025.12.12.693895 | **Preprint sin revisión por pares** |
| CO19 | Collado E et al. (2019). Mushroom productivity trends in relation to tree growth and climate across different European forest biomes. *Sci Total Environ* 689:602–615 | Artículo |
| KA18 | Karavani A, De Cáceres M, Martínez de Aragón J, Bonet JA, de-Miguel S (2018). Effect of climatic and soil moisture conditions on mushroom productivity… *Agric For Meteorol* 248:432–440 | Artículo |
| MP12 | Martínez-Peña F et al. (2012). Yield models for ectomycorrhizal mushrooms in *Pinus sylvestris* forests with special focus on *Boletus edulis*… *For Ecol Manage* 282:63–69. doi:10.1016/j.foreco.2012.06.034 | Artículo |
| OL20 | Olano JM et al. (2020). Primary productivity and climate control mushroom yields in Mediterranean pine forests. *Agric For Meteorol* 288–289:108015. doi:10.1016/j.agrformet.2020.108015 | Artículo |
| SC23 | Santolamazza-Carbone S et al. (2023). Artificial intelligence unveils key interactions between soil properties and climate factors on *Boletus edulis* and *B. reticulatus* mycelium in chestnut orchards. *Front Soil Sci* 3. doi:10.3389/fsoil.2023.1159793 | Artículo |
| TA16 | Taye ZM et al. (2016). Meteorological conditions and site characteristics driving edible mushroom production in *Pinus pinaster* forests of Central Spain. *Fungal Ecol* 23:30–41 | Artículo (contexto) |
| MICO-V | Programa Micocyl / CESEFOR. «Fructificación de especies típicas de inicio de verano». micologiacyl.es/noticias/fructificacion-de-especies-tipicas-de-inicio-de-verano | Divulgación técnica |
| TUL | Tulloss RE. *Amanita caesarea*, ficha en amanitaceae.org (ecología: 200–800 m, *Castanea*/*Quercus*, pH 6–6,5, Italia) | Base taxonómica |
| RDB | Gyosheva M. *Amanita caesarea*. Red Data Book of Bulgaria (bosques claros y cálidos, suelo drenado, VI–X) | Libro rojo |
| AMJC | Associació Micològica Joan Carranza, ficha *Amanita caesarea* (bosques térmicos, lugares abiertos orientados a levante, suelo silíceo) | Divulgación |
| GUA | Guadarramistas (2015). *Amanita caesarea* (años buenos: tormentas en agosto y lluvias en septiembre → salida en octubre) | Divulgación |

Datos:

- Open-Meteo Forecast API: lluvia, temperatura y humedad y temperatura del suelo modeladas; 40 días pasados y 8 de previsión.
- WFS de MICOCYL `mico_cyl_zonas_reguladas`: perímetros de los cotos, EPSG:25830.
- MFE25 de Castilla y León (MITECO, CC BY 4.0).
- MDT25 del IGN, por WCS (CC BY 4.0).