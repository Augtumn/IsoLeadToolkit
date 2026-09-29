"""`data/metadata_profile/layout.py` 的工作簿布局规则测试。

用 `spec.py` 手工构造的合成注册表（不依赖 markdown 解析），保证布局规则本身可独立验证。
"""
from __future__ import annotations

from data.metadata_profile.layout import (
    BLOCK_SHEET_BY_BLOCK,
    ENTITY_SHEET_BY_TABLE,
    GROUP_COLUMN,
    OWNER_ID_COLUMN,
    OWNER_SHEET_COLUMN,
    RATIO_HOST_COLUMN,
    SHEET_CHECK,
    SHEET_README,
    SHEET_SCHEMA,
    SHEET_VOCAB,
    SheetKind,
    build_layout,
    material_sheet_for,
    owner_sheet_options,
)
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


def _field(
    oid: str,
    key: str,
    *,
    table: TableKey,
    obligation: Obligation = Obligation.RECOMMENDED,
    occurrence: Occurrence = Occurrence.ZERO_TO_ONE,
    provided_by: tuple[ProvidedBy, ...] = (ProvidedBy.DATA_PROVIDER,),
    value_kind: ValueKind = ValueKind.FREE_TEXT,
    vocab_id: str | None = None,
    parent: str | None = None,
    depth: int = 0,
    block: Block | None = None,
    block_owner: str | None = None,
    order: int = 0,
    label_en: str | None = None,
    label_zh: str = "",
) -> FieldSpec:
    """构造一个测试用字段定义。"""
    return FieldSpec(
        oid=oid,
        key=key,
        label_en=label_en or key.replace("_", " ").title(),
        table=table,
        obligation=obligation,
        occurrence=occurrence,
        provided_by=provided_by,
        definition=f"definition of {oid}",
        allowed="",
        example="",
        parent=parent,
        depth=depth,
        block=block,
        block_owner=block_owner,
        value_kind=value_kind,
        vocab_id=vocab_id,
        source_doc=f"docs/metadata_{table.value}.md",
        source_line=1,
        order=order,
        label_zh=label_zh,
    )


