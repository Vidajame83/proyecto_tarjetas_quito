"""
Dashboard EDA · Entrega de tarjetas del sistema de transporte de Quito.

Ejecutar en la terminal, desde la carpeta del proyecto:
    python -m streamlit run dash_app.py

El dashboard parte SIEMPRE del Excel en bruto (data/crudos/) y aplica la misma
limpieza del notebook mediante las funciones de src/limpieza.py.
"""

import folium # mapa interactivo (Leaflet + OpenStreetMap)
import numpy as np # raíz cuadrada para escalar las burbujas
import pandas as pd # manejo de tablas
import plotly.express as px # gráficos interactivos
import streamlit as st # construcción del dashboard web

from src.limpieza import (cargar_coordenadas, cargar_crudo, preparar_datos, # nuestras funciones
                          renombrar_columnas)

# --------
# Configuración general
# --------

# Título de la pestaña del navegador y diseño a lo ancho de la pantalla
st.set_page_config(page_title="Tarjetas · Trolebús y Ecovía", page_icon="🚌", layout="wide")

# Colores fijos: cada corredor y cada tipo de ubicación tiene SIEMPRE el mismo color en todos los gráficos
COLOR_CORREDOR = {"Trole Sur": "#1B6CA8", "Trole Norte": "#2A9D8F",
                  "Ecovía Norte": "#E9A23B", "Sur Oriental": "#7B5EA7"}
COLOR_TIPO = {"ESTACION": "#16324F", "TERMINAL": "#4F7CAC", "EVENTO": "#E07A5F",
              "PARADA": "#81B29A", "PUNTO_VENTA": "#B8B8B8"}
# Nombres legibles para mostrar en pantalla en lugar de los códigos del archivo
NOMBRE_TIPO = {"ESTACION": "Estación", "TERMINAL": "Terminal", "EVENTO": "Evento",
               "PARADA": "Parada", "PUNTO_VENTA": "Punto de venta"}
# Perfiles de tarjeta confirmados por la fuente: tu = Universal, tr = Reducida, tp = Preferencial
PERFILES = {"tarjetas_universal": "Universal", "tarjetas_reducida": "Reducida",
            "tarjetas_preferencial": "Preferencial"}


# --------
# Carga de datos (se guarda en caché: se calcula una sola vez por sesión)
# --------

@st.cache_data
def cargar_todo():
    """Carga el Excel en bruto, lo limpia y lee las coordenadas."""
    crudo = cargar_crudo() # datos tal como llegaron (para la pestaña de calidad)
    datos = preparar_datos() # datos limpios con la misma lógica del notebook
    coords = cargar_coordenadas() # coordenadas de las estaciones principales
    return crudo, datos, coords


crudo, df, coords = cargar_todo() # tres tablas listas para usar


# --------
# Barra lateral: filtros
# --------

st.sidebar.header("Filtros")

# Rango de fechas: por defecto, todo el período disponible
fecha_min, fecha_max = df["fecha"].min().date(), df["fecha"].max().date()
rango = st.sidebar.date_input("Período", value=(fecha_min, fecha_max),
                              min_value=fecha_min, max_value=fecha_max)

# Selección múltiple de sistema y tipo de ubicación (por defecto, todos)
sistemas = st.sidebar.multiselect("Sistema", sorted(df["sistema"].unique()),
                                  default=sorted(df["sistema"].unique()))
tipos = st.sidebar.multiselect("Tipo de ubicación", list(NOMBRE_TIPO),
                               default=list(NOMBRE_TIPO), format_func=NOMBRE_TIPO.get)

# Opción para ver la demanda "normal", sin los días extraordinarios del lanzamiento
sin_atipicos = st.sidebar.checkbox("Excluir días atípicos", value=False,
                                   help="Días con entregas muy por encima de lo habitual (regla 1,5·IQR). "
                                        "Casi todos son de marzo y abril, durante el lanzamiento.")

st.sidebar.caption("Los eventos figuran administrativamente en el corredor Trole Sur; "
                   "por eso las comparaciones por corredor excluyen eventos.")

# date_input devuelve una sola fecha mientras el usuario está eligiendo el rango
if not isinstance(rango, tuple) or len(rango) != 2:
    st.info("Elige la fecha de inicio y la de fin del período.")
    st.stop()

