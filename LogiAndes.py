"""
LogiAndes S.A. · Solución de Business Intelligence Accionable (Prueba Práctica 2)
Materia: Visualización, Storytelling y Business Intelligence
Analista responsable (Caso): Camila Andrade

Ejecutar:  streamlit run LogiAndes.py
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
    """Compatibilidad entre `width="stretch"` y `use_container_width=True`."""
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
# 2. ESTILOS Y NAVEGACIÓN FLUIDA (PILL TABS)
# ==========================================
def inyectar_estilos(tema_nav: str):
    """Inyecta CSS con la barra de navegación fluida tipo cápsula e indicadores de estado."""
    temas = {
        "Oscuro Neón": {
            "bar_bg": "linear-gradient(145deg, #18181b 0%, #111115 100%)",
            "bar_border": "1px solid rgba(255, 255, 255, 0.09)",
            "bar_shadow": "0 14px 32px rgba(0, 0, 0, 0.28), 0 4px 12px rgba(0, 0, 0, 0.18)",
            "tab_color": "#a1a1aa",
            "tab_hover_bg": "rgba(255, 255, 255, 0.06)",
            "tab_hover_color": "#f4f4f5",
            "active_bg": "radial-gradient(circle at 50% 0%, rgba(225, 29, 72, 0.30) 0%, rgba(225, 29, 72, 0.06) 75%)",
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
            "tab_color": "rgba(255, 255, 255, 0.82)",
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
                padding-top: 1.3rem;
                padding-bottom: 2.5rem;
                max-width: 1440px;
            }}

            .top-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 0.75rem;
                margin-bottom: 0.55rem;
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
                font-size: 1.2rem;
                width: 42px;
                height: 42px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.28);
            }}
            .main-title {{
                font-size: 1.6rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin: 0;
                line-height: 1.15;
            }}
            .sub-title {{
                font-size: 0.85rem;
                opacity: 0.75;
                margin: 0;
            }}

            /* BARRA DE NAVEGACIÓN FLUIDA (PILL NAVIGATION TABS) */
            div[data-testid="stTabs"] > div[role="tablist"] {{
                background: {t["bar_bg"]} !important;
                border: {t["bar_border"]} !important;
                box-shadow: {t["bar_shadow"]} !important;
                border-radius: 999px !important;
                padding: 0.42rem 0.55rem !important;
                gap: 0.4rem !important;
                width: fit-content !important;
                max-width: 100% !important;
                margin: 0.3rem auto 1.15rem auto !important;
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                overflow-x: auto !important;
            }}

            div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
            div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{
                display: none !important;
            }}

            div[data-testid="stTabs"] button[role="tab"] {{
                border-radius: 999px !important;
                padding: 0.52rem 1.45rem !important;
                min-width: 135px !important;
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

            div[data-testid="stTabs"] button[role="tab"] p {{
                margin: 0 !important;
                text-align: center !important;
                line-height: 1.28 !important;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                color: inherit !important;
            }}

            div[data-testid="stTabs"] button[role="tab"]:hover {{
                background: {t["tab_hover_bg"]} !important;
                color: {t["tab_hover_color"]} !important;
                transform: translateY(-1px) !important;
            }}

            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
                background: {t["active_bg"]} !important;
                color: {t["active_color"]} !important;
                box-shadow: {t["active_shadow"]} !important;
                transform: scale(1.03) !important;
            }}

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

            @keyframes fadeSlideUp {{
                from {{ opacity: 0; transform: translateY(8px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            div[data-testid="stTabs"] div[role="tabpanel"] {{
                animation: fadeSlideUp 0.28s cubic-bezier(0.22, 1, 0.36, 1);
            }}

            .semaforo-pill {{
                display: inline-block;
                padding: 0.15rem 0.55rem;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 600;
                margin-top: 0.2rem;
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
    if pd.api.types.is_numeric_dtype(s):
        return s
    t = s.astype(str).str.replace(r"[^\d,.\-]", "", regex=True)
    if t.str.contains(r",\d{1,2}$").mean() > 0.5:
        t = t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        t = t.str.replace(",", "", regex=False)
    return pd.to_numeric(t, errors="coerce")


def a_binario(s: pd.Series) -> pd.Series:
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
# 4. BARRA LATERAL: ORIGEN DE DATOS Y ESTILO
# ==========================================
CARPETA_DEFECTO = Path(__file__).resolve().parent

st.sidebar.title("🚚 LogiAndes S.A.")
st.sidebar.caption("Sistema de Inteligencia de Negocios")

with st.sidebar.expander("🎨 Estilo de navegación", expanded=True):
    tema_nav = st.radio(
        "Diseño de la barra de navegación",
        ["Oscuro Neón", "Cápsula Clara", "Rojo Vibrante"],
        index=0,
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
                    <div class='main-title'>LogiAndes S.A. · Sistema de Inteligencia de Negocios</div>
                    <div class='sub-title'>De visualizaciones aisladas a decisiones monitoreables</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.warning(f"No encontré archivos CSV en `{carpeta}`. Sube el dataset de LogiAndes aquí:")
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

mapeo = {}
for campo in CAMPOS:
    clave_col = f"map_{huella[:8]}_{campo}"
    defecto = campo if campo in df_raw.columns else sug.get(campo, "(ninguna)")
    elegido = st.session_state.get(clave_col, defecto)
    if elegido not in ("(ninguna)", campo) and elegido in df_raw.columns:
        mapeo[campo] = elegido

disponibles_actual = set(df_raw.columns) | set(mapeo)
faltan_core = [c for c in CAMPOS_CORE if c not in disponibles_actual]

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
# 5. CABECERA Y FILTROS TRANSVERSALES (DOSIFICADOS)
# ==========================================
CLAVES_FILTROS = ["f_preset", "f_rango", "f_prov", "f_canal", "f_ciudad", "f_linea"]


def reiniciar_filtros():
    for k in CLAVES_FILTROS:
        st.session_state.pop(k, None)


def selector(label: str, opciones: list, clave: str) -> list:
    st.session_state[clave] = [v for v in st.session_state.get(clave, []) if v in opciones]
    if hasattr(st, "pills") and len(opciones) <= 6:
        return list(st.pills(label, opciones, selection_mode="multi", key=clave) or [])
    return st.multiselect(label, opciones, key=clave, placeholder="Todas")


def aplicar(df: pd.DataFrame, col: str, seleccion: list) -> pd.DataFrame:
    return df[df[col].isin(seleccion)] if (seleccion and col in df.columns) else df


df_filtrado = df_base.copy()
resumen_filtros = []

st.markdown(
    f"""
    <div class='top-header'>
        <div class='brand-box'>
            <div class='brand-badge'>LA</div>
            <div>
                <div class='main-title'>LogiAndes S.A. · Monitoreo de Desempeño e Inteligencia de Negocios</div>
                <div class='sub-title'>Cobertura: Quito, Guayaquil, Cuenca, Manta, Ambato y Loja · Fuente activa: <b>{nombre_archivo}</b></div>
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
        + "**. Ve a la pestaña **📋 Ficha BI & Gobernanza** para mapearlas."
    )