def _profile() -> Profile:
    """合成注册表：一张站点表、一张分析表、B6 与 B4 两个块、一个自有可重复组。"""
    site_own = (
        _field(
            "SI0",
            "terralid_site_id",
            table=TableKey.SITE,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            provided_by=(ProvidedBy.SYSTEM,),
            order=0,
        ),
        _field(
            "SI1",
            "site_name",
            table=TableKey.SITE,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE,
            order=1,
        ),
        _field(
            "SI5",
            "geolocation",
            table=TableKey.SITE,
            occurrence=Occurrence.ZERO_TO_ONE,
            order=2,
        ),
        _field(
            "SI5.1",
            "geolocation_point",
            table=TableKey.SITE,
            occurrence=Occurrence.ZERO_TO_N,
            parent="SI5",
            depth=1,
            order=3,
        ),
        _field(
            "SI5.1.1",
            "geolocation_point_longitude",
            table=TableKey.SITE,
            value_kind=ValueKind.DECIMAL,
            parent="SI5.1",
            depth=2,
            order=4,
        ),
        _field(
            "SI5.1.2",
            "geolocation_point_latitude",
            table=TableKey.SITE,
            value_kind=ValueKind.DECIMAL,
            parent="SI5.1",
            depth=2,
            order=5,
        ),
    )
    site_table = TableSpec(
        key=TableKey.SITE,
        own_fields=site_own,
        inlined_blocks=(),
        fields=site_own,
    )

    # B6 块定义（7 个子字段）。Provided by 照抄档案实际取值：
    # B6.1/B6.2 由录入者提供，B6.5 双方提供（系统可由相对值反算），B6.7 由系统提供。
    _LIA_PROVIDERS: dict[int, tuple[ProvidedBy, ...]] = {
        1: (ProvidedBy.DATA_PROVIDER,),
        2: (ProvidedBy.DATA_PROVIDER,),
        3: (ProvidedBy.DATA_PROVIDER,),
        4: (ProvidedBy.DATA_PROVIDER,),
        5: (ProvidedBy.DATA_PROVIDER, ProvidedBy.SYSTEM),
        6: (ProvidedBy.DATA_PROVIDER,),
        7: (ProvidedBy.SYSTEM,),
    }
    lia_block = tuple(
        _field(
            f"B6.{index}",
            f"lia_ratio_{key}",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY if index in (1, 2, 7) else Obligation.RECOMMENDED,
            occurrence=Occurrence.ONE if index in (1, 2, 7) else Occurrence.ZERO_TO_ONE,
            provided_by=_LIA_PROVIDERS[index],
            value_kind=kind,
            order=index,
            block=Block.LIA_RATIO,
            block_owner="A14",
        )
        for index, (key, kind) in enumerate(
            [
                ("name", ValueKind.RATIO_NAME),
                ("value", ValueKind.DECIMAL),
                ("uncertainty_type", ValueKind.CONTROLLED_VOCAB),
                ("uncertainty_sigma", ValueKind.SIGMA),
                ("uncertainty_value_absolute", ValueKind.DECIMAL),
                ("uncertainty_value_relative", ValueKind.DECIMAL),
                ("source", ValueKind.RATIO_SOURCE),
            ],
            start=1,
        )
    )
    # B4 块定义（2 个子字段，仅用于验证 B4 表独立成表）
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
        ),
        _field(
            "A7",
            "analysis_lia_pb_concentration",
            table=TableKey.ANALYSIS,
            order=1,
        ),
        _field(
            "A14",
            "analysis_lia_ratio",
            table=TableKey.ANALYSIS,
            obligation=Obligation.MANDATORY,
            occurrence=Occurrence.ONE_TO_N,
            provided_by=(ProvidedBy.DATA_PROVIDER, ProvidedBy.SYSTEM),
            order=2,
        ),
        _field(
            "A15.2",
            "analysis_lia_age_model_Tmod",
            table=TableKey.ANALYSIS,
            provided_by=(ProvidedBy.SYSTEM,),
            value_kind=ValueKind.DECIMAL,
            parent="A15",
            depth=1,
            order=3,
        ),
    )
    # A7 内联 B4，A14 内联 B6
    analysis_fields = (
        analysis_own[0],
        analysis_own[1],
        *(f for f in chem_block),
        analysis_own[2],
        *(f for f in lia_block),
        analysis_own[3],
    )
    analysis_table = TableSpec(
        key=TableKey.ANALYSIS,
        own_fields=analysis_own,
        inlined_blocks=(Block.CHEMISTRY, Block.LIA_RATIO),
        fields=analysis_fields,
    )

    blocks = {
        Block.LIA_RATIO: lia_block,
        Block.CHEMISTRY: chem_block,
    }
    return Profile(
        version="0.3.4",
        tables=(site_table, analysis_table),
        blocks=blocks,
    )


def test_layout_contains_front_and_back_matter():
    """README / SCHEMA / VOCAB / CHECK 四张信息表必须存在且不要求填写。"""
    layout = build_layout(_profile())
    for name in (SHEET_README, SHEET_SCHEMA, SHEET_VOCAB, SHEET_CHECK):
        sheet = layout.sheet(name)
        assert sheet is not None, name
        assert sheet.is_entry is False, name
    assert SHEET_README not in {s.name for s in layout.entry_sheets}


def test_entity_sheet_column_order_puts_key_then_parent_fk():
    """实体表列序：主键 → 父外键 → 其余字段；分组节点与块字段都不留在实体表。

    - ``A14`` 本身没有标量值（内容全部由 B6 块承载），故不作列 —— 它是 B6 块表的宿主锚点。
    - ``SI5`` 是分组节点（子字段 SI5.1/SI5.2/SI5.4 承载其内容），故不作列。
    """
    layout = build_layout(_profile())
    site = layout.sheet_for_table(TableKey.SITE)
    assert site is not None
    assert site.name == ENTITY_SHEET_BY_TABLE["sites"]
    assert site.columns[0].oid == "SI0"
    assert site.helper_columns == ()  # 顶层模块无父外键
    # SI5（容器）与 SI5.1（可重复组，连同其子字段）都移出实体表
    assert [c.oid for c in site.columns] == ["SI0", "SI1"]

    analysis = layout.sheet_for_table(TableKey.ANALYSIS)
    assert analysis is not None
    assert analysis.helper_columns == ("sample_id",)
    # 本夹具的分析表只有 A0 为标量：A7 与 A14 是块宿主（内容在块表），A15.2 保留
    assert [c.oid for c in analysis.columns] == ["A0", "A15.2"]


