import asyncio
import uuid

import httpx
from jose import jwt

from auth.security import create_access_token
from config import settings
from main import create_app


def _decode_unverified(token: str) -> dict:
    # We still decode with verification against the local config secret, since this smoke test is for
    # validating backend behavior, not token parsing robustness.
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


async def _register(client: httpx.AsyncClient, *, email: str, password: str, workspace_name: str) -> str:
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "workspace_name": workspace_name,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def _main() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) Protected route without auth should return 401
        resp = await client.get("/notes/")
        assert resp.status_code == 401

        # 2) Register 2 users (each gets their own workspace + owner token)
        pwd = "Password123!"
        user1_email = f"user1-{uuid.uuid4().hex}@example.com"
        user2_email = f"user2-{uuid.uuid4().hex}@example.com"

        token1 = await _register(
            client,
            email=user1_email,
            password=pwd,
            workspace_name="Team-A",
        )
        token1_claims = _decode_unverified(token1)

        token2 = await _register(
            client,
            email=user2_email,
            password=pwd,
            workspace_name="Team-B",
        )
        token2_claims = _decode_unverified(token2)

        workspace_id = int(token1_claims["wid"])
        user2_id = int(token2_claims["sub"])
        user1_id = int(token1_claims["sub"])

        headers_user1 = {"Authorization": f"Bearer {token1}"}

        # 3) Owner creates notes in their workspace
        public_note = await client.post(
            "/notes/",
            headers=headers_user1,
            json={"title": "Public note", "content": "hello public", "is_private": False},
        )
        public_note.raise_for_status()
        public_note_id = public_note.json()["id"]

        owner_private_note = await client.post(
            "/notes/",
            headers=headers_user1,
            json={"title": "Owner private note", "content": "hello private", "is_private": True},
        )
        owner_private_note.raise_for_status()
        owner_private_note_id = owner_private_note.json()["id"]

        # 4) Invite user2 into workspace A as a member
        invite = await client.post(
            "/workspaces/members/",
            headers=headers_user1,
            json={"email": user2_email, "role": "member"},
        )
        invite.raise_for_status()

        # 4.1) Verify membership is visible to the owner
        members_list = await client.get("/workspaces/members/", headers=headers_user1)
        members_list.raise_for_status()
        member_rows = {m["user_id"]: m for m in members_list.json()}
        assert user2_id in member_rows
        assert member_rows[user2_id]["role"] == "member"

        # 4.2) Verify workspaces endpoint is protected but workspace-aware
        my_ws = await client.get("/workspaces/me", headers=headers_user1)
        my_ws.raise_for_status()
        assert int(my_ws.json()["id"]) == workspace_id

        # 5) Create a member-scoped token for user2 in workspace A
        #    (The app's /auth/login picks a default workspace; this smoke test ensures RBAC works in the
        #     intended tenant by issuing a token with the right wid + role.)
        member_token = create_access_token({"sub": str(user2_id), "wid": str(workspace_id), "role": "member"})
        headers_member = {"Authorization": f"Bearer {member_token}"}

        # 5.1) Member cannot rename workspace (owner/admin only)
        rename_forbidden = await client.patch(
            "/workspaces/me",
            headers=headers_member,
            json={"name": "Should Fail"},
        )
        assert rename_forbidden.status_code == 403

        # Owner can rename workspace
        rename_ok = await client.patch(
            "/workspaces/me",
            headers=headers_user1,
            json={"name": "Team-A-Renamed"},
        )
        rename_ok.raise_for_status()

        # 6) Member can create their own private note
        member_note = await client.post(
            "/notes/",
            headers=headers_member,
            json={"title": "Member private note", "content": "mine", "is_private": True},
        )
        member_note.raise_for_status()
        member_note_id = member_note.json()["id"]

        # 7) Member can see:
        #    - public note (user1, is_private=False)
        #    - their own private note
        #    And cannot see:
        #    - owner private note
        notes_list = await client.get("/notes/", headers=headers_member)
        notes_list.raise_for_status()
        listed_ids = {n["id"] for n in notes_list.json()}

        assert public_note_id in listed_ids
        assert member_note_id in listed_ids
        assert owner_private_note_id not in listed_ids

        # 7.1) GET on private note should also be blocked for member
        private_get = await client.get(
            f"/notes/{owner_private_note_id}",
            headers=headers_member,
        )
        assert private_get.status_code == 403

        # 8) Member cannot update owner private note
        forbidden = await client.patch(
            f"/notes/{owner_private_note_id}",
            headers=headers_member,
            json={"content": "should fail"},
        )
        assert forbidden.status_code == 403

        # 9) Owner can delete member note
        delete_resp = await client.delete(f"/notes/{member_note_id}", headers=headers_user1)
        assert delete_resp.status_code == 204

        # 10) Notebooks are role-gated for create (owner/admin only)
        notebooks_list = await client.get("/notebooks/", headers=headers_member)
        notebooks_list.raise_for_status()
        assert isinstance(notebooks_list.json(), list)

        notebook_create_forbidden = await client.post(
            "/notebooks/",
            headers=headers_member,
            json={"name": "Should Fail Notebook"},
        )
        assert notebook_create_forbidden.status_code == 403

        print("Supabase smoke test: OK")
        print(f"workspace_id={workspace_id} user1_id={user1_id} user2_id={user2_id}")


if __name__ == "__main__":
    asyncio.run(_main())

