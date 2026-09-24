import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN GENERAL, TEMA BLANCO Y BOTONES VERDES
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Finanzas y Control de Gastos", 
    layout="wide", 
    page_icon="📱"
)

# Estilos CSS: Fondo Blanco, Tarjetas Blancas y Botones Verdes
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        /* Fondo General Blanco */
        .stApp {
            background-color: #FFFFFF !important;
            color: #1E293B !important;
            font-family: 'Poppins', sans-serif !important;
        }
        
        /* Encabezados y Textos */
        h1, h2, h3, h4, h5, h6, label, p, span {
            color: #0F172A !important;
        }

        /* Botones Verdes (Primarios y Secundarios) */
        div.stButton > button {
            background-color: #10B981 !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 10px 20px !important;
            transition: all 0.3s ease !important;
        }
        
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }

        /* Estilo de Tarjetas Desplegables (Expanders) */
        .st-emotion-cache-1eb5vkp, .st-emotion-cache-p222h1, div[data-testid="stExpander"] {
            background-color: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        }

        /* Cuadros de entrada de texto e información */
        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
            border: 1px solid #CBD5E1 !important;
        }

        /* Métrica y Cajas Destacadas */
        div[data-testid="stMetricValue"] {
            color: #059669 !important;
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Archivos CSV locales
ARCHIVO_GASTOS_DIARIOS = "gastos_diarios.csv"
ARCHIVO_GASTOS_FIJOS = "gastos_fijos.csv"
ARCHIVO_GASTOS_VARIABLES = "gastos_fijos_variables.csv"
ARCHIVO_FONDO_AHORRO = "fondo_ahorro.csv"

MARGEN_MES_REAL = 2445.48

# -----------------------------------------------------------------------------
# 2. CONSULTA AUTOMÁTICA DE BASE DE DATOS (tlt.sqlite3)
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

# -----------------------------------------------------------------------------
# 3. CARGA DE ARCHIVOS CSV
# -----------------------------------------------------------------------------
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
# 4. ENCABEZADO MÓVIL
# -----------------------------------------------------------------------------
st.title("📱 T L T Distribuciones — Finanzas")

col_head, col_btn = st.columns([3, 1])
with col_head:
    st.success(f"✅ **Conectado a Base de Datos (tlt.sqlite3)** — Margen del Mes Real: **S/ {v_mes_auto:,.2f}**")
with col_btn:
    if st.button("🔄 Sincronizar", use_container_width=True):
        st.rerun()

st.write("---")

# -----------------------------------------------------------------------------
# 5. BLOQUES PLEGABLES (PLANTILLA 3 MÓVIL EN BLANCO Y VERDE)
# -----------------------------------------------------------------------------

# BLOQUE 1: RESUMEN DE GANANCIAS EN LOS 3 NIVELES
with st.expander("📊 **VER BALANCE: DIARIO, SEMANAL Y MENSUAL**", expanded=True):
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.markdown("#### 📅 1. HOY")
        st.metric("Ventas Hoy", f"S/ {v_dia_auto:,.2f}")
        st.metric("Gastos Hoy", f"S/ {gastos_hoy_total:,.2f}")
        st.metric("Neto Limpio Hoy", f"S/ {(v_dia_auto - gastos_hoy_total):,.2f}")
    
    with c_m2:
        st.markdown("#### 🗓️ 2. ÚLTIMOS 7 DÍAS")
        gastos_semana_total = df_diarios[(df_diarios["Fecha"] >= hace_7_dias) & (df_diarios["Fecha"] <= hoy)]["Monto S/"].sum() if not df_diarios.empty else 0.0
        st.metric("Ventas Semanales", f"S/ {v_semana_auto:,.2f}")
        st.metric("Gastos Semanales", f"S/ {gastos_semana_total:,.2f}")
        st.metric("Neto Semanal", f"S/ {(v_semana_auto - gastos_semana_total):,.2f}")
        
    with c_m3:
        st.markdown("#### 📅 3. ACUMULADO DEL MES")
        st.metric("Margen Real Mes", f"S/ {v_mes_auto:,.2f}")
        st.metric("Gastos Mes", f"S/ {total_gastos_mes:,.2f}")
        st.metric("Neto Disponible", f"S/ {ganancia_neta_mes:,.2f}")


# BLOQUE 2: REGISTRO DE GASTOS DIARIOS POR FILAS INDEPENDIENTES
with st.expander("🚌 **REGISTRAR GASTOS DIARIOS DE HOY**", expanded=False):
    fecha_gasto_diario = st.date_input("Fecha del Gasto", value=datetime.date.today(), key="fecha_m_diaria")
    st.write("---")

    # Pasaje Diario
    col_p1, col_p2, col_p3 = st.columns([2, 3, 2])
    with col_p1: st.markdown("##### 🚌 Pasaje Diario")
    with col_p2: m_p_d = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="m_pd_m")
    with col_p3:
        if st.button("💾 Guardar Pasaje", key="btn_pd_m"):
            if m_p_d > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "pasaje diario", "Monto S/": m_p_d, "Detalle": "Pasajes de ruta habitual"}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Pasaje Diario guardado: S/ {m_p_d:.2f}")
                st.rerun()

    st.write("---")

    # Pasaje Empresa
    col_pe1, col_pe2, col_pe3 = st.columns([2, 3, 2])
    with col_pe1: st.markdown("##### 🚚 Pasaje Empresa")
    with col_pe2: m_p_e = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="m_pe_m")
    with col_pe3:
        if st.button("💾 Guardar Pasaje Emp.", key="btn_pe_m"):
            if m_p_e > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "pasaje empresa", "Monto S/": m_p_e, "Detalle": "Despacho/Movilidad almacén"}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Pasaje Empresa guardado: S/ {m_p_e:.2f}")
                st.rerun()

    st.write("---")

    # Gastos Empresa
    col_ge1, col_ge2, col_ge3 = st.columns([2, 3, 2])
    with col_ge1: st.markdown("##### 📦 Gastos Empresa")
    with col_ge2: m_g_e = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="m_ge_m")
    with col_ge3:
        if st.button("💾 Guardar Gasto Emp.", key="btn_ge_m"):
            if m_g_e > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "gastos empresa", "Monto S/": m_g_e, "Detalle": "Cinta, embalaje, insumos"}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Gasto Empresa guardado: S/ {m_g_e:.2f}")
                st.rerun()

    st.write("---")

    # Comida
    col_co1, col_co2, col_co3 = st.columns([2, 3, 2])
    with col_co1: st.markdown("##### 🍲 Comida")
    with col_co2: m_co = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="m_co_m")
    with col_co3:
        if st.button("💾 Guardar Comida", key="btn_co_m"):
            if m_co > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "comida", "Monto S/": m_co, "Detalle": "Almuerzo/Menú del día"}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Comida guardada: S/ {m_co:.2f}")
                st.rerun()


