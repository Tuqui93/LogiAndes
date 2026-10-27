"""
LogiAndes S.A. · Dashboard de Business Intelligence (Prueba Práctica 2)
Ejecutar:  streamlit run app.py
Archivo único: contiene el núcleo de cálculo de KPIs (sección 1) y la interfaz Streamlit (sección 2).
El Notebook reutiliza exactamente el bloque de la sección 1, por lo que los números coinciden.
"""
import calendar
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ###########################################################################
# SECCIÓN 1 · NÚCLEO DE CÁLCULO DE KPIs (sin dependencias de Streamlit)
# ###########################################################################
# ==== NUCLEO_INICIO ====
import calendar
from pathlib import Path

import numpy as np
import pandas as pd

try:
    RUTA_DATOS = Path(__file__).resolve().parent / "logiandes.csv"
except NameError:  # ejecución dentro de un Notebook
    RUTA_DATOS = Path.cwd() / "logiandes.csv"

# ---------------------------------------------------------------------------
# 1. Esquema de datos y supuestos explícitos
# ---------------------------------------------------------------------------
COLUMNAS = {
    "pedido_id": "pedido_id",
    "fecha_pedido": "fecha",
    "provincia": "provincia",
    "region": "region",
    "canal_entrega": "canal",
    "tipo_cliente": "tipo_cliente",
    "tiempo_atencion_min": "t_atencion",
    "tiempo_individual_entrega_min": "t_entrega",
    "reclamos_registrados": "reclamos",
    "motivo_reclamo": "motivo",
    "ventas_asociadas_usd": "ventas",
    "distancia_km": "km",
}

# SUPUESTO 1: el dataset no trae un indicador de puntualidad. Se define un SLA (minutos)
# por canal, entre el P85 y el P90 histórico de cada canal (Express≈P85; Estándar y Programado≈P90).
SLA_MIN = {"Express": 130, "Estándar urbano": 190, "Programado": 210}

# SUPUESTO 2: el dataset no trae metas. Meta de referencia = ventas diarias del mes base
# (enero) × días del mes evaluado × (1 + crecimiento objetivo).
MES_BASE = "2026-01"
META_CRECIMIENTO = 0.05

# Regla de confianza: una tasa con menos eventos que esto se marca como "baja confianza".
MIN_EVENTOS = 20

MESES_ES = {"01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr", "05": "May", "06": "Jun",
            "07": "Jul", "08": "Ago", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic"}


def nombre_mes(m):
    return f"{MESES_ES[m[5:7]]} {m[:4]}"


# ---------------------------------------------------------------------------
# 2. Definición de KPIs y umbrales (semáforo)
# ---------------------------------------------------------------------------
KPIS = {
    "cumplimiento": dict(nombre="Cumplimiento de meta de ventas", unidad="%", dec=1,
                         verde=100.0, amarillo=90.0, mejor="alto"),
    "reclamos": dict(nombre="Reclamos por 1.000 pedidos", unidad="", dec=1,
                     verde=25.0, amarillo=50.0, mejor="bajo"),
    "otd": dict(nombre="Entrega a tiempo (OTD)", unidad="%", dec=1,
                verde=90.0, amarillo=80.0, mejor="alto"),
    "p90": dict(nombre="Tiempo de entrega P90", unidad=" min", dec=0,
                verde=180.0, amarillo=220.0, mejor="bajo"),
    "prod": dict(nombre="Productividad logística (USD/km)", unidad="", dec=2,
                 verde=2.5, amarillo=2.0, mejor="alto"),
}


def estado(clave, valor):
    """Devuelve 'verde' | 'amarillo' | 'rojo' | 'nd' según los umbrales de la ficha."""
    if valor is None or pd.isna(valor):
        return "nd"
    u = KPIS[clave]
    if u["mejor"] == "alto":
        return "verde" if valor >= u["verde"] else "amarillo" if valor >= u["amarillo"] else "rojo"
    return "verde" if valor <= u["verde"] else "amarillo" if valor <= u["amarillo"] else "rojo"


# ---------------------------------------------------------------------------
# 3. Carga y preparación
# ---------------------------------------------------------------------------
def cargar_datos(ruta=RUTA_DATOS):
    raw = pd.read_csv(ruta)
    faltan = set(COLUMNAS) - set(raw.columns)
    if faltan:
        raise ValueError(f"Al CSV le faltan columnas: {sorted(faltan)}")
    df = raw.rename(columns=COLUMNAS)[list(COLUMNAS.values())].copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).drop_duplicates("pedido_id")
    for c in ("provincia", "region", "canal", "tipo_cliente"):
        df[c] = df[c].astype(str).str.strip()
    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    df["sla_min"] = df["canal"].map(SLA_MIN)
    if df["sla_min"].isna().any():
        raise ValueError(f"Canales sin SLA definido: {sorted(df.loc[df['sla_min'].isna(), 'canal'].unique())}")
    df["a_tiempo"] = (df["t_entrega"] <= df["sla_min"]).astype(int)
    df["reclamos"] = (pd.to_numeric(df["reclamos"], errors="coerce").fillna(0) > 0).astype(int)
    df["motivo"] = df["motivo"].where(df["reclamos"] == 1, "Sin reclamo").fillna("Sin motivo registrado")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Funciones estadísticas y de cálculo
# ---------------------------------------------------------------------------
def dias_mes(m):
    return calendar.monthrange(int(m[:4]), int(m[5:7]))[1]


