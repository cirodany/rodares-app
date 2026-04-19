import streamlit as st
import sqlite3
import pandas as pd

# Conexión a la base de datos
def conectar():
    return sqlite3.connect('rodares.db', check_same_thread=False)

st.set_page_config(page_title="RODARES - Sistema", layout="wide")
st.title("🏦 RODARES: Control de Préstamos")

menu = ["👥 Gestión de Socios", "💸 Nuevo Préstamo", "📊 Panel de Control"]
choice = st.sidebar.selectbox("Navegación", menu)

if choice == "👥 Gestión de Socios":
    st.header("Registro de Socios")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("nuevo_socio"):
            nombre = st.text_input("Nombre Completo")
            cedula = st.text_input("Cédula/ID")
            tel = st.text_input("Teléfono")
            if st.form_submit_button("Registrar"):
                db = conectar()
                try:
                    db.execute("INSERT INTO socios (nombre, cedula, telefono) VALUES (?,?,?)", (nombre, cedula, tel))
                    db.commit()
                    st.success("Socio guardado")
                except:
                    st.error("La cédula ya existe")
                db.close()
    
    with col2:
        st.write("Socios Actuales")
        db = conectar()
        df = pd.read_sql_query("SELECT * FROM socios", db)
        st.dataframe(df, use_container_width=True)
        db.close()

elif choice == "💸 Nuevo Préstamo":
    st.header("Asignar Préstamo a Socio")
    db = conectar()
    socios_df = pd.read_sql_query("SELECT id, nombre FROM socios", db)
    
    if socios_df.empty:
        st.warning("Primero debes registrar un socio.")
    else:
        # Creamos un diccionario para seleccionar por nombre pero guardar por ID
        opciones_socios = {row['nombre']: row['id'] for _, row in socios_df.iterrows()}
        seleccion = st.selectbox("Selecciona al Socio", opciones_socios.keys())
        
        monto = st.number_input("Monto ($)", min_value=100)
        tasa = st.number_input("Tasa Anual (%)", value=10.0)
        plazo = st.number_input("Plazo (meses)", min_value=1, value=12)
        
        if st.button("Crear Préstamo"):
            socio_id = opciones_socios[seleccion]
            db.execute("INSERT INTO prestamos (socio_id, monto, tasa_anual, plazo_meses) VALUES (?,?,?,?)", 
                       (socio_id, monto, tasa, plazo))
            db.commit()
            st.success(f"Préstamo registrado a {seleccion}")
    db.close()

elif choice == "📊 Panel de Control":
    st.header("Relación de Préstamos Activos")
    db = conectar()
    query = """
    SELECT p.id, s.nombre, p.monto, p.tasa_anual, p.plazo_meses, p.estado 
    FROM prestamos p 
    JOIN socios s ON p.socio_id = s.id
    """
    df_control = pd.read_sql_query(query, db)
    st.table(df_control)
    db.close()