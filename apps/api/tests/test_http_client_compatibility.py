import warnings

from app.main import app
from tests.http_client import TestClient


def test_shared_http_client_emits_no_starlette_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert not any("StarletteDeprecationWarning" in str(item.message) for item in recorded)
