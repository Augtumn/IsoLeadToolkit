"""`application/use_cases/entry_workbook.py` 的用例层测试：生成 / 校验 / 导入。

工作簿按 `synthetic_layout` 用 openpyxl 手工搭建（本文件自带的 `_build_workbook` 是
`tests/test_metadata_io_xlsx.py` 那份局部 helper 的等价副本 —— 不跨文件引用，避免用例层测试
随 IO 层测试一起改动），用例层的注册表用 `synthetic_profile` 夹具钉住，因此除最后一条真实
档案端到端冒烟外，测试不依赖 `reference/metadata` 的内容与版本。
"""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest
from openpyxl import Workbook

from application.use_cases import entry_workbook
from data.metadata_profile import io_xlsx, spec, validate
from data.metadata_profile.layout import SHEET_CHECK

# 合成注册表里的表头机器键名（读取记录即以它们为键）。
SITE_ID = "SI0 terralid_site_id"
SITE_NAME = "SI1 site_name"
ANALYSIS_ID = "A0 terralid_analysis_id"
ANALYSIS_TYPE = "A2 analysis_lia_type"
ANALYSIS_DATE = "A12 analysis_lia_date"
ANALYSIS_SAMPLE = "sample_id"
A15_TMOD = "A15.2 analysis_lia_age_model_Tmod"
RATIO_NAME = "B6.1 lia_ratio_name"
RATIO_VALUE = "B6.2 lia_ratio_value"
RATIO_SIGMA = "B6.4 lia_ratio_uncertainty_sigma"
RATIO_ABSOLUTE = "B6.5 lia_ratio_uncertainty_value_absolute"
RATIO_RELATIVE = "B6.6 lia_ratio_uncertainty_value_relative"
RATIO_SOURCE = "B6.7 lia_ratio_source"
OWNER_SHEET = "owner_sheet"
OWNER_ID = "owner_id"
RATIO_HOST = "ratio_host"

RATIO_SHEET = "17_LIA-Ratio"
ANALYSIS_SHEET = "5_Analysis"
SITE_SHEET = "1_Site"
ANALYSIS_TYPE_TERM = "bulk solution analysis"

PRIMARY_RATIOS = (
    ("206Pb/204Pb", 18.5),
    ("207Pb/204Pb", 15.6),
    ("208Pb/204Pb", 38.5),
)


# ──────────────────────────────────────────────────────────────────────────────
# 夹具与局部 helper
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def use_case(monkeypatch, synthetic_profile):
    """把用例层的注册表钉在合成档案上（校验/导入都走同一份夹具）。"""
    monkeypatch.setattr(
        entry_workbook, "load_profile", lambda *args, **kwargs: synthetic_profile
    )
    return entry_workbook


@pytest.fixture()
def template(tmp_path, synthetic_layout):
    """按合成布局搭好的空模板。"""
    return _build_workbook(tmp_path / "entry.xlsx", synthetic_layout)


def _build_workbook(path: Path, layout) -> Path:
    """按布局搭一个空模板（双层表头 + `99_CHECK` 单层表头）。"""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_spec in layout.sheets:
        worksheet = workbook.create_sheet(title=sheet_spec.name)
        for column, key in enumerate(sheet_spec.all_header_keys, start=1):
            worksheet.cell(row=1, column=column, value=key)
        for column, label in enumerate(sheet_spec.all_header_labels, start=1):
            worksheet.cell(row=2, column=column, value=label)
        if sheet_spec.name == SHEET_CHECK:
            for column, header in enumerate(io_xlsx.CHECK_HEADERS, start=1):
                worksheet.cell(row=1, column=column, value=header)
    workbook.save(path)
    return path


def _put(layout, path: Path, sheet_name: str, values: dict, row: int = io_xlsx.FIRST_DATA_ROW) -> None:
    """把一行写进某张表（键为表头机器键名）。"""
    workbook = openpyxl.load_workbook(path)
    worksheet = workbook[sheet_name]
    keys = list(layout.sheet(sheet_name).all_header_keys)
    for key, value in values.items():
        worksheet.cell(row=row, column=keys.index(key) + 1, value=value)
    workbook.save(path)


def _rows(layout, path: Path, sheet_name: str) -> list[dict]:
    """读回某张表的数据行。"""
    result = io_xlsx.read_sheets(layout, path, sheets=[sheet_name])
    return list(result[sheet_name].records)


