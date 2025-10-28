from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import copy
import hashlib
import sys
import types

import pytest

# Werkzeuge puede no estar instalado en entornos de prueba.
try:
    from werkzeug.security import generate_password_hash  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    security_module = types.ModuleType("security")

    def _generate_password_hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _check_password_hash(stored_hash: str, candidate: str) -> bool:
        return stored_hash == hashlib.sha256(candidate.encode("utf-8")).hexdigest()

    security_module.generate_password_hash = _generate_password_hash
    security_module.check_password_hash = _check_password_hash

    werkzeug_module = types.ModuleType("werkzeug")
    werkzeug_module.security = security_module

    sys.modules.setdefault("werkzeug", werkzeug_module)
    sys.modules["werkzeug.security"] = security_module

    generate_password_hash = _generate_password_hash

# PyJWT también puede no existir en entornos mínimos de pruebas.
try:
    import jwt  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    jwt_module = types.ModuleType("jwt")

    def _encode(payload, _secret, algorithm="HS256"):
        return f"stub-token-{payload.get('user_id', '')}"

    def _decode(token, _secret, algorithms=None):
        suffix = token.replace("stub-token-", "")
        return {"user_id": suffix}

    jwt_module.encode = _encode
    jwt_module.decode = _decode
    sys.modules["jwt"] = jwt_module

# El módulo python-dotenv no es imprescindible para ejecutar la lógica probada.
try:
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    dotenv_module = types.ModuleType("dotenv")

    def _load_dotenv(*_args, **_kwargs):
        return False

    dotenv_module.load_dotenv = _load_dotenv
    sys.modules["dotenv"] = dotenv_module

# requests se reemplaza por un stub mínimo para permitir el monkeypatch en tests.
try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    requests_module = types.ModuleType("requests")

    def _not_implemented(*_args, **_kwargs):
        raise RuntimeError("requests stub invoked sin monkeypatch")

    requests_module.get = _not_implemented  # type: ignore[attr-defined]
    sys.modules["requests"] = requests_module

# Psycopg2 se sustituye por un stub que evita conexiones reales.
try:
    import psycopg2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    psycopg2_module = types.ModuleType("psycopg2")

    def _connect(*_args, **_kwargs):
        raise RuntimeError("psycopg2 stub invocado")

    psycopg2_module.connect = _connect  # type: ignore[attr-defined]
    sys.modules["psycopg2"] = psycopg2_module

    extras_module = types.ModuleType("extras")

    class RealDictCursor:  # pragma: no cover
        pass

    extras_module.RealDictCursor = RealDictCursor
    sys.modules["psycopg2.extras"] = extras_module

# Flask no es necesario para las pruebas unitarias enfocadas en servicios.
try:
    from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    flask_module = types.ModuleType("flask")

    class Blueprint:  # Minimalista para registro de rutas
        def __init__(self, name, import_name=None):
            self.name = name
            self.import_name = import_name

        def route(self, _rule=None, **_options):  # pragma: no cover
            def decorator(func):
                return func

            return decorator

    def render_template(*_args, **_kwargs):
        return {}

    def redirect(location):  # pragma: no cover
        return {"redirect": location}

    def url_for(endpoint, **_kwargs):  # pragma: no cover
        return f"/stub/{endpoint}"

    def flash(message, category=None):  # pragma: no cover
        return {"message": message, "category": category}

    session = {}  # type: ignore

    class _Request:  # pragma: no cover
        form = {}
        files = {}

    request = _Request()

    def jsonify(payload):
        return payload

    flask_module.Blueprint = Blueprint
    flask_module.render_template = render_template
    flask_module.redirect = redirect
    flask_module.url_for = url_for
    flask_module.flash = flash
    flask_module.session = session
    flask_module.request = request
    flask_module.jsonify = jsonify

    sys.modules["flask"] = flask_module

# websockets se stubbea para evitar dependencias de red en pruebas.
try:
    import websockets  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    websockets_module = types.ModuleType("websockets")

    class ConnectionClosed(Exception):  # pragma: no cover
        pass

    exceptions_module = types.ModuleType("exceptions")
    exceptions_module.ConnectionClosed = ConnectionClosed
    websockets_module.exceptions = exceptions_module

    async def _serve(*_args, **_kwargs):
        raise RuntimeError("websockets stub invocado")

    websockets_module.serve = _serve  # type: ignore[attr-defined]
    sys.modules["websockets"] = websockets_module

# Stub para evitar inicialización real del controlador de soporte en __init__.
support_controller_stub = types.ModuleType("admin_panel.support.support_controller")
support_controller_stub.support_blueprint = object()
sys.modules.setdefault("admin_panel.support.support_controller", support_controller_stub)

from admin_panel.auth.auth_service import AuthService

from admin_panel.auth.auth_service import AuthService
from admin_panel.analytics.analytics_controller import AnalyticsService
from admin_panel.support.support_service import SupportService
from admin_panel.training.training_service import TrainingService
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.ticket import EscalationReason, Ticket, TicketStatus
from bot_siacasa.domain.entities.usuario import Usuario


class FakeDBConnector:
    """Stub liviano para simular operaciones básicas de base de datos."""

    def __init__(self, user_record: Optional[Dict[str, Any]] = None):
        self._user_record = user_record or {}
        self.executed_statements: List[Dict[str, Any]] = []

    def fetch_one(self, _query: str, _params: tuple) -> Optional[Dict[str, Any]]:
        if not self._user_record:
            return None
        return copy.deepcopy(self._user_record)

    def execute(self, query: str, params: tuple) -> None:
        self.executed_statements.append({"query": query, "params": params})

    # Métodos adicionales utilizados por TrainingService
    def fetch_all(self, _query: str, _params: tuple) -> List[Dict[str, Any]]:
        return []


