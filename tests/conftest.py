import pytest

from filinglens.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None, sec_user_agent="FilingLens tests test@example.org", raw_dir=tmp_path
    )
