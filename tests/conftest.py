"""Pytest bootstrap: workspace-local imports and headless test environment.

The Agg backend and the offscreen Qt platform are configured here once so no
test module needs its own ``matplotlib.use`` / ``QT_QPA_PLATFORM`` line; this
runs before any test module is imported.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402  (must follow the Qt platform setup)

matplotlib.use("Agg")


# ── Guard-probe hygiene ─────────────────────────────────────────────────
#
# ``tests/test_guards.py`` plants ``_guard_probe_*.py`` files next to production
# code to prove each guard really detects violations, and removes them in a
# ``finally``. A hard-killed run (this platform can die inside pytest's atexit
# cleanup, printing ``PermissionError: pytest-current``) leaves the probe behind,
# and the *next* run's "guard reports zero hits" assertions then fail on that
# debris -- a confusing, order-dependent failure that looks like a real
# regression. Sweep once per session, before any test runs.

_GUARD_SCAN_ROOTS = (
    "application",
    "core",
    "data",
    "plugins",
    "scripts",
    "tests",
    "ui",
    "utils",
    "visualization",
)


@pytest.fixture(scope="session", autouse=True)
def _sweep_stale_guard_probes():
    """Delete guard probes left behind by a previously killed test run."""
    removed: list[Path] = []
    for root_name in _GUARD_SCAN_ROOTS:
        root = PROJECT_ROOT / root_name
        if not root.is_dir():
            continue
        for stale in root.rglob("_guard_probe_*.py"):
            try:
                stale.unlink(missing_ok=True)
                removed.append(stale)
            except OSError:
                # A locked file is not worth failing the session over; the guard
                # assertions will surface it if it actually matters.
                continue
    if removed:
        import warnings

        warnings.warn(
            f"Removed {len(removed)} stale guard probe file(s) from a previous run: "
            + ", ".join(sorted(p.name for p in removed)),
            stacklevel=1,
        )
    yield


# ── UI fixtures (composition root) ──────────────────────────────────────

@pytest.fixture(scope="session")
def qapp():
    """A single offscreen QApplication for the whole session."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def main_window(qapp):
    """The real main window, built through the composition root.

    Widget behaviour must be tested against the actual window instead of ad-hoc host
    objects that fake the mixin attributes.
    """
    from ui.factory import build_main_window

    window = build_main_window()
    try:
        yield window
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


# ── TerraLID metadata-profile fixtures ──────────────────────────────────
#
# The synthetic profile below is the shared fixture for the metadata-profile tests
# (layout / workbook generation / workbook IO). It is built by hand from ``spec.py``
# rather than by parsing ``reference/metadata`` so those tests stay independent of the
# markdown parser and of each other; the parser gets its own end-to-end assertions.


