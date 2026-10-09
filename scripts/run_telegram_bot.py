"""Proceso de Telegram en vivo: escucha mensajes reales por *long polling*
(no requiere webhook ni URL pública, así que no depende de que el túnel de
ngrok siga apuntando al mismo lugar) y los delega a
`casino_ia.genai.telegram_bot.procesar_actualizacion` — el mismo motor que
ya corre en modo dry-run en los tests.

`/start` responde con el `chat_id` de quien escribe, para poder pegarlo en
la pestaña "Cliente" de la web y probar `enviar_oferta()` con un chat real.

Requiere TELEGRAM_BOT_TOKEN en el entorno (.env). Se detiene con Ctrl+C.

Uso:
    python scripts/run_telegram_bot.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests

from casino_ia.config import TELEGRAM
from casino_ia.genai.telegram_bot import procesar_actualizacion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telegram_bot_runner")

POLL_TIMEOUT_S = 25


def _get_updates(offset: int | None) -> list[dict]:
    params = {"timeout": POLL_TIMEOUT_S}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(TELEGRAM.api_url("getUpdates"), params=params, timeout=POLL_TIMEOUT_S + 10)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        log.error("getUpdates respondió ok=false: %s", body)
        return []
    return body["result"]


def _enviar_texto(chat_id: str, texto: str) -> None:
    requests.post(
        TELEGRAM.api_url("sendMessage"),
        json={"chat_id": chat_id, "text": texto},
        timeout=10,
    )


def _es_comando_start(update: dict) -> bool:
    mensaje = update.get("message") or {}
    return mensaje.get("text", "").strip().lower() == "/start"


def main() -> None:
    if not TELEGRAM.enabled:
        log.error(
            "TELEGRAM_BOT_TOKEN no está configurado — nada que escuchar. "
            "Definilo en .env y volvé a correr este script."
        )
        return

    me = requests.get(TELEGRAM.api_url("getMe"), timeout=10).json()
    log.info("Conectado como @%s (%s)", me["result"]["username"], me["result"]["first_name"])

    offset: int | None = None
    log.info("Escuchando mensajes (long polling, Ctrl+C para detener)...")
    while True:
        try:
            updates = _get_updates(offset)
        except requests.RequestException as exc:
            log.warning("Error consultando Telegram (%s), reintento en 3s", exc)
            time.sleep(3)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                if _es_comando_start(update):
                    chat_id = str(update["message"]["chat"]["id"])
                    _enviar_texto(
                        chat_id,
                        "¡Hola! Soy el asistente de Casino Palacio Real.\n\n"
                        f"Tu chat_id es: {chat_id}\n"
                        "Pegalo en la pestaña \"Cliente\" de la web para probar "
                        "el envío de una oferta por este canal, o escribime "
                        "cualquier pregunta sobre políticas de recompensas.",
                    )
                    log.info("Nuevo /start de chat_id=%s", chat_id)
                    continue
                resultado = procesar_actualizacion(update)
                log.info("Update %s procesado: %s", update["update_id"], resultado.get("tipo", resultado))
            except Exception:
                log.exception("Error procesando update %s", update.get("update_id"))


if __name__ == "__main__":
    main()
