# Entrega de tarjetas en el Trolebús y la Ecovía de Quito · Dashboard EDA

Proyecto final del módulo **Programación y Análisis de Datos (MIACD02P01)** · Maestría en Inteligencia Artificial y Ciencia de Datos.

Análisis exploratorio de datos (EDA) y dashboard interactivo sobre la entrega de tarjetas de transporte por estación y perfil de tarjeta, para apoyar la **distribución del inventario de tarjetas**.

- **Dashboard:** `https://transporte-quito.streamlit.app/`
- **Repositorio:** `https://github.com/Vidajame83/proyecto_tarjetas_quito`
- **Integrantes:** Jorge Alexander Pasquel Moreno - Cesar Santiago Bustos Fraga - Victor David Jaramillo Mejía - Ramiro Xavier Teran Subia

## Contexto y profesión
**Profesión:** Analista de Datos, integrante del equipo de gestión del Sistema Integrado de Recaudo de la Empresa Pública Metropolitana de Transporte de Pasajeros Quito..

El sistema Trolebús y Ecovía de Quito entrega tarjetas de tres perfiles (Universal, Reducida y Preferencial) en estaciones, terminales, paradas, eventos y puntos de venta. Cada punto necesita un **stock de tarjetas**, pero la demanda, y la mezcla de perfiles, no es igual en todos los lugares, días ni canales. Un inventario mal repartido deja puntos sin tarjetas y otros con stock inmovilizado.

## Pregunta de análisis
> **¿En qué estaciones, días y canales se concentra la entrega de tarjetas según su perfil (Universal, Reducida y Preferencial), y cómo debería distribuirse el inventario de tarjetas entre estaciones, paradas y eventos del sistema de transporte de Quito?**

**Preguntas de apoyo**
1. ¿Qué estaciones entregan más tarjetas?
2. ¿Qué perfil de tarjeta entrega cada estación?
3. ¿Qué canal (estación, terminal, parada, evento o punto de venta) entrega más tarjetas por jornada?
4. ¿Hay días de la semana con más demanda?
5. ¿Cómo evolucionó la entrega de tarjetas desde el lanzamiento?

**Decisión que se quiere apoyar:** cuántas tarjetas, de qué perfil y en qué punto y día conviene tener disponibles.

## Fuente de datos
| Archivo | Contenido |
|---|---|
| `data/crudos/resumen_total_tarjetas.xlsx` | Registros diarios de entrega de tarjetas por punto (3 de marzo – 21 de septiembre de 2026). Se usa la hoja **`DETALLE_TARJETAS_nuevo`**, indicada por la fuente (1.664 registros × 14 columnas). |
| `data/crudos/estaciones_transporte_quito.csv` | Coordenadas de 14 estaciones y paradas principales, para el mapa. |

- Perfiles de tarjeta **confirmados por la fuente**: `tu` = Universal, `tr` = Reducida, `tp` = Preferencial.
- Son **datos reales, agregados por día y punto de entrega**: no contienen datos personales, por lo que su uso es compatible con la LOPDP.
- Se trabajan **en bruto**: los archivos de `data/crudos/` nunca se editan; toda la limpieza se hace en código.

## Tratamiento de los datos
Los datos se reciben **en bruto** y **nunca se modifican a mano**: todo el tratamiento está en código, se explica paso a paso en el notebook y se reúne en funciones de `src/limpieza.py`. El notebook comprueba que ambas vías producen **exactamente la misma tabla**, y el dashboard aplica esas mismas funciones cada vez que se abre.

### Principios
1. **Entender antes de corregir:** cada problema se detecta, se investiga su causa y recién entonces se decide qué hacer.
2. **Marcar antes que borrar:** solo se elimina lo que no aporta información o no corresponde al alcance; lo demás se conserva y se señala.
3. **No inventar datos:** no se imputa ningún valor.
4. **No usar lo que no se entiende:** una variable sin definición clara no entra al análisis.
5. **Documentar cada decisión:** con su evidencia en el notebook y su limitación en este README.

### Flujo de tratamiento
La función `preparar_datos()` aplica, en este orden:

