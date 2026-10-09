"""Pruebas de la etapa 3 de respuesta por recompensa."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeRegressor

from casino_ia.models.response_nbo_calibrated import (
    REWARDS_NBO,
    TREATMENTS,
    ModeloRespuestaNBOCalibrado,
    assign_client_split,
    build_response_anchors,
    calibrate_mean_probability,
)


def evidence_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("HillstromEmail", "No E-Mail", 0.10),
            ("HillstromEmail", "Womens E-Mail", 0.15),
            ("HillstromEmail", "Mens E-Mail", 0.18),
            ("CriteoUpliftV21", "0", 0.04),
            ("CriteoUpliftV21", "1", 0.052),
        ],
        columns=["SourceDataset", "TreatmentLabel", "ObservedRate"],
    )


def test_anchor_mapping_is_ordered_and_explicit():
    anchors = build_response_anchors(evidence_frame())
    assert anchors.control_rate == 0.10
    assert np.isclose(anchors.low_rate, 0.13)
    assert anchors.medium_rate == 0.15
    assert anchors.high_rate == 0.18


def test_intercept_calibration_reaches_target_mean():
    raw = np.linspace(-4, 3, 500)
    probability = calibrate_mean_probability(raw, 0.17)
    assert np.isclose(probability.mean(), 0.17, atol=1e-8)
    assert probability.min() > 0
    assert probability.max() < 1


def test_client_split_is_stable_and_exclusive():
    clients = pd.Series([1, 1, 1, 2, 2, 3, 3, 3])
    split = assign_client_split(clients)
    frame = pd.DataFrame({"client": clients, "split": split})
    assert frame.groupby("client")["split"].nunique().eq(1).all()
    assert split.equals(assign_client_split(clients))


def test_treatment_contract_contains_control_and_three_rewards():
    assert TREATMENTS == ("control", "baja", "media", "alta")


def _modelo_entrenado_minimo() -> ModeloRespuestaNBOCalibrado:
    """Modelo con estimadores entrenados en datos triviales, solo para
    probar la forma de predict_options/predict_wide sin correr todo
    fit_select_evaluate (que requiere el histórico RCT simulado)."""
    inst = ModeloRespuestaNBOCalibrado()
    base = pd.DataFrame(
        {
            "IdCliente": [1, 2, 3, 4],
            "DiasDesdeUltimaSesion": [1, 5, 2, 9],
            "NroSesiones": [20, 15, 30, 10],
            "DiasActivos": [10, 8, 15, 5],
            "CoinInTotal": [5000, 3000, 8000, 2000],
            "CoinInPromedioSesion": [250, 200, 266, 200],
            "ValorTeoricoCasa": [500, 300, 800, 200],
            "CompsAcumulados": [10, 20, 5, 15],
            "PuntosAcumulados": [100, 200, 50, 150],
            "ApuestaMediaPromedio": [5.0, 4.0, 6.0, 3.0],
            "HorasJugadas": [20, 15, 30, 10],
            "AntiguedadDias": [100, 200, 50, 150],
            "RewardType": ["control", "baja", "media", "alta"],
        }
    )
    x = inst._matrix(base, fit=True)
    y_clas = np.array([0, 1, 0, 1])
    inst.response_model_ = LogisticRegression(max_iter=200).fit(x, y_clas)
    y_valor = np.array([10.0, 20.0, 15.0, 25.0])
    inst.value_model_ = DecisionTreeRegressor(max_depth=2, random_state=0).fit(x, y_valor)
    return inst


def test_predict_wide_expone_uplift_y_valor_incremental_causal():
    inst = _modelo_entrenado_minimo()
    features = pd.DataFrame(
        {
            "IdCliente": [1, 2],
            "DiasDesdeUltimaSesion": [1, 5],
            "NroSesiones": [20, 15],
            "DiasActivos": [10, 8],
            "CoinInTotal": [5000, 3000],
            "CoinInPromedioSesion": [250, 200],
            "ValorTeoricoCasa": [500, 300],
            "CompsAcumulados": [10, 20],
            "PuntosAcumulados": [100, 200],
            "ApuestaMediaPromedio": [5.0, 4.0],
            "HorasJugadas": [20, 15],
            "AntiguedadDias": [100, 200],
        }
    )
    wide = inst.predict_wide(features)

    assert "ControlProbability" in wide.columns
    for reward in REWARDS_NBO:
        for metric in (
            "ProbRespuesta",
            "ValorIncremental",
            "ValorEsperado",
            "UpliftProbability",
            "IncrementalExpectedValue",
        ):
            assert f"{metric}_{reward}" in wide.columns

    options = inst.predict_options(features)
    for reward in REWARDS_NBO:
        fila = options[options["RewardType"] == reward].iloc[0]
        esperado = fila["UpliftProbability"] * fila["ValueIncremental"] - fila["Cost"]
        assert fila["IncrementalExpectedValue"] == pytest.approx(esperado)
        assert fila["UpliftProbability"] == pytest.approx(
            fila["ResponseProbability"] - fila["ControlProbability"]
        )
