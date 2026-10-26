"""
LogiAndes S.A. · Solución de Business Intelligence Accionable (Prueba Práctica 2)
Diseño: Navegación Lateral por Áreas + LampLoginAnimation adaptada a Python/Streamlit

Ejecutar:  streamlit run LogiAndes.py
"""

import hashlib
import inspect
import io
import re
import time
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
    page_title="LogiAndes S.A. · BI Suite",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
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
# 2. ESTADO REACTIVO (Adaptación de LampLoginAnimation)
# ==========================================
for k_state, v_def in {
    "email": "camila.andrade@logiandes.ec",
    "password": "",
    "showPassword": False,
    "isLoading": False,
    "lampOn": True,
    "authenticated": False,
}.items():
    if k_state not in st.session_state:
        st.session_state[k_state] = v_def


# ==========================================
# 3. ESTILOS CSS (Lámpara reactiva + Sidebar + Pill Tabs)
# ==========================================
def inyectar_estilos_lamp(lamp_on: bool, color_acento: str = "#f43f5e"):
    lamp_beam_opacity = "1" if lamp_on else "0.08"
    lamp_fixture_glow = f"0 0 28px {color_acento}, 0 0 60px {color_acento}" if lamp_on else "none"
    lamp_cone_bg = (
        f"conic-gradient(from 180deg at 50% 0%, transparent 130deg, {color_acento}33 165deg, "
        f"{color_acento}66 180deg, {color_acento}33 195deg, transparent 230deg)"
        if lamp_on
        else "transparent"
    )
    card_border = "rgba(244, 63, 94, 0.28)" if lamp_on else "rgba(148, 163, 184, 0.16)"
    card_shadow = (
        "0 10px 30px -10px rgba(244, 63, 94, 0.14), 0 4px 12px rgba(0, 0, 0, 0.06)"
        if lamp_on
        else "0 4px 12px rgba(0, 0, 0, 0.04)"
    )

    st.markdown(
        f"""
        <style>
            .block-container {{
                padding-top: 1.1rem;
                padding-bottom: 2.5rem;
                max-width: 1460px;
            }}

            .lamp-wrapper {{
                position: relative;
                width: 100%;
                border-radius: 22px;
                background: linear-gradient(180deg, #090a0f 0%, #12131c 100%);
                border: 1px solid rgba(255, 255, 255, 0.09);
                padding: 1.55rem 1.8rem 1.35rem 1.8rem;
                margin-bottom: 1.1rem;
                overflow: hidden;
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.32);
                color: #f8fafc;
            }}

            .lamp-bulb {{
                width: 140px;
                height: 6px;
                background: {color_acento if lamp_on else '#3f3f46'};
                margin: -1.55rem auto 0.9rem auto;
                border-radius: 0 0 12px 12px;
                box-shadow: {lamp_fixture_glow};
                transition: all 0.45s ease;
                position: relative;
                z-index: 3;
            }}

            .lamp-cone {{
                position: absolute;
                top: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 680px;
                height: 260px;
                background: {lamp_cone_bg};
                filter: blur(22px);
                opacity: {lamp_beam_opacity};
                pointer-events: none;
                transition: all 0.5s cubic-bezier(0.22, 1, 0.36, 1);
                z-index: 1;
            }}

            .lamp-content {{
                position: relative;
                z-index: 2;
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 1rem;
            }}

            .lamp-title {{
                font-size: 1.55rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin: 0;
                color: #ffffff;
            }}

            .lamp-subtitle {{
                font-size: 0.86rem;
                color: #cbd5e1;
                margin-top: 0.2rem;
            }}

            .area-badge {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid {color_acento};
                color: #ffffff;
                padding: 0.42rem 1rem;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
                box-shadow: 0 0 16px {color_acento}44;
                backdrop-filter: blur(8px);
            }}

            section[data-testid="stSidebar"] > div {{
                padding-top: 1rem;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] {{
                gap: 0.42rem !important;
                width: 100% !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
                background: rgba(148, 163, 184, 0.08) !important;
                border: 1px solid rgba(148, 163, 184, 0.16) !important;
                border-radius: 12px !important;
                padding: 0.62rem 0.9rem !important;
                width: 100% !important;
                margin: 0 !important;
                cursor: pointer !important;
                transition: all 0.24s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
                display: flex !important;
                align-items: center !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
                display: none !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label p {{
                font-size: 0.88rem !important;
                font-weight: 600 !important;
                margin: 0 !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
                background: rgba(244, 63, 94, 0.12) !important;
                border-color: rgba(244, 63, 94, 0.45) !important;
                transform: translateX(4px) !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
                background: linear-gradient(135deg, #e11d48 0%, #be123c 100%) !important;
                border-color: #fda4af !important;
                color: #ffffff !important;
                box-shadow: 0 6px 18px rgba(225, 29, 72, 0.35) !important;
                transform: translateX(6px) !important;
            }}

            section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
                color: #ffffff !important;
                font-weight: 700 !important;
            }}

            div[data-testid="stTabs"] > div[role="tablist"] {{
                background: linear-gradient(145deg, #141419 0%, #0d0d11 100%) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                box-shadow: 0 14px 32px rgba(0, 0, 0, 0.28) !important;
                border-radius: 999px !important;
                padding: 0.42rem 0.6rem !important;
                gap: 0.45rem !important;
                width: fit-content !important;
                max-width: 100% !important;
                margin: 0.2rem auto 1.15rem auto !important;
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
                padding: 0.55rem 1.5rem !important;
                min-width: 145px !important;
                height: auto !important;
                border: 1px solid transparent !important;
                background: transparent !important;
                color: #9ca3af !important;
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
                background: rgba(255, 255, 255, 0.05) !important;
                color: #f8fafc !important;
                transform: translateY(-1px) !important;
            }}

            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
                background: radial-gradient(circle at 50% 0%, {color_acento}4d 0%, {color_acento}12 75%) !important;
                border-top: 2px solid {color_acento} !important;
                color: #ffffff !important;
                box-shadow: 0 -4px 16px {color_acento}44, inset 0 2px 8px {color_acento}33 !important;
                transform: scale(1.03) !important;
            }}

            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after {{
                content: "";
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: {color_acento};
                position: absolute;
                bottom: 5px;
                left: 50%;
                transform: translateX(-50%);
                box-shadow: 0 0 8px {color_acento};
            }}

            div[data-testid="stVerticalBlockBorderWrapper"] {{
                border-color: {card_border} !important;
                box-shadow: {card_shadow} !important;
                border-radius: 14px !important;
                transition: all 0.35s ease !important;
            }}

            .semaforo-pill {{
                display: inline-block;
                padding: 0.16rem 0.6rem;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 700;
                margin-top: 0.2rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# 4. MODELO DE DATOS
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
            except Exception as e:
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
# 5. ÁREAS EMPRESARIALES (BARRA LATERAL)
# ==========================================
AREAS_EMPRESA = {
    "🌐 Todas las áreas · Vista Integral": {
        "color": "#f43f5e",
        "rol": "Vista Consolidada Corporativa · Camila Andrade (BI Analyst)",
        "objetivo": "Integrar ventas netas, margen bruto, cumplimiento comercial, tasa de reclamos y tiempos de entrega en una sola fuente de verdad.",
        "kpis_foco": ["venta", "margen_pct", "cumplimiento", "reclamos", "otd"],
    },
    "🏢 Gerencia General": {
        "color": "#3b82f6",
        "rol": "Gerente General · Monitoreo Estratégico",
        "objetivo": "Supervisar si LogiAndes S.A. cumple sus metas mensuales por provincia y evaluar el desempeño general sin sesgos de volumen.",
        "kpis_foco": ["cumplimiento", "venta", "margen_pct", "otd"],
    },
    "📈 Dirección Comercial": {
        "color": "#f59e0b",
        "rol": "Directora Comercial · Desempeño Territorial y Canales",
        "objetivo": "Analizar ventas netas y alcance de cuotas filtrando por provincia, ciudad, canal de distribución y línea de servicio.",
        "kpis_foco": ["venta", "cumplimiento", "margen_pct"],
    },
    "🚚 Gerencia de Operaciones": {
        "color": "#10b981",
        "rol": "Gerente de Operaciones · Eficiencia y Variabilidad Logística",
        "objetivo": "Identificar provincias o canales con retrasos (bajo OTD) o alta dispersión en tiempos de entrega (P90 y Coeficiente de Variación).",
        "kpis_foco": ["otd", "reclamos"],
    },
    "💰 Área Financiera": {
        "color": "#8b5cf6",
        "rol": "Gerencia Financiera · Rentabilidad y Criterio Neto",
        "objetivo": "Garantizar que el seguimiento utilice Ventas Netas (no brutas) y monitorear el Margen Bruto real descontando costos logísticos.",
        "kpis_foco": ["venta", "margen_pct", "cumplimiento"],
    },
    "🎧 Atención al Cliente": {
        "color": "#ec4899",
        "rol": "Jefatura de Servicio al Cliente · Calidad de Entrega",
        "objetivo": "Evaluar la tasa estandarizada de reclamos por cada 1.000 pedidos para comparar justamente plazas grandes y medianas.",
        "kpis_foco": ["reclamos", "otd"],
    },
}

# ==========================================
# 6. BARRA LATERAL (Áreas + Lamp Login Gobernanza)
# ==========================================
CARPETA_DEFECTO = Path(__file__).resolve().parent

st.sidebar.markdown("### 🚚 LogiAndes S.A. · BI")
st.sidebar.caption("Selecciona el área empresarial para adaptar el enfoque del tablero:")

area_activa = st.sidebar.radio(
    "🏢 Áreas de la Empresa",
    list(AREAS_EMPRESA.keys()),
    index=0,
    label_visibility="collapsed",
    key="nav_area_lateral",
)
info_area = AREAS_EMPRESA[area_activa]

st.sidebar.divider()

with st.sidebar.expander("💡 Lamp Login · Gobernanza", expanded=False):
    st.caption("Control de iluminación (`lampOn`) y acceso seguro a datos sensibles:")

    st.session_state["lampOn"] = st.toggle(
        "Encender lámpara del Dashboard",
        value=st.session_state["lampOn"],
    )

    st.session_state["email"] = st.text_input(
        "Correo corporativo",
        value=st.session_state["email"],
        placeholder="usuario@logiandes.ec",
    )

    c_pass, c_eye = st.columns([3.8, 1.2], vertical_alignment="bottom")
    with c_eye:
        icono_ojo = "🙈" if st.session_state["showPassword"] else "👁️"
        if st.button(icono_ojo, key="btn_eye", help="Mostrar / ocultar contraseña", **AN_BTN):
            st.session_state["showPassword"] = not st.session_state["showPassword"]
            st.rerun()
    with c_pass:
        st.session_state["password"] = st.text_input(
            "Clave de auditor",
            value=st.session_state["password"],
            type="default" if st.session_state["showPassword"] else "password",
            placeholder="Contraseña…",
        )

    if st.button("⚡ Activar Modo Auditor", key="btn_lamp_submit", **AN_BTN):
        st.session_state["isLoading"] = True
        st.session_state["lampOn"] = True
        with st.spinner("Verificando permisos y encendiendo lámpara…"):
            time.sleep(0.8)
        st.session_state["isLoading"] = False
        st.session_state["authenticated"] = True
        st.rerun()

    if st.session_state["authenticated"]:
        st.success(f"🔓 Auditor activo: {st.session_state['email']}")
        if st.button("🔒 Cerrar sesión de auditor", key="btn_logout", **AN_BTN):
            st.session_state["authenticated"] = False
            st.rerun()
    else:
        st.caption("🔒 Vista estándar: datos sensibles anonimizados.")

inyectar_estilos_lamp(st.session_state["lampOn"], info_area["color"])

contenido, nombre_archivo = None, ""
with st.sidebar.expander("⚙️ Origen de datos (CSV)", expanded=True):
    carpeta = Path(st.text_input("Carpeta de datos", value=str(CARPETA_DEFECTO))).expanduser()
    subido = st.file_uploader("…o sube un CSV", type=["csv"], key="up_side")
    if subido is not None:
        contenido, nombre_archivo = subido.getvalue(), subido.name
    else:
        archivos = sorted(p.name for p in carpeta.glob("*.csv")) if carpeta.is_dir() else []
        if archivos:
            nombre_archivo = st.selectbox("Archivo", archivos)
            contenido = (carpeta / nombre_archivo).read_bytes()

# ==========================================
# 7. ENCABEZADO CON EFECTO DE LÁMPARA
# ==========================================
estado_luz_txt = "💡 Lámpara encendida" if st.session_state["lampOn"] else "🌑 Lámpara apagada"
st.markdown(
    f"""
    <div class='lamp-wrapper'>
        <div class='lamp-bulb'></div>
        <div class='lamp-cone'></div>
        <div class='lamp-content'>
            <div>
                <div class='lamp-title'>LogiAndes S.A. · Sistema de Inteligencia de Negocios</div>
                <div class='lamp-subtitle'>
                    <b>{info_area["rol"]}</b> — {info_area["objetivo"]}
                </div>
            </div>
            <div class='area-badge'>
                {area_activa} · {estado_luz_txt}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if contenido is None:
    st.warning(f"No encontré archivos CSV en `{carpeta}`. Sube el archivo de datos de LogiAndes aquí:")
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
    except Exception:
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
# 8. FILTROS GLOBALES DOSIFICADOS
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

if faltan_core:
    st.warning(
        "⚠️ Faltan columnas principales por asignar: **"
        + ", ".join(faltan_core)
        + "**. Ve a la pestaña **📋 4. Ficha BI & Gobernanza** para mapearlas."
    )

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
    f"📄 Archivo: **{nombre_archivo}** · Mostrando **{len(df_filtrado):,}** de {len(df_base):,} pedidos ({pct:.0%}) "
    + ("· Filtros activos: " + " | ".join(resumen_filtros) if resumen_filtros else "· Sin filtros globales")
)

