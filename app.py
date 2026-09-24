import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN GENERAL Y FUENTES
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Balance Diario de Ventas y Gastos", 
    layout="wide", 
    page_icon="📈"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

# Archivos de almacenamiento local CSV
ARCHIVO_GASTOS_DIARIOS = "gastos_diarios.csv"
ARCHIVO_GASTOS_FIJOS = "gastos_fijos.csv"
ARCHIVO_GASTOS_VARIABLES = "gastos_fijos_variables.csv"
ARCHIVO_FONDO_AHORRO = "fondo_ahorro.csv"

RESPALDO_MARGEN_MES = 2445.48

# -----------------------------------------------------------------------------
# 2. CONSULTAS A LA BASE DE DATOS SQLITE (tlt.sqlite3)
# -----------------------------------------------------------------------------
def obtener_balance_ventas(fecha_consulta):
    """
    Lee las ventas directamente desde el archivo tlt.sqlite3 guardado en el repositorio.
    """
    db_path = "tlt.sqlite3"
    fecha_str = fecha_consulta.strftime("%Y-%m-%d")
    mes_str = fecha_consulta.strftime("%Y-%m")
    
    ganancia_dia = 0.0
    ganancia_mes = RESPALDO_MARGEN_MES
    conectado = False

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            
            # 1. Ganancia del día seleccionado
            query_dia = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (strftime('%Y-%m-%d', fecha) = '{fecha_str}' OR fecha LIKE '{fecha_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_dia = pd.read_sql_query(query_dia, conn)
            if not df_dia.empty and df_dia["margen"].iloc[0] is not None:
                ganancia_dia = float(df_dia["margen"].iloc[0])

            # 2. Ganancia acumulada del mes
            query_mes = f"""
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE (strftime('%Y-%m', fecha) = '{mes_str}' OR fecha LIKE '{mes_str}%')
                  AND estado IN ('confirmada', 'entregada')
            """
            df_mes = pd.read_sql_query(query_mes, conn)
            if not df_mes.empty and df_mes["margen"].iloc[0] is not None:
                ganancia_mes = float(df_mes["margen"].iloc[0])

            conn.close()
            conectado = True
        except Exception:
            pass

    return ganancia_dia, ganancia_mes, conectado

# -----------------------------------------------------------------------------
# 3. MANEJO DE ARCHIVOS Y CARGA INICIAL
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

# Cargar DataFrames locales
df_diarios = cargar_csv(ARCHIVO_GASTOS_DIARIOS, ["Fecha", "Categoria", "Monto S/", "Detalle"])
df_fijos = cargar_csv(ARCHIVO_GASTOS_FIJOS, ["Concepto", "Monto S/", "Pagado"])
df_fijos_var = cargar_csv(ARCHIVO_GASTOS_VARIABLES, ["Fecha_Mes", "Servicio", "Monto S/"])
df_ahorro = cargar_csv(ARCHIVO_FONDO_AHORRO, ["Fecha", "Monto Ahorrado S/", "Comentario"])

# Actualización de Gastos Fijos (Alquiler: 700 / Universidad: 550)
if df_fijos.empty:
    df_fijos = pd.DataFrame([
        {"Concepto": "Alquiler", "Monto S/": 700.0, "Pagado": True},
        {"Concepto": "Universidad", "Monto S/": 550.0, "Pagado": True}
    ])
    guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)

# -----------------------------------------------------------------------------
# 4. CÁLCULOS GENERALES Y DÍA SELECCIONADO
# -----------------------------------------------------------------------------
hoy = datetime.date.today()
mes_actual_str = hoy.strftime("%Y-%m")

ganancia_dia_db, ganancia_mensual_ventas, conectado = obtener_balance_ventas(hoy)

