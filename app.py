import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

# --- CONFIGURACIÓN DE SEGURIDAD ---
PASSWORD_SISTEMA = "familia2026"

def mostrar_logo():
    if os.path.exists("logo.jpeg"):
        st.image("logo.jpeg", width=115) 
    else:
        st.caption("(Logo 3x3 no encontrado)")

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        mostrar_logo()
        st.title("Acceso a RODARES")
        clave = st.text_input("Introduce la contraseña:", type="password")
        if st.button("Entrar"):
            if clave == PASSWORD_SISTEMA:
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Contraseña incorrecta")
        return False
    return True

def conectar():
    return sqlite3.connect('rodares.db', check_same_thread=False)

def inicializar_db():
    db = conectar()
    db.execute('CREATE TABLE IF NOT EXISTS socios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, cedula TEXT UNIQUE, telefono TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS prestamos (id INTEGER PRIMARY KEY AUTOINCREMENT, socio_id INTEGER, monto REAL, tasa_anual REAL, plazo_meses INTEGER, fecha_inicio DATE, estado TEXT DEFAULT "ACTIVO")')
    db.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER, numero_cuota INTEGER, monto_pagado REAL, fecha_pago DATE, estado_pago TEXT DEFAULT "PENDIENTE")')
    db.execute('CREATE TABLE IF NOT EXISTS aportes (id INTEGER PRIMARY KEY AUTOINCREMENT, socio_id INTEGER, monto REAL, mes TEXT, anio TEXT, fecha_registro DATE)')
    db.commit()
    db.close()

