import os
import tempfile

import pytest

# Las pruebas usan una base SQLite temporal, salvo que se indique TEST_DATABASE_URL
# (por ejemplo, una base PostgreSQL de pruebas en el pipeline de CI).
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def u(client):
    return {x["simbolo"]: x["id"] for x in client.get("/api/unidades").json()}
