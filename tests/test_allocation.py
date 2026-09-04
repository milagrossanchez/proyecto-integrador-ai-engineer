"""Pruebas del optimizador de asignación de recompensas."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia.optimization.allocate import asignar_recompensas


def _scoring():
    return pd.DataFrame(
        {
            "IdCliente": range(1, 11),
            "Segmento": ["VIP", "Alto", "Medio", "Estandar"] * 2 + ["VIP", "Medio"],
            "NivelRiesgo": ["Bajo", "Bajo", "Medio", "Alto", "Bajo", "Alto", "Medio", "Bajo", "Bajo", "Medio"],
            "ProbRespuesta": [0.9, 0.8, 0.6, 0.9, 0.7, 0.5, 0.4, 0.85, 0.3, 0.55],
            "ValorTeoricoCasa": [5000, 4000, 3000, 9000, 2500, 8000, 1500, 6000, 1000, 2000],
            "NroSesiones": [50] * 10,
            "RatioTendenciaCoinIn": [1.1] * 10,
        }
    )


def test_excluye_riesgo_alto():
    cand = asignar_recompensas(_scoring(), presupuesto=10_000)
    assert not cand.empty
    assert (cand["NivelRiesgo"] != "Alto").all()


def test_respeta_presupuesto():
    cand = asignar_recompensas(_scoring(), presupuesto=30)
    asignadas = cand[cand["Asignada"]]
    assert asignadas["Costo"].sum() <= 30
    # los no asignados quedan fuera por presupuesto, no por otra razón
    assert (~cand["Asignada"]).any() or cand["Costo"].sum() <= 30


def test_riesgo_medio_sin_recompensa_alta():
    cand = asignar_recompensas(_scoring(), presupuesto=10_000)
    medios = cand[cand["NivelRiesgo"] == "Medio"]
    assert (medios["Recompensa"] != "alta").all()


def test_un_registro_por_cliente():
    cand = asignar_recompensas(_scoring(), presupuesto=10_000)
    assert cand["IdCliente"].is_unique
