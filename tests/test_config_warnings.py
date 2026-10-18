"""An entry the configuration file gets wrong is reported, not silently replaced.

Reported by review: a value that failed validation was replaced with the built-in default at debug level, so a user
with a typo in the file saw the same thing as a user whose setting was applied. These run once, at startup.
"""
from __future__ import annotations

import copy
import logging

import pytest

from core import config


@pytest.fixture()
def guarded_config():
    """merge_config writes the global CONFIG, so every test puts it back."""
    original = copy.deepcopy(config.CONFIG)
    yield
    config.CONFIG.clear()
    config.CONFIG.update(original)


def _warnings(caplog):
    return [record.getMessage() for record in caplog.records if record.levelno >= logging.WARNING]


def test_an_unknown_key_is_reported(guarded_config, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger=config.__name__):
        config.merge_config({"unknown_key": 1})
    assert any("unknown_key" in message for message in _warnings(caplog))


def test_an_unsupported_language_is_reported(guarded_config, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger=config.__name__):
        config.merge_config({"default_language": "klingon"})
    assert any("default_language" in message for message in _warnings(caplog))


def test_a_wrong_figure_size_is_reported(guarded_config, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger=config.__name__):
        config.merge_config({"figure_size": (1, 2, 3)})
    assert any("figure_size" in message for message in _warnings(caplog))


def test_a_valid_value_is_not_reported_as_a_problem(guarded_config, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger=config.__name__):
        config.merge_config({"default_language": "en"})
    assert not [message for message in _warnings(caplog) if "using default" in message]