def _build_ticket(ticket_id: str) -> Ticket:
    usuario = Usuario(id="user-1", nombre="Ana Torres")
    conversacion = Conversacion(id="conv-1", usuario=usuario)
    return Ticket(
        id=ticket_id,
        conversacion=conversacion,
        usuario=usuario,
        estado=TicketStatus.PENDING,
        razon_escalacion=EscalationReason.USER_REQUESTED,
    )


class DummyFile:
    """Objeto archivo minimalista para probar TrainingService."""

    def __init__(self, filename: str, content: bytes, content_type: str = "text/csv", should_fail: bool = False):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._should_fail = should_fail

    def save(self, destination: str) -> None:
        if self._should_fail:
            raise IOError("simulated save failure")
        Path(destination).write_bytes(self._content)


class MockResponse:
    """Respuesta HTTP falsa para probar AnalyticsService sin llamadas reales."""

    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_cp033_admin_login_success():
    hashed_password = generate_password_hash("admin123")
    user_record = {
        "id": "admin-1",
        "name": "Administrador QA",
        "email": "admin@example.com",
        "username": "admin",
        "password_hash": hashed_password,
        "role": "admin",
        "bank_code": "SIA",
        "bank_name": "Banco SIACASA",
        "is_active": True,
    }
    fake_db = FakeDBConnector(user_record=user_record)
    service = AuthService(fake_db)

    result = service.authenticate("admin", "admin123")

    assert result is not None
    assert result["name"] == "Administrador QA"
    assert "password_hash" not in result
    assert fake_db.executed_statements, "Se esperaba actualización de último inicio de sesión"


def test_cp034_admin_login_invalid_password():
    hashed_password = generate_password_hash("admin123")
    user_record = {
        "id": "admin-1",
        "name": "Administrador QA",
        "email": "admin@example.com",
        "username": "admin",
        "password_hash": hashed_password,
        "role": "admin",
        "bank_code": "SIA",
        "bank_name": "Banco SIACASA",
        "is_active": True,
    }
    fake_db = FakeDBConnector(user_record=user_record)
    service = AuthService(fake_db)

    result = service.authenticate("admin", "wrong-password")

    assert result is None
    assert not fake_db.executed_statements, "No debería registrar login con credenciales inválidas"


def test_cp035_metrics_weekly_summary(monkeypatch):
    service = AnalyticsService()
    sample_report = {
        "total_sessions": 5,
        "total_messages": 12,
        "escalated_sessions": 1,
        "avg_satisfaction_score": 4.6,
    }

    # Forzar reporte constante para los 7 días evaluados
    monkeypatch.setattr(service, "get_daily_report", lambda date=None: sample_report)

    weekly_stats = service.get_weekly_stats()

    assert len(weekly_stats) == 7
    assert all(item["sessions"] == sample_report["total_sessions"] for item in weekly_stats)
    assert all(item["satisfaction"] == sample_report["avg_satisfaction_score"] for item in weekly_stats)


def test_cp036_ticket_listing_pending():
    pending_tickets = [_build_ticket("ticket-1"), _build_ticket("ticket-2")]

    class FakeSupportRepository:
        def __init__(self, tickets):
            self.tickets = tickets
            self.received_bank_code = None

        def obtener_tickets_por_estado(self, estado, bank_code):
            self.received_bank_code = bank_code
            return self.tickets

    repo = FakeSupportRepository(pending_tickets)
    service = SupportService(repo)

    result = service.get_pending_tickets(bank_code="SIA")

    assert result == pending_tickets
    assert repo.received_bank_code == "SIA"


def test_cp037_training_upload_success(monkeypatch, tmp_path):
    content = b"id,pregunta,respuesta\n1,Hola,Hola mundo"
    dummy_file = DummyFile("dataset.csv", content)
    fake_db = FakeDBConnector()
    service = TrainingService(fake_db)
    service.upload_folder = tmp_path  # Aislar en carpeta temporal

    result = service.save_training_file(dummy_file, "Carga inicial", "admin-1", "SIA")

    assert result["status"] == "pending"
    assert Path(tmp_path).iterdir()
    assert fake_db.executed_statements, "Debe registrar el archivo en base de datos"


def test_cp038_training_upload_failure(tmp_path):
    dummy_file = DummyFile("dataset.csv", b"", should_fail=True)
    fake_db = FakeDBConnector()
    service = TrainingService(fake_db)
    service.upload_folder = tmp_path

    with pytest.raises(IOError):
        service.save_training_file(dummy_file, "Carga fallida", "admin-1", "SIA")


def test_cp039_report_export_success(monkeypatch):
    service = AnalyticsService()
    payload = {
        "total_sessions": 10,
        "total_messages": 40,
        "escalated_sessions": 2,
        "avg_satisfaction_score": 4.2,
    }

    def fake_get(url, timeout=5):
        return MockResponse(status_code=200, payload=payload)

    monkeypatch.setattr("admin_panel.analytics.analytics_controller.requests.get", fake_get)

    report = service.get_daily_report(date="2024-05-10")

    assert report == payload


def test_cp040_report_export_no_data(monkeypatch):
    service = AnalyticsService()

    def fake_get(url, timeout=5):
        return MockResponse(status_code=204, payload={})

    monkeypatch.setattr("admin_panel.analytics.analytics_controller.requests.get", fake_get)

    report = service.get_daily_report(date="2024-05-11")

    assert report == {}
