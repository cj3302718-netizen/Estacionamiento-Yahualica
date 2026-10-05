import streamlit as st
import json
import re
import os
import tempfile
import urllib.request
import threading
import time
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from io import BytesIO
from fpdf import FPDF

from db import (
    autenticar, crear_usuario, usuario_existe, contar_admins,
    obtener_vehiculos_de_usuario, crear_vehiculo, eliminar_vehiculo,
    placas_existen, obtener_espacios, obtener_registro_activo_de_usuario,
    generar_qr_imagen,
    obtener_vehiculo_por_placas, obtener_registro_activo_por_vehiculo,
    registrar_entrada, registrar_salida, obtener_vehiculos_dentro,
    decodificar_qr_de_imagen, imagen_a_base64, base64_a_bytes,
    obtener_todos_usuarios, eliminar_usuario, obtener_todos_los_registros,
    generar_siguiente_id, id_estudiante_existe,
    actualizar_usuario, id_estudiante_existe_otro,
    activar_usuario, desactivar_usuario,
    registrar_log, obtener_logs, obtener_acciones_unicas, contar_logs,
    obtener_historial_usuario, contar_visitas_usuario,
    desbloquear_usuario,
    cambiar_password_usuario,
    actualizar_telefono_usuario,
    limpiar_cache,
    obtener_registros_paginado, contar_registros_filtrados,
    contar_logs_filtrados,
    obtener_historial_vehiculo, buscar_vehiculos_admin,
    contar_usuarios_por_estado,
    enviar_mensaje, obtener_mensajes_para_usuario, contar_mensajes_no_leidos,
    marcar_mensaje_leido, obtener_mensajes_enviados, eliminar_mensaje,
    obtener_vehiculos_alerta,
    crear_tabla_mensajes, crear_indices,
    listar_todas_las_placas,
    # === NUEVAS FUNCIONES v2 ===
    obtener_token_qr, regenerar_token_qr, verificar_token_qr,
    generar_placas_temporales,
    registrar_entrada_manual, registrar_salida_manual,
    obtener_registros_manuales, contar_registros_manuales_pendientes,
    validar_registro_manual, obtener_vehiculos_manuales_dentro,
)

try:
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
    import av
    import cv2
    WEBRTC_DISPONIBLE = True
except ImportError:
    WEBRTC_DISPONIBLE = False

LOGO_COMPLETO_URL = "https://raw.githubusercontent.com/cj3302718-netizen/Estacionamiento-Yahualica/main/logo_completo.png"
LOGO_ESCUDO_URL = "https://raw.githubusercontent.com/cj3302718-netizen/Estacionamiento-Yahualica/main/logo_escudo.png"

st.set_page_config(page_title="CUYPARK", page_icon=LOGO_ESCUDO_URL, layout="centered")

COLOR_VINO = "#7B1B2E"
COLOR_VINO_CLARO = "#D7192D"
COLOR_DORADO = "#C9A961"
COLOR_CREMA = "#F5F0E8"
COLOR_AZUL = "#0066B3"

