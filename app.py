import streamlit as st
import json
import re
import os
import tempfile
import urllib.request
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
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
    actualizar_telefono_usuario
)

# --- LOGOS (URLs directas desde GitHub) ---
LOGO_COMPLETO_URL = "https://raw.githubusercontent.com/cj3302718-netizen/Estacionamiento-Yahualica/main/logo_completo.png"
LOGO_ESCUDO_URL = "https://raw.githubusercontent.com/cj3302718-netizen/Estacionamiento-Yahualica/main/logo_escudo.png"

st.set_page_config(
    page_title="CUYPARK",
    page_icon=LOGO_ESCUDO_URL,
    layout="centered"
)

# --- ESTILOS (Paleta universitaria: vino + dorado) ---
st.markdown("""
<style>
    /* Fondo general con degradado vino oscuro */
    .stApp {
        background: radial-gradient(ellipse at top, #1a0a0f 0%, #0d0407 40%, #050203 100%) !important;
    }

    header[data-testid="stHeader"] {
        background: rgba(0, 0, 0, 0) !important;
    }

    section[data-testid="stSidebar"] {
        background: #0f0508 !important;
    }

    .titulo-principal { text-align: center; color: #C9A961; font-size: 2rem; font-weight: 800; margin-bottom: 0; letter-spacing: 2px; }
    .subtitulo { text-align: center; color: #A89968; font-size: 0.9rem; margin-top: -8px; margin-bottom: 20px; }

    .panel-header { background: linear-gradient(135deg, #7B1B2E 0%, #D7192D 100%); padding: 14px 16px; border-radius: 12px; color: #FFFFFF; font-weight: 700; margin-bottom: 16px; font-size: 1.05rem; line-height: 1.3; box-shadow: 0 0 20px rgba(123, 27, 46, 0.4); }

    .contador-card { background: #1a0a0f; border: 2px solid #C9A961; border-radius: 16px; padding: 14px; text-align: center; box-shadow: 0 0 15px rgba(201, 169, 97, 0.35); margin-bottom: 10px; }
    .contador-card h4 { color: #A89968; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin: 0; }
    .contador-card .numero { font-size: 1.6rem; font-weight: 800; color: #C9A961; margin-top: 4px; }

    .edit-form { background: #0f0508; border: 2px dashed #C9A961; border-radius: 12px; padding: 16px; margin-top: 10px; }

    .hist-item { background: #1a0a0f; border-left: 3px solid #C9A961; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
    .hist-duracion { color: #A89968; font-size: 0.8rem; }

    .log-row { background: #1a0a0f; border-left: 3px solid #C9A961; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
    .log-accion { font-weight: 700; font-size: 0.85rem; }
    .log-fecha { color: #A89968; font-size: 0.75rem; }
    .log-detalle { color: #E8DFD0; font-size: 0.85rem; margin-top: 4px; }

    .ocupacion-label { display:flex; justify-content:space-between; font-size:0.88rem; margin-bottom: 4px; margin-top: 8px; }
    .ocupacion-label b { color: #C9A961; }

    .kpi-card { background: linear-gradient(135deg, #1a0a0f 0%, #2a1015 100%); border: 1px solid rgba(201, 169, 97, 0.35); border-radius: 14px; padding: 14px 16px; text-align: center; }
    .kpi-card .kpi-label { color: #A89968; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.8px; }
    .kpi-card .kpi-value { font-size: 1.7rem; font-weight: 800; color: #F5F0E8; margin-top: 2px; }
    .kpi-card .kpi-delta { font-size: 0.8rem; margin-top: 2px; }
    .delta-up { color: #00ff88; }
    .delta-down { color: #ff6666; }
    .delta-neutral { color: #A89968; }

    .bienvenida-card { background: linear-gradient(135deg, #1a3a1a 0%, #2a5028 100%); border: 2px solid #00ff88; border-radius: 16px; padding: 18px; text-align: center; margin-bottom: 16px; box-shadow: 0 0 20px rgba(0, 255, 136, 0.3); }
    .bienvenida-card h3 { color: #00ff88; margin: 0; font-size: 1.1rem; }
    .bienvenida-card p { color: #ffffff; margin: 6px 0 0 0; font-size: 0.95rem; }
    .bienvenida-card .placas { color: #00ff88; font-weight: 800; font-size: 1.3rem; }

    .val-ok { color: #00ff88; font-size: 0.8rem; margin-top: -8px; margin-bottom: 8px; }
    .val-error { color: #ff5555; font-size: 0.8rem; margin-top: -8px; margin-bottom: 8px; }

    /* Medallón del logo en login */
    .logo-medallon {
        display: inline-block;
        background: radial-gradient(circle at 30% 30%, #FFFFFF 0%, #F5F0E8 60%, #E8DFD0 100%);
        border-radius: 50%;
        padding: 6px;
        border: 3px solid #C9A961;
        box-shadow: 0 0 30px rgba(201, 169, 97, 0.6), 0 0 60px rgba(123, 27, 46, 0.4);
        margin-bottom: 16px;
    }
    .logo-medallon img {
        width: 130px;
        height: 130px;
        border-radius: 50%;
        display: block;
        object-fit: cover;
    }

    /* Logo compacto barra superior */
    .logo-barra {
        display: inline-block;
        background: radial-gradient(circle, #FFFFFF 0%, #F5F0E8 100%);
        border-radius: 50%;
        padding: 2px;
        border: 2px solid #C9A961;
        box-shadow: 0 0 8px rgba(201, 169, 97, 0.5);
        vertical-align: middle;
        margin-right: 8px;
    }
    .logo-barra img {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: block;
        object-fit: cover;
    }

    /* Marca CUYPARK con texto */
    .brand-cudy {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
        padding: 6px 0;
    }
    .brand-cudy .texto {
        text-align: right;
        line-height: 1.1;
    }
    .brand-cudy .texto .linea1 {
        color: #A89968;
        font-size: 0.65rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 600;
    }
    .brand-cudy .texto .linea2 {
        color: #C9A961;
        font-size: 0.95rem;
        font-weight: 800;
        letter-spacing: 1.5px;
    }

    /* Barra de progreso dorada */
    .stProgress > div > div > div > div {
        background-color: #C9A961 !important;
    }

    @media (max-width: 768px) {
        .stButton > button { min-height: 48px !important; font-size: 0.95rem !important; padding: 10px 14px !important; border-radius: 12px !important; }
        .stTextInput > div > div > input, .stSelectbox > div > div > div { min-height: 44px !important; font-size: 16px !important; }
        .block-container { padding-left: 12px !important; padding-right: 12px !important; padding-top: 20px !important; }
        h1 { font-size: 1.5rem !important; } h2 { font-size: 1.3rem !important; } h3 { font-size: 1.1rem !important; }
        [data-testid="stMetric"] { padding: 8px 0 !important; }
        [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
        .logo-medallon img { width: 100px; height: 100px; }
        .brand-cudy .texto .linea2 { font-size: 0.8rem; }
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# EXPORTAR EXCEL PROFESIONAL
# =========================================================
def exportar_excel_profesional(df, titulo_reporte, subtitulo_extra=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    header_fill = PatternFill(start_color="7B1B2E", end_color="7B1B2E", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    title_font = Font(bold=True, size=16, color="7B1B2E")
    sub_font = Font(italic=True, size=9, color="666666")
    border_thin = Side(style='thin', color='BFBFBF')
    border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    alt_fill = PatternFill(start_color="F5F0E8", end_color="F5F0E8", fill_type="solid")
    data_align = Alignment(vertical="center", wrap_text=False)

    total_cols = len(df.columns)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    title_cell = ws.cell(row=1, column=1, value=titulo_reporte)
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 24

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    sub_text = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  CUYPARK - Colegio Universitario de Yahualica"
    if subtitulo_extra:
        sub_text += f"  |  {subtitulo_extra}"
    sub_cell = ws.cell(row=2, column=1, value=sub_text)
    sub_cell.font = sub_font
    sub_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[3].height = 6

    header_row = 4
    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=str(col_name))
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = border
    ws.row_dimensions[header_row].height = 22

    for row_idx, row in enumerate(df.itertuples(index=False), start=header_row + 1):
        for col_idx, value in enumerate(row, start=1):
            if pd.isna(value) if not isinstance(value, (list, dict)) else False:
                value = ""
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = border
            cell.alignment = data_align
            if (row_idx - header_row) % 2 == 0:
                cell.fill = alt_fill

    for col_idx, col_name in enumerate(df.columns, start=1):
        max_len = len(str(col_name))
        for row_idx in range(header_row + 1, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 45)

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(total_cols)}{ws.max_row}"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# HELPER: SELECTOR DE RANGO DE FECHAS
# =========================================================
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


# =========================================================
# HELPER: NOTIFICACIÓN DE ENTRADA RECIENTE
# =========================================================
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


# =========================================================
# VALIDACIONES
# =========================================================
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


# =========================================================
# HELPER: MOSTRAR VALIDACIÓN EN VIVO
# =========================================================
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


# =========================================================
# HELPER: GENERAR PDF DEL QR (CUYPARK)
# =========================================================
def generar_pdf_qr(user, vehiculo, qr_bytes):
    """Genera un PDF profesional con el código QR del alumno."""

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(123, 27, 46)
            self.rect(0, 0, 210, 28, "F")

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as _f:
                    _f.write(urllib.request.urlopen(LOGO_ESCUDO_URL, timeout=5).read())
                    _logo_path = _f.name
                self.image(_logo_path, x=10, y=4, w=20)
                try:
                    os.unlink(_logo_path)
                except Exception:
                    pass
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

    pdf.cell(45, 6, "Nombre completo:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(user.get('nombre_completo') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "ID Estudiante:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(user.get('id_estudiante') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Matrícula:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(user.get('matricula') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Carrera:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(user.get('carrera') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Grupo:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(user.get('grupo') or 'N/A'), ln=1)

    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 7, "Datos del Vehículo", ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    pdf.cell(45, 6, "Tipo:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(vehiculo.get('tipo') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Placas:", border=0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(123, 27, 46)
    pdf.cell(0, 6, str(vehiculo.get('placas') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(45, 6, "Marca:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(vehiculo.get('marca') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Modelo:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(vehiculo.get('modelo') or 'N/A'), ln=1)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "Color:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(vehiculo.get('color') or 'N/A'), ln=1)

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

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    pdf.set_y(qr_y + qr_size + 8)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0, 5,
        "Presenta este código QR en la caseta del estacionamiento tanto al entrar como al salir. "
        "Puedes imprimirlo o mostrarlo desde tu dispositivo móvil.",
        align="C"
    )

    return bytes(pdf.output())


# --- ESTADO DE SESIÓN ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'qr_generado' not in st.session_state:
    st.session_state.qr_generado = None
if 'flash' not in st.session_state:
    st.session_state.flash = None


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


# =========================================================
# HELPERS: LOGO Y BRANDING
# =========================================================
def mostrar_branding_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 24px;">
                <div class="logo-medallon">
                    <img src="{LOGO_ESCUDO_URL}" alt="Colegio Universitario de Yahualica">
                </div>
                <div style="
                    color: #C9A961;
                    font-size: 0.7rem;
                    letter-spacing: 4px;
                    text-transform: uppercase;
                    font-weight: 600;
                    margin-top: 4px;
                ">
                    Colegio Universitario
                </div>
                <div style="
                    color: #C9A961;
                    font-size: 1.6rem;
                    font-weight: 800;
                    letter-spacing: 3px;
                    margin-top: 2px;
                ">
                    DE YAHUALICA
                </div>
                <div style="
                    width: 80px;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #C9A961, transparent);
                    margin: 12px auto 0 auto;
                "></div>
            </div>
        """, unsafe_allow_html=True)