if df_filtrado.empty:
    st.warning("Los filtros actuales no devuelven resultados. Pulsa **↺ Limpiar** o amplía la selección.")
    st.stop()

base = df_base
d = df_filtrado
HAY_FILTROS = len(d) != len(base)

# ==========================================
# 9. FUNCIONES DE CÁLCULO Y KPIS
# ==========================================
NOMBRE_VISIBLE = {"AñoMes": "Fecha"}


def necesita(x: pd.DataFrame, cols) -> bool:
    falta = [NOMBRE_VISIBLE.get(c, c) for c in cols if c not in x.columns]
    if falta:
        st.info(f"Para este gráfico falta: **{', '.join(falta)}**. Configúrala en **📋 4. Ficha BI & Gobernanza**.")
        return False
    return True


def mostrar(fig, clave: str, alto: int = 365):
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
    if valor is None or pd.isna(valor):
        return "⚪ Sin dato", "#64748b", "rgba(100,116,139,0.12)"
    if not menor_es_mejor:
        if valor >= verde:
            return "🟢 Óptimo (En meta)", "#16a34a", "rgba(22,163,74,0.14)"
        if valor >= amarillo:
            return "🟡 Alerta (Seguimiento)", "#d97706", "rgba(217,119,6,0.14)"
        return "🔴 Crítico (Acción)", "#dc2626", "rgba(220,38,38,0.14)"
    else:
        if valor <= verde:
            return "🟢 Óptimo (Controlado)", "#16a34a", "rgba(22,163,74,0.14)"
        if valor <= amarillo:
            return "🟡 Alerta (Atención)", "#d97706", "rgba(217,119,6,0.14)"
        return "🔴 Crítico (Excede umbral)", "#dc2626", "rgba(220,38,38,0.14)"