def test_repeatable_block_gets_its_own_sheet():
    """可重复块（B4/B6）必须独立成表，且不出现在实体表列里。"""
    layout = build_layout(_profile())
    lia_sheet = layout.sheet_for_block(Block.LIA_RATIO)
    assert lia_sheet is not None
    assert lia_sheet.name == BLOCK_SHEET_BY_BLOCK[Block.LIA_RATIO]
    assert lia_sheet.kind is SheetKind.BLOCK
    assert lia_sheet.fk_column == OWNER_ID_COLUMN
    assert lia_sheet.helper_columns == (
        OWNER_SHEET_COLUMN,
        OWNER_ID_COLUMN,
        RATIO_HOST_COLUMN,
    )
    assert [c.oid for c in lia_sheet.columns] == [
        f"B6.{i}" for i in range(1, 8)
    ]
    assert lia_sheet.host_oids == ("A14",)

    chem_sheet = layout.sheet_for_block(Block.CHEMISTRY)
    assert chem_sheet is not None
    assert chem_sheet.helper_columns == (OWNER_SHEET_COLUMN, OWNER_ID_COLUMN)
    assert [c.oid for c in chem_sheet.columns] == ["B4.1", "B4.3"]
    assert chem_sheet.host_oids == ("A7",)

    analysis = layout.sheet_for_table(TableKey.ANALYSIS)
    assert analysis is not None
    block_oids = {c.oid for c in analysis.columns if c.block is not None}
    assert block_oids == set()


def test_block_sheet_separates_system_provided_columns():
    """系统提供的块字段必须标记出来，避免 Excel 里误标红。"""
    layout = build_layout(_profile())
    lia_sheet = layout.sheet_for_block(Block.LIA_RATIO)
    assert lia_sheet is not None
    source_col = lia_sheet.column("B6.7")
    assert source_col is not None
    assert source_col.is_system_provided is True
    assert source_col.is_required_from_provider is False

    name_col = lia_sheet.column("B6.1")
    assert name_col is not None
    assert name_col.is_system_provided is False
    assert name_col.is_required_from_provider is True


def test_own_repeatable_group_becomes_rows_sheet():
    """模块自有的可重复组合并进一张"明细行"表，宿主为主表。

    一个模块最多两张表（主表 + 明细行表），避免档案里的嵌套重复组把工作簿碎成
    几十张近空表。
    """
    layout = build_layout(_profile())
    group = layout.sheet("1_Site_Rows")
    assert group is not None, layout.sheet_names
    assert group.kind is SheetKind.GROUP
    assert group.parent_sheet == ENTITY_SHEET_BY_TABLE["sites"]
    assert group.fk_column == "parent_id"
    assert group.helper_columns == ("row_id", "parent_id", GROUP_COLUMN)
    # 组成员 = SI5.1 的子字段；SI5.1 自身是分组节点（有子字段）故不建列
    assert [c.oid for c in group.columns] == ["SI5.1.1", "SI5.1.2"]
    assert group.host_oids == ("SI5.1",)
    site = layout.sheet_for_table(TableKey.SITE)
    assert site is not None
    assert "SI5.1.1" not in {c.oid for c in site.columns}


