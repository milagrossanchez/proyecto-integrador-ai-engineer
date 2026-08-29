"""Optimización de la asignación de recompensas.

Dado el scoring por cliente (riesgo + probabilidad de respuesta + valor teórico),
elige qué recompensa asignar a cada cliente maximizando el retorno esperado de la
campaña sujeto a un presupuesto.

    valor_esperado(c, r) = P(respuesta | c) * uplift_valor(c) - costo(r)

Restricciones:
  * presupuesto total de la campaña
  * NivelRiesgo == 'Alto'  -> no elegible (guardrail de juego responsable)
  * NivelRiesgo == 'Medio' -> solo recompensa 'baja' o 'media'

Método: ranking por eficiencia (valor_esperado / costo) y selección greedy tipo
mochila hasta agotar el presupuesto. El baseline de comparación es la asignación
por reglas de segmento.
"""

from __future__ import annotations

import pandas as pd

from casino_ia.config import REWARDS

RECOMPENSAS = ("alta", "media", "baja")
_PERMITIDAS_POR_RIESGO = {
    "Bajo": ("alta", "media", "baja"),
    "Medio": ("media", "baja"),
    "Alto": (),
}


def _uplift_valor(fila: pd.Series) -> float:
    """Valor incremental esperado si el cliente responde.

    Se aproxima como una fracción del valor teórico de la casa por sesión,
    ajustada por la tendencia reciente de actividad.
    """
    base = max(float(fila.get("ValorTeoricoCasa", 0.0)), 0.0)
    por_sesion = base / max(float(fila.get("NroSesiones", 1)), 1.0)
    tendencia = float(fila.get("RatioTendenciaCoinIn", 1.0) or 1.0)
    return por_sesion * REWARDS.factor_uplift * min(max(tendencia, 0.5), 2.0)


def asignar_recompensas(
    scoring: pd.DataFrame,
    presupuesto: float | None = None,
    costos: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Devuelve el plan de asignación y una columna de decisión por cliente.

    `scoring` debe tener: IdCliente, NivelRiesgo, ProbRespuesta, ValorTeoricoCasa,
    NroSesiones, RatioTendenciaCoinIn, Segmento.
    """
    presupuesto = REWARDS.presupuesto if presupuesto is None else presupuesto
    costos = costos or REWARDS.costo

    candidatos = []
    for _, fila in scoring.iterrows():
        permitidas = _PERMITIDAS_POR_RIESGO.get(str(fila["NivelRiesgo"]), ())
        if not permitidas:
            continue
        uplift = _uplift_valor(fila)
        p = float(fila["ProbRespuesta"])
        for r in permitidas:
            ve = p * uplift - costos[r]
            if ve <= 0:
                continue
            candidatos.append(
                {
                    "IdCliente": fila["IdCliente"],
                    "Segmento": fila.get("Segmento"),
                    "NivelRiesgo": fila["NivelRiesgo"],
                    "ProbRespuesta": round(p, 4),
                    "Recompensa": r,
                    "Costo": costos[r],
                    "ValorEsperado": round(ve, 2),
                    "Eficiencia": round(ve / costos[r], 3),
                }
            )

    cand = pd.DataFrame(candidatos)
    if cand.empty:
        return cand

    # una sola recompensa por cliente: la de mayor valor esperado
    cand = cand.sort_values("ValorEsperado", ascending=False).drop_duplicates("IdCliente")

    # selección greedy por eficiencia dentro del presupuesto
    cand = cand.sort_values("Eficiencia", ascending=False).reset_index(drop=True)
    gasto_acum = cand["Costo"].cumsum()
    cand["Asignada"] = gasto_acum <= presupuesto

    plan = cand[cand["Asignada"]].copy()
    plan.attrs["presupuesto"] = presupuesto
    plan.attrs["gasto_total"] = float(plan["Costo"].sum())
    plan.attrs["valor_esperado_total"] = float(plan["ValorEsperado"].sum())
    plan.attrs["clientes_asignados"] = len(plan)
    return plan


def baseline_reglas(scoring: pd.DataFrame, costos: dict[str, float] | None = None) -> pd.DataFrame:
    """Asignación por reglas de segmento (para comparar contra el optimizador)."""
    costos = costos or REWARDS.costo
    regla = {"VIP": "alta", "Alto": "media", "Medio": "baja", "Estandar": "baja"}
    df = scoring.copy()
    df = df[df["NivelRiesgo"] != "Alto"]
    df["Recompensa"] = df["Segmento"].map(regla).fillna("baja")
    df["Costo"] = df["Recompensa"].map(costos)
    df["ValorEsperado"] = df.apply(
        lambda f: float(f["ProbRespuesta"]) * _uplift_valor(f) - f["Costo"], axis=1
    ).round(2)
    return df
