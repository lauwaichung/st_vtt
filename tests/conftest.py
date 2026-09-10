from pathlib import Path

import pytest

from st_vtt.config import Config, UserConfig
from st_vtt.content import load_content

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pack():
    return load_content(ROOT / "content" / "example")


@pytest.fixture
def config(tmp_path):
    return Config(
        content_pack=str(ROOT / "content" / "example"),
        database=str(tmp_path / "test.db"),
        secret="test-secret",
        static_dir=str(tmp_path / "nostatic"),
        users=[
            UserConfig(name="Gm", role="gm"),
            UserConfig(name="Alice", role="player"),
            UserConfig(name="Bob", role="player", password="pw"),
        ],
        base_dir=ROOT,
    )