st.markdown("""
<style>
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes fadeInScale { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
    @keyframes slideInRight { from { opacity: 0; transform: translateX(100px); } to { opacity: 1; transform: translateX(0); } }
    @keyframes pulse { 0%,100% { transform: scale(1); box-shadow: 0 0 30px rgba(201,169,97,.6),0 0 60px rgba(123,27,46,.4);} 50% { transform: scale(1.03); box-shadow: 0 0 40px rgba(201,169,97,.8),0 0 80px rgba(123,27,46,.6);} }
    @keyframes shimmer { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
    @keyframes pulseAlert { 0%,100% { opacity: 1; } 50% { opacity: .65; } }

    .stApp { background: radial-gradient(ellipse at top, #1a0a0f 0%, #0d0407 40%, #050203 100%) !important; }
    header[data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }
    section[data-testid="stSidebar"] { background: #0f0508 !important; }

    .titulo-principal { text-align:center; color:#C9A961; font-size:2rem; font-weight:800; margin-bottom:0; letter-spacing:2px; animation: fadeInUp .8s ease-out; }
    .subtitulo { text-align:center; color:#A89968; font-size:.9rem; margin-top:-8px; margin-bottom:20px; animation: fadeInUp 1s ease-out .2s both; }
    .panel-header { background: linear-gradient(135deg, #7B1B2E 0%, #D7192D 100%); padding:14px 16px; border-radius:12px; color:#FFF; font-weight:700; margin-bottom:16px; font-size:1.05rem; line-height:1.3; box-shadow:0 0 20px rgba(123,27,46,.4); animation: fadeInUp .6s ease-out; }
    .contador-card { background:#1a0a0f; border:2px solid #C9A961; border-radius:16px; padding:14px; text-align:center; box-shadow:0 0 15px rgba(201,169,97,.35); margin-bottom:10px; animation: fadeInScale .6s ease-out; transition: transform .3s, box-shadow .3s; }
    .contador-card:hover { transform: translateY(-4px); box-shadow:0 0 30px rgba(201,169,97,.6); }
    .contador-card h4 { color:#A89968; font-size:.75rem; text-transform:uppercase; letter-spacing:1px; margin:0; }
    .contador-card .numero { font-size:1.6rem; font-weight:800; color:#C9A961; margin-top:4px; }
    .edit-form { background:#0f0508; border:2px dashed #C9A961; border-radius:12px; padding:16px; margin-top:10px; animation: fadeInUp .4s ease-out; }
    .hist-item { background:#1a0a0f; border-left:3px solid #C9A961; border-radius:8px; padding:12px 14px; margin-bottom:8px; animation: fadeInUp .4s ease-out; transition: transform .2s, background .2s; }
    .hist-item:hover { transform: translateX(4px); background:#240e15; }
    .hist-duracion { color:#A89968; font-size:.8rem; }
    .log-row { background:#1a0a0f; border-left:3px solid #C9A961; border-radius:8px; padding:10px 14px; margin-bottom:8px; animation: fadeInUp .4s ease-out; transition: transform .2s, background .2s; }
    .log-row:hover { transform: translateX(4px); background:#240e15; }
    .log-accion { font-weight:700; font-size:.85rem; }
    .log-fecha { color:#A89968; font-size:.75rem; }
    .log-detalle { color:#E8DFD0; font-size:.85rem; margin-top:4px; }
    .ocupacion-label { display:flex; justify-content:space-between; font-size:.88rem; margin-bottom:4px; margin-top:8px; }
    .ocupacion-label b { color:#C9A961; }
    .kpi-card { background: linear-gradient(135deg, #1a0a0f 0%, #2a1015 100%); border:1px solid rgba(201,169,97,.35); border-radius:14px; padding:14px 16px; text-align:center; animation: fadeInUp .6s ease-out; transition: transform .3s, border-color .3s, box-shadow .3s; }
    .kpi-card:hover { transform: translateY(-3px); border-color:#C9A961; box-shadow:0 0 20px rgba(201,169,97,.4); }
    .kpi-card .kpi-label { color:#A89968; font-size:.75rem; text-transform:uppercase; letter-spacing:.8px; }
    .kpi-card .kpi-value { font-size:1.7rem; font-weight:800; color:#F5F0E8; margin-top:2px; }
    .kpi-card .kpi-delta { font-size:.8rem; margin-top:2px; }
    .delta-up { color:#00ff88; } .delta-down { color:#ff6666; } .delta-neutral { color:#A89968; }
    .bienvenida-card { background: linear-gradient(135deg, #1a3a1a 0%, #2a5028 100%); border:2px solid #00ff88; border-radius:16px; padding:18px; text-align:center; margin-bottom:16px; box-shadow:0 0 20px rgba(0,255,136,.3); animation: fadeInScale .6s ease-out; }
    .bienvenida-card h3 { color:#00ff88; margin:0; font-size:1.1rem; }
    .bienvenida-card p { color:#fff; margin:6px 0 0 0; font-size:.95rem; }
    .bienvenida-card .placas { color:#00ff88; font-weight:800; font-size:1.3rem; }
    .val-ok { color:#00ff88; font-size:.8rem; margin-top:-8px; margin-bottom:8px; animation: fadeInUp .3s ease-out; }
    .val-error { color:#ff5555; font-size:.8rem; margin-top:-8px; margin-bottom:8px; animation: fadeInUp .3s ease-out; }
    .logo-medallon { display:inline-block; background: radial-gradient(circle at 30% 30%, #FFF 0%, #F5F0E8 60%, #E8DFD0 100%); border-radius:50%; padding:6px; border:3px solid #C9A961; box-shadow:0 0 30px rgba(201,169,97,.6), 0 0 60px rgba(123,27,46,.4); margin-bottom:16px; animation: pulse 3s ease-in-out infinite; }
    .logo-medallon img { width:130px; height:130px; border-radius:50%; display:block; object-fit:cover; }
    .logo-barra { display:inline-block; background: radial-gradient(circle, #FFF 0%, #F5F0E8 100%); border-radius:50%; padding:2px; border:2px solid #C9A961; box-shadow:0 0 8px rgba(201,169,97,.5); vertical-align:middle; margin-right:8px; transition: transform .3s, box-shadow .3s; }
    .logo-barra:hover { transform: scale(1.1) rotate(5deg); box-shadow:0 0 15px rgba(201,169,97,.8); }
    .logo-barra img { width:40px; height:40px; border-radius:50%; display:block; object-fit:cover; }
    .brand-cudy { display:flex; align-items:center; justify-content:flex-end; gap:10px; padding:6px 0; }
    .brand-cudy .texto { text-align:right; line-height:1.1; }
    .brand-cudy .texto .linea1 { color:#A89968; font-size:.65rem; letter-spacing:2px; text-transform:uppercase; font-weight:600; }
    .brand-cudy .texto .linea2 { color:#C9A961; font-size:.95rem; font-weight:800; letter-spacing:1.5px; }
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #7B1B2E 0%, #C9A961 100%) !important; transition: width .6s ease; }
    .stButton > button { transition: all .25s ease !important; position: relative; overflow: hidden; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow:0 6px 20px rgba(201,169,97,.4) !important; }
    .stButton > button:active { transform: translateY(0); }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #7B1B2E 0%, #D7192D 100%) !important; border:none !important; }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #D7192D 0%, #7B1B2E 100%) !important; }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color:#C9A961 !important; box-shadow:0 0 0 3px rgba(201,169,97,.2), 0 0 15px rgba(201,169,97,.4) !important; }
    div[data-testid="stToast"] { animation: slideInRight .4s ease-out !important; }
    div[data-testid="stDecoration"] { background: linear-gradient(90deg, #7B1B2E 0%, #C9A961 50%, #D7192D 100%) !important; height:3px !important; animation: shimmer 2s linear infinite; background-size:200% 100%; }
    .alert-badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:.72rem; font-weight:700; letter-spacing:.5px; animation: pulseAlert 2s ease-in-out infinite; }
    .alert-badge.critico { background: rgba(215,25,45,.2); color:#ff4444; border:1px solid #ff4444; box-shadow:0 0 10px rgba(215,25,45,.5); }
    .alert-badge.advertencia { background: rgba(255,170,0,.2); color:#ffaa00; border:1px solid #ffaa00; box-shadow:0 0 10px rgba(255,170,0,.4); }
    .alert-badge.ok { background: rgba(0,255,136,.15); color:#00ff88; border:1px solid #00ff88; }
    .alert-card { background: linear-gradient(135deg, #2a0a0f 0%, #1a0505 100%); border:2px solid #ff4444; border-radius:12px; padding:12px 14px; margin-bottom:10px; animation: fadeInScale .5s ease-out; box-shadow:0 0 15px rgba(215,25,45,.3); }

    @media (max-width: 768px) {
        .stButton > button { min-height:48px !important; font-size:.95rem !important; padding:10px 14px !important; border-radius:12px !important; }
        .stTextInput > div > div > input, .stSelectbox > div > div > div { min-height:44px !important; font-size:16px !important; }
        .block-container { padding-left:12px !important; padding-right:12px !important; padding-top:20px !important; }
        h1 { font-size:1.5rem !important; } h2 { font-size:1.3rem !important; } h3 { font-size:1.1rem !important; }
        .logo-medallon img { width:100px; height:100px; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# ESCÁNER QR EN TIEMPO REAL
# ============================================================
ESCANER_MODO = "navegador"

try:
    import streamlit.components.v1 as components
    _QR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_scanner")
    if os.path.isfile(os.path.join(_QR_DIR, "index.html")) and os.path.isfile(os.path.join(_QR_DIR, "jsQR.js")):
        _qr_scanner_comp = components.declare_component("cuypark_qr_scanner", path=_QR_DIR)
    else:
        _qr_scanner_comp = None
except Exception:
    _qr_scanner_comp = None

SEGUNDOS_ESPERA_FOTO = 5

if WEBRTC_DISPONIBLE:
    class QRScannerProcessor(VideoProcessorBase):
        """Lee el QR y, SEGUNDOS_ESPERA_FOTO segundos después, captura la foto de evidencia."""

        def __init__(self):
            self.detector = cv2.QRCodeDetector()
            self._lock = threading.Lock()
            self._frame_count = 0
            self._qr = None
            self._qr_t = None
            self._foto = None

        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            self._frame_count += 1
            h, w = img.shape[:2]

            with self._lock:
                qr, qr_t, foto = self._qr, self._qr_t, self._foto

            if qr is None:
                if self._frame_count % 3 == 0:
                    try:
                        data, _, _ = self.detector.detectAndDecode(img)
                        if data and len(data.strip()) > 3:
                            with self._lock:
                                if self._qr is None:
                                    self._qr = data.strip()
                                    self._qr_t = time.time()
                    except Exception:
                        pass

            elif foto is None:
                restante = SEGUNDOS_ESPERA_FOTO - (time.time() - qr_t)
                if restante <= 0:
                    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ok:
                        with self._lock:
                            self._foto = buf.tobytes()
                else:
                    segs = min(SEGUNDOS_ESPERA_FOTO, math.ceil(restante))
                    cv2.rectangle(img, (8, 8), (w - 8, h - 8), (0, 200, 255), 6)
                    cv2.putText(img, "QR OK - Apunta al vehiculo", (25, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.putText(img, str(segs), (w // 2 - 35, h // 2 + 45),
                                cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 200, 255), 8)

            else:
                cv2.rectangle(img, (8, 8), (w - 8, h - 8), (0, 255, 0), 6)
                cv2.putText(img, "FOTO TOMADA", (25, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3)

            return av.VideoFrame.from_ndarray(img, format="bgr24")

        def estado(self):
            with self._lock:
                qr, qr_t, foto = self._qr, self._qr_t, self._foto
            restante = None
            if qr is not None and qr_t is not None:
                restante = max(0, math.ceil(SEGUNDOS_ESPERA_FOTO - (time.time() - qr_t)))
            return {"qr": qr, "foto": foto, "restante": restante}

        def reiniciar(self):
            with self._lock:
                self._qr = None
                self._qr_t = None
                self._foto = None


@st.fragment(run_every="0.5s")
def _poll_qr_scanner():
    processor = st.session_state.get("qr_processor_ref")
    if processor is None:
        return
    estado = processor.estado()
    if estado["qr"] and estado["foto"]:
        st.session_state["qr_escaneado_actual"] = estado["qr"]
        st.session_state["qr_foto_auto"] = estado["foto"]
        processor.reiniciar()
        try:
            st.rerun(scope="app")
        except TypeError:
            st.rerun()
    elif estado["qr"]:
        st.success(
            f"✅ QR leído. 📸 Apunta la cámara al vehículo: "
            f"la foto se toma sola en **{estado['restante']} s**"
        )


def _mostrar_datos_qr_escaneado(user, qr_raw):
    """Muestra los datos del vehículo detectado y permite registrar entrada/salida."""
    try:
        if isinstance(qr_raw, str) and qr_raw.strip().startswith("{"):
            data = json.loads(qr_raw)
        else:
            data = {"placas": str(qr_raw).strip()}
    except Exception:
        data = {"placas": str(qr_raw).strip()}

    placas = (data.get("placas") or "").upper().strip().replace("-", "").replace(" ", "")

    if not placas:
        st.error("❌ QR inválido. No se pudieron extraer las placas.")
        if st.button("🔄 Volver a escanear", use_container_width=True, key="qr_reset_1"):
            st.session_state["qr_escaneado_actual"] = None
            st.session_state["qr_processor_ref"] = None
            st.session_state["qr_foto_auto"] = None
            st.rerun()
        return

    with st.spinner("🔎 Buscando vehículo..."):
        vehiculo = obtener_vehiculo_por_placas(placas)

    # --- Si NO existe el vehículo ---
    if not vehiculo:
        st.error(f"❌ No existe ningún vehículo registrado con las placas **{placas}**.")
        st.caption("Verifica que el alumno haya registrado su vehículo en la app.")

        with st.expander("🔍 Ver vehículos registrados en el sistema (debug)"):
            placas_db = listar_todas_las_placas()
            if not placas_db:
                st.warning("No hay ningún vehículo registrado todavía.")
            else:
                st.caption(f"**{len(placas_db)} vehículo(s) registrado(s):**")
                for p in placas_db:
                    icono = "🚗" if p['tipo'] == 'Auto' else "🏍️"
                    st.markdown(f"- {icono} **{p['placas']}** — {p['nombre_completo']}")

        if st.button("🔄 Volver a escanear", use_container_width=True, key="qr_reset_2"):
            st.session_state["qr_escaneado_actual"] = None
            st.session_state["qr_processor_ref"] = None
            st.session_state["qr_foto_auto"] = None
            st.rerun()
        return

    # === VALIDACIÓN DEL TOKEN DEL QR ===
    token_qr = data.get("token") if isinstance(data, dict) else None
    if token_qr and not verificar_token_qr(vehiculo['id'], token_qr):
        st.error("❌ **QR INVÁLIDO.** Este código fue regenerado o revocado por el alumno.")
        st.caption("El alumno debe descargar su QR actualizado desde la app.")
        if st.button("🔄 Volver a escanear", use_container_width=True, key="qr_token_invalid"):
            st.session_state["qr_escaneado_actual"] = None
            st.session_state["qr_processor_ref"] = None
            st.session_state["qr_foto_auto"] = None
            st.rerun()
        return

    # --- Datos del alumno encontrado ---
    st.success("✅ **QR detectado correctamente**")
    st.markdown("### 👤 Datos del alumno")
    icono = "🚗" if vehiculo['tipo'] == 'Auto' else "🏍️"

    with st.container(border=True):
        col_icon, col_info = st.columns([1, 4])
        with col_icon:
            st.markdown(
                f"<div style='text-align:center; font-size:3.5rem; padding-top:12px;'>{icono}</div>",
                unsafe_allow_html=True
            )
        with col_info:
            st.markdown(f"### {vehiculo['nombre_completo']}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Matrícula:** {vehiculo['matricula'] or 'N/A'}")
                st.markdown(f"**Carrera:** {vehiculo['carrera'] or 'N/A'}")
            with col_b:
                st.markdown(f"**ID:** {vehiculo['id_estudiante'] or 'N/A'}")
                st.markdown(f"**Grupo:** {vehiculo['grupo'] or 'N/A'}")

            st.markdown(
                f"<div style='margin-top:10px; padding:10px 14px; "
                f"background:linear-gradient(135deg,#7B1B2E,#D7192D); "
                f"border-radius:10px; display:inline-block;'>"
                f"<b style='color:#C9A961; font-size:1.15rem; letter-spacing:1px;'>"
                f"{vehiculo['tipo']} — {vehiculo['placas']}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
            if vehiculo.get('marca') or vehiculo.get('modelo') or vehiculo.get('color'):
                detalles = " | ".join(filter(None, [
                    vehiculo.get('marca'),
                    vehiculo.get('modelo'),
                    vehiculo.get('color')
                ]))
                st.caption(f"Vehículo: {detalles}")

    registro_activo = obtener_registro_activo_por_vehiculo(vehiculo['id'])
    accion = "SALIDA" if registro_activo else "ENTRADA"

    foto_auto = st.session_state.get("qr_foto_auto")
    foto_bytes = foto_auto
    if foto_auto:
        st.markdown(f"### 📸 Foto de evidencia — {accion}")
        st.image(foto_auto, caption="Foto tomada automáticamente", use_container_width=True)
        with st.expander("🔁 Tomar otra foto manualmente"):
            foto_manual = st.camera_input(
                "📸 Nueva foto del vehículo",
                key=f"cam_evidencia_qr_manual_{vehiculo['id']}_{accion}"
            )
        if foto_manual:
            foto_bytes = foto_manual.getvalue()
    else:
        foto_evidencia = st.camera_input(
            "📸 Foto del vehículo (obligatoria)",
            key=f"cam_evidencia_qr_{vehiculo['id']}_{accion}"
        )
        foto_bytes = foto_evidencia.getvalue() if foto_evidencia else None

    st.markdown(f"### ✅ Confirmar {accion}")

    if registro_activo:
        try:
            horas_dentro = (datetime.now() - registro_activo['hora_entrada']).total_seconds() / 3600
        except Exception:
            horas_dentro = 0

        if horas_dentro >= 12:
            st.error(f"🚨 Este vehículo lleva **{horas_dentro:.1f}h** dentro. Verifica antes de registrar salida.")
        elif horas_dentro >= 8:
            st.warning(f"⚠️ Este vehículo lleva **{horas_dentro:.1f}h** dentro.")

        # === FOTO DE ENTRADA PARA COMPARAR ===
        ev_entrada = registro_activo.get('evidencia_entrada')
        if ev_entrada:
            with st.expander("🖼️ Comparar con la foto de ENTRADA (verificar conductor y vehículo)"):
                img_in = base64_a_bytes(ev_entrada)
                if img_in:
                    st.image(img_in,
                             caption=f"Foto tomada al ENTRAR ({registro_activo['hora_entrada']})",
                             use_container_width=True)

        st.info(f"🟢 Está **DENTRO** desde {registro_activo['hora_entrada']}. Se registrará **SALIDA**.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🚪 Registrar SALIDA", type="primary", use_container_width=True, key="btn_salida_qr"):
                if not foto_bytes:
                    st.error("❌ Debes tomar la foto de evidencia.")
                else:
                    with st.spinner("💾 Registrando salida..."):
                        registrar_salida(
                            registro_activo['id'], vehiculo['tipo'], user['id'],
                            imagen_a_base64(foto_bytes)
                        )
                        registrar_log(
                            user['id'], "REGISTRAR_SALIDA",
                            f"Salida de {vehiculo['placas']} ({vehiculo['nombre_completo']}) por QR",
                            "Super_Registros", registro_activo['id']
                        )
                    st.session_state["qr_escaneado_actual"] = None
                    st.session_state["qr_processor_ref"] = None
                    st.session_state["qr_foto_auto"] = None
                    set_flash("success", f"✅ Salida registrada para {vehiculo['placas']}.")
                    st.rerun()
        with col_b:
            if st.button("❌ Cancelar", use_container_width=True, key="btn_cancel_qr_salida"):
                st.session_state["qr_escaneado_actual"] = None
                st.session_state["qr_processor_ref"] = None
                st.session_state["qr_foto_auto"] = None
                st.rerun()
    else:
        st.info("🔵 **NO** está dentro. Se registrará **ENTRADA**.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🚗 Registrar ENTRADA", type="primary", use_container_width=True, key="btn_entrada_qr"):
                if not foto_bytes:
                    st.error("❌ Debes tomar la foto de evidencia.")
                else:
                    with st.spinner("💾 Registrando entrada..."):
                        registrar_entrada(
                            vehiculo['id_usuario'], vehiculo['id'], vehiculo['tipo'],
                            user['id'], imagen_a_base64(foto_bytes)
                        )
                        registrar_log(
                            user['id'], "REGISTRAR_ENTRADA",
                            f"Entrada de {vehiculo['placas']} ({vehiculo['nombre_completo']}) por QR",
                            "Super_Registros"
                        )
                    st.session_state["qr_escaneado_actual"] = None
                    st.session_state["qr_processor_ref"] = None
                    st.session_state["qr_foto_auto"] = None
                    set_flash("success", f"✅ Entrada registrada para {vehiculo['placas']}.")
                    st.rerun()
        with col_b:
            if st.button("❌ Cancelar", use_container_width=True, key="btn_cancel_qr_entrada"):
                st.session_state["qr_escaneado_actual"] = None
                st.session_state["qr_processor_ref"] = None
                st.session_state["qr_foto_auto"] = None
                st.rerun()


@st.cache_resource(ttl=3600, show_spinner=False)
def _ice_metered():
    app_name = st.secrets["metered_app"]
    api_key = st.secrets["metered_api_key"]
    url = f"https://{app_name}.metered.live/api/v1/turn/credentials?apiKey={api_key}"
    with urllib.request.urlopen(url, timeout=8) as r:
        servers = json.loads(r.read().decode("utf-8"))
    if not servers:
        raise ValueError("Metered no devolvió servidores")
    return servers


@st.cache_resource(ttl=3600, show_spinner=False)
def _ice_twilio():
    from twilio.rest import Client
    token = Client(st.secrets["twilio_account_sid"], st.secrets["twilio_auth_token"]).tokens.create()
    return token.ice_servers


def obtener_ice_servers():
    for obtener in (_ice_metered, _ice_twilio):
        try:
            servers = obtener()
            if servers:
                return servers
        except Exception:
            continue
    return [{"urls": ["stun:stun.l.google.com:19302"]}]


def _hay_turn(servers):
    for srv in servers:
        urls = srv.get("urls") or srv.get("url") or []
        if isinstance(urls, str):
            urls = [urls]
        if any(str(u).startswith("turn") for u in urls):
            return True
    return False


def _seccion_escaner_qr(user):
    """Sección de escaneo QR automático en vivo (con fallback manual y entrada sin identificación)."""

    if st.session_state.get("qr_escaneado_actual"):
        _mostrar_datos_qr_escaneado(user, st.session_state["qr_escaneado_actual"])
        return

    st.markdown("### 📷 Escáner automático de QR")
    st.caption("Apunta la cámara al código QR del alumno. La detección es automática. 🔍")

    usar_navegador = (ESCANER_MODO == "navegador" and _qr_scanner_comp is not None)

    if usar_navegador:
        st.caption(
            f"💡 Al leer el QR tienes {SEGUNDOS_ESPERA_FOTO} segundos para apuntar al vehículo; "
            "la foto de evidencia se toma sola."
        )
        resultado = _qr_scanner_comp(segundos=SEGUNDOS_ESPERA_FOTO, key="qr_scanner_nav", default=None)
        if isinstance(resultado, dict) and resultado.get("qr") and resultado.get("foto"):
            foto = base64_a_bytes(resultado["foto"])
            if foto:
                st.session_state["qr_escaneado_actual"] = str(resultado["qr"]).strip()
                st.session_state["qr_foto_auto"] = foto
                st.rerun()

    elif WEBRTC_DISPONIBLE:
        col_status, col_hint = st.columns([1, 3])
        with col_status:
            st.markdown("🟢 **Cámara activa**")
        with col_hint:
            st.caption("💡 Buena iluminación y el QR completo en el recuadro = mejor detección")

        ice_servers = obtener_ice_servers()
        if not _hay_turn(ice_servers):
            st.caption("⚠️ Sin servidor TURN configurado: la cámara puede tardar o no conectar en Streamlit Cloud.")

        try:
            ctx = webrtc_streamer(
                key="qr_scanner_caseta",
                mode=WebRtcMode.SENDRECV,
                video_processor_factory=QRScannerProcessor,
                media_stream_constraints={
                    "video": {
                        "facingMode": "environment",
                        "width": {"ideal": 640},
                        "height": {"ideal": 480},
                        "frameRate": {"ideal": 15},
                    },
                    "audio": False,
                },
                async_processing=True,
                rtc_configuration={"iceServers": ice_servers},
            )

            if ctx.video_processor:
                st.session_state["qr_processor_ref"] = ctx.video_processor

            _poll_qr_scanner()

        except Exception as e:
            st.warning(f"⚠️ No se pudo iniciar la cámara automática: {e}")
            st.info("Usa la entrada manual de placas abajo.")
    else:
        st.warning("⚠️ El escáner automático no está disponible en este entorno.")
        st.caption("Instala `streamlit-webrtc` y `av`, o usa la entrada manual de placas.")

    st.markdown("---")
    tabs = st.tabs(["⌨️ Buscar por datos", "🆘 Entrada sin identificación"])

    # --------- TAB 1: BÚSQUEDA AMPLIADA ---------
    with tabs[0]:
        st.caption("Busca por placas, nombre, matrícula o ID de estudiante. "
                   "Confirma la identidad con credencial escolar u oficial.")
        termino = st.text_input("Buscar vehículo", key="busqueda_amplia_qr",
                                 placeholder="Ej. ABC-1234, Juan Pérez, 20231234, ALU-0001").strip()
        if termino:
            with st.spinner("Buscando..."):
                resultados = buscar_vehiculos_admin(termino, limite=15)
            if not resultados:
                st.warning("Sin coincidencias. Si el vehículo no está registrado, "
                           "usa la pestaña **🆘 Entrada sin identificación**.")
            else:
                st.caption(f"**{len(resultados)}** resultado(s):")
                for r in resultados:
                    icono = "🚗" if r['tipo'] == 'Auto' else "🏍️"
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**{icono} {r['placas']}** — {r['nombre_completo']}")
                            st.caption(f"Matrícula: {r['matricula'] or 'N/A'} · "
                                       f"ID: {r['id_estudiante'] or 'N/A'} · @{r['usuario']}")
                        with c2:
                            if st.button("Seleccionar", key=f"sel_veh_{r['id']}",
                                         use_container_width=True):
                                st.session_state["qr_escaneado_actual"] = json.dumps(
                                    {"placas": r['placas']}
                                )
                                st.rerun()

    # --------- TAB 2: ENTRADA SIN IDENTIFICACIÓN ---------
    with tabs[1]:
        st.warning("⚠️ Usa este formulario solo si la persona **no tiene identificación**. "
                   "Quedará marcado como **pendiente de validación** por el administrador.")
        with st.form("form_entrada_manual", clear_on_submit=False):
            nombre_vis = st.text_input("Nombre (o descripción) de quien ingresa *")
            tipo_id = st.selectbox("Identificación mostrada",
                                    ["Ninguna", "Credencial escolar", "INE", "Licencia",
                                     "Pasaporte", "Otro"])
            motivo = st.text_area("Motivo por el que se autoriza *", height=80,
                                   placeholder="Ej. Padre de familia, entrega de documentos…")
            tipo_v = st.selectbox("Tipo de vehículo", ["Auto", "Moto"])
            tiene_placas = st.checkbox("El vehículo tiene placas visibles")
            placas_man = st.text_input("Placas", key="em_placas").upper().strip() if tiene_placas else ""
            col_a, col_b, col_c = st.columns(3)
            with col_a: marca_man = st.text_input("Marca (opcional)", key="em_marca")
            with col_b: modelo_man = st.text_input("Modelo (opcional)", key="em_modelo")
            with col_c: color_man = st.text_input("Color (opcional)", key="em_color")
            foto_man = st.camera_input("📸 Foto de evidencia (obligatoria)", key="em_foto")

            enviado = st.form_submit_button("🆘 Registrar entrada manual",
                                              type="primary", use_container_width=True)
            if enviado:
                if not nombre_vis.strip() or not motivo.strip():
                    st.error("Completa nombre y motivo.")
                elif not foto_man:
                    st.error("La foto de evidencia es obligatoria.")
                else:
                    with st.spinner("Guardando entrada manual..."):
                        registrar_entrada_manual(
                            nombre=nombre_vis.strip(),
                            tipo_id=tipo_id,
                            motivo=motivo.strip(),
                            placas=placas_man or None,
                            marca=marca_man.strip() or None,
                            modelo=modelo_man.strip() or None,
                            color=color_man.strip() or None,
                            tipo_vehiculo=tipo_v,
                            id_trabajador=user['id'],
                            evidencia_b64=imagen_a_base64(foto_man.getvalue())
                        )
                        registrar_log(user['id'], "ENTRADA_MANUAL",
                                      f"Entrada manual autorizada por @{user['usuario']} — {nombre_vis.strip()}",
                                      "Super_Registros_Manuales")

                        try:
                            admins = obtener_todos_usuarios("admin", solo_activos=True)
                            for adm in admins:
                                enviar_mensaje(
                                    user['id'],
                                    "🚨 Entrada manual sin identificación",
                                    f"El trabajador @{user['usuario']} registró una entrada manual.\n\n"
                                    f"• Persona: {nombre_vis.strip()}\n"
                                    f"• Identificación: {tipo_id}\n"
                                    f"• Motivo: {motivo.strip()}\n"
                                    f"• Vehículo: {tipo_v} {placas_man or '(sin placas)'}\n\n"
                                    f"Valídala desde **Registros Manuales**.",
                                    adm['id'], "alerta"
                                )
                        except Exception:
                            pass

                    limpiar_campos(["em_placas", "em_marca", "em_modelo",
                                    "em_color", "em_foto"])
                    set_flash("success",
                              f"✅ Entrada manual registrada para {nombre_vis.strip()}. "
                              "Se notificó al administrador.")
                    st.rerun()


# ============================================================
# HELPERS: PDF
# ============================================================
def generar_pdf_reporte(df, titulo, subtitulo=""):
    class PDF(FPDF):
        def header(self):
            self.set_fill_color(123, 27, 46)
            self.rect(0, 0, 297, 22, "F")
            self.set_y(6)
            self.set_x(10)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(201, 169, 97)
            self.cell(0, 6, "CUYPARK - Colegio Universitario de Yahualica", ln=1)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(245, 240, 232)
            self.set_x(10)
            self.cell(0, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1)
            self.set_y(26)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(130, 130, 130)
            self.cell(0, 5, f"Página {self.page_no()}", align="C")

    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 10, titulo, ln=1, align="C")

    if subtitulo:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, subtitulo, ln=1, align="C")
    pdf.ln(3)

    page_width = 297 - 20
    cols = list(df.columns)[:9]
    df = df[cols]
    n = len(cols)
    widths = [page_width / n] * n

    pdf.set_fill_color(123, 27, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(10)
    for i, c in enumerate(cols):
        pdf.cell(widths[i], 7, str(c)[:25], border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(40, 40, 40)
    fill = False
    for _, row in df.iterrows():
        if pdf.get_y() > 190:
            pdf.add_page()
            pdf.set_fill_color(123, 27, 46)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(10)
            for i, c in enumerate(cols):
                pdf.cell(widths[i], 7, str(c)[:25], border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(40, 40, 40)

        if fill:
            pdf.set_fill_color(245, 240, 232)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_x(10)
        for i, c in enumerate(cols):
            val = row[c]
            if pd.isna(val):
                val = ""
            pdf.cell(widths[i], 6, str(val)[:30], border=1, align="C", fill=True)
        pdf.ln()
        fill = not fill

    return bytes(pdf.output())


# ============================================================
# HELPERS GENERALES
# ============================================================
def selector_rango_fechas(key_prefix):
    hoy = date.today()
    estado_key = f"{key_prefix}_rango"
    if estado_key not in st.session_state:
        st.session_state[estado_key] = "7d"

    st.caption("**Filtro rápido:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Hoy", key=f"{key_prefix}_btn_hoy", use_container_width=True):
            st.session_state[estado_key] = "hoy"
            st.rerun()
    with col2:
        if st.button("7 días", key=f"{key_prefix}_btn_7d", use_container_width=True):
            st.session_state[estado_key] = "7d"
            st.rerun()
    with col3:
        if st.button("Este mes", key=f"{key_prefix}_btn_mes", use_container_width=True):
            st.session_state[estado_key] = "mes"
            st.rerun()
    with col4:
        if st.button("Todo", key=f"{key_prefix}_btn_todo", use_container_width=True):
            st.session_state[estado_key] = "todo"
            st.rerun()

    opcion = st.session_state[estado_key]
    if opcion == "hoy":
        fecha_desde, fecha_hasta = hoy, hoy
    elif opcion == "7d":
        fecha_desde, fecha_hasta = hoy - timedelta(days=7), hoy
    elif opcion == "mes":
        fecha_desde, fecha_hasta = hoy.replace(day=1), hoy
    else:
        fecha_desde, fecha_hasta = None, None

    if opcion == "hoy":
        st.info(f"📅 Mostrando registros de **hoy** ({hoy.strftime('%d/%m/%Y')})")
    elif opcion == "7d":
        st.info(f"📅 Mostrando registros de los **últimos 7 días** ({fecha_desde.strftime('%d/%m/%Y')} → {fecha_hasta.strftime('%d/%m/%Y')})")
    elif opcion == "mes":
        st.info(f"📅 Mostrando registros de **{hoy.strftime('%B %Y').capitalize()}**")
    else:
        st.info("📅 Mostrando **todos los registros** (sin filtro de fecha)")

    return fecha_desde, fecha_hasta


def mostrar_paginacion_superior(key, por_pagina_options=(10, 20, 50, 100)):
    key_pp = f"{key}_por_pagina"
    if key_pp not in st.session_state:
        st.session_state[key_pp] = 20
    col1, col2 = st.columns([1, 3])
    with col1:
        st.session_state[key_pp] = st.selectbox(
            "Por página", por_pagina_options,
            index=por_pagina_options.index(st.session_state[key_pp]),
            key=f"{key}_pp_sel"
        )
    return st.session_state[key_pp]


def render_paginacion_inferior(key, pagina, total, por_pagina, session_pag_key):
    total_pags = max(1, (total + por_pagina - 1) // por_pagina)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("⬅️ Anterior", key=f"{key}_prev_b", disabled=(pagina <= 1), use_container_width=True):
            st.session_state[session_pag_key] = pagina - 1
            st.rerun()
    with c2:
        st.markdown(
            f"<div style='text-align:center; color:#C9A961; padding-top:6px;'>"
            f"Página {pagina} de {total_pags}</div>",
            unsafe_allow_html=True
        )
    with c3:
        if st.button("Siguiente ➡️", key=f"{key}_next_b", disabled=(pagina >= total_pags), use_container_width=True):
            st.session_state[session_pag_key] = pagina + 1
            st.rerun()


def notificar_entrada_reciente(user):
    registro = obtener_registro_activo_de_usuario(user['id'])
    if not registro:
        return
    clave = f"toast_entrada_{user['id']}_{registro['id']}"
    if st.session_state.get(clave, False):
        return
    try:
        delta = datetime.now() - registro['hora_entrada']
        minutos = int(delta.total_seconds() / 60)
    except Exception:
        minutos = 999
    icono = "🚗" if registro['tipo'] == 'Auto' else "🏍️"
    try:
        if minutos <= 5:
            st.toast(f"🎉 ¡Bienvenido! Tu {registro['tipo'].lower()} {registro['placas']} acaba de entrar", icon="🎉")
        elif minutos <= 60:
            st.toast(f"{icono} Tu vehículo entró hace {minutos} min", icon="ℹ️")
    except AttributeError:
        pass
    st.session_state[clave] = True


def formatear_tiempo_dentro(hora_entrada):
    try:
        delta = datetime.now() - hora_entrada
        minutos = int(delta.total_seconds() / 60)
        if minutos < 1:
            return "hace unos segundos"
        elif minutos < 60:
            return f"hace {minutos} min"
        else:
            horas = minutos // 60
            mins_resto = minutos % 60
            if mins_resto == 0:
                return f"desde hace {horas}h"
            return f"desde hace {horas}h {mins_resto}min"
    except Exception:
        return ""


def calcular_horas_dentro(hora_entrada):
    try:
        delta = datetime.now() - hora_entrada
        return delta.total_seconds() / 3600
    except Exception:
        return 0


def obtener_badge_alerta(horas):
    if horas >= 12:
        return f'<span class="alert-badge critico">🚨 {horas:.1f}h DENTRO</span>'
    elif horas >= 8:
        return f'<span class="alert-badge advertencia">⚠️ {horas:.1f}h DENTRO</span>'
    else:
        return f'<span class="alert-badge ok">✓ {horas:.1f}h</span>'


def validar_nombre(nombre):
    if not nombre or not nombre.strip():
        return False, "El nombre es obligatorio."
    patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-\.']{2,100}$"
    if not re.match(patron, nombre.strip()):
        return False, "Solo letras, espacios, acentos y guiones (2-100 caracteres)."
    return True, ""


def validar_usuario(usuario):
    if not usuario or not usuario.strip():
        return False, "El usuario es obligatorio."
    patron = r"^[a-zA-Z0-9._]{3,30}$"
    if not re.match(patron, usuario.strip()):
        return False, "3-30 caracteres: letras, números, punto o guión bajo (sin espacios)."
    return True, ""


def validar_password(password, minimo=3):
    if not password:
        return False, "La contraseña es obligatoria."
    if len(password) < minimo:
        return False, f"Debe tener al menos {minimo} caracteres."
    return True, ""


def validar_telefono(telefono):
    if not telefono or not telefono.strip():
        return True, ""
    solo_digitos = re.sub(r"\D", "", telefono)
    if len(solo_digitos) != 10:
        return False, "Debe tener exactamente 10 dígitos (ej. 444-123-4567)."
    return True, ""


def validar_matricula(matricula):
    if not matricula or not matricula.strip():
        return True, ""
    patron = r"^[A-Za-z0-9\-]{4,15}$"
    if not re.match(patron, matricula.strip()):
        return False, "4-15 caracteres alfanuméricos."
    return True, ""


def validar_id_estudiante(id_estudiante):
    if not id_estudiante or not id_estudiante.strip():
        return True, ""
    patron = r"^[A-Za-z0-9\-]{4,20}$"
    if not re.match(patron, id_estudiante.strip()):
        return False, "4-20 caracteres alfanuméricos (ej. ALU-0001)."
    return True, ""


def validar_placas(placas):
    if not placas or not placas.strip():
        return False, "Las placas son obligatorias."
    limpio = placas.strip().upper().replace("-", "").replace(" ", "")
    patron = r"^[A-Z]{3}[0-9]{3,4}[A-Z]?$"
    if not re.match(patron, limpio):
        return False, "Formato no válido. Ejemplo: ABC-1234"
    return True, ""


def validar_carrera(carrera):
    if not carrera or not carrera.strip():
        return True, ""
    if len(carrera.strip()) < 2:
        return False, "Mínimo 2 caracteres."
    if len(carrera.strip()) > 100:
        return False, "Máximo 100 caracteres."
    return True, ""


def validar_grupo(grupo):
    if not grupo or not grupo.strip():
        return True, ""
    if len(grupo.strip()) > 20:
        return False, "Máximo 20 caracteres."
    return True, ""


def mostrar_validacion(valor, validador, obligatorio=True):
    if not valor or not valor.strip():
        if obligatorio:
            return False
        return True
    ok, msg = validador(valor)
    if ok:
        st.markdown('<div class="val-ok">✅ Campo válido</div>', unsafe_allow_html=True)
        return True
    else:
        st.markdown(f'<div class="val-error">❌ {msg}</div>', unsafe_allow_html=True)
        return False


def limpiar_campos(keys):
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def grafico_dona_ocupacion(autos_ocupados, autos_libres, motos_ocupados, motos_libres):
    labels = ["🚗 Autos", "🏍️ Motos", "Libres"]
    values = [autos_ocupados, motos_ocupados, autos_libres + motos_libres]
    colors = [COLOR_VINO_CLARO, COLOR_DORADO, "#2a2a2a"]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0d0407", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color=COLOR_CREMA),
        hovertemplate="<b>%{label}</b><br>Cantidad: %{value}<br>%{percent}<extra></extra>"
    )])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_CREMA, size=11),
        margin=dict(l=10, r=10, t=10, b=10), height=280, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10, color=COLOR_CREMA)),
        annotations=[dict(text=f"<b>{autos_ocupados + motos_ocupados}</b><br><span style='font-size:10px'>Ocupados</span>",
                          x=0.5, y=0.5, font=dict(size=18, color=COLOR_DORADO), showarrow=False)]
    )
    return fig


def grafico_barras_horas(df_horas):
    fig = go.Figure(data=[go.Bar(
        x=df_horas["hora_str"], y=df_horas["entradas"],
        marker=dict(color=df_horas["entradas"], colorscale=[[0, COLOR_VINO], [1, COLOR_DORADO]], line=dict(color=COLOR_DORADO, width=1)),
        text=df_horas["entradas"], textposition="outside", textfont=dict(color=COLOR_CREMA, size=10),
        hovertemplate="<b>%{x}</b><br>Entradas: %{y}<extra></extra>"
    )])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_CREMA, size=11),
        xaxis=dict(title="", gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        yaxis=dict(title="", gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        margin=dict(l=10, r=10, t=20, b=10), height=280, showlegend=False
    )
    return fig


def grafico_linea_tendencia(df_dias):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_dias["fecha_str"], y=df_dias["entradas"],
        mode="lines+markers",
        line=dict(color=COLOR_DORADO, width=3, shape="spline"),
        marker=dict(color=COLOR_VINO_CLARO, size=10, line=dict(color=COLOR_DORADO, width=2)),
        fill="tozeroy", fillcolor="rgba(123,27,46,0.25)",
        hovertemplate="<b>%{x}</b><br>Entradas: %{y}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_CREMA, size=11),
        xaxis=dict(gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        yaxis=dict(gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        margin=dict(l=10, r=10, t=20, b=10), height=280, showlegend=False
    )
    return fig


def grafico_barras_carreras(df_carreras):
    fig = go.Figure(data=[go.Bar(
        y=df_carreras["carrera"], x=df_carreras["visitas"], orientation="h",
        marker=dict(color=df_carreras["visitas"], colorscale=[[0, COLOR_VINO], [1, COLOR_DORADO]], line=dict(color=COLOR_DORADO, width=1)),
        text=df_carreras["visitas"], textposition="outside", textfont=dict(color=COLOR_CREMA, size=10),
        hovertemplate="<b>%{y}</b><br>Visitas: %{x}<extra></extra>"
    )])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_CREMA, size=11),
        xaxis=dict(gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        yaxis=dict(gridcolor="rgba(201,169,97,0.1)", tickfont=dict(color=COLOR_CREMA, size=10)),
        margin=dict(l=10, r=10, t=20, b=10), height=280, showlegend=False
    )
    return fig


def generar_pdf_qr(user, vehiculo, qr_bytes):
    class PDF(FPDF):
        def header(self):
            self.set_fill_color(123, 27, 46)
            self.rect(0, 0, 210, 28, "F")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as _f:
                    _f.write(urllib.request.urlopen(LOGO_ESCUDO_URL, timeout=5).read())
                    _logo_path = _f.name
                self.image(_logo_path, x=10, y=4, w=20)
                try: os.unlink(_logo_path)
                except Exception: pass
            except Exception:
                pass
            self.set_y(6)
            self.set_x(35)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(201, 169, 97)
            self.cell(0, 5, "COLEGIO UNIVERSITARIO", ln=1, align="L")
            self.set_x(35)
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 6, "DE YAHUALICA", ln=1, align="L")
            self.set_y(30)

        def footer(self):
            self.set_y(-18)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(130, 130, 130)
            self.cell(0, 5, "CUYPARK - Sistema de Estacionamiento Inteligente", align="C", ln=1)
            self.cell(0, 5, f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", align="C")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_y(35)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 10, "CUYPARK", ln=1, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Boleto Digital de Estacionamiento", ln=1, align="C")
    pdf.ln(4)
    pdf.set_draw_color(201, 169, 97)
    pdf.set_line_width(0.5)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 7, "Datos del Alumno", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for etiqueta, valor in [
        ("Nombre completo:", user.get('nombre_completo') or 'N/A'),
        ("ID Estudiante:", user.get('id_estudiante') or 'N/A'),
        ("Matrícula:", user.get('matricula') or 'N/A'),
        ("Carrera:", user.get('carrera') or 'N/A'),
        ("Grupo:", user.get('grupo') or 'N/A'),
    ]:
        pdf.cell(45, 6, etiqueta, border=0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, str(valor), ln=1)
        pdf.set_font("Helvetica", "", 10)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 7, "Datos del Vehículo", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for etiqueta, valor, es_placas in [
        ("Tipo:", vehiculo.get('tipo') or 'N/A', False),
        ("Placas:", vehiculo.get('placas') or 'N/A', True),
        ("Marca:", vehiculo.get('marca') or 'N/A', False),
        ("Modelo:", vehiculo.get('modelo') or 'N/A', False),
        ("Color:", vehiculo.get('color') or 'N/A', False),
    ]:
        pdf.cell(45, 6, etiqueta, border=0)
        pdf.set_font("Helvetica", "B", 12 if es_placas else 10)
        if es_placas: pdf.set_text_color(123, 27, 46)
        pdf.cell(0, 6, str(valor), ln=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 7, "Código QR de Acceso", ln=1, align="C")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        tmp_path = tmp.name

    qr_size = 90
    qr_x = (210 - qr_size) / 2
    qr_y = pdf.get_y() + 3
    pdf.set_draw_color(201, 169, 97)
    pdf.set_line_width(0.6)
    pdf.rect(qr_x - 3, qr_y - 3, qr_size + 6, qr_size + 6)
    pdf.image(tmp_path, x=qr_x, y=qr_y, w=qr_size, h=qr_size)
    try: os.unlink(tmp_path)
    except Exception: pass
    pdf.set_y(qr_y + qr_size + 8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5,
        "Presenta este código QR en la caseta del estacionamiento tanto al entrar como al salir. "
        "Puedes imprimirlo o mostrarlo desde tu dispositivo móvil.",
        align="C")
    return bytes(pdf.output())


# ============================================================
# SESIÓN / FLASH
# ============================================================
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'qr_generado' not in st.session_state:
    st.session_state.qr_generado = None
if 'flash' not in st.session_state:
    st.session_state.flash = None
if 'qr_escaneado_actual' not in st.session_state:
    st.session_state.qr_escaneado_actual = None
if 'qr_processor_ref' not in st.session_state:
    st.session_state.qr_processor_ref = None
if 'qr_foto_auto' not in st.session_state:
    st.session_state.qr_foto_auto = None

if 'tabla_mensajes_ok' not in st.session_state:
    try:
        crear_tabla_mensajes()
        st.session_state['tabla_mensajes_ok'] = True
    except Exception:
        st.session_state['tabla_mensajes_ok'] = False


def mostrar_flash():
    if st.session_state.flash:
        tipo, texto = st.session_state.flash
        if tipo == "success": st.success(texto)
        elif tipo == "error": st.error(texto)
        elif tipo == "warning": st.warning(texto)
        elif tipo == "info": st.info(texto)
        st.session_state.flash = None


def set_flash(tipo, texto):
    st.session_state.flash = (tipo, texto)


def mostrar_branding_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 24px;">
                <div class="logo-medallon">
                    <img src="{LOGO_ESCUDO_URL}" alt="Colegio Universitario de Yahualica">
                </div>
                <div style="color: #C9A961; font-size: 0.7rem; letter-spacing: 4px; text-transform: uppercase; font-weight: 600; margin-top: 4px;">
                    Colegio Universitario
                </div>
                <div style="color: #C9A961; font-size: 1.6rem; font-weight: 800; letter-spacing: 3px; margin-top: 2px;">
                    DE YAHUALICA
                </div>
                <div style="width: 80px; height: 2px; background: linear-gradient(90deg, transparent, #C9A961, transparent); margin: 12px auto 0 auto;"></div>
            </div>
        """, unsafe_allow_html=True)


