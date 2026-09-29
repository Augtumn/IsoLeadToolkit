"""`data/metadata_profile/parse.py` + `profile.py` 的解析与组装契约测试。

覆盖三件事：

1. **规模真值**：11 张表、自有字段 247 条、块字段 61 条、逐表字段数与内联块多重集
   （内联展开后共 497 条模块字段）；
2. **语义真值**：A14 必填且 1–n、A14 内联 B6、`B6.1` 枚举全部 8 个比值名、五个
   `TerraLID ID` 必填、`O5.1` 变体写法（``**ID and name**:``）必须解析出来；
3. **硬约束**：不导入 PyQt5 / pandas / openpyxl、模块顶层无副作用、单文件 ≤800 行、
   可选依赖（`vocab` / `labels`）缺席或查询失败时按契约回退。

数据真值取自 `reference/metadata`（TerraLID Metadata Profile v0.3.4）。
"""
from __future__ import annotations

import ast
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest

import data.metadata_profile.profile as profile_mod
from data.metadata_profile.parse import (
    BLOCKS_DOC_RELATIVE,
    CHANGELOG_RELATIVE,
    infer_value_kind,
    parse_block_document,
    parse_table_document,
    read_profile_version,
)
from data.metadata_profile.spec import (
    LIA_RATIO_NAMES,
    PROFILE_VERSION_FALLBACK,
    Block,
    FieldSpec,
    Obligation,
    Occurrence,
    Profile,
    TableKey,
    ValueKind,
)

ARCHIVE_ROOT = profile_mod.DEFAULT_ROOT

#: 逐表**自有**字段数（严格 ``**ID and name:**`` 正则漏掉 `O5.1`，故 objects 是 36 而非 35）。
EXPECTED_OWN_FIELDS: dict[str, int] = {
    "sites": 31,
    "assemblages": 16,
    "objects": 36,
    "samples": 24,
    "analyses": 41,
    "ore": 20,
    "glass": 25,
    "metal": 7,
    "metal-coins": 11,
    "pigment": 36,
    "by-products": 0,
}

#: 自有字段合计。
EXPECTED_OWN_TOTAL = 247

#: `includes/metadata_blocks.md` 的字段定义总数（含 6 个块根）。
EXPECTED_BLOCK_DEFINITIONS = 61

#: 逐表**自有 + 内联块**字段数。
EXPECTED_TABLE_FIELDS: dict[str, int] = {
    "sites": 60,
    "assemblages": 23,
    "objects": 102,
    "samples": 57,
    "analyses": 102,
    "ore": 50,
    "glass": 33,
    "metal": 15,
    "metal-coins": 11,
    "pigment": 44,
    "by-products": 0,
}

#: 逐表内联的块（**按文档顺序**，可能重复）。
EXPECTED_INLINED_BLOCKS: dict[str, tuple[str, ...]] = {
    "sites": ("B3", "B5", "B5"),
    "assemblages": ("B5",),
    "objects": ("B1", "B1", "B4", "B3", "B5", "B2", "B5"),
    "samples": ("B4", "B1", "B2", "B5"),
    "analyses": ("B5", "B5", "B4", "B5", "B6", "B1", "B6", "B5"),
    "ore": ("B3", "B5", "B4"),
    "glass": ("B4",),
    "metal": ("B4",),
    "metal-coins": (),
    "pigment": ("B4",),
    "by-products": (),
}

#: 块 → 成员字段数（不含块根）。
EXPECTED_BLOCK_MEMBERS: dict[str, int] = {
    "B1": 11,
    "B2": 7,
    "B3": 15,
    "B4": 8,
    "B5": 7,
    "B6": 7,
}


@pytest.fixture(scope="module")
def loaded() -> Profile:
    """解析真实档案得到的注册表（不走缓存，避免与其他用例互相影响）。"""
    return profile_mod.build_profile(ARCHIVE_ROOT)