def mostrar_logo_escudo(tamaño_px=44):
    return f"""
        <div class="logo-barra">
            <img src="{LOGO_ESCUDO_URL}" alt="CUYPARK">
        </div>
    """


def mostrar_marca_cudy():
    return f"""
        <div class="brand-cudy">
            <div class="texto">
                <div class="linea1">Colegio Universitario</div>
                <div class="linea2">DE YAHUALICA</div>
            </div>
            <div class="logo-barra" style="margin-right: 0;">
                <img src="{LOGO_ESCUDO_URL}" alt="CUYPARK">
            </div>
        </div>
    """


# =========================================================
# HELPER: MI CUENTA (Contraseña + Teléfono)
# =========================================================
def mostrar_mi_cuenta(user):
    with st.expander("🔧 Mi cuenta — Contraseña y contacto"):

        st.markdown("#### 📱 Actualizar mi teléfono")
        st.caption("Solo el teléfono puede ser editado por ti. Otros datos son oficiales.")

        tel_actual = user.get('telefono') or ""
        st.caption(f"Teléfono actual registrado: **{tel_actual if tel_actual else '(sin teléfono)'}**")

        nuevo_tel = st.text_input("Nuevo teléfono (10 dígitos)",
                                   value=tel_actual,
                                   key=f"mt_tel_{user['id']}",
                                   placeholder="444-123-4567")

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

        p_actual = st.text_input("Contraseña actual", type="password",
                                  key=f"cp_act_{user['id']}")

        p_nueva = st.text_input("Nueva contraseña", type="password",
                                 key=f"cp_new_{user['id']}")
        p_nueva_ok = False
        if p_nueva:
            if len(p_nueva) < 3:
                st.markdown('<div class="val-error">❌ Mínimo 3 caracteres</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="val-ok">✅ Contraseña válida</div>', unsafe_allow_html=True)
                p_nueva_ok = True

        p_confirm = st.text_input("Confirmar nueva contraseña", type="password",
                                   key=f"cp_conf_{user['id']}")
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


