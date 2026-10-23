import pytest
import requests

from looplens import model


class FakeResp:
    def __init__(self, code, headers=None):
        self.status_code, self.headers = code, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_retries_then_succeeds(monkeypatch):
    codes = iter([429, 503, 200])
    monkeypatch.setattr(model.requests, "post", lambda *a, **k: FakeResp(next(codes)))
    waits = []
    r = model._post_with_retry("u", {}, {}, sleep=waits.append)
    assert r.status_code == 200 and waits == [5, 10]


def test_uses_retry_after_and_gives_up(monkeypatch):
    monkeypatch.setattr(model.requests, "post", lambda *a, **k: FakeResp(429, {"Retry-After": "7"}))
    waits = []
    with pytest.raises(requests.HTTPError):
        model._post_with_retry("u", {}, {}, tries=3, sleep=waits.append)
    assert waits == [7, 7]


def test_client_error_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(model.requests, "post", lambda *a, **k: calls.append(1) or FakeResp(400))
    with pytest.raises(requests.HTTPError):
        model._post_with_retry("u", {}, {}, sleep=lambda s: None)
    assert len(calls) == 1
