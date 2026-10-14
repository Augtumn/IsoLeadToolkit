"""Plugin-contract and integration tests for the SilverQuest analysis plugin.

Two things are pinned down here:

1. the plugin is *reachable* through the project's real extension point, not
   merely importable — the file stem is discovered by :class:`PluginManager`,
   loads through the same dynamic-import path as every other builtin, exposes
   the ``BasePlugin`` surface, appears in ``plugin_manager.plugins`` (which is
   what ``ui/panels/analysis/build.py`` iterates to build panel sections), and is
   wired to an analysis-panel callback;
2. the search takes **both** of its sides from the loaded data, selected by a
   grouping column (``run_silverquest_on_groups``), and still accepts the R
   package's galena workbook as an optional extra reference set.

The synthetic dataset below is built so the expected numbers are hand-derivable
from the R transcription (see :mod:`adapters.silverquest`): the 204Pb normalisation
has ``smatrix = diag(f * (2*18.7, 3*15.65, 4*39.0))`` with ``f = 0.001``, so a
common-mode offset of ``d`` on all three ratios costs
``d**2 / (2*(2*0.0187)**2) + d**2 / (2*(3*0.01565)**2) + d**2 / (2*(4*0.039)**2)``
plus the small correlation cross-terms (r = 0.96 / 0.94 / 0.96).

The R reference for the algorithm itself is ``SilverQuest_R_v1.R`` and is
documented in :mod:`adapters.silverquest`; the numeric expectations live in
``tests/test_silverquest.py``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from plugins.api import BasePlugin, PluginMeta
from plugins.builtins.silverquest_plugin import (
    ROLE_OTHER,
    ROLE_REFERENCE_MATCHED_PREFIX,
    ROLE_REFERENCE_UNMATCHED_PREFIX,
    ROLE_SAMPLE_MATCHED_PREFIX,
    ROLE_SAMPLE_UNMATCHED_PREFIX,
    SilverQuestPlugin,
    resolve_references,
    run_silverquest_on_groups,
    run_silverquest_search,
)
from plugins.manager import PluginManager

_PLUGIN_STEM = "silverquest_plugin"
_META_NAME = "silverquest"

#: R ratios as a raw dict, before any reinterpretation of ``dmax``.
ORE_EXACT = (18.5764, 15.6597, 38.589)
ORE_OTHER = (18.9000, 15.7000, 39.0000)


def _synthetic_grouped_frame() -> pd.DataFrame:
    """Six rows in three groups: two artefacts and one reference ore.

    ``SiteA`` carries one exact match of ``OreX`` (distance 0) and one row a
    little off it; ``SiteB`` carries one row further off ``OreX`` and further
    still from ``OreY``.  ``Latitude``/``Longitude`` are present so the hit table
    has real coordinates.

    The squared weighted distances to ``OreX`` are 0.0 / 0.3834233738598962 /
    1.5336934954387278 (see the module docstring); to ``OreY`` they are all in
    the thousands, so ``dmax`` alone decides which artefacts report hits.
    """
    return pd.DataFrame(
        {
            "Sample": ["A1", "A2", "B1", "X1", "X2", "Y1"],
            "Group": ["SiteA", "SiteA", "SiteB", "OreX", "OreX", "OreY"],
            "Pb206_204": [18.5764, 18.5864, 18.5964, 18.5764, 19.0000, 17.5000],
            "Pb207_204": [15.6597, 15.6697, 15.6797, 15.6597, 15.8000, 15.5000],
            "Pb208_204": [38.5890, 38.5990, 38.6090, 38.5890, 39.5000, 37.5000],
            "Latitude": [35.0, 35.1, 36.0, 40.0, 41.0, 38.0],
            "Longitude": [24.0, 24.1, 25.0, 12.0, 13.0, 14.0],
        }
    )


# ── plugin contract ──────────────────────────────────────────────────────


def test_plugin_file_stem_is_discovered_as_a_builtin() -> None:
    """Discovery scans ``plugins/builtins/`` by file stem (docs/plugins.md)."""
    names = PluginManager().discover()
    assert _PLUGIN_STEM in names


def test_plugin_loads_through_the_manager_and_is_a_base_plugin() -> None:
    """The manager loads by file stem and the result satisfies the host contract.

    Note: ``PluginManager.load_plugin`` executes the file under the namespace
    ``plugins._loaded.<stem>`` (docs/plugins.md), so the loaded class is a
    *distinct* class object from ``plugins.builtins.silverquest_plugin``.  The
    contract is therefore checked behaviourally rather than with ``isinstance``
    against the imported class.
    """
    manager = PluginManager()
    plugin = manager.load_plugin(_PLUGIN_STEM)

    assert type(plugin).__name__ == "SilverQuestPlugin"
    assert isinstance(plugin, BasePlugin)  # runtime_checkable Protocol
    assert manager.is_loaded(_PLUGIN_STEM) is True
    # The manager keys by file stem and also resolves meta.name.
    assert manager.get(_PLUGIN_STEM) is plugin
    assert manager.get(_META_NAME) is plugin
    assert manager.get_meta(_PLUGIN_STEM) is plugin.meta
    assert plugin.meta.plugin_type == "analysis"
    assert plugin.meta.api_version == "1.0"  # host API version gate
    # The loaded instance really is the ported algorithm, not a stub.
    assert "silverquest" in plugin.meta.description.lower()
    assert plugin.get_default_params()["dmax"] == 3.0
    assert plugin.validate_environment() == (True, "ok")


def test_plugin_meta_is_a_well_formed_descriptor() -> None:
    plugin = SilverQuestPlugin()
    assert isinstance(plugin.meta, PluginMeta)
    assert plugin.meta.name == _META_NAME
    assert plugin.meta.version
    assert plugin.meta.author


def test_plugin_passes_environment_validation() -> None:
    ok, message = SilverQuestPlugin().validate_environment()
    assert ok is True
    assert message == "ok"


def test_plugin_is_reported_loaded_in_manager_status() -> None:
    manager = PluginManager()
    manager.load_all()
    status = manager.get_status()
    assert _PLUGIN_STEM in status["loaded"]
    assert status["loaded"][_PLUGIN_STEM]["source"] == "builtin"
    assert status["loaded"][_PLUGIN_STEM]["type"] == "analysis"
    assert _PLUGIN_STEM not in status["failed"]


def test_plugin_appears_in_the_collection_the_analysis_panel_iterates() -> None:
    """``ui/panels/analysis/build.py::_build_plugin_sections`` walks this dict."""
    manager = PluginManager()
    manager.load_all()
    assert _PLUGIN_STEM in manager.plugins
    plugin = manager.plugins[_PLUGIN_STEM]
    assert hasattr(plugin, "build_ui") and callable(plugin.build_ui)


def test_panel_callback_map_wires_the_plugin_to_its_handler() -> None:
    """The panel's ``callback_map`` must know this plugin's registry key.

    Without the entry ``_build_plugin_sections`` still builds the group, but the
    button's click signal stays unconnected — a silent dead control.
    """
    import inspect

    from ui.panels.analysis import build as build_module

    source = inspect.getsource(build_module.AnalysisPanelBuildMixin._build_plugin_sections)
    assert f'"{_PLUGIN_STEM}"' in source

    from ui.panels.analysis.ml import AnalysisPanelMlMixin

    assert callable(
        getattr(AnalysisPanelMlMixin, "_on_run_silverquest", None)
    ), "the analysis panel needs a handler for the plugin callback"


def test_build_ui_returns_a_translated_group_box(qapp) -> None:
    plugin = SilverQuestPlugin()
    section = plugin.build_ui(callback=None)
    try:
        assert section is not None
        # build.py reads this property to title the QToolBox page.
        assert section.property("translate_key") == "SilverQuest Provenance"
        from PyQt5.QtWidgets import QLabel, QPushButton

        buttons = section.findChildren(QPushButton)
        labels = section.findChildren(QLabel)
        assert len(buttons) == 1
        assert buttons[0].property("translate_key") == "Run SilverQuest Provenance"
        assert labels, "the section needs an explanatory label"
    finally:
        section.deleteLater()


def test_build_ui_connects_the_callback(qapp) -> None:
    plugin = SilverQuestPlugin()
    calls: list[int] = []
    section = plugin.build_ui(callback=lambda: calls.append(1))
    try:
        from PyQt5.QtWidgets import QPushButton

        button = section.findChildren(QPushButton)[0]
        button.click()
        assert calls == [1]
    finally:
        section.deleteLater()


def test_default_params_match_the_r_shiny_inputs() -> None:
    defaults = SilverQuestPlugin().get_default_params()
    assert defaults == {
        "normalization": "204Pb",
        "dmax": 3.0,
        "jittered": True,
        "jitter_radius": 0.01,
    }
    # R lines 84-86: numericInput Radius 0.01 step 0.005, dmax 3 min 1 max 10.
    assert defaults["jitter_radius"] == pytest.approx(0.01)
    assert defaults["dmax"] == pytest.approx(3.0)


# ── integration: artefacts and references both selected by grouping column ──


def test_grouped_search_matches_artefacts_to_the_selected_reference_groups() -> None:
    """The whole point of the rework: both sides come from the loaded data.

    ``SiteA``/``SiteB`` are the artefact groups, ``OreX``/``OreY`` the reference
    groups; ``dmax=1.0`` sits between the two closest rows (dist 0 and
    0.3834233738598962) and the next one (dist 1.5336934954387278), so the hit
    counts are a property of the numbers, not of the plumbing.
    """
    frame = _synthetic_grouped_frame()

    payload = run_silverquest_on_groups(
        frame,
        "Group",
        ["SiteA", "SiteB"],
        ["OreX", "OreY"],
        dmax=1.0,
        jittered=False,
    )

    # The references are the selected rows, not a workbook.
    assert payload["reference_source"] == "groups"
    assert payload["reference_rows"] == 3
    assert payload["artefact_groups"] == ["SiteA", "SiteB"]
    assert payload["reference_groups"] == ["OreX", "OreY"]
    assert payload["artefact_indices"] == [0, 1, 2]
    assert payload["reference_indices"] == [3, 4, 5]

    result = payload["result"]
    assert result.database_rows == 3
    assert [artifact.no for artifact in result.artifacts] == ["A1", "A2", "B1"]

    # A1 is OreX verbatim: exactly one hit, at distance 0.
    a1 = result.artifacts[0]
    assert a1.n_hits == 1
    assert a1.hits[0]["Country"] == "OreX"
    assert a1.hits[0]["dist"] == pytest.approx(0.0, abs=0.0)

    # A2 is 0.0100 above OreX on every ratio (dist 0.383423) and just inside the
    # cut-off; B1 is 0.0200 above it (dist 1.533693) and just outside.
    a2 = result.artifacts[1]
    b1 = result.artifacts[2]
    assert a2.n_hits == 1
    assert a2.hits[0]["Country"] == "OreX"
    assert a2.hits[0]["dist"] == pytest.approx(0.3834233738598962, rel=1e-9)
    assert b1.n_hits == 0

    # The near-miss distance is still in the scored table (R's T1), which is what
    # makes the cut-off visible; the closest reference comes first.  R's ``no`` is
    # the 1-based database row, so key the table by it: both selected OreX rows
    # share a Country and would collide under that key.
    table_b1 = {row["no"]: (row["Country"], row["dist"]) for row in b1.table}
    assert table_b1[1] == ("OreX", pytest.approx(1.5336934954387278, rel=1e-9))
    assert table_b1[3] == ("OreY", pytest.approx(8488.19045005979, rel=1e-9))
    assert table_b1[1][1] < table_b1[3][1]

    assert payload["summary"] == (
        "SilverQuest (204Pb, dmax=1): 3 artefact(s), 2 hit(s) against 3 ore analyses."
    )

    # The nearest-reference outcome is reported per artefact.
    matches = {entry["artefact"]: entry for entry in payload["matches"]}
    assert matches["A1"]["nearest"] == "1"  # R's 1-based database row number
    assert matches["A1"]["reference_group"] == "OreX"
    assert matches["A1"]["distance"] == pytest.approx(0.0, abs=0.0)
    assert matches["A2"]["reference_group"] == "OreX"
    assert matches["A2"]["distance"] == pytest.approx(0.3834233738598962, rel=1e-9)
    assert matches["B1"]["nearest"] == ""
    assert matches["B1"]["distance"] is None


def test_grouped_search_ranks_the_selected_references_by_weighted_distance() -> None:
    """With a permissive cut-off every artefact hits both selected references."""
    frame = _synthetic_grouped_frame()

    payload = run_silverquest_on_groups(
        frame,
        "Group",
        ["SiteA", "SiteB"],
        ["OreX", "OreY"],
        dmax=10000.0,
        jittered=False,
    )
    result = payload["result"]

    assert [artifact.n_hits for artifact in result.artifacts] == [3, 3, 3]
    for artifact in result.artifacts:
        # `hits` keeps the R order: closest last (R line 372).  Both OreX rows
        # are identical, so the closest hit is always the first OreX.
        assert [hit["Country"] for hit in artifact.hits] == ["OreY", "OreX", "OreX"]
        distances = [hit["dist"] for hit in artifact.hits]
        assert distances[-1] == min(distances), "closest hit comes last"

    # Hand-derivable from the transcription: 204Pb normalisation has
    # smatrix = diag(0.001 * (2*18.7, 3*15.65, 4*39.0)) with the correlation
    # cross-terms of romatrix (0.96/0.94/0.96).  A common-mode offset of
    # d = 0.0100 on all three ratios costs 0.3834233738598962, and d = 0.0200
    # costs 1.5336934954387278.
    matches = {entry["artefact"]: entry for entry in payload["matches"]}
    assert matches["A1"]["reference_group"] == "OreX"
    assert matches["A2"]["reference_group"] == "OreX"
    assert matches["B1"]["reference_group"] == "OreX"
    assert matches["A1"]["distance"] == pytest.approx(0.0, abs=0.0)
    assert matches["A2"]["distance"] == pytest.approx(0.3834233738598962, rel=1e-9)
    assert matches["B1"]["distance"] == pytest.approx(1.5336934954387278, rel=1e-9)


def test_grouped_search_roles_label_every_selected_row() -> None:
    """The applied column is what the plot colours, so every row gets a role.

    Both sides carry the same matched/unmatched pair, and each row's label is its
    own outcome: ``SiteA`` holds two hits and ``SiteB`` none, while of the two
    ``OreX`` rows only the exact one was hit.
    """
    frame = _synthetic_grouped_frame()

    payload = run_silverquest_on_groups(
        frame, "Group", ["SiteA", "SiteB"], ["OreX", "OreY"], dmax=1.0, jittered=False
    )

    assert payload["applied_column"] == [
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_SAMPLE_UNMATCHED_PREFIX + "SiteB",
        ROLE_REFERENCE_MATCHED_PREFIX + "OreX",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "OreX",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "OreY",
    ]
    # The grouping values themselves are ordinary data; a shape per role is not
    # involved, so one grouping column is drawn with a single marker.
    assert set(payload["roles"].values()) == {
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_SAMPLE_UNMATCHED_PREFIX + "SiteB",
        ROLE_REFERENCE_MATCHED_PREFIX + "OreX",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "OreX",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "OreY",
    }
    # SiteA holds a hit, SiteB does not: the group-level summary follows the rows.
    assert payload["role_by_group"]["SiteA"] == ROLE_SAMPLE_MATCHED_PREFIX
    assert payload["role_by_group"]["SiteB"] == ROLE_SAMPLE_UNMATCHED_PREFIX
    assert payload["role_by_group"]["OreX"] == ROLE_REFERENCE_MATCHED_PREFIX
    assert payload["role_by_group"]["OreY"] == ROLE_REFERENCE_UNMATCHED_PREFIX


def test_each_side_is_counted_by_outcome() -> None:
    """``role_counts`` reports the split the role column draws, per side."""
    frame = _synthetic_grouped_frame()

    payload = run_silverquest_on_groups(
        frame, "Group", ["SiteA", "SiteB"], ["OreX", "OreY"], dmax=1.0, jittered=False
    )

    assert payload["role_counts"]["samples"] == {
        "selected": 3,
        "entered": 3,
        "matched": 2,
        "unmatched": 1,
        "excluded": 0,
    }
    assert payload["role_counts"]["references"] == {
        "selected": 3,
        "entered": 3,
        "matched": 1,
        "unmatched": 2,
        "excluded": 0,
    }


def test_one_group_holding_both_outcomes_is_split_per_sample() -> None:
    """Reported as "reference data is split into match and unmatch, the samples are not".

    The role used to be decided per *grouping value*, so one hit anywhere in a group
    marked every sample of that group matched - and when all samples share one group
    (the usual case: one site, or one artefact set) the two outcomes never appeared on
    the sample side at all.  The sample that hit and the sample that did not must be
    distinguishable even though they carry the same grouping value.
    """
    frame = pd.DataFrame(
        {
            "Sample": ["HIT", "MISS", "R1"],
            "Site": ["Tarim", "Tarim", "OreX"],
            "Pb206_204": [18.5764, 17.0000, 18.5764],
            "Pb207_204": [15.6597, 15.0000, 15.6597],
            "Pb208_204": [38.5890, 36.0000, 38.5890],
        }
    )

    payload = run_silverquest_on_groups(
        frame, "Site", ["Tarim"], ["OreX"], dmax=1.0, jittered=False
    )

    assert payload["applied_column"][:2] == [
        ROLE_SAMPLE_MATCHED_PREFIX + "Tarim",
        ROLE_SAMPLE_UNMATCHED_PREFIX + "Tarim",
    ]
    assert payload["role_counts"]["samples"]["matched"] == 1
    assert payload["role_counts"]["samples"]["unmatched"] == 1
    # The grouping value "Tarim" now yields both sample labels; the summary has to
    # pick one, and "matched" wins because that is the stronger outcome.
    assert payload["role_by_group"]["Tarim"] == ROLE_SAMPLE_MATCHED_PREFIX


def test_rows_that_never_entered_the_search_stay_other_data() -> None:
    """A row with unusable ratios is not a sample that was searched and missed.

    ``records_from_frame`` withholds it, so it never becomes an artefact; labelling
    it ``[Sample Unmatched]`` would claim a search that never happened, and counting
    it as unmatched would inflate the miss count.
    """
    frame = pd.DataFrame(
        {
            "Sample": ["A1", "A2", "R1"],
            "Site": ["SiteA", "SiteA", "OreX"],
            "Pb206_204": [18.5764, "n/a", 18.5764],
            "Pb207_204": [15.6597, 15.7000, 15.6597],
            "Pb208_204": [38.5890, 38.6000, 38.5890],
        }
    )

    payload = run_silverquest_on_groups(
        frame, "Site", ["SiteA"], ["OreX"], dmax=1.0, jittered=False
    )

    assert payload["applied_column"] == [
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_OTHER,
        ROLE_REFERENCE_MATCHED_PREFIX + "OreX",
    ]
    assert payload["role_counts"]["samples"] == {
        "selected": 2,
        "entered": 1,
        "matched": 1,
        "unmatched": 0,
        "excluded": 1,
    }


def test_grouped_search_handles_a_grouping_column_that_is_not_a_rangeindex() -> None:
    """Row positions, not index labels, are what the role column is addressed by."""
    frame = _synthetic_grouped_frame()
    frame.index = [10, 11, 12, 13, 14, 15]

    payload = run_silverquest_on_groups(
        frame, "Group", ["SiteA"], ["OreX"], dmax=2.0, jittered=False
    )

    assert payload["artefact_indices"] == [0, 1]
    assert payload["reference_indices"] == [3, 4]
    assert payload["applied_column"] == [
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_OTHER,
        ROLE_REFERENCE_MATCHED_PREFIX + "OreX",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "OreX",
        ROLE_OTHER,
    ]


def test_grouped_search_reads_the_r_input_spelling_too() -> None:
    """The R input format (``Pb206204``) must work as well as the app's spelling."""
    frame = _synthetic_grouped_frame().rename(
        columns={
            "Pb206_204": "Pb206204",
            "Pb207_204": "Pb207204",
            "Pb208_204": "Pb208204",
        }
    )
    payload = run_silverquest_on_groups(
        frame, "Group", ["SiteA"], ["OreX"], dmax=2.0, jittered=False
    )
    assert payload["result"].artifacts[0].hits[0]["dist"] == pytest.approx(0.0, abs=0.0)


