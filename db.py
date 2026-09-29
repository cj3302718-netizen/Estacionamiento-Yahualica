import streamlit as st
import pyodbc
import bcrypt
import qrcode
import json
import base64
import cv2
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO


# --- CONEXIÓN ---
def init_connection():
    drivers = pyodbc.drivers()
    if "ODBC Driver 17 for SQL Server" in drivers:
        driver = "ODBC Driver 17 for SQL Server"
    elif "ODBC Driver 18 for SQL Server" in drivers:
        driver = "ODBC Driver 18 for SQL Server"
    else:
        driver = "SQL Server"

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={st.secrets['server']};"
        f"DATABASE={st.secrets['database']};"
        f"UID={st.secrets['username']};"
        f"PWD={st.secrets['password']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


def ejecutar_query(query, params=(), fetch=False):
    conn = init_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            columnas = [c[0] for c in cursor.description]
            resultado = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
            cursor.close()
            return resultado
        conn.commit()
        cursor.close()
        return None
    finally:
        conn.close()


# --- CONTRASEÑAS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# --- AUDITORÍA ---
def registrar_log(id_usuario, accion, detalles="", tabla_afectada=None, id_afectado=None):
    try:
        ejecutar_query(
            """INSERT INTO Super_Logs (id_usuario, accion, detalles, tabla_afectada, id_afectado)
               VALUES (?, ?, ?, ?, ?)""",
            (id_usuario, accion, detalles[:500], tabla_afectada, id_afectado)
        )
    except Exception:
        pass


def obtener_logs(limite=200, filtro_accion=None, buscar=None, fecha_desde=None, fecha_hasta=None):
    condiciones = []
    params = []
    if filtro_accion and filtro_accion != "Todas":
        condiciones.append("l.accion = ?")
        params.append(filtro_accion)
    if buscar:
        condiciones.append("(l.detalles LIKE ? OR u.usuario LIKE ? OR u.nombre_completo LIKE ?)")
        like = f"%{buscar}%"
        params.extend([like, like, like])
    if fecha_desde:
        condiciones.append("CAST(l.fecha AS DATE) >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("CAST(l.fecha AS DATE) <= ?")
        params.append(fecha_hasta)
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    return ejecutar_query(
        f"""SELECT TOP {limite}
                  l.id, l.accion, l.detalles, l.tabla_afectada, l.id_afectado, l.fecha,
                  u.usuario AS usuario_accion, u.nombre_completo AS nombre_accion, u.rol AS rol_accion
           FROM Super_Logs l
           LEFT JOIN Super_Usuarios u ON l.id_usuario = u.id
           {where}
           ORDER BY l.fecha DESC""",
        tuple(params), fetch=True
    )


def obtener_acciones_unicas():
    res = ejecutar_query("SELECT DISTINCT accion FROM Super_Logs ORDER BY accion", fetch=True)
    return [r['accion'] for r in res] if res else []


def contar_logs():
    res = ejecutar_query("SELECT COUNT(*) AS t FROM Super_Logs", fetch=True)
    return res[0]['t'] if res else 0


# --- USUARIOS ---
def obtener_usuario(usuario):
    res = ejecutar_query("SELECT * FROM Super_Usuarios WHERE usuario = ?", (usuario,), fetch=True)
    return res[0] if res else None


def usuario_existe(usuario):
    return obtener_usuario(usuario) is not None


def crear_usuario(usuario, password, rol, tipo_usuario, nombre_completo,
                  matricula=None, carrera=None, grupo=None, telefono=None, id_estudiante=None):
    hashed = hash_password(password)
    query = """
        INSERT INTO Super_Usuarios
        (usuario, password, rol, tipo_usuario, nombre_completo, matricula, carrera, grupo, telefono, id_estudiante, activo, intentos_fallidos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
    """
    ejecutar_query(query, (usuario, hashed, rol, tipo_usuario, nombre_completo,
                           matricula, carrera, grupo, telefono, id_estudiante))


# =========================================================
# AUTENTICACIÓN CON BLOQUEO POR INTENTOS FALLIDOS
# =========================================================
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10


def autenticar(usuario, password):
    """Verifica credenciales con bloqueo tras 5 intentos fallidos (admins exentos)."""
    user = obtener_usuario(usuario)
    if not user:
        return None, "Usuario o contraseña incorrectos"

    es_admin = (user.get('rol') == 'admin')

    # --- 1. Verificar si está bloqueado (solo no-admins) ---
    if not es_admin:
        bloqueado_hasta = user.get('bloqueado_hasta')
        if bloqueado_hasta and isinstance(bloqueado_hasta, datetime):
            if bloqueado_hasta > datetime.now():
                minutos_restantes = int((bloqueado_hasta - datetime.now()).total_seconds() / 60) + 1
                return None, f"🔒 Cuenta bloqueada por seguridad. Intenta de nuevo en {minutos_restantes} min."
            else:
                ejecutar_query(
                    "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
                    (user['id'],)
                )
                user['intentos_fallidos'] = 0
                user['bloqueado_hasta'] = None

    # --- 2. Verificar contraseña ---
    if not verificar_password(password, user['password']):
        if es_admin:
            return None, "Usuario o contraseña incorrectos"
        else:
            intentos_actuales = (user.get('intentos_fallidos') or 0) + 1

            if intentos_actuales >= MAX_INTENTOS:
                bloqueado_hasta = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)
                ejecutar_query(
                    "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = ? WHERE id = ?",
                    (bloqueado_hasta, user['id'])
                )
                return None, f"🔒 Cuenta bloqueada por {MINUTOS_BLOQUEO} minutos tras {MAX_INTENTOS} intentos fallidos."
            else:
                ejecutar_query(
                    "UPDATE Super_Usuarios SET intentos_fallidos = ? WHERE id = ?",
                    (intentos_actuales, user['id'])
                )
                restantes = MAX_INTENTOS - intentos_actuales
                return None, f"Usuario o contraseña incorrectos. Te quedan {restantes} intento(s) antes del bloqueo."

    # --- 3. Contraseña correcta: resetear contadores ---
    ejecutar_query(
        "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (user['id'],)
    )

    # --- 4. Verificar si está activo ---
    activo = user.get('activo')
    if activo is None or activo in (0, False):
        return None, "🔒 Tu cuenta está desactivada. Contacta al administrador."

    return user, None


