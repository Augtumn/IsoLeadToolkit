"""`data/metadata_profile/ratios.py` 与 `validate.py` 的单元测试。

ratios：8 个比值的因子链推导、往返一致性、一阶相对误差传播（手算可验的算例）、
相对↔绝对换算、缺主比值时的增量行为。
validate：每条规则一正一反、系统提供字段留空不报错（回归）、open_ended 词表降级、
四条条件联动、外键悬空与跨级直挂、工作簿聚合与计数。
另含硬约束守卫：不得导入 PyQt5 / pandas / openpyxl、单文件 ≤800 行、异常处理器不得静默。

夹具用 `spec.py` 手工构造（FieldSpec / TableSpec / Profile），不依赖 parse.py / profile.py；
受控词表用假的 `vocab` 模块注入 `sys.modules`，同样不依赖 vocab.py 是否已落地。
"""
from __future__ import annotations

import ast
import datetime
import logging
import math
import sys
import types
from pathlib import Path

import pytest

import data.metadata_profile
from data.metadata_profile import ratios, spec, validate, validate_sheets
from data.metadata_profile.layout import SheetKind, SheetSpec, WorkbookLayout, make_column
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOCAB_MODULE_NAME = "data.metadata_profile.vocab"

MEASURED = {
    "206Pb/204Pb": 18.59123,
    "207Pb/204Pb": 15.62345,
    "208Pb/204Pb": 38.76543,
}
P6, P7, P8 = (MEASURED[name] for name in spec.PRIMARY_LIA_RATIO_NAMES)
UNCERTAIN_206 = 0.001 * P6  # 206/204 的 0.1% 相对不确定度对应的绝对值


# ── 夹具 ─────────────────────────────────────────────────────────────────────


def make_field(**overrides) -> FieldSpec:
    """构造一个 FieldSpec；只覆盖测试关心的字段。"""
    defaults = dict(
        oid="SI1",
        key="site_name",
        label_en="Site name",
        table=TableKey.SITE,
        obligation=Obligation.RECOMMENDED,
        occurrence=Occurrence.ZERO_TO_ONE,
        provided_by=(ProvidedBy.DATA_PROVIDER,),
        definition="",
        allowed="",
        example="",
        parent=None,
        depth=0,
        block=None,
        block_owner=None,
        value_kind=ValueKind.FREE_TEXT,
        vocab_id=None,
        source_doc="reference/metadata/docs/metadata_sites.md",
        source_line=1,
        order=0,
    )
    defaults.update(overrides)
    return FieldSpec(**defaults)


def make_table(key: TableKey = TableKey.SITE, *fields: FieldSpec) -> TableSpec:
    """构造只含自有字段的 TableSpec。"""
    return TableSpec(key=key, own_fields=tuple(fields), inlined_blocks=(), fields=tuple(fields))


def make_profile(*tables: TableSpec) -> Profile:
    """构造一个 Profile。"""
    return Profile(version="test", tables=tuple(tables))


def install_vocab(monkeypatch, module: types.ModuleType | None) -> None:
    """把假 `vocab` 模块注入 `sys.modules`（``None`` 模拟模块缺失）。"""
    monkeypatch.delattr(data.metadata_profile, "vocab", raising=False)
    if module is None:
        monkeypatch.setitem(sys.modules, VOCAB_MODULE_NAME, None)
        return
    monkeypatch.setitem(sys.modules, VOCAB_MODULE_NAME, module)
    monkeypatch.setattr(data.metadata_profile, "vocab", module, raising=False)


def fake_vocab(
    terms: dict[str, tuple[str, ...]],
    *,
    open_ids: frozenset[str] = frozenset(),
    by_oid: dict[str, str] | None = None,
) -> types.ModuleType:
    """构造最小 vocab 模块：contains / terms / open_ended / vocab_id_for。"""
    module = types.ModuleType(VOCAB_MODULE_NAME)
    module.terms = lambda vocab_id: tuple(terms.get(vocab_id, ()))
    module.open_ended = lambda vocab_id: vocab_id in open_ids
    module.contains = lambda vocab_id, value: (
        value is not None
        and " ".join(str(value).split()).casefold()
        in {" ".join(term.split()).casefold() for term in terms.get(vocab_id, ())}
    )
    module.vocab_id_for = lambda field: (by_oid or {}).get(field.oid)
    return module


def errors(issues) -> list[validate.ValidationIssue]:
    """筛选 ERROR。"""
    return [issue for issue in issues if issue.severity is validate.Severity.ERROR]


def warnings(issues) -> list[validate.ValidationIssue]:
    """筛选 WARNING。"""
    return [issue for issue in issues if issue.severity is validate.Severity.WARNING]


# ── ratios.py ────────────────────────────────────────────────────────────────


def test_ratio_sources_match_spec() -> None:
    assert {ratios.SOURCE_ORIGINAL, ratios.SOURCE_CALCULATED} == set(spec.RATIO_SOURCES)


def test_derive_all_ratios_returns_eight_with_correct_sources() -> None:
    result = ratios.derive_all_ratios(MEASURED)
    assert set(result) == set(spec.LIA_RATIO_NAMES)
    assert len(result) == 8
    for name in spec.PRIMARY_LIA_RATIO_NAMES:
        assert result[name].source == ratios.SOURCE_ORIGINAL
        assert result[name].value == MEASURED[name]
        assert result[name].is_primary
    for name in spec.DERIVED_LIA_RATIO_NAMES:
        assert result[name].source == ratios.SOURCE_CALCULATED
        assert result[name].is_calculated
        assert not result[name].is_primary


def test_derived_values_match_independent_algebra() -> None:
    result = ratios.derive_all_ratios(MEASURED)
    expected = {
        "204Pb/206Pb": 1.0 / P6,
        "207Pb/206Pb": P7 / P6,
        "208Pb/206Pb": P8 / P6,
        "207Pb/208Pb": P7 / P8,
        "206Pb/208Pb": P6 / P8,
    }
    for name, value in expected.items():
        assert result[name].value == pytest.approx(value, rel=1e-12), name


def test_inverse_round_trip_matches_original_ratio() -> None:
    result = ratios.derive_all_ratios(MEASURED)
    assert 1.0 / result["204Pb/206Pb"].value == pytest.approx(P6, rel=1e-12)
    assert 1.0 / result["206Pb/208Pb"].value == pytest.approx(P8 / P6, rel=1e-12)


def test_ratio_of_primaries_matches_derived_ratio() -> None:
    result = ratios.derive_all_ratios(MEASURED)
    assert result["207Pb/206Pb"].value == pytest.approx(
        result["207Pb/204Pb"].value / result["206Pb/204Pb"].value, rel=1e-12
    )


