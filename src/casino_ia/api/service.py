"""Servicios de cartera compartidos por la API, independientes de Streamlit."""

from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.genai import AsistentePoliticas, explicar_cliente
from casino_ia.models import (
    ModeloRespuesta,
    ModeloRespuestaNBO,
    ModeloRespuestaNBOCalibrado,
    ModeloRiesgo,
)
from casino_ia.optimization.allocate import asignar_recompensas, baseline_reglas

_COLUMNAS_LISTADO = [
    "IdCliente",
    "NombreCompleto",
    "Segmento",
    "NivelRiesgo",
    "CoinInTotal",
    "ProbRespuesta",
    "Recompensa",
    "Costo",
    "ValorEsperado",
    "Asignada",
    "MotivoDecision",
    "EsPerfilAtipico",
]
_COLUMNAS_FICHA = [
    "IdCliente",
    "NombreCompleto",
    "Segmento",
    "NivelRiesgo",
    "RiesgoScore",
    "EsPerfilAtipico",
    "ProbRespuesta",
    "DecilPropension",
    "CoinInTotal",
    "CoinInPromedioSesion",
    "ValorTeoricoCasa",
    "NroSesiones",
    "DiasActivos",
    "DiasDesdeUltimaSesion",
    "AntiguedadDias",
    "PctSesionesChasing",
    "PctSesionesLargas",
    "PctJuegoMadrugada",
    "DuracionPromedioMin",
    "DuracionMaximaMin",
    "ApuestaMediaPromedio",
    "VolatilidadResultado",
    "RatioTendenciaCoinIn",
    "Recompensa",
    "Costo",
    "ValorIncremental",
    "ValorEsperado",
    "Asignada",
    "MotivoDecision",
]


class ClientNotFoundError(LookupError):
    """La cartera no contiene el identificador solicitado."""


