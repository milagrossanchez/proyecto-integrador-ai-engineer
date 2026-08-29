"""Pruebas de la construcción de features y del scoring por reglas."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia.features.build import (
    agregar_scoring_reglas,
    construir_features_desde_sesiones,
    preparar_matriz_modelo,
)


@pytest.fixture
def sesiones():
    filas = []
    tid = 0
    for cli in range(900000, 900060):
        for d in range(1, 13):
            tid += 1
            filas.append(
                dict(
                    TransID=tid,
                    IdCliente=cli,
                    Mnum=700000 + (cli % 40),
                    IdSala=1 + (tid % 2),
                    StartTime=pd.Timestamp("2026-07-15") + pd.Timedelta(days=d, hours=(cli + d) % 24),
                    TimePlayed=300 + (cli * d) % 5000,
                    Hora=(cli + d) % 24,
                    CoinIn=10 + (cli * d) % 500,
                    Games=20,
                    AverageBet=1.5 + (d % 5),
                    Win=((-1) ** d) * ((cli * d) % 90),
                    TheoWin=(cli * d) % 40 / 10,
                    CompEarned=(d % 3),
                    PointsEarned=(cli * d) % 25,
                    TripNumber=0,
                )
            )
    return pd.DataFrame(filas)


def test_una_fila_por_cliente(sesiones):
    feats = construir_features_desde_sesiones(sesiones)
    assert len(feats) == sesiones["IdCliente"].nunique()
    assert feats["IdCliente"].is_unique


def test_columnas_esperadas(sesiones):
    feats = construir_features_desde_sesiones(sesiones)
    for col in ("CoinInTotal", "PctSesionesChasing", "DiasDesdeUltimaSesion", "RatioTendenciaCoinIn"):
        assert col in feats.columns


def test_scoring_tres_niveles(sesiones):
    feats = construir_features_desde_sesiones(sesiones)
    scored = agregar_scoring_reglas(feats)
    assert set(scored["NivelRiesgo"].unique()) <= {"Bajo", "Medio", "Alto"}
    assert scored["DecilPropension"].between(1, 10).all()


def test_matriz_sin_nulos(sesiones):
    feats = construir_features_desde_sesiones(sesiones)
    x = preparar_matriz_modelo(feats, ["CoinInPorHora", "VolatilidadResultado", "ApuestaMaxima"])
    assert not x.isna().any().any()
