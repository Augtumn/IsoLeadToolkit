"""TerraLID 档案注册表的组装与缓存入口。

`parse.py` 把 markdown 翻译成字段定义，本模块把它们组装成 `spec.Profile`：

1. 11 个模块文档 → `TableSpec`（模块自有字段 + 按文档顺序展开的内联块字段）；
2. `includes/metadata_blocks.md` → `Profile.blocks`（B1–B6 的成员字段定义）；
3. `docs/changelog.md` → 档案版本号（失败回退 `spec.PROFILE_VERSION_FALLBACK`）。

内联展开沿用 `parse.py` 给出的宿主关系：块成员被复制进宿主模块的字段序列，保留原
OID，`block_owner` 记录宿主（`A9.3` / `A14` 各有一份 B6），因此块字段的身份是
``(table, block_owner, oid)`` 三元组。表级 `order` 在这里重排为"在 `TableSpec.fields`
里的出现序"，`own_fields` 由同一批对象过滤得到，两条路径的 `order` 因此一致。

可选依赖（并行开发解耦）
------------------------

`vocab_id` 与 `label_zh` 由同伴模块填充，本模块用**函数内延迟导入**取用，模块缺席或
查询失败时回退（`vocab_id=None`、`label_zh=label_en`）并以 `logger.debug` 记录——
注册表本身不因可选模块缺席而不可用，但回退也不会静默发生：

- `vocab.vocab_id_for(spec) -> str | None`（`data/metadata_profile/vocab.py`）
- `labels.label_for(spec) -> str`（`data/metadata_profile/labels.py`）

**`value_kind` 的富化提升**：`parse.py` 只能从散文里推断取值类型，像 `A15.1`
（Allowed values 已穷举 `SK75, CR75, AJ84`，但档案没写 "controlled vocabulary"）只能落
`FREE_TEXT`，于是 `vocab.py` 里登记的年龄模型词表**注册了却不会被检查**——校验只在
`value_kind is CONTROLLED_VOCAB` 时查词表。因此富化时以 `vocab.py` 的登记为**唯一真源**：
`vocab_id_for()` 返回非 `None` 且原 `value_kind` 属于笼统类型（`FREE_TEXT` / `MIXED`）时
提升为 `CONTROLLED_VOCAB`；原值已是精确类型（`SIGMA` / `RATIO_NAME` / `RATIO_SOURCE` /
`GEOL_TYPE` / `UNIT_AGE` / `YES_NO_UNCLEAR` / `DECIMAL` / `DATE` / …）时保持不变。
`vocab` 缺席时 `value_kind` 保持解析层原值，一个字都不动。

缓存
----

`load_profile()` 带模块级**单槽缓存**（键为解析后的档案根路径）：同一次运行里重复调用
只解析一次，`root` 变更时旧条目失效，`refresh=True` 强制重建。缓存只缓存不可变的
`Profile`，不缓存中间文本。
"""
from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .parse import (
    BLOCKS_DOC_RELATIVE,
    CHANGELOG_RELATIVE,
    DOCS_DIRNAME,
    BlockDocument,
    TableDocument,
    parse_block_document,
    parse_table_document,
    read_profile_version,
)
from .spec import (
    Block,
    FieldSpec,
    Profile,
    TableKey,
    TableSpec,
    ValueKind,
)

logger = logging.getLogger(__name__)

#: 档案根相对仓库根的位置；`load_profile()` 缺省指到这里。
ARCHIVE_RELATIVE = "reference/metadata"

#: 缺省档案根：`data/metadata_profile/profile.py` 上溯三级即仓库根，再拼档案相对路径。
DEFAULT_ROOT: Path = Path(__file__).parents[2] / ARCHIVE_RELATIVE

#: `root` 路径 → `Profile` 的单槽缓存（键为 `Path.resolve()` 后的字符串）。
_PROFILE_CACHE: dict[str, Profile] = {}

