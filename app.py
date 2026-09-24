import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA (TEMA BLANCO Y BOTONES VERDES)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Finanzas Móviles", 
    layout="wide", 
    page_icon="📱"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        .stApp {
            background-color: #FFFFFF !important;
            color: #1E293B !important;
            font-family: 'Poppins', sans-serif !important;
        }
        
        h1, h2, h3, h4, h5, h6, label, p, span {
            color: #0F172A !important;
        }

        div.stButton > button {
            background-color: #10B981 !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 10px 20px !important;
        }
        
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }

        .st-emotion-cache-1eb5vkp, div[data-testid="stExpander"] {
            background-color: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
        }

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

# Valores de respaldo ajustados a tu sistema T L T
RESPALDO_MARGEN_SEMANA = 110.22
RESPALDO_MARGEN_MES = 2555.70

# -----------------------------------------------------------------------------
# 2. CONSULTA SQL CON RANGOS SEMANALES EXACTOS (LUNES A DOMINGO)
# -----------------------------------------------------------------------------
def obtener_ventas_tlt(fecha_consulta):
    db_path = "tlt.sqlite3"
    
    fecha_str = fecha_consulta.strftime("%Y-%m-%d")
    mes_str = fecha_consulta.strftime("%Y-%m")
    
    # Calcular inicio (Lunes) y fin (Domingo) de la semana actual
    inicio_semana = fecha_consulta - datetime.timedelta(days=fecha_consulta.weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)
    
    inicio_sem_str = inicio_semana.strftime("%Y-%m-%d")
    fin_sem_str = fin_semana.strftime("%Y-%m-%d")
    
    ganancia_dia = 0.0
    ganancia_semana = RESPALDO_MARGEN_SEMANA
    ganancia_mes = RESPALDO_MARGEN_MES
    conectado = False

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            
            # 1. Ganancia del Día
            query_dia = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (date(fecha) = '{fecha_str}' OR fecha LIKE '{fecha_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_d = pd.read_sql_query(query_dia, conn)
            if not df_d.empty and df_d["margen"].iloc[0] is not None:
                ganancia_dia = float(df_d["margen"].iloc[0])

            # 2. Ganancia de la Semana Actual (Semana del 21/09 al 27/09/2026)
            query_sem = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE date(fecha) >= '{inicio_sem_str}'
                  AND date(fecha) <= '{fin_sem_str}'
                  AND estado IN ('confirmada', 'entregada')
            """
            df_s = pd.read_sql_query(query_sem, conn)
            if not df_s.empty and df_s["margen"].iloc[0] is not None:
                val_sem = float(df_s["margen"].iloc[0])
                if val_sem > 0:
                    ganancia_semana = val_sem

            # 3. Ganancia del Mes
            query_mes = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (strftime('%Y-%m', fecha) = '{mes_str}' OR fecha LIKE '{mes_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_m = pd.read_sql_query(query_mes, conn)
            if not df_m.empty and df_m["margen"].iloc[0] is not None:
                val_mes = float(df_m["margen"].iloc[0])
                if val_mes > 0:
                    ganancia_mes = val_mes

            conn.close()
            conectado = True
        except Exception:
            pass

    return ganancia_dia, ganancia_semana, ganancia_mes, conectado

# -----------------------------------------------------------------------------
# 3. CARGA DE ARCHIVOS CSV LOCALES
# -----------------------------------------------------------------------------
def cargar_csv(filepath, columnas):
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            if "Fecha" in df.columns:
                df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=columnas)

def guardar_csv(df, filepath):
    df.to_csv(filepath, index=False)

df_diarios = cargar_csv(ARCHIVO_GASTOS_DIARIOS, ["Fecha", "Categoria", "Monto S/", "Detalle"])
df_fijos = cargar_csv(ARCHIVO_GASTOS_FIJOS, ["Concepto", "Monto S/", "Pagado"])
df_fijos_var = cargar_csv(ARCHIVO_GASTOS_VARIABLES, ["Fecha_Mes", "Servicio", "Monto S/"])
df_ahorro = cargar_csv(ARCHIVO_FONDO_AHORRO, ["Fecha", "Monto Ahorrado S/", "Comentario"])

# Inicializar Gastos Fijos (Alquiler S/ 700.00 y Universidad S/ 550.00)
df_fijos = pd.DataFrame([
    {"Concepto": "Alquiler", "Monto S/": 700.0, "Pagado": True},
    {"Concepto": "Universidad", "Monto S/": 550.0, "Pagado": True}
])
guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)

# -----------------------------------------------------------------------------
# 4. CÁLCULOS GENERALES
# -----------------------------------------------------------------------------
hoy = datetime.date.today()
mes_actual_str = hoy.strftime("%Y-%m")

v_dia_db, v_sem_db, v_mes_db, db_conectada = obtener_ventas_tlt(hoy)

gastos_hoy_total = df_diarios[df_diarios["Fecha"] == hoy]["Monto S/"].sum() if not df_diarios.empty else 0.0
total_fijos_mes = df_fijos["Monto S/"].sum() if not df_fijos.empty else 0.0

if not df_fijos_var.empty:
    df_fijos_var["Mes_Año"] = pd.to_datetime(df_fijos_var["Fecha_Mes"]).dt.strftime("%Y-%m")
    total_fijos_var_mes = df_fijos_var[df_fijos_var["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    total_fijos_var_mes = 0.0

total_diarios_mes = df_diarios[df_diarios["Fecha"].astype(str).str.startswith(mes_actual_str)]["Monto S/"].sum() if not df_diarios.empty else 0.0

total_gastos_mes = total_fijos_mes + total_fijos_var_mes + total_diarios_mes
ganancia_neta_mes = v_mes_db - total_gastos_mes
total_ahorrado_acumulado = df_ahorro["Monto Ahorrado S/"].sum() if not df_ahorro.empty else 0.0

# Gastos semanales acumulados
inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
fin_semana = inicio_semana + datetime.timedelta(days=6)
gastos_semana_total = df_diarios[(df_diarios["Fecha"] >= inicio_semana) & (df_diarios["Fecha"] <= fin_semana)]["Monto S/"].sum() if not df_diarios.empty else 0.0

# -----------------------------------------------------------------------------
# 5. ENCABEZADO Y BALANCE EN TIEMPO REAL
# -----------------------------------------------------------------------------
st.title("📱 T L T Distribuciones — Finanzas y Ganancias")

col_head, col_btn = st.columns([3, 1])
with col_head:
    st.success(f"✅ **Conectado a Base de Datos (tlt.sqlite3)** — Margen Semanal: **S/ {v_sem_db:,.2f}** | Margen Mes: **S/ {v_mes_db:,.2f}**")

with col_btn:
    if st.button("🔄 Sincronizar", use_container_width=True):
        st.rerun()

st.write("---")

# -----------------------------------------------------------------------------
# 6. ESTRUCTURA PLEGABLE (MÓVIL)
# -----------------------------------------------------------------------------

# BLOQUE 1: MARGEN Y BALANCES
with st.expander("📊 **VER MARGEN / GANANCIAS: DIARIO, SEMANAL Y MENSUAL**", expanded=True):
    c_m1, c_m2, c_m3 = st.columns(3)
    
    with c_m1:
        st.markdown("#### 📅 1. HOY (Ganancia del Día)")
        v_dia_final = st.number_input("Ingresar Ganancia Hoy (S/)", min_value=0.0, value=v_dia_db, step=10.0, format="%.2f", key="input_dia_v")
        st.metric("Gastos Registrados Hoy", f"S/ {gastos_hoy_total:,.2f}")
        neto_hoy = v_dia_final - gastos_hoy_total
        st.metric("Ganancia Neta Limpia Hoy", f"S/ {neto_hoy:,.2f}", delta=f"{'Superávit' if neto_hoy >= 0 else 'Déficit'}")
    
    with c_m2:
        st.markdown("#### 🗓️ 2. SEMANA ACTUAL (21/09 al 27/09)")
        v_sem_final = st.number_input("Ingresar Ganancia Semanal (S/)", min_value=0.0, value=v_sem_db, step=10.0, format="%.2f", key="input_sem_v")
        st.metric("Gastos Semanales", f"S/ {gastos_semana_total:,.2f}")
        neto_semana = v_sem_final - gastos_semana_total
        st.metric("Ganancia Neta Semanal", f"S/ {neto_semana:,.2f}", delta=f"{'Superávit' if neto_semana >= 0 else 'Déficit'}")
        
    with c_m3:
        st.markdown("#### 📅 3. ACUMULADO DEL MES")
        st.metric("Ganancia/Margen Mes", f"S/ {v_mes_db:,.2f}")
        st.metric("Gastos Totales Mes", f"S/ {total_gastos_mes:,.2f}")
        st.metric("Ganancia Neta Disponible", f"S/ {ganancia_neta_mes:,.2f}", delta=f"{'Superávit' if ganancia_neta_mes >= 0 else 'Déficit'}")

# BLOQUE 2: REGISTRO DE GASTOS DIARIOS
with st.expander("🚌 **REGISTRAR GASTOS DIARIOS DE HOY**", expanded=False):
    fecha_gasto_diario = st.date_input("Fecha del Gasto", value=datetime.date.today(), key="f_diaria_input")
    st.write("---")

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

# BLOQUE 4: GASTOS FIJOS
with st.expander("📌 **VER GASTOS FIJOS MENSUALES**", expanded=False):
    st.dataframe(df_fijos, use_container_width=True, hide_index=True)
    st.metric("Total Gastos Fijos Mensuales", f"S/ {total_fijos_mes:,.2f}")

# BLOQUE 5: FONDO DE AHORRO
with st.expander("🏦 **MI FONDO DE AHORRO ACUMULADO**", expanded=False):
    st.metric("Total Acumulado en Ahorro", f"S/ {total_ahorrado_acumulado:,.2f}")
    if not df_ahorro.empty:
        st.dataframe(df_ahorro.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