def test_missing_primary_returns_reported_only_and_warns(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios({"206Pb/204Pb": P6, "207Pb/204Pb": P7})
    assert set(result) == {"206Pb/204Pb", "207Pb/204Pb"}
    assert "208Pb/204Pb" in caplog.text
    assert result["206Pb/204Pb"].source == ratios.SOURCE_ORIGINAL


def test_empty_input_returns_empty_without_raising(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    assert ratios.derive_all_ratios({}) == {}
    assert caplog.records


def test_non_numeric_primary_is_treated_as_missing(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios({**MEASURED, "208Pb/204Pb": "t.b.d."})
    assert set(result) == set(spec.PRIMARY_LIA_RATIO_NAMES) - {"208Pb/204Pb"}
    assert "208Pb/204Pb" in caplog.text


def test_numeric_strings_are_accepted() -> None:
    result = ratios.derive_all_ratios({name: str(value) for name, value in MEASURED.items()})
    assert len(result) == 8
    assert result["206Pb/204Pb"].value == pytest.approx(P6)


def test_unknown_ratio_name_is_ignored_with_warning(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios({**MEASURED, "204Pb/204Pb": 1.0})
    assert "204Pb/204Pb" not in result
    assert "204Pb/204Pb" in caplog.text


def test_reported_derived_ratio_keeps_original_value_and_source() -> None:
    result = ratios.derive_all_ratios({**MEASURED, "207Pb/206Pb": 0.8404})
    assert len(result) == 8
    assert result["207Pb/206Pb"].value == 0.8404
    assert result["207Pb/206Pb"].source == ratios.SOURCE_ORIGINAL


def test_relative_uncertainty_is_derived_from_absolute() -> None:
    result = ratios.derive_all_ratios(MEASURED, uncertainties={"206Pb/204Pb": UNCERTAIN_206})
    primary = result["206Pb/204Pb"]
    assert primary.uncertainty_absolute == UNCERTAIN_206
    assert primary.uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)


def test_propagation_inverse_ratio_keeps_relative_uncertainty() -> None:
    """仅 206/204 带 0.1% 时，204/206 的相对不确定度同为 0.1%（指数 -1 取平方后同号）。"""
    result = ratios.derive_all_ratios(
        MEASURED,
        uncertainties={"206Pb/204Pb": UNCERTAIN_206, "207Pb/204Pb": 0.0, "208Pb/204Pb": 0.0},
    )
    assert result["204Pb/206Pb"].uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)
    assert result["207Pb/206Pb"].uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)
    assert result["208Pb/206Pb"].uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)


def test_propagation_combines_two_primaries_in_quadrature() -> None:
    """207/206 = (207/204)/(206/204)：两侧各 0.1% → sqrt(2) × 0.1%。"""
    result = ratios.derive_all_ratios(
        MEASURED,
        uncertainties={
            "206Pb/204Pb": 0.001 * P6,
            "207Pb/204Pb": 0.001 * P7,
            "208Pb/204Pb": 0.0,
        },
    )
    expected_percent = 100.0 * 0.001 * math.sqrt(2.0)
    assert result["207Pb/206Pb"].uncertainty_relative_percent == pytest.approx(
        expected_percent, rel=1e-9
    )
    assert result["208Pb/206Pb"].uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)


def test_propagated_absolute_uncertainty_is_consistent_with_relative() -> None:
    result = ratios.derive_all_ratios(
        MEASURED, uncertainties={"206Pb/204Pb": UNCERTAIN_206, "207Pb/204Pb": 0.0}
    )
    derived = result["207Pb/206Pb"]
    assert derived.uncertainty_absolute == pytest.approx(
        derived.value * derived.uncertainty_relative_percent / 100.0, rel=1e-9
    )


def test_partial_uncertainty_leaves_dependent_ratios_unknown() -> None:
    """规则：某主比值缺不确定度 → 依赖它的派生值不确定度置 None（不把未知当 0）。"""
    result = ratios.derive_all_ratios(MEASURED, uncertainties={"206Pb/204Pb": UNCERTAIN_206})
    assert result["204Pb/206Pb"].uncertainty_absolute is not None
    assert result["207Pb/206Pb"].uncertainty_absolute is None
    assert result["207Pb/206Pb"].uncertainty_relative_percent is None
    assert result["208Pb/206Pb"].uncertainty_absolute is None


def test_missing_uncertainty_differs_from_explicit_zero() -> None:
    """口径固化：缺一个主比值的不确定度（→ None）与显式传 0（→ 参与平方和）必须可区分。"""
    missing = ratios.derive_all_ratios(MEASURED, uncertainties={"206Pb/204Pb": UNCERTAIN_206})
    explicit_zero = ratios.derive_all_ratios(
        MEASURED,
        uncertainties={"206Pb/204Pb": UNCERTAIN_206, "207Pb/204Pb": 0.0, "208Pb/204Pb": 0.0},
    )
    assert missing["207Pb/206Pb"].uncertainty_absolute is None
    assert explicit_zero["207Pb/206Pb"].uncertainty_absolute is not None
    assert explicit_zero["207Pb/206Pb"].uncertainty_relative_percent == pytest.approx(0.1, rel=1e-9)
    assert explicit_zero["207Pb/206Pb"].uncertainty_absolute > 0


def test_no_uncertainties_means_all_none() -> None:
    result = ratios.derive_all_ratios(MEASURED)
    assert all(issue.uncertainty_absolute is None for issue in result.values())
    assert all(issue.uncertainty_relative_percent is None for issue in result.values())