#: 词表登记可以提升的"笼统"取值类型（精确类型不因登记而被改写）。
_VAGUE_VALUE_KINDS: frozenset[ValueKind] = frozenset(
    {ValueKind.FREE_TEXT, ValueKind.MIXED}
)


# ──────────────────────────────────────────────────────────────────────────────
# 公开入口
# ──────────────────────────────────────────────────────────────────────────────


def resolve_root(root: str | Path | None = None) -> Path:
    """把档案根参数归一为绝对路径。

    Args:
        root: 档案根（含 `docs/` 与 `includes/`）；`None` 表示仓库内的
            `reference/metadata`。

    Returns:
        归一化后的路径；`resolve()` 失败时退回未解析路径（例如盘符离线）。
    """
    candidate = DEFAULT_ROOT if root is None else Path(root).expanduser()
    try:
        return candidate.resolve()
    except OSError:  # 路径不可解析（网络盘/权限）时保持原样，后续按缺文件报错
        return candidate


def load_profile(root: str | Path | None = None, *, refresh: bool = False) -> Profile:
    """读取（并在需要时解析）TerraLID 档案注册表。

    Args:
        root: 档案根目录；缺省为仓库内的 `reference/metadata`。
        refresh: 为 `True` 时忽略已有缓存强制重建。

    Returns:
        组装好的 `Profile`（带模块级缓存）。

    Raises:
        FileNotFoundError: 档案根下缺少 `docs/` 目录、模块文档或块文档。
    """
    resolved = resolve_root(root)
    cache_key = str(resolved)
    if refresh or cache_key not in _PROFILE_CACHE:
        _PROFILE_CACHE.clear()  # 单槽缓存：root 变更即失效，避免多份档案互相污染
        _PROFILE_CACHE[cache_key] = build_profile(resolved)
    return _PROFILE_CACHE[cache_key]


def clear_profile_cache() -> None:
    """清空 `load_profile()` 的模块级缓存（测试与生成脚本用）。"""
    _PROFILE_CACHE.clear()


def build_profile(root: str | Path | None = None) -> Profile:
    """解析并组装注册表，不使用缓存。

    Args:
        root: 档案根目录；缺省为仓库内的 `reference/metadata`。

    Returns:
        `Profile`（11 张表、B1–B6 块定义、解析告警）。

    Raises:
        FileNotFoundError: 档案根下缺少 `docs/` 目录、某个模块文档或块文档。
            文件存在但内容为空（`metadata_by-products.md`）只记 warning，不报错。
    """
    root_path = Path(root) if root is not None else DEFAULT_ROOT
    docs_dir = root_path / DOCS_DIRNAME
    blocks_path = root_path / BLOCKS_DOC_RELATIVE
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"TerraLID 档案 docs 目录不存在：{docs_dir}")
    if not blocks_path.is_file():
        raise FileNotFoundError(f"TerraLID 档案块文档不存在：{blocks_path}")

    documents = tuple(
        parse_table_document(docs_dir / table.doc_name, table) for table in TableKey
    )
    blocks_doc = parse_block_document(
        blocks_path, table_for_block=_first_inliner(documents)
    )
    version = read_profile_version(root_path / CHANGELOG_RELATIVE)

    vocab_lookup = _load_vocab_lookup()
    label_lookup = _load_label_lookup()

    tables = tuple(
        _build_table_spec(document, blocks_doc, vocab_lookup, label_lookup)
        for document in documents
    )
    blocks: dict[Block, tuple[FieldSpec, ...]] = {
        block: tuple(
            _enrich(spec, vocab_lookup, label_lookup)
            for spec in blocks_doc.members.get(block, ())
        )
        for block in Block
    }

    warnings = tuple(
        warning for document in documents for warning in document.warnings
    ) + tuple(blocks_doc.warnings)

    logger.info(
        "TerraLID 档案已解析：version=%s tables=%d fields=%d blocks=%d warnings=%d",
        version,
        len(tables),
        sum(len(table.fields) for table in tables),
        len(blocks),
        len(warnings),
    )
    return Profile(version=version, tables=tables, blocks=blocks, warnings=warnings)