| Orden | Función | Qué hace |
|---|---|---|
| 1 | `cargar_crudo()` | Lee la hoja `DETALLE_TARJETAS_nuevo` sin modificarla (1.664 registros × 14 columnas) |
| 2 | `renombrar_columnas()` | Nombra la columna sin encabezado como `tipo_registro` y renombra las cantidades según su perfil |
| 3 | `eliminar_columnas_sin_informacion()` | Elimina las columnas constantes (`valor_tarifa_*`) y la variable sin definición clara (`total_dinero`) |
| 4 | `derivar_sistema_y_tipo()` | Crea `sistema` (desde el corredor) y `tipo_ubicacion` (desde el tipo de registro) |
| 5 | `ajustar_tipos()` | Convierte las categóricas a `category` y crea `mes`, `semana` y `dia_semana` |
| 6 | `excluir_distribucion_municipio()` | Quita la entrega masiva de 27.000 tarjetas al municipio |
| 7 | `estandarizar_nombres()` | Unifica variantes de un mismo punto y aplica un formato uniforme a los nombres |
| 8 | `marcar_calidad()` | Agrega la columna `atipico` sin borrar filas |

Resultado: **1.663 registros × 16 columnas**, con 93 puntos de entrega.

### Decisiones por tipo de problema

| Problema | Cómo se detectó | Tratamiento | Justificación |
|---|---|---|---|
| **Columna sin nombre** | Nombres de columna con `repr()`: el encabezado son 3 espacios | Renombrada a `tipo_registro` | Sus valores (NORMAL, PARADA, EVENTO…) son el tipo de registro |
| **Perfiles con siglas** | Columnas `cantidad_tu / tr / tp` | Renombradas: Universal (`tu`), Reducida (`tr`), Preferencial (`tp`) | Significado confirmado por la fuente |
| **Columnas constantes** | `nunique()`: `valor_tarifa_*` tiene un solo valor | Eliminadas | No varían, y según la fuente solo identifican el perfil: no son precios |
| **Variable sin definición clara** | `total_dinero` solo coincide con tarjetas × valor en 27 de 1.664 registros y está en $0 en el 96 % de las paradas | **Excluida del análisis** | Usarla llevaría a conclusiones sin sustento |
| **Variables faltantes** | La hoja no trae `sistema` ni `tipo_ubicacion` | Derivadas: sistema ← corredor; tipo ← tipo de registro (Quitumbe = terminal) | **Validadas** contra la hoja `DETALLE_TARJETAS_FINAL`: 0 diferencias en 1.664 registros |
| **Registro fuera de alcance** | Registro más grande: 27.000 tarjetas con tipo `DISTRIBUCION_MUNICIPIO` | Excluido | No es entrega al público; distorsionaría todo el análisis |
| **Datos faltantes** | `isna()`: solo `numero_planilla` (211 registros, 12,7 %) | Sin tratamiento; no se imputa | Es un código de control que no se usa en el análisis |
| **Posibles duplicados** | `duplicated()`: 0 filas idénticas; 40 casos de misma fecha y punto | **Se conservan** | Son planillas distintas del mismo día (normal y punto de venta en Quitumbe); la clave real es fecha + punto + tipo de registro |
| **Nombres inconsistentes** | Valores únicos en orden alfabético | 17 variantes unificadas con un diccionario y formato uniforme con `formatear_nombre()` (103 -> 93 puntos) | Variantes del mismo punto, mayúsculas mezcladas, tildes faltantes y errores de codificación (`I¥AQUITO` -> `Iñaquito`) |
| **Corredor de los eventos** | `crosstab`: el 100 % de los eventos figura en Trole Sur | Las comparaciones por corredor **excluyen eventos** | Es una asignación administrativa, no la ubicación real |
| **Atípicos** | Regla 1,5·IQR **dentro de cada tipo de ubicación**: 135 registros (102 en estaciones, 26 en el terminal, 7 en otros tipos) | **Se conservan** y se marcan en `atipico` | Son días reales del lanzamiento (83 en marzo y 42 en abril), no errores |
| **Asimetría** | Asimetría ≈ 2,5 en tarjetas por registro | Se usan **medianas**, Spearman y Kruskal-Wallis | Son medidas robustas a los valores extremos |

### Variables del análisis

