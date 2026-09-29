"""铅同位素比值的推导与不确定度换算。

TerraLID 档案把"补齐比值"与"换算不确定度"明确交给系统（`reference/metadata`）：

- **A14**：*Mass-bias corrected lead isotope ratios and analytical uncertainty. The
  TerraLID system will calculate all ratios not reported in the original publication.*
- **B6.6**：*Value of relative analytical uncertainty for the lead isotope ratio in per
  cent (%). If provided, the TerraLID system will calculate the corresponding absolute
  values.*
- **B6.5**：绝对不确定度由 *data provider, TerraLID system* 双方提供。

本模块提供两件事：

1. :func:`derive_all_ratios` —— 由三个实测主比值（``206Pb/204Pb`` / ``207Pb/204Pb`` /
   ``208Pb/204Pb``）补齐 ``spec.LIA_RATIO_NAMES`` 里的全部 8 个比值，并做一阶相对误差传播；
2. :func:`absolute_from_relative` / :func:`relative_from_absolute` —— B6.5 ↔ B6.6 换算。

推导走 `spec.derived_ratio_expression()` 给出的**因子链**（``∏ (N_mass/N_204) ** exp``），
不硬编码五个除法：档案若新增比值或更换基准质量数，本模块自动跟随。

设计约束：不得导入 PyQt5 / pandas / openpyxl，不做文件 IO，无全局可变状态。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Mapping

from . import spec

logger = logging.getLogger(__name__)

#: B6.7 ``Source`` 的两个取值；与 ``spec.RATIO_SOURCES`` 一致（有测试守住）。
SOURCE_ORIGINAL: str = "original"
SOURCE_CALCULATED: str = "calculated"

#: 数值不可用（缺值 / 非有限值）时的展示占位符。
NOT_AVAILABLE: str = "n/a"

#: 相对不确定度以百分数表示，换算需要 /100 或 *100。
_PERCENT = 100.0


@dataclass(frozen=True)
class RatioValue:
    """一个铅同位素比值及其不确定度（A14 / B6 的聚合结果）。

    Attributes:
        name: 比值名，取自 ``spec.LIA_RATIO_NAMES``。
        value: 比值数值。
        uncertainty_absolute: B6.5 绝对不确定度；未知为 ``None``。
        uncertainty_relative_percent: B6.6 相对不确定度（百分数）；未知为 ``None``。
        uncertainty_type: B6.3 不确定度类型（档案为受控词表）。本模块不产生该值，
            留待调用方按原始记录回填；缺省 ``None``。
        sigma: B6.4 置信水平（1 / 2 / 3）；未知为 ``None``。
        source: B6.7，``"original"``（原文报告）或 ``"calculated"``（系统推导）。
    """

    name: str
    value: float
    uncertainty_absolute: float | None = None
    uncertainty_relative_percent: float | None = None
    uncertainty_type: str | None = None
    sigma: int | None = None
    source: str = SOURCE_ORIGINAL

    @property
    def is_primary(self) -> bool:
        """是否为实测主比值（``spec.PRIMARY_LIA_RATIO_NAMES`` 之一）。"""
        return self.name in spec.PRIMARY_LIA_RATIO_NAMES

    @property
    def is_calculated(self) -> bool:
        """是否由系统推导得到。"""
        return self.source == SOURCE_CALCULATED


def derive_all_ratios(
    measured: Mapping[str, float],
    *,
    uncertainties: Mapping[str, float] | None = None,
    sigma: int | None = None,
) -> dict[str, RatioValue]:
    """由实测比值补齐档案要求报告的全部铅同位素比值。

    档案允许原文报告 8 个比值中的任意一个（``206Pb/204Pb``、``207Pb/206Pb`` 等），
    系统只补"未被报告"的那些。本函数因此分两种情形：

    - ``measured`` 含全部三个主比值（``206Pb/204Pb`` / ``207Pb/204Pb`` / ``208Pb/204Pb``）时，
      返回 8 个比值：实测的 ``source="original"``，其余由因子链推导为
      ``source="calculated"``；原文报告的派生比值优先（系统不覆盖实测值）。
    - 缺任一主比值时**不抛异常**（录入是增量过程），只返回实测到的比值，并记
      ``logger.warning`` 说明缺哪个。

    **不确定度传播（近似）**：对 ``r = ∏ p_i ** e_i``（``p_i`` 为主比值，``e_i = ±1``），
    一阶相对误差传播给出 ``(σ_r/r)² = Σ (e_i · σ_{p_i}/p_i)²``，即把各主比值的相对
    不确定度按平方和相加。这里**忽略比值之间的协方差**，因为档案（B6.3/B6.5/B6.6）
    只允许逐比值报告类型、σ 与数值，没有任何协方差/相关系数字段可供使用；测量上
    206/204、207/204、208/204 由同一次质谱测量得到、确实存在相关性，因此本函数给出的是
    在档案信息量下可做到的最佳近似（通常略偏保守或略偏乐观，取决于相关方向）。

    **缺口不确定度不等于 0**：任一参与推导的主比值没有给出不确定度时，该派生值的不确定度为
    ``None``（未知），**不**按 0 参与平方和 —— 把未知当 0 会系统性**低估**派生比值的不确定度，
    而低估不确定度会误导地球化学解释。若某一侧确实为 0，请显式传 ``0.0``：两种情况结果可区分。

    Args:
        measured: 比值名 → 数值。至少应含 ``spec.PRIMARY_LIA_RATIO_NAMES``；数值可以是
            ``int`` / ``float``，也容忍 Excel 读出的数字字符串。未知比值名会被忽略并记警告。
        uncertainties: 主比值的**绝对**不确定度（与 ``sigma`` 同级）。
        sigma: B6.4 置信水平，写入所有返回项的 ``sigma`` 字段；非法值记警告后原样保留，
            交由 `validate.py` 的 σ 规则报告。

    Returns:
        比值名 → :class:`RatioValue`；键序与 ``spec.LIA_RATIO_NAMES`` 一致（先实测后推导）。
    """
    values, missing_primaries, unusable = _collect_measured(measured)
    sigma_value = _coerce_sigma(sigma)

    result: dict[str, RatioValue] = {}
    for name in spec.LIA_RATIO_NAMES:
        number = values.get(name)
        if number is None:
            continue
        result[name] = _reported_ratio(name, number, uncertainties, sigma_value)

    if missing_primaries:
        logger.warning(
            "Lead isotope ratios not derived: primary ratio(s) %s are missing or unusable "
            "(unusable values: %s); returning the %d reported ratio(s) only",
            ", ".join(missing_primaries),
            ", ".join(unusable) if unusable else "none",
            len(result),
        )
        return result

    for name in spec.LIA_RATIO_NAMES:
        if name in result or name in spec.PRIMARY_LIA_RATIO_NAMES:
            continue
        result[name] = _calculated_ratio(name, values, uncertainties, sigma_value)
    return result


def absolute_from_relative(value: float, relative_percent: float) -> float:
    """按 B6.6 由相对不确定度（%）换算绝对不确定度。

    Args:
        value: 比值数值。
        relative_percent: 相对不确定度，百分数（档案示例 ``0.1`` 表示 0.1%）。

    Returns:
        绝对不确定度 ``value * relative_percent / 100``。
    """
    return value * relative_percent / _PERCENT


def relative_from_absolute(value: float, absolute: float) -> float | None:
    """按 B6.5/B6.6 由绝对不确定度换算相对不确定度（%）。

    Args:
        value: 比值数值。
        absolute: 绝对不确定度（与 ``sigma`` 同级）。

    Returns:
        相对不确定度百分数；``value`` 为 0 或任一参数非有限值时返回 ``None`` 并记
        ``logger.warning`` —— 不用 ``EPSILON`` 掩盖除零，那会把 0 值伪造成一个
        看似正常的相对不确定度。
    """
    if not math.isfinite(value) or not math.isfinite(absolute):
        logger.warning(
            "Cannot express absolute uncertainty %r as a relative value for ratio value %r: "
            "not finite",
            absolute,
            value,
        )
        return None
    if value == 0:
        logger.warning(
            "Cannot compute relative uncertainty: ratio value is 0 (absolute uncertainty %r)",
            absolute,
        )
        return None
    return absolute / value * _PERCENT


def primary_from_derived(name: str) -> tuple[str, ...]:
    """给出某比值依赖哪些实测主比值。

    Args:
        name: ``spec.LIA_RATIO_NAMES`` 中的比值名。

    Returns:
        该比值因子链上出现的主比值名（按因子顺序去重）。对主比值本身返回 ``(name,)``；
        例如 ``204Pb/206Pb`` 依赖 ``("206Pb/204Pb",)``，``207Pb/208Pb`` 依赖
        ``("207Pb/204Pb", "208Pb/204Pb")``。

    Raises:
        KeyError: ``name`` 不在 ``spec.LIA_RATIO_MASSES`` 中。
    """
    primaries: list[str] = []
    for mass, _exponent in spec.derived_ratio_expression(name):
        primary = spec.primary_ratio_for_mass(mass)
        if primary is None:
            logger.debug("Ratio %s has no primary source for mass %d", name, mass)
            continue
        if primary not in primaries:
            primaries.append(primary)
    return tuple(primaries)


def format_ratio(value: float, *, decimals: int = 5) -> str:
    """格式化比值展示（档案示例 ``18.59123`` 为 5 位小数）。

    Args:
        value: 比值数值。
        decimals: 小数位数。

    Returns:
        定长小数字符串；非有限值返回 :data:`NOT_AVAILABLE` 并记 ``logger.debug``。
    """
    if not _is_finite(value):
        logger.debug("Ratio value %r is not finite; formatting as %s", value, NOT_AVAILABLE)
        return NOT_AVAILABLE
    return f"{value:.{decimals}f}"


def format_uncertainty(value: float) -> str:
    """格式化不确定度展示（档案示例 ``0.00008``）。

    量级落在 ``[1e-6, 1e6)`` 时用 6 位小数并去掉无意义的尾随零，否则用科学计数法，
    避免 ``0.000000`` 或超长数字串。

    Args:
        value: 不确定度数值。

    Returns:
        格式化字符串；非有限值返回 :data:`NOT_AVAILABLE` 并记 ``logger.debug``。
    """
    if not _is_finite(value):
        logger.debug("Uncertainty %r is not finite; formatting as %s", value, NOT_AVAILABLE)
        return NOT_AVAILABLE
    magnitude = abs(value)
    if value != 0 and (magnitude < _SMALL_UNCERTAINTY or magnitude >= _LARGE_UNCERTAINTY):
        return f"{value:.5e}"
    text = f"{value:.6f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


# ──────────────────────────────────────────────────────────────────────────────
# 内部实现
# ──────────────────────────────────────────────────────────────────────────────

#: 小于该量级改用科学计数法。
_SMALL_UNCERTAINTY = 1e-6

#: 不小于该量级改用科学计数法。
_LARGE_UNCERTAINTY = 1e6


def _is_finite(value: object) -> bool:
    """判断 ``value`` 是否为有限实数（``bool`` 不算）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _coerce_float(value: object) -> float | None:
    """安全地把输入转成有限浮点数；失败记 ``logger.debug`` 并返回 ``None``。

    禁止裸 ``float()``/``int()``（开发规范 §8.1）：Excel 与手工录入都可能给出空串、
    ``"t.b.d."`` 之类的内容，转换必须被包裹。
    """
    if isinstance(value, bool):
        return None
    try:
        candidate = float(value)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.debug("Ignoring non-numeric value %r: %s", value, err)
        return None
    if not math.isfinite(candidate):
        logger.debug("Ignoring non-finite value %r", value)
        return None
    return candidate