# ──────────────────────────────────────────────────────────────────────────────
# 组装
# ──────────────────────────────────────────────────────────────────────────────


def _first_inliner(documents: tuple[TableDocument, ...]) -> dict[Block, TableKey]:
    """统计"块 → 首个内联它的模块"。

    块定义字段不属于任何模块，`FieldSpec.table` 只能取一个确定值：按模块文档顺序
    第一个内联该块的模块（B1/B2/B4→objects、B3/B5→sites、B6→analyses）。

    Args:
        documents: 全部模块文档解析结果。

    Returns:
        块 → 模块键的映射。
    """
    found: dict[Block, TableKey] = {}
    for document in documents:
        for inline in document.inlines:
            found.setdefault(inline.block, document.table)
    return found


def _build_table_spec(
    document: TableDocument,
    blocks_doc: BlockDocument,
    vocab_lookup: Callable[[FieldSpec], str | None] | None,
    label_lookup: Callable[[FieldSpec], str] | None,
) -> TableSpec:
    """把一份模块文档组装成 `TableSpec`（含内联块展开）。

    内联是按"文档位置"展开的：宿主字段之后紧跟该 include 带来的块成员，因此
    `TableSpec.fields` 的顺序与 markdown 的阅读顺序一致。

    Args:
        document: 模块文档解析结果。
        blocks_doc: 块文档解析结果（提供块成员定义）。
        vocab_lookup: `vocab.vocab_id_for`；不可用时 `None`。
        label_lookup: `labels.label_for`；不可用时 `None`。

    Returns:
        该模块的表定义。
    """
    included: dict[str, list[Block]] = {}
    for inline in document.inlines:
        if inline.owner_oid is not None:
            included.setdefault(inline.owner_oid, []).append(inline.block)

    fields: list[FieldSpec] = []
    for own in document.own_fields:
        enriched_own = _enrich(own, vocab_lookup, label_lookup)
        fields.append(replace(enriched_own, order=len(fields)))
        for block in included.get(own.oid, ()):
            for member in blocks_doc.members.get(block, ()):
                fields.append(
                    replace(
                        _enrich(member, vocab_lookup, label_lookup),
                        table=document.table,
                        block=block,
                        block_owner=own.oid,
                        order=len(fields),
                    )
                )

    return TableSpec(
        key=document.table,
        own_fields=tuple(spec for spec in fields if spec.block is None),
        inlined_blocks=tuple(inline.block for inline in document.inlines),
        fields=tuple(fields),
    )


# ──────────────────────────────────────────────────────────────────────────────
# 可选依赖：vocab / labels
# ──────────────────────────────────────────────────────────────────────────────


def _load_vocab_lookup() -> Callable[[FieldSpec], str | None] | None:
    """延迟导入 `vocab.vocab_id_for`；模块缺席或当前不可导入时回退为 `None`。

    依赖缺席（本包并行开发中）属于预期情况，记 debug；模块存在但导入失败（半成品、
    语法错误）属于异常情况，记 warning —— 两种情况下注册表都必须仍然可用。

    Returns:
        `vocab_id_for`；不可用时返回 `None`。
    """
    try:
        from .vocab import vocab_id_for
    except ImportError as err:
        logger.debug("vocab 模块不可用，vocab_id 一律回退为 None: %s", err)
        return None
    except Exception as err:  # 可选模块的导入缺陷不应让整份注册表不可用
        logger.warning("vocab 模块导入失败，vocab_id 一律回退为 None: %s", err)
        return None
    return vocab_id_for