# ──────────────────────────────────────────────────────────────────────────────
# 规模真值
# ──────────────────────────────────────────────────────────────────────────────


def test_load_profile_returns_eleven_tables_in_document_order(loaded: Profile) -> None:
    assert len(loaded.tables) == 11
    assert [table.key for table in loaded.tables] == list(TableKey)
    assert loaded.version == "0.3.4"


@pytest.mark.parametrize("table_key", sorted(EXPECTED_OWN_FIELDS))
def test_own_field_counts_match_archive(loaded: Profile, table_key: str) -> None:
    table = loaded.table(table_key)
    assert table is not None
    assert len(table.own_fields) == EXPECTED_OWN_FIELDS[table_key]


def test_own_fields_total_is_247(loaded: Profile) -> None:
    total = sum(len(table.own_fields) for table in loaded.tables)
    assert total == EXPECTED_OWN_TOTAL


@pytest.mark.parametrize("table_key", sorted(EXPECTED_TABLE_FIELDS))
def test_table_field_counts_include_inlined_blocks(loaded: Profile, table_key: str) -> None:
    table = loaded.table(table_key)
    assert table is not None
    assert len(table.fields) == EXPECTED_TABLE_FIELDS[table_key]


def test_profile_fields_equals_sum_of_table_fields(loaded: Profile) -> None:
    assert len(loaded.fields) == sum(len(table.fields) for table in loaded.tables)
    assert len(loaded.fields) == sum(EXPECTED_TABLE_FIELDS.values())


@pytest.mark.parametrize("table_key", sorted(EXPECTED_INLINED_BLOCKS))
def test_inlined_blocks_follow_document_order(loaded: Profile, table_key: str) -> None:
    table = loaded.table(table_key)
    assert table is not None
    actual = tuple(block.value for block in table.inlined_blocks)
    assert actual == EXPECTED_INLINED_BLOCKS[table_key]


def test_inlined_block_multiset_matches_archive(loaded: Profile) -> None:
    """逐表内联块的多重集必须与档案一致（analyses 内联 relation 四次、lia 两次）。"""
    expected = {
        "analyses": Counter(
            {Block.RELATION: 4, Block.CHEMISTRY: 1, Block.LIA_RATIO: 2, Block.PERSON: 1}
        ),
        "sites": Counter({Block.DATING: 1, Block.RELATION: 2}),
        "objects": Counter(
            {
                Block.PERSON: 2,
                Block.CHEMISTRY: 1,
                Block.DATING: 1,
                Block.RELATION: 2,
                Block.STATUS: 1,
            }
        ),
        "samples": Counter(
            {Block.CHEMISTRY: 1, Block.PERSON: 1, Block.STATUS: 1, Block.RELATION: 1}
        ),
        "assemblages": Counter({Block.RELATION: 1}),
        "ore": Counter({Block.DATING: 1, Block.RELATION: 1, Block.CHEMISTRY: 1}),
        "glass": Counter({Block.CHEMISTRY: 1}),
        "metal": Counter({Block.CHEMISTRY: 1}),
        "pigment": Counter({Block.CHEMISTRY: 1}),
        "metal-coins": Counter(),
        "by-products": Counter(),
    }
    for table_key, counter in expected.items():
        table = loaded.table(table_key)
        assert table is not None
        assert Counter(table.inlined_blocks) == counter, table_key


def test_block_definitions_exclude_roots_and_total_61() -> None:
    document = parse_block_document(ARCHIVE_ROOT / BLOCKS_DOC_RELATIVE)
    assert len(document.fields) == EXPECTED_BLOCK_DEFINITIONS
    assert {block.value for block in document.roots} == set(EXPECTED_BLOCK_MEMBERS)
    assert {block.value: len(members) for block, members in document.members.items()} == (
        EXPECTED_BLOCK_MEMBERS
    )
    for block, members in document.members.items():
        assert all(member.oid != block.value for member in members)
        assert all(member.block is block for member in members)
        assert all(member.block_owner is None for member in members)