# =========================================================
# CALLBACKS
# =========================================================
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
    st.rerun()


# =========================================================
# LOGIN
# =========================================================
def pantalla_login():
    mostrar_branding_login()
    st.markdown('<p class="titulo-principal">CUYPARK</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo">Sistema de Estacionamiento Inteligente — CUDY</p>', unsafe_allow_html=True)
    mostrar_flash()

    if contar_admins() == 0:
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
            user, error = autenticar(usuario.lower().strip(), password)
            if user:
                st.session_state.usuario = user
                registrar_log(user['id'], "INICIO_SESION", f"@{user['usuario']} inició sesión", "Super_Usuarios", user['id'])
                st.rerun()
            else:
                if "🔒" in error:
                    st.error(f"{error}")
                    st.info("💡 **¿Olvidaste tu contraseña?** Contacta al administrador para que la restablezca.")
                else:
                    st.warning(f"⚠️ {error}")

    st.caption("🔒 Las cuentas son creadas por el administrador.")


# =========================================================
# FRAGMENTOS CON AUTO-REFRESH
# =========================================================
@st.fragment(run_every="15s")
def _contadores_alumno():
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

    col1, col2 = st.columns(2)
    with col1:
        if autos:
            disponibles_autos = autos['capacidad_total'] - autos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🚗 Autos</h4><div class="numero">{disponibles_autos} de {autos["capacidad_total"]}</div></div>', unsafe_allow_html=True)
    with col2:
        if motos:
            disponibles_motos = motos['capacidad_total'] - motos['ocupados']
            st.markdown(f'<div class="contador-card"><h4>🏍️ Motos</h4><div class="numero">{disponibles_motos} de {motos["capacidad_total"]}</div></div>', unsafe_allow_html=True)


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


