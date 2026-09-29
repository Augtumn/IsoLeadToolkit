"""TerraLID 档案 markdown 的解析层。

把 `reference/metadata` 的字段定义翻译成 `spec.FieldSpec`（组装 `Profile` 由
`profile.py` 负责）：`parse_table_document` 解 `docs/metadata_<table>.md` →
`TableDocument`（自有字段 + 内联点）；`parse_block_document` 解
`includes/metadata_blocks.md` → `BlockDocument`（块成员 + 块根）；`read_profile_version`
解 `docs/changelog.md` → 档案版本号。

字段块的识别规则（宽松，但只认已知键）
--------------------------------------

字段块 = markdown 标题（`##`–`#####`，文本即 `label_en`）+ 紧随的元信息行；标题与元信息
之间允许空行（`metadata_sites.md` 的 `SI0` 如此）。元信息行是 ``**键名**`` 之后跟可选的
冒号与值（正则见 `_META_LINE_RE`），键名经 `strip()` → `rstrip(':')` → `strip()` 后与
`META_KEYS` 的 7 个键做大小写不敏感比对；``ID and name`` 的第一个 token 是 `oid`、
第二个 token 是 `key`（`metadata_metal-coins.md` 键名后的 ``(`nmo:TypeSeries`)`` 注解既不是
OID 也不是键名）。`Allowed values and other constraints` / `Example` 可以缺席（记空串）；
`Definition` 可跨行——紧跟的连续非空行并入定义，遇到空行、下一个元信息行、标题或 ``{%``
指令行结束。正文里其它粗体行（``**Note**:``）不算元信息，字段块到此为止，故"宽松"不会
退化成"什么都吃"。

**为什么容忍粗体外的冒号**：档案由 mkdocs 手工维护（`changelog.md` 里就有
"Correct formatting and broken links"），格式变体是常态。`metadata_objects.md:66-70` 的
`O5.1 object_pid` 整块写成 ``**ID and name**:``；它声明 `Occurrences: 0–n` 且是
`O5.1.1` / `O5.1.2` 的父，按严格写法跳过就是真实数据损失（objects 少 1 条自有字段、
两条子字段失去父）。全档扫描确认这类变体仅此一处（11 个模块文档 + 1 个块文档）。

内联块与字段身份
----------------

表文档里的 ``{% include-markdown "…/metadata_blocks.md" start="<!--XXX-start-->" %}`` 把
`XXX` 对应的块（person→B1 / status→B2 / dating→B3 / chemistry→B4 / relation→B5 / lia→B6）
内联到 **include 之前最近出现的那个字段**（`block_owner`）。同一块可被多次内联（analyses
内联 relation 四次、lia 两次），内联副本**保留原 OID**，于是 analyses 的字段序列里 `B6.2`
出现两次。块字段的身份是 ``(table, block_owner, oid)`` 三元组，不是 ``oid`` 单键：`oid` 只在
"同一模块的同一宿主"内唯一，任何以 `oid` 为键的下游结构（词表、校验报告、列索引）都必须
再带上 `block_owner`，否则 analyses 里 B5/B6 的多份副本会互相覆盖。块定义自身
（`Profile.blocks`）与内联副本是各自独立的 `FieldSpec`：前者 `block_owner=None`，后者指向
宿主 OID（`A9.3` 与 `A14` 各持一份 B6）。

深度、父字段与 `value_kind`
---------------------------

`parent` / `depth` 相对 `TableKey.oid_prefix` 计算（块字段相对块根 `B1`–`B6`）：去掉最后
一个点分片段即父。`metal-coins` 前缀 `OM.C` 自带一个点，故 `OM.C1` 是钱币表顶层
（`depth=0`、`parent=None`），不会推出档案里不存在的假父 `OM`。这条不只是"深度好看"：
`layout` 用 `parent` 判定哪些字段是可重复组的根，按"点分片段数 − 1"硬减会让
`OM.C1`–`OM.C9` 的层级判断跑偏。父 OID 确实不存在时 `parent=None` 并告警（当前档案不触发）。

`value_kind`：`allowed` 非空且不是 `t.b.d.` 时只按 `allowed` 判定（定义里常出现
"mail address" 之类举例，混用会把自由文本误判成 EMAIL），否则回退 `definition`——
`B1.4` / `B5.1` 这类 PID 组字段没有 `allowed`。规则表见 `_KIND_TESTS`，按优先级命中即取：
8 个比值名、`original, calculated`、`geological, archaeological`、`a, Ma`、
`yes, no, unclear`、`1, 2, 3`、`date formatted as YYYY-MM-DD`、`is valid mail address`、
`file path`、persistent identifier / is valid ROR ID / PIDinst、`decimal number`、`integer`、
`number`、`is valid URL`、`controlled vocabulary`；命中两个及以上互不相干的族
（DECIMAL/INTEGER/NUMBER 视为一族）→MIXED；全不命中→FREE_TEXT。
这里给出的是**文本可推断的**类型；`vocab.py` 登记了词表的字段由 `profile.py` 富化时把
FREE_TEXT / MIXED 提升为 CONTROLLED_VOCAB（受控词表以 `vocab.py` 为唯一真源，解析层不猜）。

warning 目录（`Profile.warnings`，逐条可定位到 `source_doc:source_line`）
------------------------------------------------------------------------

1. 文档里没有任何字段（`metadata_by-products.md` 是空壳）；
2. 字段块缺少 ``ID and name`` 元信息 → 跳过该字段（防御性检查，当前档案不触发）；
3. 字段缺少 ``**Definition:**``（`B3.1 date_pid`）→ 定义记为空串；
4. `Obligation` / `Occurrences` 文本无法识别 → 回退 `optional` / `0-1`（`A16` 的 `–n` 漏了 0）；
5. 同一模块内自有字段 OID 重复 → 保留首个（内联副本的重复 OID 是设计使然，不算异常）；
6. 父 OID 不存在 → `parent=None`（防御性检查，当前档案不触发）；
7. include 标记无法映射到块，或 include 之前没有字段 → 忽略该次内联。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .spec import (
    LIA_RATIO_NAMES,
    PROFILE_VERSION_FALLBACK,
    Block,
    FieldSpec,
    Obligation,
    Occurrence,
    ProvidedBy,
    TableKey,
    ValueKind,
)

logger = logging.getLogger(__name__)

#: 模块文档所在子目录（相对档案根 `reference/metadata`）。
DOCS_DIRNAME = "docs"

#: 可复用块文档的相对路径。
BLOCKS_DOC_RELATIVE = "includes/metadata_blocks.md"

#: 版本号文档的相对路径。
CHANGELOG_RELATIVE = "docs/changelog.md"

#: 字段块标题的 markdown 级别：`##`–`#####`。
FIELD_HEADING_LEVELS: tuple[int, ...] = (2, 3, 4, 5)

#: 元信息键名（只认这 7 个，冒号可在粗体内或粗体外）。
META_KEYS: tuple[str, ...] = (
    "ID and name",
    "Provided by",
    "Obligation",
    "Occurrences",
    "Definition",
    "Allowed values and other constraints",
    "Example",
)

_KEY_ID_AND_NAME = META_KEYS[0]
_KEY_DEFINITION = META_KEYS[4]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
#: 元信息行：``**键名**`` + 可选冒号（粗体内外皆可）+ 值。
_META_LINE_RE = re.compile(r"^\*\*(?P<key>[^*]+?)\*\*\s*:?\s*(?P<value>.*)$")
_INCLUDE_START_RE = re.compile(r'start="<!--(?P<stem>[A-Za-z0-9_-]+)-start-->"')
_REGION_START_RE = re.compile(r"^<!--(?P<stem>[A-Za-z0-9_-]+)-start-->$")
_REGION_END_RE = re.compile(r"^<!--(?P<stem>[A-Za-z0-9_-]+)-end-->$")
_VERSION_RE = re.compile(r"^##\s+Version\s+(?P<version>\d+(?:\.\d+)+)\s*$")

#: 归一化（小写、去尾冒号）后的键名 → 规范键名。
_META_KEY_BY_LOWER: Mapping[str, str] = {key.lower(): key for key in META_KEYS}

#: include 标记前缀 → 可复用块。
_BLOCK_BY_STEM: Mapping[str, Block] = {block.include_stem: block for block in Block}

#: 块根 OID（`B1`–`B6`）：不是模块字段，但是内联块字段父链的终点。
_BLOCK_ROOT_OIDS: frozenset[str] = frozenset(block.value for block in Block)

#: include 指令的身份行（`include-markdown` 与目标文档）可能位于 `start=` 上方若干行。
_DIRECTIVE_LOOKBACK = 8



@dataclass(frozen=True)
class InlineInclude:
    """表文档里的一次 include（一次可复用块内联）。

    Attributes:
        block: 被内联的可复用块。
        owner_oid: 宿主字段 OID（include 之前最近出现的字段）。
        source_line: include 标记所在行号（1 起）。
    """

    block: Block
    owner_oid: str | None
    source_line: int


@dataclass(frozen=True)
class TableDocument:
    """一个模块文档（`docs/metadata_<table>.md`）的解析结果。

    Attributes:
        table: 模块键。
        own_fields: 模块自有字段（不含内联块字段），`order` 为自有字段序。
        inlines: 按文档顺序记录的内联点（可能重复同一个块）。
        warnings: 解析告警，格式为 ``<相对路径>:<行号>: <说明>``。
    """

    table: TableKey
    own_fields: tuple[FieldSpec, ...]
    inlines: tuple[InlineInclude, ...]
    warnings: tuple[str, ...]

    @property
    def source_doc(self) -> str:
        """源文档相对路径（相对档案根）。"""
        return table_doc_relative(self.table)


@dataclass(frozen=True)
class BlockDocument:
    """`includes/metadata_blocks.md` 的解析结果。

    Attributes:
        members: 每个可复用块的成员字段（**不含**块根，`B6` 的成员是 `B6.1`–`B6.7`）。
        roots: 块根字段定义（`B1`–`B6` 各一条），用于回溯与父链校验。
        fields: 文档里全部字段定义（块根 + 成员，按文档顺序），共 61 条。
        warnings: 解析告警。
    """

    members: Mapping[Block, tuple[FieldSpec, ...]]
    roots: Mapping[Block, FieldSpec]
    fields: tuple[FieldSpec, ...]
    warnings: tuple[str, ...]


def table_doc_relative(table: TableKey) -> str:
    """模块文档的相对路径（相对档案根），如 ``docs/metadata_sites.md``。

    Args:
        table: 模块键。

    Returns:
        相对路径字符串。
    """
    return f"{DOCS_DIRNAME}/{table.doc_name}"


def _read_lines(path: Path) -> tuple[str, ...]:
    """读取文档为行序列（索引 + 1 即档案行号）；缺文件时抛出 `FileNotFoundError`。"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise FileNotFoundError(f"TerraLID 档案文档缺失：{path}") from err
    return tuple(text.splitlines())