def _put_primary_ratios(layout, path: Path, *, owner_id="A-1", ratio_host="A14", relative_on_first=0.1):
    """写 3 个主比值行；第一行只给相对不确定度（用于验证绝对↔相对换算）。"""
    for index, (name, value) in enumerate(PRIMARY_RATIOS):
        values = {
            OWNER_SHEET: ANALYSIS_SHEET,
            OWNER_ID: owner_id,
            RATIO_HOST: ratio_host,
            RATIO_NAME: name,
            RATIO_VALUE: value,
            RATIO_SIGMA: 2,
        }
        if index == 0 and relative_on_first is not None:
            values[RATIO_RELATIVE] = relative_on_first
        _put(layout, path, RATIO_SHEET, values, row=io_xlsx.FIRST_DATA_ROW + index)


def _put_analysis_row(layout, path: Path, *, record_id="A-1", with_date=True) -> None:
    """写一行"字段齐全"的分析记录（`sample_id` 属 ☆建议，留空只报 WARNING）。"""
    values = {ANALYSIS_ID: record_id, ANALYSIS_TYPE: ANALYSIS_TYPE_TERM}
    if with_date:
        values[ANALYSIS_DATE] = date(2024, 2, 24)
    _put(layout, path, ANALYSIS_SHEET, values)


# ──────────────────────────────────────────────────────────────────────────────
# generate_template
# ──────────────────────────────────────────────────────────────────────────────


def test_generate_template_default_path_and_delegation(tmp_path, monkeypatch, synthetic_profile):
    """缺省路径与脚本 main() 一致，且生成逻辑委托给 build_workbook()。"""
    calls: list[tuple[object, Path]] = []

    def fake_build(profile, target: Path) -> Path:
        calls.append((profile, target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"xlsx")
        return target

    monkeypatch.setattr(entry_workbook, "_load_generator", lambda: (tmp_path / "数据", fake_build))
    monkeypatch.setattr(
        entry_workbook, "load_profile", lambda *args, **kwargs: synthetic_profile
    )

    path = entry_workbook.generate_template()

    assert path.parent == tmp_path / "数据"
    assert path.name == f"entry_template_TerraLID_v{synthetic_profile.version}.xlsx"
    assert calls == [(synthetic_profile, path)]
    assert path.exists()


def test_generate_template_refuses_overwrite_without_force(tmp_path, monkeypatch, synthetic_profile):
    """目标已存在时抛 FileExistsError 且不落盘；force=True 才覆盖。"""
    calls: list[Path] = []

    def fake_build(profile, target: Path) -> Path:
        calls.append(target)
        target.write_bytes(b"new")
        return target

    monkeypatch.setattr(entry_workbook, "_load_generator", lambda: (tmp_path, fake_build))
    monkeypatch.setattr(
        entry_workbook, "load_profile", lambda *args, **kwargs: synthetic_profile
    )
    target = tmp_path / "entry.xlsx"
    target.write_bytes(b"user data")

    with pytest.raises(FileExistsError, match="未覆盖"):
        entry_workbook.generate_template(target)

    assert calls == []
    assert target.read_bytes() == b"user data"

    assert entry_workbook.generate_template(target, force=True) == target
    assert calls == [target]
    assert target.read_bytes() == b"new"


def test_generate_template_reports_missing_generator(tmp_path, monkeypatch):
    """生成器不可用时抛带说明的 RuntimeError（不是裸 ImportError）。"""
    monkeypatch.setitem(sys.modules, "scripts.build_entry_workbook", None)
    monkeypatch.setattr(entry_workbook, "_generator", None)
    monkeypatch.setattr(
        entry_workbook, "load_profile", lambda *args, **kwargs: SimpleNamespace(version="0.0.0")
    )

    with pytest.raises(RuntimeError, match="build_entry_workbook"):
        entry_workbook.generate_template(tmp_path / "entry.xlsx")


# ──────────────────────────────────────────────────────────────────────────────
# validate_entry_workbook
# ──────────────────────────────────────────────────────────────────────────────


def test_validate_empty_template_reports_no_errors(use_case, template, synthetic_layout, synthetic_profile):
    """空模板必须 0 错误（否则用户永远无法通过校验）。"""
    report = use_case.validate_entry_workbook(template)

    assert report.ok is True
    assert report.error_count == 0
    assert report.warning_count == 0
    assert report.issues == ()
    assert report.sheets_read == len(synthetic_layout.entry_sheets)
    assert report.records_read == 0
    assert report.derived_ratios == 0
    assert report.backup is None
    assert report.workbook == template
    assert report.profile_version == synthetic_profile.version


def test_validate_reports_missing_mandatory_field(use_case, template, synthetic_layout):
    """缺必填 → ERROR、ok 为 False，DTO 带齐定位信息与未渲染消息键。"""
    _put(synthetic_layout, template, SITE_SHEET, {SITE_ID: "SI-1"})

    report = use_case.validate_entry_workbook(template)

    assert report.ok is False
    assert report.error_count == 1
    issue = report.issues[0]
    assert issue.severity == "error"
    assert issue.sheet == SITE_SHEET
    assert issue.record_id == "SI-1"
    assert issue.column == SITE_NAME
    assert issue.message_key == validate.MSG_REQUIRED
    assert issue.params["oid"] == "SI1"
    assert issue.value is None
    assert "Required field" in issue.message and "SI1" in issue.message


def test_validate_accepts_blank_system_provided_columns(use_case, template, synthetic_layout):
    """系统提供的列（A15.2 / B6.5 / B6.7）留空不报错，辅助列校验确实被编排进来。"""
    _put(synthetic_layout, template, SITE_SHEET, {SITE_ID: "SI-1", SITE_NAME: "Anyang"})
    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template, relative_on_first=None)

    report = use_case.validate_entry_workbook(template)

    assert report.error_count == 0, [issue.message for issue in report.issues]
    assert report.ok is True
    flagged = {issue.column for issue in report.issues}
    assert not any(column.startswith("A15.2") for column in flagged)
    assert not any(column.startswith("B6.5") for column in flagged)
    assert not any(column.startswith("B6.7") for column in flagged)
    # `sample_id` 是 ☆建议列：空只报 WARNING，且说明辅助列规则已接入用例层。
    assert ANALYSIS_SAMPLE in flagged
    assert report.warning_count >= 1


