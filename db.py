import streamlit as st
import pyodbc
import bcrypt
import qrcode
import json
import base64
import cv2
import numpy as np
from io import BytesIO


# --- CONEXIÓN A LA BASE DE DATOS (detecta el driver automáticamente) ---
@st.cache_resource
def init_connection():
    drivers = pyodbc.drivers()

    # Buscamos el mejor driver disponible
    if "ODBC Driver 18 for SQL Server" in drivers:
        driver = "ODBC Driver 18 for SQL Server"
    elif "ODBC Driver 17 for SQL Server" in drivers:
        driver = "ODBC Driver 17 for SQL Server"
    else:
        driver = "SQL Server"  # Fallback

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={st.secrets['server']};"
        f"DATABASE={st.secrets['database']};"
        f"UID={st.secrets['username']};"
        f"PWD={st.secrets['password']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


# --- FUNCIÓN GENÉRICA PARA EJECUTAR QUERIES ---
def ejecutar_query(query, params=(), fetch=False):
    conn = init_connection()
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


# --- CONTRASEÑAS (bcrypt) ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# --- USUARIOS ---
def obtener_usuario(usuario):
    res = ejecutar_query(
        "SELECT * FROM Super_Usuarios WHERE usuario = ?",
        (usuario,),
        fetch=True
    )
    return res[0] if res else None


def usuario_existe(usuario):
    return obtener_usuario(usuario) is not None


def crear_usuario(usuario, password, rol, tipo_usuario, nombre_completo,
                  matricula=None, carrera=None, grupo=None, telefono=None, id_estudiante=None):
    hashed = hash_password(password)
    query = """
        INSERT INTO Super_Usuarios
        (usuario, password, rol, tipo_usuario, nombre_completo, matricula, carrera, grupo, telefono, id_estudiante)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    ejecutar_query(query, (usuario, hashed, rol, tipo_usuario, nombre_completo,
                           matricula, carrera, grupo, telefono, id_estudiante))


def autenticar(usuario, password):
    user = obtener_usuario(usuario)
    if not user:
        return None
    if verificar_password(password, user['password']):
        return user
    return None


def contar_admins():
    res = ejecutar_query(
        "SELECT COUNT(*) AS total FROM Super_Usuarios WHERE rol = 'admin'",
        fetch=True
    )
    return res[0]['total'] if res else 0


# --- GESTIÓN DE USUARIOS ---
def obtener_todos_usuarios(filtro_rol=None):
    if filtro_rol:
        return ejecutar_query(
            """SELECT id, usuario, rol, tipo_usuario, nombre_completo, 
                      matricula, carrera, grupo, telefono, id_estudiante, fecha_registro
               FROM Super_Usuarios WHERE rol = ? ORDER BY fecha_registro DESC""",
            (filtro_rol,),
            fetch=True
        )
    return ejecutar_query(
        """SELECT id, usuario, rol, tipo_usuario, nombre_completo, 
                  matricula, carrera, grupo, telefono, id_estudiante, fecha_registro
           FROM Super_Usuarios ORDER BY fecha_registro DESC""",
        fetch=True
    )


def eliminar_usuario(id_usuario):
    """Intenta eliminar. Devuelve (True, msg) o (False, msg) si tiene dependencias."""
    tiene_vehiculos = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Vehiculos WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']
    tiene_registros = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Registros WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']

    if tiene_vehiculos > 0 or tiene_registros > 0:
        return False, f"No se puede eliminar: tiene {tiene_vehiculos} vehículo(s) y {tiene_registros} registro(s) asociados."

    ejecutar_query("DELETE FROM Super_Usuarios WHERE id = ?", (id_usuario,))
    return True, "Usuario eliminado correctamente."


# --- VEHÍCULOS ---
def obtener_vehiculos_de_usuario(id_usuario):
    return ejecutar_query(
        "SELECT * FROM Super_Vehiculos WHERE id_usuario = ?",
        (id_usuario,),
        fetch=True
    )


def placas_existen(placas):
    res = ejecutar_query(
        "SELECT id FROM Super_Vehiculos WHERE placas = ?",
        (placas,),
        fetch=True
    )
    return len(res) > 0


def crear_vehiculo(id_usuario, tipo, placas, marca=None, modelo=None, color=None):
    query = """
        INSERT INTO Super_Vehiculos (id_usuario, tipo, placas, marca, modelo, color)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    ejecutar_query(query, (id_usuario, tipo, placas, marca, modelo, color))


def eliminar_vehiculo(id_vehiculo):
    ejecutar_query("DELETE FROM Super_Vehiculos WHERE id = ?", (id_vehiculo,))


# --- ESPACIOS ---
def obtener_espacios():
    return ejecutar_query("SELECT * FROM Super_Espacios", fetch=True)


# --- REGISTROS ---
def obtener_registro_activo_de_usuario(id_usuario):
    res = ejecutar_query(
        """SELECT r.*, v.tipo, v.placas 
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           WHERE r.id_usuario = ? AND r.estado = 'DENTRO'""",
        (id_usuario,),
        fetch=True
    )
    return res[0] if res else None


def obtener_todos_los_registros():
    return ejecutar_query(
        """SELECT r.id, r.hora_entrada, r.hora_salida, r.estado,
                  r.evidencia_entrada, r.evidencia_salida,
                  v.tipo, v.placas, v.marca, v.modelo,
                  u.nombre_completo, u.matricula, u.carrera, u.grupo, u.id_estudiante
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           ORDER BY r.hora_entrada DESC""",
        fetch=True
    )


# --- GENERACIÓN DE QR ---
def generar_qr_imagen(data_dict):
    texto = json.dumps(data_dict, ensure_ascii=False)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
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
        (placas,),
        fetch=True
    )
    return res[0] if res else None


def obtener_registro_activo_por_vehiculo(id_vehiculo):
    res = ejecutar_query(
        """SELECT * FROM Super_Registros 
           WHERE id_vehiculo = ? AND estado = 'DENTRO'""",
        (id_vehiculo,),
        fetch=True
    )
    return res[0] if res else None


def registrar_entrada(id_usuario, id_vehiculo, tipo, id_trabajador, evidencia_b64):
    ejecutar_query(
        """INSERT INTO Super_Registros 
           (id_usuario, id_vehiculo, estado, id_trabajador_entrada, evidencia_entrada)
           VALUES (?, ?, 'DENTRO', ?, ?)""",
        (id_usuario, id_vehiculo, id_trabajador, evidencia_b64)
    )
    ejecutar_query(
        "UPDATE Super_Espacios SET ocupados = ocupados + 1 WHERE tipo = ?",
        (tipo,)
    )


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
           WHERE r.estado = 'DENTRO'
           ORDER BY r.hora_entrada DESC""",
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