def test_nested_repeatable_groups_collapse_into_one_rows_sheet():
    """嵌套重复组（组里还有可重复组）只产生一张明细行表，且字段不重复。

    档案里确有这种结构：``O5 object_identifiers``（1–n）之下有 ``O5.1 object_pid``
    （0–n）。若把嵌套组也当独立表，O5.1 的字段会出现两次。
    """
    from data.metadata_profile.spec import TableSpec

    outer = _field(
        "X1",
        "outer_group",
        table=TableKey.OBJECT,
        occurrence=Occurrence.ONE_TO_N,
        order=0,
    )
    inner = _field(
        "X1.1",
        "inner_group",
        table=TableKey.OBJECT,
        occurrence=Occurrence.ZERO_TO_N,
        parent="X1",
        depth=1,
        order=1,
    )
    leaf = _field(
        "X1.1.1",
        "inner_leaf",
        table=TableKey.OBJECT,
        parent="X1.1",
        depth=2,
        order=2,
    )
    sibling = _field(
        "X1.2",
        "outer_leaf",
        table=TableKey.OBJECT,
        parent="X1",
        depth=1,
        order=3,
    )
    table = TableSpec(
        key=TableKey.OBJECT,
        own_fields=(outer, inner, leaf, sibling),
        inlined_blocks=(),
        fields=(outer, inner, leaf, sibling),
    )
    layout = build_layout(Profile(version="t", tables=(table,), blocks={}))

    rows = layout.sheet("3_Object_Rows")
    assert rows is not None, layout.sheet_names
    assert rows.host_oids == ("X1",)  # 只认最外层根
    # X1 / X1.1 是分组节点（有子字段），不建列；只保留承值叶子
    oids = [c.oid for c in rows.columns]
    assert oids == ["X1.1.1", "X1.2"]
    assert len(oids) == len(set(oids))
    # 只应存在主表 + 一张明细行表
    assert {s.name for s in layout.entry_sheets} == {"3_Object", "3_Object_Rows"}


def test_header_labels_are_unique_within_each_sheet():
    """同表内表头标签不得重名，否则用户会填错列。

    档案里 ``SI5.1.1`` 与 ``SI5.4.1.1`` 都叫 "Longitude"，重名时必须追加 ``[OID]``。
    """
    layout = build_layout(_profile())
    for sheet in layout.sheets:
        labels = list(sheet.all_header_labels)
        assert len(labels) == len(set(labels)), sheet.name
        assert len(labels) == sheet.column_count


def test_module_has_at_most_two_entry_sheets():
    """每个模块最多两张录入表：主表 + 明细行表。"""
    layout = build_layout(_profile())
    per_table: dict[str, list[str]] = {}
    for sheet in layout.entry_sheets:
        if sheet.kind in (SheetKind.ENTITY, SheetKind.GROUP) and sheet.table:
            per_table.setdefault(sheet.table, []).append(sheet.name)
    for table, names in per_table.items():
        assert len(names) <= 2, (table, names)


def test_ratio_column_number_formats_follow_profile_examples():
    """比值列 5 位小数、不确定度列 8 位小数（对齐档案示例）。"""
    layout = build_layout(_profile())
    lia_sheet = layout.sheet_for_block(Block.LIA_RATIO)
    assert lia_sheet is not None
    assert lia_sheet.column("B6.2").number_format == "0.00000"
    assert lia_sheet.column("B6.5").number_format == "0.00000000"
    assert lia_sheet.column("B6.1").number_format is None


def test_header_rows_are_machine_keys_then_labels():
    """双层表头：第 1 行机器键名，第 2 行中文标签 + 级别标记。"""
    layout = build_layout(_profile())
    lia_sheet = layout.sheet_for_block(Block.LIA_RATIO)
    assert lia_sheet is not None
    keys = lia_sheet.all_header_keys
    labels = lia_sheet.all_header_labels
    assert len(keys) == len(labels) == lia_sheet.column_count
    assert keys[0] == OWNER_SHEET_COLUMN
    assert keys[3] == "B6.1 lia_ratio_name"
    assert "★" in labels[3] or "☆" in labels[3]