def test_profile_blocks_mapping_matches_block_document(loaded: Profile) -> None:
    assert {block.value: len(specs) for block, specs in loaded.blocks.items()} == (
        EXPECTED_BLOCK_MEMBERS
    )
    assert [spec.oid for spec in loaded.fields_owned_by(Block.LIA_RATIO)] == [
        f"B6.{index}" for index in range(1, 8)
    ]


# ──────────────────────────────────────────────────────────────────────────────
# 语义真值
# ──────────────────────────────────────────────────────────────────────────────


def test_a14_is_mandatory_one_to_n_and_inlines_lia_ratio(loaded: Profile) -> None:
    analyses = loaded.table(TableKey.ANALYSIS)
    assert analyses is not None
    a14 = analyses.field("A14")
    assert a14 is not None
    assert a14.is_mandatory
    assert a14.occurrence is Occurrence.ONE_TO_N
    assert a14.label_en == "Lead isotope ratios"

    owned_by_a14 = [spec for spec in analyses.fields if spec.block_owner == "A14"]
    assert {spec.block for spec in owned_by_a14} == {Block.LIA_RATIO}
    assert [spec.oid for spec in owned_by_a14] == [f"B6.{index}" for index in range(1, 8)]


def test_ratio_block_is_inlined_twice_and_keeps_original_oids(loaded: Profile) -> None:
    """块字段身份是 (table, block_owner, oid) 三元组：`B6.2` 在 analyses 里出现两次。"""
    analyses = loaded.table(TableKey.ANALYSIS)
    assert analyses is not None
    copies = [spec for spec in analyses.fields if spec.oid == "B6.2"]
    assert len(copies) == 2
    assert {spec.block_owner for spec in copies} == {"A9.3", "A14"}
    assert all(spec.block is Block.LIA_RATIO for spec in copies)
    assert all(spec.table is TableKey.ANALYSIS for spec in copies)
    assert all(spec.source_doc == BLOCKS_DOC_RELATIVE for spec in copies)

    identity = [(spec.table.value, spec.block_owner, spec.oid) for spec in analyses.fields]
    assert len(identity) == len(set(identity))


def test_relation_block_inlined_four_times(loaded: Profile) -> None:
    analyses = loaded.table(TableKey.ANALYSIS)
    assert analyses is not None
    owners = [spec.block_owner for spec in analyses.fields if spec.oid == "B5.2"]
    assert owners == ["A3.2", "A5.2", "A9.2", "A16"]
    assert len({(owner, "B5.2") for owner in owners}) == 4


def test_b6_1_allowed_values_contain_all_ratio_names(loaded: Profile) -> None:
    spec = loaded.field("B6.1")
    assert spec is not None
    for ratio_name in LIA_RATIO_NAMES:
        assert ratio_name in spec.allowed
    assert spec.value_kind is ValueKind.RATIO_NAME
    assert spec.occurrence is Occurrence.ONE
    assert spec.is_mandatory


@pytest.mark.parametrize("oid", ["A0", "SI0", "O0", "S0", "AS0"])
def test_terralid_id_fields_are_mandatory(loaded: Profile, oid: str) -> None:
    spec = loaded.field(oid)
    assert spec is not None
    assert spec.is_mandatory, oid
    assert spec.key == "terralid_%s_id" % {
        "A0": "analysis",
        "SI0": "site",
        "O0": "object",
        "S0": "sample",
        "AS0": "assemblage",
    }[oid]
    table = loaded.table(spec.table)
    assert table is not None
    assert table.id_field is not None
    assert table.id_field.oid == oid


