"""Image-export quality tests: journal presets, font embedding and format options."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from application.use_cases.export_image import (  # noqa: E402
    IMAGE_PRESET_ORDER,
    available_image_presets,
    build_image_export_profile,
    mm_to_inch,
    resolve_image_save_kwargs,
    save_export_figure,
)
from core import app_state  # noqa: E402
from ui.panels.export.common import ExportPanelCommonMixin  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


class _StubExportPanel(ExportPanelCommonMixin):
    """The option helpers only need state access, not Qt widgets."""


# ── presets ───────────────────────────────────────────────────────────────

def test_available_presets_match_the_profile_table() -> None:
    presets = available_image_presets()
    assert [key for key, _ in presets] == list(IMAGE_PRESET_ORDER)
    assert len(presets) == 8
    labels = [label for _, label in presets]
    assert len(set(labels)) == len(labels), "preset labels must be unique"

    for key, label in presets:
        profile = build_image_export_profile(key)
        assert profile["label"] == label
        assert profile["figsize"][0] == pytest.approx(mm_to_inch(profile["width_mm"]))


def test_journal_presets_use_published_column_widths() -> None:
    expectations = {
        "science_single": 85.0,
        "science_double": 183.0,
        "nature_single": 89.0,
        "nature_double": 180.0,
        "ieee_single": 88.0,
        "elsevier_double": 190.0,
        "gsa_double": 190.0,
        "presentation": 240.0,
    }
    for key, width_mm in expectations.items():
        profile = build_image_export_profile(key)
        assert profile["width_mm"] == pytest.approx(width_mm), key
        assert profile["figsize"][0] == pytest.approx(mm_to_inch(width_mm))
        assert profile["figsize"][1] >= 2.0

    unknown = build_image_export_profile("does_not_exist")
    assert unknown["label"] == "Science Single Column"


def test_preset_labels_are_registered_in_both_locales() -> None:
    """Labels are passed to translate() as variables, so the locale checker is blind."""
    en = json.loads((REPO_ROOT / "locales/en.json").read_text(encoding="utf-8"))
    zh = json.loads((REPO_ROOT / "locales/zh.json").read_text(encoding="utf-8"))
    for _, label in available_image_presets():
        assert label in en, label
        assert label in zh, label
    for key in ("Output Quality", "Embed Fonts", "White Background"):
        assert key in en and key in zh, key


# ── format-aware save options ─────────────────────────────────────────────

def _kwargs(ext: str, **overrides):
    base = dict(export_dpi=300, bbox_tight=True, pad_inches=0.02, transparent=False)
    base.update(overrides)
    return resolve_image_save_kwargs(ext, **base)


def test_vector_formats_embed_truetype_fonts() -> None:
    for ext in ("pdf", "svg", "eps"):
        kwargs, rc = _kwargs(ext)
        assert rc["pdf.fonttype"] == 42, ext
        assert rc["ps.fonttype"] == 42, ext
        assert rc["svg.fonttype"] == "none", ext
        assert kwargs["format"] == ext


def test_font_embedding_can_be_turned_off() -> None:
    _, rc = _kwargs("svg", embed_fonts=False)
    assert rc == {"svg.fonttype": "path"}
    _, rc = _kwargs("png", embed_fonts=False)
    assert rc == {}


def test_non_transparent_exports_use_a_white_background() -> None:
    kwargs, _ = _kwargs("png")
    assert kwargs["facecolor"] == "white"
    assert kwargs["edgecolor"] == "none"

    kwargs, _ = _kwargs("svg", transparent=True)
    assert kwargs["transparent"] is True
    assert "facecolor" not in kwargs

    kwargs, _ = _kwargs("png", white_background=False)
    assert "facecolor" not in kwargs


def test_eps_drops_transparency_and_therefore_gets_the_white_background() -> None:
    kwargs, _ = _kwargs("eps", transparent=True)
    assert kwargs["transparent"] is False
    assert kwargs["facecolor"] == "white"


def test_raster_formats_carry_quality_kwargs() -> None:
    kwargs, _ = _kwargs("png", export_dpi=600)
    assert kwargs["pil_kwargs"] == {"optimize": True}
    assert kwargs["dpi"] == 600

    kwargs, _ = _kwargs("tiff")
    assert kwargs["pil_kwargs"] == {"compression": "tiff_lzw"}

    kwargs, _ = _kwargs("pdf")
    assert "pil_kwargs" not in kwargs


def test_pdf_metadata_is_forwarded_for_pdf_only() -> None:
    metadata = {"Title": "Pb isotopes", "Creator": "IsotopesAnalyse", "Subject": ""}
    kwargs, _ = _kwargs("pdf", metadata=metadata)
    assert kwargs["metadata"] == {"Title": "Pb isotopes", "Creator": "IsotopesAnalyse"}

    kwargs, _ = _kwargs("svg", metadata=metadata)
    assert "metadata" not in kwargs


def test_padding_is_only_passed_for_tight_bounding_boxes() -> None:
    kwargs, _ = _kwargs("png")
    assert kwargs["bbox_inches"] == "tight" and kwargs["pad_inches"] == 0.02

    kwargs, _ = _kwargs("png", bbox_tight=False)
    assert kwargs["bbox_inches"] is None and "pad_inches" not in kwargs


def test_dpi_is_clamped_to_the_supported_minimum() -> None:
    kwargs, _ = _kwargs("png", export_dpi=10)
    assert kwargs["dpi"] == 72


def test_real_pdf_save_embeds_truetype_and_writes_the_file(tmp_path: Path) -> None:
    figure = Figure(figsize=(2.0, 1.5))
    axis = figure.add_subplot(111)
    axis.plot([0.0, 1.0], [0.0, 1.0], label="sample")
    axis.set_xlabel("Pb206/Pb204")
    axis.legend()

    target = tmp_path / "figure.pdf"
    save_export_figure(
        figure, str(target), "pdf", export_dpi=300, bbox_tight=True,
        pad_inches=0.02, transparent=False, metadata={"Title": "Round trip"},
        embed_fonts=True,
    )

    blob = target.read_bytes()
    assert blob.startswith(b"%PDF")
    assert b"FontFile2" in blob, "PDF must embed TrueType (Type 42) fonts"
    assert b"/Type3" not in blob, "Type 3 fonts are rejected by most journals"


def test_real_png_save_writes_a_file(tmp_path: Path) -> None:
    figure = Figure(figsize=(2.0, 1.5))
    figure.add_subplot(111).plot([0.0, 1.0], [0.0, 1.0])
    target = tmp_path / "figure.png"
    save_export_figure(
        figure, str(target), "png", export_dpi=200, bbox_tight=True,
        pad_inches=0.0, transparent=False,
    )
    blob = target.read_bytes()
    assert blob[:8] == b"\x89PNG\r\n\x1a\n"


# ── the switches are ordinary export options ─────────────────────────────

def test_export_switches_have_journal_safe_defaults() -> None:
    options = app_state.export_image_options
    assert options["embed_fonts"] is True
    assert options["white_background"] is True


def test_panel_default_params_and_save_options_carry_the_switches() -> None:
    panel = _StubExportPanel()
    profile = build_image_export_profile("nature_single")
    defaults = panel._profile_default_params(profile)
    assert defaults["embed_fonts"] is True
    assert defaults["white_background"] is True

    options = panel._resolve_export_save_options(
        profile, overrides={"embed_fonts": False, "white_background": False}
    )
    assert options["embed_fonts"] is False
    assert options["white_background"] is False
    assert app_state.export_image_options["embed_fonts"] is False

    # restore the defaults for the remaining tests
    options = panel._resolve_export_save_options(profile, overrides={})
    assert options["embed_fonts"] is True
    assert options["white_background"] is True