def test_negative_uncertainty_is_ignored_with_warning(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios(MEASURED, uncertainties={"206Pb/204Pb": -0.001})
    assert result["206Pb/204Pb"].uncertainty_absolute is None
    assert caplog.records


def test_sigma_is_written_to_every_ratio() -> None:
    result = ratios.derive_all_ratios(MEASURED, sigma=2)
    assert {issue.sigma for issue in result.values()} == {2}


def test_out_of_range_sigma_is_kept_for_validation(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios(MEASURED, sigma=4)
    assert result["206Pb/204Pb"].sigma == 4
    assert caplog.records


def test_non_integral_sigma_is_dropped(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    result = ratios.derive_all_ratios(MEASURED, sigma=2.5)
    assert result["206Pb/204Pb"].sigma is None
    assert caplog.records


def test_absolute_from_relative() -> None:
    assert ratios.absolute_from_relative(18.59123, 0.1) == pytest.approx(0.01859123)
    assert ratios.absolute_from_relative(100.0, 0.0) == 0.0


def test_relative_from_absolute_round_trip() -> None:
    absolute = ratios.absolute_from_relative(P6, 0.1)
    assert ratios.relative_from_absolute(P6, absolute) == pytest.approx(0.1, rel=1e-12)


def test_relative_from_absolute_rejects_zero_value(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    assert ratios.relative_from_absolute(0.0, 0.0001) is None
    assert caplog.records


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_relative_from_absolute_rejects_non_finite(caplog, bad_value) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.ratios")
    assert ratios.relative_from_absolute(bad_value, 0.0001) is None
    assert caplog.records


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("206Pb/204Pb", ("206Pb/204Pb",)),
        ("204Pb/206Pb", ("206Pb/204Pb",)),
        ("207Pb/206Pb", ("207Pb/204Pb", "206Pb/204Pb")),
        ("207Pb/208Pb", ("207Pb/204Pb", "208Pb/204Pb")),
        ("206Pb/208Pb", ("206Pb/204Pb", "208Pb/204Pb")),
    ],
)
def test_primary_from_derived_matches_factor_chain(name, expected) -> None:
    assert ratios.primary_from_derived(name) == expected


def test_primary_from_derived_rejects_unknown_name() -> None:
    with pytest.raises(KeyError):
        ratios.primary_from_derived("205Pb/204Pb")


def test_format_ratio_uses_five_decimals() -> None:
    assert ratios.format_ratio(18.59123) == "18.59123"
    assert ratios.format_ratio(18.5) == "18.50000"
    assert ratios.format_ratio(18.59123456, decimals=3) == "18.591"


def test_format_uncertainty_matches_archive_example() -> None:
    assert ratios.format_uncertainty(0.00008) == "0.00008"
    assert ratios.format_uncertainty(0.0) == "0"
    assert ratios.format_uncertainty(1.0) == "1"
    assert "e" in ratios.format_uncertainty(1e-9)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_format_helpers_flag_non_finite_values(bad_value) -> None:
    assert ratios.format_ratio(bad_value) == ratios.NOT_AVAILABLE
    assert ratios.format_uncertainty(bad_value) == ratios.NOT_AVAILABLE


# ── validate.py：字段级规则 ───────────────────────────────────────────────────


def test_mandatory_field_missing_is_error() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    issues = validate.validate_columns((column,), {})
    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity is validate.Severity.ERROR
    assert issue.message_key == validate.MSG_REQUIRED
    assert issue.field_oid == "SI1" and issue.field_key == "site_name"
    assert issue.params["field"] == "Site name"
    assert "Site name" in validate.format_message(issue)


def test_mandatory_field_filled_is_clean() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    assert validate.validate_columns((column,), {"site_name": "Troia"}) == []


def test_system_provided_mandatory_field_may_stay_empty() -> None:
    """回归：系统补齐的字段（B6.7 Source / A15.*）留空不得报必填错。"""
    column = make_field(
        oid="B6.7",
        key="lia_ratio_source",
        label_en="Source",
        obligation=Obligation.MANDATORY,
        provided_by=(ProvidedBy.SYSTEM,),
        value_kind=ValueKind.RATIO_SOURCE,
    )
    assert validate.validate_columns((column,), {}) == []


def test_dual_provider_mandatory_field_is_required() -> None:
    column = make_field(
        obligation=Obligation.MANDATORY,
        provided_by=(ProvidedBy.DATA_PROVIDER, ProvidedBy.SYSTEM),
    )
    assert len(errors(validate.validate_columns((column,), {}))) == 1


def test_optional_field_missing_is_clean() -> None:
    column = make_field(obligation=Obligation.OPTIONAL)
    assert validate.validate_columns((column,), {}) == []


@pytest.mark.parametrize("blank", [None, "", "   ", float("nan"), [], {}])
def test_blank_values_trigger_required_rule(blank) -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    assert len(errors(validate.validate_columns((column,), {"site_name": blank}))) == 1


def test_zero_is_not_blank() -> None:
    column = make_field(
        oid="B3.3.1", key="date_absolute_start", obligation=Obligation.MANDATORY,
        value_kind=ValueKind.INTEGER,
    )
    assert validate.validate_columns((column,), {"date_absolute_start": 0}) == []


def test_blank_value_skips_type_rules() -> None:
    """空值只触发必填规则；不得因空串再报一次"不是数字"。"""
    column = make_field(obligation=Obligation.MANDATORY, value_kind=ValueKind.DECIMAL)
    issues = validate.validate_columns((column,), {"site_name": ""})
    assert [issue.message_key for issue in issues] == [validate.MSG_REQUIRED]


@pytest.mark.parametrize(
    ("value_kind", "good", "bad"),
    [
        (ValueKind.DECIMAL, "15.3", "t.b.d."),
        (ValueKind.NUMBER, "100", "abc"),
        (ValueKind.INTEGER, "2024", "x"),
    ],
)
def test_numeric_rules(value_kind, good, bad) -> None:
    column = make_field(oid="X1", key="value", value_kind=value_kind)
    assert validate.validate_columns((column,), {"value": good}) == []
    issues = validate.validate_columns((column,), {"value": bad})
    assert [issue.message_key for issue in issues] == [validate.MSG_NOT_NUMERIC]
    assert issues[0].severity is validate.Severity.ERROR


def test_integer_field_flags_non_whole_values() -> None:
    column = make_field(oid="X1", key="value", value_kind=ValueKind.INTEGER)
    issues = validate.validate_columns((column,), {"value": 2.5})
    assert [issue.message_key for issue in issues] == [validate.MSG_NOT_INTEGER]
    assert issues[0].severity is validate.Severity.WARNING


@pytest.mark.parametrize("value", ["2024-02-24", datetime.date(2024, 2, 24)])
def test_date_rule_accepts_valid_dates(value) -> None:
    column = make_field(oid="A12", key="analysis_lia_date", value_kind=ValueKind.DATE)
    assert validate.validate_columns((column,), {"analysis_lia_date": value}) == []


@pytest.mark.parametrize("value", ["24.02.2024", "2024-02-30", "20240224", "2024-2-4"])
def test_date_rule_rejects_bad_dates(value) -> None:
    column = make_field(oid="A12", key="analysis_lia_date", value_kind=ValueKind.DATE)
    issues = validate.validate_columns((column,), {"analysis_lia_date": value})
    assert [issue.message_key for issue in issues] == [validate.MSG_INVALID_DATE]


@pytest.mark.parametrize(("value", "ok"), [(1, True), ("2", True), (3, True), (4, False), ("abc", False)])
def test_sigma_rule(value, ok) -> None:
    column = make_field(oid="B6.4", key="lia_ratio_uncertainty_sigma", value_kind=ValueKind.SIGMA)
    issues = validate.validate_columns((column,), {"lia_ratio_uncertainty_sigma": value})
    assert (issues == []) is ok
    if not ok:
        assert issues[0].message_key == validate.MSG_INVALID_SIGMA


def test_ratio_name_rule() -> None:
    column = make_field(oid="B6.1", key="lia_ratio_name", value_kind=ValueKind.RATIO_NAME)
    assert validate.validate_columns((column,), {"lia_ratio_name": "207Pb/206Pb"}) == []
    issues = validate.validate_columns((column,), {"lia_ratio_name": "205Pb/204Pb"})
    assert issues[0].message_key == validate.MSG_INVALID_RATIO_NAME


def test_ratio_source_rule() -> None:
    column = make_field(oid="B6.7", key="lia_ratio_source", value_kind=ValueKind.RATIO_SOURCE)
    assert validate.validate_columns((column,), {"lia_ratio_source": "calculated"}) == []
    issues = validate.validate_columns((column,), {"lia_ratio_source": "reported"})
    assert issues[0].message_key == validate.MSG_INVALID_RATIO_SOURCE


@pytest.mark.parametrize(
    ("oid", "key", "good", "bad"),
    [
        ("SI5.1.1", "site_geolocation_point_longitude", -180.0, 180.5),
        ("SI5.2.2", "site_geolocation_box_east", 12.5, -181.0),
        ("SI5.4.1.2", "site_geolocation_polygon_point_latitude", 90.0, -90.5),
    ],
)
def test_geolocation_bounds(oid, key, good, bad) -> None:
    column = make_field(oid=oid, key=key, value_kind=ValueKind.DECIMAL)
    assert validate.validate_columns((column,), {key: good}) == []
    issues = validate.validate_columns((column,), {key: bad})
    assert [issue.message_key for issue in issues] == [validate.MSG_OUT_OF_RANGE]
    assert issues[0].params["minimum"] < issues[0].params["maximum"]


def test_geolocation_out_of_range_reports_once() -> None:
    """越界只报值域错：数值可解析，不再叠一条"不是数字"。"""
    column = make_field(oid="SI5.1.1", key="lon", value_kind=ValueKind.DECIMAL)
    issues = validate.validate_columns((column,), {"lon": "999"})
    assert len(issues) == 1


def test_geolocation_non_numeric_reports_once() -> None:
    column = make_field(oid="SI5.1.1", key="lon", value_kind=ValueKind.DECIMAL)
    issues = validate.validate_columns((column,), {"lon": "east"})
    assert [issue.message_key for issue in issues] == [validate.MSG_NOT_NUMERIC]


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("https://example.org/a", True),
        ("http://hdl.handle.net/21.11157/x", True),
        ("www.example.org", False),
        ("ftp://example.org", False),
        ("https://", False),
    ],
)
def test_url_rule(value, ok) -> None:
    column = make_field(oid="A6.3", key="analysis_lia_instrument_pid", value_kind=ValueKind.URL)
    issues = validate.validate_columns((column,), {"analysis_lia_instrument_pid": value})
    assert (issues == []) is ok