def test_owner_sheet_options_cover_records_and_rows():
    """``owner_sheet`` 下拉须含实体表**与**明细行表。

    块表要能挂到主表记录，也要能挂到明细行（如 A9.3 标样实测比值挂到某个 A9 标样行），
    因此两类表都要在候选里。
    """
    layout = build_layout(_profile())
    options = owner_sheet_options(layout)
    assert ENTITY_SHEET_BY_TABLE["sites"] in options
    assert ENTITY_SHEET_BY_TABLE["analyses"] in options
    assert "1_Site_Rows" in options
    # 信息表与块表不得作为宿主
    for excluded in (SHEET_SCHEMA, SHEET_VOCAB, SHEET_CHECK, "17_LIA-Ratio"):
        assert excluded not in options


def test_table_key_for_sheet_drives_validation_routing():
    """表名 → 模块键的映射是导入器分派校验规则的唯一依据。"""
    layout = build_layout(_profile())
    assert layout.table_key_for_sheet("1_Site") == "sites"
    assert layout.table_key_for_sheet("5_Analysis") == "analyses"
    assert layout.table_key_for_sheet(SHEET_SCHEMA) is None


def test_sheet_names_respect_excel_limits():
    """工作表名必须满足 Excel 的 31 字符与非法字符限制。"""
    layout = build_layout(_profile())
    for sheet in layout.sheets:
        assert len(sheet.name) <= 31, sheet.name
        assert not set(sheet.name) & set(r"[]:*?/\\"), sheet.name


def test_material_sheet_lookup_tolerates_case_and_plural():
    """``O12 Material`` 取值 → 材料表名，需容忍大小写/空格/复数。"""
    assert material_sheet_for("ore") == "11_Ore"
    assert material_sheet_for(" Ore ") == "11_Ore"
    assert material_sheet_for("metal") == "13_Metal"
    assert material_sheet_for("coins") == "14_Coins"
    assert material_sheet_for("unknown-material") is None


# ── 真实档案上的结构性回归（专防"字段静默丢失"与"幽灵必填列"两类 bug） ──


def test_real_profile_every_value_bearing_field_has_exactly_one_column():
    """真实档案：每个**承值**字段恰好被一张表的列承载，不多不少。

    这是对两类真实 bug 的回归：

    1. **字段静默丢失** —— 曾经的组根规则要求"可重复且有子字段"，于是可重复的**叶子**
       字段（如 ``SI8 site_type`` 1–n、``OO3.1`` 0–n、``A1`` 0–n）既进不了主表
       （可重复被排除）也成不了组，无处安放（实测 14 个）。
    2. **同一字段出现在两张表** —— 嵌套重复组若各自成根，字段会重复。
    """
    from data.metadata_profile.layout import _container_oids
    from data.metadata_profile.profile import load_profile

    profile = load_profile()
    layout = build_layout(profile)

    homes: dict[str, list[str]] = {}
    for sheet in layout.sheets:
        for column in sheet.columns:
            homes.setdefault(column.oid, []).append(sheet.name)

    homeless: list[str] = []
    duplicated: dict[str, list[str]] = {}
    for table in profile.tables:
        containers = _container_oids(table)
        for spec in table.fields:
            if spec.block is not None or spec.oid in containers:
                continue  # 块字段与分组节点由别处承载
            where = homes.get(spec.oid, [])
            if not where:
                homeless.append(f"{table.key.value}:{spec.oid}")
            elif len(where) > 1:
                duplicated[spec.oid] = where

    assert homeless == [], f"承值字段没有任何列承载: {homeless}"
    assert duplicated == {}, f"字段出现在多张表: {duplicated}"


def test_real_profile_container_fields_are_never_columns():
    """真实档案：分组节点不建列 —— 否则会产生永远填不上却标红的幽灵必填列。

    ``A9`` / ``A15`` / ``SI5`` / ``A6`` 这类字段的内容是子字段（或内联块），自身没有值；
    给它们建列会让 mandatory 规则要求用户填一个无法填写的格子。
    """
    from data.metadata_profile.layout import _container_oids
    from data.metadata_profile.profile import load_profile

    profile = load_profile()
    layout = build_layout(profile)
    all_columns = {c.oid for sheet in layout.sheets for c in sheet.columns}

    leaked: list[str] = []
    for table in profile.tables:
        containers = _container_oids(table)
        source = f"{table.key.value}.md"
        del source
        leaked.extend(oid for oid in containers if oid in all_columns)
    assert leaked == [], f"分组节点被错误地建成了列: {sorted(set(leaked))}"


