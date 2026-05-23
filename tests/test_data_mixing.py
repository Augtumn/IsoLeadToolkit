"""Tests for data.mixing helper functions."""

from __future__ import annotations

import pandas as pd
import pytest

from plugins.builtins.mixing_plugin import MixingModelPlugin

calculate_mixing = MixingModelPlugin().calculate


def test_calculate_mixing_recovers_simple_two_endmember_weights() -> None:
    df = pd.DataFrame(
        {
            "Pb206_204": [0.0, 10.0, 2.0],
            "Pb207_204": [0.0, 10.0, 2.0],
        }
    )
    endmember_groups = {"EM_A": [0], "EM_B": [1]}
    mixture_groups = {"MX": [2]}

    results = calculate_mixing(
        df=df,
        endmember_groups=endmember_groups,
        mixture_groups=mixture_groups,
        columns=["Pb206_204", "Pb207_204"],
    )

    assert len(results) == 2
    weights = {item["endmember"]: item["weight"] for item in results}
    assert weights["EM_A"] == pytest.approx(0.8, rel=0.0, abs=1e-6)
    assert weights["EM_B"] == pytest.approx(0.2, rel=0.0, abs=1e-6)
    assert sum(weights.values()) == pytest.approx(1.0, rel=0.0, abs=1e-6)
    assert all(item["rmse"] == pytest.approx(0.0, rel=0.0, abs=1e-6) for item in results)


def test_calculate_mixing_raises_for_empty_endmember_group() -> None:
    df = pd.DataFrame({"x": [1.0], "y": [2.0]})

    with pytest.raises(ValueError, match="Endmember group 'EM_A' is empty"):
        calculate_mixing(
            df=df,
            endmember_groups={"EM_A": []},
            mixture_groups={"MX": [0]},
            columns=["x", "y"],
        )