# Filtros principales (Nivel global: Periodo, Provincia, Canal) para evitar sobreinteractividad
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
            preset = st.selectbox("📅 Periodo de análisis", opciones_periodo, key="f_preset")
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
            sel_canal = selector("🛒 Canal de distribución", sorted(df_filtrado["Canal"].dropna().unique()), "f_canal")
            df_filtrado = aplicar(df_filtrado, "Canal", sel_canal)
            if sel_canal:
                resumen_filtros.append("Canal: " + ", ".join(sel_canal))

    with f4:
        st.write("")
        st.button("↺ Limpiar", on_click=reiniciar_filtros, **AN_BTN)

pct = len(df_filtrado) / max(len(df_base), 1)
st.caption(
    f"📊 Mostrando **{len(df_filtrado):,}** de {len(df_base):,} pedidos ({pct:.0%})"
    + (" · Filtros globales activos: " + " | ".join(resumen_filtros) if resumen_filtros else " · Vista nacional consolidada")
    + " · *(Los filtros específicos de Ciudad y Línea de Servicio se encuentran en las vistas Territorial y Operativa para evitar sobreinteractividad)*."
)

if df_filtrado.empty:
    st.warning("Los filtros actuales no devuelven resultados. Pulsa **↺ Limpiar** o amplía la selección.")
    st.stop()

base = df_base
d = df_filtrado
HAY_FILTROS = len(d) != len(base)

# ==========================================
# 6. FUNCIONES DE CÁLCULO, SEMÁFOROS Y FICHA TÉCNICA DE KPIS
# ==========================================
NOMBRE_VISIBLE = {"AñoMes": "Fecha"}


def necesita(x: pd.DataFrame, cols) -> bool:
    falta = [NOMBRE_VISIBLE.get(c, c) for c in cols if c not in x.columns]
    if falta:
        st.info(f"Para este gráfico falta: **{', '.join(falta)}**. Configúrala en **📋 Ficha BI & Gobernanza**.")
        return False
    return True


def mostrar(fig, clave: str, alto: int = 370):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=28, b=10), legend_title_text="")
    st.plotly_chart(fig, key=clave, config={"displaylogo": False}, **AN_PLOT)


def meta_por(x: pd.DataFrame, por=None):
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
            k["meta_total"] = meta
            k["cumplimiento"] = k["venta"] / meta * 100 if meta and meta > 0 else np.nan
    if "Hubo_Reclamo" in x and n:
        k["reclamos"] = x["Hubo_Reclamo"].sum() / n * 1000
    if "Entrega_A_Tiempo" in x and n:
        k["otd"] = x["Entrega_A_Tiempo"].mean() * 100
    return k


