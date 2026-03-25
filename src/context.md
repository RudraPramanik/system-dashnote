.\.venv\Scripts\python -m fastapi dev src.main:app
.\.venv\Scripts\python -m uvicorn src.main:app --reload
Notes Service with workspace/team multi-tenancy + RBAC while Auth Service already exists (JWT + bcrypt + Postgres via Supabase).

So the Notes service should:

• trust the Auth Service JWT
• extract user_id from token
• enforce workspace + role permissions
• allow team collaboration


1️⃣ High Level Architecture
Auth Service
 ├── login/register
 ├── JWT issue
 └── user identity

Notes Service
 ├── workspace management
 ├── team membership
 ├── notes CRUD
 └── RBAC permissions

Flow:

Client
  ↓
Auth Service (login)
  ↓
JWT
  ↓
Notes Service (Authorization header)
  ↓
Decode JWT → user_id
  ↓
Check workspace membership
  ↓
Allow CRUD
2️⃣ Database Schema Design

You need 4 tables.

users (managed by auth service)

workspaces
workspace_members
notes
workspaces
workspaces
---------
id (uuid)
name
owner_id (user_id)
created_at

Owner = Admin.

workspace_members
workspace_members
-----------------
id
workspace_id
user_id
role (admin | member)
joined_at

This controls RBAC.

notes
notes
------
id
workspace_id
created_by
title
content
is_private
created_at
updated_at

Important:

is_private = true

means only creator + admin can access.

3️⃣ Project Structure (Notes Service)
notes_service
src/
│
├ core/
│
├ domains/
│
│  ├ workspaces/
│  │   ├ models.py
│  │   ├ schemas.py
│  │   ├ repository.py
│  │   ├ service.py
│  │   ├ router.py
│  │   └ exceptions.py
│
│  ├ notes/
│  │   ├ models.py
│  │   ├ schemas.py
│  │   ├ repository.py
│  │   ├ service.py
│  │   ├ router.py
│  │   ├ permissions.py
│  │   └ events.py
│
│  └ membership/
│      ├ models.py
│      ├ repository.py
│      └ service.py

4️⃣ JWT Dependency (Auth Injection)

Notes service should verify JWT but not manage auth.

dependencies/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

SECRET_KEY = "same_secret_as_auth_service"

def get_current_user(token=Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

Now every request has:

current_user_id
5️⃣ SQLAlchemy Models
Workspace
class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID, primary_key=True)
    name = Column(String)
    owner_id = Column(UUID)
    created_at = Column(DateTime)
Workspace Members
class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(UUID, primary_key=True)
    workspace_id = Column(UUID, ForeignKey("workspaces.id"))
    user_id = Column(UUID)
    role = Column(String)
Notes
class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID, primary_key=True)
    workspace_id = Column(UUID)
    created_by = Column(UUID)

    title = Column(String)
    content = Column(Text)

    is_private = Column(Boolean, default=False)

    created_at = Column(DateTime)
    updated_at = Column(DateTime)
6️⃣ Permission Logic (Important)

Rules you defined:

Admin

✔ create notes
✔ update any note
✔ delete any note

Member

✔ create notes
✔ update/delete own note
❌ cannot update admin notes

permissions.py
def can_edit_note(user_id, note, role):

    if role == "admin":
        return True

    if note.created_by == user_id:
        return True

    return False
7️⃣ Create Workspace (One per user)

Route:

POST /workspace

Logic:

1 check if user already owns workspace
2 create workspace
3 add creator as admin member

Example:

@router.post("/workspace")
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):

    existing = db.query(Workspace).filter(
        Workspace.owner_id == user_id
    ).first()

    if existing:
        raise HTTPException(400, "Workspace already exists")

    workspace = Workspace(
        name=data.name,
        owner_id=user_id
    )

    db.add(workspace)
    db.commit()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role="admin"
    )

    db.add(member)
    db.commit()

    return workspace
8️⃣ Create Note

Route:

POST /workspace/{workspace_id}/notes

Logic:

1 verify membership
2 create note
@router.post("/{workspace_id}/notes")
def create_note(
    workspace_id: str,
    data: NoteCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(403)

    note = Note(
        workspace_id=workspace_id,
        created_by=user_id,
        title=data.title,
        content=data.content
    )

    db.add(note)
    db.commit()

    return note
9️⃣ Update Note
@router.put("/notes/{note_id}")
def update_note(
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):

    note = db.query(Note).filter(Note.id == note_id).first()

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == note.workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    if not can_edit_note(user_id, note, member.role):
        raise HTTPException(403)

    note.title = data.title
    note.content = data.content

    db.commit()

    return note
🔟 Delete Note

Same permission logic.

1️⃣1️⃣ Get Notes

Rules:

Admin:

see all workspace notes

Member:

see
- own notes
- public notes

Query:

if role == "admin":
    notes = db.query(Note).filter(
        Note.workspace_id == workspace_id
    ).all()

else:
    notes = db.query(Note).filter(
        Note.workspace_id == workspace_id,
        or_(
            Note.created_by == user_id,
            Note.is_private == False
        )
    ).all()
1️⃣2️⃣ API Endpoints
POST   /workspace
GET    /workspace/{id}

POST   /workspace/{id}/notes
GET    /workspace/{id}/notes
PUT    /notes/{note_id}
DELETE /notes/{note_id}

POST   /workspace/{id}/invite
1️⃣3️⃣ Production Improvements

Add:

1️⃣ Row Level Security (Supabase supports)
user can only see workspace where member
2️⃣ Indexing
workspace_id
created_by
3️⃣ Pagination
GET /notes?page=1&limit=20
4️⃣ Soft delete
deleted_at