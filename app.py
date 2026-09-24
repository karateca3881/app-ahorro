import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN GENERAL Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T L T Distribuciones — Finanzas, Gastos y Ahorro", 
    layout="wide", 
    page_icon="📈"
)

# Tipografía limpia y moderna
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

# Nombres de archivos CSV locales
ARCHIVO_GASTOS_DIARIOS = "gastos_diarios.csv"
ARCHIVO_GASTOS_FIJOS = "gastos_fijos.csv"
ARCHIVO_GASTOS_VARIABLES = "gastos_fijos_variables.csv"
ARCHIVO_FONDO_AHORRO = "fondo_ahorro.csv"

RESPALDO_MARGEN = 2445.48

# -----------------------------------------------------------------------------
# 2. CONSULTA DIRECTA DE VENTAS DE DJANGO (tlt.sqlite3)
# -----------------------------------------------------------------------------
def obtener_balance_ventas_tlt():
    """Consulta el margen acumulado del mes directamente desde tlt.sqlite3."""
    db_path = "tlt.sqlite3"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            query = """
                SELECT SUM(total_venta - total_costo) AS margen 
                FROM proformas_proforma 
                WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
                  AND estado IN ('confirmada', 'entregada')
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty and df["margen"].iloc[0] is not None:
                return float(df["margen"].iloc[0]), True
        except Exception:
            pass
            
    return RESPALDO_MARGEN, True

# -----------------------------------------------------------------------------
# 3. MANEJO Y PRECARGA ÚNICA DE DATOS
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

# Inicializar DataFrames locales
df_diarios = cargar_csv(ARCHIVO_GASTOS_DIARIOS, ["Fecha", "Categoria", "Monto S/", "Detalle"])
df_fijos = cargar_csv(ARCHIVO_GASTOS_FIJOS, ["Concepto", "Monto S/", "Pagado"])
df_fijos_var = cargar_csv(ARCHIVO_GASTOS_VARIABLES, ["Fecha_Mes", "Servicio", "Monto S/"])
df_ahorro = cargar_csv(ARCHIVO_FONDO_AHORRO, ["Fecha", "Monto Ahorrado S/", "Comentario"])

# PRECARGA ÚNICA DE GASTOS FIJOS (Alquiler: 700, Universidad: 550)
if df_fijos.empty:
    df_fijos = pd.DataFrame([
        {"Concepto": "Alquiler", "Monto S/": 700.0, "Pagado": True},
        {"Concepto": "Universidad", "Monto S/": 550.0, "Pagado": True}
    ])
    guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)

# -----------------------------------------------------------------------------
# 4. CÁLCULOS PRINCIPALES
# -----------------------------------------------------------------------------
ganancia_mensual_ventas, conectado = obtener_balance_ventas_tlt()

total_fijos_mes = df_fijos["Monto S/"].sum() if not df_fijos.empty else 0.0
fijos_pagados = df_fijos[df_fijos["Pagado"] == True]["Monto S/"].sum() if not df_fijos.empty else 0.0

hoy = datetime.date.today()
mes_actual_str = hoy.strftime("%Y-%m")

if not df_fijos_var.empty:
    df_fijos_var["Mes_Año"] = pd.to_datetime(df_fijos_var["Fecha_Mes"]).dt.strftime("%Y-%m")
    total_fijos_var_mes = df_fijos_var[df_fijos_var["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    total_fijos_var_mes = 0.0

if not df_diarios.empty:
    df_diarios["Mes_Año"] = pd.to_datetime(df_diarios["Fecha"]).dt.strftime("%Y-%m")
    total_diarios_mes = df_diarios[df_diarios["Mes_Año"] == mes_actual_str]["Monto S/"].sum()
else:
    total_diarios_mes = 0.0

total_gastos_mes = total_fijos_mes + total_fijos_var_mes + total_diarios_mes
total_ahorrado_acumulado = df_ahorro["Monto Ahorrado S/"].sum() if not df_ahorro.empty else 0.0
ganancia_neta_mes = ganancia_mensual_ventas - total_gastos_mes

# -----------------------------------------------------------------------------
# 5. ENCABEZADO PRINCIPAL
# -----------------------------------------------------------------------------
st.title("📈 T L T Distribuciones — Finanzas, Gastos y Fondo de Ahorro")

porcentaje_gastado = (total_gastos_mes / ganancia_mensual_ventas) * 100 if ganancia_mensual_ventas > 0 else 0

if total_gastos_mes > ganancia_mensual_ventas:
    st.error(f"🚨 **ALERTA DE DÉFICIT:** Los gastos acumulados (S/ {total_gastos_mes:,.2f}) superan las ganancias del mes (S/ {ganancia_mensual_ventas:,.2f}). Déficit: S/ {abs(ganancia_neta_mes):,.2f}")
elif porcentaje_gastado >= 85:
    st.warning(f"⚠️ **ADVERTENCIA:** Has utilizado el **{porcentaje_gastado:.1f}%** de tus ganancias acumuladas este mes.")

col_status, col_btn = st.columns([4, 1])
with col_status:
    if conectado:
        st.success(f"✅ **Conectado a Base de Datos (tlt.sqlite3)** — Margen del Mes Real: **S/ {ganancia_mensual_ventas:,.2f}**")
    else:
        st.warning(f"⚠️ **Usando monto estimado/respaldo**: **S/ {RESPALDO_MARGEN:,.2f}**")
with col_btn:
    if st.button("🔄 Sincronizar", use_container_width=True):
        st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# 6. PESTAÑAS DE NAVEGACIÓN DE LA APLICACIÓN
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Registrar Gastos",
    "2️⃣ Gastos Fijos (Alquiler/Univ.)",
    "3️⃣ Fijos Variables (Luz/Agua/Gas)",
    "4️⃣ 📈 Gráfica del Mes",
    "5️⃣ 📜 Historial de Gastos",
    "6️⃣ 🏦 Fondo de Ahorro"
])

# PESTAÑA 1: REGISTRO DE GASTOS DIARIOS DESDE LA APLICACIÓN
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
        
        detalle = st.text_input("Detalle del gasto (Ej: Pasajes de ruta, compras de embalaje, etc.)")
        
        if st.form_submit_button("💾 Guardar Gasto", type="primary", use_container_width=True):
            if monto > 0:
                nuevo = pd.DataFrame([{"Fecha": fecha_gasto, "Categoria": categoria, "Monto S/": monto, "Detalle": detalle.strip()}])
                df_diarios = pd.concat([df_diarios, nuevo], ignore_index=True)
                guardar_csv(df_diarios, ARCHIVO_GASTOS_DIARIOS)
                st.success(f"Registrado S/ {monto:.2f} en {categoria}")
                st.rerun()

    st.subheader("📋 Registro de Gastos Guardados")
    if not df_diarios.empty:
        st.dataframe(df_diarios.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)

# PESTAÑA 2: GASTOS FIJOS
with tab2:
    st.subheader("📌 Gastos Fijos Mensuales")
    col_add, col_list = st.columns([2, 3])
    with col_add:
        with st.form("form_fijo", clear_on_submit=True):
            concepto = st.text_input("Concepto", value="")
            monto_fijo = st.number_input("Monto Mensual (S/)", min_value=0.0, step=10.0, format="%.2f")
            pagado = st.checkbox("¿Pagado este mes?", value=True)
            
            if st.form_submit_button("💾 Actualizar / Agregar Fijo", use_container_width=True):
                if concepto:
                    df_fijos = df_fijos[df_fijos["Concepto"] != concepto]
                    nuevo_fijo = pd.DataFrame([{"Concepto": concepto.strip(), "Monto S/": monto_fijo, "Pagado": pagado}])
                    df_fijos = pd.concat([df_fijos, nuevo_fijo], ignore_index=True)
                    guardar_csv(df_fijos, ARCHIVO_GASTOS_FIJOS)
                    st.success(f"Gasto fijo '{concepto}' actualizado.")
                    st.rerun()

    with col_list:
        st.dataframe(df_fijos, use_container_width=True, hide_index=True)
        st.metric("Total Gastos Fijos", f"S/ {total_fijos_mes:,.2f}", delta=f"Pagado: S/ {fijos_pagados:,.2f}")

# PESTAÑA 3: FIJOS VARIABLES (LUZ, AGUA, GAS, ETC.)
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

# PESTAÑA 4: GRÁFICA DEL MES
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

# PESTAÑA 5: HISTORIAL
with tab5:
    st.subheader("📜 Histórico de Gastos por Mes")
    mes_seleccionado = st.text_input("Filtrar por Mes/Año (Ejemplo: 2026-06, 2026-07, 2026-08, 2026-09)", value=mes_actual_str)
        
    if not df_diarios.empty:
        df_filtrado_mes = df_diarios[df_diarios["Mes_Año"] == mes_seleccionado]
        if not df_filtrado_mes.empty:
            st.dataframe(df_filtrado_mes, use_container_width=True, hide_index=True)
            st.info(f"Total gastos diarios en {mes_seleccionado}: S/ {df_filtrado_mes['Monto S/'].sum():,.2f}")
        else:
            st.warning(f"No hay registros de gastos diarios para el periodo {mes_seleccionado}.")

# PESTAÑA 6: FONDO DE AHORRO
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