class DashboardService:
    """Carga artefactos una vez y prepara vistas usando la lógica de negocio actual."""

    def __init__(self) -> None:
        model_paths = [
            config.MODELS_STORE / "modelo_riesgo.joblib",
            config.MODELS_STORE / "modelo_respuesta.joblib",
        ]
        missing = [path.name for path in model_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Faltan modelos entrenados: "
                + ", ".join(missing)
                + ". Ejecuta scripts/train_models.py antes de iniciar la API."
            )

        features = cargar_features_cliente()
        risk = ModeloRiesgo.load(model_paths[0])
        response = ModeloRespuesta.load(model_paths[1])

        ruta_calibrado = config.MODELS_STORE / "modelo_respuesta_nbo_calibrado.joblib"
        if ruta_calibrado.exists():
            response_nbo = ModeloRespuestaNBOCalibrado.load(ruta_calibrado)
            self.nbo_version = "V2 calibrado (evidencia RCT Hillstrom/Criteo)"
        else:
            ruta_legacy = config.MODELS_STORE / "modelo_respuesta_nbo.joblib"
            if not ruta_legacy.is_file():
                raise FileNotFoundError(
                    "Falta modelo_respuesta_nbo.joblib o modelo_respuesta_nbo_calibrado.joblib. "
                    "Ejecuta scripts/train_models.py o scripts/train_response_nbo.py."
                )
            response_nbo = ModeloRespuestaNBO.load(ruta_legacy)
            self.nbo_version = "V2 semi-sintético (pendiente: cargar ext.HillstromEmail/CriteoUpliftV21)"

        self.scoring = (
            risk.predict(features)[
                ["IdCliente", "NivelRiesgo", "RiesgoScore", "EsPerfilAtipico"]
            ]
            .merge(response.predict_proba(features), on="IdCliente")
            .merge(response_nbo.predict_wide(features), on="IdCliente", validate="one_to_one")
            .merge(features, on="IdCliente", validate="one_to_one")
        )
        self._allocations: dict[float, tuple[pd.DataFrame, pd.DataFrame]] = {}
        self._assistant: AsistentePoliticas | None = None

    def _allocation(self, budget: float) -> tuple[pd.DataFrame, pd.DataFrame]:
        key = round(float(budget), 2)
        if key not in self._allocations:
            if len(self._allocations) >= 16:
                self._allocations.clear()
            decisions = asignar_recompensas(self.scoring, presupuesto=key)
            baseline = baseline_reglas(self.scoring)
            self._allocations[key] = decisions, baseline
        return self._allocations[key]

    @staticmethod
    def _records(frame: pd.DataFrame, columns: list[str] | None = None) -> list[dict]:
        selected = frame.loc[:, columns] if columns else frame
        return json.loads(selected.to_json(orient="records", date_format="iso"))

    def portfolio(
        self,
        budget: float,
        search: str | None,
        risk: str | None,
        assignment: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        decisions, baseline = self._allocation(budget)
        assigned = decisions[decisions["Asignada"]]
        suggested = decisions[decisions["RecompensaSugerida"].notna()]
        view = self.scoring.drop(
            columns=["NivelRiesgo", "ProbRespuesta", "Segmento"], errors="ignore"
        ).merge(decisions, on="IdCliente", validate="one_to_one")

        if search:
            view = view[view["IdCliente"].astype(str).str.contains(search.strip(), case=False)]
        if risk:
            view = view[view["NivelRiesgo"] == risk]
        if assignment == "assigned":
            view = view[view["Asignada"]]
        elif assignment == "not_assigned":
            view = view[~view["Asignada"]]

        total = len(view)
        start = (page - 1) * page_size
        clients = view.sort_values("Eficiencia", ascending=False, na_position="last").iloc[
            start : start + page_size
        ]
        risk_counts = self.scoring["NivelRiesgo"].value_counts()
        reward_counts = assigned["Recompensa"].value_counts()
        spent = float(assigned["Costo"].sum())

        return {
            "budget": budget,
            "summary": {
                "clients": int(len(self.scoring)),
                "high_risk": int(risk_counts.get("Alto", 0)),
                "eligible": int(len(suggested)),
                "assigned": int(len(assigned)),
                "spent": round(spent, 2),
                "remaining_budget": round(max(budget - spent, 0), 2),
                "expected_value": round(float(assigned["ValorEsperado"].sum()), 2),
            },
            "baseline": {
                "eligible": int(len(baseline)),
                "spent": round(float(baseline["Costo"].sum()), 2),
                "expected_value": round(float(baseline["ValorEsperado"].sum()), 2),
            },
            "risk_distribution": [
                {"name": name, "value": int(risk_counts.get(name, 0))}
                for name in ("Bajo", "Medio", "Alto")
            ],
            "reward_distribution": [
                {"name": name, "value": int(reward_counts.get(name, 0))}
                for name in ("alta", "media", "baja")
            ],
            "clients": self._records(clients, _COLUMNAS_LISTADO),
            "pagination": {"page": page, "page_size": page_size, "total": total},
        }

    def client(self, client_id: int, budget: float) -> dict:
        decisions, _ = self._allocation(budget)
        row = self.scoring[self.scoring["IdCliente"] == client_id]
        if row.empty:
            raise ClientNotFoundError(client_id)
        decision = decisions[decisions["IdCliente"] == client_id]
        ficha = row.drop(
            columns=["ProbRespuesta", "NivelRiesgo", "Segmento"], errors="ignore"
        ).merge(decision, on="IdCliente", validate="one_to_one")
        return self._records(ficha, _COLUMNAS_FICHA)[0]

    def explanation(self, client_id: int, budget: float) -> dict:
        return explicar_cliente(self.client(client_id, budget))

    def chat(self, question: str) -> dict:
        if self._assistant is None:
            self._assistant = AsistentePoliticas()
        return self._assistant.responder(question)


@lru_cache(maxsize=1)
def get_dashboard_service() -> DashboardService:
    return DashboardService()