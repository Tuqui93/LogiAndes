"""
LogiAndes S.A. · Sistema de Business Intelligence y Monitoreo Operativo
Materia: Visualización, Storytelling y Business Intelligence (Prueba Práctica 2)



import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS SOBRIOS
# ==========================================
st.set_page_config(
    page_title="LogiAndes S.A. · BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _kw_ancho(fn):
    """Compatibilidad entre versiones de Streamlit para ancho completo."""
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

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1420px; }
        .top-header {
            display: flex; align-items: center; justify-content: space-between;
            padding-bottom: 0.6rem; border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            margin-bottom: 0.8rem;
        }
        .brand-box { display: flex; align-items: center; gap: 0.75rem; }
        .brand-badge {
            background: #1e3a8a; color: #ffffff; font-weight: 800; font-size: 1.15rem;
            width: 40px; height: 40px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
        }
        .main-title { font-size: 1.45rem; font-weight: 800; margin: 0; line-height: 1.15; }
        .sub-title { font-size: 0.84rem; opacity: 0.78; margin: 0; }
        .semaforo-pill {
            display: inline-block; padding: 0.14rem 0.55rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600; margin-top: 0.15rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. REGLAS DE NEGOCIO, SUPUESTOS Y CARGA DIRECTA
# ==========================================
COLUMNAS_ESPERADAS = [
    "pedido_id",
    "fecha_pedido",
    "region",
    "provincia",
    "canal_entrega",
    "tipo_cliente",
    "distancia_km",
    "tiempo_individual_entrega_min",
    "tiempo_atencion_min",
    "ventas_asociadas_usd",
    "reclamos_registrados",
    "motivo_reclamo",
]

# SLA por defecto (minutos) justificado por las medianas empíricas del dataset:
# Express (mediana ~87 min) -> SLA 120 min
# Estándar urbano (mediana ~134 min) -> SLA 180 min
# Programado (mediana ~157 min) -> SLA 210 min
SLA_DEFAULT = {
    "Express": 120,
    "Estándar urbano": 180,
    "Programado": 210,
}

MOTIVOS_OPERATIVOS = {"Demora en entrega", "Paquete con incidencia", "Incumplimiento de horario"}
MOTIVOS_ATENCION = {"Falta de actualización", "Demora en atención"}
MIN_EVENTOS_ESTABLE = 15  # Umbral de gobernanza para advertir muestras pequeñas de reclamos


@st.cache_data(show_spinner="Cargando dataset oficial de LogiAndes S.A.…")
def cargar_datos(ruta_o_buffer, nombre_archivo: str) -> pd.DataFrame:
    if nombre_archivo.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(ruta_o_buffer)
    else:
        try:
            df = pd.read_csv(ruta_o_buffer, encoding="utf-8-sig", sep=None, engine="python")
        except Exception:
            if hasattr(ruta_o_buffer, "seek"):
                ruta_o_buffer.seek(0)
            df = pd.read_csv(ruta_o_buffer, encoding="latin-1", sep=None, engine="python")

    df.columns = [str(c).strip().lower() for c in df.columns]
    df["fecha_pedido"] = pd.to_datetime(df["fecha_pedido"], errors="coerce")
    df["anio_mes"] = df["fecha_pedido"].dt.to_period("M").astype(str)

    for col_num in ("distancia_km", "tiempo_individual_entrega_min", "tiempo_atencion_min", "ventas_asociadas_usd"):
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num], errors="coerce")

    if "reclamos_registrados" in df.columns:
        df["reclamos_registrados"] = pd.to_numeric(df["reclamos_registrados"], errors="coerce").fillna(0).astype(int)

    for col_txt in ("region", "provincia", "canal_entrega", "tipo_cliente"):
        if col_txt in df.columns:
            df[col_txt] = df[col_txt].fillna("Sin dato").astype(str).str.strip()

    if "motivo_reclamo" in df.columns:
        df["motivo_reclamo"] = (
            df["motivo_reclamo"]
            .replace(["", "nan", "None", "null", "Sin reclamo", "N/A", "-"], np.nan)
        )
        df.loc[df["reclamos_registrados"] == 0, "motivo_reclamo"] = np.nan

    return df


def aplicar_sla(df: pd.DataFrame, sla_map: dict) -> pd.DataFrame:
    """Deriva la columna entrega_a_tiempo (0/1) según el SLA específico de cada canal_entrega."""
    out = df.copy()
    sla_serie = out["canal_entrega"].map(sla_map).fillna(180)
    out["sla_canal_min"] = sla_serie
    out["entrega_a_tiempo"] = (out["tiempo_individual_entrega_min"] <= out["sla_canal_min"]).astype(int)
    out["exceso_sla_min"] = (out["tiempo_individual_entrega_min"] - out["sla_canal_min"]).clip(lower=0)
    return out


# ==========================================
# 3. FUNCIÓN ÚNICA DE CÁLCULO (COMPARTIDA CON EL NOTEBOOK)
# ==========================================
def calcular_metricas(df: pd.DataFrame) -> dict:
    """
    Calcula los indicadores de negocio sobre cualquier subconjunto del dataset.
    Esta misma función se utiliza en el Notebook para garantizar 100% de consistencia.
    """
    n_pedidos = len(df)
    if n_pedidos == 0:
        return {
            "pedidos": 0, "ventas_usd": 0.0, "ticket_medio_usd": np.nan,
            "distancia_total_km": 0.0, "usd_por_km": np.nan, "min_por_km": np.nan,
            "reclamos_n": 0, "tasa_reclamos_x1000": np.nan, "muestra_pequena": True,
            "otd_pct": np.nan, "tiempo_entrega_media": np.nan, "tiempo_entrega_mediana": np.nan,
            "tiempo_entrega_p90": np.nan, "tiempo_atencion_media": np.nan,
        }

    ventas_usd = float(df["ventas_asociadas_usd"].sum())
    distancia_km = float(df["distancia_km"].sum())
    tiempo_total_min = float(df["tiempo_individual_entrega_min"].sum())
    reclamos_n = int(df["reclamos_registrados"].sum())

    return {
        "pedidos": n_pedidos,
        "ventas_usd": ventas_usd,
        "ticket_medio_usd": ventas_usd / n_pedidos,
        "distancia_total_km": distancia_km,
        "usd_por_km": ventas_usd / distancia_km if distancia_km > 0 else np.nan,
        "min_por_km": tiempo_total_min / distancia_km if distancia_km > 0 else np.nan,
        "reclamos_n": reclamos_n,
        "tasa_reclamos_x1000": (reclamos_n / n_pedidos) * 1000.0,
        "muestra_pequena": (0 < reclamos_n < MIN_EVENTOS_ESTABLE) or (n_pedidos < 100),
        "otd_pct": float(df["entrega_a_tiempo"].mean() * 100.0),
        "tiempo_entrega_media": float(df["tiempo_individual_entrega_min"].mean()),
        "tiempo_entrega_mediana": float(df["tiempo_individual_entrega_min"].median()),
        "tiempo_entrega_p90": float(df["tiempo_individual_entrega_min"].quantile(0.90)),
        "tiempo_atencion_media": float(df["tiempo_atencion_min"].mean()),
    }


def resumen_agrupado(df: pd.DataFrame, col_grupo: str) -> pd.DataFrame:
    """Genera tabla resumen por cualquier dimensión (provincia, canal_entrega, tipo_cliente, anio_mes)."""
    filas = []
    for valor, grp in df.groupby(col_grupo, dropna=False):
        m = calcular_metricas(grp)
        m[col_grupo] = valor
        filas.append(m)
    res = pd.DataFrame(filas)
    cols_orden = [
        col_grupo, "pedidos", "ventas_usd", "ticket_medio_usd", "usd_por_km",
        "reclamos_n", "tasa_reclamos_x1000", "otd_pct",
        "tiempo_entrega_media", "tiempo_entrega_mediana", "tiempo_entrega_p90",
        "tiempo_atencion_media", "muestra_pequena",
    ]
    return res[[c for c in cols_orden if c in res.columns]]


def semaforo_kpi(valor, verde, amarillo, menor_es_mejor=False):
    if valor is None or pd.isna(valor):
        return "⚪ Sin dato", "#64748b", "rgba(100,116,139,0.12)"
    if not menor_es_mejor:
        if valor >= verde:
            return "🟢 Óptimo (En meta)", "#15803d", "rgba(21,128,61,0.12)"
        if valor >= amarillo:
            return "🟡 Alerta (Seguimiento)", "#b45309", "rgba(180,83,9,0.12)"
        return "🔴 Crítico (Bajo umbral)", "#b91c1c", "rgba(185,28,28,0.12)"
    else:
        if valor <= verde:
            return "🟢 Óptimo (Controlado)", "#15803d", "rgba(21,128,61,0.12)"
        if valor <= amarillo:
            return "🟡 Alerta (Riesgo moderado)", "#b45309", "rgba(180,83,9,0.12)"
        return "🔴 Crítico (Excede umbral)", "#b91c1c", "rgba(185,28,28,0.12)"


# ==========================================
# 4. LOCALIZACIÓN DEL ARCHIVO Y PARÁMETROS SLA
# ==========================================
CARPETA_ACTUAL = Path(__file__).resolve().parent
archivos_locales = sorted(
    [p for p in CARPETA_ACTUAL.iterdir() if p.suffix.lower() in (".csv", ".xlsx", ".xls")]
)

with st.sidebar:
    st.header("⚙️ Parámetros y Supuestos")
    if archivos_locales:
        archivo_sel = st.selectbox(
            "Dataset del repositorio",
            archivos_locales,
            format_func=lambda p: p.name,
        )
        subido = st.file_uploader("…o cargar otro archivo (.csv / .xlsx)", type=["csv", "xlsx", "xls"])
    else:
        archivo_sel = None
        subido = st.file_uploader("Cargar dataset de LogiAndes (.csv / .xlsx)", type=["csv", "xlsx", "xls"])

    st.divider()
    st.subheader("⏱️ Supuesto SLA por Canal (min)")
    st.caption(
        "El dataset no incluye una columna binaria de OTD. Se deriva comparando "
        "`tiempo_individual_entrega_min` contra el SLA de cada canal (basado en sus medianas de 87, 134 y 157 min)."
    )
    sla_express = st.number_input("SLA Express (min)", min_value=30, max_value=300, value=120, step=5)
    sla_estandar = st.number_input("SLA Estándar urbano (min)", min_value=60, max_value=360, value=180, step=5)
    sla_programado = st.number_input("SLA Programado (min)", min_value=60, max_value=420, value=210, step=5)
    meta_otd_global = st.slider("Meta de cumplimiento OTD (%)", min_value=70, max_value=98, value=85, step=1)
    umbral_reclamos = st.number_input("Umbral meta de reclamos (/1.000)", min_value=5.0, max_value=60.0, value=25.0, step=2.5)

if subido is not None:
    df_raw = cargar_datos(subido, subido.name)
    nombre_fuente = subido.name
elif archivo_sel is not None:
    df_raw = cargar_datos(archivo_sel, archivo_sel.name)
    nombre_fuente = archivo_sel.name
else:
    st.info("Sube el archivo CSV o Excel de **LogiAndes S.A.** en la barra lateral para iniciar.")
    st.stop()

faltantes = [c for c in COLUMNAS_ESPERADAS if c not in df_raw.columns]
if faltantes:
    st.error(f"El archivo cargado no contiene las columnas esperadas del caso: {', '.join(faltantes)}")
    st.stop()

sla_activo = {
    "Express": sla_express,
    "Estándar urbano": sla_estandar,
    "Programado": sla_programado,
}
df_base = aplicar_sla(df_raw, sla_activo)

# ==========================================
# 5. CABECERA Y FILTROS GLOBALES CONCISOS
# ==========================================
st.markdown(
    f"""
    <div class='top-header'>
        <div class='brand-box'>
            <div class='brand-badge'>LA</div>
            <div>
                <div class='main-title'>LogiAndes S.A. · Sistema de Inteligencia de Negocios</div>
                <div class='sub-title'>
                    Nivel de análisis disponible en datos: <b>Provincial</b> (Pichincha, Guayas, Azuay, Manabí, Tungurahua, Loja)
                    · Fuente activa: <b>{nombre_fuente}</b> ({len(df_base):,} pedidos)
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.2, 1.8, 1.5, 0.55], vertical_alignment="bottom")
    with f1:
        meses_disp = sorted(df_base["anio_mes"].dropna().unique())
        sel_meses = st.multiselect("📅 Mes (2025)", meses_disp, default=[], placeholder="Todos (Ene–Mar)")
    with f2:
        prov_disp = sorted(df_base["provincia"].dropna().unique())
        sel_prov = st.multiselect("📍 Provincia", prov_disp, default=[], placeholder="Todas las provincias")
    with f3:
        canal_disp = sorted(df_base["canal_entrega"].dropna().unique())
        sel_canal = st.multiselect("🚚 Canal de entrega", canal_disp, default=[], placeholder="Todos los canales")
    with f4:
        if st.button("↺ Todo", **AN_BTN):
            st.rerun()