def _coerce_sigma(sigma: object) -> int | None:
    """安全地把 σ 置信水平转成整数；非法值记警告后返回 ``None``。"""
    if sigma is None or isinstance(sigma, bool):
        return None
    if isinstance(sigma, float) and not sigma.is_integer():
        logger.warning("Ignoring non-integral sigma level %r", sigma)
        return None
    try:
        parsed = int(sigma)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.warning("Ignoring invalid sigma level %r: %s", sigma, err)
        return None
    if parsed not in spec.SIGMA_LEVELS:
        logger.warning(
            "Sigma level %r is not one of %s; keeping the reported value for validate.py to flag",
            parsed,
            spec.SIGMA_LEVELS,
        )
    return parsed


def _collect_measured(
    measured: Mapping[str, float],
) -> tuple[dict[str, float], list[str], list[str]]:
    """收集可用的实测比值。

    Returns:
        ``(比值名 → 数值, 缺失或不可用的主比值, 不可用的比值名)``。
    """
    values: dict[str, float] = {}
    unusable: list[str] = []
    for name in spec.LIA_RATIO_NAMES:
        if name not in measured:
            continue
        number = _coerce_float(measured[name])
        if number is None:
            unusable.append(name)
            continue
        values[name] = number
    unknown = sorted(str(key) for key in measured if key not in spec.LIA_RATIO_MASSES)
    if unknown:
        logger.warning("Ignoring unknown lead isotope ratio name(s): %s", ", ".join(unknown))
    missing = [name for name in spec.PRIMARY_LIA_RATIO_NAMES if name not in values]
    return values, missing, unusable