def tarjeta_kpi(col, clave_kpi, etiqueta, valor, fmt, ref=None, inverso=False, ayuda="", unidad="", sem=None):
    es_foco = clave_kpi in info_area["kpis_foco"]
    prefijo = "⭐ " if (es_foco and area_activa != "🌐 Todas las áreas · Vista Integral") else ""
    with col.container(border=True):
        if valor is None or pd.isna(valor):
            st.metric(prefijo + etiqueta, "N/D", help=ayuda or "Falta la columna necesaria para este KPI.")
            return
        delta = None
        if HAY_FILTROS and ref is not None and not pd.isna(ref):
            delta = f"{valor - ref:+,.1f}{unidad} vs. nacional"
        st.metric(
            prefijo + etiqueta,
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

FICHA_TECNICA_KPIS = pd.DataFrame([
    {
        "Nombre del Indicador": "1. Ventas Netas (US$)",
        "Área Principal": "Finanzas / Comercial",
        "Objetivo": "Cuantificar los ingresos reales efectivos descontando devoluciones e impuestos para alinear el criterio financiero y comercial.",
        "Fórmula": "Σ Venta_Neta",
        "Fuente": "ERP Facturación / CSV de pedidos (Venta_Neta)",
        "Frecuencia": "Mensual / Monitoreo continuo",
        "Meta": "≥ 100 % del presupuesto comercial asignado",
        "Umbral (Semáforo)": "🟢 ≥ 95 % | 🟡 85 % – 94.9 % | 🔴 < 85 %",
        "Interpretación": "Mide la tracción comercial real por provincia y canal; evita sobreestimar ingresos al excluir ventas brutas anuladas.",
    },
    {
        "Nombre del Indicador": "2. Margen Bruto (%)",
        "Área Principal": "Área Financiera",
        "Objetivo": "Monitorear la rentabilidad directa de las operaciones logísticas tras cubrir los costos directos de distribución.",
        "Fórmula": "(Σ Margen_Bruto ÷ Σ Venta_Neta) × 100",
        "Fuente": "Contabilidad Analítica / CSV (Margen_Bruto, Venta_Neta)",
        "Frecuencia": "Mensual",
        "Meta": "≥ 25.0 % sobre ventas netas",
        "Umbral (Semáforo)": "🟢 ≥ 25.0 % | 🟡 18.0 % – 24.9 % | 🔴 < 18.0 %",
        "Interpretación": "Detecta provincias o canales con alto volumen de ventas pero baja rentabilidad por sobrecostos de última milla.",
    },
    {
        "Nombre del Indicador": "3. Cumplimiento de Meta Comercial (%)",
        "Área Principal": "Gerencia General / Comercial",
        "Objetivo": "Evaluar el grado de alcance de los objetivos comerciales mensuales por provincia sin duplicar metas por pedido.",
        "Fórmula": "(Σ Venta_Neta ÷ Meta_Mensual_Provincia) × 100",
        "Fuente": "Presupuesto Comercial y Facturación (Venta_Neta, Meta_Venta)",
        "Frecuencia": "Mensual",
        "Meta": "≥ 100.0 %",
        "Umbral (Semáforo)": "🟢 ≥ 95.0 % | 🟡 85.0 % – 94.9 % | 🔴 < 85.0 %",
        "Interpretación": "Compara el desempeño real frente a la cuota esperada del periodo; corrige la desconexión entre hojas de metas y facturación.",
    },
    {
        "Nombre del Indicador": "4. Tasa de Reclamos por 1.000 Pedidos",
        "Área Principal": "Atención al Cliente",
        "Objetivo": "Estandarizar la medición de incidencias de servicio al cliente relativizando por el volumen operativo de cada territorio.",
        "Fórmula": "(Σ Hubo_Reclamo ÷ Total_Pedidos) × 1.000",
        "Fuente": "CRM Atención al Cliente / CSV (Hubo_Reclamo)",
        "Frecuencia": "Semanal / Mensual",
        "Meta": "≤ 25.0 reclamos por cada 1.000 pedidos",
        "Umbral (Semáforo)": "🟢 ≤ 25.0 | 🟡 25.1 – 50.0 | 🔴 > 50.0",
        "Interpretación": "Evita comparaciones injustas entre provincias de alto volumen (Quito/Guayaquil) y plazas medianas (Loja/Ambato).",
    },
    {
        "Nombre del Indicador": "5. Entrega a Tiempo – OTD (%)",
        "Área Principal": "Gerencia de Operaciones",
        "Objetivo": "Medir la confiabilidad y puntualidad del servicio logístico frente a la promesa de entrega pactada con los comercios.",
        "Fórmula": "(Pedidos con Entrega_A_Tiempo = 1 ÷ Total_Pedidos) × 100",
        "Fuente": "TMS Operaciones / CSV (Entrega_A_Tiempo)",
        "Frecuencia": "Diaria / Semanal / Mensual",
        "Meta": "≥ 90.0 % de pedidos entregados a tiempo",
        "Umbral (Semáforo)": "🟢 ≥ 90.0 % | 🟡 80.0 % – 89.9 % | 🔴 < 80.0 %",
        "Interpretación": "Refleja la salud operativa de las rutas urbanas y regionales; se complementa con el P90 y el coeficiente de variación.",
    },
])


# ==========================================
# 10. VISTAS DE NAVEGACIÓN SUPERIOR
# ==========================================
def render_tarjetas_superiores():
    t1, t2, t3, t4, t5 = st.columns(5)
    sem_cumpl = evaluar_umbral(K.get("cumplimiento"), 95.0, 85.0, menor_es_mejor=False)
    sem_margen = evaluar_umbral(K.get("margen_pct"), 25.0, 18.0, menor_es_mejor=False)
    sem_recl = evaluar_umbral(K.get("reclamos"), 25.0, 50.0, menor_es_mejor=True)
    sem_otd = evaluar_umbral(K.get("otd"), 90.0, 80.0, menor_es_mejor=False)

    tarjeta_kpi(
        t1, "venta", "Ventas netas", K.get("venta"), "${:,.0f}",
        ayuda="Ingresos netos efectivos (Σ Venta_Neta).",
        sem=sem_cumpl if K.get("cumplimiento") is not None else None,
    )
    tarjeta_kpi(
        t2, "margen_pct", "Margen bruto", K.get("margen_pct"), "{:.1f}%", K0.get("margen_pct"), unidad=" pp",
        ayuda=f"Σ Margen_Bruto ÷ Σ Venta_Neta. Monto: ${K.get('margen_monto', 0):,.0f}",
        sem=sem_margen,
    )
    tarjeta_kpi(
        t3, "cumplimiento", "Cumplimiento meta", K.get("cumplimiento"), "{:.1f}%", K0.get("cumplimiento"), unidad=" pp",
        ayuda="Ventas netas ÷ Meta comercial única por provincia y mes.",
        sem=sem_cumpl,
    )
    tarjeta_kpi(
        t4, "reclamos", "Reclamos / 1.000", K.get("reclamos"), "{:.1f}", K0.get("reclamos"), inverso=True,
        ayuda="Pedidos con reclamo por cada 1.000 pedidos.",
        sem=sem_recl,
    )
    tarjeta_kpi(
        t5, "otd", "Entrega a tiempo (OTD)", K.get("otd"), "{:.1f}%", K0.get("otd"), unidad=" pp",
        ayuda="Porcentaje de pedidos entregados dentro del SLA prometido.",
        sem=sem_otd,
    )


def pagina_ejecutiva():
    render_tarjetas_superiores()

    if "Provincia" in d and d["Provincia"].nunique() > 1:
        r = resumen_por(d, "Provincia")
        msgs = []
        if "Venta_Neta" in r and r["Venta_Neta"].sum() > 0:
            t = r.loc[r["Venta_Neta"].idxmax()]
            msgs.append(f"💰 **Líder en Ventas Netas:** **{t['Provincia']}** ({t['Venta_Neta'] / r['Venta_Neta'].sum():.0%} del total).")
        if "Margen_%" in r and r["Margen_%"].notna().any():
            t = r.loc[r["Margen_%"].idxmin()]
            msgs.append(f"📉 **Menor Margen Bruto:** **{t['Provincia']}** ({t['Margen_%']:.1f}%).")
        if "Cumplimiento_%" in r and r["Cumplimiento_%"].notna().any():
            t = r.loc[r["Cumplimiento_%"].idxmin()]
            msgs.append(f"🎯 **Brecha de Meta:** **{t['Provincia']}** ({t['Cumplimiento_%']:.1f}%).")
        if "Reclamos_x1000" in r and r["Reclamos_x1000"].notna().any():
            t = r.loc[r["Reclamos_x1000"].idxmax()]
            msgs.append(f"📣 **Mayor Tasa de Reclamos:** **{t['Provincia']}** ({t['Reclamos_x1000']:.1f} / 1.000 pedidos).")
        if "OTD_%" in r and r["OTD_%"].notna().any():
            t = r.loc[r["OTD_%"].idxmin()]
            msgs.append(f"⏱️ **Menor OTD:** **{t['Provincia']}** ({t['OTD_%']:.1f}%).")
        if msgs:
            st.info(f"**Lectura ejecutiva ({area_activa}):** " + " · ".join(msgs))
            st.caption(
                "⚠️ **Criterio de interpretación:** Estas asociaciones describen el comportamiento interno del dataset; "
                "no establecen causalidad directa frente a variables macroeconómicas externas (BCE / INEC)."
            )

    c1, c2 = st.columns([1, 1.3])
    with c1:
        with st.container(border=True):
            if area_activa == "💰 Área Financiera" and "Margen_Bruto" in d.columns:
                st.subheader("Margen bruto (%) por provincia (Foco Finanzas)")
                r = resumen_por(d, "Provincia").sort_values("Margen_%")
                fig = px.bar(
                    r, x="Margen_%", y="Provincia", orientation="h",
                    color="Margen_%", color_continuous_scale="Purples", text_auto=".1f",
                )
                fig.add_vline(x=25, line_dash="dash", annotation_text="Meta 25%")
                fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Margen Bruto (%)")
                mostrar(fig, "p1_margen_prov")
            else:
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
            st.subheader("Tasa de reclamos por 1.000 pedidos (Meta ≤ 25)")
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
    if not necesita(d, ["Provincia", "Canal"]):
        return

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
                    placeholder="Todas las ciudades",
                )
                d_terr = aplicar(d_terr, "Ciudad", sel_ciudad)
            else:
                st.caption("🏙️ Sin columna Ciudad en el dataset.")

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
                    "Modo de análisis territorial",
                    opciones_vista,
                    default=opciones_vista[0],
                    key="seg_terr",
                ) or opciones_vista[0]
            else:
                vista_terr = st.selectbox("Modo de análisis territorial", opciones_vista, key="rad_terr")
        with ct3:
            metrica = st.radio("Métrica", opciones_metrica, horizontal=True, key="met_terr")

    if d_terr.empty:
        st.warning("No hay pedidos para la ciudad seleccionada.")
        return

    def render_sunburst(alto=390):
        with st.container(border=True):
            st.subheader("🌞 Participación por Provincia y Canal")
            if metrica == "Ventas netas":
                fig = px.sunburst(d_terr[d_terr["Venta_Neta"] > 0], path=["Provincia", "Canal"], values="Venta_Neta")
            else:
                fig = px.sunburst(d_terr, path=["Provincia", "Canal"])
            fig.update_traces(textinfo="label+percent parent")
            mostrar(fig, "p2_sunburst", alto=alto)

    def render_calor(alto=390):
        with st.container(border=True):
            st.subheader("🔥 Matriz de Intensidad: Provincia × Canal")
            if metrica == "Ventas netas":
                piv = pd.crosstab(d_terr["Provincia"], d_terr["Canal"], values=d_terr["Venta_Neta"], aggfunc="sum").fillna(0)
            else:
                piv = pd.crosstab(d_terr["Provincia"], d_terr["Canal"])
            fig = px.imshow(piv, text_auto=".2s", aspect="auto", color_continuous_scale="Blues")
            fig.update_layout(xaxis_title=None, yaxis_title=None)
            mostrar(fig, "p2_calor", alto=alto)

    def render_scatter(alto=390):
        with st.container(border=True):
            st.subheader("🎯 Relación Volumen de Pedidos vs. Tasa de Reclamos")
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
                st.caption("Tamaño = Ventas netas · Color = OTD (%). Compara tasas relativas para evitar sesgo por tamaño.")

    def render_tabla():
        with st.container(border=True):
            st.subheader("📋 Resumen Comparativo por Provincia")
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
            render_sunburst(alto=360)
        with g2:
            render_calor(alto=360)
        render_scatter(alto=370)
        render_tabla()
    elif vista_terr == "🌞 Composición (Sunburst)":
        render_sunburst(alto=470)
    elif vista_terr == "🔥 Mapa de calor":
        render_calor(alto=440)
    elif vista_terr == "🎯 Pedidos vs. reclamos":
        render_scatter(alto=450)
    else:
        render_tabla()