d = df_base.copy()
if sel_meses:
    d = d[d["anio_mes"].isin(sel_meses)]
if sel_prov:
    d = d[d["provincia"].isin(sel_prov)]
if sel_canal:
    d = d[d["canal_entrega"].isin(sel_canal)]

if d.empty:
    st.warning("La combinación de filtros no devuelve pedidos.")
    st.stop()

HAY_FILTRO = len(d) != len(df_base)
M_ACT = calcular_metricas(d)
M_NAC = calcular_metricas(df_base)

st.caption(
    f"Mostrando **{M_ACT['pedidos']:,}** de **{M_NAC['pedidos']:,}** pedidos ({M_ACT['pedidos']/M_NAC['pedidos']:.1%}) · "
    f"SLA activo: Express ≤ {sla_express} min | Estándar urbano ≤ {sla_estandar} min | Programado ≤ {sla_programado} min."
)


def render_kpi_card(col, titulo, valor_txt, sub_txt, sem_tuple, ayuda):
    with col.container(border=True):
        st.metric(label=titulo, value=valor_txt, delta=sub_txt, delta_color="off", help=ayuda)
        txt_s, col_s, bg_s = sem_tuple
        st.markdown(
            f"<span class='semaforo-pill' style='color:{col_s};background:{bg_s};'>{txt_s}</span>",
            unsafe_allow_html=True,
        )