def test_validate_is_read_only(use_case, template, synthetic_layout):
    """只读校验：文件字节不变，也不生成备份。"""
    _put(synthetic_layout, template, SITE_SHEET, {SITE_ID: "SI-1"})
    before = template.read_bytes()

    report = use_case.validate_entry_workbook(template)

    assert report.error_count == 1
    assert template.read_bytes() == before
    assert not list(template.parent.glob("*.bak-*"))


def test_validate_rejects_missing_and_unreadable_workbooks(use_case, tmp_path):
    """文件不存在抛 FileNotFoundError；非 xlsx 抛 ValueError。"""
    with pytest.raises(FileNotFoundError):
        use_case.validate_entry_workbook(tmp_path / "nope.xlsx")

    bogus = tmp_path / "bogus.xlsx"
    bogus.write_text("not a workbook", encoding="utf-8")
    with pytest.raises(ValueError):
        use_case.validate_entry_workbook(bogus)


# ──────────────────────────────────────────────────────────────────────────────
# import_entry_workbook：比值补齐与不确定度换算
# ──────────────────────────────────────────────────────────────────────────────


def test_import_derives_five_ratios_and_converts_uncertainty(use_case, template, synthetic_layout):
    """3 个主比值 → 补齐到 8 条（5 条 source=calculated），相对不确定度换算成绝对。"""
    _put_primary_ratios(synthetic_layout, template)

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.ok is True
    assert report.error_count == 0
    assert report.derived_ratios == 5
    assert report.backup is not None and report.backup.exists()

    rows = _rows(synthetic_layout, template, RATIO_SHEET)
    assert len(rows) == 8
    by_name = {row[RATIO_NAME]: row for row in rows}
    assert set(by_name) == set(spec.LIA_RATIO_NAMES)

    calculated = {name for name, row in by_name.items() if row[RATIO_SOURCE] == "calculated"}
    assert calculated == set(spec.DERIVED_LIA_RATIO_NAMES)
    assert by_name["207Pb/206Pb"][RATIO_SOURCE] == "calculated"

    # 派生行继承宿主定位（同一组的 owner_sheet / owner_id / ratio_host）。
    derived = by_name["204Pb/206Pb"]
    assert derived[OWNER_SHEET] == ANALYSIS_SHEET
    assert derived[OWNER_ID] == "A-1"
    assert derived[RATIO_HOST] == "A14"

    # 相对不确定度 0.1% → 绝对 18.5 × 0.1 / 100；派生值的一阶传播保留同一相对量。
    measured = by_name["206Pb/204Pb"]
    assert measured[RATIO_SOURCE] == "original"
    assert measured[RATIO_ABSOLUTE] == pytest.approx(0.0185)
    assert measured[RATIO_RELATIVE] == pytest.approx(0.1)
    assert derived[RATIO_ABSOLUTE] == pytest.approx(derived[RATIO_VALUE] * 0.001)
    assert derived[RATIO_RELATIVE] == pytest.approx(0.1)