def _reported_ratio(
    name: str,
    value: float,
    uncertainties: Mapping[str, float] | None,
    sigma: int | None,
) -> RatioValue:
    """构造一个实测比值的 :class:`RatioValue`（含 B6.5 ↔ B6.6 换算）。"""
    absolute = _reported_uncertainty(name, uncertainties)
    relative = relative_from_absolute(value, absolute) if absolute is not None else None
    return RatioValue(
        name=name,
        value=value,
        uncertainty_absolute=absolute,
        uncertainty_relative_percent=relative,
        sigma=sigma,
        source=SOURCE_ORIGINAL,
    )


def _reported_uncertainty(
    name: str, uncertainties: Mapping[str, float] | None
) -> float | None:
    """取某比值的绝对不确定度；缺失或为负时返回 ``None``。"""
    if not uncertainties or name not in uncertainties:
        return None
    absolute = _coerce_float(uncertainties[name])
    if absolute is None:
        logger.debug("No usable absolute uncertainty for ratio %s", name)
        return None
    if absolute < 0:
        logger.warning("Negative absolute uncertainty %r for ratio %s; ignoring", absolute, name)
        return None
    return absolute


def _calculated_ratio(
    name: str,
    values: Mapping[str, float],
    uncertainties: Mapping[str, float] | None,
    sigma: int | None,
) -> RatioValue:
    """按因子链推导一个比值，并传播不确定度。"""
    factors = spec.derived_ratio_expression(name)
    value = _compose(factors, values)
    absolute = _propagate(factors, name, value, values, uncertainties)
    relative = relative_from_absolute(value, absolute) if absolute is not None else None
    return RatioValue(
        name=name,
        value=value,
        uncertainty_absolute=absolute,
        uncertainty_relative_percent=relative,
        sigma=sigma,
        source=SOURCE_CALCULATED,
    )