# ==========================================
# 6. PESTAÑAS DE NAVEGACIÓN (4 NIVELES)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ 1. Visión Ejecutiva",
    "🗺️ 2. Diagnóstico Territorial y Comercial",
    "🔧 3. Detalle Operativo y Motivos de Reclamo",
    "📋 4. Ficha Técnica BI & Gobernanza",
])

# ------------------------------------------
# NIVEL 1: VISIÓN EJECUTIVA
# ------------------------------------------
with tab1:
    k1, k2, k3, k4, k5 = st.columns(5)

    # Semáforos independientes y coherentes con los datos reales
    sem_ticket = semaforo_kpi(M_ACT["ticket_medio_usd"], verde=M_NAC["ticket_medio_usd"] * 0.98, amarillo=M_NAC["ticket_medio_usd"] * 0.90)
    sem_prod = semaforo_kpi(M_ACT["usd_por_km"], verde=M_NAC["usd_por_km"] * 0.98, amarillo=M_NAC["usd_por_km"] * 0.88)
    sem_otd = semaforo_kpi(M_ACT["otd_pct"], verde=meta_otd_global, amarillo=meta_otd_global - 10.0)
    sem_recl = semaforo_kpi(M_ACT["tasa_reclamos_x1000"], verde=umbral_reclamos, amarillo=50.0, menor_es_mejor=True)
    sem_tiempo = semaforo_kpi(M_ACT["tiempo_entrega_p90"], verde=180.0, amarillo=220.0, menor_es_mejor=True)

    render_kpi_card(
        k1,
        "1. Ventas Asociadas (US$)",
        f"${M_ACT['ventas_usd']:,.0f}",
        f"Ticket medio: ${M_ACT['ticket_medio_usd']:,.2f} / pedido",
        sem_ticket,
        "Suma de `ventas_asociadas_usd`. Limitación declarada: el CSV no desglosa devoluciones ni impuestos para separar venta bruta de neta.",
    )
    render_kpi_card(
        k2,
        "2. Productividad Logística",
        f"${M_ACT['usd_por_km']:,.2f} / km",
        f"Ritmo: {M_ACT['min_por_km']:,.1f} min/km recorridos",
        sem_prod,
        "Sustituye al Margen Bruto (no disponible en el dataset) midiendo el ingreso generado por cada kilómetro recorrido (`Σ ventas_asociadas_usd / Σ distancia_km`).",
    )
    render_kpi_card(
        k3,
        f"3. Entrega a Tiempo (Meta ≥ {meta_otd_global}%)",
        f"{M_ACT['otd_pct']:.1f}%",
        f"{M_ACT['otd_pct'] - M_NAC['otd_pct']:+.1f} pp vs. nacional" if HAY_FILTRO else f"SLA por canal activo",
        sem_otd,
        "Porcentaje de pedidos donde `tiempo_individual_entrega_min <= SLA_canal`. Se actualiza dinámicamente con la meta lateral.",
    )
    render_kpi_card(
        k4,
        "4. Reclamos / 1.000 pedidos",
        f"{M_ACT['tasa_reclamos_x1000']:.1f}",
        f"Eventos: n = {M_ACT['reclamos_n']} de {M_ACT['pedidos']:,}" + (" ⚠️ Muestra baja" if M_ACT["muestra_pequena"] else ""),
        sem_recl,
        f"Tasa relativizada `(Σ reclamos_registrados / Total pedidos) * 1.000`. Umbral verde ≤ {umbral_reclamos:.1f}.",
    )
    render_kpi_card(
        k5,
        "5. Tiempo Entrega (Mediana / P90)",
        f"{M_ACT['tiempo_entrega_mediana']:.0f} min (P90: {M_ACT['tiempo_entrega_p90']:.0f})",
        f"Media: {M_ACT['tiempo_entrega_media']:.1f} min · Atención: {M_ACT['tiempo_atencion_media']:.1f} min",
        sem_tiempo,
        "Mediana y Percentil 90 de `tiempo_individual_entrega_min`. Evita ocultar las colas largas (hasta 520 min) detrás del promedio.",
    )

    if M_ACT["muestra_pequena"]:
        st.warning(
            f"⚠️ **Advertencia de estabilidad estadística (Gobernanza):** La selección actual contiene solo **n = {M_ACT['reclamos_n']} reclamos** "
            f"en **{M_ACT['pedidos']:,} pedidos**. Las tasas calculadas con menos de {MIN_EVENTOS_ESTABLE} eventos (como ocurre en Tungurahua con n=8 o Azuay con n=13) "
            "tienen alta varianza muestral y no deben usarse aisladamente para decisiones punitivas."
        )

    # Síntesis ejecutiva automática basada en los datos reales
    df_prov_exec = resumen_agrupado(d, "provincia")
    if len(df_prov_exec) > 1:
        p_max_recl_abs = df_prov_exec.loc[df_prov_exec["reclamos_n"].idxmax()]
        p_max_recl_tasa = df_prov_exec.loc[df_prov_exec["tasa_reclamos_x1000"].idxmax()]
        p_lenta = df_prov_exec.loc[df_prov_exec["tiempo_entrega_media"].idxmax()]
        st.info(
            f"📌 **Hallazgo clave del caso (Conteo vs. Tasa):** **{p_max_recl_abs['provincia']}** registra el mayor volumen absoluto de reclamos "
            f"(**n = {int(p_max_recl_abs['reclamos_n'])}**), pero al relativizar por cada 1.000 pedidos el foco crítico real es "
            f"**{p_max_recl_tasa['provincia']}** (**{p_max_recl_tasa['tasa_reclamos_x1000']:.1f} / 1.000**, n = {int(p_max_recl_tasa['reclamos_n'])}). "
            f"Además, las plazas con mayores tiempos medios de entrega —lideradas por **{p_lenta['provincia']}** ({p_lenta['tiempo_entrega_media']:.0f} min)— "
            "son exactamente las que concentran las mayores tasas de reclamo."
        )

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Tasa de reclamos por 1.000 pedidos vs. Conteo absoluto (n)")
            df_r = df_prov_exec.sort_values("tasa_reclamos_x1000", ascending=True).copy()
            df_r["etiqueta"] = df_r.apply(
                lambda r: f"{r['tasa_reclamos_x1000']:.1f} (n={int(r['reclamos_n'])}{' *' if r['muestra_pequena'] else ''})",
                axis=1,
            )
            fig_r = px.bar(
                df_r, x="tasa_reclamos_x1000", y="provincia", orientation="h",
                text="etiqueta", color="tasa_reclamos_x1000",
                color_continuous_scale=["#16a34a", "#eab308", "#dc2626"],
                range_color=[0, 70],
            )
            fig_r.add_vline(x=umbral_reclamos, line_dash="dash", line_color="#15803d", annotation_text=f"Meta ≤ {umbral_reclamos:.0f}")
            fig_r.add_vline(x=50, line_dash="dot", line_color="#dc2626", annotation_text="Crítico > 50")
            fig_r.update_layout(
                height=350, margin=dict(l=10, r=20, t=20, b=10),
                coloraxis_showscale=False, yaxis_title=None,
                xaxis_title="Reclamos por cada 1.000 pedidos (entre paréntesis: eventos absolutos n)",
            )
            st.plotly_chart(fig_r, **AN_PLOT)
            st.caption("(*) Provincias con n < 15 eventos absolutos: tasa sujeta a alta sensibilidad muestral.")

    with c2:
        with st.container(border=True):
            st.subheader("Tiempo medio de entrega (min) y % Entrega a Tiempo (OTD)")
            df_t = df_prov_exec.sort_values("tiempo_entrega_media", ascending=True).copy()
            df_t["etiqueta_t"] = df_t.apply(
                lambda r: f"{r['tiempo_entrega_media']:.0f} min (OTD: {r['otd_pct']:.1f}%)",
                axis=1,
            )
            fig_t = px.bar(
                df_t, x="tiempo_entrega_media", y="provincia", orientation="h",
                text="etiqueta_t", color="otd_pct",
                color_continuous_scale="RdYlGn", range_color=[50, 100],
            )
            fig_t.update_layout(
                height=350, margin=dict(l=10, r=20, t=20, b=10),
                coloraxis_colorbar=dict(title="OTD %"),
                yaxis_title=None, xaxis_title="Tiempo individual medio de entrega (minutos)",
            )
            st.plotly_chart(fig_t, **AN_PLOT)
            st.caption("El color refleja el % de cumplimiento OTD según el SLA específico de cada canal; la barra mide los minutos promedio.")

    c3, c4 = st.columns([1.15, 1])
    with c3:
        with st.container(border=True):
            st.subheader("Evolución mensual de Ventas Asociadas vs. Referencia Ene–Feb")
            st.caption(
                "**Nota metodológica:** El archivo no contiene cuota presupuestaria (`Meta_Venta`). "
                "La línea punteada muestra el promedio mensual Ene–Feb como referencia interna comparativa, no como cuota oficial."
            )
            m_mes = resumen_agrupado(d, "anio_mes").sort_values("anio_mes")
            ref_ene_feb = m_mes[m_mes["anio_mes"].isin(["2025-01", "2025-02"])]["ventas_usd"].mean()
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(
                x=m_mes["anio_mes"], y=m_mes["ventas_usd"],
                text=[f"${v:,.0f}<br>({p:,} ped.)" for v, p in zip(m_mes["ventas_usd"], m_mes["pedidos"])],
                textposition="auto", name="Ventas asociadas (US$)", marker_color="#2563eb",
            ))
            if pd.notna(ref_ene_feb):
                fig_m.add_hline(
                    y=ref_ene_feb, line_dash="dash", line_color="#d97706",
                    annotation_text=f"Ref. media Ene-Feb: ${ref_ene_feb:,.0f}",
                )
            fig_m.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Ventas asociadas (US$)", xaxis_title="Mes")
            st.plotly_chart(fig_m, **AN_PLOT)

    with c4:
        with st.container(border=True):
            st.subheader("Ventas asociadas y Productividad (US$/km) por Provincia")
            df_v = df_prov_exec.sort_values("ventas_usd", ascending=True).copy()
            df_v["txt_v"] = df_v.apply(lambda r: f"${r['ventas_usd']:,.0f} (${r['usd_por_km']:.2f}/km)", axis=1)
            fig_v = px.bar(
                df_v, x="ventas_usd", y="provincia", orientation="h",
                text="txt_v", color="usd_por_km", color_continuous_scale="Blues",
            )
            fig_v.update_layout(
                height=345, margin=dict(l=10, r=20, t=20, b=10),
                coloraxis_colorbar=dict(title="US$/km"), yaxis_title=None, xaxis_title="Ventas asociadas (US$)",
            )
            st.plotly_chart(fig_v, **AN_PLOT)

    st.download_button(
        "📥 Descargar tabla resumen ejecutiva por provincia (CSV)",
        data=df_prov_exec.to_csv(index=False).encode("utf-8-sig"),
        file_name="resumen_ejecutivo_provincial_logiandes.csv",
        mime="text/csv",
    )