def pagina_operativa():
    d_op = d.copy()

    with st.container(border=True):
        co1, co2 = st.columns([2.2, 1.6])
        with co1:
            if "Linea_Servicio" in d_op.columns:
                lineas_disp = sorted(d_op["Linea_Servicio"].dropna().unique())
                sel_linea = st.multiselect(
                    "📦 Filtro de Nivel 3 · Línea de servicio logístico",
                    lineas_disp,
                    key="f_linea",
                    placeholder="Todas las líneas de servicio",
                )
                d_op = aplicar(d_op, "Linea_Servicio", sel_linea)
            else:
                st.caption("📦 Sin columna Línea de Servicio en este archivo.")
        with co2:
            filtro_incidencia = st.selectbox(
                "🔎 Filtro rápido de incidencias operativas",
                ["Todos los pedidos", "Solo con reclamo", "Solo entregas tardías (OTD = 0)"],
            )

    if d_op.empty:
        st.warning("No hay registros para la línea de servicio seleccionada.")
        return

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Distribución del tiempo de entrega (Boxplot)")
            if necesita(d_op, ["Provincia", "Tiempo_Entrega"]):
                fig = px.box(
                    d_op.dropna(subset=["Tiempo_Entrega"]),
                    x="Provincia", y="Tiempo_Entrega", color="Provincia", points="outliers",
                )
                fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Tiempo de entrega")
                mostrar(fig, "p3_box")
    with c2:
        with st.container(border=True):
            st.subheader("Entrega a tiempo (OTD %) por canal")
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
            st.subheader("Variabilidad logística por provincia (Media, Mediana, P90 y Coef. Variación)")
            var = (
                d_op.groupby("Provincia")["Tiempo_Entrega"]
                .agg(Media="mean", Mediana="median", P90=lambda s: s.quantile(0.9), Desv_Est="std")
                .reset_index()
            )
            var["Coef_Var_%"] = (var["Desv_Est"] / var["Media"].replace(0, np.nan)) * 100
            st.dataframe(var.round(2).sort_values("Coef_Var_%", ascending=False), hide_index=True, **AN_DF)

    with st.container(border=True):
        st.subheader("🔎 Explorador de pedidos individuales (Integrado con Lamp Login Gobernanza)")
        sensibles = [c for c in d_op.columns if any(s in _limpiar(c) for s in SENSIBLES)]
        vista = d_op.copy()
        if filtro_incidencia == "Solo con reclamo" and "Hubo_Reclamo" in vista.columns:
            vista = vista[vista["Hubo_Reclamo"] == 1]
        elif filtro_incidencia.startswith("Solo entregas tardías") and "Entrega_A_Tiempo" in vista.columns:
            vista = vista[vista["Entrega_A_Tiempo"] == 0]

        if not st.session_state["authenticated"] and sensibles:
            vista = vista.drop(columns=sensibles)
            st.caption(
                f"🔒 **Gobernanza activa:** Las columnas sensibles (`{', '.join(sensibles)}`) están ocultas. "
                "Para desbloquearlas, usa el módulo **💡 Lamp Login · Gobernanza** en la barra lateral izquierda."
            )
        elif st.session_state["authenticated"] and sensibles:
            st.success(
                f"🔓 **Modo Auditor Autorizado ({st.session_state['email']}):** Visualizando columnas protegidas (`{', '.join(sensibles)}`)."
            )

        st.dataframe(vista, height=350, **AN_DF)
        st.download_button(
            "📥 Descargar vista actual (CSV)",
            data=vista.to_csv(index=False).encode("utf-8-sig"),
            file_name="reporte_logiandes_gobernado.csv",
            mime="text/csv",
        )