def test_grouped_search_accepts_the_galena_workbook_as_extra_references() -> None:
    """One way of supplying references among others, not the interface."""
    frame = _synthetic_grouped_frame()

    payload = run_silverquest_on_groups(
        frame,
        "Group",
        ["SiteA"],
        [],  # no reference group at all
        dmax=3.0,
        jittered=False,
        seed=1,
    )

    assert payload["reference_source"] == "workbook"
    assert payload["reference_rows"] > 1000  # the R package's galena database
    assert payload["reference_only"] is True
    assert payload["applied_column"] == [
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_SAMPLE_MATCHED_PREFIX + "SiteA",
        ROLE_OTHER,
        ROLE_OTHER,
        ROLE_OTHER,
        ROLE_OTHER,
    ]
    # The workbook rows are not frame rows, so the reference side is counted from
    # the table the search actually used.
    references = payload["role_counts"]["references"]
    assert references["entered"] == payload["reference_rows"]
    assert references["matched"] >= 1
    assert references["unmatched"] == references["entered"] - references["matched"]
    matches = {entry["artefact"]: entry for entry in payload["matches"]}
    assert matches["A1"]["nearest"], "the workbook must produce a nearest reference"
    assert matches["A1"]["distance"] is not None


def test_grouped_search_rejects_an_unknown_grouping_column() -> None:
    frame = _synthetic_grouped_frame()
    with pytest.raises(ValueError, match="no grouping column"):
        run_silverquest_on_groups(frame, "Nope", ["SiteA"], ["OreX"])