# ------------------------------------------
# NIVEL 2: DIAGNÓSTICO TERRITORIAL Y COMERCIAL
# ------------------------------------------
with tab2:
    with st.container(border=True):
        tc1, tc2 = st.columns([1.6, 1.4])
        with tc1:
            seg_disp = sorted(d["tipo_cliente"].dropna().unique())
            sel_seg = st.multiselect(
                "🏢 Filtro de Nivel 2 · Segmento de Cliente (`tipo_cliente`)",
                seg_disp, default=[], placeholder="Todos los segmentos (Comercio minorista, PyME, Corporativo)",
            )
        with tc2:
            reg_disp = sorted(d["region"].dropna().unique())
            sel_reg = st.multiselect(
                "🗺️ Filtro de Nivel 2 · Región natural (`region`)",
                reg_disp, default=[], placeholder="Todas las regiones",
            )

    d_terr = d.copy()
    if sel_seg:
        d_terr = d_terr[d_terr["tipo_cliente"].isin(sel_seg)]
    if sel_reg:
        d_terr = d_terr[d_terr["region"].isin(sel_reg)]

    if d_terr.empty:
        st.warning("No hay registros para el segmento o región seleccionados.")
    else:
        g1, g2 = st.columns([1.15, 1])
        with g1:
            with st.container(border=True):
                st.subheader("🎯 Tiempo Medio de Entrega vs. Tasa de Reclamos por Provincia")
                df_sc = resumen_agrupado(d_terr, "provincia")
                fig_sc = px.scatter(
                    df_sc,
                    x="tiempo_entrega_media",
                    y="tasa_reclamos_x1000",
                    size="pedidos",
                    color="otd_pct",
                    text="provincia",
                    color_continuous_scale="RdYlGn",
                    range_color=[50, 100],
                    size_max=48,
                    hover_data={
                        "pedidos": ":,",
                        "reclamos_n": True,
                        "ventas_usd": ":$,.0f",
                        "tiempo_entrega_p90": ":.0f",
                    },
                )
                fig_sc.add_hline(y=umbral_reclamos, line_dash="dash", line_color="#15803d", annotation_text="Umbral 25/1.000")
                fig_sc.update_traces(textposition="top center")
                fig_sc.update_layout(
                    height=390, margin=dict(l=10, r=10, t=25, b=10),
                    xaxis_title="Tiempo individual medio de entrega (minutos)",
                    yaxis_title="Tasa de reclamos por 1.000 pedidos",
                    coloraxis_colorbar=dict(title="OTD %"),
                )
                st.plotly_chart(fig_sc, **AN_PLOT)
                st.caption(
                    "**Evidencia empírica:** Loja (170 min) y Manabí (162 min) se ubican en el cuadrante superior derecho "
                    "(mayor demora y mayor tasa de reclamos), mientras Tungurahua (109 min), Azuay (112 min) y Pichincha (123 min) "
                    "mantienen tiempos bajos y tasas controladas (< 20 por 1.000)."
                )

        with g2:
            with st.container(border=True):
                st.subheader("🏢 Desempeño por Segmento (`tipo_cliente`) y Canal")
                piv_seg = (
                    d_terr.groupby(["provincia", "tipo_cliente"], as_index=False)
                    .agg(
                        pedidos=("pedido_id", "count"),
                        ventas_usd=("ventas_asociadas_usd", "sum"),
                        reclamos_n=("reclamos_registrados", "sum"),
                    )
                )
                piv_seg["tasa_x1000"] = piv_seg["reclamos_n"] / piv_seg["pedidos"] * 1000
                fig_seg = px.bar(
                    piv_seg, x="provincia", y="ventas_usd", color="tipo_cliente",
                    barmode="stack", text_auto=".2s",
                    hover_data={"pedidos": ":,", "reclamos_n": True, "tasa_x1000": ":.1f"},
                )
                fig_seg.update_layout(
                    height=390, margin=dict(l=10, r=10, t=25, b=10),
                    xaxis_title=None, yaxis_title="Ventas asociadas (US$)", legend_title_text="Tipo de cliente",
                )
                st.plotly_chart(fig_seg, **AN_PLOT)
                st.caption("`tipo_cliente` es una variable de segmentación B2B (Comercio minorista, PyME, Corporativo), no un dato personal.")

        with st.container(border=True):
            st.subheader("📋 Tabla Comparativa Territorial Completa (con conteo de eventos y productividad)")
            tabla_prov = resumen_agrupado(d_terr, "provincia").sort_values("ventas_usd", ascending=False)
            st.dataframe(
                tabla_prov,
                hide_index=True,
                **AN_DF,
                column_config={
                    "provincia": "Provincia",
                    "pedidos": st.column_config.NumberColumn("Pedidos", format="%d"),
                    "ventas_usd": st.column_config.NumberColumn("Ventas Asociadas (US$)", format="$ %.0f"),
                    "ticket_medio_usd": st.column_config.NumberColumn("Venta / Pedido", format="$ %.2f"),
                    "usd_por_km": st.column_config.NumberColumn("Productividad (US$/km)", format="$ %.2f"),
                    "reclamos_n": st.column_config.NumberColumn("Reclamos (n)", format="%d"),
                    "tasa_reclamos_x1000": st.column_config.NumberColumn("Tasa / 1.000", format="%.1f"),
                    "otd_pct": st.column_config.ProgressColumn("OTD (%)", min_value=0, max_value=100, format="%.1f%%"),
                    "tiempo_entrega_media": st.column_config.NumberColumn("Media Entrega (min)", format="%.1f"),
                    "tiempo_entrega_mediana": st.column_config.NumberColumn("Mediana (min)", format="%.0f"),
                    "tiempo_entrega_p90": st.column_config.NumberColumn("P90 Entrega (min)", format="%.0f"),
                    "tiempo_atencion_media": st.column_config.NumberColumn("Media Atención (min)", format="%.1f"),
                    "muestra_pequena": st.column_config.CheckboxColumn("Alerta n<15"),
                },
            )