@pytest.mark.parametrize(
    ("value", "ok"), [("a@b.org", True), ("user@localhost", False), ("not-an-email", False)]
)
def test_email_rule(value, ok) -> None:
    column = make_field(oid="E1", key="contact_email", value_kind=ValueKind.EMAIL)
    issues = validate.validate_columns((column,), {"contact_email": value})
    assert (issues == []) is ok
    if not ok:
        assert issues[0].severity is validate.Severity.WARNING


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("10.60510/ICDP5054ESYI201", True),
        ("0000-0002-1825-0097", True),
        ("https://ror.org/02mhbdp94", True),
        ("99152/p0qhb66vvth", True),
        ("not a pid", False),
        ("/missing-prefix", False),
    ],
)
def test_pid_rule(value, ok) -> None:
    column = make_field(oid="B5.1.1", key="relation_pid_value", value_kind=ValueKind.PID)
    issues = validate.validate_columns((column,), {"relation_pid_value": value})
    assert (issues == []) is ok
    if not ok:
        assert issues[0].message_key == validate.MSG_SUSPECT_PID
        assert issues[0].severity is validate.Severity.WARNING


# ── validate.py：受控词表 ────────────────────────────────────────────────────


def vocab_column(**overrides) -> FieldSpec:
    """一个受控词表字段（默认为封闭词表 ore/glass/metal）。"""
    defaults = dict(
        oid="O12",
        key="object_material",
        label_en="Material",
        table=TableKey.OBJECT,
        obligation=Obligation.MANDATORY,
        value_kind=ValueKind.CONTROLLED_VOCAB,
        vocab_id="object_material",
    )
    defaults.update(overrides)
    return make_field(**defaults)


def test_vocab_value_inside_closed_vocabulary_is_clean(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("ore", "glass", "metal")}))
    assert validate.validate_columns((vocab_column(),), {"object_material": "ore"}) == []


def test_vocab_value_outside_closed_vocabulary_is_error(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("ore", "glass", "metal")}))
    issues = validate.validate_columns((vocab_column(),), {"object_material": "copper"})
    assert [issue.message_key for issue in issues] == [validate.MSG_VOCAB_UNKNOWN]
    assert issues[0].severity is validate.Severity.ERROR
    assert issues[0].params["value"] == "copper"


def test_vocab_value_outside_open_vocabulary_is_warning(monkeypatch) -> None:
    install_vocab(
        monkeypatch,
        fake_vocab({"site_type": ("settlement",)}, open_ids=frozenset({"site_type"})),
    )
    column = vocab_column(oid="SI8", key="site_type", vocab_id="site_type")
    issues = validate.validate_columns((column,), {"site_type": "hillfort"})
    assert [issue.message_key for issue in issues] == [validate.MSG_VOCAB_UNKNOWN_OPEN]
    assert issues[0].severity is validate.Severity.WARNING


def test_vocab_matching_is_case_and_space_insensitive(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("NIST SRM 981",)}))
    column = vocab_column()
    assert validate.validate_columns((column,), {"object_material": "  nist   srm 981 "}) == []


def test_vocab_without_terms_is_not_checked(monkeypatch) -> None:
    """空词表不得把所有值判成"词表外"。"""
    install_vocab(monkeypatch, fake_vocab({}))
    assert validate.validate_columns((vocab_column(),), {"object_material": "anything"}) == []


def test_vocab_module_unavailable_is_lenient(monkeypatch) -> None:
    """vocab.py 未落地时回退 open_ended=True：跳过成员判断（只记 debug）。"""
    install_vocab(monkeypatch, None)
    assert validate.validate_columns((vocab_column(),), {"object_material": "copper"}) == []


def test_vocab_id_resolved_by_oid_when_field_has_none(monkeypatch) -> None:
    install_vocab(
        monkeypatch,
        fake_vocab({"object_material": ("ore",)}, by_oid={"O12": "object_material"}),
    )
    column = vocab_column(vocab_id=None)
    issues = validate.validate_columns((column,), {"object_material": "copper"})
    assert [issue.message_key for issue in issues] == [validate.MSG_VOCAB_UNKNOWN]


def test_non_vocab_kind_is_not_checked_against_vocabulary(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("ore",)}))
    column = vocab_column(value_kind=ValueKind.FREE_TEXT)
    assert validate.validate_columns((column,), {"object_material": "copper"}) == []