@st.fragment(run_every="15s")
def _dashboard_datos_vivo():
    espacios = obtener_espacios()
    autos = next((e for e in espacios if e['tipo'] == 'Auto'), None)
    motos = next((e for e in espacios if e['tipo'] == 'Moto'), None)

    col1, col2 = st.columns(2)
    with col1:
        if autos:
            libres_a = autos['capacidad_total'] - autos['ocupados']
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">🚗 Autos dentro</div>
                    <div class="kpi-value">{autos['ocupados']}</div>
                    <div class="kpi-delta delta-neutral">{libres_a} lugares libres</div>
                </div>
            """, unsafe_allow_html=True)
    with col2:
        if motos:
            libres_m = motos['capacidad_total'] - motos['ocupados']
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">🏍️ Motos dentro</div>
                    <div class="kpi-value">{motos['ocupados']}</div>
                    <div class="kpi-delta delta-neutral">{libres_m} lugares libres</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 📊 Ocupación actual")
    if autos and autos['capacidad_total'] > 0:
        pct_autos = (autos['ocupados'] / autos['capacidad_total']) * 100
        st.markdown(f'<div class="ocupacion-label"><span>🚗 Autos</span><b>{autos["ocupados"]}/{autos["capacidad_total"]} ({pct_autos:.1f}%)</b></div>', unsafe_allow_html=True)
        st.progress(min(pct_autos / 100, 1.0))

    if motos and motos['capacidad_total'] > 0:
        pct_motos = (motos['ocupados'] / motos['capacidad_total']) * 100
        st.markdown(f'<div class="ocupacion-label"><span>🏍️ Motos</span><b>{motos["ocupados"]}/{motos["capacidad_total"]} ({pct_motos:.1f}%)</b></div>', unsafe_allow_html=True)
        st.progress(min(pct_motos / 100, 1.0))

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
            if ayer_count > 0:
                pct = (delta / ayer_count) * 100
                delta_txt = f"{delta:+d} ({pct:+.0f}%)"
            else:
                delta_txt = "Sin datos de ayer"
            st.metric("Entradas hoy", hoy_count, delta_txt)
        with col2:
            st.metric("Entradas ayer", ayer_count)
        with col3:
            total_usuarios = len(obtener_todos_usuarios())
            st.metric("Usuarios totales", total_usuarios)

        st.markdown("---")

        st.markdown("#### 📅 Entradas últimos 7 días")
        hace_7 = hoy - timedelta(days=6)
        df_7d = df[df['fecha'] >= hace_7].copy()

        if not df_7d.empty:
            entradas_por_dia = df_7d.groupby('fecha').size().reset_index(name='entradas')
            todas_fechas = pd.DataFrame({'fecha': pd.date_range(hace_7, hoy).date})
            entradas_por_dia = todas_fechas.merge(entradas_por_dia, on='fecha', how='left').fillna(0)
            entradas_por_dia['fecha_str'] = pd.to_datetime(entradas_por_dia['fecha']).dt.strftime('%d/%m')
            st.bar_chart(entradas_por_dia.set_index('fecha_str')['entradas'])
        else:
            st.caption("Sin entradas en los últimos 7 días.")

        st.markdown("#### ⏰ Horas de mayor demanda (últimos 7 días)")
        if not df_7d.empty:
            df_7d['hora'] = df_7d['hora_entrada'].dt.hour
            horas_pico = df_7d.groupby('hora').size().reset_index(name='entradas')
            todas_horas = pd.DataFrame({'hora': range(6, 22)})
            horas_pico = todas_horas.merge(horas_pico, on='hora', how='left').fillna(0)
            horas_pico['hora_str'] = horas_pico['hora'].apply(lambda h: f"{int(h):02d}:00")
            st.bar_chart(horas_pico.set_index('hora_str')['entradas'])
        else:
            st.caption("Sin datos suficientes.")

        st.markdown("#### 🎓 Top 5 carreras con más uso")
        por_carrera = df[df['carrera'].notna()].groupby('carrera').size().reset_index(name='visitas')
        por_carrera = por_carrera.sort_values('visitas', ascending=False).head(5)
        if not por_carrera.empty:
            por_carrera.columns = ['Carrera', 'Visitas']
            st.dataframe(por_carrera, use_container_width=True, hide_index=True)
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
        st.caption(f"**Total: {len(dentro_list)}** vehículo(s)")
        for v in dentro_list:
            icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
            with st.container(border=True):
                st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
                st.caption(f"Matrícula: {v['matricula'] or 'N/A'} | Entrada: {v['hora_entrada']}")


# =========================================================
# FRAGMENTO: LISTA DE VEHÍCULOS DENTRO
# =========================================================
def _render_lista_vehiculos_dentro(user):
    dentro = obtener_vehiculos_dentro()

    if not dentro:
        st.info("No hay vehículos dentro.")
        return

    st.write(f"**Total: {len(dentro)}**")
    for v in dentro:
        with st.container(border=True):
            icono = "🚗" if v['tipo'] == 'Auto' else "🏍️"
            st.markdown(f"**{icono} {v['placas']}** — {v['nombre_completo']}")
            st.caption(f"Matrícula: {v['matricula'] or 'N/A'}")
            st.caption(f"Entrada: {v['hora_entrada']}")

            if st.button("🚪 Registrar Salida", key=f"sal_{v['id_registro']}", use_container_width=True):
                st.session_state[f"salida_rapida_{v['id_registro']}"] = True
                st.rerun()

        if st.session_state.get(f"salida_rapida_{v['id_registro']}", False):
            st.markdown("#### 📸 Evidencia de salida")
            foto_sal = st.camera_input(f"Evidencia — {v['placas']}", key=f"cam_sal_{v['id_registro']}")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirmar", key=f"conf_sal_{v['id_registro']}", type="primary", use_container_width=True):
                    if not foto_sal:
                        st.error("Toma la foto de evidencia.")
                    else:
                        registrar_salida(v['id_registro'], v['tipo'], user['id'], imagen_a_base64(foto_sal.getvalue()))
                        registrar_log(user['id'], "REGISTRAR_SALIDA",
                                      f"Salida de {v['placas']} ({v['nombre_completo']})",
                                      "Super_Registros", v['id_registro'])
                        st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                        set_flash("success", f"✅ Salida registrada para {v['placas']}.")
                        st.rerun()
            with col_b:
                if st.button("❌ Cancelar", key=f"canc_sal_{v['id_registro']}", use_container_width=True):
                    st.session_state[f"salida_rapida_{v['id_registro']}"] = False
                    st.rerun()


@st.fragment(run_every="10s")
def _render_dentro_auto(user):
    _render_lista_vehiculos_dentro(user)


@st.fragment
def _render_dentro_manual(user):
    _render_lista_vehiculos_dentro(user)


# =========================================================
# PANEL DEL ALUMNO
# =========================================================
def panel_alumno():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">🎓 Alumno — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()
    notificar_entrada_reciente(user)

    with st.expander("👤 Ver mi perfil"):
        st.write(f"**Usuario:** {user['usuario']}")
        st.write(f"**ID Estudiante:** {user['id_estudiante'] or 'N/A'}")
        st.write(f"**Matrícula:** {user['matricula'] or 'N/A'}")
        st.write(f"**Carrera:** {user['carrera'] or 'N/A'}")
        st.write(f"**Grupo:** {user['grupo'] or 'N/A'}")
        st.write(f"**Teléfono:** {user['telefono'] or 'N/A'}")

    mostrar_mi_cuenta(user)

    st.markdown("### 🅿️ Lugares disponibles")
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
                    <p style="font-size: 0.8rem; opacity: 0.8; margin-top: 8px;">
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
                        qr_data = {
                            "id_usuario": user['id'], "usuario": user['usuario'],
                            "nombre": user['nombre_completo'], "id_estudiante": user['id_estudiante'],
                            "matricula": user['matricula'], "carrera": user['carrera'],
                            "grupo": user['grupo'], "id_vehiculo": v['id'],
                            "tipo": v['tipo'], "placas": v['placas']
                        }
                        st.session_state.qr_generado = {"imagen": generar_qr_imagen(qr_data), "vehiculo": v, "datos": qr_data}
                        st.rerun()
                with col2:
                    st.button("🗑️ Borrar", key=f"del_{v['id']}", use_container_width=True,
                              on_click=cb_mostrar_confirm, args=(f"confirmar_elim_veh_{v['id']}",))

                if st.session_state.get(f"confirmar_elim_veh_{v['id']}", False):
                    with st.container(border=True):
                        st.error(f"🚨 ¿Eliminar el vehículo **{v['tipo']} {v['placas']}**?")
                        st.caption("Esta acción es permanente y no se puede deshacer.")
                        col_si, col_no = st.columns(2)
                        with col_si:
                            st.button("✅ Sí, eliminar", key=f"si_del_veh_{v['id']}", type="primary",
                                      use_container_width=True,
                                      on_click=cb_eliminar_vehiculo,
                                      args=(v['id'], user['id'], v['tipo'], v['placas']))
                        with col_no:
                            st.button("❌ Cancelar", key=f"no_del_veh_{v['id']}", use_container_width=True,
                                      on_click=cb_ocultar_confirm, args=(f"confirmar_elim_veh_{v['id']}",))

    with st.expander("📜 Mi historial de visitas"):
        total_visitas, visitas_mes = contar_visitas_usuario(user['id'])
        historial = obtener_historial_usuario(user['id'], limite=50)

        completadas = [h for h in historial if h['hora_salida']]
        prom_str = "N/A"
        if completadas:
            tiempos = [(h['hora_salida'] - h['hora_entrada']).total_seconds() / 60 for h in completadas]
            prom = sum(tiempos) / len(tiempos)
            if prom < 60:
                prom_str = f"{prom:.0f} min"
            else:
                prom_str = f"{prom/60:.1f} hrs"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚗 Visitas totales", total_visitas)
        with col2:
            st.metric("📅 Este mes", visitas_mes)
        with col3:
            st.metric("⏱️ Promedio", prom_str)

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
            st.caption(f"Mostrando **{len(historial_filtrado)}** visita(s) (últimas 50)")

            for h in historial_filtrado:
                fecha_entrada = h['hora_entrada'].strftime("%d/%m/%Y %H:%M") if h['hora_entrada'] else "N/A"
                fecha_salida = h['hora_salida'].strftime("%d/%m/%Y %H:%M") if h['hora_salida'] else None
                icono = "🚗" if h['tipo'] == 'Auto' else "🏍️"
                estado_color = "#00ff88" if h['estado'] == 'DENTRO' else "#A89968"
                estado_txt = "🟢 DENTRO" if h['estado'] == 'DENTRO' else "🔴 COMPLETADA"

                if fecha_salida:
                    duracion = h['hora_salida'] - h['hora_entrada']
                    minutos = int(duracion.total_seconds() / 60)
                    if minutos < 60:
                        duracion_txt = f"{minutos} min"
                    else:
                        duracion_txt = f"{minutos // 60}h {minutos % 60}min"
                else:
                    delta = datetime.now() - h['hora_entrada']
                    minutos = int(delta.total_seconds() / 60)
                    if minutos < 60:
                        duracion_txt = f"{minutos} min (en curso)"
                    else:
                        duracion_txt = f"{minutos // 60}h {minutos % 60}min (en curso)"

                st.markdown(f"""
                    <div class="hist-item" style="border-left-color: {estado_color};">
                        <div style="display:flex; justify-content:space-between; flex-wrap:wrap;">
                            <span style="color:{estado_color}; font-weight:700; font-size:0.85rem;">{estado_txt}</span>
                            <span class="hist-duracion">⏱️ {duracion_txt}</span>
                        </div>
                        <div style="color:#fff; margin-top:4px; font-size:0.9rem;">
                            {icono} <b>{h['placas']}</b>
                            {f" · {h['marca']}" if h['marca'] else ""}
                            {f" · {h['modelo']}" if h['modelo'] else ""}
                        </div>
                        <div style="color:#aaa; font-size:0.8rem; margin-top:2px;">
                            ⬇️ Entrada: {fecha_entrada}
                        </div>
                        {f'<div style="color:#aaa; font-size:0.8rem;">⬆️ Salida: {fecha_salida}</div>' if fecha_salida else ''}
                    </div>
                """, unsafe_allow_html=True)

    with st.expander("➕ Registrar nuevo vehículo"):
        st.markdown("**Tipo de vehículo**")
        tipo = st.selectbox("Tipo de vehículo", ["Auto", "Moto"], key="vh_tipo", label_visibility="collapsed")

        placas = st.text_input("Placas", key="vh_placas", placeholder="Ej. ABC-1234").upper().strip()
        placas_ok = mostrar_validacion(placas, validar_placas, obligatorio=True)

        marca = st.text_input("Marca (opcional)", key="vh_marca")
        modelo = st.text_input("Modelo (opcional)", key="vh_modelo")
        color = st.text_input("Color (opcional)", key="vh_color")

        placas_unicas = True
        if placas and placas_ok:
            placas_limpias_temp = placas.replace("-", "").replace(" ", "").upper()
            if placas_existen(placas_limpias_temp):
                st.markdown('<div class="val-error">❌ Ya existe un vehículo con esas placas</div>', unsafe_allow_html=True)
                placas_unicas = False

        todos_ok = placas_ok and placas_unicas

        if st.button("Registrar vehículo", use_container_width=True, type="primary",
                     disabled=not todos_ok, key="vh_btn"):
            placas_limpias = placas.replace("-", "").replace(" ", "").upper()
            try:
                crear_vehiculo(user['id'], tipo, placas_limpias,
                               marca.strip() if marca else None,
                               modelo.strip() if modelo else None,
                               color.strip() if color else None)
                registrar_log(user['id'], "CREAR_VEHICULO",
                              f"Vehículo {tipo} {placas_limpias} registrado", "Super_Vehiculos")
                limpiar_campos(['vh_placas', 'vh_marca', 'vh_modelo', 'vh_color'])
                set_flash("success", f"✅ Vehículo {placas_limpias} registrado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")

    if st.session_state.qr_generado:
        qr_info = st.session_state.qr_generado
        st.markdown("---")
        st.markdown("### 🎫 Tu código QR")
        st.info("Presenta este código en la caseta al entrar y salir.")

        col_qr1, col_qr2, col_qr3 = st.columns([1, 2, 1])
        with col_qr2:
            st.image(qr_info['imagen'], caption=f"QR — {qr_info['vehiculo']['tipo']} {qr_info['vehiculo']['placas']}")

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            st.download_button(
                "📥 Descargar PNG",
                data=qr_info['imagen'],
                file_name=f"QR_{qr_info['vehiculo']['placas']}.png",
                mime="image/png",
                use_container_width=True
            )

        with col_dl2:
            try:
                pdf_bytes = generar_pdf_qr(user, qr_info['vehiculo'], qr_info['imagen'])
                st.download_button(
                    "📄 Descargar PDF profesional",
                    data=pdf_bytes,
                    file_name=f"CUYPARK_{qr_info['vehiculo']['placas']}_{user['matricula'] or 'alumno'}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")

        if st.button("❌ Cerrar QR", use_container_width=True):
            st.session_state.qr_generado = None
            st.rerun()


# =========================================================
# PANEL DEL TRABAJADOR
# =========================================================
def panel_trabajador():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👷 Caseta — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()

    mostrar_mi_cuenta(user)

    _contadores_caseta()
    st.caption("🟢 Contadores actualizándose cada 15s")

    st.markdown("---")

    seccion = st.radio("Sección:", ["📷 Escanear QR", "📋 Vehículos Dentro"], horizontal=True, label_visibility="collapsed")

    if seccion == "📷 Escanear QR":
        st.markdown("### 1️⃣ Escanea el QR o ingresa las placas")
        foto_qr = st.camera_input("📸 Escanear QR", key="cam_qr")
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
                    st.warning("⚠️ No se pudo leer el QR. Intenta de nuevo o usa entrada manual.")
            except Exception as e:
                st.error(f"Error al leer QR: {e}")

        if placas_manual:
            placas_detectadas = placas_manual

        if placas_detectadas:
            vehiculo = obtener_vehiculo_por_placas(placas_detectadas)
            if not vehiculo:
                st.error(f"❌ No existe vehículo con placas **{placas_detectadas}**.")
            else:
                st.markdown("### 2️⃣ Vehículo encontrado")
                with st.container(border=True):
                    icono = "🚗" if vehiculo['tipo'] == 'Auto' else "🏍️"
                    st.markdown(f"**{icono} {vehiculo['tipo']} — {vehiculo['placas']}**")
                    st.caption(f"Dueño: {vehiculo['nombre_completo']}")
                    st.caption(f"Matrícula: {vehiculo['matricula'] or 'N/A'}")
                    st.caption(f"Carrera: {vehiculo['carrera'] or 'N/A'}")

                registro_activo = obtener_registro_activo_por_vehiculo(vehiculo['id'])

                st.markdown("### 3️⃣ Toma evidencia")
                foto_evidencia = st.camera_input("📸 Evidencia del vehículo", key="cam_evidencia")

                st.markdown("### 4️⃣ Confirma")
                if registro_activo:
                    st.info(f"🟢 Está **DENTRO** desde {registro_activo['hora_entrada']}. Se registrará **SALIDA**.")
                    if st.button("🚪 Registrar SALIDA", type="primary", use_container_width=True):
                        if not foto_evidencia:
                            st.error("Debes tomar una foto de evidencia.")
                        else:
                            registrar_salida(registro_activo['id'], vehiculo['tipo'], user['id'], imagen_a_base64(foto_evidencia.getvalue()))
                            registrar_log(user['id'], "REGISTRAR_SALIDA",
                                          f"Salida de {vehiculo['placas']} ({vehiculo['nombre_completo']})",
                                          "Super_Registros", registro_activo['id'])
                            set_flash("success", f"✅ Salida registrada para {vehiculo['placas']}.")
                            st.rerun()
                else:
                    st.info(f"🔵 NO está dentro. Se registrará **ENTRADA**.")
                    if st.button("🚗 Registrar ENTRADA", type="primary", use_container_width=True):
                        if not foto_evidencia:
                            st.error("Debes tomar una foto de evidencia.")
                        else:
                            registrar_entrada(vehiculo['id_usuario'], vehiculo['id'], vehiculo['tipo'], user['id'], imagen_a_base64(foto_evidencia.getvalue()))
                            registrar_log(user['id'], "REGISTRAR_ENTRADA",
                                          f"Entrada de {vehiculo['placas']} ({vehiculo['nombre_completo']})",
                                          "Super_Registros")
                            set_flash("success", f"✅ Entrada registrada para {vehiculo['placas']}.")
                            st.rerun()

    else:
        st.markdown("### 🚘 Vehículos dentro")

        auto_refresh = st.toggle(
            "🔄 Auto-actualizar cada 10 segundos",
            value=False,
            key="auto_refresh_caseta",
            help="La lista se actualizará sola para mostrar nuevos vehículos que entren."
        )

        salida_en_curso = any(
            k.startswith("salida_rapida_") and v
            for k, v in st.session_state.items()
        )

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


# =========================================================
# PANEL DEL ADMINISTRADOR
# =========================================================
def panel_admin():
    user = st.session_state.usuario
    st.markdown(f'<div class="panel-header">👑 Admin — {user["nombre_completo"]}</div>', unsafe_allow_html=True)
    mostrar_flash()

    seccion = st.radio(
        "Sección:",
        ["📊 Dashboard", "👥 Usuarios", "📋 Registros", "📈 Métricas", "🔍 Auditoría", "🔧 Mi Cuenta"],
        horizontal=True, label_visibility="collapsed"
    )

    if seccion == "📊 Dashboard":
        st.markdown("### 📊 Estado actual del estacionamiento")
        st.caption("🟢 Datos actualizándose en tiempo real (cada 15s)")
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

            col_a, col_b = st.columns(2)
            with col_a:
                mat = st.text_input("Matrícula (opcional)", key="ca_mat")
                mat_ok = mostrar_validacion(mat, validar_matricula, obligatorio=False)

                car = st.text_input("Carrera (opcional)", key="ca_car")
                car_ok = mostrar_validacion(car, validar_carrera, obligatorio=False)
            with col_b:
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
                    crear_usuario(
                        usuario=u.lower().strip(), password=p, rol='alumno',
                        tipo_usuario='alumno', nombre_completo=nombre.strip(),
                        matricula=mat.strip() if mat else None,
                        carrera=car.strip() if car else None,
                        grupo=gru.strip() if gru else None,
                        telefono=tel.strip() if tel else None,
                        id_estudiante=id_est.strip() if id_est else None
                    )
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
                    crear_usuario(
                        usuario=u.lower().strip(), password=p, rol='trabajador',
                        tipo_usuario='administrativo', nombre_completo=nombre.strip(),
                        telefono=tel.strip() if tel else None
                    )
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
                    crear_usuario(
                        usuario=u.lower().strip(), password=p, rol='admin',
                        tipo_usuario='administrativo', nombre_completo=nombre.strip(),
                        telefono=tel.strip() if tel else None
                    )
                    registrar_log(user['id'], "CREAR_ADMIN",
                                  f"Administrador @{u.lower().strip()} ({nombre}) creado", "Super_Usuarios")
                    limpiar_campos(['cA_u', 'cA_p', 'cA_n', 'cA_tel'])
                    set_flash("success", f"✅ Administrador **{nombre}** creado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        elif sub == "📋 Ver Todos":
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                filtro = st.selectbox("Filtrar por rol", ["Todos", "alumno", "trabajador", "admin"])
            with col_f2:
                solo_activos = st.checkbox("Solo activos", value=False)

            usuarios = obtener_todos_usuarios(None if filtro == "Todos" else filtro, solo_activos=solo_activos)

            if not usuarios:
                st.info("No hay usuarios que coincidan con el filtro.")
            else:
                activos_count = sum(1 for u in usuarios if u['activo'])
                inactivos_count = len(usuarios) - activos_count
                st.write(f"**Total: {len(usuarios)}** ({activos_count} activos, {inactivos_count} inactivos)")

                for u in usuarios:
                    with st.container(border=True):
                        icono = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}.get(u['rol'], '👤')
                        estado_badge = "🟢" if u['activo'] else "🔒"

                        col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1])
                        with col1:
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
                                st.caption("🔒 **Cuenta desactivada** — no puede iniciar sesión")
                            if bloqueado_activo:
                                st.caption(f"🔐 **Cuenta bloqueada** por intentos fallidos — desbloqueo en {mins_bloqueo} min")
                            intentos = u.get('intentos_fallidos') or 0
                            if intentos > 0 and not bloqueado_activo:
                                st.caption(f"⚠️ Intentos fallidos recientes: {intentos}/5")
                            if u['id_estudiante']:
                                st.caption(f"ID: {u['id_estudiante']}")
                            st.caption(f"Rol: {u['rol']} | Teléfono: {u['telefono'] or 'N/A'}")
                            if u['rol'] == 'alumno':
                                st.caption(f"Matrícula: {u['matricula'] or 'N/A'} | Carrera: {u['carrera'] or 'N/A'}")
                        with col2:
                            if st.button("✏️", key=f"edit_{u['id']}", help="Editar", use_container_width=True):
                                for other in usuarios:
                                    if other['id'] != u['id']:
                                        st.session_state[f"editando_{other['id']}"] = False
                                st.session_state[f"editando_{u['id']}"] = not st.session_state.get(f"editando_{u['id']}", False)
                                st.rerun()
                        with col3:
                            if u['id'] == user['id']:
                                st.caption("(Tú)")
                            else:
                                if u['activo']:
                                    st.button("🔒", key=f"lock_{u['id']}", help="Desactivar cuenta", use_container_width=True,
                                              on_click=cb_mostrar_confirm, args=(f"confirmar_desactivar_{u['id']}",))
                                else:
                                    st.button("🔓", key=f"unlock_{u['id']}", help="Reactivar cuenta", use_container_width=True,
                                              on_click=cb_activar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                        with col4:
                            if u['id'] != user['id']:
                                st.button("🗑️", key=f"del_user_{u['id']}", help="Eliminar (permanente)", use_container_width=True,
                                          on_click=cb_mostrar_confirm, args=(f"confirmar_eliminar_{u['id']}",))
                        with col5:
                            bloqueado_boton = False
                            if u.get('bloqueado_hasta') and isinstance(u['bloqueado_hasta'], datetime):
                                if u['bloqueado_hasta'] > datetime.now():
                                    bloqueado_boton = True

                            if u['id'] == user['id']:
                                st.caption("")
                            elif bloqueado_boton:
                                if st.button("🔐", key=f"unlock_bloq_{u['id']}",
                                             help="Desbloquear cuenta (intentos fallidos)",
                                             use_container_width=True):
                                    ok, msg = desbloquear_usuario(u['id'])
                                    if ok:
                                        registrar_log(user['id'], "DESBLOQUEAR_USUARIO",
                                                      f"Cuenta @{u['usuario']} desbloqueada por @{user['usuario']}",
                                                      "Super_Usuarios", u['id'])
                                        set_flash("success", msg)
                                    else:
                                        set_flash("error", msg)
                                    st.rerun()
                            else:
                                st.caption("")

                        if st.session_state.get(f"confirmar_eliminar_{u['id']}", False):
                            with st.container(border=True):
                                st.error(f"🚨 ¿Eliminar **permanentemente** a **{u['nombre_completo']}** (@{u['usuario']})?")
                                st.caption("Esta acción no se puede deshacer y borrará la cuenta del sistema.")

                                # 🔒 Doble confirmación SOLO para admins
                                if u['rol'] == 'admin':
                                    st.warning("⚠️ **Estás a punto de eliminar a un ADMINISTRADOR.** Esta acción es crítica.")
                                    texto_confirmacion = st.text_input(
                                        "Escribe **ELIMINAR** (en mayúsculas) para habilitar el botón:",
                                        key=f"confirma_texto_{u['id']}",
                                        placeholder="ELIMINAR",
                                        label_visibility="visible"
                                    )
                                    confirmacion_ok = (texto_confirmacion.strip() == "ELIMINAR")
                                    if not confirmacion_ok and texto_confirmacion:
                                        st.markdown('<div class="val-error">❌ Debes escribir exactamente ELIMINAR (en mayúsculas)</div>', unsafe_allow_html=True)
                                else:
                                    confirmacion_ok = True

                                col_si, col_no = st.columns(2)
                                with col_si:
                                    st.button("✅ Sí, eliminar", key=f"si_del_{u['id']}", type="primary",
                                              use_container_width=True,
                                              disabled=not confirmacion_ok,
                                              on_click=cb_eliminar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                                with col_no:
                                    st.button("❌ Cancelar", key=f"no_del_{u['id']}", use_container_width=True,
                                              on_click=cb_ocultar_confirm, args=(f"confirmar_eliminar_{u['id']}",))

                        if st.session_state.get(f"confirmar_desactivar_{u['id']}", False):
                            with st.container(border=True):
                                st.warning(f"🔒 ¿Desactivar la cuenta de **{u['nombre_completo']}** (@{u['usuario']})?")
                                st.caption("El usuario no podrá iniciar sesión, pero sus datos e historial se conservan.")
                                col_si, col_no = st.columns(2)
                                with col_si:
                                    st.button("✅ Sí, desactivar", key=f"si_desc_{u['id']}", type="primary",
                                              use_container_width=True,
                                              on_click=cb_desactivar_usuario,
                                              args=(u['id'], user['id'], user['usuario'], u['usuario'], u['nombre_completo']))
                                with col_no:
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
                            col_a, col_b = st.columns(2)
                            with col_a:
                                ed_id = st.text_input("ID Estudiante", value=u['id_estudiante'] or "", key=f"ed_id_{u['id']}")
                                ed_id_ok = mostrar_validacion(ed_id, validar_id_estudiante, obligatorio=False)

                                ed_mat = st.text_input("Matrícula", value=u['matricula'] or "", key=f"ed_mat_{u['id']}")
                                ed_mat_ok = mostrar_validacion(ed_mat, validar_matricula, obligatorio=False)
                            with col_b:
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

                        pass_ok = True
                        pass_msg = ""
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

                        col_x, col_y = st.columns(2)
                        with col_x:
                            if st.button("💾 Guardar", use_container_width=True, type="primary",
                                         disabled=not todos_ok, key=f"ed_save_{u['id']}"):
                                try:
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
                                        nueva_password=ed_pass if ed_pass else None
                                    )
                                    detalle = f"Usuario @{u['usuario']} editado"
                                    if cambios: detalle += " — " + "; ".join(cambios)
                                    registrar_log(user['id'], "EDITAR_USUARIO", detalle, "Super_Usuarios", u['id'])
                                    st.session_state[f"editando_{u['id']}"] = False
                                    limpiar_campos([f"ed_n_{u['id']}", f"ed_tel_{u['id']}", f"ed_id_{u['id']}",
                                                    f"ed_mat_{u['id']}", f"ed_car_{u['id']}", f"ed_gru_{u['id']}",
                                                    f"ed_p_{u['id']}", f"ed_p2_{u['id']}"])
                                    set_flash("success", f"✅ Usuario **{ed_nombre}** actualizado correctamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar: {e}")
                        with col_y:
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
        registros = obtener_todos_los_registros(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        if not registros:
            st.info("No hay registros en el rango seleccionado.")
        else:
            col1, col2 = st.columns(2)
            with col1: filtro_estado = st.selectbox("Estado", ["Todos", "DENTRO", "FUERA"])
            with col2: filtro_tipo = st.selectbox("Tipo", ["Todos", "Auto", "Moto"])
            buscar = st.text_input("🔍 Buscar (nombre, placas, matrícula)").lower().strip()
            filtrados = registros
            if filtro_estado != "Todos": filtrados = [r for r in filtrados if r['estado'] == filtro_estado]
            if filtro_tipo != "Todos": filtrados = [r for r in filtrados if r['tipo'] == filtro_tipo]
            if buscar:
                filtrados = [r for r in filtrados if
                             buscar in (r['nombre_completo'] or '').lower() or
                             buscar in (r['placas'] or '').lower() or
                             buscar in (r['matricula'] or '').lower()]
            st.write(f"**Mostrando {len(filtrados)} registro(s)**")
            df_export = pd.DataFrame([{
                'ID': r['id'], 'Estado': r['estado'], 'Alumno': r['nombre_completo'],
                'Matrícula': r['matricula'], 'Carrera': r['carrera'],
                'Tipo': r['tipo'], 'Placas': r['placas'],
                'Fecha Entrada': r['hora_entrada'].strftime("%d/%m/%Y") if r['hora_entrada'] else "",
                'Hora Entrada': r['hora_entrada'].strftime("%H:%M:%S") if r['hora_entrada'] else "",
                'Fecha Salida': r['hora_salida'].strftime("%d/%m/%Y") if r['hora_salida'] else "En curso",
                'Hora Salida': r['hora_salida'].strftime("%H:%M:%S") if r['hora_salida'] else ""
            } for r in filtrados])

            if fecha_desde and fecha_hasta:
                rango_txt = f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}"
            else:
                rango_txt = "Período: Todo el historial"

            excel_data = exportar_excel_profesional(df_export, "Reporte de Registros de Estacionamiento",
                                                    f"{rango_txt} | Total: {len(filtrados)} registro(s)")
            st.download_button("📊 Exportar Reporte Excel", data=excel_data,
                               file_name=f"registros_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True, type="primary")
            st.markdown("---")
            for r in filtrados:
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

    elif seccion == "📈 Métricas":
        st.markdown("### 📈 Métricas y patrones de uso")
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
                col1, col2 = st.columns(2)
                with col1:
                    ap = completados[completados['tipo'] == 'Auto']['duracion_min'].mean()
                    if pd.notna(ap): st.metric("🚗 Autos", f"{ap:.1f} min")
                with col2:
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

        col1, col2 = st.columns(2)
        with col1:
            acciones = ["Todas"] + obtener_acciones_unicas()
            filtro_accion = st.selectbox("Filtrar por acción", acciones)
        with col2:
            buscar = st.text_input("🔍 Buscar (usuario o detalle)").lower().strip()

        logs = obtener_logs(limite=500, filtro_accion=filtro_accion, buscar=buscar if buscar else None,
                            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        if not logs:
            st.info("No hay logs que coincidan con los filtros.")
        else:
            st.write(f"**Mostrando {len(logs)} registro(s)** (máximo 500)")
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

            if fecha_desde and fecha_hasta:
                rango_txt = f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}"
            else:
                rango_txt = "Período: Todo el historial"

            excel_data = exportar_excel_profesional(df_logs, "Reporte de Auditoría del Sistema",
                                                    f"{rango_txt} | Total: {len(logs)} evento(s)")
            st.download_button("📊 Exportar Reporte Excel", data=excel_data,
                               file_name=f"auditoria_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True, type="primary")
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


# =========================================================
# ENRUTADOR
# =========================================================
if st.session_state.usuario is not None:
    rol = st.session_state.usuario['rol']
    iconos = {'alumno': '🎓', 'trabajador': '👷', 'admin': '👑'}

    col_user, col_brand, col_salir = st.columns([3, 2, 1])

    with col_user:
        st.markdown(
            f"<div style='padding-top: 10px; color: #C9A961;'>"
            f"<b>{iconos.get(rol, '👤')} @{st.session_state.usuario['usuario']}</b>"
            f"</div>",
            unsafe_allow_html=True
        )
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