def evaluar_umbral(valor, verde, amarillo, menor_es_mejor=False):
    """Evalúa el estado del KPI según umbrales de la ficha técnica."""
    if valor is None or pd.isna(valor):
        return "⚪ Sin dato", "#64748b", "rgba(100,116,139,0.12)"
    if not menor_es_mejor:
        if valor >= verde:
            return "🟢 Óptimo (En meta)", "#16a34a", "rgba(22,163,74,0.12)"
        if valor >= amarillo:
            return "🟡 Alerta (Seguimiento)", "#d97706", "rgba(217,119,6,0.12)"
        return "🔴 Crítico (Acción requerida)", "#dc2626", "rgba(220,38,38,0.12)"
    else:
        if valor <= verde:
            return "🟢 Óptimo (Controlado)", "#16a34a", "rgba(22,163,74,0.12)"
        if valor <= amarillo:
            return "🟡 Alerta (Atención)", "#d97706", "rgba(217,119,6,0.12)"
        return "🔴 Crítico (Excede umbral)", "#dc2626", "rgba(220,38,38,0.12)"


def tarjeta_kpi(col, etiqueta, valor, fmt, ref=None, inverso=False, ayuda="", unidad="", sem=None):
    with col.container(border=True):
        if valor is None or pd.isna(valor):
            st.metric(etiqueta, "N/D", help=ayuda or "Falta la columna necesaria para este KPI.")
            return
        delta = None
        if HAY_FILTROS and ref is not None and not pd.isna(ref):
            delta = f"{valor - ref:+,.1f}{unidad} vs. nacional"
        st.metric(
            etiqueta,
            fmt.format(valor),
            delta=delta,
            delta_color="inverse" if inverso else "normal",
            help=ayuda or None,
        )
        if sem:
            txt_s, col_s, bg_s = sem
            st.markdown(
                f"<span class='semaforo-pill' style='color:{col_s};background:{bg_s};'>{txt_s}</span>",
                unsafe_allow_html=True,
            )


K = calcular_kpis(d)
K0 = calcular_kpis(base)

# FICHA TÉCNICA COMPLETA DE LOS 5 KPIS (Cumple los 9 atributos exigidos en la Prueba Práctica 2)
FICHA_TECNICA_KPIS = pd.DataFrame([
    {
        "Nombre del Indicador": "1. Ventas Netas (US$)",
        "Objetivo": "Cuantificar los ingresos reales efectivos descontando devoluciones e impuestos para alinear el criterio financiero y comercial.",
        "Fórmula": "Σ Venta_Neta",
        "Fuente": "ERP Facturación / CSV de pedidos (Venta_Neta)",
        "Frecuencia": "Mensual / Monitoreo continuo",
        "Meta": "≥ 100 % del presupuesto comercial asignado al territorio",
        "Umbral (Semáforo)": "🟢 ≥ 95 % de meta | 🟡 85 % – 94.9 % | 🔴 < 85 %",
        "Interpretación": "Mide la tracción comercial real por provincia y canal; evita sobreestimar ingresos al excluir ventas brutas anuladas o con nota de crédito.",
        "Responsable": "Finanzas / Dirección Comercial",
    },
    {
        "Nombre del Indicador": "2. Margen Bruto (%)",
        "Objetivo": "Monitorear la rentabilidad directa de las operaciones logísticas tras cubrir los costos directos de distribución.",
        "Fórmula": "(Σ Margen_Bruto ÷ Σ Venta_Neta) × 100",
        "Fuente": "Contabilidad Analítica / CSV de pedidos (Margen_Bruto, Venta_Neta)",
        "Frecuencia": "Mensual",
        "Meta": "≥ 25.0 % sobre ventas netas",
        "Umbral (Semáforo)": "🟢 ≥ 25.0 % | 🟡 18.0 % – 24.9 % | 🔴 < 18.0 %",
        "Interpretación": "Permite detectar provincias o canales con alto volumen de ventas pero baja rentabilidad por sobrecostos de última milla o descuentos excesivos.",
        "Responsable": "Gerencia Financiera",
    },
    {
        "Nombre del Indicador": "3. Cumplimiento de Meta Comercial (%)",
        "Objetivo": "Evaluar el grado de alcance de los objetivos comerciales mensuales por provincia sin duplicar metas por pedido.",
        "Fórmula": "(Σ Venta_Neta ÷ Meta_Mensual_Provincia) × 100",
        "Fuente": "Presupuesto Comercial y Facturación (Venta_Neta, Meta_Venta)",
        "Frecuencia": "Mensual",
        "Meta": "≥ 100.0 %",
        "Umbral (Semáforo)": "🟢 ≥ 95.0 % | 🟡 85.0 % – 94.9 % | 🔴 < 85.0 %",
        "Interpretación": "Compara el desempeño real frente a la cuota esperada del periodo; corrige la desconexión entre hojas de metas y cierres de facturación.",
        "Responsable": "Dirección Comercial / Gerencia General",
    },
    {
        "Nombre del Indicador": "4. Tasa de Reclamos por 1.000 Pedidos",
        "Objetivo": "Estandarizar la medición de incidencias de servicio al cliente relativizando por el volumen operativo de cada territorio.",
        "Fórmula": "(Σ Hubo_Reclamo ÷ Total_Pedidos) × 1.000",
        "Fuente": "CRM Atención al Cliente / CSV de pedidos (Hubo_Reclamo)",
        "Frecuencia": "Semanal / Mensual",
        "Meta": "≤ 25.0 reclamos por cada 1.000 pedidos",
        "Umbral (Semáforo)": "🟢 ≤ 25.0 | 🟡 25.1 – 50.0 | 🔴 > 50.0 por 1.000 pedidos",
        "Interpretación": "Evita comparaciones injustas entre provincias de alto volumen (ej. Quito/Guayaquil) y plazas medianas (ej. Loja/Ambato) usando tasas en lugar de conteos absolutos.",
        "Responsable": "Atención al Cliente",
    },
    {
        "Nombre del Indicador": "5. Entrega a Tiempo – OTD (%)",
        "Objetivo": "Medir la confiabilidad y puntualidad del servicio logístico frente a la promesa de entrega pactada con los comercios.",
        "Fórmula": "(Pedidos con Entrega_A_Tiempo = 1 ÷ Total_Pedidos) × 100",
        "Fuente": "TMS Operaciones / CSV de pedidos (Entrega_A_Tiempo)",
        "Frecuencia": "Diaria / Semanal / Mensual",
        "Meta": "≥ 90.0 % de pedidos entregados a tiempo",
        "Umbral (Semáforo)": "🟢 ≥ 90.0 % | 🟡 80.0 % – 89.9 % | 🔴 < 80.0 %",
        "Interpretación": "Refleja la salud operativa de las rutas urbanas y regionales; debe analizarse junto con el P90 y el coeficiente de variación de tiempos de entrega.",
        "Responsable": "Gerencia de Operaciones",
    },
])