def test_vocab_lookup_failure_degrades_without_raising(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.validate")
    module = fake_vocab({"object_material": ("ore",)})

    def broken_contains(vocab_id, value):
        raise RuntimeError("boom")

    module.contains = broken_contains
    install_vocab(monkeypatch, module)
    assert validate.validate_columns((vocab_column(),), {"object_material": "ore"}) == []
    assert caplog.records


def test_real_vocab_module_integration() -> None:
    """vocab.py 落地后与真实词表联调；未落地时跳过（本任务不硬依赖它）。"""
    pytest.importorskip(VOCAB_MODULE_NAME)
    column = vocab_column(
        oid="B3.2", key="date_type", label_en="Date type", vocab_id="date_type"
    )
    assert validate.validate_columns((column,), {"date_type": "geological"}) == []
    issues = validate.validate_columns((column,), {"date_type": "geologic"})
    assert [issue.message_key for issue in issues] == [validate.MSG_VOCAB_UNKNOWN]
    assert issues[0].severity is validate.Severity.ERROR  # date_type 是封闭词表


# ── validate.py：取值键、记录 ID、工作表标注 ─────────────────────────────────


def test_header_key_takes_priority_over_key_and_oid() -> None:
    column = make_field(obligation=Obligation.MANDATORY, value_kind=ValueKind.DECIMAL)
    record = {"SI1 site_name": "18.5", "site_name": "not-a-number", "SI1": "also-bad"}
    assert validate.validate_columns((column,), record) == []


@pytest.mark.parametrize("key", ["site_name", "SI1"])
def test_key_and_oid_fallbacks_are_supported(key) -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    assert validate.validate_columns((column,), {key: "Troia"}) == []


def test_layout_column_spec_is_supported() -> None:
    """块表列（layout.ColumnSpec）与 FieldSpec 走同一套规则。"""
    column = make_column(make_field(obligation=Obligation.MANDATORY))
    assert column.header_key == "SI1 site_name"
    assert validate.validate_columns((column,), {column.header_key: "Troia"}) == []
    issues = validate.validate_columns((column,), {})
    assert [issue.message_key for issue in issues] == [validate.MSG_REQUIRED]


def test_sheet_name_is_annotated_on_every_issue() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    issues = validate.validate_columns((column,), {}, sheet_name="1_Site")
    assert issues[0].params["sheet"] == "1_Site"
    assert issues[0].table == "1_Site"  # table 缺省回落为工作表名


def test_explicit_table_wins_over_sheet_name() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    issues = validate.validate_columns((column,), {}, sheet_name="1_Site", table="sites")
    assert issues[0].table == "sites"
    assert issues[0].params["sheet"] == "1_Site"


def test_record_id_is_derived_from_id_field() -> None:
    id_field = make_field(oid="SI0", key="terralid_site_id", label_en="ID")
    column = make_field(obligation=Obligation.MANDATORY)
    table = make_table(TableKey.SITE, id_field, column)
    issues = validate.validate_record(make_profile(table), "sites", {"terralid_site_id": "S-7"})
    assert [issue.record_id for issue in issues] == ["S-7"]


def test_explicit_record_id_wins() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    table = make_table(TableKey.SITE, column)
    issues = validate.validate_record(make_profile(table), "sites", {}, record_id="row-3")
    assert [issue.record_id for issue in issues] == ["row-3"]


def test_validate_record_with_unknown_table_returns_empty(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.validate")
    assert validate.validate_record(make_profile(), "no-such-table", {}) == []
    assert caplog.records


def test_validate_record_uses_module_fields() -> None:
    column = make_field(obligation=Obligation.MANDATORY)
    table = make_table(TableKey.SITE, column)
    issues = validate.validate_record(make_profile(table), "sites", {})
    assert [issue.table for issue in issues] == ["sites"]


# ── validate.py：条件联动 ────────────────────────────────────────────────────


def test_geological_date_with_cultural_unit_warns() -> None:
    issues = validate.validate_conditionals(
        "objects", {"B3.2 date_type": "geological", "B3.5 date_archaeo_cultural": "Roman"}
    )
    assert [issue.message_key for issue in issues] == [validate.MSG_DATE_KIND_CONFLICT]
    assert issues[0].severity is validate.Severity.WARNING
    assert issues[0].field_oid == "B3.5"


def test_archaeological_date_with_cultural_unit_is_clean() -> None:
    assert validate.validate_conditionals(
        "objects", {"date_type": "archaeological", "date_archaeo_cultural": "Roman"}
    ) == []


def test_archaeological_date_with_orogenesis_warns() -> None:
    issues = validate.validate_conditionals(
        "objects", {"date_type": "archaeological", "date_geol_orogensis": "Variscan"}
    )
    assert [issue.message_key for issue in issues] == [validate.MSG_DATE_KIND_CONFLICT]
    assert issues[0].field_oid == "B3.6"


def test_geological_date_with_orogenesis_is_clean() -> None:
    assert validate.validate_conditionals(
        "objects", {"date_type": "geological", "date_geol_orogensis": "Variscan"}
    ) == []


@pytest.mark.parametrize(
    ("date_type", "unit", "expected_issues"),
    [("geological", "a", 1), ("archaeological", "Ma", 1), ("geological", "Ma", 0), ("archaeological", "a", 0)],
)
def test_date_unit_must_match_date_type(date_type, unit, expected_issues) -> None:
    issues = validate.validate_conditionals(
        "objects", {"date_type": date_type, "date_absolute_unit": unit}
    )
    assert len(issues) == expected_issues
    if expected_issues:
        assert issues[0].message_key == validate.MSG_DATE_UNIT_MISMATCH


def test_unknown_site_requires_project_name() -> None:
    issues = validate.validate_conditionals("sites", {"SI1 site_name": "unknown"})
    assert [issue.message_key for issue in issues] == [validate.MSG_UNKNOWN_SITE_REQUIRES_PROJECT]
    assert issues[0].severity is validate.Severity.ERROR
    assert issues[0].field_oid == "SI2"


def test_unknown_site_with_project_name_is_clean() -> None:
    assert validate.validate_conditionals(
        "sites", {"site_name": "Unknown", "project_name": "Project X"}
    ) == []


def test_known_site_without_project_name_is_clean() -> None:
    assert validate.validate_conditionals("sites", {"site_name": "Troia"}) == []


@pytest.mark.parametrize("material", ["ore", "Ore", " glass ", "coin", "by-product", "pigment", "metal"])
def test_material_without_its_module_warns(material) -> None:
    issues = validate.validate_conditionals(
        "objects", {"O12 object_material": material}, material_tables=frozenset({"objects"})
    )
    assert [issue.message_key for issue in issues] == [validate.MSG_MATERIAL_MODULE_MISSING]
    assert issues[0].params["module"]
    assert issues[0].value.strip().casefold() == material.strip().casefold()


def test_material_with_its_module_is_clean() -> None:
    assert validate.validate_conditionals(
        "objects", {"object_material": "ore"}, material_tables=frozenset({"objects", "ore"})
    ) == []


def test_material_rule_is_skipped_without_context() -> None:
    assert validate.validate_conditionals("objects", {"object_material": "ore"}) == []


def test_unknown_material_value_warns() -> None:
    issues = validate.validate_conditionals(
        "objects", {"object_material": "unobtainium"}, material_tables=frozenset({"objects"})
    )
    assert [issue.message_key for issue in issues] == [validate.MSG_UNKNOWN_MATERIAL]
    assert issues[0].params["material"] == "unobtainium"


def test_conditionals_without_relevant_fields_are_clean() -> None:
    assert validate.validate_conditionals("sites", {"site_name": "Troia"}) == []


# ── validate.py：主外键 ──────────────────────────────────────────────────────


def site_record(site_id: str) -> dict:
    return {"SI0 terralid_site_id": site_id, "SI1 site_name": "Troia"}


def assemblage_record(assemblage_id: str, site_id: str) -> dict:
    return {"AS0 terralid_assemblage_id": assemblage_id, "site_id": site_id}


def object_record(object_id: str, assemblage_id: str = "", site_id: str = "") -> dict:
    record = {"O0 terralid_object_id": object_id}
    if assemblage_id:
        record["assemblage_id"] = assemblage_id
    if site_id:
        record["site_id"] = site_id
    return record


def test_dangling_parent_reference_is_error() -> None:
    records = {
        "sites": [site_record("S1")],
        "assemblages": [assemblage_record("AS1", "S1")],
        "objects": [object_record("O1", "AS-404")],
    }
    issues = validate.validate_references("objects", records)
    assert [issue.message_key for issue in issues] == [validate.MSG_DANGLING_REFERENCE]
    assert issues[0].severity is validate.Severity.ERROR
    assert issues[0].params["value"] == "AS-404"
    assert issues[0].record_id == "O1"


def test_valid_parent_reference_is_clean() -> None:
    records = {
        "assemblages": [assemblage_record("AS1", "S1")],
        "objects": [object_record("O1", "AS1")],
    }
    assert validate.validate_references("objects", records) == []


def test_cross_level_object_attached_to_site_is_accepted() -> None:
    """档案允许 Object 直接用 site_id 挂 Site：父键悬空但 site_id 非空 → 不报错。"""
    records = {
        "sites": [site_record("S1")],
        "assemblages": [assemblage_record("AS1", "S1")],
        "objects": [object_record("O1", "AS-404", "S1")],
    }
    assert validate.validate_references("objects", records) == []


def test_cross_level_rule_does_not_apply_to_samples() -> None:
    """Sample 的层级父键是唯一挂载点，不得借 site_id 豁免。"""
    records = {
        "objects": [object_record("O1")],
        "sites": [site_record("S1")],
        "samples": [{"S0 terralid_sample_id": "SA1", "object_id": "O-404", "site_id": "S1"}],
    }
    issues = validate.validate_references("samples", records)
    assert len(issues) == 1
    assert issues[0].params["parent"] == "Objects"


def test_top_level_table_has_no_reference_rule() -> None:
    assert validate.validate_references("sites", {"sites": [site_record("S1")]}) == []


def test_empty_parent_key_is_not_an_error() -> None:
    records = {"assemblages": [assemblage_record("AS1", "S1")], "objects": [object_record("O1")]}
    assert validate.validate_references("objects", records) == []


def test_absent_parent_table_is_not_checked(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="data.metadata_profile.validate")
    assert validate.validate_references("objects", {"objects": [object_record("O1", "AS-404")]}) == []


def test_unknown_table_key_in_references_warns_and_returns_empty(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.validate")
    assert validate.validate_references("nope", {"nope": [{}]}) == []
    assert caplog.records


def test_material_module_reference_is_checked_against_objects() -> None:
    records = {"objects": [object_record("O1")], "ore": [{"object_id": "O-404"}]}
    issues = validate.validate_references("ore", records)
    assert len(issues) == 1
    assert issues[0].params["field"] == "object_id"


# ── validate.py：工作簿聚合、计数、消息渲染 ──────────────────────────────────


def workbook_profile() -> Profile:
    site_id = make_field(oid="SI0", key="terralid_site_id", label_en="ID")
    site_name = make_field(obligation=Obligation.MANDATORY)
    object_id = make_field(oid="O0", key="terralid_object_id", label_en="ID", table=TableKey.OBJECT)
    material = make_field(
        oid="O12", key="object_material", label_en="Material", table=TableKey.OBJECT,
        obligation=Obligation.MANDATORY, value_kind=ValueKind.CONTROLLED_VOCAB,
        vocab_id="object_material",
    )
    sites = make_table(TableKey.SITE, site_id, site_name)
    objects = make_table(TableKey.OBJECT, object_id, material)
    ore = make_table(
        TableKey.ORE,
        make_field(oid="OO0", key="terralid_ore_id", label_en="ID", table=TableKey.ORE),
    )
    return make_profile(sites, objects, ore)


def test_validate_workbook_aggregates_all_layers(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("ore", "glass")}))
    sheeted = {
        ("sites", "1_Site"): [{"terralid_site_id": "S1", "site_name": "unknown"}],
        ("objects", "3_Object"): [
            {"terralid_object_id": "O1", "object_material": "ore", "assemblage_id": "AS-404"}
        ],
    }
    issues = validate.validate_workbook(workbook_profile(), sheeted)
    keys = [issue.message_key for issue in issues]
    assert validate.MSG_UNKNOWN_SITE_REQUIRES_PROJECT in keys  # 联动（SI1/SI2）
    assert validate.MSG_MATERIAL_MODULE_MISSING in keys  # 联动（O12，没有 Ore 表）
    assert validate.MSG_DANGLING_REFERENCE not in keys  # 父表 assemblages 缺席 → 不判定
    assert all(issue.params.get("sheet") for issue in issues)
    summary = validate.summarize(issues)
    assert summary["error"] == 1
    assert summary["warning"] == 1
    assert summary["records"] == 2


def test_validate_workbook_material_module_present_is_clean(monkeypatch) -> None:
    install_vocab(monkeypatch, fake_vocab({"object_material": ("ore", "glass")}))
    sheeted = {
        ("objects", "3_Object"): [{"terralid_object_id": "O1", "object_material": "ore"}],
        ("ore", "11_Ore"): [{"object_id": "O1"}],
    }
    assert validate.validate_workbook(workbook_profile(), sheeted) == []


def test_summarize_counts_records_after_deduplication() -> None:
    first = validate.ValidationIssue(
        validate.Severity.ERROR, "sites", "S1", "SI1", "site_name", validate.MSG_REQUIRED
    )
    second = validate.ValidationIssue(
        validate.Severity.WARNING, "sites", "S1", "SI2", "project_name", validate.MSG_REQUIRED
    )
    third = validate.ValidationIssue(
        validate.Severity.WARNING, "objects", "", "O1", "object_material", validate.MSG_UNKNOWN_MATERIAL
    )
    assert validate.summarize([first, second, third]) == {"error": 1, "warning": 2, "records": 2}
    assert validate.summarize([]) == {"error": 0, "warning": 0, "records": 0}


def test_format_message_renders_params_and_survives_missing_placeholders(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="data.metadata_profile.validate")
    rendered = validate.ValidationIssue(
        validate.Severity.ERROR, "sites", "S1", "SI1", "site_name", validate.MSG_REQUIRED,
        {"field": "Site name", "oid": "SI1"},
    )
    assert validate.format_message(rendered) == "Required field 'Site name' (SI1) is empty"
    broken = validate.ValidationIssue(
        validate.Severity.ERROR, "sites", "S1", "SI1", "site_name", validate.MSG_REQUIRED, {}
    )
    assert validate.format_message(broken) == validate.MSG_REQUIRED
    assert caplog.records


def test_validation_issue_is_hashable_and_frozen() -> None:
    issue = validate.ValidationIssue(
        validate.Severity.ERROR, "sites", "S1", "SI1", "site_name", validate.MSG_REQUIRED
    )
    assert len({issue, issue}) == 1
    with pytest.raises(Exception):
        issue.table = "objects"  # type: ignore[misc]


def test_message_keys_are_unique_and_have_placeholders() -> None:
    assert len(validate.MESSAGE_KEYS) == len(set(validate.MESSAGE_KEYS))
    for key in validate.MESSAGE_KEYS:
        assert key.strip() == key and key
    exported = {
        value for name, value in vars(validate).items() if name.startswith("MSG_")
    }
    assert exported == set(validate.MESSAGE_KEYS)


def test_material_values_cover_layout_mapping() -> None:
    """validate 使用的 material_table_for 覆盖 layout 的全部材料取值。"""
    from data.metadata_profile.layout import MATERIAL_TABLE_BY_VALUE, material_table_for

    for value, table in MATERIAL_TABLE_BY_VALUE.items():
        assert material_table_for(value) == table


# ── validate_sheets.py：工作表辅助列 ─────────────────────────────────────────


def make_sheet(
    name: str = "1_Site",
    kind: SheetKind = SheetKind.ENTITY,
    *,
    table: str | None = "sites",
    fk_column: str | None = None,
    parent_sheet: str | None = None,
    block: Block | None = None,
    host_oids: tuple[str, ...] = (),
    columns: tuple = (),
    helper_columns: tuple[str, ...] = (),
) -> SheetSpec:
    """构造一个 SheetSpec；只覆盖测试关心的字段。"""
    return SheetSpec(
        name=name,
        title_en=name,
        title_zh=name,
        kind=kind,
        table=table,
        parent_sheet=parent_sheet,
        fk_column=fk_column,
        block=block,
        host_oids=host_oids,
        columns=columns,
        helper_columns=helper_columns,
    )


def site_sheet() -> SheetSpec:
    """顶层实体表（无父外键）。"""
    return make_sheet("1_Site")


def rows_sheet() -> SheetSpec:
    """明细行表：parent_id / group / row_id。"""
    return make_sheet(
        "7_Dating_Rows",
        SheetKind.GROUP,
        fk_column="parent_id",
        parent_sheet="1_Site",
        host_oids=("B3.1", "B3.2"),
        columns=(make_column(make_field(oid="B3.4.1", key="date_relative_period")),),
        helper_columns=("row_id", "parent_id", "group"),
    )


def block_sheet(block: Block | None = None) -> SheetSpec:
    """块表：owner_sheet / owner_id（+ ratio_host）。"""
    helpers = ("owner_sheet", "owner_id", "ratio_host") if block is Block.LIA_RATIO else (
        "owner_sheet",
        "owner_id",
    )
    return make_sheet(
        "6_Person" if block is None else "17_LIA-Ratio",
        SheetKind.BLOCK,
        table=None,
        fk_column="owner_id",
        block=block,
        host_oids=("A14", "A9.3"),
        columns=(make_column(make_field(oid="B1.1", key="person_name")),),
        helper_columns=helpers,
    )


def workbook_layout() -> WorkbookLayout:
    """含主表、明细行表与块表的最小布局。"""
    return WorkbookLayout(
        sheets=(site_sheet(), rows_sheet(), make_sheet("5_Analysis_Rows", SheetKind.GROUP), block_sheet())
    )


def test_entity_parent_fk_is_required_when_row_has_values() -> None:
    sheet = make_sheet("2_Assemblage", fk_column="site_id")
    issues = validate_sheets.validate_sheet_helpers(sheet, {"site_id": "", "AS0 terralid_assemblage_id": "AS1"})
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_REQUIRED]
    assert issues[0].severity is validate.Severity.ERROR
    assert issues[0].table == "2_Assemblage"