@dataclass(frozen=True)
class _RawBlock:
    """一个 markdown 标题块：标题文本 + 紧随其后的元信息行。"""

    label_en: str
    line: int
    metas: Mapping[str, str]


def _canonical_meta_key(text: str) -> str | None:
    """把粗体键名归一为规范元信息键名；不是已知键时返回 `None`。"""
    normalized = str(text or "").strip().rstrip(":").strip().lower()
    return _META_KEY_BY_LOWER.get(normalized)


def _raw_blocks(lines: Sequence[str]) -> tuple[_RawBlock, ...]:
    """扫描文档中的标题块（`##`–`#####` 标题 + 紧随的元信息行），按文档顺序返回。"""
    blocks: list[_RawBlock] = []
    total = len(lines)
    index = 0
    while index < total:
        heading = _HEADING_RE.match(lines[index])
        if heading is None or len(heading.group(1)) not in FIELD_HEADING_LEVELS:
            index += 1
            continue

        label = heading.group(2).strip()
        cursor = index + 1
        while cursor < total and not lines[cursor].strip():
            cursor += 1

        metas: dict[str, str] = {}
        last_key: str | None = None
        while cursor < total:
            line = lines[cursor]
            if _HEADING_RE.match(line) or not line.strip():
                break
            meta = _META_LINE_RE.match(line)
            if meta is not None:
                key = _canonical_meta_key(meta.group("key"))
                if key is None:
                    break  # 正文里的其它粗体行（`**Note**:`）→ 字段块到此为止
                last_key = key
                metas[key] = meta.group("value").strip()
            elif line.lstrip().startswith(("**", "{%")):
                break  # 指令行或其它粗体行：字段块到此为止
            elif last_key is not None:
                metas[last_key] = f"{metas[last_key]} {line.strip()}".strip()
            else:
                break
            cursor += 1

        blocks.append(_RawBlock(label_en=label, line=index + 1, metas=metas))
        index = cursor if cursor > index else index + 1
    return tuple(blocks)