def _load_label_lookup() -> Callable[[FieldSpec], str] | None:
    """延迟导入 `labels.label_for`；模块缺席或当前不可导入时回退为 `None`。

    Returns:
        `label_for`；不可用时返回 `None`（`label_zh` 回退为 `label_en`）。
    """
    try:
        from .labels import label_for
    except ImportError as err:
        logger.debug("labels 模块不可用，label_zh 一律回退为 label_en: %s", err)
        return None
    except Exception as err:  # 同上：可选模块的导入缺陷不应让注册表不可用
        logger.warning("labels 模块导入失败，label_zh 一律回退为 label_en: %s", err)
        return None
    return label_for


def _lookup_vocab_id(
    lookup: Callable[[FieldSpec], str | None] | None, spec: FieldSpec
) -> str | None:
    """查询受控词表 ID，失败即回退为 `None`。

    Args:
        lookup: `vocab.vocab_id_for`；依赖缺席时为 `None`。
        spec: 待查询字段。

    Returns:
        词表 ID；依赖缺席、查询抛错或结果为空时返回 `None`。
    """
    if lookup is None:
        return None
    try:
        value = lookup(spec)
    except Exception as err:  # 可选依赖的实现缺陷不应让整份注册表不可用，故宽捕获并记录
        logger.debug("字段 %s 的 vocab_id 查询失败，回退为 None: %s", spec.oid, err)
        return None
    return value or None


def _lookup_label_zh(
    lookup: Callable[[FieldSpec], str] | None, spec: FieldSpec
) -> str:
    """查询字段中文标签，失败即回退为 `label_en`。

    Args:
        lookup: `labels.label_for`；依赖缺席时为 `None`。
        spec: 待查询字段。

    Returns:
        中文标签；依赖缺席、查询抛错或结果为空时返回 `label_en`。
    """
    fallback = spec.label_zh or spec.label_en
    if lookup is None:
        return fallback
    try:
        value = lookup(spec)
    except Exception as err:  # 同上：单个字段的标签缺失不应让注册表不可用
        logger.debug("字段 %s 的 label_zh 查询失败，回退为 %r: %s", spec.oid, fallback, err)
        return fallback
    return value or fallback


def _enrich(
    spec: FieldSpec,
    vocab_lookup: Callable[[FieldSpec], str | None] | None,
    label_lookup: Callable[[FieldSpec], str] | None,
) -> FieldSpec:
    """填充字段的 `vocab_id` / `label_zh`，并按词表登记提升 `value_kind`。

    提升规则：`vocab_id_for(spec)` 返回非 `None` 且解析层的 `value_kind` 属于笼统类型
    （`FREE_TEXT` / `MIXED`）时改为 `CONTROLLED_VOCAB`；解析层已给出精确类型
    （`SIGMA` / `RATIO_NAME` / `GEOL_TYPE` / …）时保持原值。词表查询用的是**提升前**的
    `spec`，因此重复富化同一字段结果稳定；`vocab` 缺席时不改写 `value_kind`。
    "哪些字段有受控词表"以 `vocab.py` 的登记为唯一真源，解析层不重复维护一份。

    Args:
        spec: 解析得到的字段定义（`vocab_id=None`、`label_zh=""`）。
        vocab_lookup: `vocab.vocab_id_for`；不可用时 `None`。
        label_lookup: `labels.label_for`；不可用时 `None`。

    Returns:
        填充后的新 `FieldSpec`（`FieldSpec` frozen，故用 `dataclasses.replace`）。
    """
    vocab_id = _lookup_vocab_id(vocab_lookup, spec)
    value_kind = spec.value_kind
    if vocab_id is not None and value_kind in _VAGUE_VALUE_KINDS:
        value_kind = ValueKind.CONTROLLED_VOCAB
    return replace(
        spec,
        vocab_id=vocab_id,
        label_zh=_lookup_label_zh(label_lookup, spec),
        value_kind=value_kind,
    )


__all__ = [
    "ARCHIVE_RELATIVE",
    "DEFAULT_ROOT",
    "build_profile",
    "clear_profile_cache",
    "load_profile",
    "resolve_root",
]
