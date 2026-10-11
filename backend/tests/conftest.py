from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app("sqlite:///" + (tmp_path / "test.db").as_posix())


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