def _split_oid_and_key(payload: str) -> tuple[str, str]:
    """拆 ``ID and name`` 载荷为 ``(oid, key)``：第一个 token 是 OID，第二个是键名。"""
    tokens = str(payload or "").split()
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], ""
    return tokens[0], tokens[1]


def _derive_parent(oid: str, prefix: str) -> str | None:
    """按点分层级推出父 OID（相对 `prefix`）；已在前缀层级（顶层）时为 `None`。"""
    oid_parts = oid.split(".")
    prefix_parts = prefix.split(".")
    if len(oid_parts) <= len(prefix_parts):
        return None
    return ".".join(oid_parts[:-1])


def _derive_depth(oid: str, prefix: str) -> int:
    """按点分层级推出深度（相对 `prefix`，顶层为 0，最小 0）。"""
    return max(len(oid.split(".")) - len(prefix.split(".")), 0)


def _normalize_occurrence_text(text: str) -> str:
    """归一化 occurrences 原文（en-dash / em-dash / minus 统一为 hyphen，去空格）。"""
    normalized = str(text or "").strip().lower()
    for dash in ("\u2013", "\u2014", "\u2212"):
        normalized = normalized.replace(dash, "-")
    return normalized.replace(" ", "")


def _is_empty_constraint(text: str) -> bool:
    """判断 `allowed` 文本是否等价于"没有约束"（空串或 ``t.b.d.``）。"""
    return str(text or "").strip().lower().rstrip(".") in ("", "t.b.d")


