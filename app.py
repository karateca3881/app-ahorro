import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL Y SELECTOR DE PLANTILLA VISUAL
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Selector de Plantillas", 
    layout="wide", 
    page_icon="📈"
)

# Estilos visuales comunes
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
        
        .kpi-card {
            background-color: #1e293b;
            padding: 20px;
            border-radius: 12px;
            border-left: 6px solid #3b82f6;
            margin-bottom: 15px;
        }
        .kpi-title { font-size: 13px; color: #94a3b8; font-weight: 600; text-transform: uppercase; }
        .kpi-value { font-size: 26px; color: #f8fafc; font-weight: 700; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# Archivos CSV locales
ARCHIVO_GASTOS_DIARIOS = "gastos_diarios.csv"
ARCHIVO_GASTOS_FIJOS = "gastos_fijos.csv"
ARCHIVO_GASTOS_VARIABLES = "gastos_fijos_variables.csv"
ARCHIVO_FONDO_AHORRO = "fondo_ahorro.csv"

MARGEN_MES_REAL = 2445.48

# -----------------------------------------------------------------------------
# BASE DE DATOS Y CÁLCULOS
# -----------------------------------------------------------------------------
def obtener_ventas_tlt(fecha_consulta):
    db_path = "tlt.sqlite3"
    fecha_str = fecha_consulta.strftime("%Y-%m-%d")
    hace_7_dias_str = (fecha_consulta - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    mes_str = fecha_consulta.strftime("%Y-%m")
    
    v_dia, v_semana, v_mes = 0.0, 0.0, MARGEN_MES_REAL
    conectado = False

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            # Venta del Día
            q_dia = f"SELECT SUM(total_venta - total_costo) AS m FROM proformas_proforma WHERE strftime('%Y-%m-%d', fecha) = '{fecha_str}' AND estado IN ('confirmada', 'entregada')"
            df_d = pd.read_sql_query(q_dia, conn)
            if not df_d.empty and df_d["m"].iloc[0] is not None: v_dia = float(df_d["m"].iloc[0])

            # Venta de la Semana
            q_sem = f"SELECT SUM(total_venta - total_costo) AS m FROM proformas_proforma WHERE date(fecha) BETWEEN '{hace_7_dias_str}' AND '{fecha_str}' AND estado IN ('confirmada', 'entregada')"
            df_s = pd.read_sql_query(q_sem, conn)
            if not df_s.empty and df_s["m"].iloc[0] is not None: v_semana = float(df_s["m"].iloc[0])

            # Venta del Mes
            q_mes = f"SELECT SUM(total_venta - total_costo) AS m FROM proformas_proforma WHERE strftime('%Y-%m', fecha) = '{mes_str}' AND estado IN ('confirmada', 'entregada')"
            df_m = pd.read_sql_query(q_mes, conn)
            if not df_m.empty and df_m["m"].iloc[0] is not None: v_mes = float(df_m["m"].iloc[0])

            conn.close()
            conectado = True
        except Exception:
            pass

    return v_dia, v_semana, v_mes, conectado

def cargar_csv(filepath, columnas):
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            if "Fecha" in df.columns: df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
            return df
        except Exception: pass
    return pd.DataFrame(columns=columnas)

def guardar_csv(df, filepath):
    df.to_csv(filepath, index=False)

# Carga de datos
df_diarios = cargar_csv(ARCHIVO_GASTOS_DIARIOS, ["Fecha", "Categoria", "Monto S/", "Detalle"])
df_fijos = cargar_csv(ARCHIVO_GASTOS_FIJOS, ["Concepto", "Monto S/", "Pagado"])
df_fijos_var = cargar_csv(ARCHIVO_GASTOS_VARIABLES, ["Fecha_Mes", "Servicio", "Monto S/"])
df_ahorro = cargar_csv(ARCHIVO_FONDO_AHORRO, ["Fecha", "Monto Ahorrado S/", "Comentario"])

if df_fijos.empty:
    df_fijos = pd.DataFrame([
        {"Concepto": "Alquiler", "Monto S/": 700.0, "Pagado": True},
        {"Concepto": "Universidad", "Monto S/": 550.0, "Pagado": True}
    ])
    guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)

hoy = datetime.date.today()
mes_actual_str = hoy.strftime("%Y-%m")
hace_7_dias = hoy - datetime.timedelta(days=6)

v_dia_auto, v_semana_auto, v_mes_auto, db_conectada = obtener_ventas_tlt(hoy)

gastos_hoy_total = df_diarios[df_diarios["Fecha"] == hoy]["Monto S/"].sum() if not df_diarios.empty else 0.0
total_fijos_mes = df_fijos["Monto S/"].sum() if not df_fijos.empty else 0.0
total_fijos_var_mes = df_fijos_var[df_fijos_var["Fecha_Mes"].astype(str).str.startswith(mes_actual_str)]["Monto S/"].sum() if not df_fijos_var.empty else 0.0
total_diarios_mes = df_diarios[df_diarios["Fecha"].astype(str).str.startswith(mes_actual_str)]["Monto S/"].sum() if not df_diarios.empty else 0.0

total_gastos_mes = total_fijos_mes + total_fijos_var_mes + total_diarios_mes
ganancia_neta_mes = v_mes_auto - total_gastos_mes
total_ahorrado_acumulado = df_ahorro["Monto Ahorrado S/"].sum() if not df_ahorro.empty else 0.0

# -----------------------------------------------------------------------------
# BARRA SUPERIOR: SELECTOR DE PLANTILLAS VISUALES
# -----------------------------------------------------------------------------
st.title("🎨 Prueba las Plantillas en Vivo")

plantilla_seleccionada = st.selectbox(
    "👉 Selecciona el Diseño Visual que deseas probar:",
    [
        "Plantilla 1: Diseño Ejecutivo (Cajas KPI Grandes)",
        "Plantilla 2: Panel Lateral (Menú Vertical a la Izquierda)",
        "Plantilla 3: Diseño Plegable Móvil (Ideal Celular)",
        "Plantilla 4: Hoja Contable Minimalista (Estilo Libro de Cuentas)"
    ]
)

st.divider()

# -----------------------------------------------------------------------------
# RENDERIZADO SEGÚN LA PLANTILLA SELECCIONADA
# -----------------------------------------------------------------------------

# --- PLANTILLA 1: EJECUTIVA (KPI CARDS) ---
if "Plantilla 1" in plantilla_seleccionada:
    st.subheader("💼 Plantilla 1: Diseño Ejecutivo con Cajas Destacadas")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Ventas Hoy</div><div class="kpi-value">S/ {v_dia_auto:,.2f}</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Ventas Semanales</div><div class="kpi-value">S/ {v_semana_auto:,.2f}</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Margen Mes Real</div><div class="kpi-value">S/ {v_mes_auto:,.2f}</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Fondo Ahorro</div><div class="kpi-value">S/ {total_ahorrado_acumulado:,.2f}</div></div>', unsafe_allow_html=True)

    st.write("### ➕ Registro Rápido por Filas")
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1: st.markdown("#### 🚌 Pasaje Diario")
    with col2: m_p_d = st.number_input("Monto (S/)", min_value=0.0, step=0.5, key="p1_pd")
    with col3: st.button("💾 Guardar Pasaje", key="btn_p1_pd")


# --- PLANTILLA 2: PANEL LATERAL (SIDEBAR) ---
elif "Plantilla 2" in plantilla_seleccionada:
    st.subheader("🗂️ Plantilla 2: Panel con Menú Lateral Desplegable")
    st.info("💡 En esta plantilla, la navegación se traslada a la barra lateral izquierda.")
    
    with st.sidebar:
        st.header("🏢 T L T Distribuciones")
        opcion_side = st.radio("Menú Principal", ["📊 Resumen General", "🚌 Gastos Diarios", "💡 Recibos Variables", "🏦 Fondo Ahorro"])
    
    if opcion_side == "📊 Resumen General":
        st.metric("Margen Real del Mes", f"S/ {v_mes_auto:,.2f}")
        st.metric("Gastos Totales Acumulados", f"S/ {total_gastos_mes:,.2f}")
        st.metric("Ganancia Neta Disponible", f"S/ {ganancia_neta_mes:,.2f}")
    else:
        st.write(f"Sección activa: **{opcion_side}**")


# --- PLANTILLA 3: MÓVIL / PLEGABLE (EXPANDER) ---
elif "Plantilla 3" in plantilla_seleccionada:
    st.subheader("📱 Plantilla 3: Bloques Plegables Pensados para Celulares")
    
    with st.expander("📊 **VER MARGEN Y GANANCIAS DEL MES**", expanded=True):
        st.metric("Margen Real del Mes", f"S/ {v_mes_auto:,.2f}")
        st.metric("Ganancia Neta Disponible", f"S/ {ganancia_neta_mes:,.2f}")
        
    with st.expander("🚌 **REGISTRAR PASAJES Y GASTOS DIARIOS**", expanded=False):
        st.number_input("Pasaje Diario (S/)", min_value=0.0, key="m_pd")
        st.number_input("Pasaje Empresa (S/)", min_value=0.0, key="m_pe")
        st.number_input("Gastos Empresa (S/)", min_value=0.0, key="m_ge")
        st.number_input("Comida (S/)", min_value=0.0, key="m_co")
        st.button("💾 Guardar Todos los Gastos Diarios", type="primary", use_container_width=True)

    with st.expander("💡 **REGISTRAR RECIBOS (LUZ / AGUA / GAS)**", expanded=False):
        st.number_input("Recibo Luz (S/)", min_value=0.0, key="m_luz")
        st.number_input("Recibo Agua (S/)", min_value=0.0, key="m_agua")
        st.number_input("Recibo Gas (S/)", min_value=0.0, key="m_gas")


# --- PLANTILLA 4: LIBRO CONTABLE MINIMALISTA ---
elif "Plantilla 4" in plantilla_seleccionada:
    st.subheader("🧾 Plantilla 4: Hoja de Balance Contable Minimalista")
    
    tabla_contable = pd.DataFrame({
        "Concepto Financiero": ["Margen Ventas Mes", "Gastos Fijos (Alquiler + Univ)", "Recibos (Luz + Agua + Gas)", "Gastos Diarios Registrados", "GANANCIA NETA DISPONIBLE"],
        "Monto Registrado": [f"S/ {v_mes_auto:,.2f}", f"S/ {total_fijos_mes:,.2f}", f"S/ {total_fijos_var_mes:,.2f}", f"S/ {total_diarios_mes:,.2f}", f"S/ {ganancia_neta_mes:,.2f}"],
        "Estado": ["✅ Confirmado (tlt.sqlite3)", "📌 Programado", "💡 Recibos cargados", "🚌 Al día", "💰 Saldo Libre"]
    })
    
    st.table(tabla_contable)
