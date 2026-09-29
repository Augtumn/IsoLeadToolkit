"""TerraLID 铅同位素元数据档案的机器可读规格（契约层）。

`reference/metadata` 是 TerraLID Metadata Profile（CC-BY-4.0），其字段定义分散在
`docs/metadata_*.md` 与 `includes/metadata_blocks.md`。本模块只定义**数据结构与常量**，
是包内其余模块共同的契约：

- 解析 markdown → `parse.py` / `profile.py`
- 受控词表与中英标签 → `vocab.py` / `labels.py`
- 校验规则 → `validate.py`
- 比值推导 → `ratios.py`
- 与既有扁平列互转 → `mapping.py`
- xlsx 读写 → `io_xlsx.py`

设计约束：本模块不得导入 PyQt5 / pandas / openpyxl，也不做文件 IO —— 保持纯数据结构，
便于单测与被脚本层复用。

档案的两条核心语义（决定录入 GUI 的形态）：

1. **obligation** 只有三档（mandatory / recommended / optional），且作者刻意压低必填量以
   兼容历史数据；
2. **occurrence** 决定字段是标量还是可重复组 —— `0-1`/`1` 可拍平进父表，`0-n`/`1-n`
   必须走子表（长表）。这是 Excel 工作簿分表的唯一依据。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

#: 档案版本兜底值；实际版本由 parse.py 从 docs/changelog.md 读取。
PROFILE_VERSION_FALLBACK = "0.3.4"

#: 引用来源标识（写入生成物与文档，便于回溯到 reference/metadata）。
PROFILE_SOURCE = "reference/metadata"
PROFILE_LICENSE = "CC-BY-4.0"
PROFILE_DOI = "10.5281/zenodo.18069848"


class Obligation(str, Enum):
    """字段的强制级别。"""

    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"

    @classmethod
    def from_text(cls, text: str) -> "Obligation":
        """把档案里的 obligation 文本归一为枚举值。

        Args:
            text: 形如 ``mandatory`` / ``recommended`` / ``optional`` 的原文。

        Returns:
            对应的枚举值；无法识别时回退到 ``OPTIONAL``（不夸大强制级别）。
        """
        normalized = str(text or "").strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.OPTIONAL

    @property
    def marker(self) -> str:
        """表头级别标记：必填 ★ / 建议 ☆ / 可选 ·。"""
        return {
            Obligation.MANDATORY: "★",
            Obligation.RECOMMENDED: "☆",
            Obligation.OPTIONAL: "·",
        }[self]

    @property
    def label_zh(self) -> str:
        """级别中文名。"""
        return {
            Obligation.MANDATORY: "必填",
            Obligation.RECOMMENDED: "建议",
            Obligation.OPTIONAL: "可选",
        }[self]


class Occurrence(str, Enum):
    """字段在一条记录中允许出现的次数。"""

    ZERO_TO_ONE = "0-1"
    ONE = "1"
    ZERO_TO_N = "0-n"
    ONE_TO_N = "1-n"

    @classmethod
    def from_text(cls, text: str) -> "Occurrence":
        """把档案里的 occurrences 文本归一为枚举值。

        档案使用 en-dash（``0–n``），也容忍 hyphen（``0-n``）与紧写（``0 - n``）。

        Args:
            text: 形如 ``1–n`` / ``0–1`` 的原文。

        Returns:
            对应的枚举值；无法识别时回退到 ``ZERO_TO_ONE``。
        """
        normalized = str(text or "").strip().lower()
        for dash in ("\u2013", "\u2014", "\u2212"):
            normalized = normalized.replace(dash, "-")
        normalized = normalized.replace(" ", "")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.ZERO_TO_ONE

    @property
    def is_repeatable(self) -> bool:
        """是否可重复（需走子表/长表）。"""
        return self in (Occurrence.ZERO_TO_N, Occurrence.ONE_TO_N)

    @property
    def is_required(self) -> bool:
        """是否至少出现一次。"""
        return self in (Occurrence.ONE, Occurrence.ONE_TO_N)


class ProvidedBy(str, Enum):
    """字段由谁产生。"""

    DATA_PROVIDER = "data provider"
    SYSTEM = "TerraLID system"
    API = "API"

    @classmethod
    def parse_list(cls, text: str) -> tuple["ProvidedBy", ...]:
        """解析 ``Provided by`` 原文（可能是逗号分隔的组合）。

        Args:
            text: 例如 ``data provider, TerraLID system`` 或
                ``data provider, API (ORCID ID, ROR ID)``。

        Returns:
            去重后按固定顺序排列的枚举元组；无法识别时回退到
            ``(DATA_PROVIDER,)``。
        """
        lowered = str(text or "").strip().lower()
        found: list[ProvidedBy] = []
        if "terralid system" in lowered:
            found.append(cls.SYSTEM)
        if "api" in lowered:
            found.append(cls.API)
        if "data provider" in lowered or not found:
            found.insert(0, cls.DATA_PROVIDER)
        # 去重且保持顺序
        unique: list[ProvidedBy] = []
        for member in found:
            if member not in unique:
                unique.append(member)
        return tuple(unique)

    @property
    def is_system_provided(self) -> bool:
        """是否由系统（而非录入者）负责填。"""
        return self is ProvidedBy.SYSTEM


class ValueKind(str, Enum):
    """字段的取值类型，决定录入控件与校验方式。"""

    FREE_TEXT = "free_text"
    DECIMAL = "decimal"
    NUMBER = "number"
    INTEGER = "integer"
    DATE = "date"
    CONTROLLED_VOCAB = "controlled_vocab"
    PID = "pid"
    URL = "url"
    EMAIL = "email"
    FILE_PATH = "file_path"
    YES_NO_UNCLEAR = "yes_no_unclear"
    GEOL_TYPE = "geol_type"
    UNIT_AGE = "unit_age"
    SIGMA = "sigma"
    RATIO_NAME = "ratio_name"
    RATIO_SOURCE = "ratio_source"
    MIXED = "mixed"


class Block(str, Enum):
    """可复用块（B1–B6）。`value` 为块号，`include_stem` 为内联标记前缀。"""

    PERSON = "B1"
    STATUS = "B2"
    DATING = "B3"
    CHEMISTRY = "B4"
    RELATION = "B5"
    LIA_RATIO = "B6"

    @property
    def include_stem(self) -> str:
        """`includes/metadata_blocks.md` 中的 include 标记前缀。"""
        return {
            Block.PERSON: "person",
            Block.STATUS: "status",
            Block.DATING: "dating",
            Block.CHEMISTRY: "chemistry",
            Block.RELATION: "relation",
            Block.LIA_RATIO: "lia",
        }[self]

    @property
    def label_zh(self) -> str:
        """块的中文名。"""
        return {
            Block.PERSON: "人员/机构",
            Block.STATUS: "保存与可获取性",
            Block.DATING: "年代",
            Block.CHEMISTRY: "化学组成",
            Block.RELATION: "关联资源",
            Block.LIA_RATIO: "铅同位素比值",
        }[self]


class TableKey(str, Enum):
    """模块（表）标识；`value` 与 `docs/metadata_<value>.md` 的文件名后缀一致。"""

    SITE = "sites"
    ASSEMBLAGE = "assemblages"
    OBJECT = "objects"
    SAMPLE = "samples"
    ANALYSIS = "analyses"
    ORE = "ore"
    GLASS = "glass"
    METAL = "metal"
    COINS = "metal-coins"
    PIGMENT = "pigment"
    BY_PRODUCTS = "by-products"

    @property
    def doc_name(self) -> str:
        """文档文件名。"""
        return f"metadata_{self.value}.md"

    @property
    def oid_prefix(self) -> str:
        """模块内字段 ID 前缀（如 ``A`` / ``SI`` / ``OM.C``）。"""
        return _TABLE_OID_PREFIX[self.value]

    @property
    def label_en(self) -> str:
        """模块英文名（与 mkdocs 导航一致）。"""
        return _TABLE_LABEL_EN[self.value]

    @property
    def label_zh(self) -> str:
        """模块中文名。"""
        return _TABLE_LABEL_ZH[self.value]

    @property
    def parent(self) -> "TableKey | None":
        """层级父模块；``None`` 表示顶层。"""
        parent_value = _TABLE_PARENT.get(self.value)
        return TableKey(parent_value) if parent_value else None

    @property
    def is_material_specific(self) -> bool:
        """是否为材料专属模块（由 ``O12 Material`` 分派）。"""
        return self in (
            TableKey.ORE,
            TableKey.GLASS,
            TableKey.METAL,
            TableKey.COINS,
            TableKey.PIGMENT,
            TableKey.BY_PRODUCTS,
        )


_TABLE_OID_PREFIX: dict[str, str] = {
    "sites": "SI",
    "assemblages": "AS",
    "objects": "O",
    "samples": "S",
    "analyses": "A",
    "ore": "OO",
    "glass": "OG",
    "metal": "OM",
    "metal-coins": "OM.C",
    "pigment": "OP",
    "by-products": "BY",
}

_TABLE_LABEL_EN: dict[str, str] = {
    "sites": "Sites",
    "assemblages": "Assemblages",
    "objects": "Objects",
    "samples": "Samples",
    "analyses": "Analyses",
    "ore": "Ore",
    "glass": "Glass",
    "metal": "Metal",
    "metal-coins": "Metal: Coins",
    "pigment": "Pigments",
    "by-products": "By-products",
}

_TABLE_LABEL_ZH: dict[str, str] = {
    "sites": "遗址/矿区",
    "assemblages": "堆积单位",
    "objects": "器物",
    "samples": "样品",
    "analyses": "分析",
    "ore": "矿石",
    "glass": "玻璃",
    "metal": "金属器",
    "metal-coins": "钱币",
    "pigment": "颜料",
    "by-products": "副产品",
}

#: 层级链路：Site → Assemblage → Object → Sample → Analysis。
#: 档案允许 Object/Analysis 跨级直挂 Site，故父键只作默认建议而非硬约束。
_TABLE_PARENT: dict[str, str | None] = {
    "sites": None,
    "assemblages": "sites",
    "objects": "assemblages",
    "samples": "objects",
    "analyses": "samples",
    "ore": "objects",
    "glass": "objects",
    "metal": "objects",
    "metal-coins": "objects",
    "pigment": "objects",
    "by-products": "objects",
}

#: 层级链路中每张表的父外键列名（材料专属模块统一挂 ``object_id``）。
PARENT_FK_COLUMN: dict[str, str] = {
    "sites": "",
    "assemblages": "site_id",
    "objects": "assemblage_id",
    "samples": "object_id",
    "analyses": "sample_id",
    "ore": "object_id",
    "glass": "object_id",
    "metal": "object_id",
    "metal-coins": "object_id",
    "pigment": "object_id",
    "by-products": "object_id",
}


# ──────────────────────────────────────────────────────────────────────────────
# 铅同位素核心常量（A14 → B6 / A15）
# ──────────────────────────────────────────────────────────────────────────────

#: B6.1 Name 的全部 8 个允许值，顺序与档案一致。
LIA_RATIO_NAMES: tuple[str, ...] = (
    "206Pb/204Pb",
    "207Pb/204Pb",
    "208Pb/204Pb",
    "204Pb/206Pb",
    "207Pb/206Pb",
    "208Pb/206Pb",
    "207Pb/208Pb",
    "206Pb/208Pb",
)

#: 实测的三个主比值（其余 5 个由系统推导）。
PRIMARY_LIA_RATIO_NAMES: tuple[str, ...] = (
    "206Pb/204Pb",
    "207Pb/204Pb",
    "208Pb/204Pb",
)

#: 由主比值推导得到的 5 个比值。
DERIVED_LIA_RATIO_NAMES: tuple[str, ...] = tuple(
    name for name in LIA_RATIO_NAMES if name not in PRIMARY_LIA_RATIO_NAMES
)

#: 比值名 → (分子质量数, 分母质量数)，用于从主比值代数推导。
LIA_RATIO_MASSES: dict[str, tuple[int, int]] = {
    "206Pb/204Pb": (206, 204),
    "207Pb/204Pb": (207, 204),
    "208Pb/204Pb": (208, 204),
    "204Pb/206Pb": (204, 206),
    "207Pb/206Pb": (207, 206),
    "208Pb/206Pb": (208, 206),
    "207Pb/208Pb": (207, 208),
    "206Pb/208Pb": (206, 208),
}

#: 推导所需的分母参考质量数（204 作公共基准）。
_RATIO_BASE_MASS = 204

#: B6.7 Source 允许值。
RATIO_SOURCES: tuple[str, ...] = ("original", "calculated")

#: A15.1 Age model name 允许值，对应 Stacey & Kramers (1975) / Cumming &
#: Richards (1975) / Albarède & Juteau (1984)；三者在
#: ``data/geochemistry/engine.py::PRESET_MODELS`` 中均有实现。
AGE_MODEL_NAMES: tuple[str, ...] = ("SK75", "CR75", "AJ84")

#: A15 的 9 个子字段：模型名 + 4 个参数各带不确定度。
AGE_MODEL_PARAMETERS: tuple[str, ...] = ("Tmod", "mu", "kappa", "omega")

#: B4.6 / B6.4 Confidence level 允许值。
SIGMA_LEVELS: tuple[int, ...] = (1, 2, 3)

#: B3.2 Date type 允许值（控制 B3.5 / B3.6 的可用性）。
DATE_TYPES: tuple[str, ...] = ("geological", "archaeological")

#: B3.3.4 Unit of date 允许值，由 B3.2 派生。
DATE_UNITS: tuple[str, ...] = ("a", "Ma")

#: OO8.1 Accessibility 允许值（`unclear` 为 v0.3.4 新增）。
YES_NO_UNCLEAR: tuple[str, ...] = ("yes", "no", "unclear")


# ──────────────────────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FieldSpec:
    """档案中的一个字段定义。

    一个 ``FieldSpec`` 对应档案里的一个 ``**ID and name:**`` 条目，无论它写在
    模块文档里还是可复用块里。块字段被某模块内联时，``block_owner`` 记录宿主字段
    （例如 A14 内联 B6，则 B6.* 的 ``block_owner`` 为 ``"A14"``）。
    """

    #: 档案字段 ID，如 ``"A14"`` / ``"B6.2"`` / ``"OM.C7.1"``。
    oid: str
    #: 机器可读键名（``**ID and name:**`` 的第二个 token）。
    key: str
    #: 档案英文标签（markdown 标题）。
    label_en: str
    #: 字段所属模块。
    table: TableKey
    #: 强制级别。
    obligation: Obligation
    #: 允许出现次数。
    occurrence: Occurrence
    #: 产生方（可多方）。
    provided_by: tuple[ProvidedBy, ...]
    #: 档案原文定义。
    definition: str
    #: ``Allowed values and other constraints`` 原文（可能为空）。
    allowed: str
    #: 档案示例（可能为空或 ``t.b.d.``）。
    example: str
    #: 父字段 OID（``A9.3.1`` 的父为 ``A9.3``）；顶层字段为 ``None``。
    parent: str | None
    #: 层级深度，顶层为 0。
    depth: int
    #: 该字段所属的可复用块；模块自有字段为 ``None``。
    block: Block | None
    #: 内联该块的宿主字段 OID；模块自有字段为 ``None``。
    block_owner: str | None
    #: 取值类型，决定控件与校验。
    value_kind: ValueKind
    #: 受控词表 ID（``vocab.py`` 中的键）；自由文本为 ``None``。
    vocab_id: str | None
    #: 源文档相对路径。
    source_doc: str
    #: 源文档行号（1 起）。
    source_line: int
    #: 在所属模块内的出现序（0 起），用于稳定排序。
    order: int
    #: 中文标签；由 ``labels.py`` 填充，缺省回落到 ``label_en``。
    label_zh: str = ""

    @property
    def is_mandatory(self) -> bool:
        """是否必填。"""
        return self.obligation is Obligation.MANDATORY

    @property
    def is_repeatable(self) -> bool:
        """是否可重复（需子表承载）。"""
        return self.occurrence.is_repeatable

    @property
    def is_system_provided(self) -> bool:
        """是否由系统产生（录入者可留空，由工具补齐）。"""
        return any(p.is_system_provided for p in self.provided_by)

    @property
    def is_data_provider_provided(self) -> bool:
        """是否需要录入者填写。"""
        return ProvidedBy.DATA_PROVIDER in self.provided_by

    @property
    def is_required_from_provider(self) -> bool:
        """必填**且**须由录入者提供 —— 只有这种字段会标红/报必填错。

        系统提供的字段（如 B6.7 Source、A15.* 年龄模型参数）留空不算错，因为工具会补齐。
        """
        return self.is_mandatory and self.is_data_provider_provided

    @property
    def qualified_key(self) -> str:
        """``ID 键名`` 组合，用作列标识与校验报告定位。"""
        return f"{self.oid} {self.key}"

    @property
    def display_label(self) -> str:
        """表头显示文本：``中文标签 ★必填``。"""
        return f"{self.label_zh or self.label_en} {self.obligation.marker}"

    @property
    def has_allowed_values(self) -> bool:
        """是否存在受控取值约束。"""
        return bool(self.allowed.strip())


@dataclass(frozen=True)
class TableSpec:
    """一个模块（表）及其字段集合。"""

    key: TableKey
    #: 模块自有字段（不含内联块）。
    own_fields: tuple[FieldSpec, ...]
    #: 按出现顺序记录内联的块（可能重复，如 Analyses 内联 relation 四次）。
    inlined_blocks: tuple[Block, ...]
    #: 模块自有 + 全部内联字段，按文档出现顺序。
    fields: tuple[FieldSpec, ...]

    @property
    def label_en(self) -> str:
        """模块英文名。"""
        return self.key.label_en

    @property
    def label_zh(self) -> str:
        """模块中文名。"""
        return self.key.label_zh

    @property
    def oid_prefix(self) -> str:
        """字段 ID 前缀。"""
        return self.key.oid_prefix

    @property
    def parent(self) -> TableKey | None:
        """层级父模块；``None`` 表示顶层。"""
        return self.key.parent

    @property
    def parent_fk_column(self) -> str:
        """父外键列名；顶层模块为空串。"""
        return PARENT_FK_COLUMN[self.key.value]

    @property
    def id_field(self) -> FieldSpec | None:
        """主键字段（编号为 ``<prefix>0`` 的那条）。"""
        primary_oid = f"{self.oid_prefix}0"
        for spec in self.own_fields:
            if spec.oid == primary_oid:
                return spec
        return self.own_fields[0] if self.own_fields else None

    @property
    def scalar_fields(self) -> tuple[FieldSpec, ...]:
        """可拍平进父表的字段（不可重复）。"""
        return tuple(f for f in self.fields if not f.is_repeatable)

    @property
    def repeatable_fields(self) -> tuple[FieldSpec, ...]:
        """必须走子表的字段。"""
        return tuple(f for f in self.fields if f.is_repeatable)

    @property
    def mandatory_fields(self) -> tuple[FieldSpec, ...]:
        """必填字段。"""
        return tuple(f for f in self.fields if f.is_mandatory)

    def field(self, oid: str) -> FieldSpec | None:
        """按 OID 取字段。"""
        for spec in self.fields:
            if spec.oid == oid:
                return spec
        return None


@dataclass(frozen=True)
class Profile:
    """整份档案的注册表。"""

    version: str
    tables: tuple[TableSpec, ...]
    #: 可复用块自身作为“伪表”的字段（B1–B6），键为块。
    blocks: Mapping[Block, tuple[FieldSpec, ...]] = field(default_factory=dict)
    #: 解析过程中的告警（缺字段、无法识别的允许值等），供生成物与测试核对。
    warnings: tuple[str, ...] = ()

    @property
    def fields(self) -> tuple[FieldSpec, ...]:
        """全部模块字段（不含块定义自身，避免重复计数）。"""
        collected: list[FieldSpec] = []
        for table in self.tables:
            collected.extend(table.fields)
        return tuple(collected)

    def table(self, key: TableKey | str) -> TableSpec | None:
        """按模块键取表。"""
        target = key.value if isinstance(key, TableKey) else str(key)
        for table in self.tables:
            if table.key.value == target:
                return table
        return None

    def field(self, oid: str) -> FieldSpec | None:
        """按 OID 在全部模块中取字段（先自有后块）。"""
        for table in self.tables:
            found = table.field(oid)
            if found is not None:
                return found
        for specs in self.blocks.values():
            for spec in specs:
                if spec.oid == oid:
                    return spec
        return None

    def fields_owned_by(self, block: Block) -> tuple[FieldSpec, ...]:
        """块定义自身的字段（B1–B6 的原始定义）。"""
        return tuple(self.blocks.get(block, ()))

    def mandatory_fields(self, table: TableKey | str) -> tuple[FieldSpec, ...]:
        """某模块的必填字段。"""
        found = self.table(table)
        return found.mandatory_fields if found is not None else ()

    def all_oids(self) -> frozenset[str]:
        """全部已知 OID 集合（含块定义），用于外键/引用校验。"""
        known = {spec.oid for spec in self.fields}
        for specs in self.blocks.values():
            known.update(spec.oid for spec in specs)
        return frozenset(known)


def derived_ratio_expression(ratio_name: str) -> tuple[tuple[int, int], ...]:
    """给出由主比值推导 *ratio_name* 所需的运算链。

    比值被表达为质量数之比 ``N_a/N_b``。三个实测主比值提供 ``N_206/N_204``、
    ``N_207/N_204``、``N_208/N_204``，于是任意 ``N_a/N_b`` 都可写成
    ``(N_a/N_204) / (N_b/N_204)``；当某一侧就是 204 时退化为直接取值或取倒数。

    Args:
        ratio_name: ``LIA_RATIO_NAMES`` 中的比值名。

    Returns:
        按顺序需要相乘/相除的因子列表，每项为 ``(质量数, 指数)``，语义为
        ``∏ (N_mass / N_204) ** exponent``；指数取 ``+1`` / ``-1``。

    Raises:
        KeyError: ``ratio_name`` 不在 ``LIA_RATIO_MASSES`` 中。
    """
    numerator, denominator = LIA_RATIO_MASSES[ratio_name]
    factors: list[tuple[int, int]] = []
    if numerator != _RATIO_BASE_MASS:
        factors.append((numerator, 1))
    if denominator != _RATIO_BASE_MASS:
        factors.append((denominator, -1))
    return tuple(factors)


def primary_ratio_for_mass(mass: int) -> str | None:
    """返回某质量数相对 204 的主比值名（``206`` → ``206Pb/204Pb``）。

    Args:
        mass: 质量数，如 206 / 207 / 208。

    Returns:
        对应的主比值名；``mass`` 为 204 或不在主比值中时返回 ``None``。
    """
    if mass == _RATIO_BASE_MASS:
        return None
    candidate = f"{mass}Pb/{_RATIO_BASE_MASS}Pb"
    return candidate if candidate in PRIMARY_LIA_RATIO_NAMES else None


def iter_table_keys() -> Iterable[TableKey]:
    """按文档顺序迭代全部模块键。"""
    return tuple(TableKey)


__all__ = [
    # 常量
    "AGE_MODEL_NAMES",
    "AGE_MODEL_PARAMETERS",
    "DATE_TYPES",
    "DATE_UNITS",
    "DERIVED_LIA_RATIO_NAMES",
    "LIA_RATIO_MASSES",
    "LIA_RATIO_NAMES",
    "PARENT_FK_COLUMN",
    "PRIMARY_LIA_RATIO_NAMES",
    "PROFILE_DOI",
    "PROFILE_LICENSE",
    "PROFILE_SOURCE",
    "PROFILE_VERSION_FALLBACK",
    "RATIO_SOURCES",
    "SIGMA_LEVELS",
    "YES_NO_UNCLEAR",
    # 枚举
    "Block",
    "Obligation",
    "Occurrence",
    "ProvidedBy",
    "TableKey",
    "ValueKind",
    # 数据结构
    "FieldSpec",
    "Profile",
    "TableSpec",
    # 工具
    "derived_ratio_expression",
    "iter_table_keys",
    "primary_ratio_for_mass",
]