def _build_field(
    raw: _RawBlock,
    *,
    source_doc: str,
    table: TableKey,
    block: Block | None,
    block_owner: str | None,
    order: int,
    prefix: str | None,
    warnings: list[str],
) -> FieldSpec | None:
    """把一个原始标题块翻译成 `FieldSpec`（`prefix=None` 表示以自身 OID 为前缀）。

    Args:
        raw: 原始块（标题 + 元信息）；source_doc: 源文档相对路径。
        table: 所属模块（块定义取首个内联它的模块）。
        block / block_owner: 所属可复用块与内联宿主 OID（模块自有字段均为 `None`）。
        order: 模块内出现序（块定义内为块内序）；prefix: 计算 `parent` / `depth` 的前缀。
        warnings: 告警收集列表（就地追加）。

    Returns:
        字段定义；缺少或无法解析 ``ID and name`` 元信息时返回 `None`（已记录告警）。
    """
    payload = raw.metas.get(_KEY_ID_AND_NAME)
    if payload is None:
        warnings.append(
            f"{source_doc}:{raw.line}: 字段块缺少 `ID and name` 元信息，已跳过"
            f"（标题：{raw.label_en!r}）"
        )
        return None

    oid, key = _split_oid_and_key(payload)
    if not oid:
        warnings.append(f"{source_doc}:{raw.line}: `ID and name` 载荷为空，已跳过")
        return None

    effective_prefix = prefix if prefix is not None else oid

    obligation_text = raw.metas.get("Obligation", "")
    obligation = Obligation.from_text(obligation_text)
    if obligation_text.strip().lower() not in {member.value for member in Obligation}:
        warnings.append(
            f"{source_doc}:{raw.line}: 字段 {oid} 的 Obligation {obligation_text!r} 无法识别，"
            f"回退为 {obligation.value}"
        )

    occurrence_text = raw.metas.get("Occurrences", "")
    occurrence = Occurrence.from_text(occurrence_text)
    known_occurrences = {member.value for member in Occurrence}
    if _normalize_occurrence_text(occurrence_text) not in known_occurrences:
        warnings.append(
            f"{source_doc}:{raw.line}: 字段 {oid} 的 Occurrences {occurrence_text!r} 无法识别，"
            f"回退为 {occurrence.value}（规范写法 0-1 / 1 / 0-n / 1-n）"
        )

    definition = raw.metas.get(_KEY_DEFINITION, "")
    if _KEY_DEFINITION not in raw.metas:
        warnings.append(
            f"{source_doc}:{raw.line}: 字段 {oid} 缺少 `**Definition:**`，定义记为空串"
        )

    allowed = raw.metas.get("Allowed values and other constraints", "")
    example = raw.metas.get("Example", "")

    return FieldSpec(
        oid=oid,
        key=key,
        label_en=raw.label_en,
        table=table,
        obligation=obligation,
        occurrence=occurrence,
        provided_by=ProvidedBy.parse_list(raw.metas.get("Provided by", "")),
        definition=definition,
        allowed=allowed,
        example=example,
        parent=_derive_parent(oid, effective_prefix),
        depth=_derive_depth(oid, effective_prefix),
        block=block,
        block_owner=block_owner,
        value_kind=infer_value_kind(allowed, definition),
        vocab_id=None,  # 由 profile.py 通过 vocab.vocab_id_for() 填充
        source_doc=source_doc,
        source_line=raw.line,
        order=order,
    )


