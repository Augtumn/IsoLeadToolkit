"""受控词表（`vocab.py`）与中文字段标签（`labels.py`）的验收测试。

覆盖三类断言：

1. **覆盖率**：`FIELD_LABELS_ZH` 必须覆盖 `includes/metadata_blocks.md` 的全部 61 个块
   OID，并对 11 个模块文档各达到 ≥90%（实测 100%）；同时统计模块自有字段总数为 246。
2. **词表完备性**：档案里凡标注 ``controlled vocabulary`` 的 OID 都必须在 `vocab.py` 里
   有词表；未标该短语但档案已穷举允许值的 8 个 OID（A15.1 / B3.2 / B3.3.4 / B4.6 /
   B6.1 / B6.4 / B6.7 / OO8.1）也必须登记，且取 ``open_ended=False``。
3. **契约细节**：`vocab_id_for()` 只按 OID 命中（不读 `spec.vocab_id`）、`open_ended()`
   对未知 id 返回 True、`contains()` 的比较规则、`label_for()` 的回退链与非空性，以及
   `vocab.py` / `labels.py` 保持纯数据 + 纯函数（无第三方依赖、无文件 IO）。

测试自身会直接读 `reference/metadata/*.md` 提取 OID —— 这是刻意的：验收基线必须来自档案
原文而不是被测模块的常量，否则词表与档案脱节时测试仍会通过。此处的解析只提取
``**ID and name:**`` 与标题行，不复制 `parse.py` 的字段语义。
"""

from __future__ import annotations

import ast
import re
from dataclasses import FrozenInstanceError
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pytest

from data.metadata_profile.labels import EN_LABELS_ZH, FIELD_LABELS_ZH, label_for
from data.metadata_profile.spec import (
    AGE_MODEL_NAMES,
    DATE_TYPES,
    DATE_UNITS,
    LIA_RATIO_NAMES,
    RATIO_SOURCES,
    SIGMA_LEVELS,
    YES_NO_UNCLEAR,
    FieldSpec,
    Obligation,
    Occurrence,
    ProvidedBy,
    TableKey,
    ValueKind,
)
from data.metadata_profile.vocab import (
    VOCABULARIES,
    Vocabulary,
    contains,
    open_ended,
    terms,
    vocab_id_for,
    vocabulary,
)

# ── 验收基线（来自 task-2 描述与档案原文）──────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_METADATA_ROOT = _PROJECT_ROOT / "reference" / "metadata"
_BLOCKS_DOC = _METADATA_ROOT / "includes" / "metadata_blocks.md"
_MODULE_DOCS: tuple[Path, ...] = tuple(
    sorted((_METADATA_ROOT / "docs").glob("metadata_*.md"))
)

#: 档案模块自有字段（不含内联块）总数，见 docs/development_plan.md 与 TerraLID v0.3.4。
_MODULE_OWN_FIELD_TOTAL = 246
#: `includes/metadata_blocks.md` 的块字段总数。
_BLOCK_FIELD_TOTAL = 61
#: 模块文档允许的最低标签覆盖率。
_MIN_MODULE_COVERAGE = 0.90

#: task-2 要求覆盖的 OID（含档案未标 controlled vocabulary 但语义上需要词表的字段）。
_TASK_REQUIRED_OIDS: tuple[str, ...] = (
    "A2", "A6.1", "A6.2", "A8.2", "A9.1", "A9.4", "A10",
    "B3.2", "B3.3.3", "B3.3.4", "B3.4.1", "B3.4.2", "B3.6",
    "B4.1", "B4.2", "B4.4", "B4.5", "B4.6",
    "B5.1.2", "B5.3", "B5.4",
    "B6.1", "B6.3", "B6.4", "B6.7",
    "B1.1", "B1.4.2", "B2.2",
    "O5.1.2", "O7", "O8.1", "O8.2", "O10.2", "O11.4", "O12", "O18.1",
    "S3", "S5", "S6.2", "S7", "S8", "S1.2.2",
    "SI4.2", "SI8", "SI10",
    "AS1", "AS2", "AS4.3", "AS5.3",
    "OO1.2", "OO2.1", "OO3.1", "OO4.2", "OO5", "OO6", "OO8.1", "OO8.2",
    "OG1", "OG2.1", "OG4", "OG5", "OG6", "OG7", "OG8", "OG13.1",
    "OM1.2", "OM2.1",
    "OM.C1", "OM.C3", "OM.C4", "OM.C5", "OM.C6", "OM.C8", "OM.C9",
    "OP1", "OP3.1", "OP3.2", "OP5.1", "OP5.2", "OP6.2", "OP7.1", "OP8.1", "OP9",
)

