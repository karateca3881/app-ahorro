import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN GENERAL Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Control Diario, Semanal y Mensual", 
    layout="wide", 
    page_icon="📈"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

# Archivos CSV locales para persistencia
ARCHIVO_GASTOS_DIARIOS = "gastos_diarios.csv"
ARCHIVO_GASTOS_FIJOS = "gastos_fijos.csv"
ARCHIVO_GASTOS_VARIABLES = "gastos_fijos_variables.csv"
ARCHIVO_FONDO_AHORRO = "fondo_ahorro.csv"

RESPALDO_MARGEN_MES = 2445.48

# -----------------------------------------------------------------------------
# 2. CONSULTAS AUTOMÁTICAS A LA BASE DE DATOS (HOY, SEMANA Y MES)
# -----------------------------------------------------------------------------
def obtener_ventas_automaticas(fecha_consulta):
    """
    Consulta directamente la base de datos tlt.sqlite3 para obtener:
    - Ganancia exacta del día actual.
    - Ganancia acumulada de los últimos 7 días (Semana).
    - Ganancia acumulada del mes.
    """
    db_path = "tlt.sqlite3"
    fecha_str = fecha_consulta.strftime("%Y-%m-%d")
    hace_7_dias_str = (fecha_consulta - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    mes_str = fecha_consulta.strftime("%Y-%m")
    
    v_dia = 0.0
    v_semana = 0.0
    v_mes = RESPALDO_MARGEN_MES
    conectado = False

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            
            # 1. Ganancia de Hoy
            q_dia = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (strftime('%Y-%m-%d', fecha) = '{fecha_str}' OR fecha LIKE '{fecha_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_dia = pd.read_sql_query(q_dia, conn)
            if not df_dia.empty and df_dia["margen"].iloc[0] is not None:
                v_dia = float(df_dia["margen"].iloc[0])

            # 2. Ganancia de la Semana (Últimos 7 días)
            q_sem = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE date(fecha) BETWEEN '{hace_7_dias_str}' AND '{fecha_str}'
                  AND estado IN ('confirmada', 'entregada')
            """
            df_sem = pd.read_sql_query(q_sem, conn)
            if not df_sem.empty and df_sem["margen"].iloc[0] is not None:
                v_semana = float(df_sem["margen"].iloc[0])

            # 3. Ganancia del Mes
            q_mes = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (strftime('%Y-%m', fecha) = '{mes_str}' OR fecha LIKE '{mes_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_mes = pd.read_sql_query(q_mes, conn)
            if not df_mes.empty and df_mes["margen"].iloc[0] is not None:
                v_mes = float(df_mes["margen"].iloc[0])

            conn.close()
            conectado = True
        except Exception:
            pass

    return v_dia, v_semana, v_mes, conectado

# -----------------------------------------------------------------------------
# 3. MANEJO DE ARCHIVOS CSV
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
if df_fijos.empty:
    df_fijos = pd.DataFrame([
        {"Concepto": "Alquiler", "Monto S/": 700.0, "Pagado": True},
        {"Concepto": "Universidad", "Monto S/": 550.0, "Pagado": True}
    ])
    guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)

# -----------------------------------------------------------------------------
# 4. CÁLCULOS AUTOMÁTICOS
# -----------------------------------------------------------------------------
hoy = datetime.date.today()
mes_actual_str = hoy.strftime("%Y-%m")
hace_7_dias = hoy - datetime.timedelta(days=6)

ventas_dia_auto, ventas_semana_auto, ventas_mes_auto, db_conectada = obtener_ventas_automaticas(hoy)

if not df_diarios.empty:
    df_diarios["Fecha"] = pd.to_datetime(df_diarios["Fecha"]).dt.date
    df_diarios["Mes_Año"] = pd.to_datetime(df_diarios["Fecha"]).dt.strftime("%Y-%m")
    
    gastos_hoy_total = df_diarios[df_diarios["Fecha"] == hoy]["Monto S/"].sum()
    gastos_semana_total = df_diarios[(df_diarios["Fecha"] >= hace_7_dias) & (df_diarios["Fecha"] <= hoy)]["Monto S/"].sum()
    gastos_diarios_mes_total = df_diarios[df_diarios["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    gastos_hoy_total = 0.0
    gastos_semana_total = 0.0
    gastos_diarios_mes_total = 0.0

total_fijos_mes = df_fijos["Monto S/"].sum() if not df_fijos.empty else 0.0

if not df_fijos_var.empty:
    df_fijos_var["Mes_Año"] = pd.to_datetime(df_fijos_var["Fecha_Mes"]).dt.strftime("%Y-%m")
    total_fijos_var_mes = df_fijos_var[df_fijos_var["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    total_fijos_var_mes = 0.0

total_gastos_mes = total_fijos_mes + total_fijos_var_mes + gastos_diarios_mes_total
ganancia_neta_mes = ventas_mes_auto - total_gastos_mes
total_ahorrado_acumulado = df_ahorro["Monto Ahorrado S/"].sum() if not df_ahorro.empty else 0.0

# -----------------------------------------------------------------------------
# 5. ENCABEZADO Y BALANCE EN LOS 3 TIEMPOS (TOTALMENTE AUTOMÁTICO)
# -----------------------------------------------------------------------------
st.title("📈 T L T Distribuciones — Finanzas y Control de Gastos")

col_status, col_btn = st.columns([4, 1])
with col_status:
    if db_conectada:
        st.success(f"✅ **Conectado a Base de Datos (tlt.sqlite3)** — Margen del Mes Real: **S/ {ventas_mes_auto:,.2f}**")
    else:
        st.warning(f"⚠️ **Base de datos no detectada. Usando respaldo de mes**: **S/ {RESPALDO_MARGEN_MES:,.2f}**")
with col_btn:
    if st.button("🔄 Sincronizar", use_container_width=True):
        st.rerun()

st.divider()

# TABLERO AUTOMÁTICO DE LOS 3 TIEMPOS
st.subheader("📊 Comparativo de Ganancias Automáticas vs Gastos")

c_dia, c_sem, c_mes = st.columns(3)

with c_dia:
    st.markdown("### 📅 1. HOY (Diario)")
    neto_hoy = ventas_dia_auto - gastos_hoy_total
    st.metric("Ganancia Automática Hoy", f"S/ {ventas_dia_auto:,.2f}")
    st.metric("Gastos Registrados Hoy", f"S/ {gastos_hoy_total:,.2f}")
    st.metric("Saldo Neto Limpio Hoy", f"S/ {neto_hoy:,.2f}", delta=f"{'Superávit' if neto_hoy >= 0 else 'Déficit'}")

with c_sem:
    st.markdown("### 🗓️ 2. ÚLTIMOS 7 DÍAS (Semanal)")
    neto_semana = ventas_semana_auto - gastos_semana_total
    st.metric("Ventas de la Semana", f"S/ {ventas_semana_auto:,.2f}")
    st.metric("Gastos de la Semana", f"S/ {gastos_semana_total:,.2f}")
    st.metric("Saldo Neto Semanal", f"S/ {neto_semana:,.2f}", delta=f"{'Superávit' if neto_semana >= 0 else 'Déficit'}")

with c_mes:
    st.markdown("### 📅 3. ACUMULADO DEL MES")
    st.metric("Ganancia Real del Mes", f"S/ {ventas_mes_auto:,.2f}")
    st.metric("Total Gastos del Mes", f"S/ {total_gastos_mes:,.2f}")
    st.metric("Saldo Neto del Mes", f"S/ {ganancia_neta_mes:,.2f}", delta=f"{'Superávit' if ganancia_neta_mes >= 0 else 'Déficit'}")

st.divider()

# -----------------------------------------------------------------------------
# 6. PESTAÑAS DE TRABAJO
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Registrar Gastos Diarios",
    "2️⃣ Gastos Fijos (Alquiler/Univ.)",
    "3️⃣ Fijos Variables (Luz/Agua/Gas)",
    "4️⃣ 📈 Gráfica del Mes",
    "5️⃣ 📜 Historial de Gastos",
    "6️⃣ 🏦 Fondo de Ahorro"
])

# 1. REGISTRAR GASTOS DIARIOS EN FILAS INDEPENDIENTES
with tab1:
    st.subheader("➕ Registro Rápido de Gastos Diarios")
    
    fecha_gasto_diario = st.date_input("Fecha del Gasto Diario", value=datetime.date.today(), key="fecha_diaria_global")
    st.write("---")

    # Fila 1: PASAJE DIARIO
    c1_1, c1_2, c1_3, c1_4 = st.columns([2, 2, 3, 2])
    with c1_1:
        st.markdown("### 🚌 Pasaje Diario")
    with c1_2:
        m_pasaje_d = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="input_pasaje_d")
    with c1_3:
        d_pasaje_d = st.text_input("Detalle", value="Pasajes de ruta habitual", key="det_pasaje_d")
    with c1_4:
        if st.button("💾 Guardar Pasaje Diario", type="primary", key="btn_pasaje_d"):
            if m_pasaje_d > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "pasaje diario", "Monto S/": m_pasaje_d, "Detalle": d_pasaje_d.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Pasaje Diario guardado: S/ {m_pasaje_d:.2f}")
                st.rerun()

    st.write("---")

    # Fila 2: PASAJE EMPRESA
    c2_1, c2_2, c2_3, c2_4 = st.columns([2, 2, 3, 2])
    with c2_1:
        st.markdown("### 🚚 Pasaje Empresa")
    with c2_2:
        m_pasaje_e = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="input_pasaje_e")
    with c2_3:
        d_pasaje_e = st.text_input("Detalle", value="Movilidad/Despacho de almacén", key="det_pasaje_e")
    with c2_4:
        if st.button("💾 Guardar Pasaje Empresa", type="primary", key="btn_pasaje_e"):
            if m_pasaje_e > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "pasaje empresa", "Monto S/": m_pasaje_e, "Detalle": d_pasaje_e.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Pasaje Empresa guardado: S/ {m_pasaje_e:.2f}")
                st.rerun()

    st.write("---")

    # Fila 3: GASTOS EMPRESA
    c3_1, c3_2, c3_3, c3_4 = st.columns([2, 2, 3, 2])
    with c3_1:
        st.markdown("### 📦 Gastos Empresa")
    with c3_2:
        m_gasto_e = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="input_gasto_e")
    with c3_3:
        d_gasto_e = st.text_input("Detalle", value="Embalaje, cinta, insumos", key="det_gasto_e")
    with c3_4:
        if st.button("💾 Guardar Gasto Empresa", type="primary", key="btn_gasto_e"):
            if m_gasto_e > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "gastos empresa", "Monto S/": m_gasto_e, "Detalle": d_gasto_e.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Gasto Empresa guardado: S/ {m_gasto_e:.2f}")
                st.rerun()

    st.write("---")

    # Fila 4: COMIDA
    c4_1, c4_2, c4_3, c4_4 = st.columns([2, 2, 3, 2])
    with c4_1:
        st.markdown("### 🍲 Comida")
    with c4_2:
        m_comida = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f", key="input_comida")
    with c4_3:
        d_comida = st.text_input("Detalle", value="Almuerzo/Menú del día", key="det_comida")
    with c4_4:
        if st.button("💾 Guardar Comida", type="primary", key="btn_comida"):
            if m_comida > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto_diario, "Categoria": "comida", "Monto S/": m_comida, "Detalle": d_comida.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Comida guardada: S/ {m_comida:.2f}")
                st.rerun()

    st.write("---")
    st.subheader("📋 Historial de Gastos Diarios Registrados Hoy")
    if not df_diarios.empty:
        gastos_hoy_tabla = df_diarios[df_diarios["Fecha"] == hoy]
        if not gastos_hoy_tabla.empty:
            st.dataframe(gastos_hoy_tabla, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no has registrado gastos diarios hoy.")

# 2. GASTOS FIJOS
with tab2:
    st.subheader("📌 Gastos Fijos Mensuales")
    st.dataframe(df_fijos, use_container_width=True, hide_index=True)
    st.metric("Total Gastos Fijos Mensuales", f"S/ {total_fijos_mes:,.2f}")

# 3. FIJOS VARIABLES (LUZ, AGUA, GAS)
with tab3:
    st.subheader("💡 Recibos Variables (Ingreso Directo por Servicio)")
    fecha_recibo = st.date_input("Fecha de emisión del recibo", value=datetime.date.today(), key="fecha_recibos_indep")
    st.write("---")

    # Fila Luz
    col_l1, col_l2, col_l3 = st.columns([2, 3, 2])
    with col_l1:
        st.markdown("### 💡 Recibo de Luz")
    with col_l2:
        monto_luz = st.number_input("Monto Luz (S/)", min_value=0.0, step=1.0, format="%.2f", key="monto_luz_input")
    with col_l3:
        if st.button("💾 Guardar Luz", type="primary", key="btn_luz"):
            if monto_luz > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Luz", "Monto S/": monto_luz}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Luz registrado: S/ {monto_luz:.2f}")
                st.rerun()

    st.write("---")

    # Fila Agua
    col_a1, col_a2, col_a3 = st.columns([2, 3, 2])
    with col_a1:
        st.markdown("### 💧 Recibo de Agua")
    with col_a2:
        monto_agua = st.number_input("Monto Agua (S/)", min_value=0.0, step=1.0, format="%.2f", key="monto_agua_input")
    with col_a3:
        if st.button("💾 Guardar Agua", type="primary", key="btn_agua"):
            if monto_agua > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Agua", "Monto S/": monto_agua}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Agua registrado: S/ {monto_agua:.2f}")
                st.rerun()

    st.write("---")

    # Fila Gas
    col_g1, col_g2, col_g3 = st.columns([2, 3, 2])
    with col_g1:
        st.markdown("### 🔥 Recibo de Gas")
    with col_g2:
        monto_gas = st.number_input("Monto Gas (S/)", min_value=0.0, step=1.0, format="%.2f", key="monto_gas_input")
    with col_g3:
        if st.button("💾 Guardar Gas", type="primary", key="btn_gas"):
            if monto_gas > 0:
                nuevo = pd.DataFrame([{"Fecha_Mes": fecha_recibo, "Servicio": "Gas", "Monto S/": monto_gas}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo de Gas registrado: S/ {monto_gas:.2f}")
                st.rerun()

    st.write("---")
    st.subheader("📋 Historial de Recibos Guardados")
    if not df_fijos_var.empty:
        st.dataframe(df_fijos_var.sort_values(by="Fecha_Mes", ascending=False), use_container_width=True, hide_index=True)

# 4. GRÁFICA DEL MES
with tab4:
    st.subheader("📊 Gráfica de Evolución Mensual: Gastos vs Ganancias")
    dias_del_mes = pd.date_range(start=f"{mes_actual_str}-01", periods=30, freq='D')
    df_grafico_mes = pd.DataFrame({"Fecha": dias_del_mes.date})
    
    if not df_diarios.empty:
        df_gastos_diarios_agrup = df_diarios.groupby("Fecha")["Monto S/"].sum().reset_index()
        df_grafico_mes = pd.merge(df_grafico_mes, df_gastos_diarios_agrup, on="Fecha", how="left").fillna(0)
    else:
        df_grafico_mes["Monto S/"] = 0.0
        
    df_grafico_mes["Gastos Diarios Acumulados S/"] = df_grafico_mes["Monto S/"].cumsum() + total_fijos_mes + total_fijos_var_mes
    df_grafico_mes["Ganancia Ventas (Línea Base) S/"] = ventas_mes_auto
    st.line_chart(df_grafico_mes.set_index("Fecha")[["Gastos Diarios Acumulados S/", "Ganancia Ventas (Línea Base) S/"]])

# 5. HISTORIAL
with tab5:
    st.subheader("📜 Histórico de Gastos por Mes")
    mes_seleccionado = st.text_input("Filtrar por Mes/Año (Ej: 2026-06, 2026-07, 2026-08, 2026-09)", value=mes_actual_str)
        
    if not df_diarios.empty:
        df_filtrado_mes = df_diarios[df_diarios["Mes_Año"] == mes_seleccionado]
        if not df_filtrado_mes.empty:
            st.dataframe(df_filtrado_mes, use_container_width=True, hide_index=True)
            st.info(f"Total gastos diarios en {mes_seleccionado}: S/ {df_filtrado_mes['Monto S/'].sum():,.2f}")
        else:
            st.warning(f"No hay registros de gastos diarios para el periodo {mes_seleccionado}.")

# 6. FONDO DE AHORRO
with tab6:
    st.subheader("🏦 Fondo de Ahorro Acumulado")
    c_ahorro1, c_ahorro2 = st.columns([2, 3])
    
    with c_ahorro1:
        st.markdown("### 📥 Guardar en Ahorro")
        with st.form("form_ahorro", clear_on_submit=True):
            pct_sugerido = st.slider("Porcentaje a ahorrar del saldo libre", min_value=5, max_value=50, value=10, step=5)
            monto_sugerido = max(0.0, float(ganancia_neta_mes * (pct_sugerido / 100.0)))
            
            monto_ahorro = st.number_input("Monto a Guardar (S/)", min_value=0.0, value=monto_sugerido, step=10.0, format="%.2f")
            comentario_ahorro = st.text_input("Comentario (Ej: Fondo de emergencia, reservas)")
            fecha_ahorro = st.date_input("Fecha de Ahorro", value=datetime.date.today())
            
            if st.form_submit_button("💰 Guardar en Fondo de Ahorro", type="primary", use_container_width=True):
                if monto_ahorro > 0:
                    nuevo_ahorro = pd.DataFrame([{"Fecha": fecha_ahorro, "Monto Ahorrado S/": monto_ahorro, "Comentario": comentario_ahorro.strip()}])
                    df_ahorro = pd.concat([df_ahorro, nuevo_ahorro], ignore_index=True)
                    guardar_csv(df_ahorro, ARCHIVO_FONDO_AHORRO)
                    st.success(f"S/ {monto_ahorro:.2f} añadidos al Fondo de Ahorro.")
                    st.rerun()

    with c_ahorro2:
        st.markdown("### 📊 Estado de tu Fondo de Ahorro")
        st.metric("Total Acumulado en Ahorro", f"S/ {total_ahorrado_acumulado:,.2f}")
        if not df_ahorro.empty:
            st.dataframe(df_ahorro.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