| Estado | Variables |
|---|---|
| **Se usan** | `fecha`, `corredor`, `estacion_o_evento`, `tipo_registro`, `tarjetas_universal`, `tarjetas_reducida`, `tarjetas_preferencial`, `total_tarjetas` |
| **Derivadas** | `sistema`, `tipo_ubicacion`, `mes`, `semana`, `dia_semana`, `atipico` |
| **Con cautela** | `horario_extendido`: definición por confirmar; solo en un análisis exploratorio del notebook, no en las decisiones ni en el dashboard |
| **Solo control** | `numero_planilla` |
| **Excluidas** | `valor_tarifa_tu / tr / tp` (constantes), `total_dinero` (sin definición clara) |

### Lo que no se hizo, y por qué
- **No se imputaron valores:** las variables del análisis están completas, y el único faltante está en un código de control.
- **No se eliminaron atípicos:** son demanda real; se neutralizan con medidas robustas. En el dashboard, la casilla *Excluir días atípicos* permite comparar los resultados con y sin ellos.
- **No se calcularon montos de dinero:** no hay ninguna variable monetaria con una definición confiable.

## Indicadores del dashboard (KPI)
El dashboard muestra **cinco indicadores principales** en la parte superior y **indicadores de apoyo** dentro de cada pestaña. Todos:
- se calculan desde la **hoja `DETALLE_TARJETAS_nuevo`** de `data/crudos/resumen_total_tarjetas.xlsx`, después del tratamiento descrito arriba (función `preparar_datos()` de `src/limpieza.py`);
- **se recalculan con los filtros** de la barra lateral (período, sistema, tipo de ubicación y exclusión de días atípicos);
- usan solo **cantidades de tarjetas**: no hay indicadores monetarios porque `total_dinero` no tiene una definición clara.

Los valores de referencia corresponden a **todo el período, sin filtros** (1.663 registros).

### Indicadores principales

#### 1. Tarjetas entregadas
- **Pregunta que responde:** ¿cuántas tarjetas se entregaron en el período, lugar y canal seleccionados?
- **Construcción:** suma de `total_tarjetas` de los registros filtrados.
  `f["total_tarjetas"].sum()`
- **Columnas de origen:** `total_tarjetas` (= `cantidad_tu` + `cantidad_tr` + `cantidad_tp`; se verificó que la suma coincide en todos los registros).
- **Valor de referencia:** 120.740 tarjetas.
- **Aporte a la pregunta:** mide el **volumen total de demanda**, que es la base para dimensionar el inventario. Al filtrar, permite comparar cuánto pesa cada sistema, canal o período.

#### 2. Mediana por jornada
- **Pregunta que responde:** ¿cuántas tarjetas se entregan en una jornada típica?
- **Construcción:** mediana de `total_tarjetas` por registro (un registro = un punto en un día).
  `f["total_tarjetas"].median()`
- **Columnas de origen:** `total_tarjetas`.
- **Valor de referencia:** 47 tarjetas por jornada.
- **Por qué la mediana y no el promedio:** la distribución es muy asimétrica (asimetría ≈ 2,5) por los días de alta demanda de marzo y abril; el promedio se inflaría y no representaría un día normal.
- **Aporte a la pregunta:** indica el **tamaño típico de un lote** de tarjetas por punto y día.

#### 3. % Reducida
- **Pregunta que responde:** ¿qué parte de las tarjetas entregadas son de perfil Reducida?
- **Construcción:** tarjetas Reducidas ÷ total de tarjetas × 100.
  `f["tarjetas_reducida"].sum() / f["total_tarjetas"].sum() * 100`
- **Columnas de origen:** `cantidad_tr` (perfil Reducida, confirmado por la fuente) y `total_tarjetas`.
- **Valor de referencia:** 20,6 %.
- **Aporte a la pregunta:** define **qué proporción del inventario** debe ser de este perfil. Es el indicador que más cambia entre estaciones (del 13 % al 25 %).

#### 4. % Preferencial
- **Pregunta que responde:** ¿qué parte de las tarjetas entregadas son de perfil Preferencial?
- **Construcción:** tarjetas Preferenciales ÷ total de tarjetas × 100.
  `f["tarjetas_preferencial"].sum() / f["total_tarjetas"].sum() * 100`