def test_entity_parent_fk_is_skipped_for_blank_row() -> None:
    sheet = make_sheet("2_Assemblage", fk_column="site_id")
    assert validate_sheets.validate_sheet_helpers(sheet, {"site_id": ""}) == []


def test_soft_parent_fks_are_only_warnings() -> None:
    for fk_column in ("assemblage_id", "sample_id"):
        sheet = make_sheet("3_Object", fk_column=fk_column)
        issues = validate_sheets.validate_sheet_helpers(sheet, {fk_column: None, "O0 terralid_object_id": "O1"})
        assert [issue.severity for issue in issues] == [validate.Severity.WARNING], fk_column


def test_group_sheet_requires_parent_id_and_group() -> None:
    issues = validate_sheets.validate_sheet_helpers(rows_sheet(), {})
    assert [issue.message_key for issue in issues] == [
        validate_sheets.MSG_HELPER_REQUIRED,
        validate_sheets.MSG_HELPER_REQUIRED,
    ]
    assert [issue.params["column"] for issue in issues] == ["parent_id", "group"]


def test_group_sheet_accepts_valid_row() -> None:
    record = {"row_id": "R1", "parent_id": "S1", "group": "B3.2"}
    assert validate_sheets.validate_sheet_helpers(rows_sheet(), record) == []