def contar_admins():
    res = ejecutar_query(
        "SELECT COUNT(*) AS total FROM Super_Usuarios WHERE rol = 'admin' AND activo = 1",
        fetch=True
    )
    return res[0]['total'] if res else 0


def desbloquear_usuario(id_usuario):
    """Función auxiliar para que el admin pueda desbloquear manualmente."""
    ejecutar_query(
        "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (id_usuario,)
    )
    return True, "Cuenta desbloqueada correctamente."


# --- IDs ---
def generar_siguiente_id(prefijo="ALU"):
    res = ejecutar_query(
        """SELECT id_estudiante FROM Super_Usuarios 
           WHERE id_estudiante LIKE ? AND rol = 'alumno'""",
        (f"{prefijo}-%",), fetch=True
    )
    if not res:
        return f"{prefijo}-0001"
    numeros = []
    for r in res:
        try:
            if r['id_estudiante']:
                num = int(r['id_estudiante'].split('-')[1])
                numeros.append(num)
        except (ValueError, IndexError):
            continue
    if not numeros:
        return f"{prefijo}-0001"
    return f"{prefijo}-{max(numeros) + 1:04d}"


def id_estudiante_existe(id_estudiante):
    if not id_estudiante:
        return False
    res = ejecutar_query("SELECT id FROM Super_Usuarios WHERE id_estudiante = ?",
                         (id_estudiante,), fetch=True)
    return len(res) > 0


def id_estudiante_existe_otro(id_estudiante, id_usuario_excluir):
    if not id_estudiante:
        return False
    res = ejecutar_query(
        "SELECT id FROM Super_Usuarios WHERE id_estudiante = ? AND id != ?",
        (id_estudiante, id_usuario_excluir), fetch=True
    )
    return len(res) > 0


# --- ACTUALIZACIÓN Y BLOQUEO ---
def actualizar_usuario(id_usuario, nombre_completo, telefono=None, matricula=None,
                       carrera=None, grupo=None, id_estudiante=None,
                       tipo_usuario=None, nueva_password=None):
    if nueva_password:
        hashed = hash_password(nueva_password)
        query = """UPDATE Super_Usuarios 
                   SET nombre_completo = ?, telefono = ?, matricula = ?, carrera = ?, 
                       grupo = ?, id_estudiante = ?, tipo_usuario = ?, password = ?,
                       intentos_fallidos = 0, bloqueado_hasta = NULL
                   WHERE id = ?"""
        ejecutar_query(query, (nombre_completo, telefono, matricula, carrera,
                               grupo, id_estudiante, tipo_usuario, hashed, id_usuario))
    else:
        query = """UPDATE Super_Usuarios 
                   SET nombre_completo = ?, telefono = ?, matricula = ?, carrera = ?, 
                       grupo = ?, id_estudiante = ?, tipo_usuario = ?
                   WHERE id = ?"""
        ejecutar_query(query, (nombre_completo, telefono, matricula, carrera,
                               grupo, id_estudiante, tipo_usuario, id_usuario))


def activar_usuario(id_usuario):
    ejecutar_query(
        "UPDATE Super_Usuarios SET activo = 1, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (id_usuario,)
    )
    return True, "Usuario activado correctamente."


