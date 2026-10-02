"""
Funciones de carga y limpieza de los datos de entrega de tarjetas.

Este archivo reúne, en funciones reutilizables, las decisiones de limpieza que se
tomaron y justificaron paso a paso en el notebook `notebooks/01_EDA_tarjetas.ipynb`.
Así el notebook (análisis) y el dashboard (`dash_app.py`) usan EXACTAMENTE la misma
limpieza, y el proceso completo se puede reproducir desde los datos en bruto.
"""

from pathlib import Path # manejo de rutas de archivos que funciona en Windows, Mac y Linux

import numpy as np # cálculos numéricos
import pandas as pd # manejo de tablas (DataFrames)

# ----
# Constantes del proyecto
# ----

# Carpeta raíz del proyecto: este archivo está en src/, así que la raíz es la carpeta padre
RAIZ = Path(__file__).resolve().parent.parent

# Rutas de los datos en bruto (tal como se recibieron, sin modificar)
RUTA_EXCEL = RAIZ / "data" / "crudos" / "resumen_total_tarjetas.xlsx"
RUTA_ESTACIONES = RAIZ / "data" / "crudos" / "estaciones_transporte_quito.csv"

# Hoja del Excel con el detalle diario que se usa en el proyecto (indicada por la fuente)
HOJA_DETALLE = "DETALLE_TARJETAS_nuevo"

# Perfil de tarjeta de cada columna de cantidad, CONFIRMADO por la fuente de los datos
PERFILES = {
    "cantidad_tu": "tarjetas_universal", # tu = T. Universal
    "cantidad_tr": "tarjetas_reducida", # tr = Tarjeta Reducida
    "cantidad_tp": "tarjetas_preferencial", # tp = Tarjeta Preferencial
}

# Sistema al que pertenece cada corredor (la hoja no trae esta columna)
SISTEMA_POR_CORREDOR = {
    "Trole Sur": "TROLEBUS", "Trole Norte": "TROLEBUS",
    "Ecovía Norte": "ECOVIA", "Sur Oriental": "ECOVIA",
}

# Tipo de ubicación según el tipo de registro (la hoja no trae esta columna).
# Un registro NORMAL es una estación, salvo Quitumbe, que es un terminal terrestre.
TIPO_POR_REGISTRO = {
    "NORMAL": "ESTACION", "PARADA": "PARADA", "EVENTO": "EVENTO",
    "PUNTO_VENTA": "PUNTO_VENTA", "DISTRIBUCION_MUNICIPIO": "ESTACION",
}
TERMINALES = {"Quitumbe"}

# Variables que no se usan en el análisis porque su definición no está clara.
# `total_dinero` no coincide con tarjetas × valor, tiene $0 en casi todas las paradas
# y la fuente no ha podido precisar qué mide: usarla llevaría a conclusiones sin sustento.
VARIABLES_SIN_DEFINICION = ["total_dinero"]

# Orden lógico de los días de la semana (lunes = 0 en pandas)
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Variantes de nombres detectadas en el EDA → nombre estándar.
# Son el mismo punto de entrega escrito de distintas formas o con errores de codificación.
ESTANDAR_NOMBRES = {
    "EJIDO": "EL EJIDO",
    "Capulí": "CAPULÍ",
    "CONCEJO PROVINCIAL": "CONSEJO PROVINCIAL",
    "PMO- UNIVERSIDAD CENTRAL": "PMO UNIVERSIDAD CENTRAL",
    "PMO-UNIVERSIDAD CENTRAL": "PMO UNIVERSIDAD CENTRAL",
    "PMO-LA UNIVERSIDAD CENTRAL": "PMO UNIVERSIDAD CENTRAL",
    "PMO UCE": "PMO UNIVERSIDAD CENTRAL",
    "UCE": "UNIVERSIDAD CENTRAL",
    "Universidad Central": "UNIVERSIDAD CENTRAL",
    "PMO-NACIONES UNIDAS": "PMO NACIONES UNIDAS",
    "PMO-LA CAROLINA": "PMO LA CAROLINA",
    "PMO-CONOCOTO": "PMO CONOCOTO",
    "PMO-COTOCOLLAO": "PMO COTOCOLLAO",
    "PRONACA(MAÑANA)": "PRONACA", # mismo evento, turno de la mañana
    "PRONACA(TARDE)": "PRONACA", # mismo evento, turno de la tarde
    "MERCADO I¥AQUITO": "MERCADO IÑAQUITO", # error de codificación: ¥ en lugar de Ñ
    "PMO BASÞLICA": "PMO BASÍLICA", # error de codificación: Þ en lugar de Í
}