def test_o5_1_variant_markup_is_parsed(loaded: Profile) -> None:
    """`O5.1` 用 ``**ID and name**:``（冒号在粗体外）写成，必须按宽松规则解析出来。"""
    objects = loaded.table(TableKey.OBJECT)
    assert objects is not None
    o51 = objects.field("O5.1")
    assert o51 is not None
    assert o51.key == "object_pid"
    assert o51.occurrence is Occurrence.ZERO_TO_N
    assert o51.parent == "O5"
    assert o51.value_kind is ValueKind.PID

    for oid in ("O5.1.1", "O5.1.2"):
        child = objects.field(oid)
        assert child is not None
        assert child.parent == "O5.1", oid
    assert not any("父 OID" in warning for warning in loaded.warnings)


def test_coins_prefix_depth_uses_table_prefix(loaded: Profile) -> None:
    """`OM.C` 前缀自带一个点：`OM.C1` 是顶层，不能推出假父 `OM`。"""
    coins = loaded.table(TableKey.COINS)
    assert coins is not None
    first = coins.field("OM.C1")
    assert first is not None
    assert (first.depth, first.parent) == (0, None)
    assert first.key == "material_coin_type_series"  # `(nmo:TypeSeries)` 注解不进 key
    child = coins.field("OM.C7.1")
    assert child is not None
    assert (child.depth, child.parent) == (1, "OM.C7")
    assert coins.id_field is not None and coins.id_field.oid == "OM.C1"


def test_by_products_table_is_empty_but_present(loaded: Profile) -> None:
    by_products = loaded.table(TableKey.BY_PRODUCTS)
    assert by_products is not None
    assert by_products.fields == ()
    assert by_products.inlined_blocks == ()
    assert by_products.id_field is None
    assert any("metadata_by-products.md" in warning for warning in loaded.warnings)


def test_orders_are_sequential_per_table_and_traceable(loaded: Profile) -> None:
    for table in loaded.tables:
        assert [spec.order for spec in table.fields] == list(range(len(table.fields)))
        for own in table.own_fields:
            assert any(own is spec for spec in table.fields)
            assert own.block is None and own.block_owner is None


def test_source_lines_point_into_the_archive(loaded: Profile) -> None:
    a14 = loaded.field("A14")
    assert a14 is not None
    assert a14.source_doc == "docs/metadata_analyses.md"
    assert a14.source_line == 282  # `## Lead isotope ratios` 标题所在行
    copy = next(spec for spec in loaded.table("analyses").fields if spec.block_owner == "A14")
    block_definition = loaded.fields_owned_by(copy.block)[0]
    assert copy.source_line == block_definition.source_line
    assert copy.source_doc == BLOCKS_DOC_RELATIVE


def test_warnings_capture_only_real_anomalies(loaded: Profile) -> None:
    joined = "\n".join(loaded.warnings)
    assert len(loaded.warnings) == 3
    assert "metadata_by-products.md" in joined and "没有任何字段" in joined
    assert "B3.1" in joined and "Definition" in joined
    assert "A16" in joined and "Occurrences" in joined and "0-1" in joined


