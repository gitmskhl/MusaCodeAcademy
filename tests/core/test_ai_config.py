import os
import re

import pytest

from app.core.config import Settings, settings


@pytest.fixture
def config_data(monkeypatch):
    for key in os.environ:
        if re.fullmatch(r"AI_MODEL_[0-9]+", key.upper()) or key.upper() in {"AI_MODEL", "AI_MODELS"}:
            monkeypatch.delenv(key)
    return settings.model_dump(exclude={"ai_models", "ai_model"})


def test_numbered_models_are_sorted_deduplicated_and_overridden_by_environment(tmp_path, monkeypatch, config_data):
    env = tmp_path / ".env"
    env.write_text("AI_MODEL_10=vendor/ten\nAI_MODEL_2=vendor/old\nAI_MODEL_1=vendor/one\n"
                   "AI_MODEL_7=vendor/one\nAI_MODEL_3=\nAI_MODEL_wrong=ignored\nAI_MODEL=legacy\n")
    monkeypatch.setenv("AI_MODEL_2", "vendor/two")
    configured = Settings(_env_file=env, **config_data)
    assert configured.available_ai_models() == ["vendor/one", "vendor/two", "vendor/ten"]


def test_numbered_models_work_without_dotenv_and_legacy_model_is_a_fallback(monkeypatch, config_data):
    monkeypatch.setenv("AI_MODEL_8", "vendor/eight")
    assert Settings(_env_file=None, **config_data).available_ai_models() == ["vendor/eight"]
    monkeypatch.delenv("AI_MODEL_8")
    assert Settings(_env_file=None, ai_model="vendor/legacy", **config_data).available_ai_models() == ["vendor/legacy"]
    assert Settings(_env_file=None, ai_model=" ", **config_data).available_ai_models() == []
