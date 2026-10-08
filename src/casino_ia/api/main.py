"""FastAPI app: interfaz HTTP para el dashboard React administrativo."""

from __future__ import annotations

import os
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from casino_ia import config
from casino_ia.api.service import (
    ClientNotFoundError,
    DashboardService,
    get_dashboard_service,
)

app = FastAPI(
    title="Casino Palacio Real API",
    version="1.0.0",
    description="API local para el dashboard administrativo de scoring y recompensas.",
)
origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)


def _service() -> DashboardService:
    try:
        return get_dashboard_service()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo cargar la cartera o los modelos. Revisa la API y los logs.",
        ) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/ready")
def readiness(service: Annotated[DashboardService, Depends(_service)]) -> dict[str, int | str]:
    return {
        "status": "ready",
        "clients": int(len(service.scoring)),
        "nbo_version": service.nbo_version,
    }


@app.get("/api/v1/portfolio")
def portfolio(
    service: Annotated[DashboardService, Depends(_service)],
    budget: Annotated[float, Query(gt=0, le=1_000_000)] = config.REWARDS.presupuesto,
    search: Annotated[str | None, Query(max_length=80)] = None,
    risk: Literal["Bajo", "Medio", "Alto"] | None = None,
    assignment: Literal["assigned", "not_assigned"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    return service.portfolio(budget, search, risk, assignment, page, page_size)


@app.get("/api/v1/clients/{client_id}")
def client(
    client_id: int,
    service: Annotated[DashboardService, Depends(_service)],
    budget: Annotated[float, Query(gt=0, le=1_000_000)] = config.REWARDS.presupuesto,
) -> dict:
    try:
        return service.client(client_id, budget)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.") from exc


@app.post("/api/v1/clients/{client_id}/explanation")
def explanation(
    client_id: int,
    service: Annotated[DashboardService, Depends(_service)],
    budget: Annotated[float, Query(gt=0, le=1_000_000)] = config.REWARDS.presupuesto,
) -> dict[str, str]:
    try:
        return service.explanation(client_id, budget)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.") from exc


@app.post("/api/v1/chat")
def chat(
    request: ChatRequest,
    service: Annotated[DashboardService, Depends(_service)],
) -> dict:
    return service.chat(request.question)