# ──────────────────────────────────────────────────────────────────────────────
# value_kind 推断
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("allowed", "definition", "expected"),
    [
        ("decimal number", "", ValueKind.DECIMAL),
        ("decimal number, between -180 and 180", "", ValueKind.DECIMAL),
        ("integer", "", ValueKind.INTEGER),
        ("number", "", ValueKind.NUMBER),
        ("date formatted as YYYY-MM-DD", "", ValueKind.DATE),
        ("is valid URL", "", ValueKind.URL),
        ("is valid mail address", "", ValueKind.EMAIL),
        ("file path", "", ValueKind.FILE_PATH),
        ("controlled vocabulary", "", ValueKind.CONTROLLED_VOCAB),
        ("1, 2, 3", "", ValueKind.SIGMA),
        ("original, calculated", "", ValueKind.RATIO_SOURCE),
        ("geological, archaeological", "", ValueKind.GEOL_TYPE),
        ("a, Ma", "", ValueKind.UNIT_AGE),
        ("yes, no, unclear", "", ValueKind.YES_NO_UNCLEAR),
        ("is valid ROR ID", "", ValueKind.PID),
        ("is valid PIDinst", "", ValueKind.PID),
        ("", "Persistent identifier(s) assigned to the person.", ValueKind.PID),
        ("", "The ID of the site in the TerraLID database.", ValueKind.FREE_TEXT),
        ("t.b.d.", "The ID of the sample in the TerraLID database.", ValueKind.FREE_TEXT),
        ("", "", ValueKind.FREE_TEXT),
        # 定义里的举例不得污染判定：allowed=free text 就不能因为定义提到 mail address 变 EMAIL
        ("free text", "may include a mail address or phone number", ValueKind.FREE_TEXT),
        # 单个比值名不构成枚举
        ("206Pb/204Pb", "", ValueKind.FREE_TEXT),
        # 两个互不相干的族 → MIXED（数字族内部不触发）
        ("decimal number, controlled vocabulary", "", ValueKind.MIXED),
    ],
)
def test_infer_value_kind_rules(allowed: str, definition: str, expected: ValueKind) -> None:
    assert infer_value_kind(allowed, definition) is expected


def test_all_ratio_names_in_one_allowed_text_is_ratio_name() -> None:
    allowed = ", ".join(LIA_RATIO_NAMES)
    assert infer_value_kind(allowed) is ValueKind.RATIO_NAME


def test_archive_value_kind_spot_checks(loaded: Profile) -> None:
    expected = {
        "B6.1": ValueKind.RATIO_NAME,
        "B6.2": ValueKind.DECIMAL,
        "B6.4": ValueKind.SIGMA,
        "B6.7": ValueKind.RATIO_SOURCE,
        "B6.5": ValueKind.DECIMAL,
        "B3.2": ValueKind.GEOL_TYPE,
        "B3.3.1": ValueKind.INTEGER,
        "B3.3.4": ValueKind.UNIT_AGE,
        "B1.8": ValueKind.EMAIL,
        "B1.9": ValueKind.URL,
        "B1.4.1": ValueKind.PID,
        "B4.1": ValueKind.CONTROLLED_VOCAB,
        "OO8.1": ValueKind.YES_NO_UNCLEAR,
        "A9.6": ValueKind.NUMBER,
        "A12": ValueKind.DATE,
        "A13": ValueKind.FREE_TEXT,
        "O9": ValueKind.FILE_PATH,
        "OM.C7.1": ValueKind.INTEGER,
    }
    for oid, kind in expected.items():
        spec = loaded.field(oid)
        assert spec is not None, oid
        assert spec.value_kind is kind, oid
    assert ValueKind.MIXED not in {spec.value_kind for spec in loaded.fields}


def test_vocab_registration_promotes_only_vague_value_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """词表登记是"该字段有没有受控词表"的唯一真源：笼统类型提升，精确类型不动。"""
    registered = {
        "A15.1": "age_model_name",  # 档案已穷举 SK75/CR75/AJ84，但没写 controlled vocabulary
        "B6.1": "lia_ratio_name",  # 解析层已给出精确的 RATIO_NAME
        "B6.4": "uncertainty_sigma",  # 精确的 SIGMA
    }

    def _fake_vocab(spec: FieldSpec) -> str | None:
        return registered.get(spec.oid)

    monkeypatch.setattr(profile_mod, "_load_vocab_lookup", lambda: _fake_vocab)
    built = profile_mod.build_profile(ARCHIVE_ROOT)

    promoted = built.field("A15.1")
    assert promoted is not None
    assert promoted.vocab_id == "age_model_name"
    assert promoted.value_kind is ValueKind.CONTROLLED_VOCAB

    precise_ratio = built.field("B6.1")
    assert precise_ratio is not None
    assert precise_ratio.vocab_id == "lia_ratio_name"
    assert precise_ratio.value_kind is ValueKind.RATIO_NAME

    precise_sigma = built.field("B6.4")
    assert precise_sigma is not None
    assert precise_sigma.vocab_id == "uncertainty_sigma"
    assert precise_sigma.value_kind is ValueKind.SIGMA

    # 没有词表登记的自由文本字段不得被规则波及
    unregistered = built.field("A13")
    assert unregistered is not None
    assert unregistered.vocab_id is None
    assert unregistered.value_kind is ValueKind.FREE_TEXT