# ------------------------------------------
# NIVEL 3: DETALLE OPERATIVO Y MOTIVOS DE RECLAMO
# ------------------------------------------
with tab3:
    with st.container(border=True):
        co1, co2, co3 = st.columns([1.5, 1.5, 1.3], vertical_alignment="bottom")
        with co1:
            filtro_op = st.selectbox(
                "🔎 Filtro de incidencias operativas",
                ["Todos los pedidos", "Solo pedidos con reclamo (n=187 nacional)", "Solo entregas fuera de SLA (OTD = 0)"],
            )
        with co2:
            motivos_disp = sorted(d["motivo_reclamo"].dropna().unique())
            sel_motivo = st.multiselect(
                "📣 Filtrar por `motivo_reclamo`",
                motivos_disp, default=[], placeholder="Todos los motivos registrados",
            )
        with co3:
            mostrar_pedido_id = st.toggle(
                "🔓 Mostrar `pedido_id` individual (Modo Auditoría)",
                value=False,
                help="El dataset no contiene nombres ni cédulas. El único identificador individual trazable es `pedido_id`, que se oculta en la vista estándar.",
            )

    d_op = d.copy()
    if filtro_op.startswith("Solo pedidos con reclamo"):
        d_op = d_op[d_op["reclamos_registrados"] == 1]
    elif filtro_op.startswith("Solo entregas fuera de SLA"):
        d_op = d_op[d_op["entrega_a_tiempo"] == 0]
    if sel_motivo:
        d_op = d_op[d_op["motivo_reclamo"].isin(sel_motivo)]

    o1, o2 = st.columns(2)
    with o1:
        with st.container(border=True):
            st.subheader("📦 Dispersión de Tiempos de Entrega (minutos) por Provincia")
            fig_box_p = px.box(
                d, x="provincia", y="tiempo_individual_entrega_min", color="provincia", points="outliers",
                category_orders={"provincia": ["Loja", "Manabí", "Guayas", "Pichincha", "Azuay", "Tungurahua"]},
            )
            fig_box_p.update_layout(
                height=360, margin=dict(l=10, r=10, t=20, b=10), showlegend=False,
                xaxis_title=None, yaxis_title="Tiempo individual de entrega (minutos)",
            )
            st.plotly_chart(fig_box_p, **AN_PLOT)
            st.caption(
                "El máximo alcanza **520 minutos** frente a una media nacional de **132 minutos**. "
                "Los diagramas de caja exponen las colas largas y valores atípicos que el promedio oculta."
            )

    with o2:
        with st.container(border=True):
            st.subheader("🚚 Tiempos de Entrega (minutos) por Canal vs. Promesa SLA")
            fig_box_c = px.box(
                d, x="canal_entrega", y="tiempo_individual_entrega_min", color="canal_entrega", points="outliers",
                category_orders={"canal_entrega": ["Express", "Estándar urbano", "Programado"]},
            )
            for canal_k, valor_sla in sla_activo.items():
                fig_box_c.add_hline(
                    y=valor_sla, line_dash="dot",
                    annotation_text=f"SLA {canal_k}: {valor_sla} min",
                    annotation_position="top right",
                )
            fig_box_c.update_layout(
                height=360, margin=dict(l=10, r=10, t=20, b=10), showlegend=False,
                xaxis_title=None, yaxis_title="Tiempo individual de entrega (minutos)",
            )
            st.plotly_chart(fig_box_c, **AN_PLOT)
            st.caption(
                "**Prevención de sesgo por canal:** Las medianas reales son **87 min (Express)**, **134 min (Estándar urbano)** "
                "y **157 min (Programado)**. Evaluarlos con un SLA único sesgaría artificialmente al canal Programado."
            )

    # Análisis profundo de motivo_reclamo y tiempo_atencion_min (Variables clave señaladas por el experto)
    m1, m2 = st.columns([1.15, 1])
    with m1:
        with st.container(border=True):
            st.subheader("📣 Desglose de `motivo_reclamo`: Operaciones vs. Comunicación/Atención")
            recl_df = d[d["reclamos_registrados"] == 1].copy()
            if recl_df.empty:
                st.info("No hay reclamos registrados en la selección actual.")
            else:
                recl_df["naturaleza"] = np.where(
                    recl_df["motivo_reclamo"].isin(MOTIVOS_OPERATIVOS),
                    "1. Falla Operativa / Ruta",
                    "2. Falla de Comunicación / Atención",
                )
                conteo_mot = (
                    recl_df.groupby(["motivo_reclamo", "naturaleza"], as_index=False)
                    .agg(casos=("pedido_id", "count"), atencion_media=("tiempo_atencion_min", "mean"))
                    .sort_values("casos", ascending=True)
                )
                conteo_mot["pct"] = conteo_mot["casos"] / conteo_mot["casos"].sum() * 100
                conteo_mot["etiqueta"] = conteo_mot.apply(
                    lambda r: f"{int(r['casos'])} casos ({r['pct']:.1f}%) · Atención: {r['atencion_media']:.1f} min",
                    axis=1,
                )
                fig_mot = px.bar(
                    conteo_mot, x="casos", y="motivo_reclamo", color="naturaleza", orientation="h",
                    text="etiqueta", color_discrete_map={
                        "1. Falla Operativa / Ruta": "#dc2626",
                        "2. Falla de Comunicación / Atención": "#2563eb",
                    },
                )
                fig_mot.update_layout(
                    height=340, margin=dict(l=10, r=20, t=20, b=10),
                    xaxis_title="Número de reclamos registrados (casos)", yaxis_title=None,
                    legend_title_text="Responsabilidad primaria",
                )
                st.plotly_chart(fig_mot, **AN_PLOT)
                st.caption(
                    "**Hallazgo accionable:** De los 187 reclamos nacionales, **119 casos (63,6%)** corresponden a ejecución física "
                    "(*Demora en entrega*: 69, *Paquete con incidencia*: 29, *Incumplimiento de horario*: 21) y **68 casos (36,4%)** "
                    "a gestión informativa y soporte (*Falta de actualización*: 52, *Demora en atención*: 16)."
                )

    with m2:
        with st.container(border=True):
            st.subheader("🔥 Matriz Provincia × Motivo de Reclamo (Conteo de casos)")
            if recl_df.empty:
                st.info("Sin casos para construir la matriz.")
            else:
                piv_mot = pd.crosstab(recl_df["provincia"], recl_df["motivo_reclamo"])
                fig_hm = px.imshow(piv_mot, text_auto=True, aspect="auto", color_continuous_scale="Reds")
                fig_hm.update_layout(
                    height=340, margin=dict(l=10, r=10, t=20, b=10),
                    xaxis_title=None, yaxis_title=None, coloraxis_showscale=False,
                )
                st.plotly_chart(fig_hm, **AN_PLOT)
                st.caption("Permite focalizar si una provincia requiere intervención en ruteo físico o en notificaciones proactivas al cliente.")

    with st.container(border=True):
        st.subheader("🔎 Consulta Granular Gobernada de Pedidos")
        vista_op = d_op.copy()
        if not mostrar_pedido_id and "pedido_id" in vista_op.columns:
            vista_op = vista_op.drop(columns=["pedido_id"])
            st.caption(
                "🔒 **Gobernanza aplicada sobre columnas reales:** El dataset no incluye nombres personales ni cédulas; "
                "se oculta `pedido_id` por defecto en la vista estándar para priorizar el análisis agregado sobre el rastreo individual."
            )
        st.dataframe(vista_op, height=320, hide_index=True, **AN_DF)
        st.download_button(
            "📥 Descargar registros operativos filtrados (CSV)",
            data=vista_op.to_csv(index=False).encode("utf-8-sig"),
            file_name="detalle_operativo_logiandes.csv",
            mime="text/csv",
        )