# Aplicamos todos los filtros a la vez
filtro = (df["fecha"].dt.date.between(rango[0], rango[1])
          & df["sistema"].isin(sistemas)
          & df["tipo_ubicacion"].isin(tipos))
if sin_atipicos:
    filtro &= ~df["atipico"]
f = df[filtro] # f = datos filtrados que usan todos los gráficos

if f.empty: # si no queda nada, avisamos qué hacer en vez de mostrar errores
    st.warning("No hay registros con esos filtros. Amplía el período o agrega sistemas y tipos de ubicación.")
    st.stop()


# --------
# Encabezado e indicadores
# --------

st.title("Entrega de tarjetas en el Trolebús y la Ecovía de Quito")
st.markdown("¿En qué **estaciones, días y canales** se concentra la entrega de tarjetas según su **perfil**, "
            "y cómo distribuir el **inventario**? Registros diarios de marzo a septiembre de 2026.")

total_filtrado = f["total_tarjetas"].sum() # base para los porcentajes de los indicadores

k1, k2, k3, k4, k5 = st.columns(5) # cinco indicadores en una fila
k1.metric("Tarjetas entregadas", f"{total_filtrado:,.0f}")
k2.metric("Mediana por jornada", f"{f['total_tarjetas'].median():,.0f}")
k3.metric("% Reducida", f"{f['tarjetas_reducida'].sum() / total_filtrado * 100:.1f} %")
k4.metric("% Preferencial", f"{f['tarjetas_preferencial'].sum() / total_filtrado * 100:.1f} %")
k5.metric("Puntos activos", f"{f['estacion_o_evento'].nunique()}")

# Pestañas: cada una responde a una de las preguntas de apoyo del EDA, en el orden de la pregunta
tab_puntos, tab_perfiles, tab_canales, tab_dias, tab_evol, tab_calidad, tab_decisiones = st.tabs(
    ["Estaciones y mapa", "Perfiles por estación", "Canales", "Días", "Evolución",
     "Calidad de los datos", "Decisiones"])


# --------
# 1. Evolución
# --------

with tab_evol:
 # Total semanal de tarjetas, separado por tipo de ubicación
    semanal = (f.groupby(["semana", "tipo_ubicacion"], observed=True)["total_tarjetas"]
                 .sum().reset_index())
    semanal["tipo"] = semanal["tipo_ubicacion"].map(NOMBRE_TIPO)
    fig = px.area(semanal, x="semana", y="total_tarjetas", color="tipo",
                  color_discrete_map={NOMBRE_TIPO[k]: v for k, v in COLOR_TIPO.items()},
                  labels={"semana": "Semana", "total_tarjetas": "Tarjetas", "tipo": "Tipo"},
                  title="Tarjetas entregadas por semana")
    st.plotly_chart(fig, width="stretch")
    st.caption("La primera y la última semana del período están incompletas, por eso se ven más bajas.")

 # Mediana diaria por estación o terminal en cada mes (medida robusta a los días extremos)
    fijos = f[f["tipo_ubicacion"].isin(["ESTACION", "TERMINAL"])]
    if not fijos.empty:
        mensual = fijos.groupby("mes")["total_tarjetas"].median().reset_index()
        fig = px.bar(mensual, x="mes", y="total_tarjetas", text_auto=".0f",
                     labels={"mes": "Mes", "total_tarjetas": "Mediana diaria"},
                     title="Mediana diaria por estación o terminal", color_discrete_sequence=["#16324F"])
        st.plotly_chart(fig, width="stretch")
    st.caption("La demanda cayó cerca de un 80 % entre marzo y junio, después del lanzamiento, "
               "y repuntó levemente en septiembre.")


# --------
# 2. Puntos y mapa
# --------