def _compose(factors: tuple[tuple[int, int], ...], values: Mapping[str, float]) -> float:
    """计算 ``∏ (N_mass / N_204) ** exponent``。"""
    result = 1.0
    for mass, exponent in factors:
        primary = spec.primary_ratio_for_mass(mass)
        if primary is None:
            logger.debug("Mass %d is the reference mass; treated as 1.0", mass)
            continue
        base = values.get(primary)
        if base is None:
            logger.debug("Primary ratio %s is unavailable while composing a derived ratio", primary)
            continue
        result *= base**exponent
    return result


def _propagate(
    factors: tuple[tuple[int, int], ...],
    name: str,
    value: float,
    values: Mapping[str, float],
    uncertainties: Mapping[str, float] | None,
) -> float | None:
    """一阶相对误差传播：``(σ_r/r)² = Σ (e_i · σ_{p_i}/p_i)²``。

    任一主比值缺绝对不确定度（或该主比值为 0，无法构成相对量）时返回 ``None`` 并记
    ``logger.debug`` —— 缺什么就不报什么，不猜。
    """
    squared = 0.0
    absent: list[str] = []
    for mass, exponent in factors:
        primary = spec.primary_ratio_for_mass(mass)
        if primary is None:
            continue
        base = values.get(primary)
        absolute = _reported_uncertainty(primary, uncertainties)
        if base is None or base == 0 or absolute is None:
            absent.append(primary)
            continue
        squared += (exponent * (absolute / abs(base))) ** 2
    if absent:
        logger.debug(
            "No propagated uncertainty for derived ratio %s: missing/zero absolute uncertainty "
            "for %s",
            name,
            ", ".join(dict.fromkeys(absent)),
        )
        return None
    relative_fraction = math.sqrt(squared)
    return value * relative_fraction


__all__ = [
    "NOT_AVAILABLE",
    "SOURCE_CALCULATED",
    "SOURCE_ORIGINAL",
    "RatioValue",
    "absolute_from_relative",
    "derive_all_ratios",
    "format_ratio",
    "format_uncertainty",
    "primary_from_derived",
    "relative_from_absolute",
]