def mostrar_marca_cudy():
    return f"""
        <div class="brand-cudy">
            <div class="texto">
                <div class="linea1">Colegio Universitario</div>
                <div class="linea2">DE YAHUALICA</div>
            </div>
            <div class="logo-barra" style="margin-right: 0;">
                <img src="{LOGO_ESCUDO_URL}" alt="CUY">
            </div>
        </div>
    """


def cb_mostrar_confirm(key):
    st.session_state[key] = True


def cb_ocultar_confirm(key):
    st.session_state[key] = False


def cb_eliminar_vehiculo(vid, user_id, tipo, placas):
    ok, msg = eliminar_vehiculo(vid)
    st.session_state[f"confirmar_elim_veh_{vid}"] = False
    if ok:
        registrar_log(user_id, "ELIMINAR_VEHICULO", f"Vehículo {tipo} {placas} eliminado", "Super_Vehiculos", vid)
        st.session_state.flash = ("success", "Vehículo eliminado correctamente.")
    else:
        st.session_state.flash = ("error", msg)


def cb_activar_usuario(uid, admin_id, admin_user, target_user, target_name):
    ok, msg = activar_usuario(uid)
    if ok:
        registrar_log(admin_id, "REACTIVAR_USUARIO",
                      f"Cuenta @{target_user} ({target_name}) reactivada por @{admin_user}",
                      "Super_Usuarios", uid)
        st.session_state.flash = ("success", msg)
    else:
        st.session_state.flash = ("error", msg)