#: task-2 列出但**确实没有**受控词表的字段（自由文本 / 日期块），逐条给出理由。
_DOCUMENTED_WITHOUT_VOCAB: dict[str, str] = {
    "OO8.2": "档案 Allowed values 为 free text（可获取性说明），无候选值可枚举",
    "SI10": "SI10 project_date 是日期块，子字段 SI10.1/SI10.2 为 YYYY-MM-DD 日期，无词表",
}

#: 未标 ``controlled vocabulary`` 短语、但档案在 Allowed values 里已穷举允许值的 OID。
_ARCHIVE_ENUMERATED_WITHOUT_MARKER: frozenset[str] = frozenset(
    {"A15.1", "B3.2", "B3.3.4", "B4.6", "B6.1", "B6.4", "B6.7", "OO8.1"}
)

#: `open_ended=False` 的完整清单 —— 与冻结契约常量一一对应。
_ENUMERATED_VOCAB_IDS: dict[str, tuple[str, ...]] = {
    "age_model_name": AGE_MODEL_NAMES,
    "confidence_level": tuple(str(level) for level in SIGMA_LEVELS),
    "date_type": DATE_TYPES,
    "date_unit": DATE_UNITS,
    "lia_ratio_name": LIA_RATIO_NAMES,
    "ore_accessibility": YES_NO_UNCLEAR,
    "ratio_source": RATIO_SOURCES,
}

#: 内容抽查：这些真实存在的术语必须出现在对应词表里。
_REQUIRED_TERMS: dict[str, tuple[str, ...]] = {
    # 铅同位素标样必须真实存在且常用
    "pb_reference_material": (
        "NIST SRM 981", "NIST SRM 982", "NIST SRM 983",
        "BCR-1", "AGV-1", "JB-2", "BHVO-1", "G-2", "TILL-1",
    ),
    # 铊标样：NIST SRM 997 = Thallium Isotopic Standard
    "tl_reference_material": ("NIST SRM 997",),
    # 仪器类型
    "instrument_type": ("TIMS", "MC-TIMS", "MC-ICP-MS", "ICP-MS", "SIMS", "LA-MC-ICP-MS"),
    # 质量歧视校正模型
    "mass_bias_model": (
        "exponential law", "power law", "Russell law", "linear law",
        "Tl normalization (external normalization with Tl)",
    ),
    # IMA 矿物名
    "mineral_name": ("galena", "cerussite", "anglesite", "sphalerite", "pyrite",
                     "chalcopyrite"),
    # 钱币（Nomisma 术语体系）
    "coin_type_series": ("RIC", "RRC", "RPC"),
    "coin_deposition_type": ("hoard", "votive deposit", "chance loss"),
    "coin_denomination": ("denarius", "aureus", "sestertius", "solidus"),
    # 契约常量同源
    "lia_ratio_name": LIA_RATIO_NAMES,
    "date_type": DATE_TYPES,
    "date_unit": DATE_UNITS,
    "ratio_source": RATIO_SOURCES,
    "ore_accessibility": YES_NO_UNCLEAR,
}

#: 受控词表模块不得触碰的导入根与属性。
_FORBIDDEN_IMPORT_ROOTS = frozenset({"pandas", "numpy", "PyQt5", "openpyxl", "os",
                                     "pathlib", "io", "json"})
_FORBIDDEN_CALL_NAMES = frozenset({"open", "eval", "exec", "compile"})
_FORBIDDEN_ATTRS = frozenset({"read_text", "read_bytes", "write_text", "write_bytes",
                              "glob", "rglob", "open"})
