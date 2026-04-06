"""Tests for geochemistry package helper functions."""

from __future__ import annotations

from data import geochemistry


def test_resolve_age_model_prefers_explicit_flag() -> None:
    params = {"age_model": "2-stage"}

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "two_stage"


def test_resolve_age_model_uses_param_delta_floor_for_single_stage() -> None:
    params = {
        "Tsec": 100.0,
        "a0": 9.307,
        "b0": 10.294,
        "c0": 29.476,
        "a1": 9.307 + 5e-7,
        "b1": 10.294 - 5e-7,
        "c1": 29.476 + 5e-7,
    }

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "single_stage"


def test_resolve_age_model_returns_two_stage_when_delta_exceeds_floor() -> None:
    params = {
        "Tsec": 100.0,
        "a0": 9.307,
        "b0": 10.294,
        "c0": 29.476,
        "a1": 9.307 + 2e-6,
        "b1": 10.294,
        "c1": 29.476,
    }

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "two_stage"
