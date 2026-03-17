from pydantic import BaseModel


class MemberInvite(BaseModel):
    email: str
    role: str = "member"  # member | admin


class MemberRoleUpdate(BaseModel):
    role: str


class MemberRead(BaseModel):
    user_id: int
    email: str
    role: str

    class Config:
        from_attributes = True

