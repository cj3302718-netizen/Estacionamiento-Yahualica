import streamlit as st
import pyodbc
import bcrypt
import qrcode
import json
import base64
import cv2
import numpy as np
import secrets
import hmac
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


# --- CACHÉ ---
def limpiar_cache():
    try:
        st.cache_data.clear()
    except Exception:
        pass


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
        limpiar_cache()
    except Exception:
        pass


@st.cache_data(ttl=60, show_spinner=False)
def contar_logs():
    res = ejecutar_query("SELECT COUNT(*) AS t FROM Super_Logs", fetch=True)
    return res[0]['t'] if res else 0


@st.cache_data(ttl=120, show_spinner=False)
def obtener_acciones_unicas():
    res = ejecutar_query("SELECT DISTINCT accion FROM Super_Logs ORDER BY accion", fetch=True)
    return [r['accion'] for r in res] if res else []


def obtener_logs(limite=200, filtro_accion=None, buscar=None,
                 fecha_desde=None, fecha_hasta=None, offset=0):
    condiciones, params = [], []
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
        f"""SELECT l.id, l.accion, l.detalles, l.tabla_afectada, l.id_afectado, l.fecha,
                  u.usuario AS usuario_accion, u.nombre_completo AS nombre_accion,
                  u.rol AS rol_accion
           FROM Super_Logs l
           LEFT JOIN Super_Usuarios u ON l.id_usuario = u.id
           {where}
           ORDER BY l.fecha DESC
           OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
        tuple(params + [offset, limite]), fetch=True
    )


def contar_logs_filtrados(filtro_accion=None, buscar=None,
                          fecha_desde=None, fecha_hasta=None):
    condiciones, params = [], []
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

    res = ejecutar_query(
        f"""SELECT COUNT(*) AS t FROM Super_Logs l
            LEFT JOIN Super_Usuarios u ON l.id_usuario = u.id
            {where}""",
        tuple(params), fetch=True
    )
    return res[0]['t'] if res else 0


# --- USUARIOS ---
def obtener_usuario(usuario):
    res = ejecutar_query("SELECT * FROM Super_Usuarios WHERE usuario = ?",
                         (usuario,), fetch=True)
    return res[0] if res else None


def usuario_existe(usuario):
    return obtener_usuario(usuario) is not None


def crear_usuario(usuario, password, rol, tipo_usuario, nombre_completo,
                  matricula=None, carrera=None, grupo=None,
                  telefono=None, id_estudiante=None, lugar_asignado=None):
    hashed = hash_password(password)
    ejecutar_query(
        """INSERT INTO Super_Usuarios
           (usuario, password, rol, tipo_usuario, nombre_completo,
            matricula, carrera, grupo, telefono, id_estudiante,
            lugar_asignado, activo, intentos_fallidos)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)""",
        (usuario, hashed, rol, tipo_usuario, nombre_completo,
         matricula, carrera, grupo, telefono, id_estudiante, lugar_asignado)
    )
    limpiar_cache()


MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 10


def autenticar(usuario, password):
    user = obtener_usuario(usuario)
    if not user:
        return None, "Usuario o contraseña incorrectos"

    es_admin = (user.get('rol') == 'admin')

    if not es_admin:
        bloqueado_hasta = user.get('bloqueado_hasta')
        if bloqueado_hasta and isinstance(bloqueado_hasta, datetime):
            if bloqueado_hasta > datetime.now():
                mins = int((bloqueado_hasta - datetime.now()).total_seconds() / 60) + 1
                return None, f"🔒 Cuenta bloqueada por seguridad. Intenta de nuevo en {mins} min."
            else:
                ejecutar_query(
                    "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
                    (user['id'],)
                )
                user['intentos_fallidos'] = 0
                user['bloqueado_hasta'] = None

    if not verificar_password(password, user['password']):
        if es_admin:
            return None, "Usuario o contraseña incorrectos"
        intentos = (user.get('intentos_fallidos') or 0) + 1
        if intentos >= MAX_INTENTOS:
            bloq = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)
            ejecutar_query(
                "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = ? WHERE id = ?",
                (bloq, user['id'])
            )
            limpiar_cache()
            return None, f"🔒 Cuenta bloqueada por {MINUTOS_BLOQUEO} minutos tras {MAX_INTENTOS} intentos."
        else:
            ejecutar_query(
                "UPDATE Super_Usuarios SET intentos_fallidos = ? WHERE id = ?",
                (intentos, user['id'])
            )
            return None, f"Usuario o contraseña incorrectos. Te quedan {MAX_INTENTOS - intentos} intento(s)."

    ejecutar_query(
        "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (user['id'],)
    )
    limpiar_cache()

    if user.get('activo') in (0, False, None):
        return None, "🔒 Tu cuenta está desactivada. Contacta al administrador."

    return user, None


@st.cache_data(ttl=60, show_spinner=False)
def contar_admins():
    res = ejecutar_query(
        "SELECT COUNT(*) AS total FROM Super_Usuarios WHERE rol = 'admin' AND activo = 1",
        fetch=True
    )
    return res[0]['total'] if res else 0


def desbloquear_usuario(id_usuario):
    ejecutar_query(
        "UPDATE Super_Usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (id_usuario,)
    )
    limpiar_cache()
    return True, "Cuenta desbloqueada correctamente."


# --- IDs ---
def generar_siguiente_id(prefijo="ALU"):
    res = ejecutar_query(
        "SELECT id_estudiante FROM Super_Usuarios WHERE id_estudiante LIKE ?",
        (f"{prefijo}-%",), fetch=True
    )
    if not res:
        return f"{prefijo}-0001"
    numeros = []
    for r in res:
        try:
            if r['id_estudiante']:
                numeros.append(int(r['id_estudiante'].split('-')[1]))
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


# --- ACTUALIZACIÓN ---
def actualizar_usuario(id_usuario, nombre_completo, telefono=None, matricula=None,
                       carrera=None, grupo=None, id_estudiante=None,
                       tipo_usuario=None, nueva_password=None, lugar_asignado=None):
    if nueva_password:
        hashed = hash_password(nueva_password)
        ejecutar_query(
            """UPDATE Super_Usuarios
               SET nombre_completo = ?, telefono = ?, matricula = ?, carrera = ?,
                   grupo = ?, id_estudiante = ?, tipo_usuario = ?,
                   lugar_asignado = ?, password = ?,
                   intentos_fallidos = 0, bloqueado_hasta = NULL
               WHERE id = ?""",
            (nombre_completo, telefono, matricula, carrera,
             grupo, id_estudiante, tipo_usuario, lugar_asignado,
             hashed, id_usuario)
        )
    else:
        ejecutar_query(
            """UPDATE Super_Usuarios
               SET nombre_completo = ?, telefono = ?, matricula = ?, carrera = ?,
                   grupo = ?, id_estudiante = ?, tipo_usuario = ?, lugar_asignado = ?
               WHERE id = ?""",
            (nombre_completo, telefono, matricula, carrera,
             grupo, id_estudiante, tipo_usuario, lugar_asignado, id_usuario)
        )
    limpiar_cache()


def activar_usuario(id_usuario):
    ejecutar_query(
        "UPDATE Super_Usuarios SET activo = 1, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (id_usuario,)
    )
    limpiar_cache()
    return True, "Usuario activado correctamente."


def desactivar_usuario(id_usuario):
    res = ejecutar_query("SELECT rol FROM Super_Usuarios WHERE id = ?",
                         (id_usuario,), fetch=True)
    if res and res[0]['rol'] == 'admin':
        admins_activos = ejecutar_query(
            "SELECT COUNT(*) AS t FROM Super_Usuarios WHERE rol = 'admin' AND activo = 1",
            fetch=True
        )[0]['t']
        if admins_activos <= 1:
            return False, "No puedes desactivar al último administrador activo."
    ejecutar_query("UPDATE Super_Usuarios SET activo = 0 WHERE id = ?", (id_usuario,))
    limpiar_cache()
    return True, "Usuario desactivado correctamente."


# --- GESTIÓN USUARIOS ---
def obtener_todos_usuarios(filtro_rol=None, solo_activos=False):
    condiciones, params = [], []
    if filtro_rol:
        condiciones.append("rol = ?")
        params.append(filtro_rol)
    if solo_activos:
        condiciones.append("activo = 1")
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    return ejecutar_query(
        f"""SELECT id, usuario, rol, tipo_usuario, nombre_completo,
                  matricula, carrera, grupo, telefono, id_estudiante,
                  lugar_asignado, fecha_registro, activo,
                  intentos_fallidos, bloqueado_hasta
           FROM Super_Usuarios {where} ORDER BY fecha_registro DESC""",
        tuple(params), fetch=True
    )


def contar_usuarios_por_estado():
    res = ejecutar_query(
        """SELECT rol, activo, COUNT(*) AS total
           FROM Super_Usuarios GROUP BY rol, activo""",
        fetch=True
    )
    datos = {
        "alumno":         {"activos": 0, "inactivos": 0},
        "docente":        {"activos": 0, "inactivos": 0},
        "administrativo": {"activos": 0, "inactivos": 0},
        "trabajador":     {"activos": 0, "inactivos": 0},
        "admin":          {"activos": 0, "inactivos": 0},
    }
    for r in (res or []):
        rol = r['rol']
        if rol in datos:
            if r['activo']:
                datos[rol]['activos'] = r['total']
            else:
                datos[rol]['inactivos'] = r['total']
    return datos


def eliminar_usuario(id_usuario):
    tiene_veh = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Vehiculos WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']
    tiene_reg = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Registros WHERE id_usuario = ?",
        (id_usuario,), fetch=True
    )[0]['t']
    if tiene_veh > 0 or tiene_reg > 0:
        return False, f"No se puede eliminar: tiene {tiene_veh} vehículo(s) y {tiene_reg} registro(s). Te recomendamos desactivarlo."
    ejecutar_query("DELETE FROM Super_Usuarios WHERE id = ?", (id_usuario,))
    limpiar_cache()
    return True, "Usuario eliminado correctamente."


# --- VEHÍCULOS ---
def obtener_vehiculos_de_usuario(id_usuario):
    return ejecutar_query("SELECT * FROM Super_Vehiculos WHERE id_usuario = ?",
                          (id_usuario,), fetch=True)


def placas_existen(placas):
    if not placas:
        return False
    limpio = str(placas).upper().replace("-", "").replace(" ", "").strip()
    res = ejecutar_query(
        "SELECT id FROM Super_Vehiculos WHERE REPLACE(REPLACE(UPPER(placas),'-',''),' ','') = ?",
        (limpio,), fetch=True
    )
    return len(res) > 0


def crear_vehiculo(id_usuario, tipo, placas, marca=None, modelo=None, color=None,
                   es_tramite=0, identificador_alterno=None):
    ejecutar_query(
        """INSERT INTO Super_Vehiculos
           (id_usuario, tipo, placas, marca, modelo, color, es_tramite, identificador_alterno)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_usuario, tipo, placas, marca, modelo, color, es_tramite, identificador_alterno)
    )
    limpiar_cache()