# ------------------------------------------
# NIVEL 4: FICHA TÉCNICA BI & GOBERNANZA HONESTA
# ------------------------------------------
with tab4:
    with st.container(border=True):
        st.subheader("1. Transparencia Documental: Qué traen los datos reales y cómo se cierran las brechas")
        st.markdown(
            """
            Siguiendo buenas prácticas de auditoría de datos, este sistema **no inventa fuentes inexistentes** (no asume conexiones fantasma a ERPs o contabilidad analítica) ni fuerza nombres engañosos. Toda métrica proviene exclusivamente del archivo transaccional de **5.798 pedidos** (`Enero–Marzo 2025`) declarando explícitamente sus alcances y supuestos:
            * **Nivel geográfico real (`provincia` y `region`):** Aunque el contexto narrativo menciona ciudades como Quito, Guayaquil, Cuenca, Manta, Ambato y Loja, el dataset registra únicamente la **Provincia** (`Pichincha, Guayas, Azuay, Manabí, Tungurahua, Loja`). Por honestidad metodológica, el nivel territorial se expresa como provincial.
            * **De "Venta Neta" a `ventas_asociadas_usd`:** El archivo provee el monto económico asociado al pedido, pero no incluye columnas de impuestos, descuentos ni devoluciones. Se reporta como **Ventas Asociadas (US$)** y **Venta por Pedido (Ticket Medio)**.
            * **De "Margen Bruto" a Productividad por Kilómetro (`US$ / km`):** Al no existir costos directos en el CSV, fabricar un margen contable sería especulativo. Se reemplaza por un KPI físico-financiero verificable: **Ventas Asociadas por Kilómetro Recorrido** (`Σ ventas_asociadas_usd ÷ Σ distancia_km`).
            * **Derivación defendible de Entrega a Tiempo (OTD %):** Al no existir una marca binaria precalculada, se define en función de la distribución empírica de `tiempo_individual_entrega_min` por `canal_entrega`: **Express ≤ 120 min** (mediana real: 87 min), **Estándar urbano ≤ 180 min** (mediana real: 134 min) y **Programado ≤ 210 min** (mediana real: 157 min).
            """
        )

    with st.container(border=True):
        st.subheader("2. Ficha Técnica Auditada de los 5 KPIs del Sistema")
        ficha_honesta = pd.DataFrame([
            {
                "Indicador (KPI)": "1. Ventas Asociadas y Ticket Medio (US$)",
                "Objetivo": "Medir el valor económico movilizado por los pedidos logísticos en cada provincia, canal y segmento B2B.",
                "Fórmula Exacta": "Σ ventas_asociadas_usd  |  Ticket Medio = Σ ventas_asociadas_usd ÷ Total_Pedidos",
                "Columnas Fuente (CSV)": "ventas_asociadas_usd, pedido_id",
                "Supuesto / Limitación Declarada": "El CSV no separa venta bruta de neta ni incluye notas de crédito.",
                "Meta / Referencia": "Referencia interna: promedio mensual Ene–Feb ($386.6k/mes) y ticket nacional ($200,82).",
                "Umbral Semáforo": "🟢 ≥ 98% del ticket nacional | 🟡 90%–97,9% | 🔴 < 90%",
                "Responsable": "Dirección Comercial",
            },
            {
                "Indicador (KPI)": "2. Productividad Logística (US$ / km)",
                "Objetivo": "Evaluar la densidad económica por kilómetro recorrido ante la ausencia de datos de costo/margen bruto.",
                "Fórmula Exacta": "Σ ventas_asociadas_usd ÷ Σ distancia_km  (Complemento: Σ tiempo_individual_entrega_min ÷ Σ distancia_km)",
                "Columnas Fuente (CSV)": "ventas_asociadas_usd, distancia_km, tiempo_individual_entrega_min",
                "Supuesto / Limitación Declarada": "Sustituye al Margen Bruto contable con una métrica real de eficiencia de ruteo.",
                "Meta / Referencia": "Referencia nacional: ~$16,15 US$/km.",
                "Umbral Semáforo": "🟢 ≥ 98% media nacional | 🟡 88%–97,9% | 🔴 < 88%",
                "Responsable": "Operaciones y Finanzas",
            },
            {
                "Indicador (KPI)": "3. Entrega a Tiempo – OTD (%) por SLA de Canal",
                "Objetivo": "Cuantificar la confiabilidad de entrega respetando la promesa operativa distinta de cada canal.",
                "Fórmula Exacta": "Promedio(tiempo_individual_entrega_min ≤ SLA_canal) × 100",
                "Columnas Fuente (CSV)": "tiempo_individual_entrega_min, canal_entrega",
                "Supuesto / Limitación Declarada": "SLA derivado de percentiles propios del dataset: Express ≤ 120m, Estándar ≤ 180m, Programado ≤ 210m.",
                "Meta / Referencia": "≥ 85% de pedidos dentro del SLA de su canal.",
                "Umbral Semáforo": "🟢 ≥ 85% | 🟡 75%–84,9% | 🔴 < 75%",
                "Responsable": "Gerencia de Operaciones",
            },
            {
                "Indicador (KPI)": "4. Tasa de Reclamos por 1.000 Pedidos",
                "Objetivo": "Comparar la incidencia de reclamos entre provincias de distinto tamaño sin el sesgo del conteo bruto.",
                "Fórmula Exacta": "(Σ reclamos_registrados ÷ Total_Pedidos) × 1.000",
                "Columnas Fuente (CSV)": "reclamos_registrados, motivo_reclamo",
                "Supuesto / Limitación Declarada": "Se reporta junto al conteo absoluto (n). Si n < 15 se activa alerta de inestabilidad muestral.",
                "Meta / Referencia": "≤ 25,0 reclamos por cada 1.000 pedidos (Nacional actual: 32,3).",
                "Umbral Semáforo": "🟢 ≤ 25,0 | 🟡 25,1–50,0 | 🔴 > 50,0 (Manabí: 66,3)",
                "Responsable": "Atención al Cliente",
            },
            {
                "Indicador (KPI)": "5. Tiempo de Entrega Mediano y P90 (min)",
                "Objetivo": "Monitorear la velocidad real de entrega y la cola de demoras extremas (outliers de hasta 520 min).",
                "Fórmula Exacta": "Mediana(tiempo_individual_entrega_min) y Percentil_90(tiempo_individual_entrega_min)",
                "Columnas Fuente (CSV)": "tiempo_individual_entrega_min, tiempo_atencion_min",
                "Supuesto / Limitación Declarada": "Expresado estrictamente en minutos. Se acompaña de la media de atención al cliente.",
                "Meta / Referencia": "P90 ≤ 180 min a nivel consolidado.",
                "Umbral Semáforo": "🟢 P90 ≤ 180 min | 🟡 181–220 min | 🔴 > 220 min",
                "Responsable": "Gerencia de Operaciones",
            },
        ])
        st.dataframe(ficha_honesta, hide_index=True, **AN_DF)

    with st.container(border=True):
        st.subheader("3. Reflexión Metodológica: Sesgos, Muestras Pequeñas y Gobernanza Real")
        r1, r2 = st.columns(2)
        with r1:
            st.markdown(
                """
                * **Conteo bruto vs. Tasa relativizada:** Guayas acumula **71 reclamos** frente a **47 de Manabí**, pero Guayas procesa un volumen mucho mayor de pedidos. En términos relativos, **Manabí (66,3 / 1.000)** y **Loja (47,0 / 1.000)** superan a **Guayas (41,5 / 1.000)**.
                * **Advertencia sobre muestras pequeñas ($n < 15$):** Tungurahua registra solo **8 reclamos** (tasa de 12,7) y Azuay **13 reclamos** (tasa de 16,2). Con un denominador pequeño, un par de eventos adicionales alteran drásticamente la tasa, por lo que el dashboard exige mostrar siempre `n` junto a la tasa.
                """
            )
        with r2:
            st.markdown(
                """
                * **Sesgo de canal de entrega:** Comparar tiempos de entrega sin separar `Express` (mediana 87 min), `Estándar urbano` (134 min) y `Programado` (157 min) castigaría erróneamente a las provincias con mayor mezcla de envíos programados.
                * **Gobernanza sin falsos positivos:** Se corrigió el filtro que ocultaba `tipo_cliente` (que es un segmento corporativo/PyME/minorista y no un dato personal). La gobernanza real se aplica sobre `pedido_id` y sobre la prohibición de tomar decisiones punitivas con tamaños muestrales insuficientes o correlaciones macroeconómicas externas (BCE/INEC) no causales.
                """
            )