def desactivar_usuario(id_usuario):
    res = ejecutar_query("SELECT rol FROM Super_Usuarios WHERE id = ?", (id_usuario,), fetch=True)
    if res and res[0]['rol'] == 'admin':
        admins_activos = ejecutar_query(
            "SELECT COUNT(*) AS t FROM Super_Usuarios WHERE rol = 'admin' AND activo = 1",
            fetch=True
        )[0]['t']
        if admins_activos <= 1:
            return False, "No puedes desactivar al último administrador activo."
    ejecutar_query("UPDATE Super_Usuarios SET activo = 0 WHERE id = ?", (id_usuario,))
    return True, "Usuario desactivado correctamente."


# --- GESTIÓN ---
def obtener_todos_usuarios(filtro_rol=None, solo_activos=False):
    condiciones = []
    params = []
    if filtro_rol:
        condiciones.append("rol = ?")
        params.append(filtro_rol)
    if solo_activos:
        condiciones.append("activo = 1")
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    return ejecutar_query(
        f"""SELECT id, usuario, rol, tipo_usuario, nombre_completo, 
                  matricula, carrera, grupo, telefono, id_estudiante, fecha_registro, activo,
                  intentos_fallidos, bloqueado_hasta
           FROM Super_Usuarios {where} ORDER BY fecha_registro DESC""",
        tuple(params), fetch=True
    )


def eliminar_usuario(id_usuario):
    tiene_vehiculos = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Vehiculos WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']
    tiene_registros = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Registros WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']

    if tiene_vehiculos > 0 or tiene_registros > 0:
        return False, f"No se puede eliminar: tiene {tiene_vehiculos} vehículo(s) y {tiene_registros} registro(s). Te recomendamos desactivarlo."

    ejecutar_query("DELETE FROM Super_Usuarios WHERE id = ?", (id_usuario,))
    return True, "Usuario eliminado correctamente."


# --- VEHÍCULOS ---
def obtener_vehiculos_de_usuario(id_usuario):
    return ejecutar_query("SELECT * FROM Super_Vehiculos WHERE id_usuario = ?",
                          (id_usuario,), fetch=True)


def placas_existen(placas):
    res = ejecutar_query("SELECT id FROM Super_Vehiculos WHERE placas = ?", (placas,), fetch=True)
    return len(res) > 0


