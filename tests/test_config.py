import pytest
from pydantic import ValidationError

from filinglens.config import Settings


def test_config_does_not_require_llm_keys(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "FilingLens Contact contact@example.org")
    assert Settings(_env_file=None).snapshot_id == "2026-10-19-v1"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sec_user_agent": "bad"},
        {"snapshot_id": "../unsafe"},
        {"sec_requests_per_second": 9},
    ],
)
def test_invalid_config(kwargs):
    values = {"sec_user_agent": "FilingLens test test@example.org"} | kwargs
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
