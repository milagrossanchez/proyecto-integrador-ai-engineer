"""Capa de IA generativa: explicación de scores y generación de la oferta.

Toma la ficha de un cliente (features + scores + recompensa asignada) y produce:
  - explicacion: por qué tiene ese nivel de riesgo y esa propensión
  - oferta: recompensa concreta y su justificación
  - mensaje: comunicación personalizada

Guardrail: si NivelRiesgo == 'Alto' no se genera oferta; se devuelve una nota de
derivación al protocolo de juego responsable.

Si no hay ANTHROPIC_API_KEY, funciona en modo *plantilla* (sin LLM) para que la
demo y las pruebas corran igual.
"""

from __future__ import annotations

import json

from casino_ia.config import LLM

SYSTEM_PROMPT = """Eres analista de fidelización de un casino. Explicas de forma
clara y breve, en español, por qué un cliente tiene cierto nivel de riesgo y
cierta probabilidad de respuesta, y propones una comunicación.
Reglas estrictas:
- Usa solo los datos que te doy. No inventes cifras.
- Nunca sugieras aumentar el estímulo de juego a un cliente de riesgo alto.
- Devuelve SOLO un JSON con las claves: explicacion, oferta, mensaje.
"""


def _resumen_senales(ficha: dict) -> list[str]:
    s = []
    if ficha.get("PctSesionesChasing", 0) >= 0.1:
        s.append(f"persigue pérdidas en el {ficha['PctSesionesChasing']:.0%} de las sesiones")
    if ficha.get("PctSesionesLargas", 0) >= 0.15:
        s.append(f"{ficha['PctSesionesLargas']:.0%} de sesiones de más de 2 horas")
    if ficha.get("PctJuegoMadrugada", 0) >= 0.25:
        s.append(f"{ficha['PctJuegoMadrugada']:.0%} de juego en horario de madrugada")
    if ficha.get("DiasDesdeUltimaSesion", 99) <= 3:
        s.append("actividad muy reciente")
    if ficha.get("RatioTendenciaCoinIn", 1) and ficha["RatioTendenciaCoinIn"] >= 1:
        s.append("tendencia de gasto al alza")
    if ficha.get("CompsAcumulados", 0) > 0:
        s.append("ya usa beneficios del programa")
    return s


def _plantilla(ficha: dict) -> dict:
    nivel = ficha.get("NivelRiesgo", "Bajo")
    senales = _resumen_senales(ficha)
    if nivel == "Alto":
        return {
            "explicacion": (
                f"El cliente {ficha.get('IdCliente')} se clasifica como riesgo ALTO: "
                + (", ".join(senales) if senales else "patrones de intensidad elevada")
                + "."
            ),
            "oferta": "No aplica. Cliente excluido de campañas de incentivo.",
            "mensaje": (
                "Derivar al equipo de juego responsable para seguimiento. "
                "No enviar comunicación promocional."
            ),
        }
    prob = ficha.get("ProbRespuesta", 0)
    rec = ficha.get("Recompensa", "media")
    return {
        "explicacion": (
            f"Riesgo {nivel.lower()} y probabilidad de respuesta {prob:.0%}. "
            + ("Señales: " + ", ".join(senales) + "." if senales else "")
        ),
        "oferta": f"Recompensa {rec}: bono de juego + beneficio de cortesía acorde a su segmento.",
        "mensaje": (
            f"Hola, {ficha.get('NombreCompleto', 'estimado cliente')}. "
            "Tenemos un beneficio pensado para tu próxima visita a Casino Palacio Real. "
            "Acércate a recepción para activarlo."
        ),
    }


def explicar_cliente(ficha: dict) -> dict:
    """Devuelve {explicacion, oferta, mensaje}. Usa LLM si hay API key."""
    if ficha.get("NivelRiesgo") == "Alto" or not LLM.enabled:
        return _plantilla(ficha)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=LLM.api_key)
        msg = client.messages.create(
            model=LLM.model,
            max_tokens=LLM.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(ficha, ensure_ascii=False, default=str)}],
        )
        texto = msg.content[0].text
        data = json.loads(texto[texto.index("{") : texto.rindex("}") + 1])
        return {k: data.get(k, "") for k in ("explicacion", "oferta", "mensaje")}
    except Exception:  # noqa: BLE001 - la demo no debe caerse por el LLM
        return _plantilla(ficha)