with tab_puntos:
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        n = st.slider("Puntos a mostrar", min_value=5, max_value=25, value=10) # tamaño del ranking
        ranking = (f.groupby("estacion_o_evento")
                     .agg(tarjetas=("total_tarjetas", "sum"),
                          tipo=("tipo_ubicacion", lambda s: NOMBRE_TIPO[s.mode().iloc[0]]))
                     .nlargest(n, "tarjetas").reset_index())
        fig = px.bar(ranking.sort_values("tarjetas"), x="tarjetas", y="estacion_o_evento",
                     color="tipo", orientation="h", height=520,
                     color_discrete_map={NOMBRE_TIPO[k]: v for k, v in COLOR_TIPO.items()},
                     labels={"tarjetas": "Tarjetas", "estacion_o_evento": "", "tipo": "Tipo"},
                     title=f"Los {n} puntos con más tarjetas")
        fig.update_yaxes(categoryorder="total ascending") # ordena las barras por total, no por color
        st.plotly_chart(fig, width="stretch")
        total = f["total_tarjetas"].sum()
        st.caption(f"Estos {n} puntos concentran el {ranking['tarjetas'].sum() / total * 100:.0f} % "
                   "de las tarjetas del período filtrado.")

    with col_der:
 # Resumen por punto de entrega, unido con sus coordenadas (solo los 14 puntos que las tienen)
        por_punto = (f.groupby("estacion_o_evento")
                       .agg(tarjetas=("total_tarjetas", "sum"),
                            universal=("tarjetas_universal", "sum"),
                            reducida=("tarjetas_reducida", "sum"),
                            preferencial=("tarjetas_preferencial", "sum"),
                            jornadas=("fecha", "nunique"),
                            tipo=("tipo_ubicacion", lambda s: s.mode().iloc[0]))
                       .reset_index())
        geo = por_punto.merge(coords, on="estacion_o_evento", how="inner")

        st.markdown("**Dónde se entregan las tarjetas**")
        if geo.empty:
            st.info("Ninguno de los puntos filtrados tiene coordenadas.")
        else:
 # Mapa base de OpenStreetMap centrado en Quito
            mapa = folium.Map(location=[-0.22, -78.51], zoom_start=11, tiles="OpenStreetMap")
            maximo = geo["tarjetas"].max() # para escalar las burbujas
            for _, fila in geo.iterrows():
 # Radio ∝ raíz de las tarjetas: así el ÁREA de la burbuja es proporcional al valor
                radio = 5 + 30 * np.sqrt(fila["tarjetas"] / maximo)
                ficha = (f"<b>{fila['nombre_oficial']}</b><br>"
                         f"Tipo: {NOMBRE_TIPO[fila['tipo']]}<br>"
                         f"Tarjetas: {fila['tarjetas']:,.0f} "
                         f"({fila['tarjetas'] / total * 100:.1f} % del total)<br>"
                         f"Universal: {fila['universal']:,.0f} · Reducida: {fila['reducida']:,.0f} · "
                         f"Preferencial: {fila['preferencial']:,.0f}<br>"
                         f"Días con entregas: {fila['jornadas']}")
                folium.CircleMarker(
                    location=[fila["lat"], fila["lon"]], # posición del punto
                    radius=radio,
                    color=COLOR_TIPO[fila["tipo"]], weight=2, # borde
                    fill=True, fill_color=COLOR_TIPO[fila["tipo"]], fill_opacity=0.55,
                    popup=folium.Popup(ficha, max_width=260), # ficha al hacer clic
                    tooltip=f"{fila['estacion_o_evento']}: {fila['tarjetas']:,.0f} tarjetas", # al pasar el mouse
                ).add_to(mapa)
 # Insertamos el mapa (una página HTML completa, generada por nosotros) dentro del dashboard
            st.iframe(mapa.get_root().render(), height=500)
            st.caption(f"Clic en una burbuja para ver su ficha. El mapa muestra {len(geo)} puntos con "
                       f"coordenadas, que suman el {geo['tarjetas'].sum() / total * 100:.0f} % de las "
                       "tarjetas filtradas. Los eventos itinerantes no tienen ubicación fija.")


# --------
# 3. Canales
# --------