_OWNED_MODULES = ("vocab.py", "labels.py")

_ID_AND_NAME = re.compile(r"^\*\*ID and name:\*\*\s+(?P<oid>\S+)\s+(?P<key>\S+)")
_HEADING = re.compile(r"^#+\s+(?P<title>.+?)\s*$")
_ALLOWED = re.compile(r"^\*\*Allowed values and other constraints:\*\*\s*(?P<text>.*?)\s*$")
_CONTROLLED_VOCAB_MARKER = "controlled vocabulary"
_OID_PATTERN = re.compile(r"^(?:OM\.C\d(?:\.\d)?|[A-Z]{1,2}\d+(?:\.\d+)*)$")


class _ArchiveField(NamedTuple):
    """测试用的最小字段视图（只取验收需要的四列）。"""

    doc: str
    oid: str
    key: str
    label_en: str
    allowed: str


@lru_cache(maxsize=None)
def _parse_doc(doc: Path) -> tuple[_ArchiveField, ...]:
    """从档案 markdown 提取 ``(oid, key, label_en, allowed)``。

    只按行扫描：标题行作为 ``label_en``，``**ID and name:**`` 行起一条记录，
    随后的 ``**Allowed values...**`` 行并入当前记录。
    """
    fields: list[_ArchiveField] = []
    heading = ""
    current: list[str] | None = None
    for line in doc.read_text(encoding="utf-8").splitlines():
        matched_heading = _HEADING.match(line)
        if matched_heading and not line.startswith("**"):
            heading = matched_heading.group("title")
            continue
        matched_id = _ID_AND_NAME.match(line)
        if matched_id:
            current = [matched_id.group("oid"), matched_id.group("key"), heading, ""]
            fields.append(_ArchiveField(doc.name, *current))
            continue
        matched_allowed = _ALLOWED.match(line)
        if matched_allowed and fields:
            last = fields[-1]
            fields[-1] = last._replace(allowed=matched_allowed.group("text"))
    return tuple(fields)


@lru_cache(maxsize=None)
def _block_fields() -> tuple[_ArchiveField, ...]:
    """`includes/metadata_blocks.md` 的 61 条块字段。"""
    return _parse_doc(_BLOCKS_DOC)


@lru_cache(maxsize=None)
def _module_fields() -> dict[str, tuple[_ArchiveField, ...]]:
    """11 个模块文档各自的模块自有字段。"""
    return {doc.name: _parse_doc(doc) for doc in _MODULE_DOCS}


@lru_cache(maxsize=None)
def _all_fields() -> tuple[_ArchiveField, ...]:
    """模块自有字段 + 块字段（共 307 条）。"""
    collected: list[_ArchiveField] = []
    for fields in _module_fields().values():
        collected.extend(fields)
    collected.extend(_block_fields())
    return tuple(collected)


def _spec(
    oid: str,
    label_en: str = "Value",
    vocab_id: str | None = None,
    table: TableKey = TableKey.ANALYSIS,
) -> FieldSpec:
    """构造只填必要字段的 `FieldSpec`（`vocab_id_for` / `label_for` 只读其中几项）。"""
    return FieldSpec(
        oid=oid,
        key="test_key",
        label_en=label_en,
        table=table,
        obligation=Obligation.MANDATORY,
        occurrence=Occurrence.ONE,
        provided_by=(ProvidedBy.DATA_PROVIDER,),
        definition="",
        allowed="",
        example="",
        parent=None,
        depth=0,
        block=None,
        block_owner=None,
        value_kind=ValueKind.FREE_TEXT,
        vocab_id=vocab_id,
        source_doc="",
        source_line=1,
        order=0,
    )


# ── labels.py：覆盖率 ─────────────────────────────────────────────────────


def test_blocks_doc_has_exactly_61_fields() -> None:
    """`includes/metadata_blocks.md` 仍是 61 条块字段（覆盖率验收的分母）。"""
    assert len(_block_fields()) == _BLOCK_FIELD_TOTAL


