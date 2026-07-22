from __future__ import annotations

import re
from importlib import metadata

import groundnote


def test_groundnote_imports() -> None:
    assert groundnote.__version__ == metadata.version("groundnote")
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z0-9.+-]+)?", groundnote.__version__)