def test_group_value_must_be_a_host_oid() -> None:
    record = {"parent_id": "S1", "group": "B3.9"}
    issues = validate_sheets.validate_sheet_helpers(rows_sheet(), record)
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_INVALID_VALUE]
    assert issues[0].params["allowed"] == "B3.1, B3.2"
    assert issues[0].params["value"] == "B3.9"
    assert issues[0].record_id == ""  # 本行没有 row_id


def test_group_record_id_uses_row_id() -> None:
    record = {"row_id": "R7", "parent_id": "", "group": "B3.1"}
    issues = validate_sheets.validate_sheet_helpers(rows_sheet(), record)
    assert issues[0].record_id == "R7"


def test_block_sheet_requires_owner_sheet_and_owner_id() -> None:
    issues = validate_sheets.validate_sheet_helpers(block_sheet(), {"owner_sheet": "", "owner_id": ""})
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_REQUIRED]
    assert issues[0].params["column"] == "owner_sheet"


def test_block_sheet_requires_owner_id_only_when_data_present() -> None:
    sheet = block_sheet()
    empty = validate_sheets.validate_sheet_helpers(sheet, {"owner_sheet": "1_Site"})
    assert empty == []
    filled = validate_sheets.validate_sheet_helpers(
        sheet, {"owner_sheet": "1_Site", "B1.1 person_name": "Doe"}
    )
    assert [issue.params["column"] for issue in filled] == ["owner_id"]


