from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from pages.models import PageVersion


async def create_page_version(
    session: AsyncSession,
    page_id: int,
    content: str,
) -> PageVersion:
    """
    Append an immutable version for the given page.

    - Versions are 1-based and monotonically increasing per page.
    - The Page itself remains a pointer to "current" via application logic.
    """
    last_version = await session.scalar(
        select(func.max(PageVersion.version)).where(PageVersion.page_id == page_id)
    )

    version_number = (last_version or 0) + 1

    version = PageVersion(
        page_id=page_id,
        content=content,
        version=version_number,
    )

    session.add(version)
    await session.commit()
    await session.refresh(version)

    return version

