import streamlit as st
import json
import pandas as pd
from db import (
    autenticar, crear_usuario, usuario_existe, contar_admins,
    obtener_vehiculos_de_usuario, crear_vehiculo, eliminar_vehiculo,
    placas_existen, obtener_espacios, obtener_registro_activo_de_usuario,
    generar_qr_imagen,
    # FASE 4
    obtener_vehiculo_por_placas, obtener_registro_activo_por_vehiculo,
    registrar_entrada, registrar_salida, obtener_vehiculos_dentro,
    decodificar_qr_de_imagen, imagen_a_base64, base64_a_bytes,
    # FASE 5
    obtener_todos_usuarios, eliminar_usuario, obtener_todos_los_registros
)

st.set_page_config(
    page_title="Estacionamiento Yahualica",
    page_icon="🅿️",
    layout="wide"
)

# --- ESTILOS ---
st.markdown("""
<style>
    .titulo-principal { text-align: center; color: #00f3ff; font-size: 2.2rem; font-weight: 800; margin-bottom: 0; }
    .subtitulo { text-align: center; color: #888; font-size: 0.95rem; margin-top: -10px; margin-bottom: 30px; }
    .panel-header { background: linear-gradient(135deg, #00d2ff 0%, #0072ff 100%); padding: 20px; border-radius: 12px; color: #000; font-weight: 700; margin-bottom: 20px; }
    .contador-card { background: #111; border: 2px solid #00f3ff; border-radius: 16px; padding: 16px; text-align: center; box-shadow: 0 0 15px rgba(0, 243, 255, 0.3); }
    .contador-card h4 { color: #888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin: 0; }
    .contador-card .numero { font-size: 1.8rem; font-weight: 800; color: #00f3ff; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)


# --- ESTADO DE SESIÓN ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'qr_generado' not in st.session_state:
    st.session_state.qr_generado = None


def cerrar_sesion():
    st.session_state.usuario = None
    st.session_state.qr_generado = None
    st.rerun()


# =========================================================
# PANTALLA DE LOGIN
# =========================================================
def pantalla_login():
    st.markdown('<p class="titulo-principal">🅿️ Estacionamiento Yahualica</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo">Control de acceso inteligente</p>', unsafe_allow_html=True)

    # --- Bootstrap: primer administrador (solo si no existe ninguno) ---
    if contar_admins() == 0:
        with st.expander("🚨 Configuración inicial: Crear el primer Administrador", expanded=True):
            st.warning("No existe ningún administrador. Crea uno para poder gestionar el sistema.")
            with st.form("form_primer_admin"):
                usuario_admin = st.text_input("Usuario admin")
                pass_admin = st.text_input("Contraseña", type="password")
                nombre_admin = st.text_input("Nombre completo")
                if st.form_submit_button("Crear Administrador"):
                    if not usuario_admin or not pass_admin or not nombre_admin:
                        st.error("Todos los campos son obligatorios")
                    elif usuario_existe(usuario_admin.lower().strip()):
                        st.error("Ese usuario ya existe")
                    else:
                        crear_usuario(
                            usuario=usuario_admin.lower().strip(),
                            password=pass_admin,
                            rol='admin',
                            tipo_usuario='administrativo',
                            nombre_completo=nombre_admin
                        )
                        st.success("✅ Administrador creado. Ahora inicia sesión.")
                        st.rerun()

    # --- Login (única opción) ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.markdown("### 🔑 Iniciar Sesión")
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar al Sistema", use_container_width=True)

            if submitted:
                if not usuario or not password:
                    st.error("Completa todos los campos")
                else:
                    user = autenticar(usuario.lower().strip(), password)
                    if user:
                        st.session_state.usuario = user
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")

        st.caption("🔒 Las cuentas son creadas por el administrador. Contacta al personal de la universidad si necesitas acceso.")


# =========================================================
# PANEL DEL ALUMNO (FASE 3)
# =========================================================
def panel_alumno():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">🎓 Panel del Alumno — {user["nombre_completo"]}</div>', unsafe_allow_html=True)

    with st.expander("👤 Ver mi perfil"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Usuario:** {user['usuario']}")
            st.write(f"**ID Estudiante:** {user['id_estudiante'] or 'N/A'}")
            st.write(f"**Matrícula:** {user['matricula'] or 'N/A'}")
        with col2:
            st.write(f"**Carrera:** {user['carrera'] or 'N/A'}")
            st.write(f"**Grupo:** {user['grupo'] or 'N/A'}")
            st.write(f"**Teléfono:** {user['telefono'] or 'N/A'}")

    st.markdown("### 🅿️ Lugares disponibles")
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

    col1, col2 = st.columns(2)
    with col1:
        if autos:
            disponibles_autos = autos['capacidad_total'] - autos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🚗 Automóviles</h4><div class="numero">{disponibles_autos} de {autos["capacidad_total"]}</div></div>', unsafe_allow_html=True)
    with col2:
        if motos:
            disponibles_motos = motos['capacidad_total'] - motos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🏍️ Motocicletas</h4><div class="numero">{disponibles_motos} de {motos["capacidad_total"]}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    registro_activo = obtener_registro_activo_de_usuario(user['id'])
    if registro_activo:
        st.success(f"✅ Tienes un vehículo **DENTRO** del estacionamiento.")
        st.write(f"**Placas:** {registro_activo['placas']} — **Tipo:** {registro_activo['tipo']}")
        st.write(f"**Hora de entrada:** {registro_activo['hora_entrada']}")

    st.markdown("### 🚘 Mis vehículos registrados")
    vehiculos = obtener_vehiculos_de_usuario(user['id'])

    if not vehiculos:
        st.info("Aún no tienes vehículos registrados. Agrega uno abajo. 👇")
    else:
        for v in vehiculos:
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
                    st.markdown(f"#### {icono} {v['tipo']} — **{v['placas']}**")
                    st.caption(f"Marca: {v['marca'] or 'N/A'} | Modelo: {v['modelo'] or 'N/A'} | Color: {v['color'] or 'N/A'}")
                with col2:
                    if st.button("🎫 Generar QR", key=f"qr_{v['id']}", use_container_width=True):
                        qr_data = {
                            "id_usuario": user['id'], "usuario": user['usuario'],
                            "nombre": user['nombre_completo'], "id_estudiante": user['id_estudiante'],
                            "matricula": user['matricula'], "carrera": user['carrera'],
                            "grupo": user['grupo'], "id_vehiculo": v['id'],
                            "tipo": v['tipo'], "placas": v['placas']
                        }
                        st.session_state.qr_generado = {
                            "imagen": generar_qr_imagen(qr_data),
                            "vehiculo": v, "datos": qr_data
                        }
                        st.rerun()
                with col3:
                    if st.button("🗑️ Eliminar", key=f"del_{v['id']}", use_container_width=True):
                        eliminar_vehiculo(v['id'])
                        st.success("Vehículo eliminado")
                        st.rerun()

    with st.expander("➕ Registrar nuevo vehículo"):
        with st.form("form_vehiculo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo de vehículo", ["Auto", "Moto"])
                placas = st.text_input("Placas").upper().strip()
                color = st.text_input("Color (opcional)")
            with col2:
                marca = st.text_input("Marca (opcional)")
                modelo = st.text_input("Modelo (opcional)")

            submitted = st.form_submit_button("Registrar vehículo", use_container_width=True)

            if submitted:
                errores = []
                if not placas:
                    errores.append("Las placas son obligatorias")
                if placas and placas_existen(placas):
                    errores.append(f"Ya existe un vehículo con esas placas ({placas})")

                if errores:
                    for e in errores:
                        st.error(e)
                else:
                    try:
                        crear_vehiculo(user['id'], tipo, placas, marca or None, modelo or None, color or None)
                        st.success(f"✅ Vehículo {placas} registrado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

    if st.session_state.qr_generado:
        qr_info = st.session_state.qr_generado
        st.markdown("---")
        st.markdown("### 🎫 Tu código QR")
        st.info("Presenta este código en la caseta del estacionamiento al entrar y salir.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(qr_info['imagen'], caption=f"QR — {qr_info['vehiculo']['tipo']} {qr_info['vehiculo']['placas']}")
            st.download_button("📥 Descargar QR", data=qr_info['imagen'],
                               file_name=f"QR_{qr_info['vehiculo']['placas']}.png",
                               mime="image/png", use_container_width=True)
            if st.button("❌ Cerrar QR", use_container_width=True):
                st.session_state.qr_generado = None
                st.rerun()


# =========================================================
# PANEL DEL TRABAJADOR (FASE 4)
# =========================================================
def panel_trabajador():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👷 Panel de Caseta — {user["nombre_completo"]}</div>', unsafe_allow_html=True)

    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if autos: st.metric("🚗 Autos dentro", f"{autos['ocupados']} / {autos['capacidad_total']}")
    with col2:
        if motos: st.metric("🏍️ Motos dentro", f"{motos['ocupados']} / {motos['capacidad_total']}")
    with col3:
        if autos: st.metric("🅿️ Autos libres", autos['capacidad_total'] - autos['ocupados'])
    with col4:
        if motos: st.metric("🅿️ Motos libres", motos['capacidad_total'] - motos['ocupados'])

    st.markdown("---")

    tab_scan, tab_dentro = st.tabs(["📷 Escanear QR / Registrar Movimiento", "📋 Vehículos Dentro"])

    with tab_scan:
        st.markdown("### 1️⃣ Escanea el QR del alumno o ingresa las placas")
        col_a, col_b = st.columns(2)
        with col_a:
            foto_qr = st.camera_input("📸 Escanear QR con la cámara", key="cam_qr")
        with col_b:
            placas_manual = st.text_input("⌨️ O escribe las placas manualmente", key="placas_manual").upper().strip()

        placas_detectadas = None
        if foto_qr is not None:
            try:
                qr_data = decodificar_qr_de_imagen(foto_qr.getvalue())
                if qr_data:
                    data = json.loads(qr_data)
                    placas_detectadas = data.get("placas", "").upper()
                    st.success(f"✅ QR leído: **{placas_detectadas}**")
                else:
                    st.warning("⚠️ No se pudo leer ningún QR. Intenta de nuevo o usa la entrada manual.")
            except Exception as e:
                st.error(f"Error al leer el QR: {e}")

        if placas_manual:
            placas_detectadas = placas_manual

        if placas_detectadas:
            vehiculo = obtener_vehiculo_por_placas(placas_detectadas)
            if not vehiculo:
                st.error(f"❌ No existe ningún vehículo registrado con las placas **{placas_detectadas}**.")
            else:
                st.markdown("### 2️⃣ Vehículo encontrado")
                with st.container(border=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        icono = "🚗" if vehiculo['tipo'] == 'Auto' else "🏍️"
                        st.markdown(f"#### {icono} {vehiculo['tipo']} — {vehiculo['placas']}")
                        st.caption(f"Marca: {vehiculo['marca'] or 'N/A'} | Modelo: {vehiculo['modelo'] or 'N/A'} | Color: {vehiculo['color'] or 'N/A'}")
                    with col2:
                        st.markdown(f"**Dueño:** {vehiculo['nombre_completo']}")
                        st.caption(f"Matrícula: {vehiculo['matricula'] or 'N/A'}")
                        st.caption(f"Carrera: {vehiculo['carrera'] or 'N/A'} | Grupo: {vehiculo['grupo'] or 'N/A'}")

                registro_activo = obtener_registro_activo_por_vehiculo(vehiculo['id'])
                st.markdown("### 3️⃣ Toma la evidencia fotográfica")
                foto_evidencia = st.camera_input("📸 Evidencia del vehículo", key="cam_evidencia")
                st.markdown("### 4️⃣ Confirma el movimiento")

                if registro_activo:
                    st.info(f"🟢 Este vehículo **está DENTRO** desde {registro_activo['hora_entrada']}. Se registrará su **SALIDA**.")
                    if st.button("🚪 Registrar SALIDA", type="primary", use_container_width=True):
                        if not foto_evidencia:
                            st.error("Debes tomar una foto de evidencia antes de registrar la salida.")
                        else:
                            registrar_salida(registro_activo['id'], vehiculo['tipo'],
                                             user['id'], imagen_a_base64(foto_evidencia.getvalue()))
                            st.success(f"✅ Salida registrada para {vehiculo['placas']}.")
                            st.balloons()
                else:
                    st.info(f"🔵 Este vehículo **NO está dentro**. Se registrará su **ENTRADA**.")
                    if st.button("🚗 Registrar ENTRADA", type="primary", use_container_width=True):
                        if not foto_evidencia:
                            st.error("Debes tomar una foto de evidencia antes de registrar la entrada.")
                        else:
                            registrar_entrada(vehiculo['id_usuario'], vehiculo['id'],
                                              vehiculo['tipo'], user['id'],
                                              imagen_a_base64(foto_evidencia.getvalue()))
                            st.success(f"✅ Entrada registrada para {vehiculo['placas']}.")
                            st.balloons()

    with tab_dentro:
        st.markdown("### 🚘 Vehículos actualmente dentro")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 Refrescar", use_container_width=True):
                st.rerun()
        dentro = obtener_vehiculos_dentro()
        if not dentro:
            st.info("No hay vehículos dentro en este momento.")
        else:
            st.write(f"**Total: {len(dentro)} vehículo(s)**")
            for v in dentro:
                with st.container(border=True):
                    icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
                        st.caption(f"Matrícula: {v['matricula'] or 'N/A'} | Carrera: {v['carrera'] or 'N/A'}")
                    with col2:
                        st.caption(f"Entrada: {v['hora_entrada']}")
                        st.caption(f"ID registro: #{v['id_registro']}")
                    with col3:
                        if st.button("🚪 Salida", key=f"sal_{v['id_registro']}", use_container_width=True):
                            st.session_state[f"salida_rapida_{v['id_registro']}"] = True
                            st.rerun()

                if st.session_state.get(f"salida_rapida_{v['id_registro']}", False):
                    st.markdown("#### 📸 Toma evidencia de salida")
                    foto_sal = st.camera_input(f"Evidencia de salida — {v['placas']}", key=f"cam_sal_{v['id_registro']}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ Confirmar salida", key=f"conf_sal_{v['id_registro']}", type="primary"):
                            if not foto_sal:
                                st.error("Necesitas tomar la foto de evidencia.")
                            else:
                                registrar_salida(v['id_registro'], v['tipo'], user['id'],
                                                 imagen_a_base64(foto_sal.getvalue()))
                                st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                                st.success(f"✅ Salida registrada para {v['placas']}.")
                                st.rerun()
                    with col_b:
                        if st.button("❌ Cancelar", key=f"canc_sal_{v['id_registro']}"):
                            st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                            st.rerun()


# =========================================================
# PANEL DEL ADMINISTRADOR (FASE 5 - COMPLETO)
# =========================================================
def panel_admin():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👑 Panel del Administrador — {user["nombre_completo"]}</div>', unsafe_allow_html=True)

    tab_dash, tab_usuarios, tab_registros, tab_metricas = st.tabs([
        "📊 Dashboard", "👥 Gestión de Usuarios", "📋 Registros", "📈 Métricas"
    ])

    # =========================================================
    # TAB 1: DASHBOARD
    # =========================================================
    with tab_dash:
        st.markdown("### 📊 Estado actual del estacionamiento")
        espacios = obtener_espacios()
        autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
        motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if autos: st.metric("🚗 Autos dentro", f"{autos['ocupados']}", f"{autos['capacidad_total'] - autos['ocupados']} libres")
        with col2:
            if motos: st.metric("🏍️ Motos dentro", f"{motos['ocupados']}", f"{motos['capacidad_total'] - motos['ocupados']} libres")
        with col3:
            total_usuarios = len(obtener_todos_usuarios())
            st.metric("👥 Usuarios totales", total_usuarios)
        with col4:
            registros = obtener_todos_los_registros()
            dentro_ahora = sum(1 for r in registros if r['estado'] == 'DENTRO')
            st.metric("📋 Registros activos", dentro_ahora)

        st.markdown("---")
        st.markdown("### 🚘 Vehículos dentro ahora")
        dentro = obtener_vehiculos_dentro()
        if not dentro:
            st.info("No hay vehículos dentro en este momento.")
        else:
            df = pd.DataFrame(dentro)
            df = df.rename(columns={
                'placas': 'Placas', 'tipo': 'Tipo', 'nombre_completo': 'Dueño',
                'matricula': 'Matrícula', 'carrera': 'Carrera', 'hora_entrada': 'Entrada'
            })
            st.dataframe(df[['Placas', 'Tipo', 'Dueño', 'Matrícula', 'Carrera', 'Entrada']],
                         use_container_width=True, hide_index=True)

    # =========================================================
    # TAB 2: GESTIÓN DE USUARIOS
    # =========================================================
    with tab_usuarios:
        st.markdown("### 👥 Gestión de Usuarios")

        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "🎓 Crear Alumno", "👷 Crear Trabajador", "👑 Crear Administrador", "📋 Ver Todos"
        ])

        # --- Crear Alumno ---
        with sub_tab1:
            st.markdown("#### Crear nuevo Alumno")
            with st.form("form_admin_crear_alumno", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Datos de acceso**")
                    u = st.text_input("Usuario")
                    p = st.text_input("Contraseña", type="password")
                with col2:
                    st.markdown("**Datos personales**")
                    nombre = st.text_input("Nombre completo")
                    id_est = st.text_input("ID Estudiante")

                col3, col4, col5 = st.columns(3)
                with col3:
                    mat = st.text_input("Matrícula")
                with col4:
                    car = st.text_input("Carrera")
                with col5:
                    gru = st.text_input("Grupo")

                tel = st.text_input("Teléfono")

                if st.form_submit_button("Crear Alumno", use_container_width=True, type="primary"):
                    errores = []
                    if not u or not p or not nombre:
                        errores.append("Usuario, contraseña y nombre son obligatorios")
                    if u and usuario_existe(u.lower().strip()):
                        errores.append("Ese usuario ya existe")

                    if errores:
                        for e in errores: st.error(e)
                    else:
                        try:
                            crear_usuario(
                                usuario=u.lower().strip(), password=p, rol='alumno',
                                tipo_usuario='alumno', nombre_completo=nombre,
                                matricula=mat, carrera=car, grupo=gru,
                                telefono=tel, id_estudiante=id_est
                            )
                            st.success(f"✅ Alumno **{nombre}** (@{u}) creado correctamente.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # --- Crear Trabajador ---
        with sub_tab2:
            st.markdown("#### Crear nuevo Trabajador de Caseta")
            with st.form("form_admin_crear_trab", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    u = st.text_input("Usuario")
                    p = st.text_input("Contraseña", type="password")
                with col2:
                    nombre = st.text_input("Nombre completo")
                    tel = st.text_input("Teléfono")

                if st.form_submit_button("Crear Trabajador", use_container_width=True, type="primary"):
                    errores = []
                    if not u or not p or not nombre:
                        errores.append("Usuario, contraseña y nombre son obligatorios")
                    if u and usuario_existe(u.lower().strip()):
                        errores.append("Ese usuario ya existe")

                    if errores:
                        for e in errores: st.error(e)
                    else:
                        try:
                            crear_usuario(
                                usuario=u.lower().strip(), password=p, rol='trabajador',
                                tipo_usuario='administrativo', nombre_completo=nombre, telefono=tel
                            )
                            st.success(f"✅ Trabajador **{nombre}** (@{u}) creado correctamente.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # --- Crear Administrador ---
        with sub_tab3:
            st.markdown("#### Crear nuevo Administrador")
            st.warning("⚠️ Los administradores tienen acceso total al sistema. Otorga este rol con precaución.")
            with st.form("form_admin_crear_admin", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    u = st.text_input("Usuario")
                    p = st.text_input("Contraseña", type="password")
                with col2:
                    nombre = st.text_input("Nombre completo")
                    tel = st.text_input("Teléfono")

                if st.form_submit_button("Crear Administrador", use_container_width=True, type="primary"):
                    errores = []
                    if not u or not p or not nombre:
                        errores.append("Usuario, contraseña y nombre son obligatorios")
                    if u and usuario_existe(u.lower().strip()):
                        errores.append("Ese usuario ya existe")

                    if errores:
                        for e in errores: st.error(e)
                    else:
                        try:
                            crear_usuario(
                                usuario=u.lower().strip(), password=p, rol='admin',
                                tipo_usuario='administrativo', nombre_completo=nombre, telefono=tel
                            )
                            st.success(f"✅ Administrador **{nombre}** (@{u}) creado correctamente.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # --- Ver Todos ---
        with sub_tab4:
            st.markdown("#### Lista de usuarios registrados")
            filtro = st.selectbox("Filtrar por rol", ["Todos", "alumno", "trabajador", "admin"])
            usuarios = obtener_todos_usuarios(None if filtro == "Todos" else filtro)

            if not usuarios:
                st.info("No hay usuarios que coincidan con el filtro.")
            else:
                st.write(f"**Total: {len(usuarios)} usuario(s)**")

                for u in usuarios:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([4, 2, 1])
                        with col1:
                            icono = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}.get(u['rol'], '👤')
                            st.markdown(f"**{icono} {u['nombre_completo']}** — @{u['usuario']}")
                            st.caption(f"Rol: {u['rol']} | Tipo: {u['tipo_usuario'] or 'N/A'} | Teléfono: {u['telefono'] or 'N/A'}")
                        with col2:
                            if u['rol'] == 'alumno':
                                st.caption(f"Matrícula: {u['matricula'] or 'N/A'}")
                                st.caption(f"Carrera: {u['carrera'] or 'N/A'} | Grupo: {u['grupo'] or 'N/A'}")
                            st.caption(f"Registrado: {u['fecha_registro']}")
                        with col3:
                            # No permitir eliminar al propio admin actual
                            if u['id'] == user['id']:
                                st.caption("_(Tú)_")
                            else:
                                if st.button("🗑️", key=f"del_user_{u['id']}", help="Eliminar usuario"):
                                    ok, msg = eliminar_usuario(u['id'])
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)

    # =========================================================
    # TAB 3: REGISTROS
    # =========================================================
    with tab_registros:
        st.markdown("### 📋 Todos los registros de entrada/salida")
        registros = obtener_todos_los_registros()

        if not registros:
            st.info("Aún no hay registros en el sistema.")
        else:
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                filtro_estado = st.selectbox("Estado", ["Todos", "DENTRO", "FUERA"])
            with col2:
                filtro_tipo = st.selectbox("Tipo", ["Todos", "Auto", "Moto"])
            with col3:
                buscar = st.text_input("🔍 Buscar (nombre, placas, matrícula)").lower().strip()

            filtrados = registros
            if filtro_estado != "Todos":
                filtrados = [r for r in filtrados if r['estado'] == filtro_estado]
            if filtro_tipo != "Todos":
                filtrados = [r for r in filtrados if r['tipo'] == filtro_tipo]
            if buscar:
                filtrados = [r for r in filtrados if
                             buscar in (r['nombre_completo'] or '').lower() or
                             buscar in (r['placas'] or '').lower() or
                             buscar in (r['matricula'] or '').lower()]

            st.write(f"**Mostrando {len(filtrados)} registro(s)**")

            # Exportar CSV
            df_export = pd.DataFrame([{
                'ID': r['id'], 'Estado': r['estado'], 'Alumno': r['nombre_completo'],
                'Matrícula': r['matricula'], 'Carrera': r['carrera'],
                'Tipo': r['tipo'], 'Placas': r['placas'],
                'Entrada': r['hora_entrada'], 'Salida': r['hora_salida'] or 'En curso'
            } for r in filtrados])
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar CSV", data=csv,
                               file_name=f"registros_estacionamiento_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv")

            st.markdown("---")

            # Tabla visual con expander para evidencias
            for r in filtrados:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        icono = "🚗" if r['tipo'] == 'Auto' else "🏍️"
                        estado_icon = "🟢" if r['estado'] == 'DENTRO' else "🔴"
                        st.markdown(f"**{estado_icon} {icono} {r['placas']}**")
                        st.caption(f"Dueño: {r['nombre_completo']}")
                    with col2:
                        st.caption(f"Matrícula: {r['matricula'] or 'N/A'}")
                        st.caption(f"Carrera: {r['carrera'] or 'N/A'}")
                    with col3:
                        st.caption(f"⬇️ Entrada: {r['hora_entrada']}")
                        st.caption(f"⬆️ Salida: {r['hora_salida'] or '—'}")
                    with col4:
                        if r['evidencia_entrada'] or r['evidencia_salida']:
                            if st.button("📸 Ver", key=f"ver_ev_{r['id']}", use_container_width=True):
                                st.session_state[f"mostrar_ev_{r['id']}"] = not st.session_state.get(f"mostrar_ev_{r['id']}", False)

                    if st.session_state.get(f"mostrar_ev_{r['id']}", False):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**📷 Evidencia de Entrada**")
                            if r['evidencia_entrada']:
                                img_bytes = base64_a_bytes(r['evidencia_entrada'])
                                if img_bytes: st.image(img_bytes, use_container_width=True)
                                else: st.caption("Error al cargar imagen")
                            else:
                                st.caption("Sin evidencia")
                        with col_b:
                            st.markdown("**📷 Evidencia de Salida**")
                            if r['evidencia_salida']:
                                img_bytes = base64_a_bytes(r['evidencia_salida'])
                                if img_bytes: st.image(img_bytes, use_container_width=True)
                                else: st.caption("Error al cargar imagen")
                            else:
                                st.caption("Sin evidencia")

    # =========================================================
    # TAB 4: MÉTRICAS
    # =========================================================
    with tab_metricas:
        st.markdown("### 📈 Métricas y patrones de uso")
        registros = obtener_todos_los_registros()

        if not registros:
            st.info("Aún no hay datos suficientes para calcular métricas.")
        else:
            df = pd.DataFrame(registros)
            df['hora_entrada'] = pd.to_datetime(df['hora_entrada'], errors='coerce')
            df['hora_salida'] = pd.to_datetime(df['hora_salida'], errors='coerce')

            # --- Horas pico ---
            st.markdown("#### ⏰ Horas de mayor demanda (entradas)")
            df['hora_del_dia'] = df['hora_entrada'].dt.hour
            horas_pico = df.groupby('hora_del_dia').size().reset_index(name='entradas')
            horas_pico = horas_pico.sort_values('hora_del_dia')
            st.bar_chart(horas_pico.set_index('hora_del_dia')['entradas'])

            # --- Permanencia promedio ---
            st.markdown("#### ⏱️ Tiempo promedio de permanencia")
            completados = df.dropna(subset=['hora_salida']).copy()
            if not completados.empty:
                completados['duracion_min'] = (completados['hora_salida'] - completados['hora_entrada']).dt.total_seconds() / 60
                promedio = completados['duracion_min'].mean()
                st.metric("Promedio general", f"{promedio:.1f} min")
                if not completados.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        autos_prom = completados[completados['tipo'] == 'Auto']['duracion_min'].mean()
                        if pd.notna(autos_prom):
                            st.metric("🚗 Autos", f"{autos_prom:.1f} min")
                    with col2:
                        motos_prom = completados[completados['tipo'] == 'Moto']['duracion_min'].mean()
                        if pd.notna(motos_prom):
                            st.metric("🏍️ Motos", f"{motos_prom:.1f} min")
            else:
                st.info("Aún no hay suficientes registros completados (con salida) para calcular la permanencia.")

            # --- Uso por carrera ---
            st.markdown("#### 🎓 Uso por carrera")
            por_carrera = df[df['carrera'].notna()].groupby('carrera').size().reset_index(name='usos')
            if not por_carrera.empty:
                st.bar_chart(por_carrera.set_index('carrera')['usos'])

            # --- Uso por tipo de vehículo ---
            st.markdown("#### 🚗 Uso por tipo de vehículo")
            por_tipo = df.groupby('tipo').size().reset_index(name='cantidad')
            st.dataframe(por_tipo, use_container_width=True, hide_index=True)


# =========================================================
# ENRUTADOR PRINCIPAL
# =========================================================
if st.session_state.usuario is not None:
    col1, col2 = st.columns([5, 1])
    with col1:
        rol = st.session_state.usuario['rol']
        iconos = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}
        st.markdown(f"**{iconos.get(rol, '👤')} {rol.upper()}** — @{st.session_state.usuario['usuario']}")
    with col2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

if st.session_state.usuario is None:
    pantalla_login()
else:
    rol = st.session_state.usuario['rol']
    if rol == 'alumno':
        panel_alumno()
    elif rol == 'trabajador':
        panel_trabajador()
    elif rol == 'admin':
        panel_admin()
    else:
        st.error(f"Rol desconocido: {rol}")