def test_all_block_oids_have_labels() -> None:
    """块字段 61/61 必须有中文标签（块字段按 OID 命中，与宿主模块无关）。"""
    missing = sorted({f.oid for f in _block_fields() if f.oid not in FIELD_LABELS_ZH})
    assert not missing, f"块字段缺少中文标签（{len(missing)} 条）：{missing}"


def test_module_owned_field_total_is_246() -> None:
    """11 个模块的模块自有字段合计 246 条。"""
    per_doc = {name: len(fields) for name, fields in _module_fields().items()}
    assert sum(per_doc.values()) == _MODULE_OWN_FIELD_TOTAL, per_doc


def test_eleven_module_docs_exist() -> None:
    """验收口径是 11 个模块文档。"""
    assert len(_module_fields()) == 11, sorted(_module_fields())


def test_module_label_coverage_at_least_90_percent() -> None:
    """每个模块文档的标签覆盖率 ≥90%，未覆盖的 OID 逐个列出。"""
    report: list[str] = []
    failures: list[str] = []
    for name, fields in _module_fields().items():
        if not fields:
            report.append(f"{name}: 0 条字段（文档为占位页），跳过")
            continue
        missing = sorted({f.oid for f in fields if f.oid not in FIELD_LABELS_ZH})
        coverage = (len(fields) - len(missing)) / len(fields)
        report.append(
            f"{name}: {len(fields) - len(missing)}/{len(fields)} = {coverage:.1%}"
            + (f"，未覆盖 {missing}" if missing else "")
        )
        if coverage < _MIN_MODULE_COVERAGE:
            failures.append(report[-1])
    detail = "模块标签覆盖率：\n  " + "\n  ".join(report)
    assert not failures, "以下模块低于 90%：\n  " + "\n  ".join(failures) + "\n" + detail


def test_every_archive_oid_has_label() -> None:
    """全部 307 条档案字段（246 自有 + 61 块）都有中文标签，且没有多余键。"""
    archive_oids = {f.oid for f in _all_fields()}
    missing = sorted(archive_oids - set(FIELD_LABELS_ZH))
    extra = sorted(set(FIELD_LABELS_ZH) - archive_oids)
    assert not missing, f"缺少中文标签：{missing}"
    assert not extra, f"标签表里有档案中不存在的 OID（疑似拼写错误）：{extra}"


def test_label_keys_look_like_oids() -> None:
    """标签表的键必须都是档案风格的 OID。"""
    bad = sorted(key for key in FIELD_LABELS_ZH if not _OID_PATTERN.match(key))
    assert not bad, f"键不是合法 OID：{bad}"


def test_labels_are_short_non_empty_plain_text() -> None:
    """标签非空、无首尾空白、无 markdown 残留、长度可控（表头要能排下）。"""
    problems: list[str] = []
    for oid, label in FIELD_LABELS_ZH.items():
        if not label or not label.strip():
            problems.append(f"{oid}: 空标签")
        elif label != label.strip():
            problems.append(f"{oid}: 首尾有空白 {label!r}")
        elif any(token in label for token in ("**", "[](", "#", "|")):
            problems.append(f"{oid}: 残留 markdown {label!r}")
        elif len(label) > 30:
            problems.append(f"{oid}: 标签过长（{len(label)} 字）{label!r}")
    assert not problems, "标签质量问题：\n  " + "\n  ".join(problems)


def test_english_label_table_is_non_empty_and_plain() -> None:
    """兜底英文标签表非空、键值都不含空白噪声。"""
    assert EN_LABELS_ZH
    bad = sorted(k for k, v in EN_LABELS_ZH.items() if not k.strip() or not v.strip())
    assert not bad, f"英文标签表存在空键/空值：{bad}"


# ── labels.py：label_for 回退链 ───────────────────────────────────────────


def test_label_for_prefers_oid_lookup() -> None:
    """第一级：OID 命中优先于英文标签表。"""
    assert label_for(_spec("A14", "Lead isotope ratios")) == FIELD_LABELS_ZH["A14"]
    assert label_for(_spec("OO6", "Deposit type")) == FIELD_LABELS_ZH["OO6"]