# ==========================================
# 7. DESARROLLO DE LAS 4 VISTAS DEL DASHBOARD
# ==========================================
def pagina_ejecutiva():
    """NIVEL 1: Vista Ejecutiva (Gerencia General y Finanzas)."""
    t1, t2, t3, t4, t5 = st.columns(5)

    sem_cumpl = evaluar_umbral(K.get("cumplimiento"), 95.0, 85.0, menor_es_mejor=False)
    sem_margen = evaluar_umbral(K.get("margen_pct"), 25.0, 18.0, menor_es_mejor=False)
    sem_recl = evaluar_umbral(K.get("reclamos"), 25.0, 50.0, menor_es_mejor=True)
    sem_otd = evaluar_umbral(K.get("otd"), 90.0, 80.0, menor_es_mejor=False)

    tarjeta_kpi(
        t1, "1. Ventas netas", K.get("venta"), "${:,.0f}",
        ayuda="Ingresos netos efectivos (Σ Venta_Neta). Criterio unificado con Finanzas.",
        sem=sem_cumpl if K.get("cumplimiento") is not None else None,
    )
    tarjeta_kpi(
        t2, "2. Margen bruto", K.get("margen_pct"), "{:.1f}%", K0.get("margen_pct"), unidad=" pp",
        ayuda=f"Σ Margen_Bruto ÷ Σ Venta_Neta. Utilidad bruta acumulada: ${K.get('margen_monto', 0):,.0f}",
        sem=sem_margen,
    )
    tarjeta_kpi(
        t3, "3. Cumplimiento meta", K.get("cumplimiento"), "{:.1f}%", K0.get("cumplimiento"), unidad=" pp",
        ayuda="Ventas netas ÷ Meta comercial única por provincia y mes.",
        sem=sem_cumpl,
    )
    tarjeta_kpi(
        t4, "4. Reclamos / 1.000", K.get("reclamos"), "{:.1f}", K0.get("reclamos"), inverso=True,
        ayuda="Pedidos con reclamo por cada 1.000 pedidos (tasa estandarizada).",
        sem=sem_recl,
    )
    tarjeta_kpi(
        t5, "5. Entrega a tiempo (OTD)", K.get("otd"), "{:.1f}%", K0.get("otd"), unidad=" pp",
        ayuda="Porcentaje de pedidos entregados dentro del SLA prometido.",
        sem=sem_otd,
    )

    if "Provincia" in d and d["Provincia"].nunique() > 1:
        r = resumen_por(d, "Provincia")
        msgs = []
        if "Venta_Neta" in r and r["Venta_Neta"].sum() > 0:
            t = r.loc[r["Venta_Neta"].idxmax()]
            msgs.append(f"💰 **Concentración comercial:** **{t['Provincia']}** aporta el {t['Venta_Neta'] / r['Venta_Neta'].sum():.0%} de las ventas netas.")
        if "Cumplimiento_%" in r and r["Cumplimiento_%"].notna().any():
            t = r.loc[r["Cumplimiento_%"].idxmin()]
            msgs.append(f"🎯 **Brecha de meta:** **{t['Provincia']}** registra el menor cumplimiento ({t['Cumplimiento_%']:.1f}%).")
        if "Reclamos_x1000" in r and r["Reclamos_x1000"].notna().any():
            t = r.loc[r["Reclamos_x1000"].idxmax()]
            msgs.append(f"📣 **Foco de atención al cliente:** **{t['Provincia']}** presenta la mayor tasa relativa ({t['Reclamos_x1000']:.1f} reclamos / 1.000 pedidos).")
        if "OTD_%" in r and r["OTD_%"].notna().any():
            t = r.loc[r["OTD_%"].idxmin()]
            msgs.append(f"⏱️ **Alerta logística:** **{t['Provincia']}** tiene el menor OTD ({t['OTD_%']:.1f}%).")
        if msgs:
            st.info(" · ".join(msgs))
            st.caption(
                "⚠️ **Límite interpretativo (Gobernanza):** Estas lecturas describen asociaciones observadas en los registros internos de LogiAndes S.A. "
                "Variaciones coincidentes con indicadores del BCE o INEC no demuestran causalidad directa sin un diseño econométrico o experimental adicional."
            )

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
            st.subheader("Evolución mensual de ventas netas vs. Meta comercial")
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
                            name="Meta mensual",
                            mode="lines+markers",
                            line=dict(dash="dash", color="#F59E0B"),
                        )
                    )
                fig.update_layout(xaxis_title=None, yaxis_title="US$")
                mostrar(fig, "p1_serie")

    c3, c4 = st.columns(2)
    with c3:
        with st.container(border=True):
            st.subheader("Tasa de reclamos por 1.000 pedidos (Umbral ≤ 25)")
            if necesita(d, ["Provincia", "Hubo_Reclamo"]):
                r = resumen_por(d, "Provincia").sort_values("Reclamos_x1000")
                fig = px.bar(
                    r, x="Reclamos_x1000", y="Provincia", orientation="h",
                    color="Reclamos_x1000", color_continuous_scale="Reds", text_auto=".1f",
                )
                fig.add_vline(x=25, line_dash="dash", line_color="#16a34a", annotation_text="Meta ≤ 25")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Reclamos / 1.000 pedidos")
                mostrar(fig, "p1_reclamos")
    with c4:
        with st.container(border=True):
            cab_otd, inp_otd = st.columns([1.6, 1])
            with cab_otd:
                st.subheader("Entrega a tiempo (OTD %) por provincia")
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
            st.subheader("Cumplimiento de meta comercial por provincia (%)")
            r = resumen_por(d, "Provincia").dropna(subset=["Cumplimiento_%"]).sort_values("Cumplimiento_%")
            if not r.empty:
                fig = px.bar(
                    r, x="Cumplimiento_%", y="Provincia", orientation="h",
                    color="Cumplimiento_%", color_continuous_scale="RdYlGn", text_auto=".1f",
                )
                fig.add_vline(x=100, line_dash="dash", annotation_text="Meta 100%")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Ventas netas ÷ meta (%)")
                mostrar(fig, "p1_cumplimiento", alto=310)