- **Columnas de origen:** `cantidad_tp` (perfil Preferencial, confirmado por la fuente) y `total_tarjetas`.
- **Valor de referencia:** 3,4 %.
- **Aporte a la pregunta:** completa la **mezcla de perfiles** del inventario. Como es un perfil poco frecuente, evita tener stock inmovilizado. El % Universal se obtiene por diferencia (≈ 76 %).

#### 5. Puntos activos
- **Pregunta que responde:** ¿en cuántos puntos distintos se entregaron tarjetas?
- **Construcción:** número de valores distintos de `estacion_o_evento`, después de unificar los nombres.
  `f["estacion_o_evento"].nunique()`
- **Columnas de origen:** `estacion_o_evento` (estandarizada: 103 nombres en bruto -> 93 puntos reales).
- **Valor de referencia:** 93 puntos.
- **Aporte a la pregunta:** indica **entre cuántos puntos se reparte** el inventario. Al filtrar por tipo de ubicación, muestra cuántos puntos de cada canal hay que abastecer.

### Indicadores de apoyo, por pestaña

| Pestaña | Indicador | Construcción | Valor de referencia | Pregunta de apoyo que responde |
|---|---|---|---|---|
| Estaciones y mapa | Concentración de los N principales puntos | Tarjetas de los N puntos con más entregas ÷ total × 100 | Top 6: 72 % · Top 10: 80 % | ¿Qué estaciones entregan más tarjetas? |
| Estaciones y mapa | Participación de cada punto (en la ficha del mapa) | Tarjetas del punto ÷ total × 100 | El Recreo: 21 % | ¿Dónde se concentra la entrega? |
| Perfiles por estación | Mezcla de perfiles por estación | Tarjetas de cada perfil ÷ tarjetas de la estación × 100 (solo estaciones y terminal) | Reducida: 13 % a 25 % | ¿Qué perfil entrega cada estación? |
| Perfiles por estación | Mezcla de perfiles por corredor | Igual que el anterior, agrupando por corredor y **sin eventos** | Trole Sur: 25 % Reducida | ¿Cambia el perfil entre corredores? |
| Canales | Tarjetas por jornada por canal | Mediana de `total_tarjetas` por tipo de ubicación | Evento 105 · Estación 51 · Terminal 33 · Parada 29 · Punto de venta 6 | ¿Qué canal entrega más por jornada? |
| Canales | Participación de cada canal | Tarjetas del canal ÷ total × 100 | Las estaciones concentran la mayor parte | ¿Qué canal aporta más volumen? |
| Días | Mediana diaria por corredor y día | Mediana de `total_tarjetas` por corredor y día de la semana (solo estaciones y terminal) | Domingo, el día más bajo (salvo Trole Norte) | ¿Hay días con más demanda? |
| Evolución | Tarjetas por semana | Suma semanal de `total_tarjetas` por tipo de ubicación | Caída de ≈ 80 % entre marzo y junio | ¿Cómo evolucionó la entrega? |
| Evolución | Mediana diaria mensual por estación | Mediana mensual de `total_tarjetas` en estaciones y terminal | 169 (marzo) -> 30 (junio) -> 48 (septiembre) | ¿La demanda actual es menor que la inicial? |

### Cómo responden los indicadores a la pregunta de análisis

> *¿En qué estaciones, días y canales se concentra la entrega de tarjetas según su perfil, y cómo debería distribuirse el inventario?*

| Parte de la pregunta | Indicadores | Decisión de inventario que apoyan |
|---|---|---|
| **¿En qué estaciones?** | Tarjetas entregadas, concentración de los principales puntos, puntos activos | Repartir el stock en proporción a la demanda: El Recreo necesita cerca de una de cada cinco tarjetas |
| **¿Según qué perfil?** | % Reducida, % Preferencial, mezcla por estación y por corredor | Armar cada lote con la mezcla de su estación: ≈ 25 % Reducidas en El Recreo y Quitumbe, ≈ 13 % en Playón de la Marín |
| **¿En qué canales?** | Tarjetas por jornada por canal, participación de cada canal | Llevar lotes grandes a los eventos (≈ 100 tarjetas por jornada) y lotes mínimos a los puntos de venta |
| **¿En qué días?** | Mediana diaria por corredor y día | Reponer antes del sábado en Labrador; reducir stock los domingos en el resto |
| **¿Cuánto en total?** | Mediana por jornada y evolución mensual | Dimensionar con la demanda **actual** (≈ 30-50 por jornada), no con la del inicio del registro |

