"""
Notificaciones gratuitas al administrador mediante un bot de Telegram.

Configuración (st.secrets / .streamlit/secrets.toml):
    telegram_bot_token = "123456:ABC..."          # lo da @BotFather
    telegram_chat_ids  = "111111111,222222222"    # un chat_id por admin (o el de un grupo)

El envío se hace en un hilo aparte con timeout, así que si Telegram falla o
tarda, la caseta nunca se queda esperando.
"""
import html
import logging
import threading

import requests
import streamlit as st

log = logging.getLogger("notificaciones")


# ---------------------------------------------------------------- configuración
def _config():
    """Devuelve (token, [chat_ids]). Si falta algo, devuelve ('', [])."""
    try:
        token = str(st.secrets.get("telegram_bot_token", "") or "").strip()
        raw = st.secrets.get("telegram_chat_ids", "")
    except Exception:
        return "", []
    if isinstance(raw, (list, tuple)):
        ids = [str(x).strip() for x in raw]
    else:
        ids = [x.strip() for x in str(raw or "").split(",")]
    ids = [i for i in ids if i]
    return (token, ids) if token and ids else ("", [])


def telegram_configurado():
    token, ids = _config()
    return bool(token and ids)


# ---------------------------------------------------------------- envío
def _t(valor, n=120):
    """Texto seguro para HTML de Telegram y con longitud limitada."""
    return html.escape(str(valor or "—").strip()[:n])


def _enviar_a_todos(token, chat_ids, texto, foto_bytes=None):
    base = f"https://api.telegram.org/bot{token}"
    errores = []
    for chat in chat_ids:
        try:
            if foto_bytes:
                r = requests.post(
                    f"{base}/sendPhoto",
                    data={"chat_id": chat, "caption": texto[:1000], "parse_mode": "HTML"},
                    files={"photo": ("evidencia.jpg", foto_bytes)},
                    timeout=10,
                )
            else:
                r = requests.post(
                    f"{base}/sendMessage",
                    data={"chat_id": chat, "text": texto, "parse_mode": "HTML"},
                    timeout=10,
                )
            if not r.ok:
                try:
                    detalle = r.json().get("description", r.text[:120])
                except Exception:
                    detalle = r.text[:120]
                errores.append(f"{chat}: {detalle}")
                log.warning("Telegram rechazó el mensaje para %s: %s", chat, detalle)
        except Exception as e:
            errores.append(f"{chat}: {e}")
            log.warning("No se pudo enviar a Telegram (%s): %s", chat, e)
    return errores


def _enviar_en_segundo_plano(texto, foto_bytes=None):
    token, ids = _config()          # se lee aquí, en el hilo principal de Streamlit
    if not token:
        return
    threading.Thread(
        target=_enviar_a_todos, args=(token, ids, texto, foto_bytes), daemon=True
    ).start()


# ---------------------------------------------------------------- avisos
def notificar_entrada_manual(trabajador, nombre, tipo_id, motivo,
                             tipo_vehiculo, placas, foto_bytes=None):
    texto = (
        "🆘 <b>Entrada manual sin identificación</b>\n"
        f"👤 {_t(nombre)}\n"
        f"🪪 Identificación: {_t(tipo_id)}\n"
        f"📝 Motivo: {_t(motivo, 200)}\n"
        f"🚗 {_t(tipo_vehiculo)} · {_t(placas) if placas else 'sin placas'}\n"
        f"👷 Autorizó: {_t(trabajador)}\n\n"
        "Cuando salga quedará pendiente de tu validación."
    )
    _enviar_en_segundo_plano(texto, foto_bytes)


def notificar_salida_manual(trabajador, nombre, tipo_vehiculo, placas, foto_bytes=None):
    texto = (
        "✅ <b>Entrada manual lista para validar</b>\n"
        f"👤 {_t(nombre)} ya salió\n"
        f"🚗 {_t(tipo_vehiculo)} · {_t(placas) if placas else 'sin placas'}\n"
        f"👷 Salida registrada por: {_t(trabajador)}\n\n"
        "Entra a <b>Registros Manuales</b> para validarla."
    )
    _enviar_en_segundo_plano(texto, foto_bytes)


# ---------------------------------------------------------------- prueba
def enviar_prueba():
    """Envío síncrono para comprobar la configuración. Devuelve (ok, mensaje)."""
    token, ids = _config()
    if not token:
        return False, "Falta telegram_bot_token o telegram_chat_ids en los secrets."
    errores = _enviar_a_todos(
        token, ids, "🔔 <b>Prueba de notificaciones</b>\nSi ves esto, el aviso al administrador funciona."
    )
    if errores:
        return False, "No se pudo enviar a: " + " | ".join(errores)
    return True, f"Mensaje de prueba enviado a {len(ids)} chat(s)."


def ui_probar_telegram():
    with st.expander("🔔 Notificaciones al celular (Telegram)"):
        if telegram_configurado():
            st.success("Telegram está configurado.")
            if st.button("📨 Enviar mensaje de prueba", key="btn_prueba_tg"):
                ok, msg = enviar_prueba()
                (st.success if ok else st.error)(msg)
        else:
            st.info("Aún no está configurado. Agrega `telegram_bot_token` y "
                    "`telegram_chat_ids` en los secrets de la app.")