if login():
    inicializar_db()
    db = conectar()

    # --- LÓGICA CONTABLE MAESTRA ---
    cap_rec = db.execute("SELECT SUM(monto) FROM aportes").fetchone()[0] or 0
    cob_tot = db.execute("SELECT SUM(monto_pagado) FROM pagos WHERE estado_pago='PAGADO'").fetchone()[0] or 0
    prest_capital_fuera = db.execute("SELECT SUM(monto) FROM prestamos WHERE estado IN ('ACTIVO', 'REFINANCIADO', 'FINALIZADO')").fetchone()[0] or 0
    disponible_caja = cap_rec + cob_tot - prest_capital_fuera
    monto_en_calle = db.execute("SELECT SUM(monto_pagado) FROM pagos WHERE estado_pago='PENDIENTE'").fetchone()[0] or 0

    col_l, col_t = st.columns(2)
    with col_l: mostrar_logo()
    with col_t: st.title("Sistema RODARES")

    if 'menu_option' not in st.session_state:
        st.session_state.menu_option = "👥 Socios"

    menu = ["👥 Socios", "🧮 Simulador", "💰 Aportes Mensuales", "💸 Nuevo Préstamo", "📊 Panel Individual", "🛠️ Admin", "📑 Reportes y Consultas"]
    choice = st.sidebar.selectbox("Menú Principal", menu, index=menu.index(st.session_state.menu_option))
    st.session_state.menu_option = choice

    # --- 1. SOCIOS ---
    if choice == "👥 Socios":
        st.header("Relación de Socios")
        df_s = pd.read_sql_query("SELECT nombre as Nombre, telefono as Teléfono FROM socios", db)
        st.table(df_s)
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ Nuevo Socio"): st.session_state.f_socio = True
        with b2:
            if st.button("🧮 Ir al Simulador"):
                st.session_state.menu_option = "🧮 Simulador"
                st.rerun()

        if st.session_state.get("f_socio", False):
            with st.form("ns"):
                n = st.text_input("Nombre"); c = st.text_input("Cédula"); t = st.text_input("Teléfono")
                if st.form_submit_button("Guardar"):
                    db.execute("INSERT INTO socios (nombre, cedula, telefono) VALUES (?,?,?)", (n,c,t)); db.commit()
                    st.success("Socio Registrado"); st.session_state.f_socio = False; st.rerun()

    # --- 2. SIMULADOR ---
    elif choice == "🧮 Simulador":
        st.header("Simulador de Préstamos (5% Mensual)")
        with st.form("sim"):
            m = st.number_input("Monto (€)", min_value=10.0, value=100.0)
            p = st.number_input("Meses", min_value=1, value=4)
            if st.form_submit_button("Calcular"):
                abono = m / p
                plan = []
                for n in range(1, p + 1):
                    interes = (m - abono*(n-1)) * 0.05
                    plan.append({"Mes": n, "Cuota": f"{round(abono+interes,2)} €", "Capital": f"{round(abono,2)} €", "Interés": f"{round(interes,2)} €"})
                st.table(plan)

    # --- 3. APORTES ---
    elif choice == "💰 Aportes Mensuales":
        st.header("Gestión de Aportes")
        socios_df = pd.read_sql_query("SELECT id, nombre FROM socios", db)
        s_sel = st.selectbox("Seleccionar Socio:", [""] + socios_df['nombre'].tolist(), key="sb_ap")
        
        if s_sel:
            sid = int(socios_df[socios_df['nombre'] == s_sel]['id'].iloc[0])
            df_ind = pd.read_sql_query(f"SELECT mes as Mes, monto as Monto FROM aportes WHERE socio_id={sid} ORDER BY id DESC", db)
            st.subheader(f"Historial de {s_sel}")
            st.table(df_ind)

        if st.button("➕ Registrar Aporte (10€)"): st.session_state.f_ap = True
        if st.session_state.get("f_ap", False):
            with st.form("fa"):
                s_ap = st.selectbox("Socio", socios_df['nombre'].tolist())
                m_ap = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
                if st.form_submit_button("Guardar"):
                    sid_ap = int(socios_df[socios_df['nombre'] == s_ap]['id'].iloc[0])
                    db.execute("INSERT INTO aportes (socio_id, monto, mes, anio) VALUES (?,?,?,'2026')", (sid_ap, 10.0, m_ap))
                    db.commit(); st.success("Guardado"); st.session_state.f_ap = False; st.rerun()

        if st.button("📊 Ver Matriz General 2026"):
            df_all = pd.read_sql_query("SELECT s.nombre as Socio, a.mes, a.monto FROM aportes a JOIN socios s ON a.socio_id = s.id", db)
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            if not df_all.empty:
                matriz = df_all.pivot_table(index='Socio', columns='mes', values='monto', aggfunc='sum').fillna(0)
                for m in meses: 
                    if m not in matriz.columns: matriz[m] = 0.0
                matriz = matriz[meses]
                matriz['TOTAL'] = matriz.sum(axis=1)
                st.dataframe(matriz.style.map(lambda v: 'background-color: #d1e7ff' if v > 0 else '').format("{:.2f} €"), use_container_width=True)

    # --- 4. NUEVO PRÉSTAMO ---
    elif choice == "💸 Nuevo Préstamo":
        st.header("Generar Préstamo Real")
        st.info(f"💰 Disponible en Caja: {disponible_caja:,.2f} €")
        socios_df = pd.read_sql_query("SELECT id, nombre FROM socios", db)
        with st.form("fp"):
            s_nom = st.selectbox("Socio", [""] + socios_df['nombre'].tolist())
            mto = st.number_input("Monto (€)", min_value=0.0)
            plz = st.number_input("Meses", min_value=1)
            btn = st.form_submit_button("Procesar Préstamo")

        if btn:
            if mto > disponible_caja: st.error("❌ Fondos insuficientes en caja.")
            elif s_nom:
                sid = int(socios_df[socios_df['nombre'] == s_nom]['id'].iloc[0])
                res_d = db.execute(f"SELECT SUM(monto_pagado) FROM pagos pg JOIN prestamos p ON pg.prestamo_id=p.id WHERE p.socio_id={sid} AND pg.estado_pago='PENDIENTE' AND p.estado='ACTIVO'").fetchone()[0]
                deuda = res_d if res_d else 0
                
                if deuda > 0:
                    st.markdown("<h2 style='color:red; text-align:center;'>REFINANCIADO</h2>", unsafe_allow_html=True)
                    db.execute(f"UPDATE prestamos SET estado='REFINANCIADO' WHERE socio_id={sid} AND estado='ACTIVO'")
                
                cap_tot = mto + deuda
                abono = cap_tot / plz
                cur = db.cursor()
                cur.execute("INSERT INTO prestamos (socio_id, monto, tasa_anual, plazo_meses, fecha_inicio) VALUES (?,?,?,?,?)", (sid, cap_tot, 5.0, plz, datetime.now().strftime('%Y-%m-%d')))
                pid = cur.lastrowid
                for n in range(1, plz+1):
                    cuota = abono + ((cap_tot - abono*(n-1)) * 0.05)
                    venc = (datetime.now() + timedelta(days=30*n)).strftime('%Y-%m-%d')
                    cur.execute("INSERT INTO pagos (prestamo_id, numero_cuota, monto_pagado, fecha_pago) VALUES (?,?,?,?)", (pid, n, round(cuota, 2), venc))
                db.commit(); st.success(f"✅ Préstamo Procesado. Nuevo Capital: {cap_tot:,.2f} €")

    # --- 5. PANEL INDIVIDUAL ---
    elif choice == "📊 Panel Individual":
        st.header("Estado de Cuenta")
        socios_df = pd.read_sql_query("SELECT id, nombre FROM socios", db)
        s_sel = st.selectbox("Socio:", [""] + socios_df['nombre'].tolist(), key="sb_ind")
        if s_sel:
            sid = int(socios_df[socios_df['nombre'] == s_sel]['id'].iloc[0])
            df_c = pd.read_sql_query(f"SELECT pg.id, pg.numero_cuota as Cuota, pg.monto_pagado as Monto, pg.fecha_pago as Vencimiento, pg.estado_pago as Estado FROM pagos pg JOIN prestamos p ON pg.prestamo_id = p.id WHERE p.socio_id={sid} AND p.estado IN ('ACTIVO', 'REFINANCIADO')", db)
            st.dataframe(df_c, use_container_width=True)
            pendientes = df_c[df_c['Estado'] == 'PENDIENTE']
            if not pendientes.empty:
                id_p = st.selectbox("ID Cuota a cobrar:", pendientes['id'].tolist())
                if st.button("Confirmar Pago"):
                    db.execute("UPDATE pagos SET estado_pago = 'PAGADO' WHERE id = ?", (id_p,)); db.commit(); st.rerun()

    # --- 6. ADMIN ---
    elif choice == "🛠️ Admin":
        st.header("Tablero de Administración")
        c1, c2 = st.columns(2)
        c1.metric("Capital Recibido (Ahorros)", f"{cap_rec:,.2f} €")
        c2.metric("Cobrado Total (Cuotas)", f"{cob_tot:,.2f} €")
        c3, c4 = st.columns(2)
        c3.metric("Monto en Calle (Deuda)", f"{monto_en_calle:,.2f} €")
        c4.metric("💰 Disponible en Caja", f"{disponible_caja:,.2f} €")
        st.divider()
        if st.button("🚨 BORRAR PRÉSTAMOS"):
            db.execute("DELETE FROM pagos"); db.execute("DELETE FROM prestamos"); db.commit(); st.rerun()

    # --- 7. REPORTES Y CONSULTAS ---
    elif choice == "📑 Reportes y Consultas":
        st.header("Reportes y Consultas")
        t1, t2 = st.tabs(["📋 Relación de Préstamos", "📈 Gráfico de Ganancias"])
        with t1:
            st.dataframe(pd.read_sql_query("SELECT s.nombre as Socio, p.fecha_inicio as Fecha, p.monto as Monto FROM prestamos p JOIN socios s ON p.socio_id=s.id", db))
        with t2:
            df_gan = pd.read_sql_query("SELECT pg.fecha_pago, (pg.monto_pagado - (p.monto/p.plazo_meses)) as ganancia FROM pagos pg JOIN prestamos p ON pg.prestamo_id=p.id WHERE pg.estado_pago='PAGADO'", db)
            if not df_gan.empty:
                df_gan['fecha_pago'] = pd.to_datetime(df_gan['fecha_pago'])
                df_gan = df_gan.set_index('fecha_pago').resample('D').sum().cumsum()
                st.line_chart(df_gan['ganancia'])
    
    db.close()