def test_grouped_search_rejects_an_empty_role_selection(tmp_path, monkeypatch) -> None:
    """No reference group *and* no usable workbook is refused, not guessed."""
    frame = _synthetic_grouped_frame()
    with pytest.raises(ValueError, match="no artefact group selected"):
        run_silverquest_on_groups(frame, "Group", [], ["OreX"])

    import adapters.silverquest as silverquest_core

    monkeypatch.setattr(
        silverquest_core,
        "resolve_database_path",
        lambda path=None: tmp_path / "absent.xlsx",
    )
    with pytest.raises(ValueError, match="no reference group selected"):
        run_silverquest_on_groups(frame, "Group", ["SiteA"], [])


def test_grouped_search_reports_a_missing_workbook_when_no_group_is_selected(
    tmp_path,
) -> None:
    """An explicit workbook path is trusted, so a typo surfaces as an error."""
    frame = _synthetic_grouped_frame()
    with pytest.raises(FileNotFoundError, match="Pb_DB_20240310AllGalenas"):
        run_silverquest_on_groups(
            frame,
            "Group",
            ["SiteA"],
            [],
            database_path=str(tmp_path / "absent.xlsx"),
        )


# ── reference resolution and the legacy record entry point ──────────────────


def test_resolve_references_prefers_the_selected_rows_over_the_workbook() -> None:
    database, source = resolve_references(
        [
            {
                "no": "X1",
                "group": "OreX",
                "Pb206204": 18.5,
                "Pb207204": 15.6,
                "Pb208204": 38.5,
            }
        ],
        database_path="Z:/definitely/absent.xlsx",
    )
    assert source == "groups"
    assert database.n_rows == 1
    assert database.country.tolist() == ["OreX"]