def actualizar_placas_tramite(id_vehiculo, id_usuario, nuevas_placas):
    """Cambia el identificador TEMP por las placas reales. Devuelve (ok, mensaje)."""
    limpio = str(nuevas_placas or "").upper().replace("-", "").replace(" ", "").strip()
    if not limpio:
        return False, "Escribe las placas."
    res = ejecutar_query(
        "SELECT es_tramite FROM Super_Vehiculos WHERE id = ? AND id_usuario = ?",
        (id_vehiculo, id_usuario), fetch=True
    )
    if not res or not res[0]['es_tramite']:
        return False, "Este vehículo no está en trámite."
    if placas_existen(limpio):
        return False, "Ya existe un vehículo con esas placas."
    ejecutar_query(
        "UPDATE Super_Vehiculos SET placas = ?, es_tramite = 0 WHERE id = ? AND id_usuario = ?",
        (limpio, id_vehiculo, id_usuario)
    )
    limpiar_cache()
    return True, "Placas actualizadas."


def generar_placas_temporales():
    """Genera un identificador interno TEMP-XXXX que nunca se repite."""
    res = ejecutar_query(
        "SELECT placas FROM Super_Vehiculos WHERE placas LIKE 'TEMP-%'", fetch=True
    ) or []
    mayor = 0
    for r in res:
        sufijo = str(r['placas'])[5:]
        if sufijo.isdigit():
            mayor = max(mayor, int(sufijo))
    return f"TEMP-{mayor + 1:04d}"