def wilson(k, n, z=1.96):
    """Intervalo de confianza 95 % de Wilson para una proporción, expresado por 1.000."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    centro = p + z * z / (2 * n)
    amp = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centro - amp) / den * 1000, (centro + amp) / den * 1000)


def meses_evaluables(meses):
    """La meta de referencia solo existe para los meses posteriores al mes base."""
    return [m for m in meses if m > MES_BASE]


def meta_ventas(ctx, meses, por=None):
    """Meta de referencia (USD). `ctx` = datos con todos los filtros salvo el de periodo,
    por lo que la meta se recalcula con el MISMO subconjunto que las ventas (sin sesgo por filtros)."""
    ev = meses_evaluables(meses)
    base = ctx[ctx["mes"] == MES_BASE]
    dias = sum(dias_mes(m) for m in ev)
    factor = dias * (1 + META_CRECIMIENTO) / dias_mes(MES_BASE)
    if por is None:
        return base["ventas"].sum() * factor if (len(base) and ev) else np.nan
    serie = base.groupby(por)["ventas"].sum() * factor
    return serie if ev else serie * np.nan


def calcular_kpis(ctx, meses):
    d = ctx[ctx["mes"].isin(meses)]
    n = len(d)
    k = {"pedidos": n, "ventas": d["ventas"].sum()}
    k["dias"] = sum(dias_mes(m) for m in meses)
    k["ventas_dia"] = k["ventas"] / k["dias"] if k["dias"] else np.nan
    k["ticket"] = k["ventas"] / n if n else np.nan
    ev = meses_evaluables(meses)
    meta = meta_ventas(ctx, meses)
    ventas_ev = ctx[ctx["mes"].isin(ev)]["ventas"].sum()
    k["meta"] = meta
    k["cumplimiento"] = ventas_ev / meta * 100 if pd.notna(meta) and meta > 0 else np.nan
    k["reclamos_n"] = int(d["reclamos"].sum())
    k["reclamos"] = k["reclamos_n"] / n * 1000 if n else np.nan
    k["reclamos_ic"] = wilson(k["reclamos_n"], n)
    k["otd"] = d["a_tiempo"].mean() * 100 if n else np.nan
    k["p90"] = d["t_entrega"].quantile(0.9) if n else np.nan
    k["t_medio"] = d["t_entrega"].mean() if n else np.nan
    k["prod"] = d["ventas"].sum() / d["km"].sum() if n and d["km"].sum() > 0 else np.nan
    return k


def resumen_por(ctx, meses, col):
    """Tabla de KPIs por una dimensión (provincia, canal, ...)."""
    d = ctx[ctx["mes"].isin(meses)]
    g = d.groupby(col)
    r = pd.DataFrame({
        "pedidos": g.size(),
        "ventas": g["ventas"].sum(),
        "reclamos_n": g["reclamos"].sum(),
        "otd": g["a_tiempo"].mean() * 100,
        "p90": g["t_entrega"].quantile(0.9),
        "t_medio": g["t_entrega"].mean(),
        "km": g["km"].sum(),
    })
    r["ticket"] = r["ventas"] / r["pedidos"]
    r["reclamos"] = r["reclamos_n"] / r["pedidos"] * 1000
    r["prod"] = r["ventas"] / r["km"]
    ic = [wilson(k, n) for k, n in zip(r["reclamos_n"], r["pedidos"])]
    r["ic_inf"] = [x[0] for x in ic]
    r["ic_sup"] = [x[1] for x in ic]
    ev = meses_evaluables(meses)
    meta = meta_ventas(ctx, meses, por=col).reindex(r.index)
    ventas_ev = ctx[ctx["mes"].isin(ev)].groupby(col)["ventas"].sum().reindex(r.index)
    r["meta"] = meta
    r["cumplimiento"] = ventas_ev / meta.replace(0, np.nan) * 100
    return r.reset_index()


def resumen_mensual(ctx):
    """Serie mensual con ventas, meta de referencia y KPIs (mes base sin meta)."""
    filas = []
    for m in sorted(ctx["mes"].unique()):
        k = calcular_kpis(ctx, [m])
        filas.append({"mes": m, **{x: k[x] for x in
                      ("pedidos", "ventas", "ventas_dia", "meta", "cumplimiento", "reclamos", "otd", "p90", "prod")}})
    return pd.DataFrame(filas)


def semaforo_por(r):
    return pd.DataFrame({k: [estado(k, v) for v in r[k]] for k in KPIS}, index=r.index)


ACCIONES = {
    "cumplimiento": "Revisar plan comercial y cartera del territorio; validar si la brecha es estacional o estructural.",
    "reclamos": "Auditar los motivos de reclamo dominantes (Detalle Operativo) y acordar plan correctivo con Atención al Cliente.",
    "otd": "Revisar asignación de rutas, ventanas horarias y capacidad de flota del territorio.",
    "p90": "Investigar los pedidos de cola larga (valores atípicos) y las rutas de mayor distancia.",
    "prod": "Evaluar densidad de rutas y consolidación de entregas (menos km por USD vendido).",
}


# ---------------------------------------------------------------------------
# 5. Ficha técnica de KPIs (se genera con las mismas constantes que el cálculo)
# ---------------------------------------------------------------------------
def _sla_txt():
    return ", ".join(f"{c} ≤ {m} min" for c, m in SLA_MIN.items())


FICHAS = [
    {
        "Indicador": "1. Cumplimiento de meta de ventas",
        "Objetivo": "Saber si las ventas avanzan al ritmo esperado, comparando contra una meta de referencia calculada con el mismo subconjunto de datos.",
        "Fórmula": f"Σ ventas_asociadas_usd (meses evaluados) ÷ Meta × 100. Meta = ventas diarias del mes base ({nombre_mes(MES_BASE)}) × días del mes × (1 + {META_CRECIMIENTO:.0%}).",
        "Fuente": "CSV de pedidos: ventas_asociadas_usd, fecha_pedido.",
        "Frecuencia": "Mensual (consulta semanal del acumulado).",
        "Meta": "≥ 100 % de la meta de referencia.",
        "Umbral": "Verde ≥ 100 % · Amarillo 90–99,9 % · Rojo < 90 %.",
        "Interpretación": "Mide ritmo comercial contra una línea base interna. El mes base no tiene meta (N/D). Es una meta de referencia del analista, no una cuota oficial.",
        "Responsable": "Dirección Comercial / Gerencia General",
    },
    {
        "Indicador": "2. Reclamos por 1.000 pedidos",
        "Objetivo": "Comparar la calidad de servicio entre territorios de distinto volumen, usando una tasa y no un conteo.",
        "Fórmula": "(Σ reclamos_registrados ÷ nº de pedidos) × 1.000. Se reporta con intervalo de confianza 95 % de Wilson.",
        "Fuente": "CSV de pedidos: reclamos_registrados, motivo_reclamo.",
        "Frecuencia": "Semanal / mensual.",
        "Meta": "≤ 25 reclamos por 1.000 pedidos.",
        "Umbral": "Verde ≤ 25 · Amarillo 25,1–50 · Rojo > 50.",
        "Interpretación": f"Evita que Guayas o Pichincha parezcan peores solo por volumen. Con menos de {MIN_EVENTOS} reclamos la tasa tiene baja confianza y se marca así.",
        "Responsable": "Atención al Cliente",
    },
    {
        "Indicador": "3. Entrega a tiempo (OTD)",
        "Objetivo": "Medir la puntualidad del servicio logístico frente a la promesa de cada canal.",
        "Fórmula": "(Pedidos con tiempo_individual_entrega_min ≤ SLA del canal ÷ total de pedidos) × 100.",
        "Fuente": f"CSV de pedidos: tiempo_individual_entrega_min, canal_entrega. SLA supuesto: {_sla_txt()}.",
        "Frecuencia": "Diaria / semanal / mensual.",
        "Meta": "≥ 90 % de pedidos dentro del SLA.",
        "Umbral": "Verde ≥ 90 % · Amarillo 80–89,9 % · Rojo < 80 %.",
        "Interpretación": "Los SLA son un supuesto calibrado con la distribución histórica; el valor nacional es poco informativo y la utilidad está en comparar provincias y canales.",
        "Responsable": "Gerencia de Operaciones",
    },
    {
        "Indicador": "4. Tiempo de entrega P90 (variabilidad)",
        "Objetivo": "Detectar territorios con colas largas de retraso que el promedio esconde.",
        "Fórmula": "Percentil 90 de tiempo_individual_entrega_min (minutos).",
        "Fuente": "CSV de pedidos: tiempo_individual_entrega_min.",
        "Frecuencia": "Semanal / mensual.",
        "Meta": "≤ 180 min.",
        "Umbral": "Verde ≤ 180 · Amarillo 181–220 · Rojo > 220 min.",
        "Interpretación": "Indica el tiempo dentro del cual se entrega el 90 % de los pedidos. Depende del mix de canales: una provincia con más Programado tendrá P90 mayor sin que sea peor.",
        "Responsable": "Gerencia de Operaciones",
    },
    {
        "Indicador": "5. Productividad logística (USD por km)",
        "Objetivo": "Evaluar cuánta venta genera cada kilómetro recorrido, como aproximación a la eficiencia de ruta. Sustituye al margen bruto, que el dataset no contiene.",
        "Fórmula": "Σ ventas_asociadas_usd ÷ Σ distancia_km.",
        "Fuente": "CSV de pedidos: ventas_asociadas_usd, distancia_km.",
        "Frecuencia": "Mensual.",
        "Meta": "≥ 2,50 USD/km.",
        "Umbral": "Verde ≥ 2,50 · Amarillo 2,00–2,49 · Rojo < 2,00.",
        "Interpretación": "Es un proxy de eficiencia, no de rentabilidad: no incluye costos. Un valor bajo señala rutas largas con poca venta por pedido.",
        "Responsable": "Finanzas / Operaciones",
    },
]
# ==== NUCLEO_FIN ====


# ###########################################################################
# SECCIÓN 2 · INTERFAZ STREAMLIT (dashboard)
# ###########################################################################
# ---------------------------------------------------------------------------
# Configuración y estilo
# ---------------------------------------------------------------------------
st.set_page_config(page_title="LogiAndes S.A. · Monitoreo BI", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

NAVY, AZUL, ACERO, GRIS, LINEA = "#0B2545", "#1D4E89", "#7F9BB8", "#6B7785", "#E3E8EF"
COLOR_ESTADO = {"verde": "#2F7D5B", "amarillo": "#B7791F", "rojo": "#B4443C", "nd": "#9AA5B1"}
FONDO_ESTADO = {"verde": "#E3F1EA", "amarillo": "#F7EBCF", "rojo": "#F5DCD9", "nd": "#EEF1F5"}
TXT_ESTADO = {"verde": "En meta", "amarillo": "Seguimiento", "rojo": "Acción requerida", "nd": "Sin dato"}

st.markdown(f"""
<style>
.block-container {{ max-width: 1360px; padding-top: 1.6rem; padding-bottom: 2rem; }}
footer, #MainMenu {{ visibility: hidden; }}
h1,h2,h3 {{ color: {NAVY}; letter-spacing: -0.01em; }}
.titulo {{ font-size: 1.55rem; font-weight: 700; color: {NAVY}; margin: 0; line-height: 1.2; }}
.subtitulo {{ font-size: .86rem; color: {GRIS}; margin: .15rem 0 .9rem 0; }}

