"""API tests for inbound email / WhatsApp integrations."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from auth.models import User, WorkspaceUser
from core.database.associations import note_attachments
from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from files.models import File
from integrations.models import InboundIdempotency, WhatsAppIdentityLink
from main import create_app
from notes.models import Note
from workspaces.models import Workspace


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "JSON"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "CHAR(36)"


INBOUND_KEY = "test-inbound-key"
WA_SECRET = "wa-app-secret"
WA_VERIFY = "wa-verify-token"

_TABLES = [
    Workspace.__table__,
    User.__table__,
    WorkspaceUser.__table__,
    Note.__table__,
    File.__table__,
    note_attachments,
    InboundIdempotency.__table__,
    WhatsAppIdentityLink.__table__,
]


def _prepare_sqlite_tables(sync_conn) -> None:
    # Postgres-only defaults like '[]'::jsonb break SQLite DDL.
    for table in _TABLES:
        for col in table.columns:
            if col.server_default is not None:
                text = str(getattr(col.server_default, "arg", col.server_default))
                if "jsonb" in text.lower() or "::" in text:
                    col.server_default = None
    for table in _TABLES:
        table.create(sync_conn, checkfirst=True)


@pytest.fixture
def inbound_settings(monkeypatch):
    from config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "INBOUND_API_KEY", INBOUND_KEY)
    monkeypatch.setattr(s, "INBOUND_HMAC_SECRET", "")
    monkeypatch.setattr(s, "INBOUND_AGENTIC_ENABLED", False)
    monkeypatch.setattr(s, "WHATSAPP_APP_SECRET", WA_SECRET)
    monkeypatch.setattr(s, "WHATSAPP_VERIFY_TOKEN", WA_VERIFY)
    monkeypatch.setattr(s, "OPENAI_API_KEY", None)
    monkeypatch.setattr(s, "GEMINI_API_KEY", None)
    monkeypatch.setattr(s, "NVIDIA_NIM_API_KEY", None)
    monkeypatch.setattr(s, "NVIDIA_API_KEY", None)
    return s


async def _seed_user_workspace(session: AsyncSession, email: str = "owner@example.com"):
    ws = Workspace(name="Main")
    session.add(ws)
    await session.flush()
    user = User(email=email, password_hash="x")
    session.add(user)
    await session.flush()
    session.add(WorkspaceUser(user_id=user.id, tenant_id=ws.id, role="owner"))
    await session.commit()
    return user, ws


async def _build_client(async_session):
    async def override_get_session():
        async with async_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return app, ASGITransport(app=app)


@pytest.mark.asyncio
async def test_inbound_email_auth_unknown_happy_reject_idempotent(inbound_settings):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(_prepare_sqlite_tables)

    app, transport = await _build_client(async_session)

    async with async_session() as session:
        await _seed_user_workspace(session)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/integrations/inbound/email",
            json={
                "message_id": "m1",
                "from_email": "owner@example.com",
                "subject": "Hello",
                "body": "World",
            },
        )
        assert resp.status_code == 401

        headers = {"X-Inbound-Api-Key": INBOUND_KEY}

        resp = await client.post(
            "/integrations/inbound/email",
            headers=headers,
            json={
                "message_id": "m-unknown",
                "from_email": "nobody@example.com",
                "subject": "X",
                "body": "Y",
            },
        )
        assert resp.status_code == 404

        resp = await client.post(
            "/integrations/inbound/email",
            headers=headers,
            json={
                "message_id": "m-happy",
                "from_email": "Owner@Example.com",
                "subject": "Meeting notes",
                "body": "Discussed roadmap",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Meeting notes"
        assert data["duplicate"] is False
        note_id = data["note_id"]

        resp2 = await client.post(
            "/integrations/inbound/email",
            headers=headers,
            json={
                "message_id": "m-happy",
                "from_email": "owner@example.com",
                "subject": "Meeting notes",
                "body": "Discussed roadmap",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True
        assert resp2.json()["note_id"] == note_id

        bad_b64 = base64.b64encode(b"\x89PNG fake image").decode("ascii")
        with patch(
            "integrations.ingest.detect_mime_type",
            return_value="image/png",
        ):
            resp3 = await client.post(
                "/integrations/inbound/email",
                headers=headers,
                json={
                    "message_id": "m-attach",
                    "from_email": "owner@example.com",
                    "subject": "With file",
                    "body": "See attach",
                    "attachments": [
                        {
                            "filename": "pic.png",
                            "content_base64": bad_b64,
                            "content_type": "image/png",
                        }
                    ],
                },
            )
        assert resp3.status_code == 200
        body3 = resp3.json()
        assert body3["note_id"]
        assert body3["attachments"][0]["status"] == "rejected"


@pytest.mark.asyncio
async def test_whatsapp_verify_signature_link_ingest(inbound_settings):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(_prepare_sqlite_tables)

    state = {"user_id": 1, "workspace_id": 1, "role": "owner"}

    async def override_get_session():
        async with async_session() as session:
            yield session

    async def override_ctx() -> RequestContext:
        return RequestContext(**state)  # type: ignore[arg-type]

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_context] = override_ctx
    transport = ASGITransport(app=app)

    async with async_session() as session:
        user, _ws = await _seed_user_workspace(session, email="wa@example.com")
        state["user_id"] = user.id
        state["workspace_id"] = _ws.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/integrations/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": WA_VERIFY,
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "12345"

        payload = {"entry": []}
        raw = json.dumps(payload).encode("utf-8")
        resp = await client.post(
            "/integrations/whatsapp/webhook",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=deadbeef",
            },
        )
        assert resp.status_code == 401

        start = await client.post(
            "/integrations/whatsapp/link/start",
            json={"phone": "+15551234567"},
        )
        assert start.status_code == 200
        code = start.json()["code"]
        confirm = await client.post(
            "/integrations/whatsapp/link/confirm",
            json={"phone": "+15551234567", "code": code},
        )
        assert confirm.status_code == 200
        assert confirm.json()["verified"] is True

        wa_payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.unlinked",
                                        "from": "19999999999",
                                        "type": "text",
                                        "text": {"body": "hello"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        raw = json.dumps(wa_payload).encode("utf-8")
        sig = hmac.new(WA_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        resp = await client.post(
            "/integrations/whatsapp/webhook",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["results"][0]["status"] == "rejected"

        wa_payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
            "id": "wamid.ok1",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Capture this thought"},
        }
        raw = json.dumps(wa_payload).encode("utf-8")
        sig = hmac.new(WA_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        resp = await client.post(
            "/integrations/whatsapp/webhook",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["results"][0]["status"] == "ok"
        note_id = resp.json()["results"][0]["note_id"]

        resp2 = await client.post(
            "/integrations/whatsapp/webhook",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["results"][0]["duplicate"] is True
        assert resp2.json()["results"][0]["note_id"] == note_id

        wa_payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
            "id": "wamid.media",
            "from": "15551234567",
            "type": "image",
            "image": {"id": "media1"},
        }
        raw = json.dumps(wa_payload).encode("utf-8")
        sig = hmac.new(WA_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        resp3 = await client.post(
            "/integrations/whatsapp/webhook",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )
        assert resp3.status_code == 200
        assert resp3.json()["results"][0]["status"] == "rejected"


@pytest.mark.asyncio
async def test_inbound_agentic_flag_off_and_tenancy(inbound_settings, monkeypatch):
    from config import get_settings

    monkeypatch.setattr(get_settings(), "INBOUND_AGENTIC_ENABLED", False)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(_prepare_sqlite_tables)

    app, transport = await _build_client(async_session)

    async with async_session() as session:
        user, ws = await _seed_user_workspace(session)
        ws2 = Workspace(name="Other")
        session.add(ws2)
        await session.flush()
        session.add(WorkspaceUser(user_id=user.id, tenant_id=ws2.id, role="member"))
        await session.commit()
        expected_wid = min(ws.id, ws2.id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/integrations/inbound/email",
            headers={"X-Inbound-Api-Key": INBOUND_KEY},
            json={
                "message_id": "m-agentic-off",
                "from_email": "owner@example.com",
                "subject": "Subject Title",
                "body": "Body text",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agentic"] is False
        assert data["title"] == "Subject Title"
        assert data["workspace_id"] == expected_wid