def eliminar_vehiculo(id_vehiculo):
    tiene_reg = ejecutar_query(
        "SELECT COUNT(*) AS t FROM Super_Registros WHERE id_vehiculo = ?",
        (id_vehiculo,), fetch=True
    )[0]['t']
    if tiene_reg > 0:
        return False, f"No se puede eliminar: el vehículo tiene {tiene_reg} registro(s) asociados."
    ejecutar_query("DELETE FROM Super_Vehiculos WHERE id = ?", (id_vehiculo,))
    limpiar_cache()
    return True, "Vehículo eliminado correctamente."


def buscar_vehiculos_admin(buscar=None, limite=50):
    if buscar:
        like = f"%{buscar}%"
        return ejecutar_query(
            f"""SELECT TOP {limite}
                      v.id, v.placas, v.tipo, v.marca, v.modelo, v.color,
                      v.es_tramite, v.identificador_alterno,
                      u.id AS id_usuario, u.nombre_completo, u.usuario, u.rol,
                      u.matricula, u.id_estudiante, u.carrera, u.lugar_asignado
               FROM Super_Vehiculos v
               INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
               WHERE v.placas LIKE ?
                  OR u.nombre_completo LIKE ?
                  OR u.matricula LIKE ?
                  OR u.id_estudiante LIKE ?
                  OR u.usuario LIKE ?
                  OR u.lugar_asignado LIKE ?
               ORDER BY v.placas""",
            (like, like, like, like, like, like), fetch=True
        )
    return ejecutar_query(
        f"""SELECT TOP {limite}
                  v.id, v.placas, v.tipo, v.marca, v.modelo, v.color,
                  v.es_tramite, v.identificador_alterno,
                  u.id AS id_usuario, u.nombre_completo, u.usuario, u.rol,
                  u.matricula, u.id_estudiante, u.carrera, u.lugar_asignado
           FROM Super_Vehiculos v
           INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
           ORDER BY v.placas""",
        fetch=True
    )