def test_real_archive_promotes_age_model_name_field() -> None:
    """真实档案：`A15.1` 登记了 `age_model_name`，富化后必须是 CONTROLLED_VOCAB。"""
    if profile_mod._load_vocab_lookup() is None:
        pytest.skip("vocab.py 未落地：提升不适用，回退路径由 test_absent_optional_modules_fall_back 覆盖")
    built = profile_mod.build_profile(ARCHIVE_ROOT)

    age_model = built.field("A15.1")
    assert age_model is not None
    assert age_model.vocab_id == "age_model_name"
    assert age_model.value_kind is ValueKind.CONTROLLED_VOCAB
    assert age_model.allowed.startswith("SK75, CR75, AJ84")

    # 防止规则过度扩张：无词表的自由文本字段保持 FREE_TEXT
    description = built.field("A13")
    assert description is not None
    assert description.vocab_id is None
    assert description.value_kind is ValueKind.FREE_TEXT


# ──────────────────────────────────────────────────────────────────────────────
# 解析规则的合成用例（不依赖档案内容）
# ──────────────────────────────────────────────────────────────────────────────


def test_colon_outside_bold_is_accepted(tmp_path: Path) -> None:
    document = tmp_path / "metadata_sites.md"
    document.write_text(
        "## Field\n"
        "**ID and name**: X2 x_key  \n"
        "**Provided by**: data provider  \n"
        "**Obligation**: mandatory  \n"
        "**Occurrences**: 1–n  \n"
        "**Definition**: definition text  \n",
        encoding="utf-8",
    )
    parsed = parse_table_document(document, TableKey.SITE)
    assert len(parsed.own_fields) == 1
    field = parsed.own_fields[0]
    assert (field.oid, field.key) == ("X2", "x_key")
    assert field.obligation is Obligation.MANDATORY
    assert field.occurrence is Occurrence.ONE_TO_N
    assert field.definition == "definition text"
    assert parsed.warnings == ()


def test_unknown_bold_keys_terminate_the_field_block(tmp_path: Path) -> None:
    document = tmp_path / "metadata_sites.md"
    document.write_text(
        "## Field\n"
        "**ID and name:** X1 x_key  \n"
        "**Provided by:** data provider  \n"
        "**Obligation:** optional  \n"
        "**Occurrences:** 0-1  \n"
        "**Definition:** definition text  \n"
        "**Note**: 这不是档案元信息  \n"
        "**Example:** must not be attached  \n",
        encoding="utf-8",
    )
    parsed = parse_table_document(document, TableKey.SITE)
    assert [field.oid for field in parsed.own_fields] == ["X1"]
    assert parsed.own_fields[0].definition == "definition text"
    assert parsed.own_fields[0].example == ""


def test_heading_without_meta_lines_is_warned_and_skipped(tmp_path: Path) -> None:
    document = tmp_path / "metadata_sites.md"
    document.write_text(
        "## No metadata here\n\nsome prose\n\n## Field\n**ID and name:** X1 x_key\n",
        encoding="utf-8",
    )
    parsed = parse_table_document(document, TableKey.SITE)
    assert [field.oid for field in parsed.own_fields] == ["X1"]
    assert any("ID and name" in warning for warning in parsed.warnings)