## Resultados principales
1. La demanda cayó cerca de un 80 % después del lanzamiento (mediana diaria por estación: 169 en marzo -> 30 en junio).
2. Seis estaciones concentran el 72 % de las tarjetas; El Recreo, el 21 %.
3. Cada estación entrega una mezcla distinta de perfiles: las Reducidas van del 13 % (Playón de la Marín) al 25 % (El Recreo), y El Recreo entrega el 36 % de las Reducidas de las estaciones.
4. El 76 % de las tarjetas son Universales, el 21 % Reducidas y el 3 % Preferenciales; el Trole Sur entrega más tarjetas Reducidas (25 % frente a 16-18 %).
5. El domingo es el día de menor demanda, salvo en el Trole Norte, donde el sábado es el más alto.
6. Los eventos entregan el doble de tarjetas por jornada que una estación (105 frente a 51).

## Metodología: EDA en 7 pasos
El notebook `notebooks/01_EDA_tarjetas.ipynb` desarrolla el análisis completo, con cada línea de código comentada:

| Paso | Qué se hace | Técnicas y gráficos |
|---|---|---|
| **1. Pregunta** | Pregunta principal, 5 preguntas de apoyo y decisión | — |
| **2. Estructura** | Hojas, dimensiones, tipos, columna sin nombre, diccionario de variables, verificación de `total_dinero`, variables derivadas y validadas, ajuste de tipos y alcance | `info()`, `nunique()`, `repr()`, `crosstab` |
| **3. Univariado** | Distribución de las tarjetas, asimetría, mezcla de perfiles y variables categóricas | Histogramas (escala normal y logarítmica), media frente a mediana |
| **4. Bivariado** | Tarjetas por tipo de ubicación, correlación entre variables y entre los tres perfiles, día de la semana, horario extendido | Boxplot, Kruskal-Wallis, matriz de Spearman, dispersión 2D y **3D interactiva** |
| **5. Calidad de datos** | Faltantes, duplicados, nombres inconsistentes, corredor de los eventos y atípicos | `isna()`, `duplicated()`, regla 1,5·IQR por tipo de ubicación |
| **6. Segmentación** | Evolución, concentración de puntos, canales, **perfil por estación**, perfil por corredor, día × corredor y vista geográfica | Series de tiempo, ranking, chi-cuadrado y V de Cramér, barras apiladas, mapa de calor, **mapa de burbujas** |
| **7. Hallazgos** | Hallazgos con cifras calculadas, decisiones de inventario y limitaciones | — |

Al final, el notebook comprueba que su limpieza y la de `src/limpieza.py` producen **exactamente la misma tabla** (resultado: `True`).

## El dashboard
`dash_app.py` construye el dashboard con **Streamlit**, gráficos interactivos de **Plotly** y un mapa de **Folium**. Parte siempre del Excel en bruto y aplica la misma limpieza del notebook (`preparar_datos()` de `src/limpieza.py`).

- **Filtros** (barra lateral): período, sistema, tipo de ubicación y exclusión de días atípicos.
- **Cinco indicadores**: tarjetas entregadas, mediana por jornada, % Reducida, % Preferencial y puntos activos.
- **Siete pestañas**, en el orden de la pregunta:

| Pestaña | Qué muestra |
|---|---|
| Estaciones y mapa | Ranking de los puntos con más tarjetas y mapa de burbujas con ficha por punto |
| Perfiles por estación | Mezcla de perfiles por estación (gráfico y tabla de cantidades) y por corredor |
| Canales | Tarjetas por jornada y participación de cada tipo de ubicación |
| Días | Mapa de calor de la mediana diaria por corredor y día |
| Evolución | Tarjetas por semana y mediana diaria mensual |
| Calidad de los datos | Problemas encontrados en los datos en bruto y decisión tomada, calculados en vivo |
| Decisiones | Recomendaciones de inventario y limitaciones |

## Cómo ejecutar
Requiere **Python 3.11 o superior**. Todos los comandos se ejecutan en una terminal ubicada en la carpeta del proyecto.