def test_import_converts_absolute_uncertainty_to_relative(use_case, template, synthetic_layout):
    """反向换算：只给 B6.5 绝对不确定度时补出 B6.6 相对不确定度（%）。"""
    for index, (name, value) in enumerate(PRIMARY_RATIOS):
        _put(
            synthetic_layout,
            template,
            RATIO_SHEET,
            {
                OWNER_SHEET: ANALYSIS_SHEET,
                OWNER_ID: "A-1",
                RATIO_HOST: "A14",
                RATIO_NAME: name,
                RATIO_VALUE: value,
                RATIO_ABSOLUTE: 0.0185,
            },
            row=io_xlsx.FIRST_DATA_ROW + index,
        )

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.derived_ratios == 5
    rows = {row[RATIO_NAME]: row for row in _rows(synthetic_layout, template, RATIO_SHEET)}
    assert rows["206Pb/204Pb"][RATIO_RELATIVE] == pytest.approx(0.1)
    assert rows["206Pb/204Pb"][RATIO_SOURCE] == "original"


def test_import_is_idempotent_and_keeps_workbook_untouched_when_nothing_to_do(
    use_case, template, synthetic_layout
):
    """第二次导入没有可补的比值，既不新增行也不改文件。"""
    _put_primary_ratios(synthetic_layout, template)
    first = use_case.import_entry_workbook(template, write_check=False)
    assert first.derived_ratios == 5
    assert len(_rows(synthetic_layout, template, RATIO_SHEET)) == 8
    snapshot = template.read_bytes()

    second = use_case.import_entry_workbook(template, write_check=False)

    assert second.ok is True
    assert second.derived_ratios == 0
    assert len(_rows(synthetic_layout, template, RATIO_SHEET)) == 8
    assert template.read_bytes() == snapshot


def test_import_without_derive_leaves_data_untouched(use_case, template, synthetic_layout):
    """derive=False 时只校验：不补比值、不写数据行、不生成备份。"""
    _put_primary_ratios(synthetic_layout, template)
    before = template.read_bytes()

    report = use_case.import_entry_workbook(template, derive=False, write_check=False)

    assert report.ok is True
    assert report.derived_ratios == 0
    assert report.backup is None
    assert len(_rows(synthetic_layout, template, RATIO_SHEET)) == 3
    assert template.read_bytes() == before


# ──────────────────────────────────────────────────────────────────────────────
# import_entry_workbook：错误阻断与 99_CHECK
# ──────────────────────────────────────────────────────────────────────────────


def test_import_writes_check_report_and_keeps_data_on_errors(use_case, template, synthetic_layout):
    """有 ERROR 时只写 99_CHECK：数据行不变、备份非空、派生比值不写回。"""
    _put(synthetic_layout, template, SITE_SHEET, {SITE_ID: "SI-1"})  # 缺 SI1 → ERROR
    _put_primary_ratios(synthetic_layout, template)
    before = template.read_bytes()

    report = use_case.import_entry_workbook(template, write_check=True)

    assert report.ok is False
    assert report.error_count == 1
    assert report.derived_ratios == 0
    assert report.backup is not None and report.backup.exists()
    assert report.backup.name.startswith("entry.bak-")

    # 数据行未被改写（比值表仍 3 行，站点行保持原样）。
    assert len(_rows(synthetic_layout, template, RATIO_SHEET)) == 3
    assert _rows(synthetic_layout, template, SITE_SHEET)[0][SITE_NAME] is None
    assert template.read_bytes() != before  # 只是 99_CHECK 变了

    worksheet = openpyxl.load_workbook(template)[SHEET_CHECK]
    rows = [row for row in worksheet.iter_rows(min_row=2, values_only=True) if any(row)]
    assert rows == [
        ("error", SITE_SHEET, "SI-1", SITE_NAME, "Required field 'Site Name' (SI1) is empty", None)
    ]