/* Navegación minimalista: pestañas con subrayado */
div[data-testid="stTabs"] [role="tablist"] {{ gap: 1.7rem; border-bottom: 1px solid {LINEA}; }}
div[data-testid="stTabs"] button[role="tab"] {{ padding: .55rem 0 .65rem 0; background: transparent; height: auto; }}
div[data-testid="stTabs"] button[role="tab"] p {{ font-size: .93rem; font-weight: 500; color: {GRIS}; }}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {{ color: {NAVY}; font-weight: 700; }}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{ background-color: {NAVY} !important; height: 2px; }}
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{ background-color: transparent !important; }}

/* Tarjetas KPI */
.kpi {{ border: 1px solid {LINEA}; border-radius: 10px; padding: .95rem 1.05rem .85rem; background: #fff; height: 100%; }}
.kpi-t {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: {GRIS}; font-weight: 600; }}
.kpi-v {{ font-size: 1.85rem; font-weight: 700; color: {NAVY}; line-height: 1.25; margin: .15rem 0 .05rem; }}
.kpi-d {{ font-size: .78rem; min-height: 1.1rem; }}
.kpi-s {{ font-size: .78rem; margin-top: .45rem; padding-top: .45rem; border-top: 1px solid {LINEA}; color: #334155; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:.4rem; }}
.seccion {{ font-size: 1.02rem; font-weight: 650; color: {NAVY}; margin: 1.1rem 0 .1rem; }}
.nota {{ font-size: .78rem; color: {GRIS}; }}
</style>
""", unsafe_allow_html=True)


def _kw_ancho(fn):
    try:
        p = inspect.signature(fn).parameters.get("width")
        if p is not None and p.default is not None:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


AN_PLOT, AN_DF = _kw_ancho(st.plotly_chart), _kw_ancho(st.dataframe)


def num(v, d=0, pre="", suf=""):
    """Formato regional: 1.234,5"""
    if v is None or pd.isna(v):
        return "N/D"
    s = f"{v:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{pre}{s}{suf}"


def grafico(fig, clave, alto=340):
    fig.update_layout(
        height=alto, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=12, color="#334155"),
        separators=",.", legend_title_text="", hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(gridcolor="#EEF1F5", zeroline=False, linecolor=LINEA)
    fig.update_yaxes(gridcolor="#EEF1F5", zeroline=False, linecolor=LINEA)
    st.plotly_chart(fig, key=clave, config={"displaylogo": False, "displayModeBar": False}, **AN_PLOT)


def seccion(titulo, nota=None):
    st.markdown(f"<div class='seccion'>{titulo}</div>", unsafe_allow_html=True)
    if nota:
        st.markdown(f"<div class='nota'>{nota}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando datos…")
def datos():
    return cargar_datos()


try:
    base = datos()
except Exception as e:  # noqa: BLE001
    st.error(f"No se pudo cargar logiandes.csv: {e}")
    st.stop()

MESES_TODOS = sorted(base["mes"].unique())
OPC_PERIODO = {f"Trimestre ({nombre_mes(MESES_TODOS[0])[:3]}–{nombre_mes(MESES_TODOS[-1])[:3]})": MESES_TODOS}
OPC_PERIODO.update({nombre_mes(m).split()[0]: [m] for m in MESES_TODOS})
PERIODO_DEF = next(iter(OPC_PERIODO))
CLAVES = ["f_periodo", "f_prov", "f_canal", "f_region", "f_cliente", "f_relacion", "f_enfoque"]


def reiniciar():
    for k in CLAVES:
        st.session_state.pop(k, None)


# ---------------------------------------------------------------------------
# Cabecera y filtros globales (solo tres: periodo, provincia, canal)
# ---------------------------------------------------------------------------
st.markdown("<div class='titulo'>LogiAndes S.A. · Monitoreo de desempeño</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='subtitulo'>Quito, Guayaquil, Cuenca, Manta, Ambato y Loja · pedidos de "
    f"{nombre_mes(MESES_TODOS[0])} a {nombre_mes(MESES_TODOS[-1])} · análisis a nivel de provincia</div>",
    unsafe_allow_html=True)

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.5, 2, 2, .6], vertical_alignment="bottom")
    periodo = c1.radio("Periodo", list(OPC_PERIODO), horizontal=True, key="f_periodo")
    sel_prov = c2.multiselect("Provincia", sorted(base["provincia"].unique()), key="f_prov", placeholder="Todas")
    sel_canal = c3.multiselect("Canal de entrega", sorted(base["canal"].unique()), key="f_canal", placeholder="Todos")
    c4.button("Limpiar", on_click=reiniciar, **({"width": "stretch"} if "width" in inspect.signature(st.button).parameters else {"use_container_width": True}))

meses = OPC_PERIODO[periodo]
ctx0 = base
if sel_prov:
    ctx0 = ctx0[ctx0["provincia"].isin(sel_prov)]
if sel_canal:
    ctx0 = ctx0[ctx0["canal"].isin(sel_canal)]
if ctx0[ctx0["mes"].isin(meses)].empty:
    st.warning("Los filtros no devuelven pedidos. Pulsa **Limpiar** o amplía la selección.")
    st.stop()

n_sel = int(ctx0["mes"].isin(meses).sum())
st.markdown(f"<div class='nota'>Mostrando {num(n_sel)} de {num(len(base))} pedidos · "
            f"{'filtros activos' if (sel_prov or sel_canal or len(meses) < len(MESES_TODOS)) else 'vista consolidada'}</div>",
            unsafe_allow_html=True)


def mes_previo(ms):
    if len(ms) == 1:
        i = MESES_TODOS.index(ms[0])
        return [MESES_TODOS[i - 1]] if i > 0 else None
    return None


# ---------------------------------------------------------------------------
# Componentes reutilizables
# ---------------------------------------------------------------------------
def tarjeta(col, titulo, valor_txt, clave_kpi, valor, meta_txt, delta_html=""):
    est = estado(clave_kpi, valor)
    c = COLOR_ESTADO[est]
    col.markdown(
        f"<div class='kpi'><div class='kpi-t'>{titulo}</div><div class='kpi-v'>{valor_txt}</div>"
        f"<div class='kpi-d'>{delta_html}</div>"
        f"<div class='kpi-s'><span class='dot' style='background:{c}'></span><b style='color:{c}'>{TXT_ESTADO[est]}</b>"
        f" · <span style='color:{GRIS}'>{meta_txt}</span></div></div>", unsafe_allow_html=True)


def delta(act, prev, dec=1, suf="", mejor="alto", pct=False):
    if prev is None or pd.isna(prev) or pd.isna(act):
        return ""
    dif = (act / prev - 1) * 100 if pct else act - prev
    bueno = (dif >= 0) if mejor == "alto" else (dif <= 0)
    c = COLOR_ESTADO["verde"] if bueno else COLOR_ESTADO["rojo"]
    flecha = "▲" if dif >= 0 else "▼"
    return f"<span style='color:{c}'>{flecha} {num(abs(dif), dec)}{suf}</span> <span style='color:{GRIS}'>vs. mes anterior</span>"


def tabla_semaforo(r, idx_col):
    """Tabla de KPIs por territorio con celdas coloreadas según el umbral de la ficha."""
    sem = semaforo_por(r)
    vis = pd.DataFrame({
        idx_col.capitalize(): r[idx_col],
        "Cumplimiento meta": [num(v, 1, suf=" %") for v in r["cumplimiento"]],
        "Reclamos/1.000": [num(v, 1) + (" ⚠" if n < MIN_EVENTOS else "") for v, n in zip(r["reclamos"], r["reclamos_n"])],
        "Entrega a tiempo": [num(v, 1, suf=" %") for v in r["otd"]],
        "P90 entrega (min)": [num(v, 0) for v in r["p90"]],
        "USD por km": [num(v, 2) for v in r["prod"]],
    })
    mapa = dict(zip(vis.columns[1:], KPIS))

    def css(_):
        out = pd.DataFrame("", index=vis.index, columns=vis.columns)
        for colv, kk in mapa.items():
            out[colv] = [f"background-color:{FONDO_ESTADO[e]};color:#1F2A37" for e in sem[kk]]
        return out

    st.dataframe(vis.style.apply(css, axis=None), hide_index=True, **AN_DF)


# ---------------------------------------------------------------------------
# 1. VISIÓN EJECUTIVA
# ---------------------------------------------------------------------------
def pagina_ejecutiva():
    k = calcular_kpis(ctx0, meses)
    pm = mes_previo(meses)
    kp = calcular_kpis(ctx0, pm) if pm else None
    g = (lambda x: kp[x]) if kp else (lambda x: None)

    cols = st.columns(5)
    cumpl_txt = ("Meta ≥ 100 % de la referencia" if pd.notna(k["cumplimiento"])
                 else "Mes base: sin meta de referencia")
    tarjeta(cols[0], "Ventas · cumplimiento", num(k["ventas"], 0, "$"), "cumplimiento", k["cumplimiento"],
            f"Cumplimiento {num(k['cumplimiento'], 1, suf=' %')}" if pd.notna(k["cumplimiento"]) else cumpl_txt,
            delta(k["ventas_dia"], g("ventas_dia"), 1, " % ventas/día", pct=True) if kp else "")
    tarjeta(cols[1], "Reclamos / 1.000 pedidos", num(k["reclamos"], 1), "reclamos", k["reclamos"], "Meta ≤ 25",
            delta(k["reclamos"], g("reclamos"), 1, "", mejor="bajo") if kp else "")
    tarjeta(cols[2], "Entrega a tiempo", num(k["otd"], 1, suf=" %"), "otd", k["otd"], "Meta ≥ 90 %",
            delta(k["otd"], g("otd"), 1, " pp") if kp else "")
    tarjeta(cols[3], "Tiempo de entrega P90", num(k["p90"], 0, suf=" min"), "p90", k["p90"], "Meta ≤ 180 min",
            delta(k["p90"], g("p90"), 0, " min", mejor="bajo") if kp else "")
    tarjeta(cols[4], "Productividad logística", num(k["prod"], 2, suf=" USD/km"), "prod", k["prod"], "Meta ≥ 2,50",
            delta(k["prod"], g("prod"), 2, "") if kp else "")

    r = resumen_por(ctx0, meses, "provincia")
    sem = semaforo_por(r)
    rojas = r.loc[(sem == "rojo").any(axis=1), "provincia"].tolist()
    if len(r) > 1:
        msg = (f"**{len(rojas)} de {len(r)} provincias** tienen al menos un indicador en rojo: {', '.join(rojas)}."
               if rojas else "Ninguna provincia tiene indicadores en rojo en la selección actual.")
        st.markdown(f"<div style='margin:.9rem 0 .1rem'>{msg}</div>", unsafe_allow_html=True)

    a, b = st.columns([1.15, 1])
    with a:
        seccion("Semáforo por provincia", "Color según los umbrales de la ficha técnica. ⚠ = menos de 20 reclamos (tasa poco estable).")
        tabla_semaforo(r, "provincia")
    with b:
        seccion("Ventas vs. meta de referencia por mes", "La serie mensual no depende del filtro de periodo; sí de provincia y canal.")
        m = resumen_mensual(ctx0)
        fig = go.Figure()
        fig.add_bar(x=[nombre_mes(x) for x in m["mes"]], y=m["ventas"], name="Ventas", marker_color=AZUL,
                    text=[num(v, 0, "$") for v in m["ventas"]], textposition="outside")
        fig.add_scatter(x=[nombre_mes(x) for x in m["mes"]], y=m["meta"], name="Meta de referencia", mode="lines+markers",
                        line=dict(color="#B7791F", dash="dash"), connectgaps=False)
        fig.update_yaxes(title="USD", rangemode="tozero")
        fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
        grafico(fig, "ej_serie", 320)

    seccion("Acciones sugeridas", "Prioridad alta = indicador en rojo; media = en seguimiento. Derivadas automáticamente de los umbrales.")
    filas = []
    for i, fila in r.iterrows():
        for kk in KPIS:
            e = sem.loc[i, kk]
            if e in ("rojo", "amarillo"):
                u = KPIS[kk]
                extra = " (muestra baja: confirmar con más datos)" if kk == "reclamos" and fila["reclamos_n"] < MIN_EVENTOS else ""
                filas.append({"Prioridad": "Alta" if e == "rojo" else "Media", "Provincia": fila["provincia"],
                              "Indicador": u["nombre"], "Valor": num(fila[kk], u["dec"], suf=u["unidad"]),
                              "Meta": num(u["verde"], u["dec"], suf=u["unidad"]), "Acción sugerida": ACCIONES[kk] + extra})
    if filas:
        acc = pd.DataFrame(filas)
        acc["_o"] = acc["Prioridad"].map({"Alta": 0, "Media": 1})
        st.dataframe(acc.sort_values(["_o", "Provincia"]).drop(columns="_o"), hide_index=True, height=300, **AN_DF)
    else:
        st.success("Sin acciones pendientes en la selección actual.")
    st.caption("Límite interpretativo: estas lecturas describen asociaciones en los registros internos. Cualquier contraste con "
               "indicadores del BCE o del INEC mostraría coincidencia temporal, no causalidad.")


# ---------------------------------------------------------------------------
# 2. DIAGNÓSTICO TERRITORIAL
# ---------------------------------------------------------------------------
def pagina_territorial():
    with st.container(border=True):
        t1, t2 = st.columns([1.2, 2])
        sel_reg = t1.multiselect("Región", sorted(base["region"].unique()), key="f_region", placeholder="Todas")
        opciones = ["Pedidos vs. reclamos", "Tiempo de entrega vs. reclamos"]
        if hasattr(st, "segmented_control"):
            relacion = t2.segmented_control("Relación a explorar", opciones, default=opciones[0], key="f_relacion") or opciones[0]
        else:
            relacion = t2.radio("Relación a explorar", opciones, horizontal=True, key="f_relacion")
    ctx = ctx0[ctx0["region"].isin(sel_reg)] if sel_reg else ctx0
    d = ctx[ctx["mes"].isin(meses)]
    if d.empty:
        st.warning("Sin pedidos para la región seleccionada.")
        return
    r = resumen_por(ctx, meses, "provincia")

    a, b = st.columns(2)
    with a:
        seccion("Ventas por provincia (USD)")
        t = r.sort_values("ventas")
        fig = go.Figure(go.Bar(x=t["ventas"], y=t["provincia"], orientation="h", marker_color=AZUL,
                               text=[num(v, 0, "$") for v in t["ventas"]], textposition="outside", cliponaxis=False))
        fig.update_xaxes(title="USD", rangemode="tozero")
        grafico(fig, "te_ventas")
    with b:
        seccion("Reclamos por 1.000 pedidos, con intervalo de confianza 95 %",
                "Las barras de error muestran la incertidumbre: con pocos eventos la tasa es inestable.")
        t = r.sort_values("reclamos")
        fig = go.Figure(go.Bar(
            x=t["reclamos"], y=t["provincia"], orientation="h",
            marker_color=[COLOR_ESTADO[estado("reclamos", v)] for v in t["reclamos"]],
            error_x=dict(type="data", symmetric=False, array=t["ic_sup"] - t["reclamos"], arrayminus=t["reclamos"] - t["ic_inf"],
                         color="#475569", thickness=1.2),
            text=[num(v, 1) for v in t["reclamos"]], textposition="inside", insidetextanchor="start",
            textfont=dict(color="white")))
        fig.add_vline(x=25, line_dash="dash", line_color=COLOR_ESTADO["verde"], annotation_text="Meta 25")
        fig.add_vline(x=50, line_dash="dash", line_color=COLOR_ESTADO["rojo"], annotation_text="Rojo 50")
        fig.update_xaxes(title="Reclamos por 1.000 pedidos", rangemode="tozero")
        grafico(fig, "te_reclamos")

    c, e = st.columns(2)
    with c:
        seccion("Entrega a tiempo por provincia y canal (%)", "Escala fija ligada a los umbrales: rojo < 80, ámbar 80–90, verde ≥ 90.")
        piv = d.pivot_table(index="provincia", columns="canal", values="a_tiempo", aggfunc="mean") * 100
        npv = d.pivot_table(index="provincia", columns="canal", values="a_tiempo", aggfunc="size")
        fig = go.Figure(go.Heatmap(
            z=piv.values, x=piv.columns, y=piv.index, zmin=60, zmax=100, customdata=npv.values,
            text=[[num(v, 0, suf="%") for v in fila] for fila in piv.values], texttemplate="%{text}",
            textfont=dict(color="white", size=13), xgap=3, ygap=3, showscale=False,
            colorscale=[[0, COLOR_ESTADO["rojo"]], [.5, COLOR_ESTADO["rojo"]], [.5, COLOR_ESTADO["amarillo"]],
                        [.75, COLOR_ESTADO["amarillo"]], [.75, COLOR_ESTADO["verde"]], [1, COLOR_ESTADO["verde"]]],
            hovertemplate="%{y} · %{x}<br>OTD: %{z:.1f}%<br>Pedidos: %{customdata}<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        grafico(fig, "te_heat")
    with e:
        if relacion == "Pedidos vs. reclamos":
            seccion("Pedidos vs. reclamos por provincia y mes", "Cada punto es una provincia en un mes (continuidad con la clase anterior).")
            pm_ = d.groupby(["provincia", "mes"]).agg(pedidos=("pedido_id", "size"), rec=("reclamos", "sum")).reset_index()
            pm_["tasa"] = pm_["rec"] / pm_["pedidos"] * 1000
            fig = px.scatter(pm_, x="pedidos", y="tasa", color="provincia", color_discrete_sequence=px.colors.qualitative.Safe,
                             hover_data={"mes": True})
            fig.update_traces(marker=dict(size=11, line=dict(width=1, color="white")))
            fig.update_layout(xaxis_title="Pedidos en el mes", yaxis_title="Reclamos por 1.000 pedidos")
            grafico(fig, "te_sc1")
            if len(pm_) >= 5:
                rho = pm_[["pedidos", "tasa"]].corr(method="spearman").iloc[0, 1]
                st.caption(f"Correlación de Spearman = {num(rho, 2)} con n = {len(pm_)} puntos. Una asociación débil o inestable "
                           "con tan pocos puntos no permite concluir que el volumen cause más o menos reclamos.")
        else:
            seccion("Tiempo medio de entrega vs. reclamos por provincia", "Tamaño del punto = pedidos.")
            fig = px.scatter(r, x="t_medio", y="reclamos", size="pedidos", text="provincia", size_max=38)
            fig.update_traces(marker=dict(color=AZUL, opacity=.8, line=dict(width=1, color="white")), textposition="top center")
            fig.update_layout(xaxis_title="Tiempo medio de entrega (min)", yaxis_title="Reclamos por 1.000 pedidos")
            grafico(fig, "te_sc2")
            if len(r) >= 5:
                rho = r[["t_medio", "reclamos"]].corr(method="spearman").iloc[0, 1]
                st.caption(f"Correlación de Spearman = {num(rho, 2)} con n = {len(r)} provincias. Con solo {len(r)} observaciones "
                           "es una pista para investigar, no una prueba de causalidad.")

    seccion("Tabla comparativa por provincia")
    t = r.copy()
    t["confianza"] = np.where(t["reclamos_n"] < MIN_EVENTOS, "Baja (<20 reclamos)", "Aceptable")
    t = t.sort_values("ventas", ascending=False)[["provincia", "pedidos", "ventas", "ticket", "cumplimiento", "reclamos_n",
                                                    "reclamos", "ic_inf", "ic_sup", "confianza", "otd", "p90", "prod"]]
    st.dataframe(t, hide_index=True, **AN_DF, column_config={
        "provincia": "Provincia", "pedidos": st.column_config.NumberColumn("Pedidos", format="%d"),
        "ventas": st.column_config.NumberColumn("Ventas (USD)", format="$ %.0f"),
        "ticket": st.column_config.NumberColumn("Ticket (USD)", format="$ %.2f"),
        "cumplimiento": st.column_config.NumberColumn("Cumplimiento meta (%)", format="%.1f"),
        "reclamos_n": st.column_config.NumberColumn("Reclamos (n)", format="%d"),
        "reclamos": st.column_config.NumberColumn("Reclamos/1.000", format="%.1f"),
        "ic_inf": st.column_config.NumberColumn("IC 95 % inf.", format="%.1f"),
        "ic_sup": st.column_config.NumberColumn("IC 95 % sup.", format="%.1f"),
        "confianza": "Confianza de la tasa",
        "otd": st.column_config.NumberColumn("OTD (%)", format="%.1f"),
        "p90": st.column_config.NumberColumn("P90 (min)", format="%.0f"),
        "prod": st.column_config.NumberColumn("USD/km", format="%.2f"),
    })


# ---------------------------------------------------------------------------
# 3. DETALLE OPERATIVO
# ---------------------------------------------------------------------------
def acceso_analista() -> bool:
    try:
        codigo = st.secrets.get("ACCESS_CODE", "analista2026")
    except Exception:  # noqa: BLE001
        codigo = "analista2026"
    return st.text_input("Código de acceso (analistas)", type="password", key="f_codigo",
                         help="Control de acceso de demostración. En producción se reemplazaría por autenticación corporativa.") == codigo


def pagina_operativa():
    with st.container(border=True):
        o1, o2 = st.columns([1.6, 1.4])
        sel_cli = o1.multiselect("Tipo de cliente", sorted(base["tipo_cliente"].unique()), key="f_cliente", placeholder="Todos")
        enfoque = o2.selectbox("Enfoque del explorador de pedidos",
                               ["Todos los pedidos", "Solo con reclamo", "Solo fuera de SLA"], key="f_enfoque")
    ctx = ctx0[ctx0["tipo_cliente"].isin(sel_cli)] if sel_cli else ctx0
    d = ctx[ctx["mes"].isin(meses)]
    if d.empty:
        st.warning("Sin pedidos para el tipo de cliente seleccionado.")
        return

    a, b = st.columns(2)
    with a:
        seccion("Tiempo de entrega por provincia (minutos)", "La caja muestra mediana y rango intercuartílico; los puntos son atípicos.")
        fig = px.box(d, x="provincia", y="t_entrega", points="outliers", color_discrete_sequence=[AZUL])
        fig.update_layout(xaxis_title=None, yaxis_title="Minutos")
        grafico(fig, "op_box_prov")
    with b:
        seccion("Tiempo de entrega por canal vs. SLA (minutos)", "La marca roja indica el SLA supuesto de cada canal.")
        fig = px.box(d, x="canal", y="t_entrega", points="outliers", color_discrete_sequence=[ACERO])
        canales = sorted(d["canal"].unique())
        fig.add_scatter(x=canales, y=[SLA_MIN[c] for c in canales], mode="markers", name="SLA",
                        marker=dict(symbol="line-ew", size=64, line=dict(width=3, color=COLOR_ESTADO["rojo"])))
        fig.update_layout(xaxis_title=None, yaxis_title="Minutos", showlegend=False)
        grafico(fig, "op_box_canal")

    c, e = st.columns([1.15, 1])
    with c:
        seccion("Variabilidad logística por provincia")
        v = d.groupby("provincia").agg(media=("t_entrega", "mean"), mediana=("t_entrega", "median"),
                                       p90=("t_entrega", lambda s: s.quantile(.9)), desv=("t_entrega", "std"),
                                       fuera=("a_tiempo", lambda s: (1 - s.mean()) * 100)).reset_index()
        v["cv"] = v["desv"] / v["media"] * 100
        st.dataframe(v.sort_values("cv", ascending=False), hide_index=True, **AN_DF, column_config={
            "provincia": "Provincia", "media": st.column_config.NumberColumn("Media (min)", format="%.1f"),
            "mediana": st.column_config.NumberColumn("Mediana (min)", format="%.1f"),
            "p90": st.column_config.NumberColumn("P90 (min)", format="%.0f"),
            "desv": st.column_config.NumberColumn("Desv. est.", format="%.1f"),
            "fuera": st.column_config.NumberColumn("Fuera de SLA (%)", format="%.1f"),
            "cv": st.column_config.NumberColumn("Coef. variación (%)", format="%.1f")})
        st.caption("El coeficiente de variación (desviación ÷ media) mide la inestabilidad relativa de las entregas.")
    with e:
        seccion("Motivos de reclamo (Pareto)")
        mo = d[d["reclamos"] == 1]["motivo"].value_counts().reset_index()
        mo.columns = ["motivo", "n"]
        if mo.empty:
            st.info("No hay reclamos en la selección.")
        else:
            mo["acum"] = mo["n"].cumsum() / mo["n"].sum() * 100
            fig = go.Figure()
            fig.add_bar(x=mo["motivo"], y=mo["n"], marker_color=AZUL, name="Reclamos")
            fig.add_scatter(x=mo["motivo"], y=mo["acum"], yaxis="y2", mode="lines+markers", name="% acumulado",
                            line=dict(color="#B7791F"))
            fig.update_layout(yaxis=dict(title="Reclamos"), yaxis2=dict(overlaying="y", side="right", range=[0, 105], showgrid=False,
                                                                       title="% acumulado"), legend=dict(orientation="h", y=1.15))
            fig.update_xaxes(tickangle=-25)
            grafico(fig, "op_pareto", 310)

    seccion("Explorador de pedidos (acceso restringido)",
            "El dataset no contiene datos personales, pero el detalle por pedido es información operativa y queda tras un control de acceso.")
    if acceso_analista():
        vista = d
        if enfoque == "Solo con reclamo":
            vista = vista[vista["reclamos"] == 1]
        elif enfoque == "Solo fuera de SLA":
            vista = vista[vista["a_tiempo"] == 0]
        vista = vista[["pedido_id", "fecha", "provincia", "canal", "tipo_cliente", "t_entrega", "sla_min", "a_tiempo",
                       "reclamos", "motivo", "ventas", "km"]].sort_values("fecha")
        st.caption(f"{num(len(vista))} pedidos · se muestran los primeros 1.000.")
        st.dataframe(vista.head(1000), hide_index=True, height=320, **AN_DF)
        st.download_button("Descargar selección (CSV)", vista.to_csv(index=False).encode("utf-8-sig"),
                           "pedidos_seleccion.csv", "text/csv")
    else:
        st.info("Introduce el código de acceso para ver el detalle de pedidos. Código de la demostración: ver README.")


# ---------------------------------------------------------------------------
# 4. METODOLOGÍA Y GOBERNANZA
# ---------------------------------------------------------------------------
def pagina_metodologia():
    seccion("1. Problema empresarial y audiencias")
    st.markdown(
        "LogiAndes S.A. creció con información dispersa: cada área usa sus propias cifras (ventas brutas o netas, tiempos "
        "promedio sin dispersión, reclamos sin relación con el volumen, metas separadas de la facturación). Este dashboard "
        "integra una única definición de cada indicador para **monitorear, interpretar y actuar**.")
    st.dataframe(pd.DataFrame([
        ["Gerencia general", "Saber si se cumplen los objetivos", "Visión Ejecutiva: 5 KPI con semáforo y acciones sugeridas"],
        ["Dirección comercial", "Comparar territorios, canal y periodo", "Filtros de periodo, provincia y canal; Diagnóstico Territorial"],
        ["Operaciones", "Detectar retrasos y alta variabilidad", "Detalle Operativo: boxplots, P90, coeficiente de variación, SLA"],
        ["Finanzas", "Una sola definición de ventas y eficiencia", "Ventas con meta de referencia y productividad USD/km (el dataset no trae margen)"],
        ["Atención al cliente", "Comparar reclamos sin sesgo de volumen", "Tasa por 1.000 pedidos con IC 95 % y Pareto de motivos"],
    ], columns=["Audiencia", "Necesidad", "Respuesta en el dashboard"]), hide_index=True, **AN_DF)

    seccion("2. Fichas técnicas de los KPI")
    for f in FICHAS:
        with st.expander(f["Indicador"]):
            for kk in ("Objetivo", "Fórmula", "Fuente", "Frecuencia", "Meta", "Umbral", "Interpretación", "Responsable"):
                st.markdown(f"**{kk}:** {f[kk]}")

    seccion("3. Supuestos y limitaciones de los datos")
    st.markdown(
        f"- **Ventas.** El dataset trae `ventas_asociadas_usd`; no distingue ventas brutas de netas ni incluye costos, por lo que no hay margen bruto. "
        "Se usa la productividad USD/km como aproximación de eficiencia.\n"
        f"- **Meta.** No existe en los datos. Se define una *meta de referencia*: ventas diarias de {nombre_mes(MES_BASE)} × días del mes × "
        f"{1 + META_CRECIMIENTO:.2f}. Se calcula con el mismo subconjunto filtrado, y {nombre_mes(MES_BASE)} queda sin meta.\n"
        f"- **SLA.** Supuesto por canal ({', '.join(f'{c} {m} min' for c, m in SLA_MIN.items())}), calibrado con la distribución histórica; "
        "por eso el OTD nacional informa poco y la comparación entre territorios es lo valioso.\n"
        "- **Territorio.** El nivel disponible es provincia (Pichincha, Guayas, Azuay, Manabí, Tungurahua, Loja); no hay ciudad ni línea de servicio. "
        "El canal de entrega (Estándar urbano, Express, Programado) cumple el papel de tipo de servicio.\n"
        "- **Periodo.** Solo tres meses de datos: no permite estacionalidad ni tendencias robustas.")

    seccion("4. Reflexión: riesgos y límites")
    a, b = st.columns(2)
    with a:
        st.markdown(
            "**Sobreinteractividad.** Se limitan los controles: 3 filtros globales (periodo, provincia, canal) y como máximo 2 locales por vista. "
            "No se ofrecen filtros por cliente o pedido en las vistas agregadas; más controles fragmentarían la muestra (algunas provincias tienen menos de 20 reclamos) y aumentarían la carga cognitiva.\n\n"
            "**Sesgos visuales.** Los reclamos se expresan como tasa y no como conteo, para no culpar a las provincias grandes. Las escalas de color están fijadas a los umbrales "
            "(no al mínimo y máximo de los datos), los ejes de barras parten de cero, y las tasas se muestran con intervalo de confianza. Los boxplots evitan que el promedio oculte las colas.")
    with b:
        st.markdown(
            "**Privacidad.** El dataset no contiene nombres, cédulas ni identificadores de clientes o vendedores; solo `pedido_id`. Las vistas ejecutiva y territorial son agregadas, y el detalle por pedido queda tras un código de acceso.\n\n"
            "**Gobernanza.** El control de acceso es de demostración; en producción requiere autenticación y permisos por rol. Cada KPI tiene definición, fuente, responsable y umbrales documentados, y el cálculo de KPIs vive en un solo bloque (sección 1 de este archivo), reutilizado tal cual por el Notebook.\n\n"
            "**Límites interpretativos.** Los indicadores muestran asociaciones, no causas. Contrastar con datos del BCE o el INEC solo mostraría coincidencias. Con 6 provincias y 3 meses, las correlaciones son exploratorias. "
            "El semáforo depende de umbrales y metas supuestos, que deben validarse con las áreas.")

    seccion("5. Herramienta")
    st.markdown("Streamlit permite iterar rápido sobre datos ya procesados en Python y validar estructura, filtros e indicadores con la gerencia. "
                "La definición de KPIs queda desacoplada de la interfaz, por lo que podría migrarse más adelante a una herramienta de distribución corporativa.")

    with st.expander("Calidad de los datos"):
        cal = pd.DataFrame({"Columna": base.columns, "Nulos (%)": [round(base[c].isna().mean() * 100, 1) for c in base.columns],
                            "Valores únicos": [int(base[c].nunique()) for c in base.columns]})
        st.dataframe(cal, hide_index=True, **AN_DF)
        st.caption(f"{num(len(base))} pedidos · del {base['fecha'].min():%d/%m/%Y} al {base['fecha'].max():%d/%m/%Y}.")


# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------
t_ej, t_te, t_op, t_me = st.tabs(["Visión ejecutiva", "Diagnóstico territorial", "Detalle operativo", "Metodología y gobernanza"])
with t_ej:
    pagina_ejecutiva()
with t_te:
    pagina_territorial()
with t_op:
    pagina_operativa()
with t_me:
    pagina_metodologia()