def pagina_territorial():
    """NIVEL 2: Diagnóstico Territorial (Dirección Comercial y Atención al Cliente)."""
    if not necesita(d, ["Provincia", "Canal"]):
        return

    # Filtro progresivo propio del Nivel 2 (Ciudad) según diseño de Camila Andrade
    d_terr = d.copy()
    with st.container(border=True):
        ct1, ct2, ct3 = st.columns([1.5, 2.0, 1.1])
        with ct1:
            if "Ciudad" in d_terr.columns:
                ciudades_disp = sorted(d_terr["Ciudad"].dropna().unique())
                sel_ciudad = st.multiselect(
                    "🏙️ Filtro de Nivel 2 · Ciudad / Cantón",
                    ciudades_disp,
                    key="f_ciudad",
                    placeholder="Todas las ciudades del territorio",
                )
                d_terr = aplicar(d_terr, "Ciudad", sel_ciudad)
            else:
                st.caption("🏙️ Sin desglose por ciudad en este archivo.")

        opciones_vista = [
            "🎛️ Vista integrada",
            "🌞 Composición (Sunburst)",
            "🔥 Mapa de calor",
            "🎯 Pedidos vs. reclamos",
            "📋 Tabla comparativa",
        ]
        opciones_metrica = ["Pedidos"] + (["Ventas netas"] if "Venta_Neta" in d_terr else [])

        with ct2:
            if hasattr(st, "segmented_control"):
                vista_terr = st.segmented_control(
                    "Visualización territorial",
                    opciones_vista,
                    default=opciones_vista[0],
                    key="seg_terr",
                ) or opciones_vista[0]
            else:
                vista_terr = st.selectbox("Visualización territorial", opciones_vista, key="rad_terr")
        with ct3:
            metrica = st.radio("Métrica de volumen", opciones_metrica, horizontal=True, key="met_terr")

    if d_terr.empty:
        st.warning("No hay pedidos para la ciudad seleccionada.")
        return

    def render_sunburst(alto=400):
        with st.container(border=True):
            st.subheader("🌞 Participación por Provincia y Canal")
            if metrica == "Ventas netas":
                fig = px.sunburst(d_terr[d_terr["Venta_Neta"] > 0], path=["Provincia", "Canal"], values="Venta_Neta")
            else:
                fig = px.sunburst(d_terr, path=["Provincia", "Canal"])
            fig.update_traces(textinfo="label+percent parent")
            mostrar(fig, "p2_sunburst", alto=alto)

    def render_calor(alto=400):
        with st.container(border=True):
            st.subheader("🔥 Matriz de Intensidad: Provincia × Canal")
            if metrica == "Ventas netas":
                piv = pd.crosstab(d_terr["Provincia"], d_terr["Canal"], values=d_terr["Venta_Neta"], aggfunc="sum").fillna(0)
            else:
                piv = pd.crosstab(d_terr["Provincia"], d_terr["Canal"])
            fig = px.imshow(piv, text_auto=".2s", aspect="auto", color_continuous_scale="Blues")
            fig.update_layout(xaxis_title=None, yaxis_title=None)
            mostrar(fig, "p2_calor", alto=alto)

    def render_scatter(alto=400):
        with st.container(border=True):
            st.subheader("🎯 Relación Volumen de Pedidos vs. Tasa de Reclamos (Continuidad Clase 1)")
            if necesita(d_terr, ["Hubo_Reclamo"]):
                r = resumen_por(d_terr, "Provincia")
                tamano = r["Venta_Neta"].fillna(0).clip(lower=0) if "Venta_Neta" in r else None
                fig = px.scatter(
                    r, x="Pedidos", y="Reclamos_x1000", size=tamano,
                    color="OTD_%" if "OTD_%" in r else None,
                    text="Provincia", color_continuous_scale="RdYlGn", size_max=45,
                )
                fig.update_traces(textposition="top center")
                fig.update_layout(xaxis_title="Volumen de Pedidos", yaxis_title="Reclamos por 1.000 pedidos")
                mostrar(fig, "p2_scatter", alto=alto)
                st.caption(
                    "Prevención de sesgo visual: El eje Y mide la tasa por cada 1.000 pedidos (no el conteo bruto), "
                    "permitiendo comparar justamente territorios con distinto volumen de operación."
                )

    def render_tabla():
        with st.container(border=True):
            st.subheader("📋 Desempeño Integral Comparativo por Territorio")
            r = resumen_por(d_terr, "Provincia")
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
            render_sunburst(alto=370)
        with g2:
            render_calor(alto=370)
        render_scatter(alto=380)
        render_tabla()
    elif vista_terr == "🌞 Composición (Sunburst)":
        render_sunburst(alto=480)
    elif vista_terr == "🔥 Mapa de calor":
        render_calor(alto=450)
    elif vista_terr == "🎯 Pedidos vs. reclamos":
        render_scatter(alto=460)
    else:
        render_tabla()