# Formato uniforme de los nombres (se aplica DESPUÉS de unificar las variantes)
# Conectores que siempre van en minúscula dentro de un nombre (salvo si son la primera palabra)
CONECTORES = {"de", "del", "y"}
# Artículos: en minúscula solo después de "de" ("Casa de la Cultura"); si no, son parte
# del nombre propio y van con mayúscula ("Boulevard La Carolina", "Mercado Las Cuadras")
ARTICULOS = {"la", "las", "los", "el"}
# Siglas que se mantienen en mayúsculas
SIGLAS = {"PMO", "EPN", "IGM", "CEAM", "ARCA", "PJ", "PRONACA"}
# Palabras que el archivo escribe sin tilde o con errores, ya pasadas a formato título
CORRECCIONES_PALABRAS = {
    "Administracion": "Administración", "Alcaldia": "Alcaldía", "Calderon": "Calderón",
    "Carcelen": "Carcelén", "Cumbaya": "Cumbayá", "Gerontologico": "Gerontológico",
    "Historico": "Histórico", "Chillogalo": "Chillogallo", "Conquito": "ConQuito",
}

# Nombre oficial en el archivo de estaciones → nombre usado en el Excel de tarjetas.
# Sin esta tabla no se pueden unir las coordenadas con las entregas.
MAPA_COORDENADAS = {
    "Terminal Terrestre Quitumbe": "Quitumbe",
    "Estacion Multimodal El Labrador": "Labrador",
    "Terminal Sur – El Recreo": "El Recreo",
    "Terminal Interparroquial Rio Coca": "Río Coca",
    "Terminal Microregional Playon de la Marin": "Playón de la Marín",
    "Terminal Sur Ecovia – Guamani": "Guamaní",
    "Parada Espana (Ecovia)": "España",
    "Parada Jipijapa (Metro / Ecovia)": "Jipijapa",
    "Parada Chimbacalle (Trolebus)": "Chimbacalle",
    "Parada Colon (Trolebus / Ecovia)": "Colón",
    "Parada Estadio (Ecovia)": "Estadio",
    "Parada La Colina (Ecovia)": "La Colina",
    "Parada Plaza Chica (Trolebus)": "Plaza Chica",
    "Parada Plaza Grande (Trolebus)": "Plaza Grande",
}


# ----
# Funciones
# ----

def cargar_crudo(ruta=RUTA_EXCEL):
    """Lee la hoja de detalle del Excel en bruto, sin ninguna modificación."""
    return pd.read_excel(ruta, sheet_name=HOJA_DETALLE)


def renombrar_columnas(df):
    """Da nombres claros a las columnas.
    - La columna del tipo de registro llega SIN NOMBRE (su encabezado son espacios en blanco).
    - Las cantidades se renombran con el perfil de tarjeta confirmado por la fuente.
    """
    df = df.copy()
    sin_nombre = [c for c in df.columns if str(c).strip() == ""] # encabezados vacíos
    nuevos = {sin_nombre[0]: "tipo_registro"} if sin_nombre else {}
    nuevos.update(PERFILES) # cantidad_tu → tarjetas_universal, ...
    return df.rename(columns=nuevos)


def eliminar_columnas_sin_informacion(df):
    """Elimina columnas constantes (como `valor_tarifa_*`) y las variables sin definición clara."""
    constantes = [c for c in df.columns if df[c].nunique(dropna=True) <= 1] # 0 o 1 valor distinto
    return df.drop(columns=constantes + VARIABLES_SIN_DEFINICION)


def derivar_sistema_y_tipo(df):
    """Crea `sistema` (desde el corredor) y `tipo_ubicacion` (desde el tipo de registro)."""
    df = df.copy()
    df["sistema"] = df["corredor"].map(SISTEMA_POR_CORREDOR)
    df["tipo_ubicacion"] = df["tipo_registro"].map(TIPO_POR_REGISTRO)
    df.loc[df["estacion_o_evento"].isin(TERMINALES) & (df["tipo_registro"] == "NORMAL"),
           "tipo_ubicacion"] = "TERMINAL" # Quitumbe es un terminal
    return df