def test_resolve_references_falls_back_to_the_workbook() -> None:
    database, source = resolve_references(None)
    assert source == "workbook"
    assert database.n_rows > 1000


def test_search_delegates_to_the_numeric_core(tmp_path) -> None:
    """The record entry point still runs the port end to end on a workbook."""
    pandas = pytest.importorskip("pandas")
    workbook = tmp_path / "tiny_db.xlsx"
    pandas.DataFrame(
        {
            "Country": ["Peru"],
            "Latitude": [-12.0],
            "Longitude": [-75.0],
            "Pb206204": [0.0],
            "Pb207204": [0.0],
            "Pb208204": [1.0],
        }
    ).to_excel(workbook, index=False)

    payload = SilverQuestPlugin().search(
        [{"no": "A", "Pb206204": 0.05, "Pb207204": 0.05, "Pb208204": 1.05}],
        database_path=str(workbook),
        jittered=False,
    )
    result = payload["result"]
    assert result.database_rows == 1
    assert result.total_hits == 1
    assert result.artifacts[0].no == "A"
    # dist = 0.05**2/(f*2*18.7) + cross terms + 0.05**2/(f*3*15.65) = 2.396030
    assert result.artifacts[0].hits[0]["dist"] == pytest.approx(2.396030167416815, rel=1e-9)
    assert "SilverQuest" in payload["summary"]