def test_missing_parent_is_reported_and_reset(tmp_path: Path) -> None:
    document = tmp_path / "metadata_sites.md"
    document.write_text(
        "## Child\n"
        "**ID and name:** ZZ9.1 child_key\n"
        "**Provided by:** data provider\n"
        "**Obligation:** optional\n"
        "**Occurrences:** 0-1\n"
        "**Definition:** d\n",
        encoding="utf-8",
    )
    parsed = parse_table_document(document, TableKey.SITE)
    assert parsed.own_fields[0].parent is None
    assert parsed.own_fields[0].depth == 1  # ZZ9 不存在，但层级仍由前缀算出
    assert any("父 OID ZZ9" in warning for warning in parsed.warnings)


def test_unknown_occurrence_text_falls_back_with_warning(tmp_path: Path) -> None:
    document = tmp_path / "metadata_sites.md"
    document.write_text(
        "## Field\n"
        "**ID and name:** X1 x_key\n"
        "**Provided by:** data provider\n"
        "**Obligation:** optional\n"
        "**Occurrences:** –n\n"
        "**Definition:** d\n",
        encoding="utf-8",
    )
    parsed = parse_table_document(document, TableKey.SITE)
    assert parsed.own_fields[0].occurrence is Occurrence.ZERO_TO_ONE
    assert any("Occurrences" in warning for warning in parsed.warnings)


def test_read_profile_version_reads_first_version_line(tmp_path: Path) -> None:
    assert read_profile_version(ARCHIVE_ROOT / CHANGELOG_RELATIVE) == "0.3.4"
    changelog = tmp_path / "changelog.md"
    changelog.write_text("## Version 9.9.9\n\n## Version 0.1\n", encoding="utf-8")
    assert read_profile_version(changelog) == "9.9.9"
    assert (
        read_profile_version(tmp_path / "missing.md", fallback="1.2.3") == "1.2.3"
    )
    assert read_profile_version(tmp_path, fallback=PROFILE_VERSION_FALLBACK) == (
        PROFILE_VERSION_FALLBACK
    )


# ──────────────────────────────────────────────────────────────────────────────
# 组装、缓存与错误路径
# ──────────────────────────────────────────────────────────────────────────────


def test_load_profile_caches_by_root_and_refresh_rebuilds(tmp_path: Path) -> None:
    profile_mod.clear_profile_cache()
    try:
        first = profile_mod.load_profile()
        assert profile_mod.load_profile() is first
        rebuilt = profile_mod.load_profile(refresh=True)
        assert rebuilt is not first
        assert rebuilt == first

        copied_root = tmp_path / "metadata"
        shutil.copytree(ARCHIVE_ROOT, copied_root)
        from_copy = profile_mod.load_profile(copied_root)
        assert from_copy is not rebuilt
        assert from_copy.version == rebuilt.version
        assert len(from_copy.fields) == len(rebuilt.fields)
        # 单槽缓存：换回默认 root 会重建，而不是命中拷贝那份
        assert profile_mod.load_profile() is not from_copy
    finally:
        profile_mod.clear_profile_cache()


