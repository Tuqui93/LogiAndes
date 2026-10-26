"""
LogiAndes S.A. · Dashboard de Business Intelligence (Navegación Fluida)

Ejecutar:  streamlit run LogiAndes.py
Datos:     cualquier CSV en la misma carpeta que este script,
           o súbelo desde la barra lateral (⚙️ Origen de datos).
"""

import hashlib
import inspect
import io
import re
import unicodedata
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="LogiAndes S.A. · BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _kw_ancho(fn):
    """`width="stretch"` en Streamlit reciente; `use_container_width` en versiones antiguas."""
    try:
        p = inspect.signature(fn).parameters.get("width")
        if p is not None and p.default is not None:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


AN_PLOT = _kw_ancho(st.plotly_chart)
AN_DF = _kw_ancho(st.dataframe)
AN_BTN = _kw_ancho(st.button)


# ==========================================
# 2. ESTILOS Y NAVEGACIÓN FLUIDA (CSS)
# ==========================================
def inyectar_estilos(tema_nav: str):
    """Inyecta el CSS del dashboard y de la barra de navegación fluida inspirada en los 3 estilos de referencia."""
    temas = {
        "Oscuro Neón": {
            "bar_bg": "linear-gradient(145deg, #18181b 0%, #111115 100%)",
            "bar_border": "1px solid rgba(255, 255, 255, 0.08)",
            "bar_shadow": "0 14px 32px rgba(0, 0, 0, 0.28), 0 4px 12px rgba(0, 0, 0, 0.18)",
            "tab_color": "#a1a1aa",
            "tab_hover_bg": "rgba(255, 255, 255, 0.05)",
            "tab_hover_color": "#f4f4f5",
            "active_bg": "radial-gradient(circle at 50% 0%, rgba(225, 29, 72, 0.28) 0%, rgba(225, 29, 72, 0.06) 75%)",
            "active_color": "#ffffff",
            "active_shadow": "inset 0 2.5px 0 0 #f43f5e, 0 0 18px rgba(244, 63, 94, 0.35)",
            "dot_color": "#f43f5e",
        },
        "Cápsula Clara": {
            "bar_bg": "#ffffff",
            "bar_border": "1px solid rgba(226, 232, 240, 0.95)",
            "bar_shadow": "0 12px 28px rgba(15, 23, 42, 0.08), 0 2px 6px rgba(15, 23, 42, 0.04)",
            "tab_color": "#64748b",
            "tab_hover_bg": "#f1f5f9",
            "tab_hover_color": "#0f172a",
            "active_bg": "linear-gradient(135deg, #d90429 0%, #ef233c 100%)",
            "active_color": "#ffffff",
            "active_shadow": "0 6px 16px rgba(217, 4, 41, 0.32)",
            "dot_color": "#ffffff",
        },
        "Rojo Vibrante": {
            "bar_bg": "linear-gradient(135deg, #c1121f 0%, #dc2626 100%)",
            "bar_border": "1px solid rgba(255, 255, 255, 0.2)",
            "bar_shadow": "0 14px 30px rgba(220, 38, 38, 0.30)",
            "tab_color": "rgba(255, 255, 255, 0.80)",
            "tab_hover_bg": "rgba(255, 255, 255, 0.12)",
            "tab_hover_color": "#ffffff",
            "active_bg": "rgba(255, 255, 255, 0.24)",
            "active_color": "#ffffff",
            "active_shadow": "0 4px 14px rgba(0, 0, 0, 0.16), inset 0 1px 1px rgba(255, 255, 255, 0.35)",
            "dot_color": "#ffffff",
        },
    }
    t = temas.get(tema_nav, temas["Oscuro Neón"])

    st.markdown(
        f"""
        <style>
            .block-container {{
                padding-top: 1.4rem;
                padding-bottom: 2.5rem;
                max-width: 1440px;
            }}

            /* Encabezado superior */
            .top-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 0.75rem;
                margin-bottom: 0.6rem;
            }}
            .brand-box {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}
            .brand-badge {{
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                color: white;
                font-weight: 800;
                font-size: 1.25rem;
                width: 42px;
                height: 42px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.28);
            }}
            .main-title {{
                font-size: 1.65rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin: 0;
                line-height: 1.15;
            }}
            .sub-title {{
                font-size: 0.86rem;
                opacity: 0.72;
                margin: 0;
            }}
            .status-pill {{
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.25);
                padding: 0.35rem 0.85rem;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 600;
            }}

            /* =====================================================
               BARRA DE NAVEGACIÓN FLUIDA (PILL NAVIGATION TABS)
               ===================================================== */
            div[data-testid="stTabs"] > div[role="tablist"] {{
                background: {t["bar_bg"]} !important;
                border: {t["bar_border"]} !important;
                box-shadow: {t["bar_shadow"]} !important;
                border-radius: 999px !important;
                padding: 0.42rem 0.55rem !important;
                gap: 0.35rem !important;
                width: fit-content !important;
                max-width: 100% !important;
                margin: 0.35rem auto 1.2rem auto !important;
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                overflow-x: auto !important;
            }}

            /* Ocultar línea inferior nativa de Streamlit */
            div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
            div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{
                display: none !important;
            }}

            /* Botón individual de cada pestaña */
            div[data-testid="stTabs"] button[role="tab"] {{
                border-radius: 999px !important;
                padding: 0.5rem 1.35rem !important;
                min-width: 112px !important;
                height: auto !important;
                border: none !important;
                background: transparent !important;
                color: {t["tab_color"]} !important;
                transition: all 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
                position: relative !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
            }}

            /* Texto e icono apilados dentro del botón */
            div[data-testid="stTabs"] button[role="tab"] p {{
                margin: 0 !important;
                text-align: center !important;
                line-height: 1.28 !important;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                letter-spacing: 0.01em !important;
                color: inherit !important;
                transition: transform 0.25s ease !important;
            }}

            /* Efecto Hover */
            div[data-testid="stTabs"] button[role="tab"]:hover {{
                background: {t["tab_hover_bg"]} !important;
                color: {t["tab_hover_color"]} !important;
                transform: translateY(-1px) !important;
            }}

            /* Pestaña Activa */
            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
                background: {t["active_bg"]} !important;
                color: {t["active_color"]} !important;
                box-shadow: {t["active_shadow"]} !important;
                transform: scale(1.03) !important;
            }}

            /* Punto luminoso indicador bajo la pestaña activa */
            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after {{
                content: "";
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: {t["dot_color"]};
                position: absolute;
                bottom: 5px;
                left: 50%;
                transform: translateX(-50%);
                box-shadow: 0 0 6px {t["dot_color"]};
            }}

            /* Animación fluida al cambiar de pestaña */
            @keyframes fadeSlideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(8px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            div[data-testid="stTabs"] div[role="tabpanel"] {{
                animation: fadeSlideUp 0.28s cubic-bezier(0.22, 1, 0.36, 1);
            }}

            /* Mejora visual de tarjetas de métricas */
            div[data-testid="stMetric"] {{
                padding: 0.2rem 0.1rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# 3. MODELO DE DATOS: LECTURA, ALIAS Y LIMPIEZA
# ==========================================
CAMPOS_CORE = ["Provincia", "Canal", "Venta_Neta", "Margen_Bruto", "Hubo_Reclamo", "Entrega_A_Tiempo"]
CAMPOS_OPCIONALES = ["Fecha", "Ciudad", "Linea_Servicio", "Tiempo_Entrega", "Meta_Venta"]
CAMPOS = CAMPOS_CORE + CAMPOS_OPCIONALES

ALIAS = {
    "Fecha": ["fecha", "fecha_pedido", "fecha_de_pedido", "fecha_factura", "date", "order_date"],
    "Provincia": ["provincia", "province"],
    "Ciudad": ["ciudad", "city"],
    "Canal": ["canal", "canal_venta", "canal_de_venta", "channel"],
    "Linea_Servicio": ["linea_servicio", "linea_de_servicio", "servicio", "tipo_servicio", "linea"],
    "Venta_Neta": ["venta_neta", "ventas_netas", "ventaneta", "venta_neta_usd", "ventas_netas_usd", "net_sales"],
    "Margen_Bruto": ["margen_bruto", "margenbruto", "margen", "utilidad_bruta", "gross_margin"],
    "Hubo_Reclamo": ["hubo_reclamo", "reclamo", "reclamos", "tuvo_reclamo", "con_reclamo", "claim"],
    "Entrega_A_Tiempo": ["entrega_a_tiempo", "entrega_tiempo", "a_tiempo", "entregado_a_tiempo", "on_time", "otd"],
    "Tiempo_Entrega": [
        "tiempo_entrega", "tiempo_de_entrega", "dias_entrega", "dias_de_entrega",
        "horas_entrega", "lead_time", "delivery_time",
    ],
    "Meta_Venta": ["meta_venta", "meta_ventas", "meta", "meta_mensual", "meta_comercial", "target"],
}

SENSIBLES = ("vendedor", "cliente", "nombre", "cedula", "telefono", "correo", "email", "direccion")


def _limpiar(txt) -> str:
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def _leer(contenido: bytes) -> pd.DataFrame:
    """Lee un CSV probando codificaciones y separadores habituales (Excel en español usa ';')."""
    ultimo = None
    for enc in ("utf-8-sig", "latin-1"):
        for sep in (None, ";", ",", "\t"):
            try:
                df = pd.read_csv(io.BytesIO(contenido), sep=sep, engine="python", encoding=enc)
            except Exception as e:  # noqa: BLE001
                ultimo = e
                continue
            if df.shape[1] > 1:
                return df
    raise ValueError(f"No se pudo leer el CSV. Revisa separador y codificación. Detalle: {ultimo}")


@st.cache_data(show_spinner="Leyendo datos…")
def cargar_csv(contenido: bytes) -> pd.DataFrame:
    df = _leer(contenido)
    df.columns = [str(c).strip() for c in df.columns]
    usados, renombrar = set(), {}
    for col in df.columns:
        limpia = _limpiar(col)
        for estandar, alias in ALIAS.items():
            if estandar in usados or limpia not in alias:
                continue
            if col != estandar and estandar in df.columns:
                continue
            renombrar[col] = estandar
            usados.add(estandar)
            break
    return df.rename(columns=renombrar)


def a_numero(s: pd.Series) -> pd.Series:
    """'$1,234.50', '1.234,50' o 'US$ 90' → número."""
    if pd.api.types.is_numeric_dtype(s):
        return s
    t = s.astype(str).str.replace(r"[^\d,.\-]", "", regex=True)
    if t.str.contains(r",\d{1,2}$").mean() > 0.5:
        t = t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        t = t.str.replace(",", "", regex=False)
    return pd.to_numeric(t, errors="coerce")


def a_binario(s: pd.Series) -> pd.Series:
    """Sí/No, True/False, 1/0 → 1/0."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype(int)
    if pd.api.types.is_numeric_dtype(s):
        return (pd.to_numeric(s, errors="coerce").fillna(0) > 0).astype(int)
    t = s.astype(str).str.strip().str.lower()
    positivos = [
        "si", "sí", "s", "1", "true", "yes", "y", "verdadero", "a tiempo",
        "entregado a tiempo", "on time", "ok", "cumple", "con reclamo",
    ]
    return t.isin(positivos).astype(int)


def a_fecha(s: pd.Series) -> pd.Series:
    """Detecta dd/mm/aaaa (formato local) para no confundir día y mes."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    t = s.astype(str).str.strip()
    dayfirst = t.str.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}").mean() > 0.5
    return pd.to_datetime(t, errors="coerce", dayfirst=dayfirst)


PISTAS = {
    "Fecha": {"si": {"fecha": 3, "date": 3, "pedido": 1, "factura": 1}, "no": [], "tipo": "fecha"},
    "Provincia": {"si": {"provincia": 3, "province": 3, "prov": 1}, "no": ["meta", "id"], "tipo": "texto"},
    "Ciudad": {"si": {"ciudad": 3, "city": 3, "canton": 3}, "no": ["id"], "tipo": "texto"},
    "Canal": {"si": {"canal": 3, "channel": 3, "medio": 1}, "no": ["id"], "tipo": "texto"},
    "Linea_Servicio": {"si": {"servicio": 3, "linea": 3, "service": 2, "producto": 1}, "no": ["id"], "tipo": "texto"},
    "Venta_Neta": {
        "si": {"neta": 4, "neto": 4, "net": 3, "venta": 2, "ventas": 2, "ingreso": 2, "monto": 1, "factur": 1, "total": 1},
        "no": ["bruta", "bruto", "meta", "margen", "costo", "descuento", "reclamo", "tiempo", "id", "impuesto"],
        "tipo": "numero+",
    },
    "Margen_Bruto": {
        "si": {"margen": 4, "utilidad": 3, "ganancia": 3, "profit": 3, "bruto": 1, "bruta": 1},
        "no": ["meta", "id"],
        "tipo": "numero+",
    },
    "Hubo_Reclamo": {
        "si": {"reclam": 4, "queja": 3, "claim": 3},
        "no": ["tipo", "motivo", "tiempo", "costo", "monto", "id"],
        "tipo": "binario",
    },
    "Entrega_A_Tiempo": {
        "si": {
            "a_tiempo": 4, "puntual": 4, "otd": 4, "on_time": 4, "ontime": 4, "sla": 3,
            "cumpl": 2, "retras": 2, "atras": 2, "estado": 1, "tiempo": 1, "entrega": 1,
        },
        "no": ["id", "reclam"],
        "tipo": "binario",
    },
    "Tiempo_Entrega": {
        "si": {
            "tiempo_entrega": 4, "tiempo_de_entrega": 4, "lead_time": 4, "dias_entrega": 4,
            "horas_entrega": 4, "demora": 3, "transporte": 2, "tiempo": 2, "dias": 2, "horas": 2, "duracion": 2,
        },
        "no": ["a_tiempo", "meta", "id", "reclam"],
        "tipo": "numero+",
    },
    "Meta_Venta": {
        "si": {"meta": 4, "target": 4, "objetivo": 3, "presupuesto": 3},
        "no": ["id", "cumpl"],
        "tipo": "numero",
    },
}


def _tipo_ok(s: pd.Series, tipo: str) -> bool:
    s = s.dropna()
    if s.empty:
        return False
    if len(s) > 2000:
        s = s.sample(2000, random_state=0)
    n = s.nunique()
    if tipo == "binario":
        return n <= 3
    if tipo == "fecha":
        return (not pd.api.types.is_numeric_dtype(s)) and a_fecha(s).notna().mean() >= 0.8
    num = a_numero(s).notna().mean() >= 0.8
    if tipo == "numero":
        return num
    if tipo == "numero+":
        return num and n > 3
    return (not num) and n <= 500


@st.cache_data(show_spinner=False)
def sugerir_mapeo(_df: pd.DataFrame, huella: str) -> dict:
    """Propone qué columna del CSV corresponde a cada campo, mirando nombre y contenido."""
    candidatos = []
    for campo in CAMPOS:
        if campo in _df.columns:
            continue
        regla = PISTAS[campo]
        for col in _df.columns:
            if col in CAMPOS:
                continue
            nombre = _limpiar(col)
            partes = set(nombre.split("_"))

            def hit(t, nombre=nombre, partes=partes):
                return (t in partes) if len(t) <= 3 else (t in nombre)

            if any(hit(t) for t in regla["no"]):
                continue
            puntos = sum(p for t, p in regla["si"].items() if hit(t))
            if puntos > 0 and _tipo_ok(_df[col], regla["tipo"]):
                candidatos.append((puntos, campo, col))
    sug, usadas = {}, set()
    for puntos, campo, col in sorted(candidatos, reverse=True):
        if campo not in sug and col not in usadas:
            sug[campo] = col
            usadas.add(col)
    return sug


@st.cache_data(show_spinner=False)
def preparar_datos(_df: pd.DataFrame, huella: str, mapeo: tuple, margen_es_pct: bool) -> pd.DataFrame:
    """Aplica el mapeo manual, convierte tipos y crea AñoMes."""
    x = _df.copy()
    for campo, origen in dict(mapeo).items():
        x[campo] = x[origen]
    for c in ("Provincia", "Ciudad", "Canal", "Linea_Servicio"):
        if c in x:
            x[c] = x[c].fillna("Sin dato").astype(str).str.strip()
    for c in ("Venta_Neta", "Margen_Bruto", "Tiempo_Entrega", "Meta_Venta"):
        if c in x:
            x[c] = a_numero(x[c])
    for c in ("Hubo_Reclamo", "Entrega_A_Tiempo"):
        if c in x:
            x[c] = a_binario(x[c])
    if margen_es_pct and "Margen_Bruto" in x and "Venta_Neta" in x:
        x["Margen_Bruto"] = x["Venta_Neta"] * x["Margen_Bruto"] / 100
    if "Fecha" in x:
        x["Fecha"] = a_fecha(x["Fecha"])
        x["AñoMes"] = x["Fecha"].dt.strftime("%Y-%m")
    return x


# ==========================================
# 4. BARRA LATERAL: ORIGEN DE DATOS Y APARIENCIA
# ==========================================
CARPETA_DEFECTO = Path(__file__).resolve().parent

st.sidebar.title("🚚 LogiAndes S.A.")
st.sidebar.caption("Módulo de Inteligencia de Negocios")

with st.sidebar.expander("🎨 Estilo de navegación", expanded=True):
    tema_nav = st.radio(
        "Diseño de la barra superior",
        ["Oscuro Neón", "Cápsula Clara", "Rojo Vibrante"],
        index=0,
        help="Alterna entre los 3 estilos de barra de navegación fluida tipo cápsula.",
    )

inyectar_estilos(tema_nav)

contenido, nombre_archivo = None, ""
with st.sidebar.expander("⚙️ Origen de datos", expanded=True):
    carpeta = Path(st.text_input("Carpeta de datos", value=str(CARPETA_DEFECTO))).expanduser()
    subido = st.file_uploader("…o sube un CSV", type=["csv"], key="up_side")
    if subido is not None:
        contenido, nombre_archivo = subido.getvalue(), subido.name
    else:
        archivos = sorted(p.name for p in carpeta.glob("*.csv")) if carpeta.is_dir() else []
        if archivos:
            nombre_archivo = st.selectbox("Archivo", archivos)
            contenido = (carpeta / nombre_archivo).read_bytes()

if contenido is None:
    st.markdown(
        """
        <div class='top-header'>
            <div class='brand-box'>
                <div class='brand-badge'>LA</div>
                <div>
                    <div class='main-title'>LogiAndes S.A. · Panel de Desempeño</div>
                    <div class='sub-title'>Inteligencia de Negocios y Operaciones Logísticas</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.warning(f"No encontré archivos CSV en `{carpeta}`. Sube uno aquí para empezar:")
    subido_main = st.file_uploader("Sube tu CSV", type=["csv"], key="up_main")
    if subido_main is None:
        st.stop()
    contenido, nombre_archivo = subido_main.getvalue(), subido_main.name

try:
    df_raw = cargar_csv(contenido)
except ValueError as e:
    st.error(str(e))
    st.stop()

if df_raw.empty:
    st.warning("El archivo seleccionado está vacío.")
    st.stop()

huella = hashlib.md5(contenido).hexdigest()
sug = sugerir_mapeo(df_raw, huella)

# Inicializar estado del mapeo en session_state para que esté disponible antes de renderizar la pestaña Gobernanza
mapeo = {}
for campo in CAMPOS:
    clave_col = f"map_{huella[:8]}_{campo}"
    defecto = campo if campo in df_raw.columns else sug.get(campo, "(ninguna)")
    elegido = st.session_state.get(clave_col, defecto)
    if elegido not in ("(ninguna)", campo) and elegido in df_raw.columns:
        mapeo[campo] = elegido

disponibles_actual = set(df_raw.columns) | set(mapeo)
faltan_core = [c for c in CAMPOS_CORE if c not in disponibles_actual]

# Detectar valores por defecto de Margen y Meta
sugiere_pct_def = False
if "Margen_Bruto" in disponibles_actual and "Venta_Neta" in disponibles_actual:
    try:
        m_s = a_numero(df_raw[mapeo.get("Margen_Bruto", "Margen_Bruto")]).dropna()
        v_s = a_numero(df_raw[mapeo.get("Venta_Neta", "Venta_Neta")]).dropna()
        sugiere_pct_def = len(m_s) > 0 and len(v_s) > 0 and m_s.between(0, 100).all() and v_s.median() > 100
    except Exception:  # noqa: BLE001
        pass

clave_margen = f"margen_{huella[:8]}"
margen_es_pct = st.session_state.get(
    clave_margen,
    "Porcentaje (%)" if sugiere_pct_def else "Monto (US$)",
) == "Porcentaje (%)"

clave_meta = f"meta_{huella[:8]}"
META_REPETIDA = st.session_state.get(
    clave_meta,
    "Repetida en cada pedido (provincia y mes)",
).startswith("Repetida")

df_base = preparar_datos(df_raw, huella, tuple(sorted(mapeo.items())), margen_es_pct)

# ==========================================
# 5. FILTROS GLOBALES COMPACTOS Y CABECERA
# ==========================================
CLAVES_FILTROS = ["f_preset", "f_rango", "f_prov", "f_canal", "f_ciudad", "f_linea"]


def reiniciar_filtros():
    for k in CLAVES_FILTROS:
        st.session_state.pop(k, None)


def selector(label: str, opciones: list, clave: str) -> list:
    """Botones tipo 'pill' si hay pocas opciones; lista desplegable si hay muchas."""
    st.session_state[clave] = [v for v in st.session_state.get(clave, []) if v in opciones]
    if hasattr(st, "pills") and len(opciones) <= 6:
        return list(st.pills(label, opciones, selection_mode="multi", key=clave) or [])
    return st.multiselect(label, opciones, key=clave, placeholder="Todas")


def aplicar(df: pd.DataFrame, col: str, seleccion: list) -> pd.DataFrame:
    return df[df[col].isin(seleccion)] if (seleccion and col in df.columns) else df


df_filtrado = df_base.copy()
resumen_filtros = []

# Cabecera ejecutiva limpia
st.markdown(
    f"""
    <div class='top-header'>
        <div class='brand-box'>
            <div class='brand-badge'>LA</div>
            <div>
                <div class='main-title'>LogiAndes S.A. · Panel de Desempeño</div>
                <div class='sub-title'>Fuente activa: <b>{nombre_archivo}</b></div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if faltan_core:
    st.warning(
        "⚠️ Faltan columnas principales por asignar: **"
        + ", ".join(faltan_core)
        + "**. Ve a la pestaña **⚙️ Gobernanza** en la barra de navegación para mapearlas."
    )

# Contenedor de filtros globales
with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.25, 2.1, 1.65, 0.55], vertical_alignment="top")

    with f1:
        if "AñoMes" in df_filtrado.columns and df_filtrado["Fecha"].notna().any():
            f_min, f_max = df_filtrado["Fecha"].min().date(), df_filtrado["Fecha"].max().date()
            meses = sorted(df_filtrado["AñoMes"].dropna().unique())
            opciones_periodo = (
                ["Todo el periodo", "Últimos 30 días", "Últimos 90 días"]
                + [f"Mes {m}" for m in meses]
                + ["Personalizado"]
            )
            preset = st.selectbox("📅 Periodo", opciones_periodo, key="f_preset")
            if preset == "Últimos 30 días":
                f_ini, f_fin = max(f_min, f_max - timedelta(days=29)), f_max
            elif preset == "Últimos 90 días":
                f_ini, f_fin = max(f_min, f_max - timedelta(days=89)), f_max
            elif preset.startswith("Mes "):
                mes = preset[4:]
                f_ini = df_filtrado.loc[df_filtrado["AñoMes"] == mes, "Fecha"].min().date()
                f_fin = df_filtrado.loc[df_filtrado["AñoMes"] == mes, "Fecha"].max().date()
            elif preset == "Personalizado":
                rango = st.date_input("Rango", value=(f_min, f_max), min_value=f_min, max_value=f_max, key="f_rango")
                f_ini, f_fin = rango if isinstance(rango, (tuple, list)) and len(rango) == 2 else (f_min, f_max)
            else:
                f_ini, f_fin = f_min, f_max
            fechas = df_filtrado["Fecha"].dt.date
            df_filtrado = df_filtrado[(fechas >= f_ini) & (fechas <= f_fin)]
            if preset != "Todo el periodo":
                resumen_filtros.append(f"Periodo: {f_ini:%d/%m/%Y} → {f_fin:%d/%m/%Y}")
        else:
            st.caption("📅 Sin columna de fecha disponible.")

    with f2:
        if "Provincia" in df_filtrado.columns:
            sel_prov = selector("📍 Provincia", sorted(df_filtrado["Provincia"].dropna().unique()), "f_prov")
            df_filtrado = aplicar(df_filtrado, "Provincia", sel_prov)
            if sel_prov:
                resumen_filtros.append("Provincia: " + ", ".join(sel_prov))

    with f3:
        if "Canal" in df_filtrado.columns:
            sel_canal = selector("🛒 Canal", sorted(df_filtrado["Canal"].dropna().unique()), "f_canal")
            df_filtrado = aplicar(df_filtrado, "Canal", sel_canal)
            if sel_canal:
                resumen_filtros.append("Canal: " + ", ".join(sel_canal))

    with f4:
        st.write("")
        st.button("↺ Limpiar", on_click=reiniciar_filtros, **AN_BTN)

    if "Ciudad" in df_filtrado.columns or "Linea_Servicio" in df_filtrado.columns:
        with st.expander("➕ Filtros adicionales (Ciudad y Línea de servicio)"):
            g1, g2 = st.columns(2)
            with g1:
                if "Ciudad" in df_filtrado.columns:
                    sel_ciudad = st.multiselect(
                        "Ciudad",
                        sorted(df_filtrado["Ciudad"].dropna().unique()),
                        key="f_ciudad",
                        placeholder="Todas",
                    )
                    df_filtrado = aplicar(df_filtrado, "Ciudad", sel_ciudad)
                    if sel_ciudad:
                        resumen_filtros.append("Ciudad: " + ", ".join(sel_ciudad))
            with g2:
                if "Linea_Servicio" in df_filtrado.columns:
                    sel_linea = st.multiselect(
                        "Línea de servicio",
                        sorted(df_filtrado["Linea_Servicio"].dropna().unique()),
                        key="f_linea",
                        placeholder="Todas",
                    )
                    df_filtrado = aplicar(df_filtrado, "Linea_Servicio", sel_linea)
                    if sel_linea:
                        resumen_filtros.append("Línea: " + ", ".join(sel_linea))

pct = len(df_filtrado) / max(len(df_base), 1)
st.caption(
    f"📊 Mostrando **{len(df_filtrado):,}** de {len(df_base):,} pedidos ({pct:.0%})"
    + (" · Filtros activos: " + " | ".join(resumen_filtros) if resumen_filtros else " · Sin filtros aplicados")
)

if df_filtrado.empty:
    st.warning("Los filtros actuales no devuelven resultados. Pulsa **↺ Limpiar** o amplía la selección.")
    st.stop()

base = df_base
d = df_filtrado
HAY_FILTROS = len(d) != len(base)

# ==========================================
# 6. FUNCIONES DE CÁLCULO Y PRESENTACIÓN
# ==========================================
NOMBRE_VISIBLE = {"AñoMes": "Fecha"}


def necesita(x: pd.DataFrame, cols) -> bool:
    falta = [NOMBRE_VISIBLE.get(c, c) for c in cols if c not in x.columns]
    if falta:
        st.info(f"Para este gráfico falta: **{', '.join(falta)}**. Configúrala en la pestaña **⚙️ Gobernanza**.")
        return False
    return True


def mostrar(fig, clave: str, alto: int = 370):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=28, b=10), legend_title_text="")
    st.plotly_chart(fig, key=clave, config={"displaylogo": False}, **AN_PLOT)


def meta_por(x: pd.DataFrame, por=None):
    """Meta de ventas agregada."""
    if "Meta_Venta" not in x:
        return None
    por = list(por or [])
    if META_REPETIDA and "Provincia" in x and "AñoMes" in x:
        llaves = por + [c for c in ("Provincia", "AñoMes") if c not in por]
        celdas = x.groupby(llaves)["Meta_Venta"].first()
        return celdas.groupby(level=por).sum() if por else celdas.sum()
    return x.groupby(por)["Meta_Venta"].sum() if por else x["Meta_Venta"].sum()


def resumen_por(x: pd.DataFrame, col: str) -> pd.DataFrame:
    g = x.groupby(col)
    r = pd.DataFrame({"Pedidos": g.size()})
    if "Venta_Neta" in x:
        r["Venta_Neta"] = g["Venta_Neta"].sum()
        if "Margen_Bruto" in x:
            r["Margen_%"] = g["Margen_Bruto"].sum() / r["Venta_Neta"].replace(0, np.nan) * 100
        if "Meta_Venta" in x and col in ("Provincia", "AñoMes"):
            meta = meta_por(x, [col]).reindex(r.index)
            r["Cumplimiento_%"] = r["Venta_Neta"] / meta.replace(0, np.nan) * 100
    if "Hubo_Reclamo" in x:
        r["Reclamos_x1000"] = g["Hubo_Reclamo"].sum() / r["Pedidos"] * 1000
    if "Entrega_A_Tiempo" in x:
        r["OTD_%"] = g["Entrega_A_Tiempo"].mean() * 100
    if "Tiempo_Entrega" in x:
        r["Tiempo_medio"] = g["Tiempo_Entrega"].mean()
    return r.reset_index()


def calcular_kpis(x: pd.DataFrame) -> dict:
    n = len(x)
    k = {"pedidos": n}
    if "Venta_Neta" in x:
        k["venta"] = x["Venta_Neta"].sum()
        if "Margen_Bruto" in x:
            k["margen_monto"] = x["Margen_Bruto"].sum()
            k["margen_pct"] = k["margen_monto"] / k["venta"] * 100 if k["venta"] > 0 else np.nan
        if "Meta_Venta" in x:
            meta = meta_por(x)
            k["cumplimiento"] = k["venta"] / meta * 100 if meta and meta > 0 else np.nan
    if "Hubo_Reclamo" in x and n:
        k["reclamos"] = x["Hubo_Reclamo"].sum() / n * 1000
    if "Entrega_A_Tiempo" in x and n:
        k["otd"] = x["Entrega_A_Tiempo"].mean() * 100
    return k


def tarjeta(col, etiqueta, valor, fmt, ref=None, inverso=False, ayuda="", unidad=""):
    with col.container(border=True):
        if valor is None or pd.isna(valor):
            st.metric(etiqueta, "N/D", help=ayuda or "Falta la columna necesaria para este KPI.")
            return
        delta = None
        if HAY_FILTROS and ref is not None and not pd.isna(ref):
            delta = f"{valor - ref:+,.1f}{unidad} vs. total"
        st.metric(
            etiqueta,
            fmt.format(valor),
            delta=delta,
            delta_color="inverse" if inverso else "normal",
            help=ayuda or None,
        )


K = calcular_kpis(d)
K0 = calcular_kpis(base)

DEFINICIONES = pd.DataFrame([
    {
        "KPI": "Ventas netas",
        "Fórmula": "Σ Venta_Neta",
        "Fuente": "CSV de pedidos",
        "Responsable (propuesto)": "Finanzas",
    },
    {
        "KPI": "Margen bruto (%)",
        "Fórmula": "Σ Margen_Bruto ÷ Σ Venta_Neta × 100",
        "Fuente": "CSV de pedidos",
        "Responsable (propuesto)": "Finanzas",
    },
    {
        "KPI": "Cumplimiento de meta (%)",
        "Fórmula": "Σ Venta_Neta ÷ Meta del periodo × 100 (meta contada una vez por provincia y mes)",
        "Fuente": "Meta_Venta",
        "Responsable (propuesto)": "Dirección comercial",
    },
    {
        "KPI": "Reclamos por 1.000 pedidos",
        "Fórmula": "Pedidos con reclamo ÷ pedidos totales × 1.000",
        "Fuente": "Hubo_Reclamo",
        "Responsable (propuesto)": "Atención al cliente",
    },
    {
        "KPI": "Entrega a tiempo – OTD (%)",
        "Fórmula": "Pedidos entregados a tiempo ÷ pedidos totales × 100",
        "Fuente": "Entrega_A_Tiempo",
        "Responsable (propuesto)": "Operaciones",
    },
])


# ==========================================
# 7. VISTAS DE LAS 5 SECCIONES DEL DASHBOARD
# ==========================================
def pagina_ejecutiva():
    t1, t2, t3, t4, t5 = st.columns(5)
    tarjeta(t1, "Ventas netas", K.get("venta"), "${:,.0f}", ayuda="Suma de Venta_Neta")
    tarjeta(
        t2, "Margen bruto", K.get("margen_pct"), "{:.1f}%", K0.get("margen_pct"), unidad=" pp",
        ayuda=f"Margen bruto ÷ ventas netas. Monto: ${K.get('margen_monto', 0):,.0f}",
    )
    tarjeta(
        t3, "Cumplimiento meta", K.get("cumplimiento"), "{:.1f}%", K0.get("cumplimiento"), unidad=" pp",
        ayuda="Ventas netas ÷ Meta_Venta. Requiere la columna Meta_Venta.",
    )
    tarjeta(
        t4, "Reclamos / 1.000", K.get("reclamos"), "{:.1f}", K0.get("reclamos"), inverso=True,
        ayuda="Pedidos con reclamo ÷ total de pedidos × 1.000",
    )
    tarjeta(
        t5, "Entrega a tiempo (OTD)", K.get("otd"), "{:.1f}%", K0.get("otd"), unidad=" pp",
        ayuda="Pedidos entregados a tiempo ÷ total de pedidos",
    )

    if "Provincia" in d and d["Provincia"].nunique() > 1:
        r = resumen_por(d, "Provincia")
        msgs = []
        if "Venta_Neta" in r and r["Venta_Neta"].sum() > 0:
            t = r.loc[r["Venta_Neta"].idxmax()]
            msgs.append(f"💰 **{t['Provincia']}** concentra el {t['Venta_Neta'] / r['Venta_Neta'].sum():.0%} de las ventas netas.")
        if "Cumplimiento_%" in r and r["Cumplimiento_%"].notna().any():
            t = r.loc[r["Cumplimiento_%"].idxmin()]
            msgs.append(f"🎯 Menor cumplimiento: **{t['Provincia']}** ({t['Cumplimiento_%']:.1f}%).")
        if "Reclamos_x1000" in r and r["Reclamos_x1000"].notna().any():
            t = r.loc[r["Reclamos_x1000"].idxmax()]
            msgs.append(f"📣 Mayor tasa de reclamos: **{t['Provincia']}** ({t['Reclamos_x1000']:.1f} / 1.000).")
        if "OTD_%" in r and r["OTD_%"].notna().any():
            t = r.loc[r["OTD_%"].idxmin()]
            msgs.append(f"⏱️ Menor OTD: **{t['Provincia']}** ({t['OTD_%']:.1f}%).")
        if msgs:
            st.info(" · ".join(msgs))

    c1, c2 = st.columns([1, 1.3])
    with c1:
        with st.container(border=True):
            st.subheader("Ventas netas por provincia")
            if necesita(d, ["Provincia", "Venta_Neta"]):
                r = resumen_por(d, "Provincia").sort_values("Venta_Neta")
                fig = px.bar(
                    r, x="Venta_Neta", y="Provincia", orientation="h",
                    color="Venta_Neta", color_continuous_scale="Blues", text_auto=".3s",
                )
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Ventas netas (US$)")
                mostrar(fig, "p1_ventas_prov")
    with c2:
        with st.container(border=True):
            st.subheader("Evolución mensual de ventas netas")
            if necesita(d, ["AñoMes", "Venta_Neta"]):
                m = d.groupby("AñoMes", as_index=False)["Venta_Neta"].sum().sort_values("AñoMes")
                fig = px.line(m, x="AñoMes", y="Venta_Neta", markers=True)
                fig.update_traces(name="Ventas netas", showlegend=True)
                meta_m = meta_por(d, ["AñoMes"])
                if meta_m is not None:
                    fig.add_trace(
                        go.Scatter(
                            x=m["AñoMes"],
                            y=meta_m.reindex(m["AñoMes"]).values,
                            name="Meta",
                            mode="lines",
                            line=dict(dash="dash", color="#F59E0B"),
                        )
                    )
                fig.update_layout(xaxis_title=None, yaxis_title="US$")
                mostrar(fig, "p1_serie")

    c3, c4 = st.columns(2)
    with c3:
        with st.container(border=True):
            st.subheader("Reclamos por 1.000 pedidos")
            if necesita(d, ["Provincia", "Hubo_Reclamo"]):
                r = resumen_por(d, "Provincia").sort_values("Reclamos_x1000")
                fig = px.bar(
                    r, x="Reclamos_x1000", y="Provincia", orientation="h",
                    color="Reclamos_x1000", color_continuous_scale="Reds", text_auto=".1f",
                )
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Reclamos / 1.000 pedidos")
                mostrar(fig, "p1_reclamos")
    with c4:
        with st.container(border=True):
            cab_otd, inp_otd = st.columns([1.6, 1])
            with cab_otd:
                st.subheader("Entrega a tiempo por provincia")
            with inp_otd:
                meta_otd = st.number_input("Meta OTD (%)", 0, 100, 90, key="meta_otd")
            if necesita(d, ["Provincia", "Entrega_A_Tiempo"]):
                r = resumen_por(d, "Provincia").sort_values("OTD_%")
                fig = px.bar(
                    r, x="OTD_%", y="Provincia", orientation="h",
                    color="OTD_%", color_continuous_scale="RdYlGn", text_auto=".1f",
                )
                fig.add_vline(x=meta_otd, line_dash="dash", annotation_text=f"Meta {meta_otd}%")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="% entregado a tiempo")
                mostrar(fig, "p1_otd", alto=325)

    if "Meta_Venta" in d and "Provincia" in d and "Venta_Neta" in d:
        with st.container(border=True):
            st.subheader("Cumplimiento de meta por provincia")
            r = resumen_por(d, "Provincia").dropna(subset=["Cumplimiento_%"]).sort_values("Cumplimiento_%")
            if r.empty:
                st.info("No hay metas válidas para calcular el cumplimiento.")
            else:
                fig = px.bar(
                    r, x="Cumplimiento_%", y="Provincia", orientation="h",
                    color="Cumplimiento_%", color_continuous_scale="RdYlGn", text_auto=".1f",
                )
                fig.add_vline(x=100, line_dash="dash", annotation_text="Meta 100%")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Ventas netas ÷ meta (%)")
                mostrar(fig, "p1_cumplimiento", alto=320)


def pagina_territorial():
    """Elimina las pestañas anidadas usando un control segmentado fluido y vista integrada."""
    if not necesita(d, ["Provincia", "Canal"]):
        return

    opciones_vista = [
        "🎛️ Vista integrada",
        "🌞 Composición (Sunburst)",
        "🔥 Mapa de calor",
        "🎯 Pedidos vs. reclamos",
        "📋 Tabla comparativa",
    ]
    opciones_metrica = ["Pedidos"] + (["Ventas netas"] if "Venta_Neta" in d else [])

    col_sel, col_met = st.columns([2.4, 1.2])
    with col_sel:
        if hasattr(st, "segmented_control"):
            vista_terr = st.segmented_control(
                "Modo de visualización territorial",
                opciones_vista,
                default=opciones_vista[0],
                key="seg_terr",
            ) or opciones_vista[0]
        else:
            vista_terr = st.radio("Modo de visualización territorial", opciones_vista, horizontal=True, key="rad_terr")
    with col_met:
        metrica = st.radio("Medir composición y mapa de calor por", opciones_metrica, horizontal=True, key="met_terr")

    def render_sunburst(alto=430):
        with st.container(border=True):
            st.subheader("🌞 Composición por Provincia y Canal")
            if metrica == "Ventas netas":
                fig = px.sunburst(d[d["Venta_Neta"] > 0], path=["Provincia", "Canal"], values="Venta_Neta")
            else:
                fig = px.sunburst(d, path=["Provincia", "Canal"])
            fig.update_traces(textinfo="label+percent parent")
            mostrar(fig, "p2_sunburst", alto=alto)

    def render_calor(alto=430):
        with st.container(border=True):
            st.subheader("🔥 Matriz Provincia × Canal")
            if metrica == "Ventas netas":
                piv = pd.crosstab(d["Provincia"], d["Canal"], values=d["Venta_Neta"], aggfunc="sum").fillna(0)
            else:
                piv = pd.crosstab(d["Provincia"], d["Canal"])
            fig = px.imshow(piv, text_auto=".2s", aspect="auto", color_continuous_scale="Blues")
            fig.update_layout(xaxis_title=None, yaxis_title=None)
            mostrar(fig, "p2_calor", alto=alto)

    def render_scatter(alto=430):
        with st.container(border=True):
            st.subheader("🎯 Volumen de pedidos vs. Tasa de reclamos")
            if necesita(d, ["Hubo_Reclamo"]):
                r = resumen_por(d, "Provincia")
                tamano = r["Venta_Neta"].fillna(0).clip(lower=0) if "Venta_Neta" in r else None
                fig = px.scatter(
                    r, x="Pedidos", y="Reclamos_x1000", size=tamano,
                    color="OTD_%" if "OTD_%" in r else None,
                    text="Provincia", color_continuous_scale="RdYlGn", size_max=45,
                )
                fig.update_traces(textposition="top center")
                fig.update_layout(xaxis_title="Pedidos", yaxis_title="Reclamos por 1.000 pedidos")
                mostrar(fig, "p2_scatter", alto=alto)
                st.caption("Tamaño de burbuja = Ventas netas · Color = Entrega a tiempo (OTD %).")

    def render_tabla():
        with st.container(border=True):
            st.subheader("📋 Resumen comparativo por provincia")
            r = resumen_por(d, "Provincia")
            if "Venta_Neta" in r:
                r = r.sort_values("Venta_Neta", ascending=False)
            st.dataframe(
                r,
                hide_index=True,
                **AN_DF,
                column_config={
                    "Venta_Neta": st.column_config.NumberColumn("Ventas netas", format="$ %.0f"),
                    "Margen_%": st.column_config.ProgressColumn("Margen (%)", min_value=0, max_value=100, format="%.1f"),
                    "Cumplimiento_%": st.column_config.NumberColumn("Cumplimiento (%)", format="%.1f"),
                    "Reclamos_x1000": st.column_config.NumberColumn("Reclamos / 1.000", format="%.1f"),
                    "OTD_%": st.column_config.ProgressColumn("Entrega a tiempo (%)", min_value=0, max_value=100, format="%.1f"),
                    "Tiempo_medio": st.column_config.NumberColumn("Tiempo medio", format="%.1f"),
                },
            )

    if vista_terr == "🎛️ Vista integrada":
        g1, g2 = st.columns(2)
        with g1:
            render_sunburst(alto=380)
        with g2:
            render_calor(alto=380)
        render_scatter(alto=390)
        render_tabla()
    elif vista_terr == "🌞 Composición (Sunburst)":
        render_sunburst(alto=500)
    elif vista_terr == "🔥 Mapa de calor":
        render_calor(alto=460)
    elif vista_terr == "🎯 Pedidos vs. reclamos":
        render_scatter(alto=480)
    else:
        render_tabla()


def pagina_operativa():
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Distribución del tiempo de entrega")
            if necesita(d, ["Provincia", "Tiempo_Entrega"]):
                fig = px.box(
                    d.dropna(subset=["Tiempo_Entrega"]),
                    x="Provincia", y="Tiempo_Entrega", color="Provincia", points="outliers",
                )
                fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Tiempo de entrega")
                mostrar(fig, "p3_box")
    with c2:
        with st.container(border=True):
            st.subheader("Entrega a tiempo por canal")
            if necesita(d, ["Canal", "Entrega_A_Tiempo"]):
                r = resumen_por(d, "Canal").sort_values("OTD_%")
                fig = px.bar(
                    r, x="OTD_%", y="Canal", orientation="h",
                    color="OTD_%", color_continuous_scale="RdYlGn", text_auto=".1f",
                )
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="% entregado a tiempo")
                mostrar(fig, "p3_otd_canal")

    if "Provincia" in d and "Tiempo_Entrega" in d:
        with st.container(border=True):
            st.subheader("Variabilidad de entrega por provincia")
            var = (
                d.groupby("Provincia")["Tiempo_Entrega"]
                .agg(Media="mean", Mediana="median", P90=lambda s: s.quantile(0.9), Desv_Est="std")
                .reset_index()
            )
            var["Coef_Var_%"] = (var["Desv_Est"] / var["Media"].replace(0, np.nan)) * 100
            st.dataframe(var.round(2).sort_values("Coef_Var_%", ascending=False), hide_index=True, **AN_DF)
            st.caption(
                "El coeficiente de variación (desv. estándar ÷ media) permite comparar la dispersión entre "
                "provincias aunque sus tiempos medios sean distintos. P90: el 90 % de las entregas tarda ese tiempo o menos."
            )


def pagina_pedidos():
    """Sección dedicada al explorador de pedidos individuales y exportación gobernada."""
    sensibles = [c for c in d.columns if any(s in _limpiar(c) for s in SENSIBLES)]
    vista = d.drop(columns=sensibles).copy()

    with st.container(border=True):
        c_busq, c_est, c_desc = st.columns([2, 1.5, 1.2], vertical_alignment="bottom")
        with c_busq:
            texto_busq = st.text_input(
                "🔎 Buscar en pedidos filtrados (provincia, ciudad, canal…)",
                placeholder="Escribe para filtrar filas…",
            )
        with c_est:
            filtro_rapido = st.selectbox(
                "Filtro rápido de incidencias",
                ["Todos los pedidos filtrados", "Solo con reclamo", "Solo entregas fuera de tiempo"],
            )
        if filtro_rapido == "Solo con reclamo" and "Hubo_Reclamo" in vista.columns:
            vista = vista[vista["Hubo_Reclamo"] == 1]
        elif filtro_rapido == "Solo entregas fuera de tiempo" and "Entrega_A_Tiempo" in vista.columns:
            vista = vista[vista["Entrega_A_Tiempo"] == 0]

        if texto_busq.strip():
            patron = texto_busq.strip().lower()
            cols_txt = [c for c in ("Provincia", "Ciudad", "Canal", "Linea_Servicio") if c in vista.columns]
            if cols_txt:
                mascara = vista[cols_txt].astype(str).apply(lambda col: col.str.lower().str.contains(patron, na=False)).any(axis=1)
                vista = vista[mascara]

        with c_desc:
            st.download_button(
                "📥 Descargar CSV filtrado",
                data=vista.to_csv(index=False).encode("utf-8-sig"),
                file_name="reporte_logiandes_filtrado.csv",
                mime="text/csv",
                **AN_BTN,
            )

        if sensibles:
            st.caption(f"🔒 Columnas ocultas automáticamente por gobernanza de datos: **{', '.join(sensibles)}**")
        st.caption(f"Mostrando **{len(vista):,}** registros.")
        st.dataframe(vista, height=460, **AN_DF)


def pagina_gobernanza():
    """Centraliza el mapeo de columnas, calidad de datos y diccionario de KPIs."""
    with st.container(border=True):
        st.subheader("🧩 Mapeo de columnas del archivo y reglas de cálculo")
        st.caption("Confirma o ajusta qué columna de tu archivo CSV corresponde a cada campo estándar del modelo.")
        opciones_col = ["(ninguna)"] + list(df_raw.columns)
        grid = st.columns(3)
        for i, campo in enumerate(CAMPOS):
            defecto = campo if campo in df_raw.columns else sug.get(campo, "(ninguna)")
            etiqueta = campo + (" *" if campo in CAMPOS_CORE else " (opcional)")
            grid[i % 3].selectbox(
                etiqueta,
                opciones_col,
                index=opciones_col.index(defecto) if defecto in opciones_col else 0,
                key=f"map_{huella[:8]}_{campo}",
            )

        ajustes = st.columns(2)
        if "Margen_Bruto" in disponibles_actual:
            ajustes[0].radio(
                "Margen_Bruto está expresado como…",
                ["Monto (US$)", "Porcentaje (%)"],
                index=1 if sugiere_pct_def else 0,
                key=clave_margen,
            )
        if "Meta_Venta" in disponibles_actual:
            ajustes[1].radio(
                "Meta_Venta se registra…",
                ["Repetida en cada pedido (provincia y mes)", "Un valor por pedido (se suma)"],
                key=clave_meta,
            )

    col_cal, col_dic = st.columns([1, 1.4])
    with col_cal:
        with st.container(border=True):
            st.subheader("🧪 Auditoría de calidad de datos")
            cols_ok = [c for c in CAMPOS + ["AñoMes"] if c in base.columns]
            calidad = pd.DataFrame({
                "Columna": cols_ok,
                "Vacíos (%)": [round(base[c].isna().mean() * 100, 1) for c in cols_ok],
                "Valores únicos": [int(base[c].nunique(dropna=True)) for c in cols_ok],
            })
            st.dataframe(calidad, hide_index=True, **AN_DF)
            st.caption(f"Filas totales: **{len(base):,}** · Filas duplicadas exactas: **{int(base.duplicated().sum()):,}**")

    with col_dic:
        with st.container(border=True):
            st.subheader("📖 Diccionario oficial de KPIs")
            st.dataframe(DEFINICIONES, hide_index=True, **AN_DF)
            st.caption("Los responsables son una propuesta basada en las áreas del caso; deben validarse con la gerencia.")


# ==========================================
# 8. BARRA DE NAVEGACIÓN PRINCIPAL (5 PESTAÑAS FLUIDAS)
# ==========================================
# El doble espacio antes de \n genera el salto de línea entre icono y etiqueta dentro del botón cápsula
tab_ej, tab_te, tab_op, tab_pe, tab_go = st.tabs([
    "🏛️  \nEjecutiva",
    "🗺️  \nTerritorial",
    "🔧  \nOperativa",
    "🔎  \nPedidos",
    "⚙️  \nGobernanza",
])

with tab_ej:
    pagina_ejecutiva()
with tab_te:
    pagina_territorial()
with tab_op:
    pagina_operativa()
with tab_pe:
    pagina_pedidos()
with tab_go:
    pagina_gobernanza()

st.divider()
st.caption("LogiAndes S.A. © 2026 · Prototipo BI en Streamlit con Navegación Fluida · Datos de uso académico.")