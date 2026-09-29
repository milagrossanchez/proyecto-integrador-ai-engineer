"""Pruebas del registro y medición de respuestas reales a las recompensas."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia.metrics.respuesta_real import calcular_metricas_respuesta


def _dataset():
    rng = np.random.default_rng(0)
    n = 120
    canal = rng.choice(["telegram", "web"], size=n, p=[0.7, 0.3])
    prob = rng.uniform(0.1, 0.9, size=n)
    respondio = (rng.random(n) < prob).astype(int)
    oferta = pd.Timestamp("2026-09-01") + pd.to_timedelta(rng.integers(0, 10, n), unit="D")
    respuesta = oferta + pd.to_timedelta(rng.integers(1, 48, n), unit="h")
    return pd.DataFrame(
        {
            "IdEvento": [f"e{i}" for i in range(n)],
            "IdCampana": "SIM-01",
            "IdCliente": rng.integers(900000, 900100, n),
            "Canal": canal,
            "TipoRecompensa": rng.choice(["baja", "media", "alta"], n),
            "NivelRiesgo": "Bajo",
            "ProbRespuestaPredicha": prob,
            "ValorIncrementalPredicho": rng.uniform(5, 50, n),
            "FechaOferta": oferta,
            "FechaRespuesta": respuesta,
            "Respondio": respondio,
            "ValorGenerado": np.where(respondio, rng.uniform(5, 60, n), 0.0),
        }
    )


def test_metricas_basicas():
    m = calcular_metricas_respuesta(_dataset())
    assert m["resueltos"] == 120
    assert 0.0 <= m["tasa_respuesta_global"] <= 1.0
    assert set(m["por_canal"]) <= {"telegram", "web"}
    assert m["tiempo_respuesta_promedio_horas"] > 0


def test_pendientes_no_cuentan_en_tasa():
    df = _dataset()
    df.loc[:9, ["Respondio", "FechaRespuesta", "ValorGenerado"]] = [None, pd.NaT, None]
    m = calcular_metricas_respuesta(df)
    assert m["pendientes"] == 10
    assert m["resueltos"] == 110


def test_calibracion_presente():
    m = calcular_metricas_respuesta(_dataset())
    assert "error_calibracion_absoluto_medio" in m
    assert m["error_calibracion_absoluto_medio"] >= 0


def test_dataset_vacio_no_rompe():
    vacio = pd.DataFrame(columns=[
        "IdEvento", "Canal", "TipoRecompensa", "NivelRiesgo",
        "ProbRespuestaPredicha", "FechaOferta", "FechaRespuesta",
        "Respondio", "ValorGenerado",
    ])
    m = calcular_metricas_respuesta(vacio)
    assert m["resueltos"] == 0