def cb_desactivar_usuario(uid, admin_id, admin_user, target_user, target_name):
    ok, msg = desactivar_usuario(uid)
    st.session_state[f"confirmar_desactivar_{uid}"] = False
    if ok:
        registrar_log(admin_id, "DESACTIVAR_USUARIO",
                      f"Cuenta @{target_user} ({target_name}) desactivada por @{admin_user}",
                      "Super_Usuarios", uid)
        st.session_state.flash = ("success", msg)
    else:
        st.session_state.flash = ("error", msg)


def cb_eliminar_usuario(uid, admin_id, admin_user, target_user, target_name):
    ok, msg = eliminar_usuario(uid)
    st.session_state[f"confirmar_eliminar_{uid}"] = False
    if ok:
        registrar_log(admin_id, "ELIMINAR_USUARIO",
                      f"Cuenta @{target_user} ({target_name}) eliminada permanentemente por @{admin_user}",
                      "Super_Usuarios", uid)
        st.session_state.flash = ("success", msg)
    else:
        st.session_state.flash = ("error", msg)


def cerrar_sesion():
    st.session_state.usuario = None
    st.session_state.qr_generado = None
    st.session_state.flash = None
    st.session_state.qr_escaneado_actual = None
    st.session_state.qr_processor_ref = None
    st.session_state.qr_foto_auto = None
    st.rerun()


def mostrar_mi_cuenta(user):
    with st.expander("🔧 Mi cuenta — Contraseña y contacto"):
        st.markdown("#### 📱 Actualizar mi teléfono")
        st.caption("Solo el teléfono puede ser editado por ti. Otros datos son oficiales.")

        tel_actual = user.get('telefono') or ""
        st.caption(f"Teléfono actual registrado: **{tel_actual if tel_actual else '(sin teléfono)'}**")

        nuevo_tel = st.text_input("Nuevo teléfono (10 dígitos)", value=tel_actual,
                                   key=f"mt_tel_{user['id']}", placeholder="444-123-4567")

        tel_ok = False
        if nuevo_tel and nuevo_tel.strip():
            ok, msg = validar_telefono(nuevo_tel)
            if ok:
                st.markdown('<div class="val-ok">✅ Teléfono válido</div>', unsafe_allow_html=True)
                tel_ok = True
            else:
                st.markdown(f'<div class="val-error">❌ {msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="val-error">❌ El teléfono es obligatorio</div>', unsafe_allow_html=True)

        tel_modificado = (nuevo_tel.strip() != tel_actual.strip()) if nuevo_tel else False
        if not tel_modificado and tel_ok:
            st.caption("💡 No has modificado el teléfono.")

        todos_tel_ok = tel_ok and tel_modificado

        if st.button("💾 Guardar teléfono", use_container_width=True, type="primary",
                     disabled=not todos_tel_ok, key=f"mt_btn_{user['id']}"):
            ok, msg = actualizar_telefono_usuario(user['id'], nuevo_tel.strip())
            if ok:
                registrar_log(user['id'], "ACTUALIZAR_TELEFONO",
                              f"@{user['usuario']} actualizó su teléfono",
                              "Super_Usuarios", user['id'])
                st.session_state.usuario['telefono'] = nuevo_tel.strip()
                limpiar_campos([f"mt_tel_{user['id']}"])
                set_flash("success", f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

        st.markdown("---")
        st.markdown("#### 🔑 Cambiar mi contraseña")
        st.caption("Actualiza tu contraseña personal. Necesitas conocer la actual.")

        p_actual = st.text_input("Contraseña actual", type="password", key=f"cp_act_{user['id']}")
        p_nueva = st.text_input("Nueva contraseña", type="password", key=f"cp_new_{user['id']}")
        p_nueva_ok = False
        if p_nueva:
            if len(p_nueva) < 3:
                st.markdown('<div class="val-error">❌ Mínimo 3 caracteres</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="val-ok">✅ Contraseña válida</div>', unsafe_allow_html=True)
                p_nueva_ok = True

        p_confirm = st.text_input("Confirmar nueva contraseña", type="password", key=f"cp_conf_{user['id']}")
        p_conf_ok = False
        if p_confirm:
            if p_confirm == p_nueva:
                st.markdown('<div class="val-ok">✅ Las contraseñas coinciden</div>', unsafe_allow_html=True)
                p_conf_ok = True
            else:
                st.markdown('<div class="val-error">❌ Las contraseñas no coinciden</div>', unsafe_allow_html=True)

        actual_ok = bool(p_actual)
        todos_pass_ok = actual_ok and p_nueva_ok and p_conf_ok

        if st.button("🔐 Cambiar contraseña", use_container_width=True, type="primary",
                     disabled=not todos_pass_ok, key=f"cp_btn_{user['id']}"):
            ok, msg = cambiar_password_usuario(user['id'], p_actual, p_nueva)
            if ok:
                registrar_log(user['id'], "CAMBIAR_PASSWORD",
                              f"@{user['usuario']} cambió su contraseña",
                              "Super_Usuarios", user['id'])
                limpiar_campos([f"cp_act_{user['id']}", f"cp_new_{user['id']}", f"cp_conf_{user['id']}"])
                set_flash("success", f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"❌ {msg}")


def pantalla_login():
    mostrar_branding_login()
    st.markdown('<p class="titulo-principal">CUYPARK</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo">Sistema de Estacionamiento Inteligente — CUY</p>', unsafe_allow_html=True)
    mostrar_flash()

    with st.spinner("🔐 Verificando sistema..."):
        hay_admin = contar_admins() > 0

    if not hay_admin:
        with st.expander("🚨 Configuración inicial: Crear el primer Administrador", expanded=True):
            st.warning("No existe ningún administrador. Crea uno para poder gestionar el sistema.")
            usuario_admin = st.text_input("Usuario admin", key="pa_u")
            u_ok = mostrar_validacion(usuario_admin, validar_usuario, obligatorio=True)
            pass_admin = st.text_input("Contraseña", type="password", key="pa_p")
            p_ok = mostrar_validacion(pass_admin, validar_password, obligatorio=True)
            nombre_admin = st.text_input("Nombre completo", key="pa_n")
            n_ok = mostrar_validacion(nombre_admin, validar_nombre, obligatorio=True)
            todos_ok = u_ok and p_ok and n_ok
            if st.button("Crear Administrador", use_container_width=True, type="primary",
                         disabled=not todos_ok, key="pa_btn"):
                if usuario_existe(usuario_admin.lower().strip()):
                    st.error("❌ Ese usuario ya existe")
                else:
                    crear_usuario(usuario=usuario_admin.lower().strip(), password=pass_admin,
                                  rol='admin', tipo_usuario='administrativo',
                                  nombre_completo=nombre_admin.strip())
                    limpiar_campos(['pa_u', 'pa_p', 'pa_n'])
                    set_flash("success", "✅ Administrador creado. Ahora inicia sesión.")
                    st.rerun()

    st.markdown("### 🔑 Iniciar Sesión")
    usuario = st.text_input("Usuario", key="login_u")
    password = st.text_input("Contraseña", type="password", key="login_p")

    if st.button("Ingresar al Sistema", use_container_width=True, type="primary", key="login_btn"):
        if not usuario or not password:
            st.error("Completa todos los campos")
        else:
            with st.spinner("🔓 Autenticando..."):
                user, error = autenticar(usuario.lower().strip(), password)
            if user:
                st.session_state.usuario = user
                registrar_log(user['id'], "INICIO_SESION",
                              f"@{user['usuario']} inició sesión", "Super_Usuarios", user['id'])
                st.rerun()
            else:
                if "🔒" in error:
                    st.error(f"{error}")
                    st.info("💡 **¿Olvidaste tu contraseña?** Contacta al administrador.")
                else:
                    st.warning(f"⚠️ {error}")

    st.caption("🔒 Las cuentas son creadas por el administrador.")


@st.fragment(run_every="15s")
def _contadores_alumno():
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)
    col1, col2 = st.columns(2)
    with col1:
        if autos:
            disponibles = autos['capacidad_total'] - autos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🚗 Autos</h4><div class="numero">{disponibles} de {autos["capacidad_total"]}</div></div>', unsafe_allow_html=True)
    with col2:
        if motos:
            disponibles = motos['capacidad_total'] - motos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🏍️ Motos</h4><div class="numero">{disponibles} de {motos["capacidad_total"]}</div></div>', unsafe_allow_html=True)


@st.fragment(run_every="15s")
def _contadores_caseta():
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)
    col1, col2 = st.columns(2)
    with col1:
        if autos: st.metric("🚗 Autos dentro", f"{autos['ocupados']} / {autos['capacidad_total']}")
    with col2:
        if motos: st.metric("🏍️ Motos dentro", f"{motos['ocupados']} / {motos['capacidad_total']}")


@st.fragment(run_every="5m")
def _verificar_alertas_programadas(user):
    try:
        alertas = obtener_vehiculos_alerta(12)
        if alertas:
            clave = f"alerta_programada_{date.today().isoformat()}_{len(alertas)}"
            if not st.session_state.get(clave):
                st.toast(f"🚨 {len(alertas)} vehículo(s) llevan +12h dentro.", icon="🚨")
                st.session_state[clave] = True
    except Exception:
        pass