@st.cache_data(ttl=30, show_spinner=False)
def listar_todas_las_placas(limite=200):
    res = ejecutar_query(
        f"""SELECT TOP {limite} v.placas, v.tipo, u.nombre_completo
            FROM Super_Vehiculos v
            INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
            ORDER BY v.placas""",
        fetch=True
    )
    return res or []


# --- ESPACIOS ---
@st.cache_data(ttl=10, show_spinner=False)
def obtener_espacios():
    return ejecutar_query("SELECT * FROM Super_Espacios", fetch=True)


class EstacionamientoLleno(Exception):
    """Se intentó registrar una entrada pero ya no hay lugares de ese tipo de vehículo."""


def estado_espacio(tipo):
    """Capacidad y ocupación en vivo (sin caché) de un tipo de vehículo ('Auto' o 'Moto')."""
    res = ejecutar_query(
        "SELECT capacidad_total, ocupados FROM Super_Espacios WHERE tipo = ?",
        (tipo,), fetch=True
    )
    return res[0] if res else None


def verificar_hay_lugar(tipo):
    """Lanza EstacionamientoLleno si no hay lugares libres para ese tipo."""
    e = estado_espacio(tipo)
    if e and int(e['ocupados'] or 0) >= int(e['capacidad_total'] or 0):
        nombre = "autos" if tipo == "Auto" else "motos"
        raise EstacionamientoLleno(
            f"El estacionamiento de {nombre} está lleno ({e['ocupados']} de {e['capacidad_total']})."
        )


def actualizar_capacidad(tipo, nueva_capacidad):
    """Cambia la capacidad total de un tipo. Devuelve (ok, mensaje)."""
    try:
        nueva = int(nueva_capacidad)
    except (TypeError, ValueError):
        return False, "La capacidad debe ser un número entero."
    if nueva < 0 or nueva > 10000:
        return False, "La capacidad debe estar entre 0 y 10,000."
    e = estado_espacio(tipo)
    if not e:
        return False, f"No existe configuración de espacios para {tipo}."
    if nueva < int(e['ocupados'] or 0):
        return False, (f"Hay {e['ocupados']} vehículo(s) dentro; la capacidad no puede ser menor "
                       f"({nueva}). Espera a que salgan o recalcula la ocupación.")
    ejecutar_query("UPDATE Super_Espacios SET capacidad_total = ? WHERE tipo = ?", (nueva, tipo))
    limpiar_cache()
    return True, "Capacidad actualizada."


def recalcular_ocupados():
    """Vuelve a calcular la ocupación real contando los vehículos con estado DENTRO."""
    resultado = {}
    for tipo in ("Auto", "Moto"):
        n = ejecutar_query(
            """SELECT COUNT(*) AS t FROM Super_Registros r
               INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
               WHERE r.estado = 'DENTRO' AND v.tipo = ?""",
            (tipo,), fetch=True
        )
        total = int(n[0]['t']) if n else 0
        try:
            m = ejecutar_query(
                "SELECT COUNT(*) AS t FROM Super_Registros_Manuales WHERE estado = 'DENTRO' AND tipo_vehiculo = ?",
                (tipo,), fetch=True
            )
            total += int(m[0]['t']) if m else 0
        except Exception:
            pass
        ejecutar_query("UPDATE Super_Espacios SET ocupados = ? WHERE tipo = ?", (total, tipo))
        resultado[tipo] = total
    limpiar_cache()
    return resultado


# --- REGISTROS ---
def obtener_registro_activo_de_usuario(id_usuario):
    res = ejecutar_query(
        """SELECT r.*, v.tipo, v.placas FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           WHERE r.id_usuario = ? AND r.estado = 'DENTRO'""",
        (id_usuario,), fetch=True
    )
    return res[0] if res else None


@st.cache_data(ttl=300, show_spinner=False)
def _existe_columna_metodo():
    """True si Super_Registros ya tiene la columna metodo_ingreso (migración v3)."""
    try:
        res = ejecutar_query("SELECT COL_LENGTH('Super_Registros', 'metodo_ingreso') AS c", fetch=True)
        return bool(res and res[0]['c'])
    except Exception:
        return False


def _sel_metodo():
    return "r.metodo_ingreso" if _existe_columna_metodo() else "CAST(NULL AS NVARCHAR(80))"


def _cond_metodo(filtro):
    """Condición SQL para filtrar por forma de ingreso ('QR' o 'Manual')."""
    if not filtro or filtro == "Todos":
        return None
    tiene = _existe_columna_metodo()
    if filtro == "Manual":
        return "r.metodo_ingreso = 'MANUAL'" if tiene else "1 = 0"
    if filtro == "QR":
        return "ISNULL(r.metodo_ingreso, 'QR') = 'QR'" if tiene else None
    return None


def obtener_todos_los_registros(fecha_desde=None, fecha_hasta=None):
    condiciones, params = [], []
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