def test_label_for_falls_back_to_english_table() -> None:
    """第二级：未知 OID 但英文标签是已知写法时走 EN_LABELS_ZH。"""
    spec = _spec("ZZ9", "Longitude")
    assert label_for(spec) == EN_LABELS_ZH["Longitude"]


def test_label_for_falls_back_to_raw_english_then_oid() -> None:
    """第三/四级：未知英文标签回落到英文原文，英文也缺失时回落到 OID。"""
    assert label_for(_spec("ZZ9", "Brand New Field")) == "Brand New Field"
    assert label_for(_spec("ZZ9", "")) == "ZZ9"
    assert label_for(_spec("ZZ9", "   ")) == "ZZ9"


def test_label_for_never_returns_empty_for_archive_fields() -> None:
    """对档案里每一条真实字段，label_for 都必须给出非空标签。"""
    empty = [
        f.oid
        for f in _all_fields()
        if not label_for(_spec(f.oid, f.label_en, table=TableKey.SITE)).strip()
    ]
    assert not empty, f"以下字段拿到空标签：{sorted(set(empty))}"


# ── vocab.py：覆盖完备性 ──────────────────────────────────────────────────


def test_task_required_oids_have_vocabulary() -> None:
    """task-2 列出的 OID（除已记录的无词表字段）都必须能解析出词表。"""
    missing = [
        oid
        for oid in _TASK_REQUIRED_OIDS
        if oid not in _DOCUMENTED_WITHOUT_VOCAB and vocab_id_for(_spec(oid)) is None
    ]
    assert not missing, f"task-2 要求覆盖但缺词表的 OID：{missing}"


def test_documented_oids_without_vocabulary_stay_empty() -> None:
    """明确记录为「无受控词表」的字段不得凭空造词表。"""
    for oid, reason in _DOCUMENTED_WITHOUT_VOCAB.items():
        assert vocab_id_for(_spec(oid)) is None, f"{oid} 不应有词表：{reason}"


def test_every_controlled_vocabulary_oid_is_covered() -> None:
    """档案里标注 controlled vocabulary 的每个 OID 都必须有词表。"""
    marked = {
        f.oid
        for f in _all_fields()
        if _CONTROLLED_VOCAB_MARKER in f.allowed
    }
    assert marked, "档案里没有解析到 controlled vocabulary 标注，解析逻辑可能失效"
    missing = sorted(oid for oid in marked if vocab_id_for(_spec(oid)) is None)
    assert not missing, f"{len(missing)} 个标注受控词表的 OID 缺词表：{missing}"


def test_extra_vocabularies_are_archive_enumerated() -> None:
    """没有 controlled vocabulary 标注、却有词表的 OID 必须正好是档案已穷举的那 8 个。"""
    marked = {f.oid for f in _all_fields() if _CONTROLLED_VOCAB_MARKER in f.allowed}
    extra = {
        f.oid
        for f in _all_fields()
        if _CONTROLLED_VOCAB_MARKER not in f.allowed and vocab_id_for(_spec(f.oid))
    }
    assert extra == set(_ARCHIVE_ENUMERATED_WITHOUT_MARKER), (
        f"多出未记录的词表映射：{sorted(extra - set(_ARCHIVE_ENUMERATED_WITHOUT_MARKER))}；"
        f"缺少已记录的：{sorted(set(_ARCHIVE_ENUMERATED_WITHOUT_MARKER) - extra)}"
    )


def test_every_vocabulary_is_reachable_from_some_oid() -> None:
    """每个词表都必须至少被一个档案 OID 引用（防止死词表与键名拼写错误）。"""
    reachable = {
        vocab_id_for(_spec(f.oid))
        for f in _all_fields()
    }
    reachable.discard(None)
    orphans = sorted(set(VOCABULARIES) - reachable)
    assert not orphans, f"没有任何 OID 引用的词表：{orphans}"


