"""Configuración central del proyecto.

Lee variables de entorno desde `.env` (ver `.env.example`) y expone rutas y
parámetros usados por todo el pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # opcional: si python-dotenv está instalado, carga .env automáticamente
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# --- Rutas del proyecto ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
METRICS = REPORTS / "metrics"
MODELS_STORE = ROOT / "models_store"
RAG_DOCS = ROOT / "rag" / "politicas"

CSV_SESIONES = DATA_RAW / "playersession_ficticio_100k.csv"

for _p in (DATA_INTERIM, DATA_PROCESSED, FIGURES, METRICS, MODELS_STORE):
    _p.mkdir(parents=True, exist_ok=True)


# --- Base de datos -------------------------------------------------------------
@dataclass(frozen=True)
class DBConfig:
    server: str = os.getenv("DB_SERVER", r"MILI\SQLEXPRESS")
    database: str = os.getenv("DB_NAME", "CasinoPalacioReal")
    driver: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    trusted: str = os.getenv("DB_TRUSTED_CONNECTION", "yes")
    user: str = os.getenv("DB_USER", "")
    password: str = os.getenv("DB_PASSWORD", "")

    def sqlalchemy_url(self) -> str:
        drv = self.driver.replace(" ", "+")
        if self.user:
            return (
                f"mssql+pyodbc://{self.user}:{self.password}@{self.server}/"
                f"{self.database}?driver={drv}"
            )
        return (
            f"mssql+pyodbc://@{self.server}/{self.database}"
            f"?driver={drv}&trusted_connection={self.trusted}"
        )


# --- IA generativa ------------------------------------------------------------
@dataclass(frozen=True)
class LLMConfig:
    api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "claude-sonnet-5")
    max_tokens: int = 1024

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


# --- Parámetros de negocio de la asignación de recompensas --------------------
@dataclass(frozen=True)
class RewardConfig:
    presupuesto: float = float(os.getenv("PRESUPUESTO_CAMPANA", "15000"))
    costo: dict[str, float] = field(
        default_factory=lambda: {
            "alta": float(os.getenv("COSTO_RECOMPENSA_ALTA", "40")),
            "media": float(os.getenv("COSTO_RECOMPENSA_MEDIA", "15")),
            "baja": float(os.getenv("COSTO_RECOMPENSA_BAJA", "5")),
        }
    )
    # fracción del valor teórico de la casa que se considera "uplift" recuperable
    factor_uplift: float = 0.15


DB = DBConfig()
LLM = LLMConfig()
REWARDS = RewardConfig()

# Fecha de corte del histórico simulado (último día con datos).
FECHA_CORTE = "2026-07-29"