def test_real_profile_has_no_duplicate_header_labels_anywhere():
    """真实档案生成的全部工作表：表头标签在表内唯一（防同名列填错）。"""
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    for sheet in layout.sheets:
        labels = list(sheet.all_header_labels)
        assert len(labels) == len(set(labels)), sheet.name
        assert len(labels) == sheet.column_count, sheet.name
        assert all(key.strip() for key in sheet.all_header_keys), sheet.name


def test_columns_for_record_filters_by_group():
    """明细行表按 ``group`` 只校验该组适用的列。

    否则 ``group=A15`` 的行会被要求填 A9 组的必填字段（``A9.1`` 标样名），
    产生一批永远无法消除的假错 —— 这正是 A15 无法落行的根因。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    rows = layout.sheet("5_Analysis_Rows")
    assert rows is not None
    # A9（标样）与 A15（年龄模型）是容器组根；A1（实验室编号 0–n）与 A10（校正模型 0–n）
    # 是可重复叶子，各自成为"单列组"
    assert set(rows.host_oids) == {"A1", "A9", "A10", "A15"}

    a15_row = {GROUP_COLUMN: "A15", "A15.1 analysis_lia_age_model_name": "SK75"}
    a15_columns = {c.oid for c in rows.columns_for_record(a15_row)}
    assert a15_columns == {f"A15.{i}" for i in range(1, 10)}
    assert "A9.1" not in a15_columns

    a9_row = {GROUP_COLUMN: "A9", "A9.1 analysis_lia_standard-pb_name": "NIST SRM 981"}
    a9_columns = {c.oid for c in rows.columns_for_record(a9_row)}
    assert a9_columns == {"A9.1", "A9.4", "A9.5", "A9.6"}

    # 未填 group 时**不按组筛列**（group 自身的必填错由 validate_sheets 负责），但"未启用
    # 的可选分组不施必填"这条仍然生效：
    #   · A15 是 0–n（可选）→ 未填时其子列跳过；
    #   · A9  是 1–n（必填容器，档案要求每个分析至少一个 Pb 标准物质）→ 子列**始终**在范围内；
    #   · A1 / A10 是可重复叶子（单列组），没有祖先分组，始终保留。
    empty_columns = {c.oid for c in rows.columns_for_record({})}
    assert empty_columns == {"A1", "A9.1", "A9.4", "A9.5", "A9.6", "A10"}, empty_columns
    # 未知 group 同此
    assert {c.oid for c in rows.columns_for_record({GROUP_COLUMN: "NOPE"})} == empty_columns
    # 但只要填了该组任意一格，该组就被"启用"，其子列重新纳入校验
    touched = rows.columns_for_record({"A9.1 analysis_lia_standard-pb_name": "NIST SRM 981"})
    assert {c.oid for c in touched} >= {"A9.1", "A9.4", "A9.5", "A9.6"}
    # 选定了 group=A15 时，A9 组整组让位（否则 group=A15 的行会被要求填标样名）
    assert {c.oid for c in rows.columns_for_record({GROUP_COLUMN: "A15"})} == {
        f"A15.{i}" for i in range(1, 10)
    }


def test_optional_group_not_required_when_unused():
    """未启用的可选分组，其 mandatory 子字段不得报必填（真实档案，1_Site）。

    档案把 ``SI5.1 Point``、``SI5.2 Boundary box``、``SI6 Registry`` 声明为 ``0–1``，
    组内子字段（经纬度/四至/登记系统名）是 mandatory —— 这个 mandatory 只在**该组被使用时**
    才成立。不区分的话，用户只填"遗址名"就会被 6 条假 ERROR 挡住，误以为必须填满全部字段。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    site = layout.sheet("1_Site")
    assert site is not None

    only_name = {"SI0 terralid_site_id": "SI-1", "SI1 site_name": "Anyang"}
    kept = {c.oid for c in site.columns_for_record(only_name)}
    # 三个**可选**分组（SI5.1 / SI5.2 / SI6）都未启用 → 其子列全部跳过；
    # SI5.3（地理位置描述）保留，因为 SI5 本身是 occurrence=1 的必填容器。
    assert kept == {"SI0", "SI1", "SI2", "SI3", "SI5.3", "SI9"}, kept