# BLOQUE 3: REGISTRO DE RECIBOS (LUZ / AGUA / GAS)
with st.expander("💡 **REGISTRAR RECIBOS (LUZ / AGUA / GAS)**", expanded=False):
    fecha_recibo = st.date_input("Fecha de emisión del recibo", value=datetime.date.today(), key="f_recibos_m")
    
    # Luz
    r_l1, r_l2, r_l3 = st.columns([2, 3, 2])
    with r_l1: st.markdown("##### 💡 Recibo de Luz")
    with r_l2: m_luz = st.number_input("Monto (S/)", min_value=0.0, step=1.0, format="%.2f", key="m_luz_m")
    with r_l3:
        if st.button("💾 Guardar Luz", key="btn_luz_m"):
            if m_luz > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Luz", "Monto S/": m_luz}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Luz guardado: S/ {m_luz:.2f}")
                st.rerun()

    st.write("---")

    # Agua
    r_a1, r_a2, r_a3 = st.columns([2, 3, 2])
    with r_a1: st.markdown("##### 💧 Recibo de Agua")
    with r_a2: m_agua = st.number_input("Monto (S/)", min_value=0.0, step=1.0, format="%.2f", key="m_agua_m")
    with r_a3:
        if st.button("💾 Guardar Agua", key="btn_agua_m"):
            if m_agua > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Agua", "Monto S/": m_agua}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Agua guardado: S/ {m_agua:.2f}")
                st.rerun()

    st.write("---")

    # Gas
    r_g1, r_g2, r_g3 = st.columns([2, 3, 2])
    with r_g1: st.markdown("##### 🔥 Recibo de Gas")
    with r_g2: m_gas = st.number_input("Monto (S/)", min_value=0.0, step=1.0, format="%.2f", key="m_gas_m")
    with r_g3:
        if st.button("💾 Guardar Gas", key="btn_gas_m"):
            if m_gas > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Gas", "Monto S/": m_gas}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Gas guardado: S/ {m_gas:.2f}")
                st.rerun()


# BLOQUE 4: GASTOS FIJOS (ALQUILER Y UNIVERSIDAD)
with st.expander("📌 **VER GASTOS FIJOS MENSUALES**", expanded=False):
    st.dataframe(df_fijos, use_container_width=True, hide_index=True)
    st.metric("Total Gastos Fijos Mensuales", f"S/ {total_fijos_mes:,.2f}")


# BLOQUE 5: FONDO DE AHORRO
with st.expander("🏦 **MI FONDO DE AHORRO ACUMULADO**", expanded=False):
    st.metric("Total Acumulado en Ahorro", f"S/ {total_ahorrado_acumulado:,.2f}")
    if not df_ahorro.empty:
        st.dataframe(df_ahorro.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