def build_synthetic_profile():
    """A minimal but representative synthetic registry (sites + analyses + B4/B6)."""
    from data.metadata_profile.spec import (
        Block,
        FieldSpec,
        Obligation,
        Occurrence,
        Profile,
        ProvidedBy,
        TableKey,
        TableSpec,
        ValueKind,
    )

    def _field(oid, key, **kwargs):
        return FieldSpec(
            oid=oid,
            key=key,
            label_en=kwargs.pop("label_en", key.replace("_", " ").title()),
            table=kwargs.pop("table"),
            obligation=kwargs.pop("obligation", Obligation.RECOMMENDED),
            occurrence=kwargs.pop("occurrence", Occurrence.ZERO_TO_ONE),
            provided_by=kwargs.pop("provided_by", (ProvidedBy.DATA_PROVIDER,)),
            definition=kwargs.pop("definition", f"definition of {oid}"),
            allowed=kwargs.pop("allowed", ""),
            example=kwargs.pop("example", ""),
            parent=kwargs.pop("parent", None),
            depth=kwargs.pop("depth", 0),
            block=kwargs.pop("block", None),
            block_owner=kwargs.pop("block_owner", None),
            value_kind=kwargs.pop("value_kind", ValueKind.FREE_TEXT),
            vocab_id=kwargs.pop("vocab_id", None),
            source_doc=kwargs.pop("source_doc", "docs/metadata_test.md"),
            source_line=kwargs.pop("source_line", 1),
            order=kwargs.pop("order", 0),
            label_zh=kwargs.pop("label_zh", ""),
        )

    site_own = (
        _field(
            "SI0",
            "terralid_site_id",
            table=TableKey.SITE,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            provided_by=(ProvidedBy.SYSTEM,),
            order=0,
            label_zh="遗址ID",
        ),
        _field(
            "SI1",
            "site_name",
            table=TableKey.SITE,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            order=1,
            label_zh="遗址名称",
        ),
        _field(
            "SI5",
            "site_geolocation",
            table=TableKey.SITE,
            order=2,
            label_zh="地理位置",
        ),
        _field(
            "SI5.1",
            "site_geolocation_point",
            table=TableKey.SITE,
            occurrence=Occurrence.ZERO_TO_N,
            parent="SI5",
            depth=1,
            order=3,
            label_zh="点位",
        ),
        _field(
            "SI5.1.1",
            "site_geolocation_point_longitude",
            table=TableKey.SITE,
            value_kind=ValueKind.DECIMAL,
            parent="SI5.1",
            depth=2,
            order=4,
            label_zh="经度",
        ),
        _field(
            "SI5.1.2",
            "site_geolocation_point_latitude",
            table=TableKey.SITE,
            value_kind=ValueKind.DECIMAL,
            parent="SI5.1",
            depth=2,
            order=5,
            label_zh="纬度",
        ),
    )
    site_table = TableSpec(
        key=TableKey.SITE,
        own_fields=site_own,
        inlined_blocks=(),
        fields=site_own,
    )

    # B6 lead-isotope ratio block. `Provided by` mirrors the real profile:
    # B6.1/B6.2 from the provider, B6.5 from both, B6.7 from the system only.
    lia_keys = [
        ("name", Obligation.MANDATORY, Occurrence.ONE, (ProvidedBy.DATA_PROVIDER,),
         ValueKind.RATIO_NAME, "lia_ratio_name"),
        ("value", Obligation.MANDATORY, Occurrence.ONE, (ProvidedBy.DATA_PROVIDER,),
         ValueKind.DECIMAL, None),
        ("uncertainty_type", Obligation.RECOMMENDED, Occurrence.ZERO_TO_ONE,
         (ProvidedBy.DATA_PROVIDER,), ValueKind.CONTROLLED_VOCAB,
         "lia_uncertainty_type"),
        ("uncertainty_sigma", Obligation.RECOMMENDED, Occurrence.ZERO_TO_ONE,
         (ProvidedBy.DATA_PROVIDER,), ValueKind.SIGMA, None),
        ("uncertainty_value_absolute", Obligation.RECOMMENDED,
         Occurrence.ZERO_TO_ONE,
         (ProvidedBy.DATA_PROVIDER, ProvidedBy.SYSTEM), ValueKind.DECIMAL, None),
        ("uncertainty_value_relative", Obligation.RECOMMENDED,
         Occurrence.ZERO_TO_ONE, (ProvidedBy.DATA_PROVIDER,), ValueKind.DECIMAL,
         None),
        ("source", Obligation.MANDATORY, Occurrence.ONE, (ProvidedBy.SYSTEM,),
         ValueKind.RATIO_SOURCE, "lia_ratio_source"),
    ]
    lia_block = tuple(
        _field(
            f"B6.{index}",
            f"lia_ratio_{name}",
            table=TableKey.ANALYSIS,
            obligation=obligation,
            occurrence=occurrence,
            provided_by=providers,
            value_kind=kind,
            vocab_id=vocab,
            order=index,
            block=Block.LIA_RATIO,
            block_owner="A14",
            label_zh=f"比值字段{index}",
        )
        for index, (name, obligation, occurrence, providers, kind, vocab) in enumerate(
            lia_keys, start=1
        )
    )

    chem_block = (
        _field(
            "B4.1",
            "chemistry_method",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            value_kind=ValueKind.CONTROLLED_VOCAB,
            vocab_id="chemistry_method",
            order=0,
            block=Block.CHEMISTRY,
            block_owner="A7",
            label_zh="分析方法",
        ),
        _field(
            "B4.3",
            "chemistry_value",
            table=TableKey.ANALYSIS,
            occurrence=Occurrence.ONE_TO_N,
            value_kind=ValueKind.DECIMAL,
            order=1,
            block=Block.CHEMISTRY,
            block_owner="A7",
            label_zh="值",
        ),
    )

    analysis_own = (
        _field(
            "A0",
            "terralid_analysis_id",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            provided_by=(ProvidedBy.SYSTEM,),
            order=0,
            label_zh="分析ID",
        ),
        _field(
            "A1",
            "analysis_lab_id",
            table=TableKey.ANALYSIS,
            order=1,
            label_zh="实验室编号",
        ),
        _field(
            "A2",
            "analysis_lia_type",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            value_kind=ValueKind.CONTROLLED_VOCAB,
            vocab_id="analysis_type",
            order=2,
            label_zh="分析类型",
        ),
        _field(
            "A7",
            "analysis_lia_pb_concentration",
            table=TableKey.ANALYSIS,
            order=3,
            label_zh="Pb浓度",
        ),
        _field(
            "A12",
            "analysis_lia_date",
            table=TableKey.ANALYSIS,
            value_kind=ValueKind.DATE,
            order=4,
            label_zh="分析日期",
        ),
        _field(
            "A14",
            "analysis_lia_ratio",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE_TO_N,
            provided_by=(ProvidedBy.DATA_PROVIDER, ProvidedBy.SYSTEM),
            order=5,
            label_zh="铅同位素比值",
        ),
        _field(
            "A15.2",
            "analysis_lia_age_model_Tmod",
            table=TableKey.ANALYSIS,
            provided_by=(ProvidedBy.SYSTEM,),
            value_kind=ValueKind.DECIMAL,
            parent="A15",
            depth=1,
            order=6,
            label_zh="模式年龄",
        ),
    )
    analysis_fields = (
        analysis_own[0],
        analysis_own[1],
        analysis_own[2],
        analysis_own[3],
        *chem_block,
        analysis_own[4],
        analysis_own[5],
        *lia_block,
        analysis_own[6],
    )
    analysis_table = TableSpec(
        key=TableKey.ANALYSIS,
        own_fields=analysis_own,
        inlined_blocks=(Block.CHEMISTRY, Block.LIA_RATIO),
        fields=analysis_fields,
    )

    return Profile(
        version="0.3.4-test",
        tables=(site_table, analysis_table),
        blocks={Block.LIA_RATIO: lia_block, Block.CHEMISTRY: chem_block},
    )


@pytest.fixture(scope="session")
def synthetic_profile():
    """The shared synthetic TerraLID registry."""
    return build_synthetic_profile()


@pytest.fixture(scope="session")
def synthetic_layout(synthetic_profile):
    """The workbook layout built from ``synthetic_profile``."""
    from data.metadata_profile.layout import build_layout

    return build_layout(synthetic_profile)