def test_build_profile_requires_docs_dir_and_block_document(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    with pytest.raises(FileNotFoundError):
        profile_mod.build_profile(root)

    (root / "docs").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        profile_mod.build_profile(root)

    (root / "includes").mkdir()
    (root / "includes" / "metadata_blocks.md").write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        profile_mod.build_profile(root)


def test_empty_archive_warns_instead_of_raising(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    (root / "docs").mkdir(parents=True)
    (root / "includes").mkdir()
    (root / "includes" / "metadata_blocks.md").write_text("", encoding="utf-8")
    for table_key in TableKey:
        (root / "docs" / table_key.doc_name).write_text("", encoding="utf-8")

    built = profile_mod.build_profile(root)
    assert len(built.tables) == 11
    assert all(table.fields == () for table in built.tables)
    assert built.version == PROFILE_VERSION_FALLBACK
    assert any("没有任何字段" in warning for warning in built.warnings)
    assert any("区域标记" in warning for warning in built.warnings)


def test_optional_vocab_and_labels_are_filled_or_fall_back(loaded: Profile) -> None:
    vocab_lookup = profile_mod._load_vocab_lookup()
    label_lookup = profile_mod._load_label_lookup()
    for spec in loaded.fields:
        assert spec.label_zh  # 永远非空：有 labels 就是译文，没有就回退 label_en
        if label_lookup is None:
            assert spec.label_zh == spec.label_en
        if vocab_lookup is None:
            assert spec.vocab_id is None
        else:
            assert spec.vocab_id is None or isinstance(spec.vocab_id, str)


def test_absent_optional_modules_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profile_mod, "_load_vocab_lookup", lambda: None)
    monkeypatch.setattr(profile_mod, "_load_label_lookup", lambda: None)
    built = profile_mod.build_profile(ARCHIVE_ROOT)
    assert len(built.fields) == EXPECTED_OWN_TOTAL + 250
    assert all(spec.vocab_id is None for spec in built.fields)
    assert all(spec.label_zh == spec.label_en for spec in built.fields)
    # 回退路径不得改写解析层的 value_kind：A15.1 仍是 FREE_TEXT，精确类型原样保留
    age_model = built.field("A15.1")
    assert age_model is not None
    assert age_model.value_kind is ValueKind.FREE_TEXT
    ratio_name = built.field("B6.1")
    assert ratio_name is not None
    assert ratio_name.value_kind is ValueKind.RATIO_NAME
    description = built.field("A13")
    assert description is not None
    assert description.value_kind is ValueKind.FREE_TEXT


def test_optional_module_failure_does_not_break_the_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(spec: object) -> str:
        raise RuntimeError("optional module is broken")

    monkeypatch.setattr(profile_mod, "_load_vocab_lookup", lambda: _boom)
    monkeypatch.setattr(profile_mod, "_load_label_lookup", lambda: _boom)
    built = profile_mod.build_profile(ARCHIVE_ROOT)
    assert len(built.tables) == 11
    assert all(spec.vocab_id is None for spec in built.fields)
    assert all(spec.label_zh == spec.label_en for spec in built.fields)


# ──────────────────────────────────────────────────────────────────────────────
# 硬约束（§1.2 / §2 / §4 / §10）
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("module_name", ["parse", "profile"])
def test_module_shape_and_import_discipline(module_name: str) -> None:
    module = __import__(f"data.metadata_profile.{module_name}", fromlist=["__doc__"])
    source_path = Path(module.__file__)
    source = source_path.read_text(encoding="utf-8")

    assert source.startswith('"""'), "文件头必须是模块 docstring"
    assert "logger = logging.getLogger(__name__)" in source
    assert len(source.splitlines()) <= 800
    assert re.findall(
        r"^\s*(?:import|from)\s+(PyQt5|pandas|openpyxl)\b", source, re.MULTILINE
    ) == []
    assert module.__doc__ and module.__doc__.strip()


@pytest.mark.parametrize("module_name", ["parse", "profile"])
def test_module_level_has_no_io_side_effects(module_name: str) -> None:
    module = __import__(f"data.metadata_profile.{module_name}", fromlist=["__doc__"])
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    allowed = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Expr,
    )
    io_calls = {
        "open",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "glob",
        "rglob",
        "iterdir",
        "mkdir",
        "touch",
        "unlink",
        "resolve",
        "exists",
        "is_file",
        "is_dir",
    }
    for node in tree.body:
        assert isinstance(node, allowed), ast.dump(node)[:80]
        if isinstance(node, ast.Expr):
            assert isinstance(node.value, ast.Constant), "模块顶层只允许 docstring 表达式"
        value = getattr(node, "value", None)
        if value is None:
            continue
        for call in ast.walk(value):
            if not isinstance(call, ast.Call):
                continue
            name = call.func.attr if isinstance(call.func, ast.Attribute) else ""
            assert name not in io_calls, f"模块顶层不得调用 {name}()（无 IO 副作用）"
