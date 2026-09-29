"""Pruebas del canal de Telegram en modo dry-run (sin TELEGRAM_BOT_TOKEN)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia.config import TELEGRAM
from casino_ia.genai import telegram_bot as tb


def test_dry_run_activo_sin_token():
    assert TELEGRAM.enabled is False  # entorno de test: sin token configurado


def test_enviar_oferta_riesgo_alto_no_envia():
    ficha = {"IdCliente": 1, "NivelRiesgo": "Alto", "Asignada": True, "Recompensa": "baja"}
    r = tb.enviar_oferta("chat123", ficha)
    assert r["enviado"] is False


def test_enviar_oferta_sin_asignacion_no_envia():
    ficha = {"IdCliente": 1, "NivelRiesgo": "Bajo", "Asignada": False}
    r = tb.enviar_oferta("chat123", ficha)
    assert r["enviado"] is False


def test_enviar_oferta_valida_registra_evento_pendiente():
    ficha = {
        "IdCliente": 900001,
        "NivelRiesgo": "Bajo",
        "Asignada": True,
        "Recompensa": "media",
        "ProbRespuesta": 0.7,
        "ValorIncremental": 20.0,
        "NombreCompleto": "Cliente Prueba",
    }
    r = tb.enviar_oferta("chat456", ficha, id_campana="TEST")
    assert r["enviado"] is True
    assert r["telegram"]["dry_run"] is True
    assert r["id_evento"]


def test_procesar_boton_si_marca_respuesta_positiva():
    ficha = {
        "IdCliente": 900002, "NivelRiesgo": "Bajo", "Asignada": True,
        "Recompensa": "baja", "ProbRespuesta": 0.5, "ValorIncremental": 10.0,
    }
    tb.enviar_oferta("chatBoton", ficha, id_campana="TEST")
    update = {
        "callback_query": {
            "data": "recompensa_si",
            "message": {"chat": {"id": "chatBoton"}},
        }
    }
    r = tb.procesar_actualizacion(update)
    assert r["procesado"] is True
    assert r["respondio"] is True


def test_procesar_texto_libre_usa_el_asistente_rag():
    update = {"message": {"chat": {"id": "chatTexto"}, "text": "Que incluye la recompensa media?"}}
    r = tb.procesar_actualizacion(update)
    assert r["procesado"] is True
    assert r["tipo"] == "texto_libre"
    assert r["telegram"]["dry_run"] is True
