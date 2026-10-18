"""An export profile is the callers own copy of a journal preset.

Reported by review: build_image_export_profile copied the preset dict but not its lists, so a caller that edited
the returned profile rewrote the module-level preset for the rest of the run.
"""
from __future__ import annotations

import pytest

from application.use_cases.export_image import _IMAGE_EXPORT_PROFILES, build_image_export_profile


@pytest.mark.parametrize("key", ["science_single", "nature_single"])
def test_editing_a_profile_does_not_change_the_preset(qapp, key: str) -> None:
    if key not in _IMAGE_EXPORT_PROFILES:  # a preset may be renamed; the test follows the table
        pytest.skip("preset not defined: " + key)
    preset = _IMAGE_EXPORT_PROFILES[key]
    before_styles = list(preset.get("styles", []) or [])
    before_legend = dict(preset.get("legend", {}) or {})

    profile = build_image_export_profile(key)
    profile["styles"].append("SHOULD-NOT-LEAK")
    profile["legend"]["SHOULD-NOT-LEAK"] = True

    assert list(preset.get("styles", []) or []) == before_styles, "the preset keeps its own list"
    assert dict(preset.get("legend", {}) or {}) == before_legend, "and its own legend settings"