def test_declared_oids_all_exist_in_the_archive() -> None:
    """白盒检查：`_VOCAB_SPECS` 的 oids 列不得出现档案里不存在的 OID（防拼写错误）。

    ``_OID_VOCAB`` 由该列推导，所以一个错的 OID 会静默地什么都不命中 —— 这里直接拿它对
    档案 OID 全集做差集。
    """
    from data.metadata_profile import vocab as vocab_module

    archive_oids = {f.oid for f in _all_fields()}
    declared = {oid for spec in vocab_module._VOCAB_SPECS for oid in spec[4]}  # noqa: SLF001
    unknown = sorted(declared - archive_oids)
    assert not unknown, f"词表声明了档案中不存在的 OID：{unknown}"


# ── vocab.py：注册表结构与术语质量 ────────────────────────────────────────


def test_vocabulary_registry_is_consistent() -> None:
    """键与 id 一致、类型正确、必填文本字段非空。"""
    assert len(VOCABULARIES) >= 70, f"词表数量异常偏少：{len(VOCABULARIES)}"
    problems: list[str] = []
    for key, vocab in VOCABULARIES.items():
        if not isinstance(vocab, Vocabulary):
            problems.append(f"{key}: 不是 Vocabulary")
            continue
        if key != vocab.id:
            problems.append(f"{key}: 键与 id 不一致（{vocab.id}）")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", vocab.id):
            problems.append(f"{key}: id 不是小写 snake_case")
        for attr in ("label_en", "label_zh", "source"):
            if not str(getattr(vocab, attr)).strip():
                problems.append(f"{key}: {attr} 为空")
    assert not problems, "词表注册表问题：\n  " + "\n  ".join(problems)


def test_vocabulary_is_frozen() -> None:
    """Vocabulary 是冻结 dataclass，词表不会被就地改写。"""
    vocab = VOCABULARIES["instrument_type"]
    with pytest.raises(FrozenInstanceError):
        vocab.terms = ()  # type: ignore[misc]


def test_terms_are_unique_stripped_and_normalised_unique() -> None:
    """术语非空、去空白、无重复，且不存在大小写/空白差异造成的重复写法。"""
    problems: list[str] = []
    for key, vocab in VOCABULARIES.items():
        if not vocab.terms:
            problems.append(f"{key}: 空词表")
            continue
        for term in vocab.terms:
            if not term or term != term.strip():
                problems.append(f"{key}: 术语含空串或首尾空白 {term!r}")
        if len(set(vocab.terms)) != len(vocab.terms):
            problems.append(f"{key}: 完全重复的术语")
        normalised = [" ".join(t.split()).casefold() for t in vocab.terms]
        if len(set(normalised)) != len(normalised):
            problems.append(f"{key}: 归一化后重复（大小写/空白变体），应只留规范写法")
    assert not problems, "术语质量问题：\n  " + "\n  ".join(problems)


def test_local_vocabularies_declare_local_supplement() -> None:
    """`open_ended=True` 的本地补充词表必须在 source 里说明「本地补充」。"""
    problems = [
        key
        for key, vocab in VOCABULARIES.items()
        if vocab.open_ended and "本地补充" not in vocab.source
    ]
    assert not problems, f"以下词表的 source 未声明是本地补充：{sorted(problems)}"


def test_mineral_names_use_lowercase_ima_style() -> None:
    """矿物名统一小写（IMA 规范写法），不得混入 Limonite 式写法。"""
    bad = [t for t in terms("mineral_name") if t != t.lower()]
    assert not bad, f"矿物名应全小写：{bad}"


def test_explicitly_documented_term_decisions_are_recorded() -> None:
    """把「检索无果故不收 Pb-1」这一决定固化下来，避免后来人凭印象加回去。"""
    source = VOCABULARIES["pb_reference_material"].source
    assert "Pb-1" in source and "未收" in source, "A9.1 的 source 必须保留 Pb-1 的处理记录"
    assert "Pb-1" not in terms("pb_reference_material")


@pytest.mark.parametrize("vocab_id", sorted(_REQUIRED_TERMS))
def test_required_terms_are_present(vocab_id: str) -> None:
    """内容抽查：关键术语必须真实且出现在词表里。"""
    required = _REQUIRED_TERMS[vocab_id]
    missing = [term for term in required if not contains(vocab_id, term)]
    assert not missing, f"{vocab_id} 缺少必需术语：{missing}"


