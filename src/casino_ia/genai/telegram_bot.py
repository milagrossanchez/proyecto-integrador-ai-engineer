"""Canal de Telegram: notifica la recompensa al cliente y captura su respuesta.

Dos flujos:

1. `enviar_oferta(chat_id, ficha)` — se llama desde el orquestador cuando el
   optimizador asignó una recompensa a un cliente con `IdTelegramChat`
   registrado. Envía el mensaje generado por `genai.explainer` con dos
   botones (Sí / No), y dispara `metrics.registrar_resultado` con la oferta
   como "pendiente".

2. `procesar_actualizacion(update)` — se llama desde el webhook que Telegram
   invoca por cada evento nuevo (ver `docs/arquitectura_produccion.md`,
   banda 2: "Telegram Bot API (webhook HTTPS)"). Dos casos:
     - El cliente tocó un botón (Sí/No) -> respuesta estructurada, se cierra
       el evento con `metrics.actualizar_respuesta`.
     - El cliente escribió texto libre (o el operador de marketing pregunta
       algo por Telegram) -> se delega al mismo `AsistentePoliticas` (RAG)
       que usa el widget web, para que sea UN solo motor de chat en todos
       los canales.

Sin `TELEGRAM_BOT_TOKEN` configurado, todo corre en modo *dry-run*: arma los
mensajes y los devuelve/loguea, no llama a la API real de Telegram. Así el
código se puede probar y demostrar sin depender de credenciales externas.
"""

from __future__ import annotations

import logging

from casino_ia.config import TELEGRAM
from casino_ia.genai.explainer import explicar_cliente
from casino_ia.genai.rag import AsistentePoliticas
from casino_ia.metrics.respuesta_real import actualizar_respuesta, registrar_resultado

log = logging.getLogger(__name__)

_BOTON_SI = "recompensa_si"
_BOTON_NO = "recompensa_no"

# eventos pendientes en memoria: id_evento por (chat_id, id_campana). En
# producción esto se resuelve con una consulta a la tabla de resultados
# (buscar el evento "pendiente" más reciente de ese chat_id), no en memoria.
_EVENTOS_PENDIENTES: dict[str, str] = {}


def _teclado_si_no() -> dict:
    return {
        "inline_keyboard": [[
            {"text": "Sí, me interesa 🎁", "callback_data": _BOTON_SI},
            {"text": "No, gracias", "callback_data": _BOTON_NO},
        ]]
    }


def _llamar_api(metodo: str, payload: dict) -> dict:
    if not TELEGRAM.enabled:
        log.info("[dry-run] Telegram.%s payload=%s", metodo, payload)
        return {"ok": True, "dry_run": True, "metodo": metodo, "payload": payload}
    import requests

    r = requests.post(TELEGRAM.api_url(metodo), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def enviar_oferta(chat_id: str, ficha: dict, id_campana: str = "PROD") -> dict:
    """Envía la oferta de recompensa por Telegram y registra el evento pendiente."""
    if ficha.get("NivelRiesgo") == "Alto" or not ficha.get("Asignada"):
        return {"enviado": False, "motivo": "sin oferta que enviar (riesgo alto o no asignada)"}

    textos = explicar_cliente(ficha)
    resultado = _llamar_api(
        "sendMessage",
        {"chat_id": chat_id, "text": textos["mensaje"], "reply_markup": _teclado_si_no()},
    )

    id_evento = registrar_resultado(
        id_campana=id_campana,
        id_cliente=ficha["IdCliente"],
        canal="telegram",
        tipo_recompensa=ficha["Recompensa"],
        nivel_riesgo=ficha["NivelRiesgo"],
        prob_respuesta_predicha=float(ficha.get("ProbRespuesta", 0.0)),
        valor_incremental_predicho=float(ficha.get("ValorIncremental", 0.0) or 0.0),
    )
    _EVENTOS_PENDIENTES[str(chat_id)] = id_evento
    return {"enviado": True, "id_evento": id_evento, "telegram": resultado}


def procesar_actualizacion(update: dict) -> dict:
    """Procesa un update entrante del webhook de Telegram."""
    if "callback_query" in update:
        return _procesar_boton(update["callback_query"])
    if "message" in update and "text" in update["message"]:
        return _procesar_texto_libre(update["message"])
    return {"procesado": False, "motivo": "tipo de update no manejado"}


def _procesar_boton(callback: dict) -> dict:
    chat_id = str(callback["message"]["chat"]["id"])
    dato = callback["data"]
    id_evento = _EVENTOS_PENDIENTES.pop(chat_id, None)

    respondio = 1 if dato == _BOTON_SI else 0
    if id_evento:
        actualizar_respuesta(id_evento, respondio=respondio)

    texto = "¡Genial! Un asesor te contacta para activar tu beneficio." if respondio \
        else "Sin problema, seguimos atentos a tu próxima visita."
    resultado = _llamar_api("sendMessage", {"chat_id": chat_id, "text": texto})
    return {"procesado": True, "tipo": "boton", "respondio": bool(respondio),
            "id_evento": id_evento, "telegram": resultado}


def _procesar_texto_libre(mensaje: dict) -> dict:
    chat_id = str(mensaje["chat"]["id"])
    pregunta = mensaje["text"]
    asistente = AsistentePoliticas()
    r = asistente.responder(pregunta)
    resultado = _llamar_api("sendMessage", {"chat_id": chat_id, "text": r["respuesta"]})
    return {"procesado": True, "tipo": "texto_libre", "pregunta": pregunta,
            "fuentes": r["fuentes"], "telegram": resultado}