def crear_vehiculo(id_usuario, tipo, placas, marca=None, modelo=None, color=None):
    ejecutar_query(
        """INSERT INTO Super_Vehiculos (id_usuario, tipo, placas, marca, modelo, color)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (id_usuario, tipo, placas, marca, modelo, color)
    )


def eliminar_vehiculo(id_vehiculo):
    tiene_registros = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Registros WHERE id_vehiculo = ?",
        (id_vehiculo,), fetch=True
    )[0]['t']
    if tiene_registros > 0:
        return False, f"No se puede eliminar: el vehículo tiene {tiene_registros} registro(s) de entrada/salida asociados. Se conserva por integridad del historial."

    ejecutar_query("DELETE FROM Super_Vehiculos WHERE id = ?", (id_vehiculo,))
    return True, "Vehículo eliminado correctamente."


# --- ESPACIOS ---
def obtener_espacios():
    return ejecutar_query("SELECT * FROM Super_Espacios", fetch=True)


# --- REGISTROS ---
def obtener_registro_activo_de_usuario(id_usuario):
    res = ejecutar_query(
        """SELECT r.*, v.tipo, v.placas FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           WHERE r.id_usuario = ? AND r.estado = 'DENTRO'""",
        (id_usuario,), fetch=True
    )
    return res[0] if res else None


def obtener_todos_los_registros(fecha_desde=None, fecha_hasta=None):
    condiciones = []
    params = []
    if fecha_desde:
        condiciones.append("CAST(r.hora_entrada AS DATE) >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("CAST(r.hora_entrada AS DATE) <= ?")
        params.append(fecha_hasta)
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    return ejecutar_query(
        f"""SELECT r.id, r.hora_entrada, r.hora_salida, r.estado,
                  r.evidencia_entrada, r.evidencia_salida,
                  v.tipo, v.placas, v.marca, v.modelo,
                  u.nombre_completo, u.matricula, u.carrera, u.grupo, u.id_estudiante
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           {where}
           ORDER BY r.hora_entrada DESC""",
        tuple(params), fetch=True
    )


# --- QR ---
def generar_qr_imagen(data_dict):
    texto = json.dumps(data_dict, ensure_ascii=False)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# --- CASETA ---
def obtener_vehiculo_por_placas(placas):
    res = ejecutar_query(
        """SELECT v.*, u.usuario, u.nombre_completo, u.matricula, 
                  u.id_estudiante, u.carrera, u.grupo, u.telefono
           FROM Super_Vehiculos v
           INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
           WHERE v.placas = ?""",
        (placas,), fetch=True
    )
    return res[0] if res else None


def obtener_registro_activo_por_vehiculo(id_vehiculo):
    res = ejecutar_query(
        "SELECT * FROM Super_Registros WHERE id_vehiculo = ? AND estado = 'DENTRO'",
        (id_vehiculo,), fetch=True
    )
    return res[0] if res else None


def registrar_entrada(id_usuario, id_vehiculo, tipo, id_trabajador, evidencia_b64):
    ejecutar_query(
        """INSERT INTO Super_Registros 
           (id_usuario, id_vehiculo, estado, id_trabajador_entrada, evidencia_entrada)
           VALUES (?, ?, 'DENTRO', ?, ?)""",
        (id_usuario, id_vehiculo, id_trabajador, evidencia_b64)
    )
    ejecutar_query("UPDATE Super_Espacios SET ocupados = ocupados + 1 WHERE tipo = ?", (tipo,))


def registrar_salida(id_registro, tipo, id_trabajador, evidencia_b64):
    ejecutar_query(
        """UPDATE Super_Registros 
           SET hora_salida = GETDATE(), estado = 'FUERA',
               id_trabajador_salida = ?, evidencia_salida = ?
           WHERE id = ?""",
        (id_trabajador, evidencia_b64, id_registro)
    )
    ejecutar_query(
        "UPDATE Super_Espacios SET ocupados = ocupados - 1 WHERE tipo = ? AND ocupados > 0",
        (tipo,)
    )


def obtener_vehiculos_dentro():
    return ejecutar_query(
        """SELECT r.id AS id_registro, r.hora_entrada, v.placas, v.tipo,
                  u.nombre_completo, u.matricula, u.carrera, u.id_estudiante
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           WHERE r.estado = 'DENTRO' ORDER BY r.hora_entrada DESC""",
        fetch=True
    )


def decodificar_qr_de_imagen(imagen_bytes):
    try:
        arr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        return data if data else None
    except Exception:
        return None


def imagen_a_base64(imagen_bytes):
    return base64.b64encode(imagen_bytes).decode('utf-8')


def base64_a_bytes(b64_str):
    try:
        return base64.b64decode(b64_str)
    except Exception:
        return None


# --- HISTORIAL PERSONAL DEL ALUMNO ---
def obtener_historial_usuario(id_usuario, limite=50):
    return ejecutar_query(
        f"""SELECT TOP {limite}
                  r.id, r.hora_entrada, r.hora_salida, r.estado,
                  v.tipo, v.placas, v.marca, v.modelo
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           WHERE r.id_usuario = ?
           ORDER BY r.hora_entrada DESC""",
        (id_usuario,), fetch=True
    )


def contar_visitas_usuario(id_usuario):
    res = ejecutar_query(
        """SELECT 
              COUNT(*) AS total,
              SUM(CASE WHEN MONTH(hora_entrada) = MONTH(GETDATE()) 
                       AND YEAR(hora_entrada) = YEAR(GETDATE()) 
                       THEN 1 ELSE 0 END) AS este_mes
           FROM Super_Registros
           WHERE id_usuario = ?""",
        (id_usuario,), fetch=True
    )
    if res:
        return res[0]['total'] or 0, res[0]['este_mes'] or 0
    return 0, 0


# --- CAMBIO DE CONTRASEÑA (auto-servicio) ---
def cambiar_password_usuario(id_usuario, password_actual, password_nueva):
    """Cambia la contraseña de un usuario. Verifica la actual primero."""
    user = ejecutar_query(
        "SELECT password FROM Super_Usuarios WHERE id = ?",
        (id_usuario,), fetch=True
    )
    if not user:
        return False, "Usuario no encontrado."

    hashed_actual = user[0]['password']

    if not verificar_password(password_actual, hashed_actual):
        return False, "La contraseña actual es incorrecta."

    if verificar_password(password_nueva, hashed_actual):
        return False, "La nueva contraseña no puede ser igual a la actual."

    hashed_nueva = hash_password(password_nueva)
    ejecutar_query(
        "UPDATE Super_Usuarios SET password = ?, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (hashed_nueva, id_usuario)
    )
    return True, "Contraseña actualizada correctamente."


# --- ACTUALIZAR TELÉFONO (auto-servicio) ---
def actualizar_telefono_usuario(id_usuario, telefono):
    """Permite al usuario actualizar su propio teléfono."""
    ejecutar_query(
        "UPDATE Super_Usuarios SET telefono = ? WHERE id = ?",
        (telefono, id_usuario)
    )
    return True, "Teléfono actualizado correctamente."