def _resolve_missing_parents(
    fields: Sequence[FieldSpec],
    *,
    known_oids: frozenset[str],
    source_doc: str,
    warnings: list[str],
) -> tuple[FieldSpec, ...]:
    """把指向不存在父字段的 `parent` 置为 `None` 并告警，返回修正后的字段元组。"""
    resolved: list[FieldSpec] = []
    for spec in fields:
        if spec.parent is not None and spec.parent not in known_oids:
            warnings.append(
                f"{source_doc}:{spec.source_line}: 字段 {spec.oid} 的父 OID {spec.parent} "
                f"在该模块内不存在，parent 置为 None"
            )
            spec = replace(spec, parent=None)
        resolved.append(spec)
    return tuple(resolved)


def _directive_mentions_include(lines: Sequence[str], index: int) -> bool:
    """判断第 `index` 行是否位于引用块文档的 include 指令内。"""
    start = max(index - _DIRECTIVE_LOOKBACK, 0)
    window = " ".join(lines[start : index + 1])
    return "include-markdown" in window and "metadata_blocks.md" in window


def _find_includes(
    lines: Sequence[str],
    own_fields: Sequence[FieldSpec],
    *,
    source_doc: str,
    warnings: list[str],
) -> tuple[InlineInclude, ...]:
    """找出表文档里的全部 include 及其宿主字段，按文档顺序返回内联点。"""
    records: list[InlineInclude] = []
    for index, line in enumerate(lines):
        match = _INCLUDE_START_RE.search(line)
        if match is None or not _directive_mentions_include(lines, index):
            continue
        line_no = index + 1
        stem = match.group("stem")
        block = _BLOCK_BY_STEM.get(stem)
        if block is None:
            warnings.append(
                f"{source_doc}:{line_no}: include 标记 {stem!r} 无法映射到可复用块，已忽略"
            )
            continue

        owner: FieldSpec | None = None
        for candidate in own_fields:
            if candidate.source_line >= line_no:
                break
            owner = candidate
        if owner is None:
            warnings.append(
                f"{source_doc}:{line_no}: include {stem!r} 之前没有字段，"
                f"无法确定 block_owner，已忽略该次内联"
            )
            continue
        records.append(InlineInclude(block=block, owner_oid=owner.oid, source_line=line_no))
    return tuple(records)