def test_enumeration_derived_vocabularies_match_contract() -> None:
    """词表内容与冻结契约常量逐项一致（防止两处漂移）。"""
    problems: list[str] = []
    for vocab_id, expected in _ENUMERATED_VOCAB_IDS.items():
        if terms(vocab_id) != tuple(expected):
            problems.append(f"{vocab_id}: {terms(vocab_id)} != {tuple(expected)}")
    assert not problems, "枚举词表与 spec.py 常量不一致：\n  " + "\n  ".join(problems)


# ── vocab.py：查询函数语义 ────────────────────────────────────────────────


def test_vocab_id_for_uses_oid_only() -> None:
    """`vocab_id_for` 只看 OID：即使 spec.vocab_id 是伪造值也不受影响。"""
    assert vocab_id_for(_spec("A6.1", vocab_id="bogus_id")) == "instrument_type"
    assert vocab_id_for(_spec("B6.1", vocab_id="not_a_vocab")) == "lia_ratio_name"
    assert vocab_id_for(_spec("OM.C9")) == "coin_peculiarity"


def test_vocab_id_for_returns_none_for_free_text_fields() -> None:
    """自由文本 / 数值 / 日期字段没有词表。"""
    for oid in ("A0", "A1", "A7", "B6.2", "O3", "S11", "SI1", "OO7", "UNKNOWN"):
        assert vocab_id_for(_spec(oid)) is None, oid


def test_block_fields_hit_by_oid_across_host_tables() -> None:
    """块字段在任意宿主模块内联时都按同一 OID 命中同一词表。"""
    for table in (TableKey.ANALYSIS, TableKey.OBJECT, TableKey.SITE,
                  TableKey.SAMPLE, TableKey.ORE):
        assert vocab_id_for(_spec("B6.1", table=table)) == "lia_ratio_name"
        assert vocab_id_for(_spec("B4.6", table=table)) == "confidence_level"


def test_lookup_helpers_defaults_for_unknown_id() -> None:
    """未知 id 的默认值：terms→()、vocabulary→None、open_ended→True（保守）。"""
    assert terms("no_such_vocabulary") == ()
    assert vocabulary("no_such_vocabulary") is None
    assert open_ended("no_such_vocabulary") is True
    assert terms("") == ()
    assert open_ended("") is True


def test_open_ended_false_set_is_exactly_the_enumerated_one() -> None:
    """`open_ended=False` 只允许这 7 个档案已穷举的词表。"""
    closed = {key for key, vocab in VOCABULARIES.items() if not vocab.open_ended}
    assert closed == set(_ENUMERATED_VOCAB_IDS), (
        f"多出：{sorted(closed - set(_ENUMERATED_VOCAB_IDS))}；"
        f"缺少：{sorted(set(_ENUMERATED_VOCAB_IDS) - closed)}"
    )


def test_closed_vocabularies_cite_the_archive() -> None:
    """`open_ended=False` 的词表必须在 source 里写明档案已枚举。"""
    bad = [
        key
        for key, vocab in VOCABULARIES.items()
        if not vocab.open_ended and "档案已枚举" not in vocab.source
    ]
    assert not bad, f"封闭词表未注明档案出处：{bad}"


def test_open_ended_indicates_free_text_tolerance() -> None:
    """`open_ended=True` 占绝大多数：档案明说词表可能不全，词表外取值不应报硬错。"""
    opened = [key for key, vocab in VOCABULARIES.items() if vocab.open_ended]
    assert len(opened) == len(VOCABULARIES) - len(_ENUMERATED_VOCAB_IDS)
    assert len(opened) > len(_ENUMERATED_VOCAB_IDS)
    for vocab_id in ("instrument_model", "pb_reference_material", "glass_group",
                     "coin_mint", "analysed_compound"):
        assert open_ended(vocab_id) is True


# ── vocab.py：contains 语义 ───────────────────────────────────────────────


def test_contains_is_case_and_whitespace_insensitive() -> None:
    """大小写与空白不敏感。"""
    assert contains("instrument_type", "tims") is True
    assert contains("instrument_type", "  TIMS  ") is True
    assert contains("instrument_type", "mc-icp-ms") is True
    assert contains("instrument_type", "Mc-Icp-Ms") is True
    assert contains("pb_reference_material", "nist srm 981") is True
    assert contains("confidence_level", " 2 ") is True