def test_optional_group_activated_by_any_descendant():
    """填了可选分组里任意一格，整组就"启用"，其 mandatory 子字段重新纳入校验。"""
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    site = layout.sheet("1_Site")
    assert site is not None

    # 只填了西边界 → SI5.2 组已启用 → 东西南北四边都要校验（缺三边会被报出来）
    partial = {
        "SI0 terralid_site_id": "SI-1",
        "SI1 site_name": "Anyang",
        "SI5.2.1 site_geolocation_box_west": 113.0,
    }
    kept = {c.oid for c in site.columns_for_record(partial)}
    assert {"SI5.2.1", "SI5.2.2", "SI5.2.3", "SI5.2.4"} <= kept
    # 但同级的 SI5.1（Point）仍未被启用
    assert "SI5.1.1" not in kept and "SI5.1.2" not in kept
    # SI6（Registry）同理
    assert "SI6.2" not in kept


def test_mandatory_container_does_not_suppress_its_children():
    """必填容器（``A6`` 仪器，``occurrence = 1``）不得让子字段"自我抑制"。

    档案要求 ``A6.1`` 仪器类型必填。若把 ``A6`` 也当成可选分组，``A6.1`` 会因自己为空而
    "整组未填 → 不要求"，于是永远不被校验 —— 这条用例固化的正是这个回归。
    判据与工作簿里"红底"条件格式的因子一致：只取**最近的可选**分组。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    analysis = layout.sheet("5_Analysis")
    assert analysis is not None
    assert analysis.column("A6.1").optional_ancestors == ()
    assert analysis.column("A8.1").optional_ancestors == ("A8",)

    kept = {
        c.oid
        for c in analysis.columns_for_record({"A2 analysis_lia_type": "U-Pb TIMS"})
    }
    assert "A6.1" in kept, "A6.1 必须仍在校验集合里（档案 mandatory）"
    assert "A8.1" not in kept and "A8.2" not in kept, "A8 组未启用，不应要求"


def test_optional_ancestor_is_the_nearest_optional_group():
    """``optional_ancestors`` 只含可选分组，跳过必填容器 —— 与条件格式因子口径一致。"""
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    ore_rows = layout.sheet("11_Ore_Rows")
    assert ore_rows is not None
    # OO1.1 是 1–n 必填容器，由更外层的可选组 OO1 把门
    assert ore_rows.column("OO1.1.1").optional_ancestors == ("OO1",)
    assert "OO1.1" in ore_rows.column("OO1.1.1").ancestors

    site_rows = layout.sheet("1_Site_Rows")
    assert site_rows is not None
    # SI5.4.1 是 1–n 必填容器，SI5 是 1 必填容器，只有 SI5.4 是可选的
    assert site_rows.column("SI5.4.1.1").optional_ancestors == ("SI5.4",)


def test_block_root_is_not_an_optional_group():
    """块根不算可选分组 —— 块表里存在一行，本身就是"这一组在用"的声明。

    块字段的祖先链首项就是块根（``B6.1`` → ``B6``），而块根不在块自己的字段集合里，会被
    "祖先查不到 ⇒ 按可选处理"命中。若不排除，空着的比值行会因 "B6 组未启用" 把
    ``B6.1``/``B6.2`` 从必填里抹掉（实测影响 49 个块列）—— 而档案要求二者必填。
    块**内部**的嵌套可选组（如人员的 PID ``B1.4``）仍照常计入。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())

    ratio = layout.sheet("17_LIA-Ratio")
    assert ratio is not None
    assert ratio.column("B6.1").optional_ancestors == ()
    assert ratio.column("B6.2").optional_ancestors == ()
    assert "B6" in ratio.column("B6.1").ancestors  # 祖先链仍记录块根
    # 只填了归属列、比值留空的行走在必填范围内
    blank_row = {
        "owner_sheet": "5_Analysis", "owner_id": "A-1", "ratio_host": "A14",
    }
    kept = {c.oid for c in ratio.columns_for_record(blank_row)}
    assert {"B6.1", "B6.2"} <= kept

    person = layout.sheet("6_Person")
    assert person is not None
    assert person.column("B1.1").optional_ancestors == ()  # 块根不算
    assert person.column("B1.4.1").optional_ancestors == ("B1.4",)  # 块内嵌套组算


