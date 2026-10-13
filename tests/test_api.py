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

    def telegram_status(self):
        return {"enabled": True, "connected": True, "username": "CasinoPalacioReal_bot"}

    def send_telegram(self, client_id, budget, chat_id):
        if client_id != 42:
            raise ClientNotFoundError(client_id)
        return {"enviado": True, "id_evento": "evt-1", "telegram": {"ok": True}}

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


def test_telegram_status_forwards_service_response(monkeypatch):
    monkeypatch.setattr(main, "get_dashboard_service", FakeService)

    response = TestClient(main.app).get("/api/v1/telegram/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "connected": True, "username": "CasinoPalacioReal_bot"}


def test_send_telegram_ok_and_not_found(monkeypatch):
    monkeypatch.setattr(main, "get_dashboard_service", FakeService)
    client = TestClient(main.app)

    ok = client.post("/api/v1/clients/42/telegram", json={"chat_id": "123"})
    assert ok.status_code == 200
    assert ok.json()["enviado"] is True

    not_found = client.post("/api/v1/clients/999/telegram", json={"chat_id": "123"})
    assert not_found.status_code == 404

    empty = client.post("/api/v1/clients/42/telegram", json={"chat_id": "   "})
    assert empty.status_code == 422