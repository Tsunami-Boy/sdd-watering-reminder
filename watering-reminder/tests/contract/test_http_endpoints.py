import pytest
from fastapi.testclient import TestClient

from tests.fakes import FakeRepository
from waterbot.app import create_app

SECRET = "path-secret"
TOKEN = "header-token"


class FakeRuntime:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.started = self.stopped = False
        self.fail = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def process_update(self, data: dict) -> None:
        if self.fail:
            raise RuntimeError("boom")
        self.updates.append(data)


@pytest.fixture
def parts():
    return FakeRepository(), FakeRuntime()


@pytest.fixture
def client(parts):
    repo, runtime = parts
    with TestClient(create_app(SECRET, TOKEN, repo, runtime)) as c:
        yield c


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200 and response.json() == {"status": "healthy"}
    assert client.head("/healthz").status_code == 200


def test_healthz_degraded_when_database_is_down(client, parts):
    parts[0].healthy = False
    assert client.get("/healthz").status_code == 503
    assert client.get("/healthz").json() == {"status": "degraded"}
    assert client.head("/healthz").status_code == 503


def test_webhook_wrong_path_secret_is_404(client, parts):
    r = client.post(
        "/webhook/wrong", json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": TOKEN}
    )
    assert r.status_code == 404 and parts[1].updates == []


def test_webhook_wrong_header_token_is_403(client, parts):
    assert client.post(f"/webhook/{SECRET}", json={"update_id": 1}).status_code == 403
    r = client.post(
        f"/webhook/{SECRET}",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "x"},
    )
    assert r.status_code == 403 and parts[1].updates == []


def test_webhook_accepts_valid_requests(client, parts):
    r = client.post(
        f"/webhook/{SECRET}",
        json={"update_id": 5},
        headers={"X-Telegram-Bot-Api-Secret-Token": TOKEN},
    )
    assert r.status_code == 200 and parts[1].updates == [{"update_id": 5}]


def test_webhook_answers_200_even_if_handling_fails(client, parts):
    parts[1].fail = True
    r = client.post(
        f"/webhook/{SECRET}",
        json={"update_id": 5},
        headers={"X-Telegram-Bot-Api-Secret-Token": TOKEN},
    )
    assert r.status_code == 200


def test_lifespan_starts_and_stops_the_runtime(parts):
    repo, runtime = parts
    with TestClient(create_app(SECRET, TOKEN, repo, runtime)):
        assert runtime.started and not runtime.stopped
    assert runtime.stopped