def parse_table_document(path: str | Path, table: TableKey) -> TableDocument:
    """解析一个模块文档（`docs/metadata_<table>.md`）。

    Args:
        path: 文档路径。
        table: 模块键；决定 `oid_prefix`（用于 `parent` / `depth`）与 `source_doc`。

    Returns:
        模块自有字段、内联点与解析告警。

    Raises:
        FileNotFoundError: 文档不存在。
    """
    doc_path = Path(path)
    source_doc = table_doc_relative(table)
    lines = _read_lines(doc_path)
    warnings: list[str] = []

    own_fields: list[FieldSpec] = []
    seen_lines: dict[str, int] = {}
    for raw in _raw_blocks(lines):
        spec = _build_field(
            raw,
            source_doc=source_doc,
            table=table,
            block=None,
            block_owner=None,
            order=len(own_fields),
            prefix=table.oid_prefix,
            warnings=warnings,
        )
        if spec is None:
            continue
        if spec.oid in seen_lines:
            warnings.append(
                f"{source_doc}:{spec.source_line}: 字段 {spec.oid} 的 OID 重复"
                f"（首次出现于第 {seen_lines[spec.oid]} 行），已跳过重复项"
            )
            continue
        seen_lines[spec.oid] = spec.source_line
        own_fields.append(spec)

    known_oids = frozenset(seen_lines) | _BLOCK_ROOT_OIDS
    resolved = _resolve_missing_parents(
        own_fields, known_oids=known_oids, source_doc=source_doc, warnings=warnings
    )
    inlines = _find_includes(lines, resolved, source_doc=source_doc, warnings=warnings)

    if not resolved and not inlines:
        warnings.append(f"{source_doc}: 文档中没有任何字段（空壳文档）")

    return TableDocument(
        table=table,
        own_fields=resolved,
        inlines=inlines,
        warnings=tuple(warnings),
    )


def _region_bounds(
    lines: Sequence[str], *, source_doc: str, warnings: list[str]
) -> tuple[tuple[Block, int, int], ...]:
    """扫描块文档的区域标记，返回 ``(块, 起始行, 结束行)``，按起始行排序。"""
    bounds: list[tuple[Block, int, int]] = []
    opened: tuple[Block, int] | None = None
    for index, line in enumerate(lines):
        line_no = index + 1
        stripped = line.strip()
        start_match = _REGION_START_RE.match(stripped)
        if start_match is not None:
            block = _BLOCK_BY_STEM.get(start_match.group("stem"))
            if block is None:
                warnings.append(
                    f"{source_doc}:{line_no}: 区域标记 {start_match.group('stem')!r} "
                    f"无法映射到可复用块，已忽略"
                )
                continue
            if opened is not None:
                warnings.append(
                    f"{source_doc}:{line_no}: 块 {opened[0].value} 的区域未闭合就遇到新区域标记"
                )
            opened = (block, line_no)
            continue
        end_match = _REGION_END_RE.match(stripped)
        if end_match is not None and opened is not None:
            bounds.append((opened[0], opened[1], line_no))
            opened = None
    if opened is not None:
        warnings.append(f"{source_doc}: 块 {opened[0].value} 的区域标记未闭合")
    return tuple(bounds)


def _region_for_line(bounds: Sequence[tuple[Block, int, int]], line: int) -> Block | None:
    """返回包含第 `line` 行的区域对应的块；位于所有区域之外时为 `None`。"""
    for block, start, end in bounds:
        if start < line < end:
            return block
    return None