def test_contains_rejects_unknown_values_and_inputs() -> None:
    """词表外取值、未知 id、空值一律 False，且不抛异常。"""
    assert contains("instrument_type", "TIMs-9000") is False
    assert contains("instrument_type", "") is False
    assert contains("instrument_type", "   ") is False
    assert contains("instrument_type", None) is False
    assert contains("no_such_vocabulary", "TIMS") is False
    assert contains("", "TIMS") is False


def test_contains_does_not_do_alias_or_substring_matching() -> None:
    """只做归一化后的全等比较：不做子串、前缀或别名匹配。

    这条是刻意固化的契约 —— 别名必须在词表内容层解决（只收规范写法），
    否则校验层会把 ``SRM 981`` 当成 ``NIST SRM 981`` 而放过不规范写法。
    """
    assert contains("pb_reference_material", "SRM 981") is False
    assert contains("pb_reference_material", "NIST SRM 98") is False
    assert contains("instrument_type", "TIMS ") is True  # 空白仍应容忍
    assert contains("instrument_type", "TI") is False


def test_contains_agrees_with_terms_for_every_vocabulary() -> None:
    """对每个词表的每个术语，contains 必须为真（自洽性）。"""
    problems: list[str] = []
    for key, vocab in VOCABULARIES.items():
        for term in vocab.terms:
            if not contains(key, term):
                problems.append(f"{key}: {term!r}")
    assert not problems, f"contains 与 terms 不自洽：{problems}"


def test_vocabulary_and_terms_agree() -> None:
    """`vocabulary()` 与 `terms()` 返回同一份数据。"""
    for key, vocab in VOCABULARIES.items():
        assert vocabulary(key) is vocab
        assert terms(key) == vocab.terms


# ── 模块边界：纯数据 + 纯函数 ─────────────────────────────────────────────


def _module_paths() -> list[Path]:
    package_dir = _PROJECT_ROOT / "data" / "metadata_profile"
    return [package_dir / name for name in _OWNED_MODULES]


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


@pytest.mark.parametrize("module_path", _module_paths(), ids=lambda p: p.name)
def test_owned_modules_are_dependency_free_and_io_free(module_path: Path) -> None:
    """`vocab.py` / `labels.py` 不得导入 pandas/numpy/PyQt5/openpyxl，也不得做文件 IO。"""
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = _import_roots(tree) & _FORBIDDEN_IMPORT_ROOTS
    assert not forbidden_imports, f"{module_path.name} 导入了禁用依赖：{forbidden_imports}"
    forbidden_calls = _called_names(tree) & (_FORBIDDEN_CALL_NAMES | _FORBIDDEN_ATTRS)
    assert not forbidden_calls, f"{module_path.name} 出现疑似 IO/动态执行调用：{forbidden_calls}"
    assert "read_text(" not in source and "open(" not in source


def test_owned_modules_declare_docstring_and_all() -> None:
    """文件头 docstring 与 `__all__` 是项目规范（§1.2/§2.1）。"""
    for module_path in _module_paths():
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{module_path.name} 缺少文件头 docstring"
        assert "__all__" in module_path.read_text(encoding="utf-8"), (
            f"{module_path.name} 缺少 __all__"
        )


def test_vocab_public_api_surface() -> None:
    """公开 API 已定稿：6 个查询入口 + Vocabulary，名字不得漂移。"""
    from data.metadata_profile import vocab as vocab_module

    assert set(vocab_module.__all__) == {
        "Vocabulary",
        "VOCABULARIES",
        "contains",
        "open_ended",
        "terms",
        "vocab_id_for",
        "vocabulary",
    }


def test_labels_public_api_surface() -> None:
    """`labels.py` 只导出两张表和 `label_for`。"""
    from data.metadata_profile import labels as labels_module

    assert set(labels_module.__all__) == {"EN_LABELS_ZH", "FIELD_LABELS_ZH", "label_for"}