# Gastos de hoy
if not df_diarios.empty:
    df_diarios["Fecha"] = pd.to_datetime(df_diarios["Fecha"]).dt.date
    df_diarios["Mes_Año"] = pd.to_datetime(df_diarios["Fecha"]).dt.strftime("%Y-%m")
    gastos_hoy_total = df_diarios[df_diarios["Fecha"] == hoy]["Monto S/"].sum()
    total_diarios_mes = df_diarios[df_diarios["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    gastos_hoy_total = 0.0
    total_diarios_mes = 0.0

# Gastos Fijos y Variables del Mes
total_fijos_mes = df_fijos["Monto S/"].sum() if not df_fijos.empty else 0.0

if not df_fijos_var.empty:
    df_fijos_var["Mes_Año"] = pd.to_datetime(df_fijos_var["Fecha_Mes"]).dt.strftime("%Y-%m")
    total_fijos_var_mes = df_fijos_var[df_fijos_var["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    total_fijos_var_mes = 0.0

total_gastos_mes = total_fijos_mes + total_fijos_var_mes + total_diarios_mes
ganancia_neta_mes = ganancia_mensual_ventas - total_gastos_mes
total_ahorrado_acumulado = df_ahorro["Monto Ahorrado S/"].sum() if not df_ahorro.empty else 0.0

# -----------------------------------------------------------------------------
# 5. ENCABEZADO Y BALANCE DEL DÍA EN TIEMPO REAL
# -----------------------------------------------------------------------------
st.title("📈 T L T Distribuciones — Balance Diario de Ventas y Gastos")

col_status, col_btn = st.columns([4, 1])
with col_status:
    if conectado:
        st.success(f"✅ **Conectado a Base de Datos (tlt.sqlite3)** — Margen del Mes Real: **S/ {ganancia_mensual_ventas:,.2f}**")
    else:
        st.warning(f"⚠️ **Base de datos no detectada. Usando respaldo de mes**: **S/ {RESPALDO_MARGEN_MES:,.2f}**")
with col_btn:
    if st.button("🔄 Sincronizar", use_container_width=True):
        st.rerun()

st.divider()

# Sección para registrar o ajustar la ganancia del día
st.subheader(f"📅 Balance de Hoy ({hoy.strftime('%d/%m/%Y')})")

col_input, col_m1, col_m2, col_m3 = st.columns([2, 2, 2, 2])

with col_input:
    ganancia_dia_final = st.number_input(
        "Ganancia de Ventas de Hoy (S/)", 
        min_value=0.0, 
        value=ganancia_dia_db, 
        step=10.0, 
        format="%.2f"
    )

ganancia_neta_dia = ganancia_dia_final - gastos_hoy_total

with col_m1:
    st.metric("Ventas / Ganancia Hoy", f"S/ {ganancia_dia_final:,.2f}")
with col_m2:
    st.metric("Gastos Registrados Hoy", f"S/ {gastos_hoy_total:,.2f}")
with col_m3:
    st.metric(
        "Ganancia Neta Limpia Hoy", 
        f"S/ {ganancia_neta_dia:,.2f}",
        delta=f"{'Superávit' if ganancia_neta_dia >= 0 else 'Déficit'}"
    )

st.divider()

# -----------------------------------------------------------------------------
# 6. PESTAÑAS DE NAVEGACIÓN
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Registrar Gastos",
    "2️⃣ Gastos Fijos (Alquiler/Univ.)",
    "3️⃣ Fijos Variables (Luz/Agua/Gas)",
    "4️⃣ 📈 Gráfica del Mes",
    "5️⃣ 📜 Historial / Meses Anteriores",
    "6️⃣ 🏦 Fondo de Ahorro"
])

# 1. REGISTRAR GASTOS DIARIOS
with tab1:
    st.subheader("➕ Registrar Gasto Diario")
    with st.form("form_diario", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            categoria = st.selectbox("Categoría", [
                "pasaje diario", 
                "pasaje empresa", 
                "gastos empresa", 
                "comida", 
                "extra", 
                "artículos"
            ])
        with c2:
            monto = st.number_input("Monto (S/)", min_value=0.0, step=0.5, format="%.2f")
        with c3:
            fecha_gasto = st.date_input("Fecha", value=datetime.date.today())
        
        detalle = st.text_input("Detalle (Ej: Pasaje a almacén, compra de empaques, comida)")
        
        if st.form_submit_button("💾 Guardar Gasto Diario", type="primary", use_container_width=True):
            if monto > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto, "Categoria": categoria, "Monto S/": monto, "Detalle": detalle.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Registrado S/ {monto:.2f} en {categoria}")
                st.rerun()

    st.subheader("📋 Gastos Registrados Hoy")
    if not df_diarios.empty:
        gastos_hoy_tabla = df_diarios[df_diarios["Fecha"] == hoy]
        if not gastos_hoy_tabla.empty:
            st.dataframe(gastos_hoy_tabla, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no has registrado gastos el día de hoy.")

# 2. GASTOS FIJOS
with tab2:
    st.subheader("📌 Gastos Fijos Mensuales")
    st.dataframe(df_fijos, use_container_width=True, hide_index=True)
    st.metric("Total Gastos Fijos Mensuales", f"S/ {total_fijos_mes:,.2f}")

# 3. FIJOS VARIABLES (LUS, AGUA, GAS)
with tab3:
    st.subheader("💡 Recibos Variables (Luz, Agua, Gas, Internet)")
    with st.form("form_fijo_var", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            servicio = st.selectbox("Servicio", ["Luz", "Agua", "Gas", "Internet", "Teléfono", "Otro"])
        with c2:
            monto_var = st.number_input("Monto Recibo (S/)", min_value=0.0, step=1.0, format="%.2f")
        with c3:
            fecha_servicio = st.date_input("Fecha Recibo", value=datetime.date.today())
            
        if st.form_submit_button("💾 Registrar Recibo", type="primary", use_container_width=True):
            if monto_var > 0:
                nuevo_recibo = pd.DataFrame([{"Fecha_Mes": fecha_servicio, "Servicio": servicio, "Monto S/": monto_var}])
                df_fijos_var = pd.concat([df_fijos_var, nuevo_recibo], ignore_index=True)
                guardar_csv(df_fijos_var, ARCHIVO_GASTOS_VARIABLES)
                st.success(f"Recibo registrado: {servicio} - S/ {monto_var:.2f}")
                st.rerun()

    if not df_fijos_var.empty:
        st.dataframe(df_fijos_var.sort_values(by="Fecha_Mes", ascending=False), use_container_width=True, hide_index=True)

# 4. GRÁFICA DEL MES
with tab4:
    st.subheader("📊 Gráfica de Evolución Mensual: Gastos vs Ganancias")
    col_metric1, col_metric2, col_metric3 = st.columns(3)
    col_metric1.metric("Ganancia Real del Mes", f"S/ {ganancia_mensual_ventas:,.2f}")
    col_metric2.metric("Total Gastos Acumulados", f"S/ {total_gastos_mes:,.2f}")
    col_metric3.metric("Ganancia Neta Disponible", f"S/ {ganancia_neta_mes:,.2f}")
    
    st.divider()
    
    dias_del_mes = pd.date_range(start=f"{mes_actual_str}-01", periods=30, freq='D')
    df_grafico_mes = pd.DataFrame({"Fecha": dias_del_mes.date})
    
    if not df_diarios.empty:
        df_gastos_diarios_agrup = df_diarios.groupby("Fecha")["Monto S/"].sum().reset_index()
        df_grafico_mes = pd.merge(df_grafico_mes, df_gastos_diarios_agrup, on="Fecha", how="left").fillna(0)
    else:
        df_grafico_mes["Monto S/"] = 0.0
        
    df_grafico_mes["Gastos Diarios Acumulados S/"] = df_grafico_mes["Monto S/"].cumsum() + total_fijos_mes + total_fijos_var_mes
    df_grafico_mes["Ganancia Ventas (Línea Base) S/"] = ganancia_mensual_ventas
    st.line_chart(df_grafico_mes.set_index("Fecha")[["Gastos Diarios Acumulados S/", "Ganancia Ventas (Línea Base) S/"]])

# 5. HISTORIAL POR MESES
with tab5:
    st.subheader("📜 Histórico de Gastos (Filtro por Mes)")
    mes_seleccionado = st.text_input("Ingresa el Mes a consultar (Ej: 2026-06, 2026-07, 2026-08, 2026-09)", value=mes_actual_str)
        
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
    st.metric("Total Acumulado en Ahorro", f"S/ {total_ahorrado_acumulado:,.2f}")
    if not df_ahorro.empty:
        st.dataframe(df_ahorro.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