def pagina_ficha_y_gobernanza():
    with st.container(border=True):
        st.subheader("1. Problema Empresarial y Necesidades de las 5 Áreas (Navegables en el Panel Izquierdo)")
        st.markdown(
            """
            LogiAndes S.A. opera en **Quito, Guayaquil, Cuenca, Manta, Ambato y Loja**. Antes de esta solución BI, cada área manejaba cifras aisladas: Comercial reportaba *ventas brutas*, Finanzas *ventas netas*, Operaciones miraba *tiempos promedio* ocultando la variabilidad, Atención al Cliente contaba *reclamos absolutos* sin relativizar por volumen, y las *metas* no coincidían con los periodos de facturación.
            """
        )
        resumen_areas = pd.DataFrame([
            {"Área (Pestaña Lateral)": k, "Rol / Audiencia": v["rol"], "Necesidad y Solución BI": v["objetivo"]}
            for k, v in AREAS_EMPRESA.items()
            if k != "🌐 Todas las áreas · Vista Integral"
        ])
        st.dataframe(resumen_areas, hide_index=True, **AN_DF)

    with st.container(border=True):
        st.subheader("2. Ficha Técnica Oficial de los 5 KPIs")
        st.dataframe(FICHA_TECNICA_KPIS, hide_index=True, **AN_DF)

    with st.container(border=True):
        st.subheader("3. Reflexión sobre Interactividad, Sesgos, Privacidad y Límites Interpretativos")
        r1, r2 = st.columns(2)
        with r1:
            st.markdown(
                """
                * **🎛️ Riesgos de sobreinteractividad:** Se evitó saturar la pantalla con múltiples filtros simultáneos organizando la exploración en **pestañas laterales por área** y **3 niveles jerárquicos superiores** (filtros globales de Periodo/Provincia/Canal arriba; Ciudad en el Nivel 2; Línea de servicio en el Nivel 3).
                * **👁️ Sesgos visuales:** Se reemplazaron los conteos brutos de reclamos por la **tasa por cada 1.000 pedidos** y los promedios simples de entrega por **Boxplots, P90 y Coeficiente de Variación**.
                """
            )
        with r2:
            st.markdown(
                """
                * **🔒 Privacidad y gobernanza (`LampLoginAnimation`):** Los identificadores de vendedores y clientes permanecen ocultos por defecto y solo se habilitan cuando un auditor inicia sesión en el panel lateral **💡 Lamp Login · Gobernanza**.
                * **📉 Límites interpretativos (BCE / INEC):** Las caídas o picos en la serie temporal muestran asociaciones internas; cruzar estos datos con indicadores macroeconómicos del **BCE** o **INEC** aporta contexto, pero no prueba causalidad sin un análisis adicional.
                """
            )

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


# ==========================================
# 11. NAVEGACIÓN SUPERIOR FLUIDA
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
    f"LogiAndes S.A. © 2026 · Vista activa: {area_activa} · "
    "Prototipo BI en Streamlit con LampLoginAnimation UI & Navegación Lateral por Áreas."
)