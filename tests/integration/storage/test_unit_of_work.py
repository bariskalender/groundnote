from __future__ import annotations

import pytest

from groundnote.storage import (
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteUnitOfWorkFactory,
)

from .conftest import make_chunk, make_document


def test_unit_of_work_commit_persists(initialized_database) -> None:  # type: ignore[no-untyped-def]
    factory = SQLiteUnitOfWorkFactory(initialized_database)

    with factory() as uow:
        assert uow.documents is not None
        uow.documents.add(make_document())
        uow.commit()

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert SQLiteDocumentRepository(connection).count() == 1


def test_unit_of_work_rolls_back_without_commit(initialized_database) -> None:  # type: ignore[no-untyped-def]
    factory = SQLiteUnitOfWorkFactory(initialized_database)

    with factory() as uow:
        assert uow.documents is not None
        uow.documents.add(make_document())

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert SQLiteDocumentRepository(connection).count() == 0


def test_unit_of_work_rolls_back_on_exception(initialized_database) -> None:  # type: ignore[no-untyped-def]
    factory = SQLiteUnitOfWorkFactory(initialized_database)

    with pytest.raises(RuntimeError), factory() as uow:
        assert uow.documents is not None
        uow.documents.add(make_document())
        raise RuntimeError("boom")

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert SQLiteDocumentRepository(connection).count() == 0


def test_unit_of_work_groups_document_and_chunk(initialized_database) -> None:  # type: ignore[no-untyped-def]
    factory = SQLiteUnitOfWorkFactory(initialized_database)

    with factory() as uow:
        assert uow.documents is not None
        assert uow.vectors is not None
        uow.documents.add(make_document())
        uow.vectors.add_chunk(make_chunk())
        uow.commit()

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 1


def test_unit_of_work_cannot_commit_after_close(initialized_database) -> None:  # type: ignore[no-untyped-def]
    factory = SQLiteUnitOfWorkFactory(initialized_database)
    uow = factory()
    with uow:
        pass

    with pytest.raises(RuntimeError):
        uow.commit()