def pagina_operativa():
    """NIVEL 3: Detalle Operativo (Gerencia de Operaciones y Consulta Granular Gobernada)."""
    d_op = d.copy()

    # Filtro progresivo propio del Nivel 3 (Línea de Servicio) + Control de Rol de Gobernanza
    with st.container(border=True):
        co1, co2, co3 = st.columns([1.8, 1.4, 1.4], vertical_alignment="bottom")
        with co1:
            if "Linea_Servicio" in d_op.columns:
                lineas_disp = sorted(d_op["Linea_Servicio"].dropna().unique())
                sel_linea = st.multiselect(
                    "📦 Filtro de Nivel 3 · Línea de servicio logístico",
                    lineas_disp,
                    key="f_linea",
                    placeholder="Todas las líneas (Urbana, Regional, Express…)",
                )
                d_op = aplicar(d_op, "Linea_Servicio", sel_linea)
            else:
                st.caption("📦 Sin columna de Línea de Servicio en el archivo.")
        with co2:
            filtro_incidencia = st.selectbox(
                "🔎 Filtro operativo de pedidos",
                ["Todos los pedidos", "Solo con reclamo", "Solo entregas tardías (OTD = 0)"],
            )
        with co3:
            rol_autorizado = st.toggle(
                "🔓 Vista auditor autorizado (Mostrar vendedor/cliente)",
                value=False,
                help="Simula el criterio de gobernanza de Camila: por defecto se anonimizan datos de vendedores y clientes.",
            )

    if d_op.empty:
        st.warning("No hay registros para la línea de servicio seleccionada.")
        return

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Distribución y dispersión del tiempo de entrega (Boxplot)")
            if necesita(d_op, ["Provincia", "Tiempo_Entrega"]):
                fig = px.box(
                    d_op.dropna(subset=["Tiempo_Entrega"]),
                    x="Provincia", y="Tiempo_Entrega", color="Provincia", points="outliers",
                )
                fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Tiempo de entrega")
                mostrar(fig, "p3_box")
                st.caption("Supera la limitación de mirar solo promedios: expone mediana, rango intercuartílico y valores atípicos.")
    with c2:
        with st.container(border=True):
            st.subheader("Entrega a tiempo (OTD %) por canal y servicio")
            if necesita(d_op, ["Canal", "Entrega_A_Tiempo"]):
                r = resumen_por(d_op, "Canal").sort_values("OTD_%")
                fig = px.bar(
                    r, x="OTD_%", y="Canal", orientation="h",
                    color="OTD_%", color_continuous_scale="RdYlGn", text_auto=".1f",
                )
                fig.add_vline(x=90, line_dash="dash", annotation_text="Meta 90%")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="% entregado a tiempo")
                mostrar(fig, "p3_otd_canal")

    if "Provincia" in d_op and "Tiempo_Entrega" in d_op:
        with st.container(border=True):
            st.subheader("Estadísticos de variabilidad logística por provincia")
            var = (
                d_op.groupby("Provincia")["Tiempo_Entrega"]
                .agg(Media="mean", Mediana="median", P90=lambda s: s.quantile(0.9), Desv_Est="std")
                .reset_index()
            )
            var["Coef_Var_%"] = (var["Desv_Est"] / var["Media"].replace(0, np.nan)) * 100
            st.dataframe(var.round(2).sort_values("Coef_Var_%", ascending=False), hide_index=True, **AN_DF)
            st.caption(
                "El Coeficiente de Variación (Desv_Est ÷ Media) identifica qué territorios sufren mayor inestabilidad en entregas. "
                "P90 indica el tiempo máximo dentro del cual se completa el 90 % de los pedidos."
            )

    # Explorador de pedidos con gobernanza de datos sensibles
    with st.container(border=True):
        st.subheader("🔎 Explorador trazable de pedidos individuales")
        sensibles = [c for c in d_op.columns if any(s in _limpiar(c) for s in SENSIBLES)]
        vista = d_op.copy()
        if filtro_incidencia == "Solo con reclamo" and "Hubo_Reclamo" in vista.columns:
            vista = vista[vista["Hubo_Reclamo"] == 1]
        elif filtro_incidencia.startswith("Solo entregas tardías") and "Entrega_A_Tiempo" in vista.columns:
            vista = vista[vista["Entrega_A_Tiempo"] == 0]

        if not rol_autorizado and sensibles:
            vista = vista.drop(columns=sensibles)
            st.caption(
                f"🔒 **Gobernanza activa (Vista estándar):** Se han ocultado las columnas `{', '.join(sensibles)}` "
                "para proteger datos personales y evitar rankings punitivos sin contexto."
            )
        elif rol_autorizado and sensibles:
            st.warning(
                f"🔓 **Modo Auditor Autorizado activo:** Visualizando columnas sensibles (`{', '.join(sensibles)}`). "
                "Uso exclusivo para auditoría operativa interna."
            )

        st.dataframe(vista, height=360, **AN_DF)
        st.download_button(
            "📥 Descargar vista actual (CSV)",
            data=vista.to_csv(index=False).encode("utf-8-sig"),
            file_name="reporte_logiandes_gobernado.csv",
            mime="text/csv",
        )