def parse_block_document(
    path: str | Path,
    *,
    table_for_block: Mapping[Block, TableKey] | None = None,
) -> BlockDocument:
    """解析 `includes/metadata_blocks.md`。

    块根（`B1`–`B6`）位于 ``<!--X-start-->`` 区域之外，是块的标识本身而不是模块字段：模块里
    与之等价的字段是内联它的那个宿主字段（如 `A14` ↔ `B6`）。因此 `members` **不含**块根，
    `roots` 单独给出，两者合计 61 条 = 文档里全部字段定义。

    Args:
        path: 块文档路径。
        table_for_block: 块 → 首个内联它的模块，用于给 `FieldSpec.table` 一个确定值；缺失时
            回退为 `TableKey.ANALYSIS`（`B4` / `B6` 的首个内联模块是 analyses）。

    Returns:
        块成员、块根、全部字段与解析告警。

    Raises:
        FileNotFoundError: 文档不存在。
    """
    doc_path = Path(path)
    source_doc = BLOCKS_DOC_RELATIVE
    lines = _read_lines(doc_path)
    warnings: list[str] = []
    owners = dict(table_for_block or {})

    bounds = _region_bounds(lines, source_doc=source_doc, warnings=warnings)
    present_blocks = {block for block, _, _ in bounds}

    members: dict[Block, list[FieldSpec]] = {block: [] for block in Block}
    roots: dict[Block, FieldSpec] = {}
    every_field: list[FieldSpec] = []

    for raw in _raw_blocks(lines):
        block = _region_for_line(bounds, raw.line)
        if block is None:
            oid, _ = _split_oid_and_key(raw.metas.get(_KEY_ID_AND_NAME, ""))
            root_block = next((b for b in Block if b.value == oid), None)
            spec = _build_field(
                raw,
                source_doc=source_doc,
                table=owners.get(root_block, TableKey.ANALYSIS),
                block=None,
                block_owner=None,
                order=0,
                prefix=None,
                warnings=warnings,
            )
            if spec is None:
                continue
            if root_block is None:
                warnings.append(
                    f"{source_doc}:{raw.line}: 字段 {spec.oid} 位于所有块区域之外，"
                    f"且不是块根（B1–B6），已忽略"
                )
                continue
            if root_block in roots:
                warnings.append(f"{source_doc}:{raw.line}: 块根 {spec.oid} 重复定义，已忽略")
                continue
            roots[root_block] = spec
            every_field.append(spec)
            continue

        spec = _build_field(
            raw,
            source_doc=source_doc,
            table=owners.get(block, TableKey.ANALYSIS),
            block=block,
            block_owner=None,
            order=len(members[block]),
            prefix=block.value,
            warnings=warnings,
        )
        if spec is None:
            continue
        members[block].append(spec)
        every_field.append(spec)

    resolved_members: dict[Block, tuple[FieldSpec, ...]] = {}
    for block in Block:
        known = frozenset({block.value}) | {spec.oid for spec in members[block]}
        resolved_members[block] = _resolve_missing_parents(
            members[block], known_oids=known, source_doc=source_doc, warnings=warnings
        )
        if block not in present_blocks:
            warnings.append(
                f"{source_doc}: 未找到块 {block.value} 的 "
                f"`<!--{block.include_stem}-start-->` 区域标记"
            )
        elif not resolved_members[block]:
            warnings.append(f"{source_doc}: 块 {block.value} 的区域内没有任何字段")

    ordered_every = tuple(sorted(every_field, key=lambda spec: spec.source_line))
    return BlockDocument(
        members=resolved_members,
        roots=roots,
        fields=ordered_every,
        warnings=tuple(warnings),
    )



def _token_set(text: str) -> frozenset[str]:
    """把枚举型 `allowed` 文本切成小写、去尾点号的 token 集合。"""
    parts = re.split(r"[,;]", str(text or ""))
    return frozenset(part.strip().lower().rstrip(".") for part in parts if part.strip())


def _is_ratio_name(text: str) -> bool:
    """文本是否枚举了铅同位素比值名（命中 ≥2 个即认定）。"""
    lowered = text.lower()
    return sum(1 for name in LIA_RATIO_NAMES if name.lower() in lowered) >= 2


def _regex_test(pattern: re.Pattern[str]) -> Callable[[str], bool]:
    """构造"文本命中正则"的判定函数。"""
    return lambda text: pattern.search(text) is not None


_DATE_RE = re.compile(r"date\s+formatted\s+as\s+YYYY-MM-DD", re.IGNORECASE)
_EMAIL_RE = re.compile(r"mail\s+address", re.IGNORECASE)
_FILE_PATH_RE = re.compile(r"file\s+path", re.IGNORECASE)
_PID_RE = re.compile(r"persistent\s+identifier|is\s+valid\s+ror\s+id|pidinst", re.IGNORECASE)
_DECIMAL_RE = re.compile(r"decimal\s+number", re.IGNORECASE)
_INTEGER_RE = re.compile(r"\binteger\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\bnumber\b", re.IGNORECASE)
_URL_RE = re.compile(r"\burl\b", re.IGNORECASE)
_VOCAB_RE = re.compile(r"controlled\s+vocabulary", re.IGNORECASE)