def test_search_reports_a_missing_database(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Pb_DB_20240310AllGalenas"):
        run_silverquest_search(
            [{"no": "A", "Pb206204": 1.0, "Pb207204": 1.0, "Pb208204": 1.0}],
            database_path=str(tmp_path / "absent.xlsx"),
        )


def test_database_available_reports_the_missing_workbook(tmp_path) -> None:
    ok, message = SilverQuestPlugin().database_available(str(tmp_path / "absent.xlsx"))
    assert ok is False
    assert "ISOTOPES_SILVERQUEST_DB" in message


def test_database_available_accepts_a_present_workbook(tmp_path) -> None:
    workbook = tmp_path / "present.xlsx"
    workbook.write_bytes(b"placeholder")
    ok, message = SilverQuestPlugin().database_available(str(workbook))
    assert ok is True
    assert message == str(workbook)


def test_a_match_names_the_reference_it_matched() -> None:
    """Both sides of a match are labelled, and both sides also carry their misses.

    Reported as "red copper and Tarim are both original data - where do I see what matched what?":
    a role alone left the partner to the dialog table, so the data itself could not answer it.  The
    answer is the same column read row by row: the sample that hit a reference is
    ``[Sample Matched]`` and the reference it hit is ``[Reference Matched]``, while the sample that
    hit nothing is ``[Sample Unmatched]`` and the references nobody hit are
    ``[Reference Unmatched]``.
    """
    import pandas as pd

    from plugins.builtins.silverquest_plugin import run_silverquest_on_groups

    ore = {"Pb206_204": 18.5764, "Pb207_204": 15.6597, "Pb208_204": 38.589}
    rows = [dict(ore, Sample=f"R{i}", Site="Tarim") for i in range(90)]
    rows.append(dict(ore, Sample="A1", Site="Red Copper"))
    rows.append({"Sample": "B1", "Site": "Bronze", "Pb206_204": 17.0, "Pb207_204": 15.0, "Pb208_204": 36.0})
    # One reference nobody can hit, so both reference labels are present.
    rows.append(
        {"Sample": "F1", "Site": "Faraway", "Pb206_204": 21.0, "Pb207_204": 15.8, "Pb208_204": 40.0}
    )
    frame = pd.DataFrame(rows)

    out = run_silverquest_on_groups(
        frame, "Site", ["Red Copper", "Bronze"], ["Tarim", "Faraway"], dmax=1.0
    )

    roles = [str(role) for role in out["applied_column"]]
    assert sorted(set(roles)) == [
        ROLE_REFERENCE_MATCHED_PREFIX + "Tarim",
        ROLE_REFERENCE_UNMATCHED_PREFIX + "Faraway",
        ROLE_SAMPLE_MATCHED_PREFIX + "Red Copper",
        ROLE_SAMPLE_UNMATCHED_PREFIX + "Bronze",
    ], sorted(set(roles))
    # Exactly one sample matched; every reference row is labelled on its own outcome.
    assert roles.count(ROLE_SAMPLE_MATCHED_PREFIX + "Red Copper") == 1
    assert roles.count(ROLE_REFERENCE_MATCHED_PREFIX + "Tarim") == 90
    assert roles.count(ROLE_REFERENCE_UNMATCHED_PREFIX + "Faraway") == 1
    counts = out["role_counts"]
    assert counts["samples"] == {
        "selected": 2,
        "entered": 2,
        "matched": 1,
        "unmatched": 1,
        "excluded": 0,
    }
    assert counts["references"]["matched"] == 90
    assert counts["references"]["unmatched"] == 1
