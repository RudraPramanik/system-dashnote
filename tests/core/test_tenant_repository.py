from core.database.mixins import WorkspaceTenantMixin
from core.database.repository import TenantRepository
from core.database.utils import tenant_filter
from core.database.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class DummyModel(Base, WorkspaceTenantMixin):
    __tablename__ = "dummy_tenant_model"

    id: Mapped[int] = mapped_column(primary_key=True)


def test_tenant_repository_holds_workspace_id() -> None:
    class DummySession:
        pass

    session = DummySession()
    repo = TenantRepository(session=session, workspace_id=42)

    assert repo.session is session
    assert repo.workspace_id == 42


def test_tenant_filter_uses_workspace_id_column() -> None:
    expr = tenant_filter(DummyModel, 99)

    # SQLAlchemy binary expression; left/right should reflect the workspace filter
    assert str(expr.left).endswith(".workspace_id")
    assert expr.right.value == 99