#: 取值类型判定规则，按优先级排列（命中即取；同族内更具体的在前）。
_KIND_TESTS: tuple[tuple[ValueKind, Callable[[str], bool]], ...] = (
    (ValueKind.RATIO_NAME, _is_ratio_name),
    (ValueKind.RATIO_SOURCE, lambda text: _token_set(text) == {"original", "calculated"}),
    (ValueKind.GEOL_TYPE, lambda text: _token_set(text) == {"geological", "archaeological"}),
    (ValueKind.UNIT_AGE, lambda text: _token_set(text) == {"a", "ma"}),
    (ValueKind.YES_NO_UNCLEAR, lambda text: _token_set(text) == {"yes", "no", "unclear"}),
    (ValueKind.SIGMA, lambda text: _token_set(text) == {"1", "2", "3"}),
    (ValueKind.DATE, _regex_test(_DATE_RE)),
    (ValueKind.EMAIL, _regex_test(_EMAIL_RE)),
    (ValueKind.FILE_PATH, _regex_test(_FILE_PATH_RE)),
    (ValueKind.PID, _regex_test(_PID_RE)),
    (ValueKind.DECIMAL, _regex_test(_DECIMAL_RE)),
    (ValueKind.INTEGER, _regex_test(_INTEGER_RE)),
    (ValueKind.NUMBER, _regex_test(_NUMBER_RE)),
    (ValueKind.URL, _regex_test(_URL_RE)),
    (ValueKind.CONTROLLED_VOCAB, _regex_test(_VOCAB_RE)),
)

#: `MIXED` 判定用的族归类：数字类三种视为同一族，其余各自成族。
_KIND_FAMILIES: Mapping[ValueKind, str] = {
    ValueKind.DECIMAL: "number",
    ValueKind.INTEGER: "number",
    ValueKind.NUMBER: "number",
}


def infer_value_kind(allowed: str, definition: str = "") -> ValueKind:
    """按 `allowed` / `definition` 文本推断字段取值类型。

    `allowed` 非空且不是 `t.b.d.` 时只看 `allowed`；否则回退到 `definition`，让 `B1.4` /
    `B5.1` 这类没有 `allowed` 的 PID 组字段仍能识别。命中两个及以上互不相干的族（数字族
    `DECIMAL`/`INTEGER`/`NUMBER` 视为一族）时返回 `MIXED`。

    Args:
        allowed: ``Allowed values and other constraints`` 原文；definition: 定义原文。

    Returns:
        推断出的取值类型；无任何线索时为 `ValueKind.FREE_TEXT`。本函数不查词表；
        `profile.py` 富化时可能据 `vocab.py` 登记把 FREE_TEXT / MIXED 提升为 CONTROLLED_VOCAB。
    """
    text = str(allowed or "").strip()
    if _is_empty_constraint(text):
        text = str(definition or "").strip()
    if not text:
        return ValueKind.FREE_TEXT

    matched = [kind for kind, test in _KIND_TESTS if test(text)]
    if not matched:
        return ValueKind.FREE_TEXT
    families = {_KIND_FAMILIES.get(kind, kind.value) for kind in matched}
    if len(families) > 1:
        return ValueKind.MIXED
    return matched[0]



def read_profile_version(
    path: str | Path, *, fallback: str = PROFILE_VERSION_FALLBACK
) -> str:
    """读取档案版本号（`docs/changelog.md` 顶部第一个 ``## Version X.Y.Z``）。

    Args:
        path: changelog 路径；fallback: 读取失败时的兜底版本号。

    Returns:
        版本号字符串（如 ``"0.3.4"``）；文档缺失或不含版本行时返回 `fallback`。
    """
    doc_path = Path(path)
    try:
        lines = _read_lines(doc_path)
    except OSError as err:  # 缺失 / 是目录 / 无权限：版本号都退到兜底值，不阻断注册表
        logger.warning("档案 changelog 读取失败，版本号回退为 %s: %s", fallback, err)
        return fallback

    for line in lines:
        match = _VERSION_RE.match(line.strip())
        if match is not None:
            return match.group("version")

    logger.debug("changelog 中没有 `## Version X.Y.Z` 行，版本号回退为 %s", fallback)
    return fallback


__all__ = [
    # 常量
    "BLOCKS_DOC_RELATIVE",
    "CHANGELOG_RELATIVE",
    "DOCS_DIRNAME",
    "FIELD_HEADING_LEVELS",
    "META_KEYS",
    # 解析产物
    "BlockDocument",
    "InlineInclude",
    "TableDocument",
    # 解析入口
    "infer_value_kind",
    "parse_block_document",
    "parse_table_document",
    "read_profile_version",
    "table_doc_relative",
]