```bash
# 1. Clonar el repositorio
git https://github.com/Vidajame83/proyecto_tarjetas_quito
cd proyecto_tarjetas_quito

# 2. Crear y activar un entorno virtual propio del proyecto
python -m venv .venv
.venv\Scripts\activate            # Windows  ·  en Mac/Linux: source .venv/bin/activate

# 3. Instalar las librerías con sus versiones exactas
python -m pip install -r requirements.txt

# 4. Ejecutar el dashboard (se abre en http://localhost:8501)
python -m streamlit run dash_app.py
```

**Notebook del EDA:** abrir `notebooks/01_EDA_tarjetas.ipynb` en VS Code o Jupyter, seleccionar el kernel del entorno del proyecto y ejecutar **Restart -> Run All**. Genera los archivos de `reportes/` y `data/procesados/`.

**Recomendaciones**
- El dashboard se ejecuta con `streamlit run`, no con `python dash_app.py`: Streamlit levanta un servidor local y lo muestra en el navegador.
- Instalar librerías con el notebook y el dashboard **cerrados**: Windows no permite reemplazar archivos que están en uso.
- Dentro de VS Code, los mapas muestran las burbujas pero **no las calles**, porque su visor bloquea las imágenes externas. Los mapas completos se ven en el navegador: en el dashboard o abriendo los archivos de `reportes/`.

## Estructura del proyecto
```
proyecto_tarjetas_quito/
├── dash_app.py                     # dashboard en Streamlit
├── requirements.txt                # librerías con versiones exactas
├── README.md                       # este archivo
├── .gitignore                      # archivos que no se suben a GitHub
├── .streamlit/
│   └── config.toml                 # colores y tipografía del dashboard
├── data/
│   ├── crudos/                     # datos en bruto, sin modificar
│   │   ├── resumen_total_tarjetas.xlsx
│   │   └── estaciones_transporte_quito.csv
│   └── procesados/
│       └── tarjetas_procesadas.csv # tabla procesada que genera el notebook (evidencia)
├── notebooks/
│   └── 01_EDA_tarjetas.ipynb       # EDA completo en 7 pasos, con código comentado
├── src/
│   ├── __init__.py                 # convierte src en un paquete importable
│   └── limpieza.py                 # funciones de carga y limpieza (las usan el notebook y el dashboard)
├── reportes/                       # resultados interactivos que genera el notebook
│   ├── mapa_tarjetas.html          # mapa de burbujas por punto de entrega
│   └── perfiles_3d.html            # dispersión 3D de los tres perfiles de tarjeta
└── docs/
    └── Proyecto_final_Dashboard_EDA.pdf   # cargar el documento cuando se tenga
```

**Cómo se relacionan los archivos:** `data/crudos/` -> `src/limpieza.py` (una sola limpieza) -> la usan tanto `notebooks/01_EDA_tarjetas.ipynb` (análisis) como `dash_app.py` (dashboard).

## Publicar el dashboard (Streamlit Community Cloud)
1. Subir este repositorio a GitHub (incluida la carpeta `data/crudos/`, que el dashboard necesita).
2. Entrar a [share.streamlit.io](https://share.streamlit.io) con la cuenta de GitHub.
3. **Create app** -> elegir el repositorio, la rama `main` y el archivo **`dash_app.py`** -> **Deploy**.
4. Copiar el enlace generado al inicio de este README y en la entrega.

## Limitaciones
- `total_dinero` no tiene una definición clara y se excluyó: el análisis no incluye información monetaria.
- La hoja no trae `sistema` ni `tipo_ubicacion`: se derivaron y se validaron contra la hoja `DETALLE_TARJETAS_FINAL` (0 diferencias).
- Los eventos figuran administrativamente en el corredor Trole Sur; las comparaciones por corredor los excluyen.
- El significado de `horario_extendido` debe confirmarse con la fuente; solo se usa en un análisis exploratorio.
- El mapa incluye los 14 puntos con coordenadas (83 % de las tarjetas); los eventos itinerantes no tienen ubicación fija.
- No hay datos por hora ni de las personas usuarias, y siete meses no muestran estacionalidad anual.
- Es un análisis **descriptivo**: muestra asociaciones, no causas.
