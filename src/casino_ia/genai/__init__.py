from casino_ia.genai.explainer import explicar_cliente
from casino_ia.genai.rag import AsistentePoliticas

__all__ = ["explicar_cliente", "AsistentePoliticas", "telegram_bot"]

from casino_ia.genai import telegram_bot  # noqa: E402  (import al final: evita ciclos)
