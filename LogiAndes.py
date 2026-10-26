"""
LogiAndes S.A. · Dashboard de Business Intelligence (prototipo en Streamlit)

Ejecutar:  streamlit run LogiAndes.py
Datos:     cualquier CSV en la misma carpeta que este script,
           o súbelo desde la barra lateral (⚙️ Datos y definiciones).
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
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="LogiAndes S.A. · BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Colores que se leen bien tanto en tema claro como oscuro.
st.markdown(
    """
<style>
    .main-title { font-size: 2.1rem; font-weight: 700; color: #3B82F6; margin-bottom: .2rem; }
    .sub-title  { font-size: 1rem; opacity: .75; margin-bottom: 1.2rem; }
</style>
""",
    unsafe_allow_html=True,
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
# 2. MODELO DE DATOS: LECTURA, ALIAS Y LIMPIEZA
# ==========================================
CAMPOS_CORE = ["Provincia", "Canal", "Venta_Neta", "Margen_Bruto", "Hubo_Reclamo", "Entrega_A_Tiempo"]
CAMPOS_OPCIONALES = ["Fecha", "Ciudad", "Linea_Servicio", "Tiempo_Entrega", "Meta_Venta"]
CAMPOS = CAMPOS_CORE + CAMPOS_OPCIONALES

# Nombres alternativos (ya normalizados: minúsculas, sin tildes, con guion bajo).
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
    "Tiempo_Entrega": ["tiempo_entrega", "tiempo_de_entrega", "dias_entrega", "dias_de_entrega",
                       "horas_entrega", "lead_time", "delivery_time"],
    "Meta_Venta": ["meta_venta", "meta_ventas", "meta", "meta_mensual", "meta_comercial", "target"],
}

# Columnas que se ocultan en la tabla de detalle y en la descarga (gobernanza).
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
                continue  # evita columnas duplicadas
            renombrar[col] = estandar
            usados.add(estandar)
            break
    return df.rename(columns=renombrar)


def a_numero(s: pd.Series) -> pd.Series:
    """'$1,234.50', '1.234,50' o 'US$ 90' → número."""
    if pd.api.types.is_numeric_dtype(s):
        return s
    t = s.astype(str).str.replace(r"[^\d,.\-]", "", regex=True)
    if t.str.contains(r",\d{1,2}$").mean() > 0.5:  # formato europeo: 1.234,50
        t = t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:  # formato anglosajón: 1,234.50
        t = t.str.replace(",", "", regex=False)
    return pd.to_numeric(t, errors="coerce")


def a_binario(s: pd.Series) -> pd.Series:
    """Sí/No, True/False, 1/0 → 1/0."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype(int)
    if pd.api.types.is_numeric_dtype(s):
        return (pd.to_numeric(s, errors="coerce").fillna(0) > 0).astype(int)
    t = s.astype(str).str.strip().str.lower()
    positivos = ["si", "sí", "s", "1", "true", "yes", "y", "verdadero", "a tiempo",
                 "entregado a tiempo", "on time", "ok", "cumple", "con reclamo"]
    return t.isin(positivos).astype(int)


def a_fecha(s: pd.Series) -> pd.Series:
    """Detecta dd/mm/aaaa (formato local) para no confundir día y mes."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    t = s.astype(str).str.strip()
    dayfirst = t.str.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}").mean() > 0.5
    return pd.to_datetime(t, errors="coerce", dayfirst=dayfirst)


@st.cache_data(show_spinner=False)
def preparar_datos(_df: pd.DataFrame, huella: str, mapeo: tuple, margen_es_pct: bool) -> pd.DataFrame:
    """Aplica el mapeo manual, convierte tipos y crea AñoMes. `huella` identifica el archivo en la caché."""
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
# 3. BARRA LATERAL: ORIGEN DE DATOS, NAVEGACIÓN Y FILTROS
# ==========================================
CARPETA_DEFECTO = Path(__file__).resolve().parent

st.sidebar.title("🚚 LogiAndes S.A.")
st.sidebar.caption("Módulo de Inteligencia de Negocios")

# Contenedores creados en orden visual; se rellenan en el orden que necesita el código.
caja_nav = st.sidebar.container()
caja_filtros = st.sidebar.container()
exp_datos = st.sidebar.expander("⚙️ Datos y definiciones")

# --- 3.1 Origen de datos ---
contenido, nombre_archivo = None, ""
with exp_datos:
    carpeta = Path(st.text_input("Carpeta de datos", value=str(CARPETA_DEFECTO))).expanduser()
    subido = st.file_uploader("…o sube un CSV", type=["csv"])
    if subido is not None:
        contenido, nombre_archivo = subido.getvalue(), subido.name
    else:
        archivos = sorted(p.name for p in carpeta.glob("*.csv")) if carpeta.is_dir() else []
        if archivos:
            nombre_archivo = st.selectbox("Archivo", archivos)
            contenido = (carpeta / nombre_archivo).read_bytes()

if contenido is None:
    st.markdown("<div class='main-title'>LogiAndes S.A.</div>", unsafe_allow_html=True)
    st.warning(
        f"No encontré archivos CSV en `{carpeta}`.\n\n"
        "Copia tu CSV a esa carpeta, cambia la ruta o súbelo desde **⚙️ Datos y definiciones** (barra lateral)."
    )
    st.stop()

try:
    df_raw = cargar_csv(contenido)
except ValueError as e:
    st.error(str(e))
    st.stop()

if df_raw.empty:
    st.warning("El archivo seleccionado está vacío.")
    st.stop()

huella = hashlib.md5(contenido).hexdigest()

# --- 3.2 Mapeo de columnas y definiciones ---
with exp_datos:
    st.caption(f"📄 {nombre_archivo} · {len(df_raw):,} filas · {df_raw.shape[1]} columnas")

    mapeo = {}
    faltan = [c for c in CAMPOS if c not in df_raw.columns]
    if faltan:
        st.markdown("**Columnas no reconocidas**")
        st.caption("Indica qué columna de tu CSV corresponde a cada campo. Las opcionales pueden quedar sin asignar.")
        for campo in faltan:
            etiqueta = campo + ("" if campo in CAMPOS_CORE else " (opcional)")
            elegido = st.selectbox(etiqueta, ["(ninguna)"] + list(df_raw.columns), key=f"map_{huella[:8]}_{campo}")
            if elegido != "(ninguna)":
                mapeo[campo] = elegido

    disponibles = set(df_raw.columns) | set(mapeo)

    # ¿Margen_Bruto es un monto o un porcentaje? Se sugiere según los valores.
    margen_es_pct = False
    if "Margen_Bruto" in disponibles:
        sugiere_pct = False
        try:
            m = a_numero(df_raw[mapeo.get("Margen_Bruto", "Margen_Bruto")]).dropna()
            v = a_numero(df_raw[mapeo.get("Venta_Neta", "Venta_Neta")]).dropna()
            sugiere_pct = len(m) > 0 and len(v) > 0 and m.between(0, 100).all() and v.median() > 100
        except Exception:  # noqa: BLE001
            pass
        opcion = st.radio("Margen_Bruto está expresado como…", ["Monto (US$)", "Porcentaje (%)"],
                          index=1 if sugiere_pct else 0, key=f"margen_{huella[:8]}")
        margen_es_pct = opcion == "Porcentaje (%)"

    META_REPETIDA = True
    if "Meta_Venta" in disponibles:
        opcion = st.radio("Meta_Venta se registra…",
                          ["Repetida en cada pedido (provincia y mes)", "Un valor por pedido (se suma)"],
                          key=f"meta_{huella[:8]}")
        META_REPETIDA = opcion.startswith("Repetida")

    st.caption("Columnas detectadas: " + ", ".join(df_raw.columns))

df_base = preparar_datos(df_raw, huella, tuple(sorted(mapeo.items())), margen_es_pct)

faltan_core = [c for c in CAMPOS_CORE if c not in df_base.columns]
if faltan_core:
    st.warning(
        f"⚠️ Faltan columnas obligatorias: **{', '.join(faltan_core)}**. "
        "Asígnalas en la barra lateral → **⚙️ Datos y definiciones**. Mientras tanto verás solo lo que se puede calcular."
    )

# --- 3.3 Navegación ---
ETIQUETAS_NIVEL = {
    "1. Visión Ejecutiva (Nacional)": "🏛️  Visión Ejecutiva",
    "2. Diagnóstico Territorial": "🗺️  Diagnóstico Territorial",
    "3. Detalle Operativo": "🔧  Detalle Operativo",
}
NIVEL_1, NIVEL_2, NIVEL_3 = list(ETIQUETAS_NIVEL)

with caja_nav:
    st.markdown("### 🧭 Navegación")
    nivel_pagina = st.radio(
        "Nivel de análisis",
        list(ETIQUETAS_NIVEL),
        format_func=lambda x: ETIQUETAS_NIVEL[x],
        label_visibility="collapsed",
    )

# --- 3.4 Filtros ---
CLAVES_FILTROS = ["f_preset", "f_rango", "f_prov", "f_ciudad", "f_canal", "f_linea"]


def reiniciar_filtros():
    for k in CLAVES_FILTROS:
        st.session_state.pop(k, None)


def filtro_multi(df: pd.DataFrame, col: str, etiqueta: str, clave: str) -> pd.DataFrame:
    """Multiselect en cascada: vacío = todas las opciones."""
    if col not in df.columns:
        return df
    opciones = sorted(df[col].dropna().unique())
    st.session_state[clave] = [v for v in st.session_state.get(clave, []) if v in opciones]
    seleccion = st.multiselect(etiqueta, opciones, key=clave, placeholder="Todas")
    return df[df[col].isin(seleccion)] if seleccion else df


df_filtrado = df_base.copy()

with caja_filtros:
    st.divider()
    c_tit, c_btn = st.columns([1.4, 1])
    c_tit.markdown("### 🎛️ Filtros")
    c_btn.button("↺ Limpiar", on_click=reiniciar_filtros, **AN_BTN)

    if "Fecha" in df_filtrado.columns and df_filtrado["Fecha"].notna().any():
        f_min, f_max = df_filtrado["Fecha"].min().date(), df_filtrado["Fecha"].max().date()
        with st.expander("📅 Periodo", expanded=True):
            preset = st.selectbox(
                "Atajo",
                ["Todo el periodo", "Últimos 30 días", "Últimos 90 días", "Personalizado"],
                key="f_preset",
            )
            if preset == "Últimos 30 días":
                f_ini, f_fin = max(f_min, f_max - timedelta(days=29)), f_max
            elif preset == "Últimos 90 días":
                f_ini, f_fin = max(f_min, f_max - timedelta(days=89)), f_max
            elif preset == "Personalizado":
                rango = st.date_input("Rango", value=(f_min, f_max), min_value=f_min, max_value=f_max, key="f_rango")
                f_ini, f_fin = rango if isinstance(rango, (tuple, list)) and len(rango) == 2 else (f_min, f_max)
            else:
                f_ini, f_fin = f_min, f_max
            st.caption(f"📆 {f_ini:%d/%m/%Y} → {f_fin:%d/%m/%Y}")
        fechas = df_filtrado["Fecha"].dt.date
        df_filtrado = df_filtrado[(fechas >= f_ini) & (fechas <= f_fin)]

    with st.expander("📍 Territorio", expanded=True):
        df_filtrado = filtro_multi(df_filtrado, "Provincia", "Provincia", "f_prov")
        df_filtrado = filtro_multi(df_filtrado, "Ciudad", "Ciudad", "f_ciudad")

    with st.expander("🛒 Canal y servicio", expanded=False):
        df_filtrado = filtro_multi(df_filtrado, "Canal", "Canal", "f_canal")
        df_filtrado = filtro_multi(df_filtrado, "Linea_Servicio", "Línea de servicio", "f_linea")

    pct = len(df_filtrado) / max(len(df_base), 1)
    st.progress(pct, text=f"{len(df_filtrado):,} de {len(df_base):,} pedidos ({pct:.0%})")

if df_filtrado.empty:
    st.warning("⚠️ Los filtros actuales no devuelven resultados. Pulsa **↺ Limpiar** o amplía la selección.")
    st.stop()

base = df_base      # referencia: todos los datos
d = df_filtrado     # lo que ve el usuario
HAY_FILTROS = len(d) != len(base)

# ==========================================
# 4. FUNCIONES DE CÁLCULO Y PRESENTACIÓN
# ==========================================
NOMBRE_VISIBLE = {"AñoMes": "Fecha"}


def encabezado(titulo: str, subtitulo: str):
    st.markdown(f"<div class='main-title'>{titulo}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>{subtitulo}</div>", unsafe_allow_html=True)


def necesita(x: pd.DataFrame, cols) -> bool:
    falta = [NOMBRE_VISIBLE.get(c, c) for c in cols if c not in x.columns]
    if falta:
        st.info(f"Para este gráfico falta: **{', '.join(falta)}**. Asígnala en la barra lateral → ⚙️ Datos y definiciones.")
        return False
    return True


def mostrar(fig, clave: str, alto: int = 380):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10), legend_title_text="")
    st.plotly_chart(fig, key=clave, config={"displaylogo": False}, **AN_PLOT)


def meta_por(x: pd.DataFrame, por=None):
    """Meta de ventas agregada. Si la meta se repite en cada pedido, se cuenta una vez por provincia y mes."""
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
        st.metric(etiqueta, fmt.format(valor), delta=delta,
                  delta_color="inverse" if inverso else "normal", help=ayuda or None)


K = calcular_kpis(d)
K0 = calcular_kpis(base)

DEFINICIONES = pd.DataFrame([
    {"KPI": "Ventas netas", "Fórmula": "Σ Venta_Neta",
     "Fuente": "CSV de pedidos", "Responsable (propuesto)": "Finanzas"},
    {"KPI": "Margen bruto (%)", "Fórmula": "Σ Margen_Bruto ÷ Σ Venta_Neta × 100",
     "Fuente": "CSV de pedidos", "Responsable (propuesto)": "Finanzas"},
    {"KPI": "Cumplimiento de meta (%)", "Fórmula": "Σ Venta_Neta ÷ Meta del periodo × 100 (meta contada una vez por provincia y mes)",
     "Fuente": "Meta_Venta", "Responsable (propuesto)": "Dirección comercial"},
    {"KPI": "Reclamos por 1.000 pedidos", "Fórmula": "Pedidos con reclamo ÷ pedidos totales × 1.000",
     "Fuente": "Hubo_Reclamo", "Responsable (propuesto)": "Atención al cliente"},
    {"KPI": "Entrega a tiempo – OTD (%)", "Fórmula": "Pedidos entregados a tiempo ÷ pedidos totales × 100",
     "Fuente": "Entrega_A_Tiempo", "Responsable (propuesto)": "Operaciones"},
])

# ==========================================
# 5. PÁGINA 1: VISIÓN EJECUTIVA
# ==========================================
if nivel_pagina == NIVEL_1:
    encabezado("Visión Ejecutiva Nacional", "Monitoreo macro de ventas, márgenes y desempeño territorial.")

    t1, t2, t3, t4, t5 = st.columns(5)
    tarjeta(t1, "Ventas netas", K.get("venta"), "${:,.0f}", ayuda="Suma de Venta_Neta")
    tarjeta(t2, "Margen bruto", K.get("margen_pct"), "{:.1f}%", K0.get("margen_pct"), unidad=" pp",
            ayuda=f"Margen bruto ÷ ventas netas. Monto: ${K.get('margen_monto', 0):,.0f}")
    tarjeta(t3, "Cumplimiento de meta", K.get("cumplimiento"), "{:.1f}%", K0.get("cumplimiento"), unidad=" pp",
            ayuda="Ventas netas ÷ Meta_Venta. Requiere la columna Meta_Venta.")
    tarjeta(t4, "Reclamos por 1.000 pedidos", K.get("reclamos"), "{:.1f}", K0.get("reclamos"), inverso=True,
            ayuda="Pedidos con reclamo ÷ total de pedidos × 1.000")
    tarjeta(t5, "Entrega a tiempo (OTD)", K.get("otd"), "{:.1f}%", K0.get("otd"), unidad=" pp",
            ayuda="Pedidos entregados a tiempo ÷ total de pedidos")

    # Lectura automática
    if "Provincia" in d and d["Provincia"].nunique() > 1:
        r = resumen_por(d, "Provincia")
        msgs = []
        if "Venta_Neta" in r and r["Venta_Neta"].sum() > 0:
            t = r.loc[r["Venta_Neta"].idxmax()]
            msgs.append(f"💰 **{t['Provincia']}** concentra el {t['Venta_Neta'] / r['Venta_Neta'].sum():.0%} de las ventas netas.")
        if "Cumplimiento_%" in r and r["Cumplimiento_%"].notna().any():
            t = r.loc[r["Cumplimiento_%"].idxmin()]
            msgs.append(f"🎯 Menor cumplimiento de meta: **{t['Provincia']}** ({t['Cumplimiento_%']:.1f}%).")
        if "Reclamos_x1000" in r and r["Reclamos_x1000"].notna().any():
            t = r.loc[r["Reclamos_x1000"].idxmax()]
            msgs.append(f"📣 Mayor tasa de reclamos: **{t['Provincia']}** ({t['Reclamos_x1000']:.1f} por cada mil pedidos).")
        if "OTD_%" in r and r["OTD_%"].notna().any():
            t = r.loc[r["OTD_%"].idxmin()]
            msgs.append(f"⏱️ Menor entrega a tiempo: **{t['Provincia']}** ({t['OTD_%']:.1f}%).")
        if msgs:
            st.info("\n\n".join(msgs))
            st.caption("Estas lecturas describen asociaciones en los datos; no establecen causas sin un análisis adicional.")

    st.divider()

    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.subheader("Ventas netas por provincia")
        if necesita(d, ["Provincia", "Venta_Neta"]):
            r = resumen_por(d, "Provincia").sort_values("Venta_Neta")
            fig = px.bar(r, x="Venta_Neta", y="Provincia", orientation="h", color="Venta_Neta",
                         color_continuous_scale="Blues", text_auto=".3s")
            fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Ventas netas (US$)")
            mostrar(fig, "p1_ventas_prov")
    with c2:
        st.subheader("Evolución mensual de ventas netas")
        if necesita(d, ["AñoMes", "Venta_Neta"]):
            m = d.groupby("AñoMes", as_index=False)["Venta_Neta"].sum().sort_values("AñoMes")
            fig = px.line(m, x="AñoMes", y="Venta_Neta", markers=True)
            fig.update_traces(name="Ventas netas", showlegend=True)
            meta_m = meta_por(d, ["AñoMes"])
            if meta_m is not None:
                fig.add_trace(go.Scatter(x=m["AñoMes"], y=meta_m.reindex(m["AñoMes"]).values, name="Meta",
                                         mode="lines", line=dict(dash="dash", color="#F59E0B")))
            fig.update_layout(xaxis_title=None, yaxis_title="US$")
            mostrar(fig, "p1_serie")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Reclamos por 1.000 pedidos")
        if necesita(d, ["Provincia", "Hubo_Reclamo"]):
            r = resumen_por(d, "Provincia").sort_values("Reclamos_x1000")
            fig = px.bar(r, x="Reclamos_x1000", y="Provincia", orientation="h", color="Reclamos_x1000",
                         color_continuous_scale="Reds", text_auto=".1f")
            fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Reclamos / 1.000 pedidos")
            mostrar(fig, "p1_reclamos")
    with c4:
        st.subheader("Entrega a tiempo por provincia")
        if necesita(d, ["Provincia", "Entrega_A_Tiempo"]):
            meta_otd = st.number_input("Meta OTD (%) · supuesto editable", 0, 100, 90, key="meta_otd")
            r = resumen_por(d, "Provincia").sort_values("OTD_%")
            fig = px.bar(r, x="OTD_%", y="Provincia", orientation="h", color="OTD_%",
                         color_continuous_scale="RdYlGn", text_auto=".1f")
            fig.add_vline(x=meta_otd, line_dash="dash", annotation_text=f"Meta {meta_otd}%")
            fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="% entregado a tiempo")
            mostrar(fig, "p1_otd")

    if "Meta_Venta" in d and "Provincia" in d and "Venta_Neta" in d:
        st.subheader("Cumplimiento de meta por provincia")
        r = resumen_por(d, "Provincia").dropna(subset=["Cumplimiento_%"]).sort_values("Cumplimiento_%")
        if r.empty:
            st.info("No hay metas válidas para calcular el cumplimiento.")
        else:
            fig = px.bar(r, x="Cumplimiento_%", y="Provincia", orientation="h", color="Cumplimiento_%",
                         color_continuous_scale="RdYlGn", text_auto=".1f")
            fig.add_vline(x=100, line_dash="dash", annotation_text="Meta 100%")
            fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Ventas netas ÷ meta (%)")
            mostrar(fig, "p1_cumplimiento", alto=340)

    with st.expander("📖 Definición de los KPIs"):
        st.dataframe(DEFINICIONES, hide_index=True, **AN_DF)
        st.caption("Los responsables son una propuesta basada en las áreas del caso; deben validarse con la gerencia.")

# ==========================================
# 6. PÁGINA 2: DIAGNÓSTICO TERRITORIAL
# ==========================================
elif nivel_pagina == NIVEL_2:
    encabezado("Diagnóstico Territorial y Canales", "Cómo se reparte el desempeño entre provincias y canales.")

    if necesita(d, ["Provincia", "Canal"]):
        tab_comp, tab_calor, tab_disp, tab_tabla = st.tabs(
            ["🌞 Composición", "🔥 Mapa de calor", "🎯 Pedidos vs. reclamos", "📋 Tabla comparativa"])

        opciones = ["Pedidos"] + (["Ventas netas"] if "Venta_Neta" in d else [])

        with tab_comp:
            metrica = st.radio("Medir por", opciones, horizontal=True, key="metrica_comp")
            if metrica == "Ventas netas":
                dd = d[d["Venta_Neta"] > 0]
                fig = px.sunburst(dd, path=["Provincia", "Canal"], values="Venta_Neta")
            else:
                fig = px.sunburst(d, path=["Provincia", "Canal"])
            fig.update_traces(textinfo="label+percent parent")
            mostrar(fig, "p2_sunburst", alto=480)

        with tab_calor:
            metrica2 = st.radio("Medir por", opciones, horizontal=True, key="metrica_calor")
            if metrica2 == "Ventas netas":
                piv = pd.crosstab(d["Provincia"], d["Canal"], values=d["Venta_Neta"], aggfunc="sum").fillna(0)
            else:
                piv = pd.crosstab(d["Provincia"], d["Canal"])
            fig = px.imshow(piv, text_auto=".2s", aspect="auto", color_continuous_scale="Blues")
            fig.update_layout(xaxis_title=None, yaxis_title=None)
            mostrar(fig, "p2_calor", alto=420)

        with tab_disp:
            if necesita(d, ["Hubo_Reclamo"]):
                r = resumen_por(d, "Provincia")
                tamano = r["Venta_Neta"].fillna(0).clip(lower=0) if "Venta_Neta" in r else None
                fig = px.scatter(r, x="Pedidos", y="Reclamos_x1000", size=tamano,
                                 color="OTD_%" if "OTD_%" in r else None,
                                 text="Provincia", color_continuous_scale="RdYlGn", size_max=45)
                fig.update_traces(textposition="top center")
                fig.update_layout(xaxis_title="Pedidos", yaxis_title="Reclamos por 1.000 pedidos")
                mostrar(fig, "p2_scatter", alto=450)
                st.caption("Cada burbuja es una provincia: tamaño = ventas netas, color = entrega a tiempo. "
                           "Compara tasas, no conteos. Una asociación visible aquí no demuestra causalidad.")

        with tab_tabla:
            r = resumen_por(d, "Provincia")
            if "Venta_Neta" in r:
                r = r.sort_values("Venta_Neta", ascending=False)
            st.dataframe(
                r, hide_index=True, **AN_DF,
                column_config={
                    "Venta_Neta": st.column_config.NumberColumn("Ventas netas", format="$ %.0f"),
                    "Margen_%": st.column_config.ProgressColumn("Margen (%)", min_value=0, max_value=100, format="%.1f"),
                    "Cumplimiento_%": st.column_config.NumberColumn("Cumplimiento (%)", format="%.1f"),
                    "Reclamos_x1000": st.column_config.NumberColumn("Reclamos / 1.000", format="%.1f"),
                    "OTD_%": st.column_config.ProgressColumn("Entrega a tiempo (%)", min_value=0, max_value=100, format="%.1f"),
                    "Tiempo_medio": st.column_config.NumberColumn("Tiempo medio", format="%.1f"),
                })

# ==========================================
# 7. PÁGINA 3: DETALLE OPERATIVO
# ==========================================
else:
    encabezado("Detalle Operativo y Granularidad", "Variabilidad de entregas, desempeño por canal y pedidos individuales.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribución del tiempo de entrega")
        if necesita(d, ["Provincia", "Tiempo_Entrega"]):
            fig = px.box(d.dropna(subset=["Tiempo_Entrega"]), x="Provincia", y="Tiempo_Entrega",
                         color="Provincia", points="outliers")
            fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Tiempo de entrega")
            mostrar(fig, "p3_box")
    with c2:
        st.subheader("Entrega a tiempo por canal")
        if necesita(d, ["Canal", "Entrega_A_Tiempo"]):
            r = resumen_por(d, "Canal").sort_values("OTD_%")
            fig = px.bar(r, x="OTD_%", y="Canal", orientation="h", color="OTD_%",
                         color_continuous_scale="RdYlGn", text_auto=".1f")
            fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="% entregado a tiempo")
            mostrar(fig, "p3_otd_canal")

    if "Provincia" in d and "Tiempo_Entrega" in d:
        st.subheader("Variabilidad de entrega por provincia")
        var = (d.groupby("Provincia")["Tiempo_Entrega"]
                 .agg(Media="mean", Mediana="median", P90=lambda s: s.quantile(0.9), Desv_Est="std")
                 .reset_index())
        var["Coef_Var_%"] = (var["Desv_Est"] / var["Media"].replace(0, np.nan)) * 100
        st.dataframe(var.round(2).sort_values("Coef_Var_%", ascending=False), hide_index=True, **AN_DF)
        st.caption("El coeficiente de variación (desv. estándar ÷ media) permite comparar la dispersión entre "
                   "provincias aunque sus tiempos medios sean distintos. P90: el 90 % de las entregas tarda ese tiempo o menos.")

    st.divider()

    with st.expander("🧪 Calidad de datos"):
        cols_ok = [c for c in CAMPOS + ["AñoMes"] if c in base.columns]
        calidad = pd.DataFrame({
            "Columna": cols_ok,
            "Vacíos (%)": [round(base[c].isna().mean() * 100, 1) for c in cols_ok],
        })
        st.dataframe(calidad, hide_index=True, **AN_DF)
        st.caption(f"Filas totales: {len(base):,} · Filas duplicadas: {int(base.duplicated().sum()):,}")

    with st.expander(f"🔎 Ver pedidos individuales ({len(d):,} filas)"):
        sensibles = [c for c in d.columns if any(s in _limpiar(c) for s in SENSIBLES)]
        vista = d.drop(columns=sensibles)
        if sensibles:
            st.caption(f"🔒 Columnas ocultas por gobernanza: {', '.join(sensibles)}")
        st.dataframe(vista, height=400, **AN_DF)
        st.download_button("📥 Descargar datos filtrados (CSV)",
                           data=vista.to_csv(index=False).encode("utf-8-sig"),
                           file_name="reporte_logiandes_filtrado.csv", mime="text/csv")

st.divider()
st.caption("LogiAndes S.A. © 2026 · Prototipo BI en Streamlit · Datos de uso académico.")