@st.fragment(run_every="15s")
def _dashboard_datos_vivo():
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

    col_logo, col_titulo = st.columns([1, 6])
    with col_logo:
        st.markdown(f"""
            <div style="background: radial-gradient(circle, #FFFFFF 0%, #F5F0E8 100%); border-radius: 50%; padding: 4px;
                border: 3px solid {COLOR_DORADO}; box-shadow: 0 0 12px rgba(201,169,97,.5);
                width:70px; height:70px; display:flex; align-items:center; justify-content:center;">
                <img src="{LOGO_ESCUDO_URL}" style="width:60px; height:60px; border-radius:50%;" alt="CUY">
            </div>
        """, unsafe_allow_html=True)
    with col_titulo:
        st.markdown(f"""
            <div style="padding-top: 8px;">
                <div style="color:{COLOR_DORADO}; font-size:1.6rem; font-weight:800; letter-spacing:1px;">📊 Panel de Control</div>
                <div style="color:{COLOR_CREMA}; font-size:.85rem; opacity:.7; margin-top:-4px;">Colegio Universitario de Yahualica · Actualizado cada 15s</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if autos:
            libres = autos['capacidad_total'] - autos['ocupados']
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">🚗 Autos dentro</div>
                    <div class="kpi-value">{autos['ocupados']}</div>
                    <div class="kpi-delta delta-neutral">{libres} lugares libres</div>
                </div>
            """, unsafe_allow_html=True)
    with col2:
        if motos:
            libres = motos['capacidad_total'] - motos['ocupados']
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">🏍️ Motos dentro</div>
                    <div class="kpi-value">{motos['ocupados']}</div>
                    <div class="kpi-delta delta-neutral">{libres} lugares libres</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 📊 Ocupación actual")
    if autos and autos['capacidad_total'] > 0:
        pct = (autos['ocupados'] / autos['capacidad_total']) * 100
        st.markdown(f'<div class="ocupacion-label"><span>🚗 Autos</span><b>{autos["ocupados"]}/{autos["capacidad_total"]} ({pct:.1f}%)</b></div>', unsafe_allow_html=True)
        st.progress(min(pct / 100, 1.0))
    if motos and motos['capacidad_total'] > 0:
        pct = (motos['ocupados'] / motos['capacidad_total']) * 100
        st.markdown(f'<div class="ocupacion-label"><span>🏍️ Motos</span><b>{motos["ocupados"]}/{motos["capacidad_total"]} ({pct:.1f}%)</b></div>', unsafe_allow_html=True)
        st.progress(min(pct / 100, 1.0))

    st.markdown("---")
    registros = obtener_todos_los_registros()

    if registros:
        df = pd.DataFrame(registros)
        df['hora_entrada'] = pd.to_datetime(df['hora_entrada'], errors='coerce')
        df['fecha'] = df['hora_entrada'].dt.date

        hoy = date.today()
        ayer = hoy - timedelta(days=1)

        st.markdown("#### 📈 Actividad reciente")
        hoy_count = len(df[df['fecha'] == hoy])
        ayer_count = len(df[df['fecha'] == ayer])

        col1, col2, col3 = st.columns(3)
        with col1:
            delta = hoy_count - ayer_count
            delta_txt = f"{delta:+d} ({((delta/ayer_count)*100):+.0f}%)" if ayer_count > 0 else "Sin datos de ayer"
            st.metric("Entradas hoy", hoy_count, delta_txt)
        with col2:
            st.metric("Entradas ayer", ayer_count)
        with col3:
            st.metric("Usuarios totales", len(obtener_todos_usuarios()))

        st.markdown("---")

        if autos and motos:
            st.markdown("#### 🍩 Distribución de ocupación")
            autos_libres = autos['capacidad_total'] - autos['ocupados']
            motos_libres = motos['capacidad_total'] - motos['ocupados']
            fig_dona = grafico_dona_ocupacion(autos['ocupados'], autos_libres, motos['ocupados'], motos_libres)
            st.plotly_chart(fig_dona, use_container_width=True, config={"displayModeBar": False})

        st.markdown("#### ⏰ Horas de mayor demanda (últimos 7 días)")
        hace_7 = hoy - timedelta(days=6)
        df_7d = df[df['fecha'] >= hace_7].copy()
        if not df_7d.empty:
            df_7d['hora'] = df_7d['hora_entrada'].dt.hour
            horas_pico = df_7d.groupby('hora').size().reset_index(name='entradas')
            todas_horas = pd.DataFrame({'hora': range(6, 22)})
            horas_pico = todas_horas.merge(horas_pico, on='hora', how='left').fillna(0)
            horas_pico['hora_str'] = horas_pico['hora'].apply(lambda h: f"{int(h):02d}:00")
            fig_horas = grafico_barras_horas(horas_pico)
            st.plotly_chart(fig_horas, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Sin datos suficientes en los últimos 7 días.")

        st.markdown("#### 📅 Tendencia últimos 30 días")
        hace_30 = hoy - timedelta(days=29)
        df_30d = df[df['fecha'] >= hace_30].copy()
        if not df_30d.empty:
            entradas_dia = df_30d.groupby('fecha').size().reset_index(name='entradas')
            todas_fechas_30 = pd.DataFrame({'fecha': pd.date_range(hace_30, hoy).date})
            entradas_dia = todas_fechas_30.merge(entradas_dia, on='fecha', how='left').fillna(0)
            entradas_dia['fecha_str'] = pd.to_datetime(entradas_dia['fecha']).dt.strftime('%d/%m')
            fig_tendencia = grafico_linea_tendencia(entradas_dia)
            st.plotly_chart(fig_tendencia, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Sin datos en los últimos 30 días.")

        st.markdown("#### 🎓 Top 5 carreras con más uso")
        por_carrera = df[df['carrera'].notna()].groupby('carrera').size().reset_index(name='visitas')
        por_carrera = por_carrera.sort_values('visitas', ascending=True).tail(5)
        if not por_carrera.empty:
            fig_carreras = grafico_barras_carreras(por_carrera)
            st.plotly_chart(fig_carreras, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Sin datos de carreras aún.")
    else:
        st.info("Aún no hay registros para mostrar estadísticas.")

    st.markdown("---")
    st.markdown("### 🚘 Vehículos dentro ahora")
    dentro_list = obtener_vehiculos_dentro()
    if not dentro_list:
        st.info("No hay vehículos dentro.")
    else:
        criticos = [v for v in dentro_list if calcular_horas_dentro(v['hora_entrada']) >= 12]
        advertencias = [v for v in dentro_list if 8 <= calcular_horas_dentro(v['hora_entrada']) < 12]

        if criticos:
            st.markdown(f"""
                <div class="alert-card">
                    <div style="color:#ff4444; font-weight:800; font-size:1rem;">
                        🚨 {len(criticos)} vehículo(s) con MÁS DE 12 HORAS dentro
                    </div>
                    <div style="color:#E8DFD0; font-size:.85rem; margin-top:6px;">
                        Estos vehículos podrían estar abandonados o tener una incidencia.
                    </div>
                </div>
            """, unsafe_allow_html=True)

        if advertencias:
            with st.expander(f"⚠️ {len(advertencias)} vehículo(s) con 8-12 horas dentro"):
                for v in advertencias:
                    horas = calcular_horas_dentro(v['hora_entrada'])
                    icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
                    with st.container(border=True):
                        col_a, col_b = st.columns([3, 2])
                        with col_a:
                            st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
                            st.caption(f"Entrada: {v['hora_entrada']}")
                        with col_b:
                            st.markdown(obtener_badge_alerta(horas), unsafe_allow_html=True)

        st.markdown(f"#### Todos los vehículos dentro ({len(dentro_list)})")
        for v in dentro_list:
            horas = calcular_horas_dentro(v['hora_entrada'])
            icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
            with st.container(border=True):
                col_a, col_b = st.columns([3, 2])
                with col_a:
                    st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
                    st.caption(f"Matrícula: {v['matricula'] or 'N/A'} | Entrada: {v['hora_entrada']}")
                with col_b:
                    st.markdown(obtener_badge_alerta(horas), unsafe_allow_html=True)


def _render_lista_vehiculos_dentro(user):
    # ==== VEHÍCULOS CON ENTRADA MANUAL (SIN IDENTIFICACIÓN) ====
    manuales = obtener_vehiculos_manuales_dentro()
    if manuales:
        st.markdown(f"#### 🆘 Vehículos con entrada manual ({len(manuales)})")
        for m in manuales:
            with st.container(border=True):
                icono = "🚗" if m['tipo_vehiculo'] == 'Auto' else "🏍️"
                st.markdown(f"**{icono} {m['placas'] or '(sin placas)'}** — "
                            f"{m['nombre_visitante']}")
                st.caption(f"Entrada: {m['hora_entrada']} · Autorizó: "
                           f"{m['trabajador_nombre']}")
                st.caption(f"{m['marca'] or '—'} {m['modelo'] or ''} "
                           f"{m['color'] or ''}".strip())

                if m['evidencia_entrada']:
                    with st.expander("📸 Ver foto de entrada"):
                        img = base64_a_bytes(m['evidencia_entrada'])
                        if img:
                            st.image(img, use_container_width=True)

                if st.button("🚪 Registrar salida manual",
                             key=f"sal_manual_{m['id_registro']}",
                             use_container_width=True):
                    st.session_state[f"sal_manual_activo_{m['id_registro']}"] = True
                    st.rerun()

            if st.session_state.get(f"sal_manual_activo_{m['id_registro']}", False):
                foto_sal = st.camera_input(
                    f"📸 Evidencia de salida — {m['placas'] or m['nombre_visitante']}",
                    key=f"cam_sal_man_{m['id_registro']}"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key=f"conf_sal_man_{m['id_registro']}",
                                 type="primary", use_container_width=True):
                        if not foto_sal:
                            st.error("Toma la foto de evidencia.")
                        else:
                            with st.spinner("Guardando salida..."):
                                registrar_salida_manual(
                                    m['id_registro'], user['id'],
                                    imagen_a_base64(foto_sal.getvalue())
                                )
                                registrar_log(user['id'], "SALIDA_MANUAL",
                                              f"Salida manual de {m['nombre_visitante']}",
                                              "Super_Registros_Manuales", m['id_registro'])
                            st.session_state[f"sal_manual_activo_{m['id_registro']}"] = False
                            set_flash("success", "✅ Salida manual registrada.")
                            st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key=f"canc_sal_man_{m['id_registro']}",
                                 use_container_width=True):
                        st.session_state[f"sal_manual_activo_{m['id_registro']}"] = False
                        st.rerun()

        st.markdown("---")

    # ==== BÚSQUEDA DE VEHÍCULOS REGISTRADOS ====
    buscar = st.text_input("🔍 Buscar vehículo (placas, nombre o matrícula)",
                           key="buscar_dentro_caseta",
                           placeholder="Ej. ABC-1234 o Juan Pérez")
    dentro = obtener_vehiculos_dentro()
    if not dentro:
        st.info("No hay vehículos dentro.")
        return

    if buscar and buscar.strip():
        t = buscar.strip().lower()
        dentro_filtrado = [v for v in dentro if
                           t in (v['placas'] or '').lower() or
                           t in (v['nombre_completo'] or '').lower() or
                           t in (v['matricula'] or '').lower()]
        if len(dentro_filtrado) < len(dentro):
            st.caption(f"🔎 **{len(dentro_filtrado)}** de **{len(dentro)}** para '{buscar}'")
        dentro = dentro_filtrado
    else:
        criticos = sum(1 for v in dentro if calcular_horas_dentro(v['hora_entrada']) >= 12)
        advertencias = sum(1 for v in dentro if 8 <= calcular_horas_dentro(v['hora_entrada']) < 12)
        if criticos or advertencias:
            c1, c2 = st.columns(2)
            with c1:
                if criticos: st.markdown(f'<div class="alert-badge critico">🚨 {criticos} con +12h dentro</div>', unsafe_allow_html=True)
            with c2:
                if advertencias: st.markdown(f'<div class="alert-badge advertencia">⚠️ {advertencias} con +8h dentro</div>', unsafe_allow_html=True)
        st.write(f"**Total: {len(dentro)}**")

    if not dentro:
        st.info("No hay vehículos que coincidan con la búsqueda.")
        return

    for v in dentro:
        horas = calcular_horas_dentro(v['hora_entrada'])
        with st.container(border=True):
            icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
            col_info, col_badge = st.columns([3, 2])
            with col_info:
                st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
                st.caption(f"Matrícula: {v['matricula'] or 'N/A'}")
                st.caption(f"Entrada: {v['hora_entrada']}")
            with col_badge:
                st.markdown(obtener_badge_alerta(horas), unsafe_allow_html=True)

            if horas >= 12:
                st.warning(f"⚠️ **Atención:** Este vehículo lleva **{horas:.1f} horas** estacionado.")

            if st.button("🚪 Registrar Salida", key=f"sal_{v['id_registro']}", use_container_width=True):
                st.session_state[f"salida_rapida_{v['id_registro']}"] = True
                st.rerun()

        if st.session_state.get(f"salida_rapida_{v['id_registro']}", False):
            st.markdown("#### 📸 Evidencia de salida")
            foto_sal = st.camera_input(f"Evidencia — {v['placas']}", key=f"cam_sal_{v['id_registro']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar", key=f"conf_sal_{v['id_registro']}", type="primary", use_container_width=True):
                    if not foto_sal:
                        st.error("Toma la foto de evidencia.")
                    else:
                        with st.spinner("💾 Guardando salida..."):
                            registrar_salida(v['id_registro'], v['tipo'], user['id'],
                                             imagen_a_base64(foto_sal.getvalue()))
                            registrar_log(user['id'], "REGISTRAR_SALIDA",
                                          f"Salida de {v['placas']} ({v['nombre_completo']})",
                                          "Super_Registros", v['id_registro'])
                        st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                        set_flash("success", f"✅ Salida registrada para {v['placas']}.")
                        st.rerun()
            with c2:
                if st.button("❌ Cancelar", key=f"canc_sal_{v['id_registro']}", use_container_width=True):
                    st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                    st.rerun()


@st.fragment(run_every="10s")
def _render_dentro_auto(user):
    _render_lista_vehiculos_dentro(user)


@st.fragment
def _render_dentro_manual(user):
    _render_lista_vehiculos_dentro(user)


# ============================================================
# PANEL ALUMNO
# ============================================================
def panel_alumno():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">🎓 Alumno — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()
    notificar_entrada_reciente(user)

    no_leidos = contar_mensajes_no_leidos(user['id'])
    if no_leidos > 0:
        st.info(f"💬 Tienes **{no_leidos}** mensaje(s) sin leer. Revisa la sección Mensajes abajo.")

    with st.expander("👤 Ver mi perfil"):
        st.write(f"**Usuario:** {user['usuario']}")
        st.write(f"**ID Estudiante:** {user['id_estudiante'] or 'N/A'}")
        st.write(f"**Matrícula:** {user['matricula'] or 'N/A'}")
        st.write(f"**Carrera:** {user['carrera'] or 'N/A'}")
        st.write(f"**Grupo:** {user['grupo'] or 'N/A'}")
        st.write(f"**Teléfono:** {user['telefono'] or 'N/A'}")

    mostrar_mi_cuenta(user)

    titulo_msj = f"💬 Mensajes ({no_leidos} sin leer)" if no_leidos > 0 else "💬 Mensajes"
    with st.expander(titulo_msj):
        mensajes = obtener_mensajes_para_usuario(user['id'])
        if not mensajes:
            st.info("No tienes mensajes.")
        else:
            for m in mensajes:
                icono_leido = "📬" if not m['leido'] else "📭"
                tipo_icon = {"mensaje": "💬", "alerta": "🚨", "aviso": "📢"}.get(m['tipo'], "💬")
                with st.container(border=True):
                    st.markdown(f"**{icono_leido} {tipo_icon} {m['asunto']}**")
                    st.caption(f"De: {m['remitente_nombre']} ({m['remitente_rol']}) · {m['fecha'].strftime('%d/%m/%Y %H:%M')}")
                    if m.get('es_broadcast'):
                        st.caption("📢 Mensaje general")
                    with st.expander("Ver mensaje"):
                        st.write(m['cuerpo'])
                        if not m['leido']:
                            if st.button("✅ Marcar como leído", key=f"al_leido_{m['id']}", use_container_width=True):
                                marcar_mensaje_leido(m['id'])
                                st.rerun()

    st.markdown("Lugares disponibles")
    st.caption("🟢 Actualizándose en tiempo real (cada 15s)")
    _contadores_alumno()
    st.markdown("---")

    registro_activo = obtener_registro_activo_de_usuario(user['id'])
    if registro_activo:
        try:
            delta = datetime.now() - registro_activo['hora_entrada']
            minutos = int(delta.total_seconds() / 60)
        except Exception:
            minutos = 999
        if minutos <= 5:
            st.markdown(f"""
                <div class="bienvenida-card">
                    <h3>🎉 ¡Bienvenido al estacionamiento!</h3>
                    <p>Tu <b>{registro_activo['tipo'].lower()}</b> acaba de entrar:</p>
                    <p class="placas">{registro_activo['placas']}</p>
                    <p style="font-size:.8rem; opacity:.8; margin-top:8px;">
                        Entrada registrada a las {registro_activo['hora_entrada'].strftime('%H:%M')}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        else:
            tiempo_txt = formatear_tiempo_dentro(registro_activo['hora_entrada'])
            st.success(f"✅ Vehículo **DENTRO**: {registro_activo['placas']} ({registro_activo['tipo']}) — {tiempo_txt}")
            st.caption(f"Entrada: {registro_activo['hora_entrada'].strftime('%d/%m/%Y %H:%M')}")

    st.markdown("### 🚘 Mis vehículos")
    vehiculos = obtener_vehiculos_de_usuario(user['id'])

    if not vehiculos:
        st.info("Aún no tienes vehículos registrados. Agrega uno abajo. 👇")
    else:
        for v in vehiculos:
            with st.container(border=True):
                icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
                st.markdown(f"**{icono} {v['tipo']} — {v['placas']}**")
                st.caption(f"Marca: {v['marca'] or 'N/A'} | Modelo: {v['modelo'] or 'N/A'} | Color: {v['color'] or 'N/A'}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🎫 QR", key=f"qr_{v['id']}", use_container_width=True):
                        with st.spinner("🎫 Generando QR..."):
                            token = obtener_token_qr(user['id'])
                            if not token:
                                token = regenerar_token_qr(user['id'])
                            qr_data = {
                                "id_usuario": user['id'], "usuario": user['usuario'],
                                "nombre": user['nombre_completo'], "id_estudiante": user['id_estudiante'],
                                "matricula": user['matricula'], "carrera": user['carrera'],
                                "grupo": user['grupo'], "id_vehiculo": v['id'],
                                "tipo": v['tipo'], "placas": v['placas'],
                                "token": token,
                            }
                            st.session_state.qr_generado = {
                                "imagen": generar_qr_imagen(qr_data),
                                "vehiculo": v, "datos": qr_data
                            }
                        st.rerun()
                with col2:
                    st.button("🗑️ Borrar", key=f"del_{v['id']}", use_container_width=True,
                              on_click=cb_mostrar_confirm, args=(f"confirmar_elim_veh_{v['id']}",))

                if st.session_state.get(f"confirmar_elim_veh_{v['id']}", False):
                    with st.container(border=True):
                        st.error(f"🚨 ¿Eliminar el vehículo **{v['tipo']} {v['placas']}**?")
                        st.caption("Esta acción es permanente y no se puede deshacer.")
                        cs, cn = st.columns(2)
                        with cs:
                            st.button("✅ Sí, eliminar", key=f"si_del_veh_{v['id']}", type="primary",
                                      use_container_width=True,
                                      on_click=cb_eliminar_vehiculo,
                                      args=(v['id'], user['id'], v['tipo'], v['placas']))
                        with cn:
                            st.button("❌ Cancelar", key=f"no_del_veh_{v['id']}", use_container_width=True,
                                      on_click=cb_ocultar_confirm, args=(f"confirmar_elim_veh_{v['id']}",))

    with st.expander("📜 Mi historial de visitas"):
        total_visitas, visitas_mes = contar_visitas_usuario(user['id'])
        historial = obtener_historial_usuario(user['id'], limite=100)

        completadas = [h for h in historial if h['hora_salida']]
        prom_str = "N/A"
        if completadas:
            tiempos = [(h['hora_salida'] - h['hora_entrada']).total_seconds() / 60 for h in completadas]
            prom = sum(tiempos) / len(tiempos)
            prom_str = f"{prom:.0f} min" if prom < 60 else f"{prom/60:.1f} hrs"

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("🚗 Visitas totales", total_visitas)
        with col2: st.metric("📅 Este mes", visitas_mes)
        with col3: st.metric("⏱️ Promedio", prom_str)

        st.markdown("---")
        filtro = st.radio("Filtrar:", ["Todas", "Dentro", "Fuera"], horizontal=True,
                          label_visibility="collapsed", key="filtro_historial")

        if filtro == "Dentro":
            historial_filtrado = [h for h in historial if h['estado'] == 'DENTRO']
        elif filtro == "Fuera":
            historial_filtrado = [h for h in historial if h['estado'] == 'FUERA']
        else:
            historial_filtrado = historial

        if not historial_filtrado:
            st.info("No hay visitas que coincidan con el filtro.")
        else:
            key_lazy = "hist_lazy_count"
            if key_lazy not in st.session_state:
                st.session_state[key_lazy] = 10
            visibles = historial_filtrado[:st.session_state[key_lazy]]
            st.caption(f"Mostrando **{len(visibles)}** de **{len(historial_filtrado)}** visita(s)")

            for h in visibles:
                fecha_entrada = h['hora_entrada'].strftime("%d/%m/%Y %H:%M") if h['hora_entrada'] else "N/A"
                fecha_salida = h['hora_salida'].strftime("%d/%m/%Y %H:%M") if h['hora_salida'] else None
                icono = "🚗" if h['tipo'] == 'Auto' else "🏍️"
                estado_color = "#00ff88" if h['estado'] == 'DENTRO' else "#A89968"
                estado_txt = "🟢 DENTRO" if h['estado'] == 'DENTRO' else "🔴 COMPLETADA"

                if fecha_salida:
                    dur = h['hora_salida'] - h['hora_entrada']
                    mins = int(dur.total_seconds() / 60)
                    duracion_txt = f"{mins} min" if mins < 60 else f"{mins // 60}h {mins % 60}min"
                else:
                    delta = datetime.now() - h['hora_entrada']
                    mins = int(delta.total_seconds() / 60)
                    duracion_txt = f"{mins} min (en curso)" if mins < 60 else f"{mins // 60}h {mins % 60}min (en curso)"

                st.markdown(f"""
                    <div class="hist-item" style="border-left-color: {estado_color};">
                        <div style="display:flex; justify-content:space-between; flex-wrap:wrap;">
                            <span style="color:{estado_color}; font-weight:700; font-size:.85rem;">{estado_txt}</span>
                            <span class="hist-duracion">⏱️ {duracion_txt}</span>
                        </div>
                        <div style="color:#fff; margin-top:4px; font-size:.9rem;">
                            {icono} <b>{h['placas']}</b>
                            {f" · {h['marca']}" if h['marca'] else ""}
                            {f" · {h['modelo']}" if h['modelo'] else ""}
                        </div>
                        <div style="color:#aaa; font-size:.8rem; margin-top:2px;">⬇️ Entrada: {fecha_entrada}</div>
                        {f'<div style="color:#aaa; font-size:.8rem;">⬆️ Salida: {fecha_salida}</div>' if fecha_salida else ''}
                    </div>
                """, unsafe_allow_html=True)

            if st.session_state[key_lazy] < len(historial_filtrado):
                if st.button("⬇️ Ver más", use_container_width=True, key="hist_ver_mas"):
                    st.session_state[key_lazy] += 10
                    st.rerun()

    with st.expander("➕ Registrar nuevo vehículo"):
        st.markdown("**Tipo de vehículo**")
        tipo = st.selectbox("Tipo", ["Auto", "Moto"], key="vh_tipo",
                            label_visibility="collapsed")

        sin_placas = st.checkbox("El vehículo aún no tiene placas (en trámite)",
                                 key="vh_sin_placas")

        if sin_placas:
            st.info("Se generará un identificador interno **TEMP-XXXX**. "
                    "Podrás actualizar las placas después.")
            identificador = st.text_input(
                "Últimos dígitos del número de serie / VIN (opcional)",
                key="vh_vin"
            )
            placas = generar_placas_temporales()
            placas_ok = True
            placas_unicas = True
        else:
            placas = st.text_input("Placas", key="vh_placas",
                                    placeholder="Ej. ABC-1234").upper().strip()
            placas_ok = mostrar_validacion(placas, validar_placas, obligatorio=True)
            placas_unicas = True
            if placas and placas_ok and placas_existen(placas.replace("-", "").replace(" ", "")):
                st.markdown('<div class="val-error">❌ Ya existe un vehículo con esas placas</div>',
                            unsafe_allow_html=True)
                placas_unicas = False
            identificador = None

        marca = st.text_input("Marca (opcional)", key="vh_marca")
        modelo = st.text_input("Modelo (opcional)", key="vh_modelo")
        color = st.text_input("Color (opcional)", key="vh_color")

        todos_ok = placas_ok and placas_unicas
        if st.button("Registrar vehículo", use_container_width=True, type="primary",
                     disabled=not todos_ok, key="vh_btn"):
            placas_limpias = placas.replace("-", "").replace(" ", "").upper()
            try:
                with st.spinner("Registrando vehículo..."):
                    crear_vehiculo(
                        user['id'], tipo, placas_limpias,
                        marca.strip() if marca else None,
                        modelo.strip() if modelo else None,
                        color.strip() if color else None,
                        es_tramite=1 if sin_placas else 0,
                        identificador_alterno=(identificador.strip()
                                               if sin_placas and identificador else None)
                    )
                    registrar_log(user['id'], "CREAR_VEHICULO",
                                  f"Vehículo {tipo} {placas_limpias} registrado"
                                  + (" (en trámite)" if sin_placas else ""),
                                  "Super_Vehiculos")
                limpiar_campos(['vh_placas', 'vh_marca', 'vh_modelo', 'vh_color',
                                'vh_vin', 'vh_sin_placas'])
                set_flash("success", f"✅ Vehículo {placas_limpias} registrado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")

    if st.session_state.qr_generado:
        qr_info = st.session_state.qr_generado
        st.markdown("---")
        st.markdown("### 🎫 Tu código QR")
        st.info("Presenta este código en la caseta. Si pierdes el celular, "
                "usa **Regenerar** para invalidar el anterior.")

        _, col_qr, _ = st.columns([1, 2, 1])
        with col_qr:
            st.image(qr_info['imagen'],
                     caption=f"QR — {qr_info['vehiculo']['tipo']} {qr_info['vehiculo']['placas']}")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("📥 Descargar PNG", data=qr_info['imagen'],
                file_name=f"QR_{qr_info['vehiculo']['placas']}.png", mime="image/png",
                use_container_width=True)
        with col_dl2:
            try:
                with st.spinner("📄 Generando PDF profesional..."):
                    pdf_bytes = generar_pdf_qr(user, qr_info['vehiculo'], qr_info['imagen'])
                st.download_button("📄 Descargar PDF", data=pdf_bytes,
                    file_name=f"CUYPARK_{qr_info['vehiculo']['placas']}_{user['matricula'] or 'alumno'}.pdf",
                    mime="application/pdf", use_container_width=True, type="primary")
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔁 Regenerar QR (invalidar anterior)",
                         use_container_width=True, key="btn_regen_qr"):
                with st.spinner("Regenerando..."):
                    regenerar_token_qr(user['id'])
                    registrar_log(user['id'], "REGENERAR_QR",
                                  f"@{user['usuario']} regeneró su token QR",
                                  "Super_Usuarios", user['id'])
                st.session_state.qr_generado = None
                set_flash("success", "✅ Token renovado. El QR anterior ya no funciona.")
                st.rerun()
        with col_r2:
            if st.button("❌ Cerrar QR", use_container_width=True, key="btn_cerrar_qr"):
                st.session_state.qr_generado = None
                st.rerun()


# ============================================================
# PANEL TRABAJADOR
# ============================================================
def panel_trabajador():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👷 Caseta — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()
    mostrar_mi_cuenta(user)

    _contadores_caseta()
    st.caption("🟢 Contadores actualizándose cada 15s")
    st.markdown("---")

    seccion = st.radio("Sección:", ["📷 Escanear QR", "📋 Vehículos Dentro"],
                       horizontal=True, label_visibility="collapsed")

    if seccion == "📷 Escanear QR":
        _seccion_escaner_qr(user)
    else:
        st.markdown("### 🚘 Vehículos dentro")
        auto_refresh = st.toggle("🔄 Auto-actualizar cada 10 segundos", value=False,
            key="auto_refresh_caseta",
            help="La lista se actualizará sola para mostrar nuevos vehículos que entren.")
        salida_en_curso = any(k.startswith("salida_rapida_") and v for k, v in st.session_state.items())

        if auto_refresh and not salida_en_curso:
            st.caption("🟢 Actualizando automáticamente cada 10 segundos")
            _render_dentro_auto(user)
        elif auto_refresh and salida_en_curso:
            st.caption("⏸️ Auto-actualización pausada mientras registras una salida")
            _render_dentro_manual(user)
        else:
            if st.button("🔄 Refrescar ahora", use_container_width=True):
                st.rerun()
            _render_dentro_manual(user)


# ============================================================
# PANEL ADMIN
# ============================================================
def panel_admin():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👑 Admin — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()
    _verificar_alertas_programadas(user)

    seccion = st.radio(
        "Sección:",
        ["📊 Dashboard", "👥 Usuarios", "📋 Registros", "📈 Métricas",
         "🔍 Auditoría", "💬 Mensajes", "🚗 Vehículos",
         "🆘 Registros Manuales", "🔧 Mi Cuenta"],
        horizontal=True, label_visibility="collapsed"
    )

    if seccion == "📊 Dashboard":
        _dashboard_datos_vivo()

    elif seccion == "👥 Usuarios":
        st.markdown("### 👥 Gestión de Usuarios")
        sub = st.radio("Acción:", ["🎓 Crear Alumno", "👷 Crear Trabajador", "👑 Crear Admin", "📋 Ver Todos"],
                       horizontal=True, label_visibility="collapsed")

        if sub == "🎓 Crear Alumno":
            id_sugerido = generar_siguiente_id("ALU")
            st.info(f"💡 El ID sugerido es **{id_sugerido}**.")
            u = st.text_input("Usuario", key="ca_u", placeholder="mín. 3 caracteres, sin espacios")
            u_ok = mostrar_validacion(u, validar_usuario)
            p = st.text_input("Contraseña", type="password", key="ca_p")
            p_ok = mostrar_validacion(p, validar_password)
            nombre = st.text_input("Nombre completo", key="ca_n")
            n_ok = mostrar_validacion(nombre, validar_nombre)
            id_est = st.text_input("ID Estudiante", value=id_sugerido, key="ca_id")
            id_ok = mostrar_validacion(id_est, validar_id_estudiante)
            ca, cb = st.columns(2)
            with ca:
                mat = st.text_input("Matrícula (opcional)", key="ca_mat")
                mat_ok = mostrar_validacion(mat, validar_matricula, obligatorio=False)
                car = st.text_input("Carrera (opcional)", key="ca_car")
                car_ok = mostrar_validacion(car, validar_carrera, obligatorio=False)
            with cb:
                gru = st.text_input("Grupo (opcional)", key="ca_gru")
                gru_ok = mostrar_validacion(gru, validar_grupo, obligatorio=False)
                tel = st.text_input("Teléfono (opcional)", key="ca_tel", placeholder="10 dígitos")
                tel_ok = mostrar_validacion(tel, validar_telefono, obligatorio=False)

            usuario_unico = True
            if u and u_ok and usuario_existe(u.lower().strip()):
                st.markdown('<div class="val-error">❌ Ese usuario ya existe</div>', unsafe_allow_html=True)
                usuario_unico = False
            id_unico = True
            if id_est and id_ok and id_estudiante_existe(id_est.strip()):
                st.markdown('<div class="val-error">❌ Ese ID ya está en uso</div>', unsafe_allow_html=True)
                id_unico = False

            todos_ok = u_ok and p_ok and n_ok and id_ok and mat_ok and car_ok and gru_ok and tel_ok and usuario_unico and id_unico
            if st.button("✅ Crear Alumno", use_container_width=True, type="primary",
                         disabled=not todos_ok, key="ca_btn"):
                try:
                    with st.spinner("💾 Creando alumno..."):
                        crear_usuario(usuario=u.lower().strip(), password=p, rol='alumno',
                            tipo_usuario='alumno', nombre_completo=nombre.strip(),
                            matricula=mat.strip() if mat else None,
                            carrera=car.strip() if car else None,
                            grupo=gru.strip() if gru else None,
                            telefono=tel.strip() if tel else None,
                            id_estudiante=id_est.strip() if id_est else None)
                        registrar_log(user['id'], "CREAR_ALUMNO",
                                      f"Alumno @{u.lower().strip()} ({nombre}) creado con ID {id_est}",
                                      "Super_Usuarios")
                    limpiar_campos(['ca_u', 'ca_p', 'ca_n', 'ca_id', 'ca_mat', 'ca_car', 'ca_gru', 'ca_tel'])
                    set_flash("success", f"✅ Alumno **{nombre}** creado con ID **{id_est}**.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        elif sub == "👷 Crear Trabajador":
            u = st.text_input("Usuario", key="ct_u")
            u_ok = mostrar_validacion(u, validar_usuario)
            p = st.text_input("Contraseña", type="password", key="ct_p")
            p_ok = mostrar_validacion(p, validar_password)
            nombre = st.text_input("Nombre completo", key="ct_n")
            n_ok = mostrar_validacion(nombre, validar_nombre)
            tel = st.text_input("Teléfono (opcional)", key="ct_tel", placeholder="10 dígitos")
            tel_ok = mostrar_validacion(tel, validar_telefono, obligatorio=False)

            usuario_unico = True
            if u and u_ok and usuario_existe(u.lower().strip()):
                st.markdown('<div class="val-error">❌ Ese usuario ya existe</div>', unsafe_allow_html=True)
                usuario_unico = False
            todos_ok = u_ok and p_ok and n_ok and tel_ok and usuario_unico

            if st.button("✅ Crear Trabajador", use_container_width=True, type="primary",
                         disabled=not todos_ok, key="ct_btn"):
                try:
                    with st.spinner("💾 Creando trabajador..."):
                        crear_usuario(usuario=u.lower().strip(), password=p, rol='trabajador',
                            tipo_usuario='administrativo', nombre_completo=nombre.strip(),
                            telefono=tel.strip() if tel else None)
                        registrar_log(user['id'], "CREAR_TRABAJADOR",
                                      f"Trabajador @{u.lower().strip()} ({nombre}) creado", "Super_Usuarios")
                    limpiar_campos(['ct_u', 'ct_p', 'ct_n', 'ct_tel'])
                    set_flash("success", f"✅ Trabajador **{nombre}** creado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        elif sub == "👑 Crear Admin":
            st.warning("⚠️ Los admins tienen acceso total. Otorga este rol con precaución.")
            u = st.text_input("Usuario", key="cA_u")
            u_ok = mostrar_validacion(u, validar_usuario)
            p = st.text_input("Contraseña", type="password", key="cA_p")
            p_ok = mostrar_validacion(p, validar_password)
            nombre = st.text_input("Nombre completo", key="cA_n")
            n_ok = mostrar_validacion(nombre, validar_nombre)
            tel = st.text_input("Teléfono (opcional)", key="cA_tel")
            tel_ok = mostrar_validacion(tel, validar_telefono, obligatorio=False)

            usuario_unico = True
            if u and u_ok and usuario_existe(u.lower().strip()):
                st.markdown('<div class="val-error">❌ Ese usuario ya existe</div>', unsafe_allow_html=True)
                usuario_unico = False
            todos_ok = u_ok and p_ok and n_ok and tel_ok and usuario_unico

            if st.button("✅ Crear Administrador", use_container_width=True, type="primary",
                         disabled=not todos_ok, key="cA_btn"):
                try:
                    with st.spinner("💾 Creando administrador..."):
                        crear_usuario(usuario=u.lower().strip(), password=p, rol='admin',
                            tipo_usuario='administrativo', nombre_completo=nombre.strip(),
                            telefono=tel.strip() if tel else None)
                        registrar_log(user['id'], "CREAR_ADMIN",
                                      f"Administrador @{u.lower().strip()} ({nombre}) creado", "Super_Usuarios")
                    limpiar_campos(['cA_u', 'cA_p', 'cA_n', 'cA_tel'])
                    set_flash("success", f"✅ Administrador **{nombre}** creado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        elif sub == "📋 Ver Todos":
            cf1, cf2 = st.columns([2, 1])
            with cf1:
                filtro = st.selectbox("Filtrar por rol", ["Todos", "alumno", "trabajador", "admin"])
            with cf2:
                solo_activos = st.checkbox("Solo activos", value=False)

            with st.spinner("📋 Cargando usuarios..."):
                usuarios = obtener_todos_usuarios(None if filtro == "Todos" else filtro, solo_activos=solo_activos)

            if not usuarios:
                st.info("No hay usuarios que coincidan con el filtro.")
            else:
                activos_count = sum(1 for u in usuarios if u['activo'])
                inactivos_count = len(usuarios) - activos_count
                st.write(f"**Total: {len(usuarios)}** ({activos_count} activos, {inactivos_count} inactivos)")

                with st.expander("📊 Comparativa activos vs inactivos por rol"):
                    datos = contar_usuarios_por_estado()
                    df_comp = pd.DataFrame([
                        {"Rol": r.capitalize(), "Activos": d["activos"], "Inactivos": d["inactivos"]}
                        for r, d in datos.items()
                    ])
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)

                    fig_comp = go.Figure(data=[
                        go.Bar(name='Activos', x=df_comp['Rol'], y=df_comp['Activos'],
                               marker_color='#00ff88', text=df_comp['Activos'], textposition='outside'),
                        go.Bar(name='Inactivos', x=df_comp['Rol'], y=df_comp['Inactivos'],
                               marker_color='#D7192D', text=df_comp['Inactivos'], textposition='outside'),
                    ])
                    fig_comp.update_layout(
                        barmode='group', paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=COLOR_CREMA, size=11),
                        xaxis=dict(gridcolor="rgba(201,169,97,0.1)"),
                        yaxis=dict(gridcolor="rgba(201,169,97,0.1)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=10, r=10, t=40, b=10), height=300,
                    )
                    st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

                    if st.button("⚡ Crear índices recomendados en la BD", use_container_width=True, key="btn_indices"):
                        with st.spinner("Creando índices..."):
                            creados, errores = crear_indices()
                        st.success(f"✅ {len(creados)} índice(s) creado(s) exitosamente.")
                        if errores:
                            st.caption(f"ℹ️ {len(errores)} ya existían: {', '.join(errores[:5])}...")

                st.markdown("---")

                for u in usuarios:
                    with st.container(border=True):
                        icono = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}.get(u['rol'], '👤')
                        estado_badge = "🟢" if u['activo'] else "🔒"

                        c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
                        with c1:
                            bloqueado_activo = False
                            mins_bloqueo = 0
                            if u.get('bloqueado_hasta') and isinstance(u['bloqueado_hasta'], datetime):
                                if u['bloqueado_hasta'] > datetime.now():
                                    bloqueado_activo = True
                                    mins_bloqueo = int((u['bloqueado_hasta'] - datetime.now()).total_seconds() / 60) + 1
                            if bloqueado_activo:
                                estado_badge = "🔐"
                            st.markdown(f"**{estado_badge} {icono} {u['nombre_completo']}** — @{u['usuario']}")
                            if not u['activo']:
                                st.caption("🔒 **Cuenta desactivada**")
                            if bloqueado_activo:
                                st.caption(f"🔐 **Bloqueada** — desbloqueo en {mins_bloqueo} min")
                            intentos = u.get('intentos_fallidos') or 0
                            if intentos > 0 and not bloqueado_activo:
                                st.caption(f"⚠️ Intentos fallidos recientes: {intentos}/5")
                            if u['id_estudiante']:
                                st.caption(f"ID: {u['id_estudiante']}")
                            st.caption(f"Rol: {u['rol']} | Teléfono: {u['telefono'] or 'N/A'}")
                            if u['rol'] == 'alumno':
                                st.caption(f"Matrícula: {u['matricula'] or 'N/A'} | Carrera: {u['carrera'] or 'N/A'}")
                        with c2:
                            if st.button("✏️", key=f"edit_{u['id']}", help="Editar", use_container_width=True):
                                for other in usuarios:
                                    if other['id'] != u['id']:
                                        st.session_state[f"editando_{other['id']}"] = False
                                st.session_state[f"editando_{u['id']}"] = not st.session_state.get(f"editando_{u['id']}", False)
                                st.rerun()
                        with c3:
                            if u['id'] == user['id']:
                                st.caption("(Tú)")
                            else:
                                if u['activo']:
                                    st.button("🔒", key=f"lock_{u['id']}", help="Desactivar cuenta",
                                              use_container_width=True,
                                              on_click=cb_mostrar_confirm, args=(f"confirmar_desactivar_{u['id']}",))
                                else:
                                    st.button("🔓", key=f"unlock_{u['id']}", help="Reactivar cuenta",
                                              use_container_width=True,
                                              on_click=cb_activar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                        with c4:
                            if u['id'] != user['id']:
                                st.button("🗑️", key=f"del_user_{u['id']}", help="Eliminar",
                                          use_container_width=True,
                                          on_click=cb_mostrar_confirm, args=(f"confirmar_eliminar_{u['id']}",))
                        with c5:
                            bloqueado_boton = False
                            if u.get('bloqueado_hasta') and isinstance(u['bloqueado_hasta'], datetime):
                                if u['bloqueado_hasta'] > datetime.now():
                                    bloqueado_boton = True
                            if u['id'] == user['id']:
                                st.caption("")
                            elif bloqueado_boton:
                                if st.button("🔐", key=f"unlock_bloq_{u['id']}",
                                             help="Desbloquear cuenta", use_container_width=True):
                                    ok, msg = desbloquear_usuario(u['id'])
                                    if ok:
                                        registrar_log(user['id'], "DESBLOQUEAR_USUARIO",
                                                      f"Cuenta @{u['usuario']} desbloqueada", "Super_Usuarios", u['id'])
                                        set_flash("success", msg)
                                    else:
                                        set_flash("error", msg)
                                    st.rerun()

                        if st.session_state.get(f"confirmar_eliminar_{u['id']}", False):
                            with st.container(border=True):
                                st.error(f"🚨 ¿Eliminar **permanentemente** a **{u['nombre_completo']}** (@{u['usuario']})?")
                                st.caption("Esta acción no se puede deshacer.")
                                if u['rol'] == 'admin':
                                    st.warning("⚠️ **Estás a punto de eliminar a un ADMINISTRADOR.**")
                                    texto = st.text_input("Escribe **ELIMINAR** para confirmar:",
                                                          key=f"confirma_texto_{u['id']}", placeholder="ELIMINAR")
                                    conf_ok = (texto.strip() == "ELIMINAR")
                                else:
                                    conf_ok = True

                                cs, cn = st.columns(2)
                                with cs:
                                    st.button("✅ Sí, eliminar", key=f"si_del_{u['id']}", type="primary",
                                              use_container_width=True, disabled=not conf_ok,
                                              on_click=cb_eliminar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                                with cn:
                                    st.button("❌ Cancelar", key=f"no_del_{u['id']}", use_container_width=True,
                                              on_click=cb_ocultar_confirm, args=(f"confirmar_eliminar_{u['id']}",))

                        if st.session_state.get(f"confirmar_desactivar_{u['id']}", False):
                            with st.container(border=True):
                                st.warning(f"🔒 ¿Desactivar la cuenta de **{u['nombre_completo']}** (@{u['usuario']})?")
                                cs, cn = st.columns(2)
                                with cs:
                                    st.button("✅ Sí, desactivar", key=f"si_desc_{u['id']}", type="primary",
                                              use_container_width=True,
                                              on_click=cb_desactivar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                                with cn:
                                    st.button("❌ Cancelar", key=f"no_desc_{u['id']}", use_container_width=True,
                                              on_click=cb_ocultar_confirm, args=(f"confirmar_desactivar_{u['id']}",))

                    if st.session_state.get(f"editando_{u['id']}", False):
                        st.markdown('<div class="edit-form">', unsafe_allow_html=True)
                        st.markdown(f"#### ✏️ Editando: @{u['usuario']}")
                        st.caption(f"Rol: **{u['rol']}** (no modificable)")

                        ed_nombre = st.text_input("Nombre completo", value=u['nombre_completo'], key=f"ed_n_{u['id']}")
                        ed_n_ok = mostrar_validacion(ed_nombre, validar_nombre)
                        ed_tel = st.text_input("Teléfono", value=u['telefono'] or "", key=f"ed_tel_{u['id']}")
                        ed_tel_ok = mostrar_validacion(ed_tel, validar_telefono, obligatorio=False)

                        if u['rol'] == 'alumno':
                            ea, eb = st.columns(2)
                            with ea:
                                ed_id = st.text_input("ID Estudiante", value=u['id_estudiante'] or "", key=f"ed_id_{u['id']}")
                                ed_id_ok = mostrar_validacion(ed_id, validar_id_estudiante, obligatorio=False)
                                ed_mat = st.text_input("Matrícula", value=u['matricula'] or "", key=f"ed_mat_{u['id']}")
                                ed_mat_ok = mostrar_validacion(ed_mat, validar_matricula, obligatorio=False)
                            with eb:
                                ed_car = st.text_input("Carrera", value=u['carrera'] or "", key=f"ed_car_{u['id']}")
                                ed_car_ok = mostrar_validacion(ed_car, validar_carrera, obligatorio=False)
                                ed_gru = st.text_input("Grupo", value=u['grupo'] or "", key=f"ed_gru_{u['id']}")
                                ed_gru_ok = mostrar_validacion(ed_gru, validar_grupo, obligatorio=False)
                            ed_id_unico = True
                            if ed_id and ed_id_ok and id_estudiante_existe_otro(ed_id.strip(), u['id']):
                                st.markdown('<div class="val-error">❌ Ese ID ya lo usa otro usuario</div>', unsafe_allow_html=True)
                                ed_id_unico = False
                        else:
                            ed_id = u['id_estudiante']; ed_id_ok = True; ed_id_unico = True
                            ed_mat = u['matricula']; ed_mat_ok = True
                            ed_car = u['carrera']; ed_car_ok = True
                            ed_gru = u['grupo']; ed_gru_ok = True

                        st.markdown("##### 🔐 Cambiar contraseña *(opcional)*")
                        ed_pass = st.text_input("Nueva contraseña", type="password", key=f"ed_p_{u['id']}")
                        ed_pass2 = st.text_input("Confirmar contraseña", type="password", key=f"ed_p2_{u['id']}")
                        pass_ok, pass_msg = True, ""
                        if ed_pass:
                            if len(ed_pass) < 3:
                                pass_ok = False; pass_msg = "Mínimo 3 caracteres"
                            elif ed_pass != ed_pass2:
                                pass_ok = False; pass_msg = "Las contraseñas no coinciden"
                        if ed_pass:
                            if pass_ok:
                                st.markdown('<div class="val-ok">✅ Contraseña válida</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="val-error">❌ {pass_msg}</div>', unsafe_allow_html=True)

                        todos_ok = ed_n_ok and ed_tel_ok and ed_id_ok and ed_mat_ok and ed_car_ok and ed_gru_ok and ed_id_unico and pass_ok

                        cx, cy = st.columns(2)
                        with cx:
                            if st.button("💾 Guardar", use_container_width=True, type="primary",
                                         disabled=not todos_ok, key=f"ed_save_{u['id']}"):
                                try:
                                    with st.spinner("💾 Guardando cambios..."):
                                        cambios = []
                                        if ed_nombre != u['nombre_completo']:
                                            cambios.append(f"nombre: '{u['nombre_completo']}' → '{ed_nombre}'")
                                        if ed_pass: cambios.append("contraseña cambiada")
                                        actualizar_usuario(
                                            id_usuario=u['id'], nombre_completo=ed_nombre.strip(),
                                            telefono=ed_tel.strip() or None,
                                            matricula=ed_mat.strip() or None,
                                            carrera=ed_car.strip() or None,
                                            grupo=ed_gru.strip() or None,
                                            id_estudiante=ed_id.strip() or None,
                                            tipo_usuario=u['tipo_usuario'],
                                            nueva_password=ed_pass if ed_pass else None)
                                        detalle = f"Usuario @{u['usuario']} editado"
                                        if cambios: detalle += " — " + "; ".join(cambios)
                                        registrar_log(user['id'], "EDITAR_USUARIO", detalle, "Super_Usuarios", u['id'])
                                    st.session_state[f"editando_{u['id']}"] = False
                                    limpiar_campos([f"ed_n_{u['id']}", f"ed_tel_{u['id']}", f"ed_id_{u['id']}",
                                                    f"ed_mat_{u['id']}", f"ed_car_{u['id']}", f"ed_gru_{u['id']}",
                                                    f"ed_p_{u['id']}", f"ed_p2_{u['id']}"])
                                    set_flash("success", f"✅ Usuario **{ed_nombre}** actualizado.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with cy:
                            if st.button("❌ Cancelar", use_container_width=True, key=f"ed_cancel_{u['id']}"):
                                st.session_state[f"editando_{u['id']}"] = False
                                limpiar_campos([f"ed_n_{u['id']}", f"ed_tel_{u['id']}", f"ed_id_{u['id']}",
                                                f"ed_mat_{u['id']}", f"ed_car_{u['id']}", f"ed_gru_{u['id']}",
                                                f"ed_p_{u['id']}", f"ed_p2_{u['id']}"])
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    elif seccion == "📋 Registros":
        st.markdown("### 📋 Registros de entradas/salidas")
        fecha_desde, fecha_hasta = selector_rango_fechas("registros")

        c1, c2 = st.columns(2)
        with c1: filtro_estado = st.selectbox("Estado", ["Todos", "DENTRO", "FUERA"], key="reg_estado")
        with c2: filtro_tipo = st.selectbox("Tipo", ["Todos", "Auto", "Moto"], key="reg_tipo")

        buscar = st.text_input("🔍 Buscar (nombre, placas, matrícula)", key="reg_buscar").lower().strip()
        por_pagina = mostrar_paginacion_superior("reg")

        filtros_actuales = f"{fecha_desde}|{fecha_hasta}|{filtro_estado}|{filtro_tipo}|{buscar}|{por_pagina}"
        if st.session_state.get("reg_filtros_prev") != filtros_actuales:
            st.session_state["reg_pagina"] = 1
            st.session_state["reg_filtros_prev"] = filtros_actuales

        pagina = st.session_state.get("reg_pagina", 1)
        offset = (pagina - 1) * por_pagina

        with st.spinner("📋 Cargando registros..."):
            total = contar_registros_filtrados(fecha_desde, fecha_hasta, filtro_estado, filtro_tipo, buscar or None)
            registros = obtener_registros_paginado(fecha_desde, fecha_hasta, filtro_estado, filtro_tipo,
                                                   buscar or None, offset, por_pagina)

        if not registros:
            st.info("No hay registros en el rango seleccionado.")
        else:
            st.caption(f"**Mostrando {len(registros)} de {total} registro(s)**")

            df_export = pd.DataFrame([{
                'ID': r['id'], 'Estado': r['estado'], 'Alumno': r['nombre_completo'],
                'Matrícula': r['matricula'], 'Carrera': r['carrera'],
                'Tipo': r['tipo'], 'Placas': r['placas'],
                'Fecha Entrada': r['hora_entrada'].strftime("%d/%m/%Y") if r['hora_entrada'] else "",
                'Hora Entrada': r['hora_entrada'].strftime("%H:%M:%S") if r['hora_entrada'] else "",
                'Fecha Salida': r['hora_salida'].strftime("%d/%m/%Y") if r['hora_salida'] else "En curso",
                'Hora Salida': r['hora_salida'].strftime("%H:%M:%S") if r['hora_salida'] else ""
            } for r in registros])

            rango_txt = (f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}"
                         if fecha_desde and fecha_hasta else "Período: Todo el historial")

            with st.spinner("📄 Generando PDF..."):
                pdf_data = generar_pdf_reporte(
                    df_export, "Reporte de Registros",
                    f"{rango_txt} | Página {pagina}")
            st.download_button("📄 Descargar Reporte PDF", data=pdf_data,
                file_name=f"registros_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True, type="primary", key="dl_reg_pdf")

            st.markdown("---")

            for r in registros:
                with st.container(border=True):
                    icono = "🚗" if r['tipo'] == 'Auto' else "🏍️"
                    estado_icon = "🟢" if r['estado'] == 'DENTRO' else "🔴"
                    st.markdown(f"**{estado_icon} {icono} {r['placas']}** — {r['nombre_completo']}")
                    st.caption(f"Matrícula: {r['matricula'] or 'N/A'} | Carrera: {r['carrera'] or 'N/A'}")
                    st.caption(f"⬇️ Entrada: {r['hora_entrada']}")
                    st.caption(f"⬆️ Salida: {r['hora_salida'] or '—'}")
                    if r['evidencia_entrada'] or r['evidencia_salida']:
                        if st.button("📸 Ver evidencias", key=f"ver_ev_{r['id']}", use_container_width=True):
                            st.session_state[f"mostrar_ev_{r['id']}"] = not st.session_state.get(f"mostrar_ev_{r['id']}", False)
                    if st.session_state.get(f"mostrar_ev_{r['id']}", False):
                        if r['evidencia_entrada']:
                            st.markdown("**📷 Entrada:**")
                            img = base64_a_bytes(r['evidencia_entrada'])
                            if img: st.image(img, use_container_width=True)
                        if r['evidencia_salida']:
                            st.markdown("**📷 Salida:**")
                            img = base64_a_bytes(r['evidencia_salida'])
                            if img: st.image(img, use_container_width=True)

            st.markdown("---")
            render_paginacion_inferior("reg", pagina, total, por_pagina, "reg_pagina")

    elif seccion == "📈 Métricas":
        st.markdown("### 📈 Métricas y patrones de uso")
        with st.spinner("📈 Calculando métricas..."):
            registros = obtener_todos_los_registros()
        if not registros:
            st.info("Aún no hay datos suficientes para calcular métricas.")
        else:
            df = pd.DataFrame(registros)
            df['hora_entrada'] = pd.to_datetime(df['hora_entrada'], errors='coerce')
            df['hora_salida'] = pd.to_datetime(df['hora_salida'], errors='coerce')

            st.markdown("#### ⏰ Horas de mayor demanda")
            df['hora_del_dia'] = df['hora_entrada'].dt.hour
            horas_pico = df.groupby('hora_del_dia').size().reset_index(name='entradas').sort_values('hora_del_dia')
            st.bar_chart(horas_pico.set_index('hora_del_dia')['entradas'])

            st.markdown("#### ⏱️ Permanencia promedio")
            completados = df.dropna(subset=['hora_salida']).copy()
            if not completados.empty:
                completados['duracion_min'] = (completados['hora_salida'] - completados['hora_entrada']).dt.total_seconds() / 60
                st.metric("Promedio general", f"{completados['duracion_min'].mean():.1f} min")
                c1, c2 = st.columns(2)
                with c1:
                    ap = completados[completados['tipo'] == 'Auto']['duracion_min'].mean()
                    if pd.notna(ap): st.metric("🚗 Autos", f"{ap:.1f} min")
                with c2:
                    mp = completados[completados['tipo'] == 'Moto']['duracion_min'].mean()
                    if pd.notna(mp): st.metric("🏍️ Motos", f"{mp:.1f} min")
            else:
                st.info("Aún no hay registros completados.")

            st.markdown("#### 🎓 Uso por carrera")
            por_carrera = df[df['carrera'].notna()].groupby('carrera').size().reset_index(name='usos')
            if not por_carrera.empty: st.bar_chart(por_carrera.set_index('carrera')['usos'])

            st.markdown("#### 🚗 Uso por tipo")
            por_tipo = df.groupby('tipo').size().reset_index(name='cantidad')
            st.dataframe(por_tipo, use_container_width=True, hide_index=True)

    elif seccion == "🔍 Auditoría":
        st.markdown("### 🔍 Registro de Auditoría")
        st.caption("Historial de todas las acciones importantes en el sistema.")
        st.metric("Total de registros en el log", contar_logs())

        fecha_desde, fecha_hasta = selector_rango_fechas("auditoria")

        c1, c2 = st.columns(2)
        with c1:
            acciones = ["Todas"] + obtener_acciones_unicas()
            filtro_accion = st.selectbox("Filtrar por acción", acciones, key="aud_accion")
        with c2:
            buscar = st.text_input("🔍 Buscar (usuario o detalle)", key="aud_buscar").lower().strip()

        por_pagina = mostrar_paginacion_superior("aud")

        filtros_actuales = f"{fecha_desde}|{fecha_hasta}|{filtro_accion}|{buscar}|{por_pagina}"
        if st.session_state.get("aud_filtros_prev") != filtros_actuales:
            st.session_state["aud_pagina"] = 1
            st.session_state["aud_filtros_prev"] = filtros_actuales

        pagina = st.session_state.get("aud_pagina", 1)
        offset = (pagina - 1) * por_pagina

        with st.spinner("🔍 Cargando logs..."):
            total = contar_logs_filtrados(filtro_accion, buscar or None, fecha_desde, fecha_hasta)
            logs = obtener_logs(limite=por_pagina, filtro_accion=filtro_accion,
                                buscar=buscar if buscar else None,
                                fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, offset=offset)

        if not logs:
            st.info("No hay logs que coincidan con los filtros.")
        else:
            st.write(f"**Mostrando {len(logs)} de {total} registro(s)**")
            df_logs = pd.DataFrame([{
                'ID': l['id'],
                'Fecha': l['fecha'].strftime("%d/%m/%Y") if l['fecha'] else "",
                'Hora': l['fecha'].strftime("%H:%M:%S") if l['fecha'] else "",
                'Acción': l['accion'],
                'Usuario': f"@{l['usuario_accion']}" if l['usuario_accion'] else "Sistema",
                'Nombre completo': l['nombre_accion'] or "",
                'Rol': l['rol_accion'] or "",
                'Detalles': l['detalles'] or "",
                'Tabla afectada': l['tabla_afectada'] or "",
                'ID afectado': l['id_afectado'] if l['id_afectado'] else ""
            } for l in logs])

            rango_txt = (f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}"
                         if fecha_desde and fecha_hasta else "Período: Todo el historial")

            with st.spinner("📄 Generando PDF..."):
                pdf_data = generar_pdf_reporte(
                    df_logs, "Reporte de Auditoría",
                    f"{rango_txt} | Página {pagina}")
            st.download_button("📄 Descargar Reporte PDF", data=pdf_data,
                file_name=f"auditoria_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True, type="primary", key="dl_aud_pdf")

            st.markdown("---")

            colores_accion = {
                "INICIO_SESION": "#00ff88",
                "CREAR_ALUMNO": "#C9A961", "CREAR_TRABAJADOR": "#C9A961", "CREAR_ADMIN": "#D7192D",
                "EDITAR_USUARIO": "#C9A961",
                "DESACTIVAR_USUARIO": "#D7192D", "REACTIVAR_USUARIO": "#00ff88",
                "ELIMINAR_USUARIO": "#7B1B2E", "ELIMINAR_VEHICULO": "#7B1B2E",
                "CREAR_VEHICULO": "#C9A961",
                "REGISTRAR_ENTRADA": "#00ff88", "REGISTRAR_SALIDA": "#C9A961",
                "DESBLOQUEAR_USUARIO": "#00ff88",
                "CAMBIAR_PASSWORD": "#C9A961",
                "ACTUALIZAR_TELEFONO": "#C9A961",
                "ENVIAR_MENSAJE": "#0066B3",
                "ENTRADA_MANUAL": "#ffaa00",
                "SALIDA_MANUAL": "#ffaa00",
                "VALIDAR_ENTRADA_MANUAL": "#00ff88",
                "REGENERAR_QR": "#C9A961",
            }
            for l in logs:
                color = colores_accion.get(l['accion'], "#C9A961")
                icono_rol = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}.get(l['rol_accion'], '👤')
                fecha_str = l['fecha'].strftime("%d/%m/%Y %H:%M:%S") if l['fecha'] else "N/A"
                st.markdown(f"""
                    <div class="log-row" style="border-left-color: {color};">
                        <div style="display:flex; justify-content:space-between; flex-wrap:wrap;">
                            <span class="log-accion" style="color: {color};">{l['accion']}</span>
                            <span class="log-fecha">{fecha_str}</span>
                        </div>
                        <div class="log-detalle">
                            {icono_rol} <b>@{l['usuario_accion'] or 'sistema'}</b>
                            {f"({l['nombre_accion']})" if l['nombre_accion'] else ""}
                        </div>
                        <div class="log-detalle">{l['detalles'] or ''}</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            render_paginacion_inferior("aud", pagina, total, por_pagina, "aud_pagina")

    elif seccion == "💬 Mensajes":
        st.markdown("### 💬 Mensajes")
        tab1, tab2, tab3 = st.tabs(["📥 Recibidos", "📤 Enviados", "✉️ Nuevo mensaje"])

        with tab1:
            mensajes = obtener_mensajes_para_usuario(user['id'])
            if not mensajes:
                st.info("No tienes mensajes recibidos.")
            else:
                no_leidos = sum(1 for m in mensajes if not m['leido'])
                st.caption(f"**{no_leidos}** sin leer de **{len(mensajes)}**")
                for m in mensajes:
                    icono_leido = "📭" if m['leido'] else "📬"
                    pref = "🔵 " if not m['leido'] else ""
                    tipo_icon = {"mensaje": "💬", "alerta": "🚨", "aviso": "📢"}.get(m['tipo'], "💬")
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.markdown(f"**{pref}{tipo_icon} {m['asunto']}**")
                            st.caption(f"De: @{m['remitente_usuario']} ({m['remitente_nombre']}) · {m['fecha'].strftime('%d/%m/%Y %H:%M')}")
                            if m.get('es_broadcast'):
                                st.caption("📢 Mensaje general")
                        with c2:
                            if not m['leido']:
                                if st.button("✅", key=f"leido_{m['id']}", help="Marcar como leído", use_container_width=True):
                                    marcar_mensaje_leido(m['id'])
                                    st.rerun()
                        with st.expander("Ver contenido"):
                            st.write(m['cuerpo'])
                            if st.button("🗑️ Eliminar", key=f"del_msg_{m['id']}", use_container_width=True):
                                eliminar_mensaje(m['id'])
                                st.rerun()

        with tab2:
            enviados = obtener_mensajes_enviados(user['id'])
            if not enviados:
                st.info("No has enviado mensajes.")
            else:
                for m in enviados:
                    with st.container(border=True):
                        st.markdown(f"**{m['asunto']}**")
                        dest = "📢 Todos los alumnos" if m.get('es_broadcast') else f"@{m['destinatario_usuario']} ({m['destinatario_nombre']})"
                        st.caption(f"Para: {dest} · {m['fecha'].strftime('%d/%m/%Y %H:%M')}")
                        with st.expander("Ver contenido"):
                            st.write(m['cuerpo'])
                            if st.button("🗑️ Eliminar", key=f"del_env_{m['id']}", use_container_width=True):
                                eliminar_mensaje(m['id'])
                                st.rerun()

        with tab3:
            st.markdown("#### ✉️ Enviar nuevo mensaje")
            destinatario_tipo = st.radio(
                "Destinatario",
                ["📢 Todos los alumnos (broadcast)", "🎓 Un alumno específico",
                 "👷 Un trabajador", "👑 Un admin"],
                horizontal=False, key="msg_dest_tipo"
            )

            destinatario_id = None
            if "Todos los alumnos" in destinatario_tipo:
                destinatario_id = None
            else:
                if "alumno" in destinatario_tipo:
                    usuarios_dest = obtener_todos_usuarios("alumno", solo_activos=True)
                elif "trabajador" in destinatario_tipo:
                    usuarios_dest = obtener_todos_usuarios("trabajador", solo_activos=True)
                else:
                    usuarios_dest = obtener_todos_usuarios("admin", solo_activos=True)

                opciones = {f"{u['nombre_completo']} (@{u['usuario']})": u['id'] for u in usuarios_dest}
                if opciones:
                    sel = st.selectbox("Selecciona el destinatario", list(opciones.keys()), key="msg_dest_sel")
                    destinatario_id = opciones[sel]
                else:
                    st.warning("No hay usuarios disponibles.")
                    destinatario_id = -1

            asunto = st.text_input("Asunto", key="msg_asunto", max_chars=200)
            tipo_msg = st.selectbox("Tipo", ["mensaje", "aviso", "alerta"], key="msg_tipo")
            cuerpo = st.text_area("Mensaje", key="msg_cuerpo", height=150)

            asunto_ok = bool(asunto and asunto.strip())
            cuerpo_ok = bool(cuerpo and cuerpo.strip())
            dest_ok = destinatario_id != -1

            if st.button("📤 Enviar mensaje", type="primary", use_container_width=True,
                         disabled=not (asunto_ok and cuerpo_ok and dest_ok), key="msg_enviar"):
                enviar_mensaje(user['id'], asunto.strip(), cuerpo.strip(), destinatario_id, tipo_msg)
                registrar_log(user['id'], "ENVIAR_MENSAJE",
                              f"@{user['usuario']} envió '{asunto[:60]}' "
                              f"{'a todos los alumnos' if destinatario_id is None else f'a usuario ID {destinatario_id}'}",
                              "Super_Mensajes")
                limpiar_campos(['msg_asunto', 'msg_cuerpo'])
                set_flash("success", "✅ Mensaje enviado.")
                st.rerun()

    elif seccion == "🚗 Vehículos":
        st.markdown("### 🚗 Vehículos registrados")
        st.caption("Busca un vehículo para ver su historial detallado.")

        buscar_veh = st.text_input("🔍 Buscar por placas, alumno o matrícula", key="veh_buscar_admin").strip()

        with st.spinner("🔎 Buscando vehículos..."):
            vehiculos = buscar_vehiculos_admin(buscar_veh if buscar_veh else None, limite=50)

        if not vehiculos:
            st.info("No se encontraron vehículos.")
        else:
            st.caption(f"**{len(vehiculos)}** vehículo(s)")
            for v in vehiculos:
                icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{icono} {v['placas']}** — {v['tipo']}")
                        st.caption(f"Dueño: {v['nombre_completo']} (@{v['usuario']})")
                        st.caption(f"Matrícula: {v['matricula'] or 'N/A'} | ID: {v['id_estudiante'] or 'N/A'} | Carrera: {v['carrera'] or 'N/A'}")
                        st.caption(f"Marca: {v['marca'] or 'N/A'} | Modelo: {v['modelo'] or 'N/A'} | Color: {v['color'] or 'N/A'}")
                    with c2:
                        if st.button("📜 Historial", key=f"hist_veh_{v['id']}", use_container_width=True):
                            st.session_state[f"ver_hist_veh_{v['id']}"] = not st.session_state.get(f"ver_hist_veh_{v['id']}", False)
                            st.rerun()

                    if st.session_state.get(f"ver_hist_veh_{v['id']}", False):
                        st.markdown("---")
                        st.markdown(f"#### 📜 Historial de {v['placas']}")
                        historial = obtener_historial_vehiculo(v['id'])

                        if not historial:
                            st.info("Este vehículo no tiene registros.")
                        else:
                            total_visitas = len(historial)
                            completadas = [h for h in historial if h['hora_salida']]
                            activo = any(h['estado'] == 'DENTRO' for h in historial)

                            ca, cb, cc = st.columns(3)
                            with ca: st.metric("Visitas", total_visitas)
                            with cb:
                                prom_str = "N/A"
                                if completadas:
                                    tiempos = [(h['hora_salida'] - h['hora_entrada']).total_seconds() / 60 for h in completadas]
                                    prom = sum(tiempos) / len(tiempos)
                                    prom_str = f"{prom:.0f} min" if prom < 60 else f"{prom/60:.1f} h"
                                st.metric("Permanencia prom.", prom_str)
                            with cc:
                                st.metric("Estado actual", "🟢 DENTRO" if activo else "🔴 FUERA")

                            df_h = pd.DataFrame([{
                                'fecha': h['hora_entrada'].date(),
                                'hora': h['hora_entrada'].hour
                            } for h in historial])
                            if not df_h.empty:
                                por_dia = df_h.groupby('fecha').size().reset_index(name='entradas')
                                por_dia['fecha_str'] = pd.to_datetime(por_dia['fecha']).dt.strftime('%d/%m')
                                fig = go.Figure(data=[go.Bar(
                                    x=por_dia['fecha_str'], y=por_dia['entradas'],
                                    marker=dict(color=COLOR_DORADO),
                                    text=por_dia['entradas'], textposition="outside",
                                    textfont=dict(color=COLOR_CREMA, size=10),
                                )])
                                fig.update_layout(
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                    font=dict(color=COLOR_CREMA, size=10),
                                    xaxis=dict(gridcolor="rgba(201,169,97,0.1)"),
                                    yaxis=dict(gridcolor="rgba(201,169,97,0.1)"),
                                    margin=dict(l=10, r=10, t=20, b=10), height=180,
                                    showlegend=False,
                                    title=dict(text="Visitas por día", font=dict(color=COLOR_DORADO, size=12))
                                )
                                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                            df_hist = pd.DataFrame([{
                                'Fecha': h['hora_entrada'].strftime("%d/%m/%Y %H:%M") if h['hora_entrada'] else "",
                                'Salida': h['hora_salida'].strftime("%d/%m/%Y %H:%M") if h['hora_salida'] else "En curso",
                                'Estado': h['estado'],
                                'Duración': (
                                    f"{int(((h['hora_salida'] - h['hora_entrada']).total_seconds())/60)} min"
                                    if h['hora_salida'] else "—"
                                )
                            } for h in historial[:30]])
                            st.dataframe(df_hist, use_container_width=True, hide_index=True)

                            if st.button("❌ Cerrar historial", key=f"cerrar_hist_{v['id']}", use_container_width=True):
                                st.session_state[f"ver_hist_veh_{v['id']}"] = False
                                st.rerun()

    elif seccion == "🆘 Registros Manuales":
        st.markdown("### 🆘 Registros manuales (entradas sin identificación)")
        pendientes = contar_registros_manuales_pendientes()
        if pendientes:
            st.error(f"⚠️ **{pendientes}** registro(s) sin validar.")
        else:
            st.success("✅ No hay registros pendientes de validación.")

        fecha_desde, fecha_hasta = selector_rango_fechas("manuales")

        ver_solo_pendientes = st.checkbox("Ver solo pendientes de validación",
                                           value=bool(pendientes))

        with st.spinner("Cargando registros manuales..."):
            registros = obtener_registros_manuales(
                fecha_desde, fecha_hasta, solo_pendientes=ver_solo_pendientes
            )

        if not registros:
            st.info("No hay registros manuales en el rango.")
        else:
            st.caption(f"**{len(registros)}** registro(s)")

            df_man = pd.DataFrame([{
                'ID': r['id'],
                'Fecha': r['hora_entrada'].strftime("%d/%m/%Y") if r['hora_entrada'] else "",
                'Entrada': r['hora_entrada'].strftime("%H:%M") if r['hora_entrada'] else "",
                'Salida': r['hora_salida'].strftime("%d/%m/%Y %H:%M") if r['hora_salida'] else "En curso",
                'Persona': r['nombre_visitante'],
                'ID mostrada': r['tipo_identificacion'] or "",
                'Motivo': r['motivo'] or "",
                'Tipo': r['tipo_vehiculo'] or "",
                'Placas': r['placas'] or "(sin placas)",
                'Marca': r['marca'] or "",
                'Modelo': r['modelo'] or "",
                'Autorizó': r['trabajador_nombre'] or "",
                'Validado': "Sí" if r['validado'] else "NO",
                'Validó admin': r['admin_nombre'] or "",
            } for r in registros])

            with st.spinner("Generando PDF..."):
                pdf_data = generar_pdf_reporte(
                    df_man, "Reporte de Entradas Manuales",
                    f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
            st.download_button(
                "📄 Descargar reporte PDF",
                data=pdf_data,
                file_name=f"entradas_manuales_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True, type="primary", key="dl_man_pdf"
            )

            st.markdown("---")
            for r in registros:
                with st.container(border=True):
                    badge = "✅ Validado" if r['validado'] else "🟡 Pendiente"
                    st.markdown(f"### {badge} — {r['nombre_visitante']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**ID mostrada:** {r['tipo_identificacion'] or '—'}")
                        st.markdown(f"**Motivo:** {r['motivo'] or '—'}")
                        st.markdown(f"**Tipo vehículo:** {r['tipo_vehiculo']}")
                        st.markdown(f"**Placas:** {r['placas'] or '(sin placas)'}")
                        st.markdown(f"**Marca/Modelo/Color:** "
                                    f"{r['marca'] or '—'} / {r['modelo'] or '—'} / {r['color'] or '—'}")
                    with c2:
                        st.markdown(f"**Entrada:** {r['hora_entrada']}")
                        st.markdown(f"**Salida:** {r['hora_salida'] or 'En curso'}")
                        st.markdown(f"**Autorizó:** {r['trabajador_nombre']} "
                                    f"(@{r['trabajador_usuario']})")
                        if r['validado']:
                            st.markdown(f"**Validado por:** {r['admin_nombre']} "
                                        f"({r['fecha_validacion']})")

                    ev1, ev2 = st.columns(2)
                    with ev1:
                        if r['evidencia_entrada']:
                            st.markdown("**📷 Entrada:**")
                            img = base64_a_bytes(r['evidencia_entrada'])
                            if img: st.image(img, use_container_width=True)
                    with ev2:
                        if r['evidencia_salida']:
                            st.markdown("**📷 Salida:**")
                            img = base64_a_bytes(r['evidencia_salida'])
                            if img: st.image(img, use_container_width=True)

                    if not r['validado']:
                        if st.button(f"✅ Validar registro #{r['id']}",
                                     key=f"val_man_{r['id']}",
                                     type="primary", use_container_width=True):
                            validar_registro_manual(r['id'], user['id'])
                            registrar_log(user['id'], "VALIDAR_ENTRADA_MANUAL",
                                          f"Validó entrada manual #{r['id']} de {r['nombre_visitante']}",
                                          "Super_Registros_Manuales", r['id'])
                            set_flash("success", f"✅ Registro #{r['id']} validado.")
                            st.rerun()

    elif seccion == "🔧 Mi Cuenta":
        st.markdown("### 🔧 Mi Cuenta")
        st.caption("Gestiona tu propia cuenta desde aquí.")

        with st.expander("👤 Ver mi información"):
            st.write(f"**Usuario:** {user['usuario']}")
            st.write(f"**Nombre completo:** {user['nombre_completo']}")
            st.write(f"**Rol:** {user['rol']}")
            st.write(f"**Tipo:** {user['tipo_usuario'] or 'N/A'}")
            st.write(f"**Teléfono:** {user['telefono'] or 'N/A'}")
            st.write(f"**Registrado:** {user['fecha_registro']}")

        mostrar_mi_cuenta(user)


# ============================================================
# MAIN
# ============================================================
if st.session_state.usuario is not None:
    rol = st.session_state.usuario['rol']
    iconos = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}

    col_user, col_brand, col_salir = st.columns([3, 2, 1])
    with col_user:
        st.markdown(
            f"<div style='padding-top: 10px; color: #C9A961;'>"
            f"<b>{iconos.get(rol, '👤')} @{st.session_state.usuario['usuario']}</b>"
            f"</div>", unsafe_allow_html=True)
    with col_brand:
        st.markdown(mostrar_marca_cudy(), unsafe_allow_html=True)
    with col_salir:
        if st.button("🚪 Salir", use_container_width=True):
            cerrar_sesion()

if st.session_state.usuario is None:
    pantalla_login()
else:
    rol = st.session_state.usuario['rol']
    if rol == 'alumno': panel_alumno()
    elif rol == 'trabajador': panel_trabajador()
    elif rol == 'admin': panel_admin()
    else: st.error(f"Rol desconocido: {rol}")