with tab_canales:
 # Tarjetas por jornada (mediana) y porcentaje del total en cada tipo de ubicación
    canales = (f.groupby("tipo_ubicacion", observed=True)["total_tarjetas"]
                 .agg(tarjetas_por_jornada="median", total="sum").reset_index())
    canales["%_del_total"] = canales["total"] / canales["total"].sum() * 100
    canales["tipo"] = canales["tipo_ubicacion"].map(NOMBRE_TIPO)
    mapa_color = {NOMBRE_TIPO[k]: v for k, v in COLOR_TIPO.items()}

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(canales.sort_values("tarjetas_por_jornada", ascending=False),
                     x="tipo", y="tarjetas_por_jornada", color="tipo", text_auto=".0f",
                     color_discrete_map=mapa_color,
                     labels={"tipo": "", "tarjetas_por_jornada": "Tarjetas por jornada (mediana)"},
                     title="Intensidad: tarjetas por jornada")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.bar(canales.sort_values("%_del_total", ascending=False),
                     x="tipo", y="%_del_total", color="tipo", text_auto=".1f",
                     color_discrete_map=mapa_color,
                     labels={"tipo": "", "%_del_total": "% de todas las tarjetas"},
                     title="Volumen: participación en el total")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    st.caption("Los eventos son el canal más intenso por jornada (conviene llevar lotes grandes), "
               "pero las estaciones concentran la mayor parte del total porque abren todos los días.")


# --------
# 4. Perfiles de tarjeta por estación y por corredor
# --------

with tab_perfiles:
    colores_perfil = {"Universal": "#16324F", "Reducida": "#E9A23B", "Preferencial": "#81B29A"}
    fijos = f[f["tipo_ubicacion"].isin(["ESTACION", "TERMINAL"])] # abren todos los días

    if fijos.empty:
        st.info("Incluye estaciones o terminales en los filtros para comparar perfiles por estación.")
    else:
 # Mezcla de perfiles de cada estación, en formato "largo" para las barras apiladas
        por_estacion = fijos.groupby("estacion_o_evento")[list(PERFILES)].sum().rename(columns=PERFILES)
        pct = por_estacion.div(por_estacion.sum(axis=1), axis=0) * 100
        orden = pct.sort_values("Reducida").index.tolist() # de menos a más Reducidas
        largo = (pct.reset_index()
                   .melt(id_vars="estacion_o_evento", var_name="perfil", value_name="%"))
        fig = px.bar(largo, x="%", y="estacion_o_evento", color="perfil", orientation="h",
                     text_auto=".1f", color_discrete_map=colores_perfil,
                     category_orders={"estacion_o_evento": orden[::-1]},
                     labels={"%": "% de tarjetas", "estacion_o_evento": "", "perfil": "Perfil"},
                     title="Perfil de tarjeta por estación")
        st.plotly_chart(fig, width="stretch")

 # Tabla con las cantidades: es lo que se usa para planificar el inventario
        tabla = por_estacion.assign(Total=por_estacion.sum(axis=1)).sort_values("Total", ascending=False)
        tabla["% Reducida"] = (tabla["Reducida"] / tabla["Total"] * 100).round(1)
        st.dataframe(tabla, width="stretch")
        st.caption(f"La proporción de tarjetas Reducidas va del {pct['Reducida'].min():.0f} % "
                   f"({pct['Reducida'].idxmin()}) al {pct['Reducida'].max():.0f} % "
                   f"({pct['Reducida'].idxmax()}): cada estación necesita una mezcla distinta de tarjetas.")

    sin_eventos = f[f["tipo_ubicacion"] != "EVENTO"] # el corredor de los eventos no es real
    if not sin_eventos.empty:
        largo_c = (sin_eventos.groupby("corredor", observed=True)[list(PERFILES)].sum()
                     .rename(columns=PERFILES).reset_index()
                     .melt(id_vars="corredor", var_name="perfil", value_name="tarjetas"))
        largo_c["%"] = largo_c["tarjetas"] / largo_c.groupby("corredor")["tarjetas"].transform("sum") * 100
        fig = px.bar(largo_c, x="%", y="corredor", color="perfil", orientation="h", text_auto=".1f",
                     color_discrete_map=colores_perfil,
                     labels={"%": "% de tarjetas", "corredor": "", "perfil": "Perfil"},
                     title="Perfil de tarjeta por corredor (sin eventos)")
        st.plotly_chart(fig, width="stretch")


# --------
# 5. Días de la semana
# --------