def obtener_registros_paginado(fecha_desde=None, fecha_hasta=None, filtro_estado=None,
                               filtro_tipo=None, buscar=None, offset=0, limite=20, filtro_metodo=None):
    condiciones, params = [], []
    if fecha_desde:
        condiciones.append("CAST(r.hora_entrada AS DATE) >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("CAST(r.hora_entrada AS DATE) <= ?")
        params.append(fecha_hasta)
    if filtro_estado and filtro_estado != "Todos":
        condiciones.append("r.estado = ?")
        params.append(filtro_estado)
    if filtro_tipo and filtro_tipo != "Todos":
        condiciones.append("v.tipo = ?")
        params.append(filtro_tipo)
    if buscar:
        condiciones.append("(u.nombre_completo LIKE ? OR v.placas LIKE ? OR u.matricula LIKE ?)")
        like = f"%{buscar}%"
        params.extend([like, like, like])
    cm = _cond_metodo(filtro_metodo)
    if cm:
        condiciones.append(cm)
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    return ejecutar_query(
        f"""SELECT r.id, r.hora_entrada, r.hora_salida, r.estado,
                  r.evidencia_entrada, r.evidencia_salida,
                  v.tipo, v.placas, v.marca, v.modelo,
                  u.nombre_completo, u.matricula, u.carrera, u.grupo, u.id_estudiante,
                  {_sel_metodo()} AS metodo_ingreso
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           {where}
           ORDER BY r.hora_entrada DESC
           OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
        tuple(params + [offset, limite]), fetch=True
    )


def contar_registros_filtrados(fecha_desde=None, fecha_hasta=None,
                               filtro_estado=None, filtro_tipo=None, buscar=None, filtro_metodo=None):
    condiciones, params = [], []
    if fecha_desde:
        condiciones.append("CAST(r.hora_entrada AS DATE) >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("CAST(r.hora_entrada AS DATE) <= ?")
        params.append(fecha_hasta)
    if filtro_estado and filtro_estado != "Todos":
        condiciones.append("r.estado = ?")
        params.append(filtro_estado)
    if filtro_tipo and filtro_tipo != "Todos":
        condiciones.append("v.tipo = ?")
        params.append(filtro_tipo)
    if buscar:
        condiciones.append("(u.nombre_completo LIKE ? OR v.placas LIKE ? OR u.matricula LIKE ?)")
        like = f"%{buscar}%"
        params.extend([like, like, like])
    cm = _cond_metodo(filtro_metodo)
    if cm:
        condiciones.append(cm)
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    res = ejecutar_query(
        f"""SELECT COUNT(*) AS t FROM Super_Registros r
            INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
            INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
            {where}""",
        tuple(params), fetch=True
    )
    return res[0]['t'] if res else 0


def obtener_historial_vehiculo(id_vehiculo, limite=100):
    return ejecutar_query(
        f"""SELECT TOP {limite}
                  r.id, r.hora_entrada, r.hora_salida, r.estado,
                  r.evidencia_entrada, r.evidencia_salida,
                  v.tipo, v.placas, v.marca, v.modelo,
                  u.nombre_completo, u.matricula, u.carrera, u.id_estudiante
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           WHERE v.id = ?
           ORDER BY r.hora_entrada DESC""",
        (id_vehiculo,), fetch=True
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


# --- TOKEN QR (REGENERAR / VALIDAR) ---
def generar_token_qr():
    return secrets.token_hex(16).upper()


def obtener_token_qr(id_usuario):
    res = ejecutar_query(
        "SELECT qr_token FROM Super_Usuarios WHERE id = ?",
        (id_usuario,), fetch=True
    )
    return res[0]['qr_token'] if res else None


def regenerar_token_qr(id_usuario):
    nuevo = generar_token_qr()
    ejecutar_query(
        "UPDATE Super_Usuarios SET qr_token = ?, qr_token_updated = GETDATE() WHERE id = ?",
        (nuevo, id_usuario)
    )
    limpiar_cache()
    return nuevo


def verificar_token_qr(id_vehiculo, token):
    """Si el dueño ya generó su token, el QR debe traer ese mismo token.
    Si el dueño nunca generó token, se aceptan los QR antiguos."""
    res = ejecutar_query(
        """SELECT u.qr_token FROM Super_Vehiculos v
           INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
           WHERE v.id = ?""",
        (id_vehiculo,), fetch=True
    )
    if not res:
        return False
    token_bd = res[0]['qr_token']
    if not token_bd:
        return True
    return hmac.compare_digest(str(token or "").encode("utf-8"), str(token_bd).encode("utf-8"))


# --- CASETA ---
def obtener_vehiculo_por_placas(placas):
    """Busca vehículo normalizando placas: ignora guiones, espacios y mayúsculas."""
    if not placas:
        return None
    limpio = str(placas).upper().replace("-", "").replace(" ", "").strip()

    res = ejecutar_query(
        """SELECT v.*, u.usuario, u.nombre_completo, u.matricula, u.rol,
                  u.id_estudiante, u.carrera, u.grupo, u.telefono, u.lugar_asignado
           FROM Super_Vehiculos v
           INNER JOIN Super_Usuarios u ON v.id_usuario = u.id
           WHERE REPLACE(REPLACE(UPPER(v.placas), '-', ''), ' ', '') = ?""",
        (limpio,), fetch=True
    )
    return res[0] if res else None


def obtener_registro_activo_por_vehiculo(id_vehiculo):
    res = ejecutar_query(
        "SELECT * FROM Super_Registros WHERE id_vehiculo = ? AND estado = 'DENTRO'",
        (id_vehiculo,), fetch=True
    )
    return res[0] if res else None


def registrar_entrada(id_usuario, id_vehiculo, tipo, id_trabajador, evidencia_b64, metodo=None):
    """metodo: 'QR' o 'MANUAL' (búsqueda + identificación verificada)."""
    verificar_hay_lugar(tipo)
    if metodo and _existe_columna_metodo():
        ejecutar_query(
            """INSERT INTO Super_Registros
               (id_usuario, id_vehiculo, estado, id_trabajador_entrada, evidencia_entrada, metodo_ingreso)
               VALUES (?, ?, 'DENTRO', ?, ?, ?)""",
            (id_usuario, id_vehiculo, id_trabajador, evidencia_b64, str(metodo)[:80])
        )
    else:
        ejecutar_query(
            """INSERT INTO Super_Registros
               (id_usuario, id_vehiculo, estado, id_trabajador_entrada, evidencia_entrada)
               VALUES (?, ?, 'DENTRO', ?, ?)""",
            (id_usuario, id_vehiculo, id_trabajador, evidencia_b64)
        )
    ejecutar_query("UPDATE Super_Espacios SET ocupados = ocupados + 1 WHERE tipo = ?", (tipo,))
    limpiar_cache()


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
    limpiar_cache()


@st.cache_data(ttl=10, show_spinner=False)
def obtener_vehiculos_dentro():
    return ejecutar_query(
        """SELECT r.id AS id_registro, r.hora_entrada, v.placas, v.tipo, v.id AS id_vehiculo,
                  u.nombre_completo, u.matricula, u.carrera, u.id_estudiante, u.lugar_asignado
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


# --- HISTORIAL PERSONAL ---
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


@st.cache_data(ttl=60, show_spinner=False)
def contar_visitas_usuario(id_usuario):
    res = ejecutar_query(
        """SELECT COUNT(*) AS total,
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


# --- AUTO-SERVICIO ---
def cambiar_password_usuario(id_usuario, password_actual, password_nueva):
    user = ejecutar_query("SELECT password FROM Super_Usuarios WHERE id = ?",
                          (id_usuario,), fetch=True)
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
    limpiar_cache()
    return True, "Contraseña actualizada correctamente."


def actualizar_telefono_usuario(id_usuario, telefono):
    ejecutar_query("UPDATE Super_Usuarios SET telefono = ? WHERE id = ?",
                   (telefono, id_usuario))
    limpiar_cache()
    return True, "Teléfono actualizado correctamente."


# =========================================================
# SISTEMA DE MENSAJES
# =========================================================
def enviar_mensaje(id_remitente, asunto, cuerpo, id_destinatario=None, tipo='mensaje'):
    ejecutar_query(
        """INSERT INTO Super_Mensajes (id_remitente, id_destinatario, asunto, cuerpo, tipo)
           VALUES (?, ?, ?, ?, ?)""",
        (id_remitente, id_destinatario, asunto[:200], cuerpo, tipo)
    )
    limpiar_cache()


def obtener_mensajes_para_usuario(id_usuario, limite=50):
    return ejecutar_query(
        f"""SELECT TOP {limite}
                  m.id, m.asunto, m.cuerpo, m.tipo, m.leido, m.fecha,
                  u.usuario AS remitente_usuario, u.nombre_completo AS remitente_nombre,
                  u.rol AS remitente_rol,
                  CASE WHEN m.id_destinatario IS NULL THEN 1 ELSE 0 END AS es_broadcast
           FROM Super_Mensajes m
           INNER JOIN Super_Usuarios u ON m.id_remitente = u.id
           WHERE m.id_destinatario = ? OR m.id_destinatario IS NULL
           ORDER BY m.fecha DESC""",
        (id_usuario,), fetch=True
    )


def contar_mensajes_no_leidos(id_usuario):
    res = ejecutar_query(
        """SELECT COUNT(*) AS t FROM Super_Mensajes
           WHERE (id_destinatario = ? OR id_destinatario IS NULL) AND leido = 0""",
        (id_usuario,), fetch=True
    )
    return res[0]['t'] if res else 0


def marcar_mensaje_leido(id_mensaje):
    ejecutar_query("UPDATE Super_Mensajes SET leido = 1 WHERE id = ?", (id_mensaje,))
    limpiar_cache()


def obtener_mensajes_enviados(id_remitente, limite=50):
    return ejecutar_query(
        f"""SELECT TOP {limite}
                  m.id, m.asunto, m.cuerpo, m.tipo, m.fecha,
                  d.usuario AS destinatario_usuario, d.nombre_completo AS destinatario_nombre,
                  CASE WHEN m.id_destinatario IS NULL THEN 1 ELSE 0 END AS es_broadcast
           FROM Super_Mensajes m
           LEFT JOIN Super_Usuarios d ON m.id_destinatario = d.id
           WHERE m.id_remitente = ?
           ORDER BY m.fecha DESC""",
        (id_remitente,), fetch=True
    )


def eliminar_mensaje(id_mensaje):
    ejecutar_query("DELETE FROM Super_Mensajes WHERE id = ?", (id_mensaje,))
    limpiar_cache()


# =========================================================
# ALERTAS PROGRAMADAS
# =========================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_vehiculos_alerta(horas_minimas=12):
    return ejecutar_query(
        """SELECT r.id AS id_registro, r.hora_entrada, v.placas, v.tipo, v.id AS id_vehiculo,
                  u.id AS id_usuario, u.nombre_completo, u.matricula, u.carrera,
                  DATEDIFF(MINUTE, r.hora_entrada, GETDATE()) AS minutos_dentro
           FROM Super_Registros r
           INNER JOIN Super_Vehiculos v ON r.id_vehiculo = v.id
           INNER JOIN Super_Usuarios u ON r.id_usuario = u.id
           WHERE r.estado = 'DENTRO'
             AND DATEDIFF(MINUTE, r.hora_entrada, GETDATE()) >= ?
           ORDER BY r.hora_entrada ASC""",
        (horas_minimas * 60,), fetch=True
    )


# =========================================================
# ENTRADAS MANUALES SIN IDENTIFICACIÓN
# =========================================================
def registrar_entrada_manual(nombre, tipo_id, motivo, placas, marca, modelo,
                              color, tipo_vehiculo, id_trabajador, evidencia_b64):
    if tipo_vehiculo:
        verificar_hay_lugar(tipo_vehiculo)
    ejecutar_query(
        """INSERT INTO Super_Registros_Manuales
           (nombre_visitante, tipo_identificacion, motivo, placas, marca, modelo,
            color, tipo_vehiculo, id_trabajador, evidencia_entrada)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nombre, tipo_id, motivo, placas, marca, modelo, color,
         tipo_vehiculo, id_trabajador, evidencia_b64)
    )
    if tipo_vehiculo:
        ejecutar_query(
            "UPDATE Super_Espacios SET ocupados = ocupados + 1 WHERE tipo = ?",
            (tipo_vehiculo,)
        )
    limpiar_cache()


def registrar_salida_manual(id_registro, id_trabajador, evidencia_b64):
    res = ejecutar_query(
        "SELECT tipo_vehiculo FROM Super_Registros_Manuales WHERE id = ?",
        (id_registro,), fetch=True
    )
    tipo = res[0]['tipo_vehiculo'] if res else None
    ejecutar_query(
        """UPDATE Super_Registros_Manuales
           SET hora_salida = GETDATE(), estado = 'FUERA',
               id_trabajador_salida = ?, evidencia_salida = ?
           WHERE id = ?""",
        (id_trabajador, evidencia_b64, id_registro)
    )
    if tipo:
        ejecutar_query(
            "UPDATE Super_Espacios SET ocupados = ocupados - 1 WHERE tipo = ? AND ocupados > 0",
            (tipo,)
        )
    limpiar_cache()


def obtener_registros_manuales(fecha_desde=None, fecha_hasta=None,
                                solo_pendientes=False, limite=200):
    cond, params = [], []
    if fecha_desde:
        cond.append("CAST(rm.hora_entrada AS DATE) >= ?"); params.append(fecha_desde)
    if fecha_hasta:
        cond.append("CAST(rm.hora_entrada AS DATE) <= ?"); params.append(fecha_hasta)
    if solo_pendientes:
        cond.append("rm.validado = 0 AND rm.estado = 'FUERA'")
    where = "WHERE " + " AND ".join(cond) if cond else ""
    return ejecutar_query(
        f"""SELECT TOP {limite} rm.*,
                   t.nombre_completo AS trabajador_nombre, t.usuario AS trabajador_usuario,
                   a.nombre_completo AS admin_nombre, a.usuario AS admin_usuario
            FROM Super_Registros_Manuales rm
            LEFT JOIN Super_Usuarios t ON rm.id_trabajador = t.id
            LEFT JOIN Super_Usuarios a ON rm.id_admin_valida = a.id
            {where}
            ORDER BY rm.hora_entrada DESC""",
        tuple(params), fetch=True
    )


def contar_registros_manuales_pendientes():
    res = ejecutar_query(
        """SELECT COUNT(*) AS t FROM Super_Registros_Manuales
           WHERE validado = 0 AND estado = 'FUERA'""",
        fetch=True
    )
    return res[0]['t'] if res else 0


def validar_registro_manual(id_registro, id_admin):
    ejecutar_query(
        """UPDATE Super_Registros_Manuales
           SET validado = 1, id_admin_valida = ?, fecha_validacion = GETDATE()
           WHERE id = ?""",
        (id_admin, id_registro)
    )
    limpiar_cache()
    return True, "Registro validado."


def obtener_vehiculos_manuales_dentro():
    return ejecutar_query(
        """SELECT rm.id AS id_registro, rm.nombre_visitante, rm.placas,
                  rm.marca, rm.modelo, rm.color, rm.tipo_vehiculo,
                  rm.hora_entrada, rm.evidencia_entrada,
                  u.nombre_completo AS trabajador_nombre
           FROM Super_Registros_Manuales rm
           INNER JOIN Super_Usuarios u ON rm.id_trabajador = u.id
           WHERE rm.estado = 'DENTRO'
           ORDER BY rm.hora_entrada DESC""",
        fetch=True
    )


# =========================================================
# ÍNDICES RECOMENDADOS
# =========================================================
INDICES_RECOMENDADOS = [
    ("IX_Usuarios_Usuario", "CREATE INDEX IX_Usuarios_Usuario ON Super_Usuarios(usuario)"),
    ("IX_Usuarios_Rol_Activo", "CREATE INDEX IX_Usuarios_Rol_Activo ON Super_Usuarios(rol, activo)"),
    ("IX_Usuarios_IdEstudiante", "CREATE INDEX IX_Usuarios_IdEstudiante ON Super_Usuarios(id_estudiante)"),
    ("IX_Usuarios_LugarAsignado", "CREATE INDEX IX_Usuarios_LugarAsignado ON Super_Usuarios(lugar_asignado)"),
    ("IX_Usuarios_QRToken", "CREATE INDEX IX_Usuarios_QRToken ON Super_Usuarios(qr_token)"),
    ("IX_Vehiculos_Placas", "CREATE INDEX IX_Vehiculos_Placas ON Super_Vehiculos(placas)"),
    ("IX_Vehiculos_IdUsuario", "CREATE INDEX IX_Vehiculos_IdUsuario ON Super_Vehiculos(id_usuario)"),
    ("IX_Registros_Estado", "CREATE INDEX IX_Registros_Estado ON Super_Registros(estado)"),
    ("IX_Registros_HoraEntrada", "CREATE INDEX IX_Registros_HoraEntrada ON Super_Registros(hora_entrada DESC)"),
    ("IX_Registros_IdVehiculo", "CREATE INDEX IX_Registros_IdVehiculo ON Super_Registros(id_vehiculo)"),
    ("IX_Registros_IdUsuario", "CREATE INDEX IX_Registros_IdUsuario ON Super_Registros(id_usuario)"),
    ("IX_Registros_Metodo", "CREATE INDEX IX_Registros_Metodo ON Super_Registros(metodo_ingreso)"),
    ("IX_Logs_Fecha", "CREATE INDEX IX_Logs_Fecha ON Super_Logs(fecha DESC)"),
    ("IX_Logs_Accion", "CREATE INDEX IX_Logs_Accion ON Super_Logs(accion)"),
    ("IX_Mensajes_Destinatario", "CREATE INDEX IX_Mensajes_Destinatario ON Super_Mensajes(id_destinatario, leido)"),
    ("IX_Manuales_Estado", "CREATE INDEX IX_Manuales_Estado ON Super_Registros_Manuales(estado, validado)"),
]


def crear_tabla_mensajes():
    try:
        ejecutar_query("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Super_Mensajes' AND xtype='U')
            CREATE TABLE Super_Mensajes (
                id INT IDENTITY(1,1) PRIMARY KEY,
                id_remitente INT NOT NULL,
                id_destinatario INT NULL,
                asunto NVARCHAR(200) NOT NULL,
                cuerpo NVARCHAR(MAX) NOT NULL,
                tipo NVARCHAR(50) DEFAULT 'mensaje',
                leido BIT DEFAULT 0,
                fecha DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (id_remitente) REFERENCES Super_Usuarios(id),
                FOREIGN KEY (id_destinatario) REFERENCES Super_Usuarios(id)
            )
        """)
        return True, "Tabla Super_Mensajes lista."
    except Exception as e:
        return False, f"Error: {e}"


def crear_indices():
    creados, errores = [], []
    for nombre, sql in INDICES_RECOMENDADOS:
        try:
            ejecutar_query(sql)
            creados.append(nombre)
        except Exception:
            errores.append(nombre)
    return creados, errores
