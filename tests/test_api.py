"""Pruebas del contrato HTTP sin cargar modelos ni depender de SQL Server."""

from fastapi.testclient import TestClient

from casino_ia.api import main
from casino_ia.api.service import ClientNotFoundError


class FakeService:
    scoring = [{"IdCliente": 42}]

    def __init__(self):
        self.portfolio_args = None

    def portfolio(self, *args):
        self.portfolio_args = args
        return {"budget": args[0], "clients": [], "pagination": {"total": 0}}

    def client(self, client_id, budget):
        if client_id != 42:
            raise ClientNotFoundError(client_id)
        return {"IdCliente": client_id, "Asignada": False}

    def explanation(self, client_id, budget):
        return {"explicacion": "Sin recompensa", "oferta": "No aplica", "mensaje": "No enviar"}

    def chat(self, question):
        return {"respuesta": question, "fuentes": []}


def test_portfolio_forwards_filters_and_pagination(monkeypatch):
    fake = FakeService()
    monkeypatch.setattr(main, "get_dashboard_service", lambda: fake)

    response = TestClient(main.app).get(
        "/api/v1/portfolio?budget=25000&risk=Medio&assignment=assigned&page=2&page_size=10"
    )

    assert response.status_code == 200
    assert response.json()["budget"] == 25000
    assert fake.portfolio_args == (25000, None, "Medio", "assigned", 2, 10)


def test_client_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(main, "get_dashboard_service", FakeService)

    response = TestClient(main.app).get("/api/v1/clients/999")

    assert response.status_code == 404


def test_chat_trims_and_rejects_empty_question(monkeypatch):
    monkeypatch.setattr(main, "get_dashboard_service", FakeService)
    client = TestClient(main.app)

    assert client.post("/api/v1/chat", json={"question": "  política  "}).json()[
        "respuesta"
    ] == "política"
    assert client.post("/api/v1/chat", json={"question": "   "}).status_code == 422