@pytest.mark.parametrize("owner_sheet", ["1_Site", "5_Analysis_Rows"])
def test_block_sheet_accepts_entity_and_rows_hosts(owner_sheet) -> None:
    record = {"owner_sheet": owner_sheet, "owner_id": "X1", "B1.1 person_name": "Doe"}
    assert validate_sheets.validate_sheet_helpers(block_sheet(), record) == []


def test_block_sheet_rejects_unknown_host_sheet() -> None:
    record = {"owner_sheet": "99_Nowhere", "owner_id": "X1", "B1.1 person_name": "Doe"}
    issues = validate_sheets.validate_sheet_helpers(block_sheet(), record)
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_INVALID_VALUE]
    assert issues[0].params["column"] == "owner_sheet"


def test_owner_sheet_candidates_follow_layout_when_given() -> None:
    layout = workbook_layout()
    record = {"owner_sheet": "7_Dating_Rows", "owner_id": "R1", "B1.1 person_name": "Doe"}
    assert validate_sheets.validate_sheet_helpers(block_sheet(), record, layout=layout) == []
    bad = {"owner_sheet": "9_Nonexistent_Rows", "owner_id": "R1", "B1.1 person_name": "Doe"}
    issues = validate_sheets.validate_sheet_helpers(block_sheet(), bad, layout=layout)
    # 给出布局时以布局的工作表集合为准
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_INVALID_VALUE]
    assert "7_Dating_Rows" in issues[0].params["allowed"]


def test_ratio_host_is_validated_on_the_lia_sheet() -> None:
    sheet = block_sheet(Block.LIA_RATIO)
    base = {"owner_sheet": "1_Site", "owner_id": "S1", "B1.1 person_name": "Doe"}
    assert validate_sheets.validate_sheet_helpers(sheet, {**base, "ratio_host": "A14"}) == []
    assert validate_sheets.validate_sheet_helpers(sheet, {**base, "ratio_host": "A9.3"}) == []
    empty = validate_sheets.validate_sheet_helpers(sheet, base)
    assert [issue.params["column"] for issue in empty] == ["ratio_host"]
    invalid = validate_sheets.validate_sheet_helpers(sheet, {**base, "ratio_host": "A15"})
    assert [issue.message_key for issue in invalid] == [validate_sheets.MSG_HELPER_INVALID_VALUE]
    assert invalid[0].params["allowed"] == "A14, A9.3"


def test_ratio_host_rule_also_matches_by_helper_column() -> None:
    """`block` 未标注但辅助列含 ratio_host 时同样适用（判据是列，不是块）。"""
    sheet = make_sheet(
        "17_LIA-Ratio", SheetKind.BLOCK, table=None, fk_column="owner_id", block=None,
        columns=(make_column(make_field(oid="B6.2", key="lia_ratio_value")),),
        helper_columns=("owner_sheet", "owner_id", "ratio_host"),
    )
    record = {"owner_sheet": "1_Site", "owner_id": "X1", "ratio_host": "A15"}
    issues = validate_sheets.validate_sheet_helpers(sheet, record)
    assert [issue.message_key for issue in issues] == [validate_sheets.MSG_HELPER_INVALID_VALUE]


@pytest.mark.parametrize("kind", [SheetKind.README, SheetKind.SCHEMA, SheetKind.VOCAB, SheetKind.CHECK])
def test_information_sheets_have_no_helper_rules(kind) -> None:
    sheet = make_sheet("0_SCHEMA", kind, table=None)
    assert validate_sheets.validate_sheet_helpers(sheet, {}) == []


def test_block_owner_reference_existence_is_out_of_scope() -> None:
    """已知限制：本函数不查 owner_id 指向的记录是否存在（跨表完整性由导入层负责）。"""
    record = {"owner_sheet": "1_Site", "owner_id": "DOES-NOT-EXIST", "B1.1 person_name": "Doe"}
    assert validate_sheets.validate_sheet_helpers(block_sheet(), record) == []


def test_validate_sheets_message_keys_are_registered() -> None:
    assert validate_sheets.MESSAGE_KEYS == (
        validate_sheets.MSG_HELPER_REQUIRED,
        validate_sheets.MSG_HELPER_INVALID_VALUE,
    )


def test_validate_does_not_import_validate_sheets() -> None:
    """依赖必须单向：`validate.py` 不反向 import `validate_sheets`（否则会成环）。"""
    imported: set[str] = set()
    for node in ast.walk(parse_source("data/metadata_profile/validate.py")):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            names = {alias.name for alias in node.names}
            imported.update(name for name in names if name.startswith("validate"))
    assert not {name for name in imported if name.endswith("validate_sheets")}, sorted(imported)


# ── 硬约束守卫 ───────────────────────────────────────────────────────────────

SOURCE_FILES = (
    "data/metadata_profile/ratios.py",
    "data/metadata_profile/validate.py",
    "data/metadata_profile/validate_sheets.py",
)
FORBIDDEN_IMPORTS = {"PyQt5", "pandas", "openpyxl"}


def parse_source(relative_path: str) -> ast.Module:
    """解析项目内的源文件。"""
    return ast.parse((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


@pytest.mark.parametrize("relative_path", SOURCE_FILES)
def test_module_avoids_forbidden_imports(relative_path) -> None:
    imported: set[str] = set()
    for node in ast.walk(parse_source(relative_path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & FORBIDDEN_IMPORTS), sorted(imported & FORBIDDEN_IMPORTS)


@pytest.mark.parametrize("relative_path", SOURCE_FILES)
def test_module_stays_within_line_budget(relative_path) -> None:
    lines = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 800, f"{relative_path} 有 {len(lines)} 行"


@pytest.mark.parametrize("relative_path", SOURCE_FILES)
def test_exception_handlers_are_not_silent(relative_path) -> None:
    """对齐 scripts/check_silent_exceptions.py：处理器不得只有 pass / 仅一条日志。"""
    for node in ast.walk(parse_source(relative_path)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = [item for item in node.body if not (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))]
        assert len(body) >= 2, f"{relative_path}:{node.lineno} 的异常处理器过于安静"
