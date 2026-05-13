from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.sql.dml import Insert

from core.database.associations import note_attachments
from files import repository as files_repo


@pytest.mark.asyncio
async def test_link_success():
    workspace_id = 1
    note_id = 7
    file_id = uuid4()

    file_row = MagicMock()
    file_row.workspace_id = workspace_id
    note_row = MagicMock()
    note_row.workspace_id = workspace_id

    res_file = MagicMock()
    res_file.scalar_one_or_none.return_value = file_row
    res_note = MagicMock()
    res_note.scalar_one_or_none.return_value = note_row
    res_insert = MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[res_file, res_note, res_insert])
    session.commit = AsyncMock()

    await files_repo.link_to_note(session, workspace_id, note_id, file_id)

    assert session.execute.await_count == 3
    session.commit.assert_awaited_once()

    insert_stmt = session.execute.call_args_list[2][0][0]
    assert isinstance(insert_stmt, Insert)
    assert insert_stmt.table.name == note_attachments.name


@pytest.mark.asyncio
async def test_link_rejects_cross_workspace_file():
    workspace_id = 1
    file_row = MagicMock()
    file_row.workspace_id = 99

    res_file = MagicMock()
    res_file.scalar_one_or_none.return_value = file_row

    session = AsyncMock()
    session.execute = AsyncMock(return_value=res_file)

    with pytest.raises(HTTPException) as exc_info:
        await files_repo.link_to_note(session, workspace_id, 1, uuid4())

    assert exc_info.value.status_code == 403
    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_rejects_cross_workspace_note():
    workspace_id = 1
    file_row = MagicMock()
    file_row.workspace_id = workspace_id
    note_row = MagicMock()
    note_row.workspace_id = 55

    res_file = MagicMock()
    res_file.scalar_one_or_none.return_value = file_row
    res_note = MagicMock()
    res_note.scalar_one_or_none.return_value = note_row

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[res_file, res_note])

    with pytest.raises(HTTPException) as exc_info:
        await files_repo.link_to_note(session, workspace_id, 3, uuid4())

    assert exc_info.value.status_code == 403
    assert session.execute.await_count == 2
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_is_idempotent():
    workspace_id = 2
    note_id = 10
    file_id = uuid4()

    file_row = MagicMock()
    file_row.workspace_id = workspace_id
    note_row = MagicMock()
    note_row.workspace_id = workspace_id

    res_file = MagicMock()
    res_file.scalar_one_or_none.return_value = file_row
    res_note = MagicMock()
    res_note.scalar_one_or_none.return_value = note_row
    res_insert = MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            res_file,
            res_note,
            res_insert,
            res_file,
            res_note,
            res_insert,
        ]
    )
    session.commit = AsyncMock()

    await files_repo.link_to_note(session, workspace_id, note_id, file_id)
    await files_repo.link_to_note(session, workspace_id, note_id, file_id)

    assert session.execute.await_count == 6
    assert session.commit.await_count == 2