def pagina_ficha_y_gobernanza():
    """MÓDULO DOCUMENTAL: Cumple todos los requisitos conceptuales y metodológicos de la Prueba Práctica 2."""
    # 1. Descripción del problema y matriz de audiencias
    with st.container(border=True):
        st.subheader("1. Diagnóstico del Problema Empresarial y Necesidades por Audiencia")
        st.markdown(
            """
            **Problema empresarial en LogiAndes S.A.:** La empresa opera en **Quito, Guayaquil, Cuenca, Manta, Ambato y Loja** atendiendo a comercios medianos, pero su rápido crecimiento dejó la información fragmentada en hojas de cálculo aisladas y criterios semánticos contradictorios (Comercial reportaba *ventas brutas*, Finanzas *ventas netas*, Operaciones solo miraba *tiempos promedio* sin dispersión, Atención al Cliente contaba *reclamos absolutos* sin relativizar por volumen, y las *metas comerciales* estaban desconectadas de los periodos de facturación).
            """
        )
        audiencias_df = pd.DataFrame([
            {
                "Audiencia": "1. Gerencia General",
                "Necesidad de Información": "Monitorear si la empresa cumple sus objetivos estratégicos nacionales y territoriales.",
                "Respuesta en el Dashboard": "Vista Ejecutiva (Nivel 1) con 5 tarjetas KPI semaforizadas, cumplimiento de meta mensual y serie temporal.",
            },
            {
                "Audiencia": "2. Dirección Comercial",
                "Necesidad de Información": "Analizar el desempeño comercial filtrando por provincia, ciudad, línea de servicio y periodo.",
                "Respuesta en el Dashboard": "Filtros jerárquicos en 3 niveles, Sunburst y Mapa de calor Provincia × Canal, y seguimiento de metas.",
            },
            {
                "Audiencia": "3. Gerencia de Operaciones",
                "Necesidad de Información": "Identificar territorios y canales con retrasos o alta variabilidad en los tiempos de entrega.",
                "Respuesta en el Dashboard": "Detalle Operativo (Nivel 3) con Boxplots de tiempos, OTD (%), P90 y Coeficiente de Variación provincial.",
            },
            {
                "Audiencia": "4. Área Financiera",
                "Necesidad de Información": "Unificar el criterio de ingresos en Ventas Netas e incorporar el Margen Bruto real.",
                "Respuesta en el Dashboard": "Cálculo estandarizado de Ventas Netas (US$) y Margen Bruto (% y monto) en tarjetas y tablas comparativas.",
            },
            {
                "Audiencia": "5. Atención al Cliente",
                "Necesidad de Información": "Evaluar reclamos mediante tasas relativas para evitar comparaciones injustas entre provincias de distinto tamaño.",
                "Respuesta en el Dashboard": "KPI de Tasa de Reclamos por 1.000 pedidos y gráfico de dispersión Volumen de Pedidos vs. Tasa de Reclamos.",
            },
        ])
        st.dataframe(audiencias_df, hide_index=True, **AN_DF)
        st.caption(
            "**Estrategia de herramientas (Tensión 2 del caso):** Se utiliza **Streamlit** para este prototipo funcional ágil en Python; "
            "**Gradio** se reserva para consultas acotadas de resumen puntual; y **Power BI / Tableau** para la futura distribución corporativa con seguridad a nivel de fila (RLS)."
        )

    # 2. Ficha técnica completa de los 5 KPIs
    with st.container(border=True):
        st.subheader("2. Ficha Técnica Oficial de los 5 KPIs (Modelo Semántico Unificado)")
        st.dataframe(FICHA_TECNICA_KPIS, hide_index=True, **AN_DF)

    # 3. Reflexión sobre los 4 pilares exigidos en la Prueba Práctica 2
    with st.container(border=True):
        st.subheader("3. Marco de Gobernanza, Ética y Límites Interpretativos")
        r1, r2 = st.columns(2)
        with r1:
            st.markdown(
                """
                * **🎛️ Prevención de sobreinteractividad:** Colocar 10 filtros simultáneos (provincia, ciudad, canal, cliente, vendedor, estado, tipo de reclamo, etc.) fragmenta la muestra y produce fatiga cognitiva. Por ello, este dashboard aplica **revelación progresiva en 3 niveles**: filtros estratégicos arriba (Periodo, Provincia, Canal), filtro táctico de **Ciudad** en el Nivel 2 (Territorial) y filtro operativo de **Línea de Servicio** e incidencias en el Nivel 3 (Operativo).
                * **👁️ Mitigación de sesgos visuales:** Reportar conteos absolutos de reclamos sesga la atención hacia Quito y Guayaquil solo por su tamaño. El dashboard corrige este sesgo utilizando **tasas por cada 1.000 pedidos**, **Boxplots** (para no ocultar la dispersión detrás del promedio) y líneas de referencia explícitas en metas (100 % comercial, 90 % OTD y ≤ 25 reclamos/1.000).
                """
            )
        with r2:
            st.markdown(
                """
                * **🔒 Privacidad y gobernanza de datos:** En cumplimiento del principio de mínimo privilegio, las vistas Ejecutiva y Territorial presentan datos agregados por provincia y canal. En el Nivel Operativo, los identificadores de **vendedores, clientes o contactos** se enmascaran automáticamente por defecto y solo pueden habilitarse mediante el conmutador de *Auditor Autorizado*, evitando rankings punitivos sin contexto.
                * **📉 Límites interpretativos y fuentes externas (BCE / INEC):** Aunque se contraste la serie mensual de ventas con indicadores macroeconómicos del **Banco Central del Ecuador (BCE)** o del **INEC**, una caída simultánea muestra **asociación temporal, no causalidad**. Atribuir variaciones internas al entorno macro requiere aislar factores logísticos internos (como quiebres de ruta o caídas de OTD).
                """
            )

    # 4. Configuración técnica de columnas y calidad del dataset
    with st.expander("🧩 Configuración técnica de mapeo de columnas y auditoría de calidad del CSV"):
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

        cols_ok = [c for c in CAMPOS + ["AñoMes"] if c in base.columns]
        calidad = pd.DataFrame({
            "Columna estándar": cols_ok,
            "Valores nulos (%)": [round(base[c].isna().mean() * 100, 1) for c in cols_ok],
            "Cardinalidad (únicos)": [int(base[c].nunique(dropna=True)) for c in cols_ok],
        })
        st.dataframe(calidad, hide_index=True, **AN_DF)
        st.caption(f"Total registros cargados: **{len(base):,}** · Duplicados exactos: **{int(base.duplicated().sum()):,}**")


# ==========================================
# 8. BARRA DE NAVEGACIÓN PRINCIPAL FLUIDA
# ==========================================
tab_ej, tab_te, tab_op, tab_bi = st.tabs([
    "🏛️  \n1. Visión Ejecutiva",
    "🗺️  \n2. Diagnóstico Territorial",
    "🔧  \n3. Detalle Operativo",
    "📋  \n4. Ficha BI & Gobernanza",
])

with tab_ej:
    pagina_ejecutiva()
with tab_te:
    pagina_territorial()
with tab_op:
    pagina_operativa()
with tab_bi:
    pagina_ficha_y_gobernanza()

st.divider()
st.caption(
    "LogiAndes S.A. © 2026 · Solución de Business Intelligence en Streamlit · "
    "Visualización, Storytelling y Business Intelligence (Prueba Práctica 2)."
)