def test_declared_group_does_not_enable_nested_subgroups():
    """行上声明 ``group=O5`` 只说明 O5 在用，**不向下传递**到嵌套的 ``O5.1`` 子组。

    否则 ``O5.1.1``/``O5.1.2``（PID 值与类型）会被无条件要求 —— 而 ``O5.1`` 是 ``0–n``
    的可选子组。这条是填示例数据时踩出来的真 bug。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    rows = layout.sheet("3_Object_Rows")
    assert rows is not None
    assert rows.column("O5.1.1").optional_ancestors == ("O5.1",)

    declared = {c.oid for c in rows.columns_for_record({GROUP_COLUMN: "O5"})}
    assert "O5.1.1" not in declared and "O5.1.2" not in declared, declared
    assert "O5.3" in declared, "O5 自身的必填项仍应在范围内"

    touched = {
        c.oid
        for c in rows.columns_for_record(
            {
                GROUP_COLUMN: "O5",
                "O5.1.1 object_pid_value": "0000-0001-2345-678X",
            }
        )
    }
    assert {"O5.1.1", "O5.1.2"} <= touched, "真填了 PID 后同组两列都要校验"


def test_container_ancestors_come_from_registry_not_string_truncation():
    """祖先链取自注册表的 parent，不能靠 OID 字符串截断。

    钱币表 ``OM.C7.1`` 截断 OID 会得到并不存在的 ``OM.C``；若把 ``OM.C`` 当成一个
    "没有后代列"的分组，``OM.C7.1``/``OM.C7.2`` 整棵子树会被错误地跳过校验。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    coins = layout.sheet("14_Coins")
    assert coins is not None
    opening = coins.column("OM.C7.1")
    assert opening is not None
    assert "OM.C" not in opening.ancestors, opening.ancestors
    assert opening.ancestors == ("OM.C7",)

    # 未填 OM.C7 时其子列不被要求；填了则两列都纳入
    assert "OM.C7.1" not in {c.oid for c in coins.columns_for_record({})}
    kept = {
        c.oid
        for c in coins.columns_for_record({"OM.C7.1 material_coin_date_from": 100})
    }
    assert {"OM.C7.1", "OM.C7.2"} <= kept


def test_stray_columns_detects_values_from_other_groups():
    """本行填了别的组的列 → 能识别出来（多半是填错行）。"""
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    rows = layout.sheet("5_Analysis_Rows")
    assert rows is not None

    record = {
        GROUP_COLUMN: "A15",
        "A15.1 analysis_lia_age_model_name": "SK75",
        "A9.1 analysis_lia_standard-pb_name": "NIST SRM 981",  # 属于 A9 组
    }
    strays = [c.oid for c in rows.stray_columns_for_record(record)]
    assert strays == ["A9.1"]
    # 干净的行没有游离列
    assert rows.stray_columns_for_record({GROUP_COLUMN: "A15"}) == ()


def test_rows_sheet_gives_repeatable_leaf_fields_a_home():
    """可重复的**叶子**字段（如 SI8 site_type 1–n）必须能落行。

    它们没有子字段，成不了"容器组根"；若不单独成组就会无处安放（实测 14 个）。
    """
    from data.metadata_profile.profile import load_profile

    layout = build_layout(load_profile())
    site_rows = layout.sheet("1_Site_Rows")
    assert site_rows is not None
    assert "SI8" in site_rows.host_oids, site_rows.host_oids
    assert site_rows.column("SI8") is not None
    assert [c.oid for c in site_rows.columns_for_record({GROUP_COLUMN: "SI8"})] == ["SI8"]