def test_import_derives_missing_ratios_only_when_clean(
    use_case, template, synthetic_layout
):
    """0 错误时写回；随后再次校验不应出现新问题（不写脏数据）。"""
    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template)
    before = use_case.validate_entry_workbook(template)
    assert before.ok is True

    report = use_case.import_entry_workbook(template)

    assert report.derived_ratios == 5
    after = use_case.validate_entry_workbook(template)
    assert after.error_count == 0
    assert after.warning_count == before.warning_count
    assert after.records_read == before.records_read + 5


# ──────────────────────────────────────────────────────────────────────────────
# import_entry_workbook：A15 年龄模型参数
# ──────────────────────────────────────────────────────────────────────────────


def test_import_writes_age_model_parameters(use_case, template, synthetic_layout, monkeypatch, caplog):
    """A14 主比值齐全时反演 A15.2，并按当前引擎模型写 A15.1；日期列保持日期类型。"""
    from data.geochemistry import engine

    calls: list[tuple[float, float, float]] = []

    def fake_calculate(pb206, pb207, pb208, **kwargs):
        calls.append((pb206, pb207, pb208))
        return {
            "t_Model (Ma)": 250.54,
            "mu_model": 9.86,
            "kappa_model": 3.92,
            "omega": 38.5,
        }

    monkeypatch.setattr("data.geochemistry.calculate_all_parameters", fake_calculate)
    monkeypatch.setattr(engine, "current_model_name", "Stacey & Kramers (2nd Stage)")
    caplog.set_level(logging.INFO, logger=entry_workbook.__name__)

    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template)

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.ok is True and report.derived_ratios == 5
    assert calls == [(18.5, 15.6, 38.5)]

    analysis = _rows(synthetic_layout, template, ANALYSIS_SHEET)[0]
    assert analysis[A15_TMOD] == pytest.approx(250.54)
    assert any("source=calculated" in record.getMessage() for record in caplog.records)

    # 写回时日期还原成 date，而不是把 `YYYY-MM-DD` 写成文本。
    keys = list(synthetic_layout.sheet(ANALYSIS_SHEET).all_header_keys)
    cell = openpyxl.load_workbook(template)[ANALYSIS_SHEET].cell(
        row=io_xlsx.FIRST_DATA_ROW, column=keys.index(ANALYSIS_DATE) + 1
    )
    assert isinstance(cell.value, (date, datetime))
    assert str(cell.value)[:10] == "2024-02-24"


def test_import_skips_age_model_for_reference_material_ratios(
    use_case, template, synthetic_layout, monkeypatch
):
    """`ratio_host=A9.3`（标样实测值）不得用于分析自身的 A15 反演。"""
    from data.geochemistry import engine

    monkeypatch.setattr(engine, "current_model_name", "Stacey & Kramers (2nd Stage)")
    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template, ratio_host="A9.3")
    before = template.read_bytes()

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.derived_ratios == 5  # 比值本身照补
    assert _rows(synthetic_layout, template, ANALYSIS_SHEET)[0][A15_TMOD] is None
    assert template.read_bytes() != before


def test_import_skips_age_model_when_engine_name_is_not_a_terralid_model(
    use_case, template, synthetic_layout, monkeypatch, caplog
):
    """引擎停在档案三个年龄模型之外时，A15 一个都不写（不给参数配错模型名）。"""
    from data.geochemistry import engine

    monkeypatch.setattr(engine, "current_model_name", "V1V2 (Geokit)")
    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template)
    caplog.set_level(logging.WARNING, logger=entry_workbook.__name__)

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.ok is True
    assert _rows(synthetic_layout, template, ANALYSIS_SHEET)[0][A15_TMOD] is None
    assert any("A15 not derived" in record.getMessage() for record in caplog.records)