with tab_dias:
    fijos = f[f["tipo_ubicacion"].isin(["ESTACION", "TERMINAL"])] # abren todos los días
    if fijos.empty:
        st.info("Incluye estaciones o terminales en los filtros para comparar días.")
    else:
        calor = fijos.pivot_table(values="total_tarjetas", index="corredor", columns="dia_semana",
                                  aggfunc="median", observed=True)
        fig = px.imshow(calor, text_auto=".0f", color_continuous_scale="Blues", aspect="auto",
                        labels={"x": "", "y": "", "color": "Mediana"},
                        title="Mediana diaria de tarjetas por corredor y día (estaciones y terminal)")
        st.plotly_chart(fig, width="stretch")
 # Día de menor y de mayor demanda en cada corredor, calculados con los datos filtrados
        resumen_dias = "; ".join(f"{c}: más bajo el {fila.idxmin()}, más alto el {fila.idxmax()}"
                                 for c, fila in calor.iterrows())
        st.caption(resumen_dias + ".")


# --------
# 6. Calidad de los datos (paso 5 del EDA, calculado en vivo desde el Excel en bruto)
# --------

with tab_calidad:
    st.subheader("Qué se encontró en los datos en bruto y qué se decidió")
    crudo_nombrado = renombrar_columnas(crudo) # el crudo con la columna sin nombre ya renombrada
    sin_nombre = sum(str(c).strip() == "" for c in crudo.columns)
    calidad = pd.DataFrame([
        ["Registros en la hoja DETALLE_TARJETAS_nuevo", f"{len(crudo):,}", "Punto de partida"],
        ["Columnas sin nombre", f"{sin_nombre}", "Renombrada a tipo_registro"],
        ["Columnas sistema y tipo de ubicación", "No vienen en la hoja",
         "Derivadas del corredor y del tipo de registro (validadas: 0 diferencias)"],
        ["Distribución masiva al municipio",
         f"{crudo_nombrado.loc[crudo_nombrado['tipo_registro'] == 'DISTRIBUCION_MUNICIPIO', 'total_tarjetas'].sum():,} tarjetas",
         "Excluida: no es demanda del público"],
        ["Columnas constantes (valor_tarifa_*)", f"{(crudo.nunique(dropna=True) <= 1).sum()}",
         "Eliminadas: solo identifican el perfil, no son precios"],
        ["Nombres de puntos distintos",
         f"{crudo['estacion_o_evento'].nunique()} → {df['estacion_o_evento'].nunique()}",
         "Variantes unificadas y formato uniforme (mayúsculas, tildes, prefijos)"],
        ["total_dinero", "Sin definición clara",
         "Excluida: no coincide con tarjetas × valor y tiene $0 en casi todas las paradas"],
        ["Eventos asignados a Trole Sur", "100 %", "Comparaciones por corredor sin eventos"],
        ["Días atípicos (1,5·IQR)", f"{df['atipico'].sum()}", "Se conservan y marcan; se usan medianas"],
    ], columns=["Aspecto", "Valor", "Decisión"])
    st.dataframe(calidad, hide_index=True, width="stretch")
    st.caption("Todo se calcula desde la hoja DETALLE_TARJETAS_nuevo de data/crudos/resumen_total_tarjetas.xlsx con src/limpieza.py.")


# --------
# 7. Decisiones
# --------

with tab_decisiones:
    st.subheader("Decisiones que apoya el análisis")
    st.markdown("""
- **Inventario por estación:** asignar el stock en proporción a la demanda. Seis estaciones (El Recreo,
  Labrador, Río Coca, Quitumbe, Playón de la Marín y Guamaní) reúnen el 72 % de las tarjetas;
  solo El Recreo, el 21 %.
- **Inventario por perfil:** en El Recreo y Quitumbe, alrededor de un 25 % de tarjetas Reducidas;
  en Playón de la Marín basta con un 13 %.
- **Eventos:** llevar lotes grandes (mediana de 105 tarjetas por jornada, el doble que una estación).
- **Días:** reponer antes del sábado en Labrador y reducir stock y personal los domingos en el resto.
- **Horario extendido:** evaluarlo antes de ampliarlo; se asocia con más entregas, pero no está probado que las cause.
""")
    st.subheader("Limitaciones")
    st.markdown("""
- `total_dinero` no tiene una definición clara y se excluyó: el análisis no incluye información monetaria.
- No hay datos por hora ni de las personas usuarias; siete meses no muestran estacionalidad anual.
- El significado de `horario_extendido` debe confirmarse con la fuente.
- Es un análisis descriptivo: muestra asociaciones, no causas.
""")