def ajustar_tipos(df):
    """Convierte las variables de texto con pocos valores a `category` y crea variables de tiempo."""
    df = df.copy()
    for col in ["corredor", "sistema", "tipo_ubicacion", "tipo_registro"]:
        df[col] = df[col].astype("category") # ocupa menos memoria y agrupa mejor
    df["fecha"] = pd.to_datetime(df["fecha"]) # asegura el tipo fecha
    df["mes"] = df["fecha"].dt.to_period("M").astype(str) # "2026-03", "2026-04", ...
    df["semana"] = df["fecha"].dt.to_period("W").dt.start_time # lunes de cada semana
    df["dia_semana"] = pd.Categorical( # día con orden Lun → Dom
        df["fecha"].dt.dayofweek.map(dict(enumerate(DIAS))),
        categories=DIAS, ordered=True)
    return df


def excluir_distribucion_municipio(df):
    """Quita la entrega masiva al municipio: no es demanda del público."""
    df = df[df["tipo_registro"] != "DISTRIBUCION_MUNICIPIO"].copy()
    df["tipo_registro"] = df["tipo_registro"].cat.remove_unused_categories() # limpia la categoría vacía
    return df


def formatear_nombre(nombre):
    """Da un formato uniforme al nombre de un punto de entrega.
    Ejemplos:  "CENTRO HISTORICO" → "Centro Histórico"
               "Estación Labrador" → "Labrador"      (se quita el prefijo)
               "Colón N/S"         → "Colón"         (se quita el sentido Norte/Sur)
               "PMO LA CAROLINA"   → "PMO La Carolina" (las siglas se conservan)
    """
    nombre = nombre.strip() # quita espacios al inicio y al final
    nombre = nombre.removeprefix("Estación ") # el tipo ya está en tipo_ubicacion
    nombre = nombre.removesuffix(" N/S") # N/S = ambos sentidos de la parada
    nombre = nombre.replace(" -", " - ").replace("-", " - ") # separa los guiones con espacios
    palabras = []
    for i, palabra in enumerate(nombre.split()): # split() también elimina espacios dobles
        if palabra.upper() in SIGLAS: # sigla → mayúsculas
            palabras.append(palabra.upper())
        elif i > 0 and palabra.lower() in CONECTORES: # "de", "del", "y" → minúscula
            palabras.append(palabra.lower())
        elif i > 0 and palabra.lower() in ARTICULOS and palabras[-1] == "de": # "de la" → minúscula
            palabras.append(palabra.lower())
        else: # resto → Primera letra en mayúscula
            palabra = palabra.capitalize()
            palabras.append(CORRECCIONES_PALABRAS.get(palabra, palabra)) # agrega tildes faltantes
    return " ".join(palabras)


def estandarizar_nombres(df):
    """Unifica las variantes de un mismo punto y luego da formato uniforme a todos los nombres."""
    df = df.copy()
    df["estacion_o_evento"] = (df["estacion_o_evento"]
                               .replace(ESTANDAR_NOMBRES) # 1) une variantes del mismo punto
                               .map(formatear_nombre)) # 2) mismo formato para todos
    return df


def marcar_calidad(df):
    """Agrega la columna `atipico`, sin borrar ninguna fila.
    `atipico` es True si las tarjetas del registro superan Q3 + 1,5·IQR
    dentro de su propio tipo de ubicación.
    """
    df = df.copy()

    def _atipico(serie): # regla del rango intercuartílico
        q1, q3 = serie.quantile([0.25, 0.75])
        return serie > q3 + 1.5 * (q3 - q1)

    df["atipico"] = (df.groupby("tipo_ubicacion", observed=True)["total_tarjetas"]
                       .transform(_atipico)) # se calcula dentro de cada tipo
    return df


def preparar_datos(ruta=RUTA_EXCEL):
    """Aplica toda la limpieza, en orden, desde el Excel en bruto."""
    df = cargar_crudo(ruta)
    df = renombrar_columnas(df)
    df = eliminar_columnas_sin_informacion(df)
    df = derivar_sistema_y_tipo(df)
    df = ajustar_tipos(df)
    df = excluir_distribucion_municipio(df)
    df = estandarizar_nombres(df)
    df = marcar_calidad(df)
    return df.reset_index(drop=True)


def cargar_coordenadas(ruta=RUTA_ESTACIONES):
    """Lee las coordenadas en bruto y agrega el nombre con el que aparece cada punto en el Excel."""
    coords = pd.read_csv(ruta)
    coords["estacion_o_evento"] = coords["Nombre"].map(MAPA_COORDENADAS) # une ambos catálogos
    return coords.rename(columns={"Nombre": "nombre_oficial", "Latitud": "lat", "Longitud": "lon"})