def test_import_survives_geochemistry_failure(use_case, template, synthetic_layout, monkeypatch, caplog):
    """地球化学引擎抛错只记 warning，导入本身照常完成。"""
    def boom(*args, **kwargs):
        raise RuntimeError("engine unavailable")

    monkeypatch.setattr("data.geochemistry.calculate_all_parameters", boom)
    caplog.set_level(logging.WARNING, logger=entry_workbook.__name__)

    _put_analysis_row(synthetic_layout, template)
    _put_primary_ratios(synthetic_layout, template)

    report = use_case.import_entry_workbook(template, write_check=False)

    assert report.ok is True
    assert report.derived_ratios == 5
    assert _rows(synthetic_layout, template, ANALYSIS_SHEET)[0][A15_TMOD] is None
    assert any(
        "calculate_all_parameters() failed" in record.getMessage() for record in caplog.records
    )


# ──────────────────────────────────────────────────────────────────────────────
# 真实档案端到端（真 profile + 真生成器）
# ──────────────────────────────────────────────────────────────────────────────


def test_real_template_generates_and_validates_clean(tmp_path):
    """真实档案生成的空模板必须 0 错误、26 张录入表可读（端到端口径）。"""
    target = tmp_path / "entry.xlsx"

    path = entry_workbook.generate_template(target)
    report = entry_workbook.validate_entry_workbook(path)

    assert path == target and path.exists()
    assert report.profile_version
    assert report.sheets_read == 26
    assert report.records_read == 0
    assert report.error_count == 0
    assert report.issues == ()


def test_real_workbook_lands_a15_row_without_new_errors(tmp_path, monkeypatch):
    """真实档案端到端：补齐 5 个派生比值、A15 落进 `5_Analysis_Rows` 的 ``group=A15`` 行，
    且随后校验**不新增 ERROR**（明细行表按 ``group`` 筛列，否则 A15 行会被要求填 A9.1）。"""
    from data.geochemistry import engine
    from data.metadata_profile.layout import build_layout
    from data.metadata_profile.profile import load_profile

    monkeypatch.setattr(engine, "current_model_name", "Stacey & Kramers (2nd Stage)")
    layout = build_layout(load_profile())
    path = entry_workbook.generate_template(tmp_path / "entry.xlsx")
    _put(layout, path, ANALYSIS_SHEET, {
        ANALYSIS_ID: "A-1",
        ANALYSIS_TYPE: ANALYSIS_TYPE_TERM,
        "A6.1 analysis_lia_instrument_type": "MC-ICP-MS",
        "A8.1 analysis_lia_pb_intensity_value": 10.5,
        "A8.2 analysis_lia_pb_intensity_unit": "V",
    })
    _put_primary_ratios(layout, path, owner_id="A-1")
    before = entry_workbook.validate_entry_workbook(path)
    assert before.error_count == 0  # sample_id 是 ☆建议列，只报 WARNING

    report = entry_workbook.import_entry_workbook(path, write_check=False)

    assert report.ok is True and report.derived_ratios == 5
    a15_rows = [row for row in _rows(layout, path, "5_Analysis_Rows")
                if row.get("group") == "A15"]
    assert len(a15_rows) == 1
    assert a15_rows[0]["parent_id"] == "A-1"
    assert a15_rows[0]["A15.1 analysis_lia_age_model_name"] == "SK75"
    assert a15_rows[0]["A15.2 analysis_lia_age_model_Tmod"] is not None
    after = entry_workbook.validate_entry_workbook(path)
    assert after.error_count == 0
    assert after.warning_count == before.warning_count


def test_real_rows_sheet_flags_columns_of_another_group(tmp_path):
    """明细行表里填了**别的组**的列 → WARNING（不是 ERROR），且本组必填列仍然照查。"""
    from data.metadata_profile.layout import build_layout
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    path = entry_workbook.generate_template(tmp_path / "entry.xlsx")
    _put(layout, path, "5_Analysis_Rows", {
        "row_id": "R-1", "parent_id": "A-1", "group": "A9",
        "A9.1 analysis_lia_standard-pb_name": "NIST SRM 981",
        "A15.2 analysis_lia_age_model_Tmod": 250.5,  # 属于 A15 组 -> 填错行
    })

    report = entry_workbook.validate_entry_workbook(path)

    strays = [i for i in report.issues if i.message_key == entry_workbook.MSG_STRAY_GROUP_COLUMN]
    assert len(strays) == 1
    assert strays[0].severity == "warning"
    assert strays[0].sheet == "5_Analysis_Rows"
    assert strays[0].record_id == "R-1"
    assert strays[0].column == "A15.2 analysis_lia_age_model_Tmod"
    assert strays[0].value == 250.5
    assert report.error_count == 0
