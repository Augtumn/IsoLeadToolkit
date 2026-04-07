# 开发规划（进行中）

本文件仅保留尚未完成或正在推进的事项。历史已完成条目不再重复记录。

## 阶段进展（2026-04-07 · StateStore 第一百六十七批）

- P2-3（数值稳定性统一）继续收敛 ternary 边界估计中的近零判定：
    - `visualization/plotting/ternary.py` 将 `_robust_bounds` 的 `trim_ratio <= 0.0` 判定改为复用 `_TERNARY_LIMIT_EPSILON`，统一 tiny trim_ratio 的阈值语义。
- 回归测试新增：
    - `tests/test_plotting_ternary_helpers.py` 新增 1 个测试，覆盖超小 `trim_ratio`（`1e-12`）按“无裁剪”路径返回原始 min/max 的行为。

## 阶段进展（2026-04-07 · StateStore 第一百六十六批）

- P2-3（数值稳定性统一）继续收敛 legend 偏移零值判定：
    - `visualization/plotting/styling/legend.py` 新增 `_LEGEND_OFFSET_EPSILON` 与 `_is_zero_offset`，将 `_legend_layout_config` 中 `dx/dy == 0.0` 改为统一近零判断。
- 回归测试新增：
    - `tests/test_legend_styling_helpers.py` 新增 1 个测试，覆盖 near-zero 偏移输入下 `bbox` 保持 `None` 的稳定路径。

## 阶段进展（2026-04-07 · StateStore 第一百六十五批）

- P2-3（数值稳定性统一）继续收敛 V1V2 预设中的地幔参数字面量：
    - `data/geochemistry/engine.py` 新增 `MU_V1V2_DEFAULT`、`KAPPA_V1V2_DEFAULT`、`OMEGA_V1V2_DEFAULT`，并统一 `V1V2 (Geokit)` 与 `V1V2 (Zhu 1993)` 的 `mu_M/omega_M` 预设值来源。
- 回归测试新增：
    - `tests/test_geochemistry_engine.py` 新增 1 个测试，覆盖两个 V1V2 预设对共享常量的绑定，以及 `OMEGA_V1V2_DEFAULT = MU_V1V2_DEFAULT * KAPPA_V1V2_DEFAULT` 的关系。

## 阶段进展（2026-04-07 · StateStore 第一百六十四批）

- P2-3（数值稳定性统一）继续收敛 geochemistry 预设模型中的参数字面量：
    - `data/geochemistry/engine.py` 将 `PRESET_MODELS` 中 `V1V2 (Geokit)` 的时间参数 `T1/T2/Tsec` 改为 `T_EARTH_1ST`、`T_EARTH_CANON`、`T_SK_STAGE2`。
    - 同时将 `Stacey & Kramers (2nd Stage)` 的 `mu_M/omega_M` 字面量改为 `MU_M_DEFAULT/OMEGA_M_DEFAULT`。
- 回归测试新增：
    - `tests/test_geochemistry_engine.py` 新增 2 个测试，覆盖：
        - Geokit 预设时间参数与命名常量绑定；
        - Stacey & Kramers 二阶段预设地幔参数与命名常量绑定。

## 阶段进展（2026-04-07 · StateStore 第一百六十三批）

- P2-3（数值稳定性统一）继续收敛 delta 模块 V1V2 默认参数：
    - `data/geochemistry/delta.py` 将 `calculate_v1v2` 的默认参数 `a/b/c` 从字面量替换为命名常量 `REGRESSION_A/B/C`。
- 回归测试新增：
    - `tests/test_geochemistry_delta_helpers.py` 新增 1 个测试，覆盖 `calculate_v1v2` 默认参数路径与显式传入 `REGRESSION_A/B/C` 路径结果一致。

## 阶段进展（2026-04-07 · StateStore 第一百六十二批）

- P2-3（数值稳定性统一）继续收敛 geochemistry 中 E1/E2 回退默认值：
    - `data/geochemistry/engine.py` 与 `data/geochemistry/delta.py` 将 `params.get('E1', 0.0)` / `params.get('E2', 0.0)` 改为命名常量 `E1_DEFAULT` / `E2_DEFAULT`。
- 回归测试新增/增强：
    - `tests/test_geochemistry_engine.py` 新增 1 个测试，覆盖 `calculate_modelcurve` 在缺失 `E1/E2` 时使用命名常量回退。
    - `tests/test_geochemistry_delta_helpers.py` 新增 1 个测试，覆盖 `calculate_deltas` 缺失 `E1/E2` 时与显式常量参数路径结果一致。

## 阶段进展（2026-04-07 · StateStore 第一百六十一批）

- P2-3（数值稳定性统一）继续收敛 geochemistry engine 的地幔参数回退默认值：
    - `data/geochemistry/engine.py` 将 `_update_derived_params` 与 `calculate_modelcurve` 中 `mu_M/omega_M` 的回退字面量替换为 `MU_M_DEFAULT`、`OMEGA_M_DEFAULT` 命名常量。
- 回归测试新增：
    - `tests/test_geochemistry_engine.py` 新增 2 个测试，覆盖：
        - 缺失 `mu_M` 时 `_update_derived_params` 使用命名常量回退；
        - 缺失 `mu_M/omega_M` 时 `calculate_modelcurve` 与显式传入命名常量结果一致。

## 阶段进展（2026-04-07 · StateStore 第一百六十批）

- P2-3（数值稳定性统一）继续收敛 geochemistry engine 演化参数零值判断：
    - `data/geochemistry/engine.py` 新增 `_is_zero_like`，并将 `_exp_evolution_term` 中重复的 `E == 0 or E == 0.0` 改为统一零值判定 helper。
- 回归测试新增：
    - `tests/test_geochemistry_engine.py` 新增 3 个测试，覆盖：
        - `_is_zero_like` 对零值输入的判定；
        - `_exp_evolution_term` 在 `E=0` 时退化为纯指数项；
        - `_exp_evolution_term` 在非零 `E` 时按演化因子公式计算。

## 阶段进展（2026-04-07 · StateStore 第一百五十九批）

- P2-3（数值稳定性统一）收敛 isochron 模块浮点零比较：
    - `data/geochemistry/isochron.py` 新增 `_is_near_zero`，并将 `calculate_paleoisochron_line` 与 `calculate_pbpb_age_from_ratio` 中直接 `== 0` / `==` 判定改为统一近零判断。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - `_is_near_zero` 相对 `_SOURCE_DEN_FLOOR` 的阈值行为；
        - paleoisochron 在近等时刻（`e8T≈e8t`）场景下返回 `None` 的保护路径。

## 阶段进展（2026-04-07 · StateStore 第一百五十八批）

- P2-3（数值稳定性统一）推进 GeoPanel 参数控件配置常量收敛：
    - `ui/panels/geo_panel.py` 新增 `_GEO_PARAM_DEFAULT_DECIMALS`、`_GEO_PARAM_SCIENTIFIC_DECIMALS`、`_GEO_PARAM_DEFAULT_STEP`，并移除 `_add_geo_param` 中冗余 `setDecimals` 调用，统一 scientific/非 scientific 路径配置。
- 回归测试增强：
    - `tests/test_geo_panel_helpers.py` 扩展 2 个路径断言，覆盖：
        - scientific 模式下步长与精度常量；
        - 非 scientific 模式下默认步长与精度常量。

## 阶段进展（2026-04-07 · StateStore 第一百五十七批）

- P2-3（数值稳定性统一）继续收敛 Pb-Pb 年龄求解区间常量：
    - `data/geochemistry/isochron.py` 新增 `_PBPB_SOLVER_BOUNDS`，替换 `calculate_pbpb_age_from_ratio` 中内联 `(1e6, 10e9)`。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 1 个测试，覆盖 `calculate_pbpb_age_from_ratio` 对 `_PBPB_SOLVER_BOUNDS` 的透传。

## 阶段进展（2026-04-07 · StateStore 第一百五十六批）

- P2-3（数值稳定性统一）继续收敛 age 求解区间常量：
    - `data/geochemistry/age.py` 新增 `_AGE_SOLVER_BOUNDS`，统一替换 `calculate_single_stage_age` 与 `calculate_two_stage_age` 中四处重复 `(-4700e6, 4700e6)` 字面量。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖单阶段与两阶段年龄计算对 `_AGE_SOLVER_BOUNDS` 的透传。

## 阶段进展（2026-04-06 · StateStore 第一百五十五批）

- P2-3（数值稳定性统一）继续收敛 age 模块标量分母保护：
    - `data/geochemistry/age.py` 新增 `_safe_scalar_denominator`，统一替换 `calculate_single_stage_age` 与 `calculate_two_stage_age` 中重复的 `if abs(denom) < EPSILON: denom = EPSILON` 逻辑。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 1 个测试，覆盖 `_safe_scalar_denominator` 的 EPSILON 下界保护行为。

## 阶段进展（2026-04-06 · StateStore 第一百五十四批）

- P2-3（数值稳定性统一）继续收敛 source 反演分母保护逻辑：
    - `data/geochemistry/source.py` 新增 `_safe_denominator`，统一 `_invert_mu`、`_invert_omega`、`_invert_kappa` 中重复的 `np.where(abs(..)<EPSILON, EPSILON, ..)` 逻辑。
- 回归测试新增：
    - `tests/test_geochemistry_source_helpers.py` 新增 2 个测试，覆盖：
        - `_safe_denominator` 的 EPSILON 下界保护行为；
        - `_invert_mu` 在退化时间项场景下返回有限值。

## 阶段进展（2026-04-06 · StateStore 第一百五十二批）

- P2-3（数值稳定性统一）继续收敛 geochemistry/geo-panel 科学计数法参数字面量：
    - `data/geochemistry/engine.py` 新增 `E1_CUMMING_RICHARDS`、`E2_CUMMING_RICHARDS`，替换 `Cumming & Richards (Model III)` 预设中的散落字面量。
    - `ui/panels/geo_panel.py` 新增衰变常数默认值与科学步长常量（`_GEO_DECAY_LAMBDA_*`、`_GEO_PARAM_SCIENTIFIC_STEP`），替换面板构建与参数控件配置中的散落字面量。
- 回归测试新增/增强：
    - `tests/test_geochemistry_engine.py` 新增 1 个测试，覆盖 `Cumming & Richards (Model III)` 预设对命名常量的使用。
    - `tests/test_geo_panel_helpers.py` 新增 2 个测试，覆盖：
        - GeoPanel 衰变常数默认值与 engine 常量对齐；
        - `_add_geo_param` 科学计数模式步长使用命名常量。

## 阶段进展（2026-04-06 · StateStore 第一百五十一批）

- P2-3（数值稳定性统一）继续收敛 age 求解器端点保护常量：
    - `data/geochemistry/age.py` 将 `_solve_age_scipy` 中上端点安全边距 `1.0` 提炼为 `_AGE_SOLVER_ENDPOINT_MARGIN`。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 1 个测试，覆盖 `_solve_age_scipy` 调用 `brentq` 时上端点扣减安全边距路径。

## 阶段进展（2026-04-06 · StateStore 第一百五十批）

- P2-3（数值稳定性统一）推进 age 求根容差常量收敛：
    - `data/geochemistry/age.py` 将 `_solve_age_scipy` 中 `optimize.brentq(..., xtol=1e-6)` 提炼为 `_AGE_SOLVER_XTOL`。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - 端点异号直接求根路径对 `_AGE_SOLVER_XTOL` 的透传；
        - 区间扫描变号路径对 `_AGE_SOLVER_XTOL` 的透传。

## 阶段进展（2026-04-06 · StateStore 第一百四十九批）

- P2-3（数值稳定性统一）推进 export legend 锚点判定阈值收敛：
    - `ui/panels/export/common.py` 将 legend `bbox_to_anchor` 点锚判定阈值 `1e-9` 提炼为 `_LEGEND_BBOX_POINT_EPSILON`。
- 回归测试新增：
    - `tests/test_export_panel_common_helpers.py` 新增 2 个测试，覆盖：
        - 近点锚 bbox 归一化为二元锚点；
        - 区域锚 bbox 保持四元锚点范围。

## 阶段进展（2026-04-06 · StateStore 第一百四十八批）

- P2-3（数值稳定性统一）推进 geochemistry facade 的年龄模型判别阈值收敛：
    - `data/geochemistry/__init__.py` 将 `resolve_age_model` 中参数差异阈值 `1e-6` 提炼为 `_AGE_MODEL_PARAM_DELTA_FLOOR`。
- 回归测试新增：
    - `tests/test_geochemistry_init_helpers.py` 新增 3 个测试，覆盖：
        - 显式 `age_model` 标志优先；
        - 参数差异低于阈值回退 `single_stage`；
        - 参数差异高于阈值保持 `two_stage`。

## 阶段进展（2026-04-06 · StateStore 第一百四十七批）

- P2-3（数值稳定性统一）继续收敛 ternary helper 的数值护栏常量：
    - `visualization/plotting/ternary.py` 新增 `_TERNARY_LIMIT_EPSILON`、`_TERNARY_FACTORS_FILL_VALUE`、`_TERNARY_FACTORS_MIN_VALUE`，替换 `_equalized_window`、`recommend_boundary_percent_from_components`、`calculate_auto_ternary_factors` 中的散落字面量。
- 回归测试新增：
    - `tests/test_plotting_ternary_helpers.py` 新增 2 个测试，覆盖：
        - 低跨度数据下边界推荐值 fallback 路径；
        - 含零值/负值/NaN 输入时自动因子计算的有限正值输出路径。

## 阶段进展（2026-04-06 · StateStore 第一百四十六批）

- P2-3（数值稳定性统一）推进 Matplotlib 布局API兼容收敛：
    - `visualization/plotting/style.py` 新增 `configure_constrained_layout`，优先使用 `set_layout_engine('constrained')` 与 layout engine `set(...)` 参数配置，并在异常/缺失时回退旧版 `set_constrained_layout*` 接口。
    - `visualization/plotting/kde.py`、`ui/app_parts/plotting.py`、`ui/panels/display/themes.py` 统一改为调用该辅助函数，移除分散的弃用接口直接调用。
- 回归测试新增/增强：
    - `tests/test_plotting_style_helpers.py` 新增 2 个测试，覆盖：
        - layout engine 新API路径参数配置；
        - 新API不可用时 legacy API 回退路径。
    - `tests/test_plotting_kde_helpers.py` 新增 1 个测试，覆盖边际 KDE 渲染对布局辅助函数的委托调用。
    - `tests/test_ui_wrapper_helpers.py` 新增 1 个测试，覆盖显示主题自动布局对布局辅助函数的委托调用。

## 阶段进展（2026-04-06 · StateStore 第一百四十五批）

- P2-3（数值稳定性统一）继续收敛 York 回归容差常量：
    - `data/geochemistry/isochron.py` 将 `york_regression` 的默认容差 `1e-15` 提炼为 `_YORK_TOL_DEFAULT`。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - 简单线性样本的 York 回归参数回收；
        - 非正不确定度输入触发 `ValueError`。

## 阶段进展（2026-04-06 · StateStore 第一百四十四批）

- P2-3（数值稳定性统一）继续收敛 KDE 退化判定阈值：
    - `visualization/plotting/kde.py` 将近常量数据判定阈值 `1e-12` 提炼为 `_KDE_MIN_STD` 常量。
- 回归测试新增：
    - `tests/test_plotting_kde_helpers.py` 新增 1 个测试，覆盖近常量输入下 `_estimate_density_curve` 返回 `None` 的保护分支。

## 阶段进展（2026-04-06 · StateStore 第一百四十三批）

- P2-3（数值稳定性统一）推进 lasso 几何判定分母保护：
    - `application/use_cases/selection_interaction.py` 的射线法点在多边形判断从内联 `or 1e-12` 改为显式 `dy == 0` 分支处理，避免除零且保持微小斜率边的几何判定连续性。
- 回归测试新增：
    - `tests/test_selection_and_tooltip_usecases.py` 新增 1 个测试，覆盖近水平边（`dy≈1e-16`）场景下 lasso 选择结果稳定性。

## 阶段进展（2026-04-06 · StateStore 第一百四十二批）

- P2-3（数值稳定性统一）继续收敛 age 求解保护常量：
    - `data/geochemistry/age.py` 将重复字面值 `1e-10`、`1e10` 提炼为 `_RATIO_DIFF_FLOOR` 与 `_SOLVER_GUARD_VALUE`，统一单/双阶段标量与数组路径的奇异点保护语义。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - 单阶段分母奇异点短路返回 `None`；
        - 双阶段数组路径中奇异元素回退为 `NaN`，常规元素保持求解结果。

## 阶段进展（2026-04-06 · StateStore 第一百四十一批）

- P2-3（数值稳定性统一）继续收敛 isochron 生长曲线分母保护：
    - `data/geochemistry/isochron.py` 的 `calculate_isochron1_growth_curve` 分母阈值改为复用 `_SOURCE_DEN_FLOOR`，去除散落字面值。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - 退化分母场景返回 `None`；
        - 常规输入返回指定步长的 `x/y` 生长曲线数组。

## 阶段进展（2026-04-06 · StateStore 第一百四十批）

- P2-3（数值稳定性统一）推进 isochron 反演分母保护统一：
    - `data/geochemistry/isochron.py` 新增 `_SOURCE_DEN_FLOOR = max(EPSILON, 1e-15)`，并将源区 `Mu/Kappa` 反演中的硬编码分母阈值统一为该常量。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 2 个测试，覆盖：
        - `calculate_source_mu_from_isochron` 在退化分母场景返回 `0.0`；
        - `calculate_source_kappa_from_slope` 在退化分母场景返回 `0.0`。

## 阶段进展（2026-04-06 · StateStore 第一百三十九批）

- P2-2（AppState 分层拆分）扫尾清理：
    - `visualization/line_styles.py` 在自定义 state 分支改用局部 `state` 别名写入，去除残留的 `setattr(app_state, ...)` 模式匹配噪音，保持行为不变。
- 回归测试新增：
    - `tests/test_localization_line_style_helpers.py` 新增 1 个测试，覆盖 `resolve_line_style` 对空字符串颜色覆盖值的回退策略。

## 阶段进展（2026-04-06 · StateStore 第一百三十八批）

- P2-3（数值稳定性统一）推进选择叠加椭圆计算：
    - `visualization/selection_overlay.py` 的 `draw_confidence_ellipse` 新增有限值筛选、输入长度一致性检查与协方差分母下界保护，避免 NaN/Inf 点导致整批失败。
- 回归测试新增：
    - `tests/test_selection_overlay_helpers.py` 新增 3 个测试，覆盖：
        - 非有限点过滤后仍可绘制椭圆；
        - 长度不一致输入返回 `None`；
        - 零方差退化场景返回 `None`。

## 阶段进展（2026-04-06 · StateStore 第一百三十七批）

- P2-2（AppState 分层拆分）继续清理剩余 `setattr(app_state, ...)` 旁路写入：
    - `core/localization.py` 的 `set_language` 改为显式 `state_gateway.set_language_code`。
    - `visualization/line_styles.py` 的全局状态写入改为显式 `state_gateway.set_line_styles`（对非全局自定义 state 仍保留原地写入行为）。
- 回归测试新增：
    - `tests/test_localization_line_style_helpers.py` 新增 4 个测试，覆盖语言切换 gateway 路径、非法语言拒绝、line_style 全局状态写入与自定义状态分支。

## 阶段进展（2026-04-06 · StateStore 第一百三十六批）

- P2-2（AppState 分层拆分）继续迁移 ternary helper 的状态写入路径：
    - `visualization/plotting/ternary.py` 将 `configure_ternary_axis`、`calculate_auto_ternary_factors` 中 `app_state` 直写改为显式 `state_gateway` API（`set_ternary_limit_mode`、`set_ternary_boundary_percent`、`set_ternary_factors`）。
- 回归测试新增：
    - `tests/test_plotting_ternary_helpers.py` 新增 4 个测试，覆盖：
        - ternary 归一化对无效行的回退；
        - 轴配置 helper 的 gateway 写入路径；
        - 自动因子计算的 gateway 写入与无数据失败分支。

## 阶段进展（2026-04-06 · StateStore 第一百三十五批）

- P2-1（类型注解补齐）收敛 UI 顶层 helper 签名：
    - `ui/app.py`：`_configure_matplotlib_fonts`、`_configure_matplotlib`
    - `ui/control_panel.py`：`create_control_panel`、`create_section_dialog`
    - `ui/app_parts/styles.py`：`_clear_widget_styles`
    - `ui/dialogs/*.py`：`get_*` / `show_*` 顶层包装函数全部补齐显式类型注解。
- 回归测试新增：
    - `tests/test_ui_wrapper_helpers.py` 新增 13 个测试，覆盖 matplotlib 启动配置 helper、control panel 工厂函数、dialog 包装函数返回路径以及样式清理 helper 行为。

## 阶段进展（2026-04-06 · StateStore 第一百三十四批）

- P2-1（类型注解补齐）推进日志入口函数：
    - `utils/logger.py` 的 `setup_logging` 增加显式参数与返回类型注解，并同步补齐 `LoggerWriter` 方法签名类型。
- 回归测试新增：
    - `tests/test_logger_setup.py` 新增 2 个测试，覆盖：
        - `setup_logging` 对 `stdout/stderr` 的重定向与日志文件落盘；
        - `ISOTOPES_LOG_LEVEL` 环境变量对根日志级别的控制。

## 阶段进展（2026-04-06 · StateStore 第一百三十三批）

- P2-1（类型注解补齐）收敛 `visualization` 模块级兼容导出函数：
    - `visualization/style_manager.py` 的 `apply_custom_style` 补齐显式参数与返回类型注解。
- 回归测试新增：
    - `tests/test_style_manager_exports.py` 新增 1 个测试，覆盖 `apply_custom_style` 对 `style_manager_instance.apply_style` 的参数透传行为。

## 阶段进展（2026-04-06 · StateStore 第一百三十二批）

- P2-1（类型注解补齐）继续收敛 geochem overlay helper：
    - `visualization/plotting/geochem/isochron_fits.py`：`_draw_isochron_overlays`
    - `visualization/plotting/geochem/model_overlays.py`：`_draw_model_curves`、`_draw_mu_kappa_paleoisochrons`
    - `visualization/plotting/geochem/paleoisochron_overlays.py`：`_draw_paleoisochrons`
    - `visualization/plotting/geochem/plumbotectonics_isoage.py`：`_draw_plumbotectonics_isoage_lines`
    - `visualization/plotting/geochem/selected_isochron_overlay.py`：`_draw_selected_isochron`
- 回归测试新增：
    - `tests/test_geochem_overlay_draw_helpers.py` 新增 6 个测试，覆盖上述 helper 的关键绘制分支与空数据保护分支。

## 阶段进展（2026-04-06 · StateStore 第一百三十一批）

- P2-1（类型注解补齐）推进 equation overlays 模块：
    - `visualization/plotting/geochem/equation_overlays.py` 的 `_safe_eval_expression`、内部 `_eval_node` 与 `_draw_equation_overlays` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_equation_overlays_helpers.py` 新增 2 个测试，覆盖：
        - 算术与 `where` 表达式求值；
        - 未知变量/非法调用符号拒绝。

## 阶段进展（2026-04-06 · StateStore 第一百三十批）

- P2-1（类型注解补齐）推进 plumbotectonics 曲线模块：
    - `visualization/plotting/geochem/plumbotectonics_curves.py` 的 `_fit_plumbotectonics_curve` 与 `_draw_plumbotectonics_curves` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_plumbotectonics_curves_helpers.py` 新增 2 个测试，覆盖：
        - 重复点与无效值过滤后的拟合输出；
        - 有效点不足时回退原始点返回。

## 阶段进展（2026-04-06 · StateStore 第一百二十九批）

- P2-1（类型注解补齐）推进 model age lines 模块：
    - `visualization/plotting/geochem/model_age_lines.py` 的 `_resolve_model_age`、`_draw_model_age_lines`、`_draw_model_age_lines_86` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_model_age_lines_helpers.py` 新增 2 个测试，覆盖：
        - 单阶段分支使用 CDT 年龄与 `T2` 覆写；
        - 两阶段分支优先使用有限 `tSK` 并在缺失处回退 `tCDT`。

## 阶段进展（2026-04-06 · StateStore 第一百二十八批）

- P2-1（类型注解补齐）推进地化叠加调度模块：
    - `visualization/plotting/rendering/geo_layers.py` 的 `_render_geo_overlays` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_rendering_geo_layers_helpers.py` 新增 2 个测试，覆盖：
        - Plumbotectonics 分支的 isoage/curve/equation 调度顺序；
        - Mu-Age 分支的 paleoisochron 与 equation 调度。

## 阶段进展（2026-04-06 · StateStore 第一百二十七批）

- P2-1（类型注解补齐）推进 plotting KDE 模块：
    - `visualization/plotting/kde.py` 的 `clear_marginal_axes` 与 `draw_marginal_kde` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_plotting_kde_helpers.py` 新增 2 个测试，覆盖：
        - 边际 KDE 绘制后 axes 注册；
        - `clear_marginal_axes` 清理并重置状态。

## 阶段进展（2026-04-06 · StateStore 第一百二十六批）

- P2-1（类型注解补齐）推进 plotting 样式核心模块：
    - `visualization/plotting/styling/core.py` 的 `_apply_current_style`、`_enforce_plot_style`、`_apply_axis_text_style` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_styling_core_helpers.py` 新增 2 个测试，覆盖：
        - 轴标签/标题样式应用；
        - 坐标轴 spine 可见性与线宽应用。

## 阶段进展（2026-04-06 · StateStore 第一百二十五批）

- P2-1（类型注解补齐）推进渲染 KDE 辅助模块：
    - `visualization/plotting/rendering/kde.py` 的 `_resolve_kde_style` 与 `_render_kde_overlay` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_rendering_kde_helpers.py` 新增 2 个测试，覆盖：
        - 主 KDE 样式从 legacy 配置生成 fallback；
        - marginal KDE 样式默认与字段差异（无 `levels`）。

## 阶段进展（2026-04-06 · StateStore 第一百二十四批）

- P2-1（类型注解补齐）推进渲染散点辅助模块：
    - `visualization/plotting/rendering/common/scatter.py` 的 `_render_scatter_groups` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_rendering_scatter_helpers.py` 新增 2D 路径测试，覆盖分组散点渲染后 `sample_coordinates` 与 `artist_to_sample` 映射构建。

## 阶段进展（2026-04-06 · StateStore 第一百二十三批）

- P2-1（类型注解补齐）推进渲染图例辅助模块：
    - `visualization/plotting/rendering/common/legend.py` 的 `_notify_legend_panel`、`_build_legend_proxies`、`_build_overlay_legend_entries`、`_place_inline_legend`、`_render_legend` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_rendering_legend_helpers.py` 新增 2 个测试，覆盖：
        - patch 模式下图例代理句柄构建；
        - overlay 图例条目样式应用与文本翻译路径。

## 阶段进展（2026-04-06 · StateStore 第一百二十二批）

- P2-1（类型注解补齐）推进渲染标题辅助模块：
    - `visualization/plotting/rendering/common/title.py` 的 `_render_title_labels` 补齐显式参数与返回类型注解。
- 回归测试新增：
    - `tests/test_rendering_title_helpers.py` 新增 2 个测试，覆盖：
        - PCA 模式标题与 `PCx` 坐标轴标签；
        - 地化模式子集渲染时标题 `(Subset)` 标记与 206/207 坐标轴标签。

## 阶段进展（2026-04-06 · StateStore 第一百二十一批）

- P2-1（类型注解补齐）推进 plotting core 轴与懒加载辅助函数：
    - `visualization/plotting/core.py` 的 `_lazy_import_umap`、`_lazy_import_mplot3d`、`_lazy_import_ellipse`、`_lazy_import_mpltern` 与 `_ensure_axes` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_plotting_core_axes_helpers.py` 新增 2 个测试，覆盖：
        - `fig` 缺失时 `_ensure_axes` 返回 `None`；
        - `_ensure_axes` 在 2D/3D 间切换并重置 `legend_ax`。

## 阶段进展（2026-04-06 · StateStore 第一百二十批）

- P2-1（类型注解补齐）推进 overlay 样式刷新模块：
    - `visualization/plotting/styling/overlays.py` 的 `refresh_overlay_styles`、`refresh_overlay_visibility` 及内部可见性辅助函数补齐显式类型注解。
- 回归测试新增：
    - `tests/test_overlay_styling_visibility.py` 新增 2 个测试，覆盖：
        - 样式刷新对 artist 颜色/线宽/线型/透明度的应用；
        - 可见性刷新对 toggle 与分组可见性的联动控制。

## 阶段进展（2026-04-06 · StateStore 第一百一十九批）

- P2-1（类型注解补齐）推进 geochem 标签模块：
    - `visualization/plotting/geochem/isochron_labels.py` 的 `_build_isochron_label` 与 `refresh_paleoisochron_labels` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_isochron_labels_helpers.py` 新增 2 个测试，覆盖：
        - 默认标签策略（age + n_points）；
        - 扩展开关组合下的 MSWD/R²/slope/intercept 文本拼接。

## 阶段进展（2026-04-06 · StateStore 第一百一十八批）

- P2-1（类型注解补齐）继续推进 label layout 几何 helper：
    - `visualization/plotting/label_layout.py` 的 `_slope_angle_deg`、`_pick_anchor_on_line`、`apply_adjust_text_to_labels` 补齐显式类型注解。
- 回归测试增强：
    - `tests/test_label_layout_settings.py` 扩展 2 个测试，覆盖：
        - 无 `transData` 时角度计算回退；
        - 曲线锚点在 start/center/end 模式下的选点与不可见曲线返回 `None`。

## 阶段进展（2026-04-06 · StateStore 第一百一十七批）

- P2-1（类型注解补齐）推进 label layout 参数归一化模块：
    - `visualization/plotting/label_layout.py` 的 `_float_pair`、`_resolve_adjust_text_settings`、`_lazy_import_adjust_text` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_label_layout_settings.py` 新增 2 个测试，覆盖：
        - adjustText pair 参数归一化（序列/标量/回退）；
        - `iter_lim` 与 `time_lim` 的上下界夹逼规则。

## 阶段进展（2026-04-06 · StateStore 第一百一十六批）

- P2-1（类型注解补齐）推进 embedding dataframe 对齐模块：
    - `visualization/plotting/rendering/embedding/dataframe.py` 的 `_reset_plot_dataframe` 与 `prepare_plot_dataframe` 补齐显式 DataFrame 类型签名。
- 回归测试新增：
    - `tests/test_embedding_dataframe_helpers.py` 新增 2 个测试，覆盖：
        - 可见组过滤命中时的筛选行为；
        - 可见组过滤失配时自动回退并重置过滤状态。

## 阶段进展（2026-04-06 · StateStore 第一百一十五批）

- P2-1（类型注解补齐）推进 plotting core helper：
    - `visualization/plotting/core.py` 的 `_build_group_palette`、`_get_subset_dataframe`、`_get_pb_columns`、`_find_age_column` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_plotting_core_column_helpers.py` 新增 3 个测试，覆盖 Pb 列精确/启发式识别与年龄列优先级规则。

## 阶段进展（2026-04-06 · StateStore 第一百一十四批）

- P2-1（类型注解补齐）推进事件编排模块：
    - `visualization/events.py` 的 `_sync_render_mode` 增加显式参数与返回类型注解。
- 回归测试新增：
    - `tests/test_events_render_mode_sync.py` 新增 2 个测试，覆盖：
        - render_mode 变化时状态与控制面板变量同步；
        - render_mode 不变时的 no-op 行为。

## 阶段进展（2026-04-06 · StateStore 第一百一十三批）

- P2-1（类型注解补齐）推进 plotting 数据辅助模块：
    - `visualization/plotting/data.py` 的 `_lazy_import_geochemistry` 增加显式返回类型注解。
- 回归测试新增：
    - `tests/test_plotting_data_lazy_import.py` 新增缓存行为测试，锁定 lazy import 在首轮加载后复用同一模块/函数引用。

## 阶段进展（2026-04-06 · StateStore 第一百一十二批）

- P2-1（类型注解补齐）推进 embedding 算法调度工具：
    - `visualization/plotting/rendering/embedding/algorithm.py` 的 `resolve_target_dimensions` 增加显式返回类型注解。
- 回归测试新增：
    - `tests/test_embedding_algorithm_helpers.py` 新增 3 个测试，覆盖：
        - legacy 算法别名规范化；
        - ternary 与默认二维维度解析；
        - embedding 参数默认补全与显式参数透传。

## 阶段进展（2026-04-06 · StateStore 第一百一十一批）

- P2-1（类型注解补齐）推进事件处理 helper：
    - `visualization/event_handlers/pointer_events.py` 的 `_resolve_sample_index` 增加显式类型注解。
- 回归测试新增：
    - `tests/test_pointer_events_helpers.py` 新增 3 个测试，覆盖：
        - 散点命中映射优先；
        - 最近点查找回退路径；
        - 缺失坐标时返回 `None`。

## 阶段进展（2026-04-06 · StateStore 第一百一十批）

- P2-1（类型注解补齐）推进 plotting isochron 辅助模块：
    - `visualization/plotting/isochron.py` 的 `resolve_isochron_errors` 补齐显式参数与返回类型注解。
- 回归测试新增：
    - `tests/test_plotting_isochron_helpers.py` 新增 2 个测试，覆盖：
        - columns 模式下按列解析误差数组；
        - columns 缺失时回退到 fixed 参数填充。

## 阶段进展（2026-04-06 · StateStore 第一百零九批）

- P2-1（类型注解补齐）推进 legend 样式工具：
    - `visualization/plotting/styling/legend.py` 的 `_legend_layout_config`、`_legend_columns_for_layout`、`_style_legend` 补齐显式类型注解。
- 回归测试新增：
    - `tests/test_legend_styling_helpers.py` 新增 3 个测试，覆盖：
        - in-plot 图例位置偏移到 bbox 的映射；
        - outside 位置的布局短路规则；
        - 列数自动决策规则。

## 阶段进展（2026-04-06 · StateStore 第一百零八批）

- P2-1（类型注解补齐）继续推进 geochem overlay 公共工具：
    - `visualization/plotting/geochem/overlay_common.py` 的 artist 注册、label 参数合并、文本模板与 bbox 构造函数补齐显式类型注解。
- 回归测试新增：
    - `tests/test_overlay_common_helpers.py` 新增 3 个测试，覆盖：
        - label 模板格式化与缺失占位符回退；
        - label bbox 默认值与自定义边框；
        - 样式合并时对空字符串/None 的忽略规则。

## 阶段进展（2026-04-06 · StateStore 第一百零七批）

- P2-1（类型注解补齐）推进 visualization/geochem 元数据模块：
    - `visualization/plotting/geochem/plumbotectonics_metadata.py` 补齐函数签名类型注解（section 选择、分组键生成、调色板映射、marker 规则）。
- 回归测试新增：
    - `tests/test_plumbotectonics_metadata.py` 新增 5 个测试，覆盖：
        - variant 名称回退策略；
        - 分组键去重与 style_key 生成；
        - 颜色循环映射；
        - overlay 默认颜色索引；
        - marker 关键词映射规则。

## 阶段进展（2026-04-06 · StateStore 第一百零六批）

- P2-1（类型注解补齐）收口 data 层残留项：
    - `data/mixing.py` 中单纯形求解内部目标函数 `obj` 增加显式参数与返回类型注解。
- 回归测试新增：
    - `tests/test_data_mixing.py` 新增 2 个测试，覆盖：
        - 双端元简单场景下的权重回收（0.8/0.2）与残差；
        - 空端元分组时的异常路径。

## 阶段进展（2026-04-06 · StateStore 第一百零五批）

- P2-1（类型注解补齐）继续推进 data/geochemistry 求解辅助函数：
    - `data/geochemistry/age.py` 中 `_solve_age_scipy` 的 `_eval`，以及单/双阶段年龄求解内部 `f`、`f_scalar` 增加显式参数与返回类型注解。
    - `data/geochemistry/isochron.py` 中 Pb-Pb 年龄反解内部函数 `f` 增加显式类型注解。
- 回归测试新增：
    - `tests/test_geochemistry_age_isochron.py` 新增 3 个测试，覆盖：
        - Pb-Pb 反解年龄可回收构造输入年龄；
        - 非正比值短路返回；
        - 等时线斜率年龄计算与 Pb-Pb 反解一致。

## 阶段进展（2026-04-06 · StateStore 第一百零四批）

- P2-1（类型注解补齐）扩展至 data 层：
    - `data/geochemistry/engine.py` 的 `GeochemistryEngine` 方法签名补齐显式类型注解（`__init__`、`_update_derived_params`、`get_available_models`、`load_preset`、`update_parameters`、`get_parameters`）。
    - `params` 字段增加显式容器类型，减少调用侧的隐式 Any 传播。
- 回归测试新增：
    - `tests/test_geochemistry_engine.py` 新增 3 个测试，覆盖预设列表一致性、未知模型加载返回值、参数更新时对无效/未知键的处理与 `v_M` 派生值同步。

## 阶段进展（2026-04-06 · StateStore 第一百零三批）

- P2-1（类型注解补齐）继续推进：
    - `core/state/app_state.py` 的 Overlay 兼容属性 getter/setter 补齐显式类型注解。
    - 覆盖域：展示开关、地化模型参数、等时线误差字段、线宽参数与 overlay 标签/artist 运行时容器。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 `test_app_state_overlay_detail_property_setters_dispatch_to_state_store`，新增 `model_curve_models=None` 路径断言，锁定可空值分发与快照一致性。

## 阶段进展（2026-04-06 · StateStore 第一百零二批）

- P2-1（类型注解补齐）继续推进：
    - `core/state/app_state.py` 的 Legend 兼容属性 getter/setter 补齐显式类型注解。
    - 覆盖域：位置/列数/偏移/显示模式、边框样式、隐藏组、快照三元、运行时 legend 映射与回调。
- 回归测试更新：
    - `tests/test_state_store.py` 新增 `test_app_state_runtime_legend_properties_passthrough`，锁定：
        - `legend_to_scatter`、`legend_update_callback` 仍为运行时透传属性；
        - 两者不进入 StateStore 快照。

## 阶段进展（2026-04-06 · StateStore 第一百零一批）

- P2-1（类型注解补齐）启动首批落地，覆盖 core 轻量状态对象：
    - `core/overlay_state.py`
    - `core/legend_state.py`
- 改造内容：
    - 为构造函数补充 `-> None`。
    - 为关键字段补充显式类型注解（含运行时容器字段与可空字段）。
    - 为 `OverlayState` 的 `_init_equation_styles`、`clear_artists` 补充返回类型注解。
- 回归测试新增：
    - `tests/test_overlay_legend_state.py`，覆盖：
        - `OverlayState.clear_artists` 运行时容器清理行为。
        - `OverlayState._init_equation_styles` style_key 与样式条目生成。
        - `LegendState` 默认值稳定性。

## 阶段进展（2026-04-06 · StateStore 第一百批）

- 收口边界测试新增：
    - `tests/test_state_store.py` 新增 `test_state_store_snapshot_excludes_runtime_legend_domains`，明确 `legend_to_scatter` 与 `legend_update_callback` 不进入 StateStore 快照。
- 最终审计（本批执行）：
    - `scripts/check_state_mutations.py --fail-on-hits` → `TOTAL=0`
    - `scripts/check_gateway_generic_mutations.py --fail-on-hits` → `TOTAL=0`
    - `scripts/check_gateway_generic_mutations_in_tests.py --fail-on-hits` → `TOTAL=0`
    - `scripts/check_gateway_direct_state_assignments.py --fail-on-hits` → `TOTAL=0`
    - `pytest tests/test_state_store.py tests/test_gateway_set_attr_compatibility.py tests/test_guard_scripts.py` → `145 passed`
- 结论：当前 StateStore 迁移主线已无待收口项（按既定决策，运行时对象域保持非托管）。

## 阶段进展（2026-04-04 · StateStore 第九十九批）

- 批次决策落地：运行时对象域保持非托管（不纳入 StateStore 快照），避免将不可序列化/仅会话内有效对象写入状态仓。
    - 代表字段：`legend_to_scatter`、`legend_update_callback`（以及同类 artist/callback 引用）
- 约束收敛：继续仅迁移“可归一化、可快照、可回放”的配置与参数域；运行时对象仍通过 gateway 显式 API 维护。
- 守护校验：`check_gateway_direct_state_assignments.py` 与 `check_state_mutations.py` 均为 `TOTAL=0`。

## 阶段进展（2026-04-04 · StateStore 第九十八批）

- 新增 Legend 参数域 StateStore 托管：
    - `legend_display_mode`
    - `hidden_groups`
- `core/state/store.py` 新增对应 action、快照导出与 `_sync_state` 回写：
    - `SET_LEGEND_DISPLAY_MODE`
    - `SET_HIDDEN_GROUPS`
- `core/state/gateway.py` 新增显式 API 与 `set_attr` 兼容映射：
    - `set_legend_display_mode`
    - `set_hidden_groups`
- `core/state/app_state.py` 对应兼容属性 setter 改为优先 dispatch。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 legend 兼容 setter 断言与 snapshot/restore 覆盖。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 legend 偏好兼容用例。

## 阶段进展（2026-04-04 · StateStore 第九十七批）

- 新增 Overlay 参数域 StateStore 托管：
    - `paleoisochron_min_age`
    - `paleoisochron_max_age`
    - `model_curve_models`
- `core/state/store.py` 新增对应 action 与快照同步：
    - `SET_PALEOISOCHRON_MIN_AGE`
    - `SET_PALEOISOCHRON_MAX_AGE`
    - `SET_MODEL_CURVE_MODELS`
  同时补齐 snapshot 导出与 `_sync_state` 回写。
- `core/state/gateway.py` 新增显式 API 与 `set_attr` 兼容映射：
    - `set_paleoisochron_min_age`
    - `set_paleoisochron_max_age`
    - `set_model_curve_models`
- `core/state/app_state.py` 对应兼容属性 setter 改为优先 dispatch（无 store 时回退原行为）。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与 overlay 兼容属性分发断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 geochem 参数兼容用例。

## 阶段进展（2026-04-04 · StateStore 第九十六批）

- `core/state/app_state.py` 的 Legend 快照兼容属性 setter 收口到 StateStore：
    - `legend_last_title`
    - `legend_last_handles`
    - `legend_last_labels`
- 实现方式：复用既有 `SET_LEGEND_SNAPSHOT` action，按“单字段更新 + 其余字段沿用当前值”组合分发。
- 回归测试更新：
    - `tests/test_state_store.py` 的 `test_app_state_legend_property_setters_dispatch_to_state_store` 增补 legend 快照三字段断言。

## 阶段进展（2026-04-04 · StateStore 第九十五批）

- `core/state/app_state.py` 的同位素误差兼容属性 setter 收口到 StateStore：
    - `isochron_error_mode`
    - `isochron_sx_col`、`isochron_sy_col`、`isochron_rxy_col`
    - `isochron_sx_value`、`isochron_sy_value`、`isochron_rxy_value`
- 实现方式：复用既有 `SET_ISOCHRON_ERROR_COLUMNS` / `SET_ISOCHRON_ERROR_FIXED` action，兼容属性写入改为组合分发并保留无 store 回退。
- 同步机制修正：`core/state/store.py` `_sync_state` 对误差字段改为直接回写 `overlay` 子状态，避免通过兼容 setter 触发递归分发。
- 回归测试更新：
    - `tests/test_state_store.py` 新增 `test_app_state_isochron_error_property_setters_dispatch_to_state_store`，覆盖列误差与固定误差两种写入路径。

## 阶段进展（2026-04-04 · StateStore 第九十四批）

- `core/state/app_state.py` 顶层 Overlay 兼容属性 setter 继续收口到 StateStore（action 已覆盖域）：
    - `isochron_label_options`、`equation_overlays`、`line_styles`
    - `paleoisochron_step`、`paleoisochron_ages`
    - `plumbotectonics_variant`、`plumbotectonics_group_visibility`
    - `selected_isochron_data`、`isochron_results`
    - `model_curve_width`、`plumbotectonics_curve_width`、`paleoisochron_width`
    - `model_age_line_width`、`isochron_line_width`
    - `overlay_artists`、`overlay_curve_label_data`、`paleoisochron_label_data`
    - `plumbotectonics_label_data`、`plumbotectonics_isoage_label_data`
- 行为调整：在 `state_store` 可用时，以上属性统一通过 `SET_*` action 分发，兼容 `state_store` 不可用时的旧回退路径。
- 同步机制修正：`core/state/store.py` `_sync_state` 对上述字段改为直接回写 `overlay` 子状态，避免通过兼容 setter 触发递归分发。
- 回归测试更新：
    - `tests/test_state_store.py` 新增 `test_app_state_overlay_detail_property_setters_dispatch_to_state_store`，锁定写入路径与 store 快照一致性。

## 阶段进展（2026-04-04 · StateStore 第九十三批）

- `core/state/app_state.py` 顶层 Overlay 兼容属性 setter 收口到 StateStore（首批高频 geochem 域）：
    - `show_model_curves`、`show_plumbotectonics_curves`、`show_paleoisochrons`
    - `show_model_age_lines`、`show_growth_curves`、`show_isochrons`
    - `show_equation_overlays`、`geo_model_name`
    - `use_real_age_for_mu_kappa`、`mu_kappa_age_col`
- 行为调整：在 `state_store` 可用时，以上属性写入统一通过 `SET_*` action 分发；无 store 场景保持旧兼容回退。
- 同步机制修正：`core/state/store.py` 的 `_sync_state` 对上述字段改为直接回写 `overlay` 子状态，避免通过属性 setter 触发递归分发。
- 回归测试更新：
    - `tests/test_state_store.py` 新增 `test_app_state_overlay_property_setters_dispatch_to_state_store`，锁定兼容属性写入与 store 快照一致性。

## 阶段进展（2026-04-04 · StateStore 第九十二批）

- `core/state/app_state.py` 的 LegendState 兼容属性 setter 收口到 StateStore：
    - `legend_position`、`legend_columns`、`legend_offset`、`legend_nudge_step`、`legend_location`
    - `legend_frame_on`、`legend_frame_alpha`、`legend_frame_facecolor`、`legend_frame_edgecolor`
- 行为调整：在 `state_store` 可用时，以上属性写入通过对应 `SET_*` action 分发，避免直接写 `legend` 子状态导致快照不同步。
- 回归测试更新：
    - `tests/test_state_store.py` 新增 `test_app_state_legend_property_setters_dispatch_to_state_store`，锁定兼容属性写入与 store 快照一致性。

## 阶段进展（2026-04-04 · StateStore 第九十一批）

- `core/state/app_state.py` 的 `StyleState` 兼容视图补齐字体域写入分发：
    - 新增 `custom_primary_font` setter（dispatch `SET_CUSTOM_PRIMARY_FONT`）
    - 新增 `custom_cjk_font` setter（dispatch `SET_CUSTOM_CJK_FONT`）
    - 新增 `plot_font_sizes` property + setter（dispatch `SET_PLOT_FONT_SIZES`）
- 兼容视图回归增强：
    - `tests/test_state_store.py` 的 `test_compatibility_views_dispatch_to_state_store` 新增字体域断言，验证通过 `style_state` 写入后 state/store 保持一致。

## 阶段进展（2026-04-04 · StateStore 第九十批）

- 网关样式写入机制清理：
    - `core/state/gateway.py` 移除 `panel_style_fallback_keys` 相关逻辑与分支。
    - `set_panel_style_updates` 仅允许显式托管键并通过兼容映射分发，不再存在直写后门。
- 行为等价性：在第八十九批完成所有样式键托管后，此批仅做结构收敛，不改变既有样式行为。

## 阶段进展（2026-04-04 · StateStore 第八十九批）

- 样式参数域纳入 StateStore 托管（字体）：
    - `custom_primary_font`
    - `custom_cjk_font`
    - `plot_font_sizes`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并补充字体名/字体大小映射归一化。
- `core/state/gateway.py` 新增显式 API：
    - `set_custom_primary_font`
    - `set_custom_cjk_font`
    - `set_plot_font_sizes`
- 面板样式写入收口：上述字段已从 fallback 直写集合移除，改为通过兼容映射分发到显式 setter。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与样式托管断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_panel_style_updates` 与 `set_attr` 兼容断言。

## 阶段进展（2026-04-04 · StateStore 第八十八批）

- 样式参数域纳入 StateStore 托管（adjustText 布局）：
    - `adjust_text_force_text`
    - `adjust_text_force_static`
    - `adjust_text_expand`
    - `adjust_text_iter_lim`
    - `adjust_text_time_lim`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并补充 pair/迭代上限/时间上限归一化。
- `core/state/gateway.py` 新增显式 API：
    - `set_adjust_text_force_text`
    - `set_adjust_text_force_static`
    - `set_adjust_text_expand`
    - `set_adjust_text_iter_lim`
    - `set_adjust_text_time_lim`
- 面板样式写入收口：上述字段已从 fallback 直写集合移除，改为通过兼容映射分发到显式 setter。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与样式托管断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_panel_style_updates` 与 `set_attr` 兼容断言。

## 阶段进展（2026-04-04 · StateStore 第八十七批）

- 样式参数域纳入 StateStore 托管（文本与图例边框）：
    - `label_color`、`label_weight`、`label_pad`
    - `title_color`、`title_weight`、`title_pad`
    - `legend_frame_on`、`legend_frame_alpha`、`legend_frame_facecolor`、`legend_frame_edgecolor`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并补充文本权重/间距归一化。
- `core/state/gateway.py` 新增显式 API：
    - `set_label_color`、`set_label_weight`、`set_label_pad`
    - `set_title_color`、`set_title_weight`、`set_title_pad`
    - `set_legend_frame_on`、`set_legend_frame_alpha`、`set_legend_frame_facecolor`、`set_legend_frame_edgecolor`
- 面板样式写入收口：上述字段已从 fallback 直写集合移除，改为通过兼容映射分发到显式 setter。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与样式托管断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_panel_style_updates` 与 `set_attr` 兼容断言。

## 阶段进展（2026-04-04 · StateStore 第八十六批）

- 样式参数域纳入 StateStore 托管（次级网格/刻度/边框）：
    - `minor_ticks`、`minor_tick_length`、`minor_tick_width`
    - `show_top_spine`、`show_right_spine`
    - `minor_grid`、`minor_grid_color`、`minor_grid_linewidth`、`minor_grid_alpha`、`minor_grid_linestyle`
    - `scatter_show_edge`、`scatter_edgecolor`、`scatter_edgewidth`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并复用线宽/透明度/颜色归一化规则。
- `core/state/gateway.py` 新增显式 API：
    - `set_minor_ticks`、`set_minor_tick_length`、`set_minor_tick_width`
    - `set_show_top_spine`、`set_show_right_spine`
    - `set_minor_grid`、`set_minor_grid_color`、`set_minor_grid_linewidth`、`set_minor_grid_alpha`、`set_minor_grid_linestyle`
    - `set_scatter_show_edge`、`set_scatter_edgecolor`、`set_scatter_edgewidth`
- 面板样式写入收口：上述字段已从 fallback 直写集合移除，改为通过兼容映射分发到显式 setter。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与样式托管断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_panel_style_updates` 与 `set_attr` 兼容断言。

## 阶段进展（2026-04-04 · StateStore 第八十五批）

- 样式参数域纳入 StateStore 托管（网格与坐标轴核心）：
    - `plot_facecolor`、`axes_facecolor`
    - `grid_color`、`grid_linewidth`、`grid_alpha`、`grid_linestyle`
    - `tick_direction`、`tick_color`、`tick_length`、`tick_width`
    - `axis_linewidth`、`axis_line_color`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并补充颜色/线宽/透明度/方向归一化。
- `core/state/gateway.py` 新增显式 API：
    - `set_plot_facecolor`、`set_axes_facecolor`
    - `set_grid_color`、`set_grid_linewidth`、`set_grid_alpha`、`set_grid_linestyle`
    - `set_tick_direction`、`set_tick_color`、`set_tick_length`、`set_tick_width`
    - `set_axis_linewidth`、`set_axis_line_color`
- 面板样式写入收口：上述托管字段已从 fallback 直写键集合移除，改为通过兼容映射分发到显式 setter。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展 snapshot/restore 与样式域托管断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_panel_style_updates` 与 `set_attr` 兼容断言。

## 阶段进展（2026-04-03 · StateStore 第八十四批）

- 样式参数域纳入 StateStore 托管：
    - `plot_style_grid`
    - `plot_marker_size`
    - `plot_marker_alpha`
    - `show_plot_title`
    - `plot_dpi`
- `core/state/store.py` 新增对应 action、快照输出与 `_sync_state` 回写，并补充数值归一化（size/alpha/dpi）。
- `core/state/gateway.py` 新增显式 API：
    - `set_plot_style_grid`
    - `set_plot_marker_size`
    - `set_plot_marker_alpha`
    - `set_show_plot_title`
    - `set_plot_dpi`
- `set_panel_style_updates` 的允许键中新增上述托管字段，同时从 fallback 直写集合移除，避免再走 `_state` 旁路。
- 回归测试更新：
    - `tests/test_state_store.py` 新增样式参数域托管测试并接入 snapshot/restore。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展面板样式批量更新断言与 `set_attr` 兼容性用例。

## 阶段进展（2026-04-03 · StateStore 第八十三批）

- 参数域纳入 StateStore 托管：
    - `ml_params`
    - `v1v2_params`
- `core/state/store.py` 新增对应 action（`SET_ML_PARAMS`、`SET_V1V2_PARAMS`）、快照输出与 `_sync_state` 回写。
- `core/state/gateway.py` 新增显式 API：`set_ml_params/get_ml_params`、`set_v1v2_params/get_v1v2_params`，并接入 `set_attr` 兼容转发。
- `core/state/app_state.py` 的 `AlgorithmState` 兼容视图新增 `ml_params` 与 `v1v2_params` 的 dispatch 写路径。
- 调用侧改造：
    - `ui/dialogs/provenance_ml/dialog.py`、`ui/dialogs/provenance_ml/workflow.py` 改为通过 gateway 读取 `ml_params`。
    - `visualization/plotting/rendering/embedding/compute_geochem.py` 改为通过 gateway 读取 `v1v2_params`。
- 回归测试更新：
    - `tests/test_state_store.py` 扩展参数域 snapshot/restore 与兼容视图断言。
    - `tests/test_gateway_set_attr_compatibility.py` 扩展 `set_attr` 参数域兼容性用例。

## 阶段进展（2026-04-03 · StateStore 第八十二批）

- 参数域纳入 StateStore 托管：
    - `umap_params`
    - `tsne_params`
    - `pca_params`
    - `robust_pca_params`
- `core/state/store.py` 新增对应 action（`SET_*_PARAMS`）、快照输出与 `_sync_state` 回写，参数统一按 dict 归一化。
- `core/state/gateway.py` 新增显式 API：`set_umap_params`、`set_tsne_params`、`set_pca_params`、`set_robust_pca_params`，并接入 `set_attr` 兼容转发。
- `core/state/app_state.py` 的 `AlgorithmState` 兼容视图参数 setter 改为优先 `state_store.dispatch`，减少兼容层旁路写入。
- 回归测试更新：
    - `tests/test_state_store.py` 补充参数域 snapshot/restore 与兼容视图分发断言。
    - `tests/test_gateway_set_attr_compatibility.py` 新增参数域 `set_attr` 兼容性用例。

## 核查更新（2026-03-07）

本次按代码现状逐项核查后，更新如下：

- 仍未完成（保持原计划）：
    - AppState 分层的全量字段迁移与调用切换。
    - 类型注解全覆盖（P2）。
    - 数值稳定性统一收口。
    - 测试框架落地。
    - 配置外部化。
    - 插件系统（含 ML 管线插件化）。

## 执行策略调整（2026-03-07）

按当前决策，`ML 管线增强` 延后到插件功能开发完成后再推进。

- 当前阶段只推进：第一优先级 + 第二优先级。
- 延后事项：`1.2 ML 管线增强`（依赖插件接口与插件管理能力）。
- 进入条件：`插件开发计划` 至少完成 M2（内置插件迁移）。

## 阶段进展（2026-03-31）

- 图像导出能力完成一轮增强（对应 1.1 的 E2/E3 局部落地）：
    - `ExportPanel` 图像导出新增 `Export Image` 直接导出入口，保留 `Preview Export` 预览链路。
    - 新增导出参数：`DPI`、`Tight Bounding Box`、`Padding (inch)`、`Transparent Background`。
    - 新增模板来源提示：优先 `SciencePlots`，不可用时自动回退到内置样式。
    - 统一预览保存与直接导出的 `savefig` 选项解析与后缀归一化逻辑。
    - 导出面板完成模块化拆分：`export_panel.py` 收敛为组装器，图像导出/数据导出/选择同步/公共逻辑迁移到 `ui/panels/export/` 子包。
    - E5 文档项部分完成：新增 `docs/export.md`，补充导出架构、流程、参数与依赖说明。

## 阶段进展（2026-04-01）

- 可视化渲染层完成新一轮大块拆分并清理冗余兼容层：
    - embedding 计算链路归位到 `visualization/plotting/rendering/embedding/`（`algorithm.py`、`dataframe.py`、`compute_ml.py`、`compute_geochem.py`、`compute_ternary.py`）。
    - 通用渲染 helper 归位到 `visualization/plotting/rendering/common/`（`state_access.py`、`legend.py`、`scatter.py`、`title.py`）。
    - raw 渲染归位到 `visualization/plotting/rendering/raw/`（`plot2d.py`、`plot3d.py`）。
    - 已移除无调用的兼容门面文件（旧的 `embedding_*`、`raw_plot_*`、`helpers`/`*_helpers` 等平铺门面），内部调用统一指向子目录实现。
    - 已进一步移除 visualization 内无调用兼容层：`event_handlers/selection_interaction.py`、`plotting/geochem/isochron_overlays.py`、`plotting/geochem/isochron_rendering.py`；`plotting/geo.py` 改为直接导入底层实现模块。
    - Plumbotectonics 叠加能力按职责拆分为 `plotting/geochem/plumbotectonics_metadata.py`、`plotting/geochem/plumbotectonics_curves.py`、`plotting/geochem/plumbotectonics_isoage.py`，并删除旧单体 `plotting/geochem/plumbotectonics.py`。
    - `core/state.py` 初始化职责完成模块化下沉：新增 `core/state_bootstrap.py` 承载 KDE 覆盖层样式同步与运行期默认状态初始化，`AppState` 入口保留且外部字段行为不变。
    - `core/session.py` 会话迁移规则完成解耦：新增 `core/session_migration.py` 承载算法/渲染模式/列表字段规范化与版本迁移逻辑，`session.py` 聚焦文件 I/O 与持久化编排。
    - `core` 子模块完成目录化迁移：`state.py`/`state_gateway.py`/`state_bootstrap.py` 迁移到 `core/state/`（`app_state.py`、`gateway.py`、`bootstrap.py`），`session.py`/`session_migration.py` 迁移到 `core/session/`（`io.py`、`migration.py`），并在子包 `__init__.py` 中补齐显式 `__all__` 导出。
    - 异步 embedding 计算当前保留在 `visualization/embedding_worker.py` 单文件实现，避免过度拆分导致可读性下降。
    - 目标达成：降低平铺文件噪音与导入歧义，进一步提升渲染层可维护性。

## 阶段进展（2026-04-01 · V1V2 一致性修复）

- 已完成 V1V2 与文献实现一致性的关键修复与回归保护：
    - 修复 `GeochemistryEngine` 预设参数更新缺陷：`v1v2_formula` 现在可被正确写入和切换，`V1V2 (Zhu 1993)` 预设可稳定触发 Zhu(1993) 直接系数分支。
    - 为非 Zhu 模型补充显式 `v1v2_formula='default'`，避免模型切换后公式状态残留。
    - 修复菜单对话框模式下 Data 面板的地球化学模型自动同步失效：切换到 `V1V2` 可自动应用 `V1V2 (Zhu 1993)`，切回 Pb 演化图自动恢复 `Stacey & Kramers (2nd Stage)`。
    - 新增回归测试 `tests/test_geochem_model_sync.py`，覆盖“无 GeoPanel 引用时的模型自动同步”场景。
    - 同步清理一个历史状态写入守卫违规点：`embedding_plot.py` 中 `ternary_ranges` 改为通过 `state_gateway` 写入。

## 阶段进展（2026-04-02 · V1V2 投影口径统一）

- 根据业务决策，`V1V2 (Zhu 1993)` 的坐标计算改为与 Geokit 一致：统一走 `a/b/c` 回归平面投影路径，不再使用直接系数分支。
- 更新 `docs/geochemistry.md` 中 Zhu1993 与 V1V2 方法描述，反映“统一平面投影实现”。
- 增加回归测试，确保 `v1v2_formula='zhu1993'` 与 `default` 在相同 `a/b/c` 下得到一致的 `V1/V2` 结果。
- 调整单阶段 Delta 计算的年龄截断策略：Geokit 与 Zhu1993 均在进入 Delta 计算前执行 `t = max(t, 0)`，避免负年龄进入参考曲线计算。

## 阶段进展（2026-04-02 · 地球化学参数语义收敛）

- 模型参考反演逻辑改为按 `age_model` 自动选择参考参数：
    - `two_stage` 使用 `(a1,b1,c1,T1)`
    - `single_stage` 使用 `(a0,b0,c0,T2)`
- 因此单阶段模型的 `calculate_model_mu/kappa` 与初始比值反演不再依赖 `a1/b1/c1`。
- Geo 面板新增模型语义可见性：
    - 单阶段仅 Geokit 显示 `T1+T2`，其余单阶段仅显示 `T2`
    - 单阶段隐藏 `a1/b1/c1` 与 `Tsec`
    - 双阶段保留完整参数显示
    - 应用参数时仅提交当前可见参数，避免无效参数写入。

## 阶段进展（2026-04-02 · StateStore 首批状态域落地）

- 新增 `core/state/store.py`，提供 `dispatch(action)` 与 `snapshot()`，首批托管状态域：
    - `render_mode`
    - `selected_indices`
    - `export_image_options`
- `AppState` 初始化接入 `state_store`，并补充 `export_image_options` 运行期默认值。
- `AppStateGateway` 已接入 StateStore 分发：
    - `set_render_mode`
    - `set_selected_indices` / `add_selected_indices` / `remove_selected_indices` / `clear_selected_indices`
    - `set_export_image_options` / `get_export_image_options`
    - `set_attr/set_attrs` 对上述域做兼容桥接，保留旧调用入口。
- 导出面板已接入导出选项状态桥接：
    - 面板构建时读取 `export_image_options` 作为初始值
    - 解析保存参数时同步回写到 StateStore
- 新增测试 `tests/test_state_store.py` 覆盖首批状态域行为与归一化规则。
- 第二批状态域继续迁移（列选择与可见组）：
    - `selected_2d_cols/selected_3d_cols/selected_ternary_cols`
    - `selected_2d_confirmed/selected_3d_confirmed/selected_ternary_confirmed`
    - `available_groups/visible_groups`
    - `AppStateGateway` 的 `reset_column_selection`、`set_selected_*_columns`、`sync_available_and_visible_groups`、`set_visible_groups` 已改为通过 StateStore action 分发。
- 第三批状态域继续迁移（数据加载链路）：
    - `df_global/file_path/sheet_name`
    - `group_cols/data_cols/last_group_col`
    - `data_version`（含 embedding cache 失效）
    - `AppStateGateway` 的 `set_dataframe_and_source`、`set_group_data_columns`、`set_last_group_col`、`bump_data_version` 已改为通过 StateStore action 分发。
- 第四批状态域继续迁移（选择交互链路）：
    - `selection_mode/selection_tool`
    - `AppStateGateway` 的 `clear_selection`、`disable_selection_mode`、`set_selection_tool` 已改为通过 StateStore action 分发。
    - `set_attr` 对 `selection_mode/selection_tool` 的兼容桥接已接入。
- 第五批状态域继续迁移（会话偏好链路）：
    - `algorithm/point_size/tooltip_columns/ui_theme/preserve_import_render_mode`
    - `AppStateGateway` 新增显式写入入口：`set_algorithm`、`set_point_size`、`set_tooltip_columns`、`set_ui_theme`。
    - `ui/app_parts/session.py` 会话恢复链路已改为优先调用显式 gateway 方法，减少 `set_attr` 隐式写入路径。
- 第六批状态域继续迁移（KDE 分析链路）：
        - `show_kde/show_marginal_kde`
        - `marginal_kde_top_size/marginal_kde_right_size`
        - `marginal_kde_max_points/marginal_kde_bw_adjust/marginal_kde_gridsize/marginal_kde_cut/marginal_kde_log_transform`
        - `StateStore` 新增 KDE 相关 action 归一化与同步回写，`AppStateGateway` 新增显式 API：
            `set_show_kde`、`set_show_marginal_kde`、`set_marginal_kde_layout`、`set_marginal_kde_compute_options`。
        - `ui/panels/analysis/equations.py` KDE 参数保存链路改为显式 gateway API，减少散落 `set_attr` 写入。
        - `tests/test_state_store.py` 新增 KDE 状态域回归测试。
    - 第七批状态域继续迁移（方程叠加开关）：
        - `show_equation_overlays`
        - `StateStore` 新增方程叠加开关 action，`AppStateGateway` 新增 `set_show_equation_overlays`。
        - 分析面板方程开关改为显式 gateway API；新增状态回归测试覆盖显式 API 与兼容 `set_attr` 桥接。
    - 第八批状态域继续迁移（Tooltip 显示开关）：
        - `show_tooltip`
        - `StateStore` 新增 tooltip 显示开关 action，`AppStateGateway` 新增 `set_show_tooltip`。
        - `ui/panels/analysis/selection.py` 与 `ui/panels/data/grouping.py` tooltip 开关改为显式 gateway API。
        - `tests/test_state_store.py` 新增 tooltip 显示开关回归测试，覆盖显式 API 与兼容桥接。
    - 第九批状态域继续迁移（分组列兼容桥接清理）：
        - `group_cols/data_cols` 的 `set_attr` 兼容路径改为转发 `set_group_data_columns`，避免旁路 StateStore。
        - `ui/panels/data/grouping.py` 分组列应用动作改为显式 `set_group_data_columns`。
        - `tests/test_state_store.py` 新增兼容桥接回归测试，验证 `set_attr("group_cols"/"data_cols")` 不会破坏已托管域一致性。
    - 第十批迁移清理（Tooltip 列配置写入路径）：
        - `ui/panels/analysis/selection.py` 与 `ui/panels/data/grouping.py` 的 tooltip 列配置从 `set_attr("tooltip_columns")` 改为显式 `set_tooltip_columns`。
        - 进一步减少 UI 层对通用 `set_attr` 的依赖，统一走已托管域显式 API。
    - 第十一批迁移清理（运行期 UI 引用与标记写入）：
        - `core/state/gateway.py` 新增显式 API：`set_paleo_label_refreshing`、`set_control_panel_ref`。
        - `ui/app_parts/plotting.py` 与 `ui/control_panel.py` 对应写入改为显式 API，不再通过 `set_attr` 间接写入。
        - `set_attr` 为上述字段保留兼容转发，确保旧调用路径行为一致。
    - 第十二批迁移清理（地化模型写入路径）：
        - `core/state/gateway.py` 新增 `set_geo_model_name`。
        - `ui/panels/data/grouping.py`、`ui/panels/geo_panel.py` 与 `tests/test_geochem_model_sync.py` 改为显式模型写入 API。
    - 第十三批迁移清理（data_version 显式写入）：
        - `core/state/gateway.py` 新增 `set_data_version`，并接入 `set_attr` 兼容转发。
        - `tests/test_state_store.py` 状态恢复改为显式 API。
    - 第十四批迁移清理（置信椭圆参数写入）：
        - `core/state/gateway.py` 新增 `set_confidence_level`。
        - `ui/panels/analysis/selection.py` 改为显式 API。
    - 第十五批迁移清理（图例回调注册）：
        - `core/state/gateway.py` 新增 `set_legend_update_callback`。
        - `ui/main_window.py` 初始化回调注册改为显式 API。
    - 第十六批迁移清理（Figure/Canvas 引用写入）：
        - `core/state/gateway.py` 新增 `set_figure`、`set_canvas`。
        - `ui/main_window_parts/canvas.py` 改为显式 API。
    - 第十七批迁移清理（Axes/Legend Axes 写入）：
        - `core/state/gateway.py` 新增 `set_axis`、`set_legend_ax`。
        - `visualization/plotting/core.py` 轴对象写入改为显式 API。
    - 第十八批迁移清理（PCA 诊断元数据）：
        - `core/state/gateway.py` 新增 `set_pca_diagnostics`。
        - `visualization/plotting/core.py` 与 `visualization/plotting/rendering/embedding/compute_ml.py` 诊断字段写入统一为显式 API。
    - 第十九批迁移清理（当前调色板写入）：
        - `core/state/gateway.py` 新增 `set_current_palette`。
        - `visualization/plotting/core.py` 调色板初始化改为显式 API。
    - 第二十批迁移清理（adjustText 运行标记）：
        - `core/state/gateway.py` 新增 `set_adjust_text_in_progress`。
        - `visualization/plotting/label_layout.py` 运行标记写入改为显式 API。
    - 第二十一批迁移清理（叠加标签刷新标记）：
        - `core/state/gateway.py` 新增 `set_overlay_label_refreshing`。
        - `visualization/plotting/geochem/isochron_labels.py` 刷新标记写入改为显式 API。
    - 第二十二批迁移清理（当前图标题写入）：
        - `core/state/gateway.py` 新增 `set_current_plot_title`。
        - `rendering/common/title.py`、`rendering/raw/plot2d.py`、`rendering/raw/plot3d.py` 标题写入改为显式 API。
    - 第二十三批迁移清理（annotation 写入）：
        - `core/state/gateway.py` 新增 `set_annotation`。
        - `rendering/raw/plot2d.py`、`rendering/raw/plot3d.py` 注释对象写入改为显式 API。
    - 第二十四批迁移清理（last_2d_cols 写入）：
        - `core/state/gateway.py` 新增 `set_last_2d_cols`。
        - `rendering/raw/plot2d.py` 最近 2D 轴列记录改为显式 API。
    - 第二十五批迁移清理（最近文件列表）：
        - `core/state/gateway.py` 新增 `set_recent_files`。
        - `ui/dialogs/data_import/workflow.py` 最近文件更新改为显式 API。
    - 第二十六批迁移清理（语言切换写入）：
        - `core/state/gateway.py` 新增 `set_language_code`。
        - `ui/dialogs/file_dialog.py`、`ui/dialogs/data_import/build.py` 语言写入改为显式 API。
    - 第二十七批迁移清理（line_styles 写入）：
        - `core/state/gateway.py` 新增 `set_line_styles`。
        - `ui/dialogs/line_style_dialog.py` 与 `ui/panels/display/themes.py` 对应写入改为显式 API。
    - 第二十八批迁移清理（saved_themes 写入）：
        - `core/state/gateway.py` 新增 `set_saved_themes`。
        - `ui/panels/display/themes.py` 主题加载/初始化写入改为显式 API。
    - 第二十九批迁移清理（图例样式参数）：
        - `core/state/gateway.py` 新增 `set_color_scheme`、`set_legend_position`、`set_legend_location`、`set_legend_columns`、`set_legend_nudge_step`、`set_legend_offset`。
        - `ui/panels/legend/actions.py` 与 `ui/panels/display/themes.py` 对应写入改为显式 API。
    - 第三十批迁移清理（ui_theme 显式写入）：
        - `ui/panels/display/themes.py` 中 `ui_theme` 写入改为 `set_ui_theme`。
    - 第三十一批迁移清理（等时线/Plumbotectonics 可见性结果写入）：
        - `core/state/gateway.py` 新增 `set_isochron_results`、`set_plumbotectonics_group_visibility`。
        - `ui/main_window_parts/legend_actions.py`、`visualization/plotting/geochem/isochron_fits.py` 对应写入改为显式 API。
        - 第三十二批迁移清理（地化面板显式写入）：
                - `core/state/gateway.py` 新增显式 API：
                    `set_show_model_curves`、`set_show_plumbotectonics_curves`、`set_show_paleoisochrons`、
                    `set_show_model_age_lines`、`set_show_growth_curves`、`set_use_real_age_for_mu_kappa`、
                    `set_mu_kappa_age_col`、`set_plumbotectonics_variant`、`set_paleoisochron_step`、`set_paleoisochron_ages`。
                - `ui/panels/data/geochem.py` 对应状态写入改为显式 API。
        - 第三十三批迁移清理（叠加标签容器写入）：
                - `core/state/gateway.py` 新增 `set_overlay_artists`、`set_overlay_curve_label_data`、
                    `set_paleoisochron_label_data`、`set_plumbotectonics_isoage_label_data`。
                - `visualization/plotting/geochem/overlay_common.py`、`paleoisochron_overlays.py`、
                    `plumbotectonics_isoage.py` 对应写入改为显式 API。
        - 第三十四批迁移清理（投影与三元参数写入）：
                - `core/state/gateway.py` 新增 `standardize_data`、`pca_component_indices`、
                    ternary limit/manual/stretch 相关显式 setter，并在 `set_attr` 中添加兼容分发。
                - `ui/panels/data/projection.py` 将对应固定字段写入从 `set_attr` 迁移到显式 API。
        - 第三十五批迁移清理（线型/混合/图例顺序固定字段）：
                - `core/state/gateway.py` 新增线型宽度、`isochron_label_options`、
                    `mixing_endmembers`/`mixing_mixtures`、`custom_palettes`/`custom_shape_sets`、
                    `legend_item_order`、`ternary_ranges` 等显式 setter。
                - `ui/dialogs/line_style_dialog.py`、`ui/panels/analysis/mixing.py`、
                    `ui/panels/legend/editors.py`、`ui/main_window_parts/legend_core.py`、
                    `visualization/plotting/rendering/embedding_plot.py` 改为显式 API 调用。
        - 第三十六批迁移清理（生产代码剩余动态入口）：
                - `core/state/gateway.py` 新增 `set_kde_style`、`set_marginal_kde_style`、
                    `set_overlay_toggle`，并在 `set_attr` 添加兼容分发。
                - `ui/main_window_parts/legend_actions.py` overlay toggle 改为 `set_overlay_toggle`。
                - `ui/panels/analysis/equations.py` legacy KDE 样式写入改为显式 API。
        - 第三十七批迁移清理（embedding 快照写入）：
                - `core/state/gateway.py` 新增 `set_last_embedding(embedding, embedding_type)`，
                    并为 `last_embedding`/`last_embedding_type` 添加兼容分发。
                - `visualization/plotting/core.py`、`rendering/embedding/compute_geochem.py`、
                    `rendering/embedding/compute_ml.py`、`rendering/embedding/compute_ternary.py`
                    将 embedding 快照写入从 `set_attrs` 迁移到显式 API。
        - 第三十八批迁移清理（会话/图例/三元与等时线设置）：
                - `core/state/gateway.py` 新增 `set_file_path`、`set_sheet_name`、`set_ternary_factors`、
                    `set_legend_snapshot`、`set_isochron_error_columns`、`set_isochron_error_fixed`，
                    并为 `ternary_factors` 添加兼容分发。
                - `ui/app.py`、`ui/app_parts/session.py`、`ui/panels/data/projection.py`、
                    `ui/panels/data/geochem.py`、`ui/panels/display/themes.py`、`ui/panels/legend/build.py`、
                    `visualization/plotting/rendering/common/legend.py` 对应 `set_attrs` 调用迁移到显式 API。
                - `visualization/plotting/core.py` RobustPCA 分支诊断写入改为 `set_pca_diagnostics`。
        - 第三十九批迁移清理（ML/方程叠加固定写入）：
                - `core/state/gateway.py` 新增 `set_ml_last_result`、`set_ml_last_model_meta`、
                    `set_equation_overlays`，并在 `set_attr` 中添加兼容分发。
                - `ui/dialogs/provenance_ml/workflow.py` 与 `ui/panels/analysis/equations.py`
                    将固定字段 `set_attrs` 调用迁移到显式 API。
        - 第四十批迁移清理（面板样式批量写入收口）：
            - `core/state/gateway.py` 新增 `set_panel_style_updates(updates)` 专用入口。
            - `ui/panels/base_panel.py` 将样式字典写入从 `set_attrs` 迁移到专用显式 API。
        - 第四十一批迁移清理（防回退守护）：
                - 新增 `scripts/check_gateway_generic_mutations.py`，扫描生产目录
                    `application/core/data/ui/visualization` 中 `state_gateway.set_attr/set_attrs` 调用。
                - 新增 `tests/test_gateway_generic_mutation_guard.py`，在 CI/本地 pytest 中
                    强制 `TOTAL=0`，避免后续重构回退到通用写入口。
        - 第四十二批迁移清理（测试侧显式 API 对齐）：
                - `tests/test_state_store.py` 的通用入口调用最小化：
                  `_restore_state` 从 `set_attrs` 改为显式 `set_algorithm`/`set_selection_mode`，
                  tooltip/equation 覆盖测试改为显式 setter；
                  仅保留 `group_cols/data_cols` 兼容性专用测试使用 `set_attr`。
                - 第四十三批迁移清理（测试通用入口白名单守护）：
                                - 将 `group_cols/data_cols` 的 `set_attr` 兼容性校验拆分到
                                    `tests/test_gateway_set_attr_compatibility.py`。
                                - 新增 `scripts/check_gateway_generic_mutations_in_tests.py`，限制测试目录中
                                    `state_gateway.set_attr/set_attrs` 仅可出现在兼容性专用测试。
                                - 新增 `tests/test_gateway_generic_mutation_test_guard.py`，强制该守护规则生效。
                - 第四十四批迁移清理（线宽同步一致性修复）：
                                - `ui/panels/base_panel.py` 更新样式面板线宽同步逻辑：
                                    写回 `line_styles` 时优先使用本次 `style_updates` 新值，
                                    避免同一轮交互内读取到旧的 `app_state.*_width`。
                                - 第四十五批迁移清理（网关兼容分发结构化）：
                                                                - `core/state/gateway.py` 的 `set_attr` 兼容桥接从长 if 链
                                                                    重构为集中式 dispatch table（`_build_compat_attr_handlers`），
                                                                    保持行为不变并降低后续维护成本。
                                                                - `tests/test_gateway_set_attr_compatibility.py` 增加
                                                                    `show_tooltip` 兼容分发回归用例，覆盖 dispatch table 路径。
                                - 第四十六批迁移清理（兼容分发彻底收口）：
                                                                - `core/state/gateway.py` 新增 `_set_group_cols_compat`、
                                                                    `_set_data_cols_compat`、`_set_export_image_options_compat`，
                                                                    并将 `group_cols/data_cols/export_image_options` 纳入统一 dispatch table。
                                                                - `set_attr` 只保留“映射分发 + 默认 setattr”两段逻辑。
                                                                - `tests/test_gateway_set_attr_compatibility.py` 新增
                                                                    `export_image_options` 兼容路径回归测试。
                                - 第四十七批迁移清理（守护脚本去重）：
                                                                - 新增共享扫描模块 `scripts/gateway_mutation_guard.py`，
                                                                    收敛 generic gateway 调用扫描与结果输出逻辑。
                                                                - `scripts/check_gateway_generic_mutations.py` 与
                                                                    `scripts/check_gateway_generic_mutations_in_tests.py`
                                                                    改为复用共享模块，去除重复扫描实现。
                                - 第四十八批迁移清理（守护测试去重）：
                                                                - 新增 `tests/guard_helpers.py`，统一封装 guard 脚本执行与断言。
                                                                - `tests/test_state_mutation_guard.py`、
                                                                    `tests/test_gateway_generic_mutation_guard.py`、
                                                                    `tests/test_gateway_generic_mutation_test_guard.py`
                                                                    改为复用共享 helper，移除重复 subprocess 模板代码。
                                - 第四十九批迁移清理（守护扫描与用例参数化）：
                                                                - 新增 `scripts/source_scan_guard.py` 作为通用源码扫描底座。
                                                                - `scripts/check_state_mutations.py` 与
                                                                    `scripts/gateway_mutation_guard.py` 复用该底座，
                                                                    统一扫描与输出流程。
                                                                - 新增参数化守护测试 `tests/test_guard_scripts.py`，
                                                                    合并原 3 个独立守护测试文件并移除重复实现。
                                - 第五十批迁移清理（overlay toggle 路由结构化）：
                                                                - `core/state/gateway.py` 为 `set_overlay_toggle` 新增
                                                                    `_overlay_toggle_handlers` 分发表，替换 if 链路由实现。
                                                                - `tests/test_gateway_set_attr_compatibility.py` 新增参数化回归，
                                                                    覆盖已知 overlay 开关路由与未知字段兜底赋值路径。
                                - 第五十一批迁移清理（兼容分发表声明式重构）：
                                                                - `core/state/gateway.py` 的 `set_attr` 兼容映射改为
                                                                    分组声明式构建（direct/bool/int/float/str + special handlers），
                                                                    并引入 `_compat_handler` 统一包装转换逻辑。
                                                                - `tests/test_gateway_set_attr_compatibility.py` 增加
                                                                    `point_size/ui_theme/confidence_level` 转换路径回归测试。
                                - 第五十二批迁移清理（守护扫描底座测试覆盖）：
                                                                - 新增 `tests/test_source_scan_guard.py`，覆盖
                                                                    `scan_pattern_hits` 的计数与 allowlist 行为，
                                                                    以及 `print_scan_result` 的输出格式与排序稳定性。
                                - 第五十三批迁移清理（图例与语言偏好纳入 StateStore）：
                                                                - `core/state/store.py` 新增语言与图例偏好状态域：
                                                                    `language`、`color_scheme`、`legend_position`、
                                                                    `legend_location`、`legend_columns`、`legend_nudge_step`、`legend_offset`。
                                                                - `core/state/gateway.py` 的对应显式 API
                                                                    `set_language_code`、`set_color_scheme`、
                                                                    `set_legend_*` 改为通过 StateStore action 分发。
                                                                - 新增/扩展回归测试，覆盖显式 setter 与兼容
                                                                    `set_attr` 写入后 Store 快照一致性。
                                - 第五十四批迁移清理（最近文件与主题样式纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `recent_files`、`line_styles`、`saved_themes`。
                                                                - `core/state/gateway.py` 的 `set_recent_files`、
                                                                    `set_line_styles`、`set_saved_themes` 改为
                                                                    通过 StateStore action 分发。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与兼容 `set_attr` 的 Store 一致性。
                                - 第五十五批迁移清理（自定义样式配置纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `custom_palettes`、`custom_shape_sets`、`legend_item_order`。
                                                                - `core/state/gateway.py` 的 `set_custom_palettes`、
                                                                    `set_custom_shape_sets`、`set_legend_item_order` 改为
                                                                    通过 StateStore action 分发。
                                                                - `ui/panels/legend/editors.py` 自定义调色板/形状集
                                                                    写入改为显式 gateway API，避免旁路 Store。
                                                                - 扩展状态与兼容测试，覆盖显式 setter 与 `set_attr`
                                                                    在上述三域上的快照一致性。
                                - 第五十六批迁移清理（混合组与三元范围纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `mixing_endmembers`、`mixing_mixtures`、`ternary_ranges`。
                                                                - `core/state/gateway.py` 的 `set_mixing_endmembers`、
                                                                    `set_mixing_mixtures`、`set_ternary_ranges` 改为
                                                                    通过 StateStore action 分发。
                                                                - `ui/panels/analysis/mixing.py` 设置端元/混合组改为
                                                                    “拷贝-更新-gateway 写回”，避免字典原地修改旁路 Store。
                                                                - `visualization/plotting/rendering/embedding/compute_ternary.py`
                                                                    清理三元范围改为 `state_gateway.set_ternary_ranges({})`，
                                                                    保证 Store 快照与运行态同步。
                                                                - 扩展状态与兼容测试，覆盖显式 setter 与 `set_attr`
                                                                    在上述三域上的一致性。
                                - 第五十七批迁移清理（KDE 样式与 ML 结果纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `kde_style`、`marginal_kde_style`、
                                                                    `ml_last_result`、`ml_last_model_meta`。
                                                                - `core/state/gateway.py` 的 `set_kde_style`、
                                                                    `set_marginal_kde_style`、`set_ml_last_result`、
                                                                    `set_ml_last_model_meta` 改为通过
                                                                    StateStore action 分发。
                                                                - 扩展状态与兼容测试，覆盖显式 setter 与 `set_attr`
                                                                    在上述四域上的快照一致性。
                                - 第五十八批迁移清理（投影与三元配置纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `standardize_data`、`pca_component_indices`、
                                                                    `ternary_auto_zoom`、`ternary_limit_mode`、
                                                                    `ternary_limit_anchor`、`ternary_boundary_percent`、
                                                                    `ternary_manual_limits_enabled`、`ternary_manual_limits`、
                                                                    `ternary_stretch_mode`、`ternary_stretch`、`ternary_factors`。
                                                                - `core/state/gateway.py` 对应显式 API
                                                                    `set_standardize_data`、`set_pca_component_indices`、
                                                                    `set_ternary_*` 系列改为 action dispatch。
                                                                - `StateStore` 为上述字段新增归一化规则，
                                                                    统一三元参数范围与 `ternary_factors` 列表语义。
                                                                - 扩展状态与兼容测试，覆盖显式 setter 与 `set_attr`
                                                                    在上述域上的快照一致性。
                                - 第五十九批迁移清理（方程与等时线样式配置纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `model_curve_width`、`plumbotectonics_curve_width`、
                                                                    `paleoisochron_width`、`model_age_line_width`、
                                                                    `isochron_line_width`、`selected_isochron_line_width`、
                                                                    `isochron_label_options`、`equation_overlays`。
                                                                - `core/state/gateway.py` 对应显式 API
                                                                    `set_*_width`、`set_isochron_label_options`、
                                                                    `set_equation_overlays` 改为 action dispatch。
                                                                - `ui/dialogs/line_style_dialog.py` 的等时线标签选项
                                                                    写入改为汇总后通过 gateway 一次回写，避免原地修改。
                                                                - `ui/panels/analysis/equations.py` 的单条方程开关改为
                                                                    复制列表后通过 gateway 回写，避免原地修改旁路 Store。
                                                                - 扩展状态与兼容测试，覆盖上述域的显式 setter 与
                                                                    `set_attr` 快照一致性。
                                - 第六十批迁移清理（地化叠加可见性开关纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `show_model_curves`、`show_plumbotectonics_curves`、
                                                                    `show_paleoisochrons`、`show_model_age_lines`、
                                                                    `show_growth_curves`、`show_isochrons`。
                                                                - `core/state/gateway.py` 对应显式 API
                                                                    `set_show_model_curves`、`set_show_plumbotectonics_curves`、
                                                                    `set_show_paleoisochrons`、`set_show_model_age_lines`、
                                                                    `set_show_growth_curves`、`set_show_isochrons`
                                                                    改为 action dispatch，并将 `show_isochrons`
                                                                    纳入 `set_attr` 兼容分发。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 在上述开关域上的一致性。
                                - 第六十一批迁移清理（地化参数域纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `use_real_age_for_mu_kappa`、`mu_kappa_age_col`、
                                                                    `plumbotectonics_variant`、`paleoisochron_step`、
                                                                    `paleoisochron_ages`。
                                                                - `core/state/gateway.py` 对应显式 API
                                                                    `set_use_real_age_for_mu_kappa`、`set_mu_kappa_age_col`、
                                                                    `set_plumbotectonics_variant`、`set_paleoisochron_step`、
                                                                    `set_paleoisochron_ages` 改为 action dispatch。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 在上述参数域上的一致性。
                                - 第六十二批迁移清理（等时线误差配置域纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `isochron_error_mode`、`isochron_sx_col`、
                                                                    `isochron_sy_col`、`isochron_rxy_col`、
                                                                    `isochron_sx_value`、`isochron_sy_value`、`isochron_rxy_value`。
                                                                - `core/state/gateway.py` 的 `set_isochron_error_columns`、
                                                                    `set_isochron_error_fixed` 改为 action dispatch，
                                                                    并为 `set_attr` 增加等时线误差字段兼容桥接，
                                                                    避免旁路 Store 导致快照不一致。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 在该域上的一致性。
                                - 第六十三批迁移清理（地化模型名纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：`geo_model_name`，
                                                                    并补充 `SET_GEO_MODEL_NAME` action 的 dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 的 `set_geo_model_name`
                                                                    改为 action dispatch，避免旁路 Store。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 在该域上的一致性。
                                - 第六十四批迁移清理（门控业务域收口到 dispatch）：
                                                                - `core/state/store.py` 新增状态域并接入 action/snapshot/sync：
                                                                    `paleo_label_refreshing`、`overlay_label_refreshing`、
                                                                    `adjust_text_in_progress`、`confidence_level`、
                                                                    `current_palette`、`current_plot_title`、`last_2d_cols`、
                                                                    `isochron_results`、`plumbotectonics_group_visibility`、
                                                                    `draw_selection_ellipse`。
                                                                - 新增 action：`SET_FILE_PATH`、`SET_SHEET_NAME`、`SET_DATA_VERSION`，
                                                                    对应 `set_file_path`/`set_sheet_name`/`set_data_version`
                                                                    改为 dispatch，避免 bypass 已托管域。
                                                                - `core/state/gateway.py` 将上述业务 setter
                                                                    全部迁移到 dispatch，仅保留运行期对象引用类字段直写
                                                                    （如 fig/canvas/selector/worker 等）。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖新增业务域的快照一致性与 `set_attr` 兼容路径。
                                - 第六十五批迁移清理（initial_render_done 纳入 StateStore）：
                                                                - `core/state/store.py` 新增 `initial_render_done`
                                                                    状态域及 `SET_INITIAL_RENDER_DONE` action，
                                                                    补齐 snapshot/sync。
                                                                - `core/state/gateway.py` 的 `set_initial_render_done`
                                                                    改为 action dispatch，并在 `set_attr` 兼容映射中
                                                                    增加 `initial_render_done`。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖该域在显式 setter 与 `set_attr` 路径下的一致性。
                                - 第六十六批迁移清理（门控直写白名单守护）：
                                                                - 新增 `scripts/check_gateway_direct_state_assignments.py`，
                                                                    扫描 `core/state/gateway.py` 中
                                                                    `self._state.<field> = ...` 直写，仅允许运行期对象字段。
                                                                - 将 `export_image_options` 非 dict 兼容分支
                                                                    从直写改为安全调用显式 setter，避免旁路 StateStore。
                                                                - `tests/test_guard_scripts.py` 纳入新守护脚本，
                                                                    持续防止业务状态回退到 gateway 直写路径。
                                - 第六十七批迁移清理（overlay toggle 未知键收口）：
                                                                - `core/state/gateway.py` 的 `set_overlay_toggle`
                                                                    移除未知 attr 的兜底直写路径，改为仅允许
                                                                    `OVERLAY_TOGGLE_MAP` 映射内字段并记录告警。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    同步更新兼容预期：未知 overlay 键不再创建
                                                                    动态状态字段，避免绕过托管写入口。
                                - 第六十八批迁移清理（图例颜色/形状写入收口）：
                                                                - `ui/main_window_parts/legend_actions.py`
                                                                    将分组颜色与形状的字典就地修改改为
                                                                    `state_gateway.set_palette_and_marker_map(...)`，
                                                                    避免 UI 层绕过 gateway 直接改共享状态。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    新增回归，验证 `set_palette_and_marker_map`
                                                                    同步更新 `app_state.current_palette` 与
                                                                    `state_store` 快照一致性。
                                - 第六十九批迁移清理（group_marker_map 纳入 StateStore）：
                                                                - `core/state/store.py` 新增
                                                                    `group_marker_map` 状态域与
                                                                    `SET_GROUP_MARKER_MAP` action，
                                                                    并接入 snapshot/sync。
                                                                - `core/state/gateway.py`
                                                                    新增 `set_group_marker_map`，
                                                                    `set_palette_and_marker_map` 改为
                                                                    palette 与 marker map 双 dispatch。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 兼容路径。
                                - 第七十批迁移清理（overlay label state 受控键收口）：
                                                                - `core/state/gateway.py` 的
                                                                    `set_overlay_label_state` 改为
                                                                    白名单键更新，仅允许
                                                                    `paleoisochron_label_data`、
                                                                    `plumbotectonics_label_data`、
                                                                    `plumbotectonics_isoage_label_data`、
                                                                    `overlay_curve_label_data`。
                                                                - 未知键改为告警并忽略，防止
                                                                    动态属性写入绕过网关边界。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    新增已知键更新与未知键忽略回归测试。
                                - 第七十一批迁移清理（overlay label 显式 setter 对齐）：
                                                                - `core/state/gateway.py` 新增
                                                                    `set_plumbotectonics_label_data`，
                                                                    并将 `set_overlay_label_state`
                                                                    改为通过 setter 映射分发，移除
                                                                    该路径上的动态 `setattr` 写入。
                                                                - `set_attr` 兼容映射新增
                                                                    `plumbotectonics_label_data`
                                                                    到显式 setter 的转发。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    白名单同步新增该字段。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    新增该兼容路径回归测试。
                                - 第七十二批迁移清理（set_attr 未知键彻底收口）：
                                                                - `core/state/gateway.py` 的
                                                                    `set_attr` 移除未知键直写旁路，
                                                                    改为记录告警并忽略，避免
                                                                    动态属性注入。
                                                                - `set_panel_style_updates` 改为
                                                                    受控更新：优先走兼容映射，
                                                                    否则仅允许更新 `app_state`
                                                                    已有字段，未知键忽略并告警。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    新增 `set_attr` 未知键忽略与
                                                                    panel style update 受控更新回归。
                                - 第七十三批迁移清理（panel style 回退白名单化）：
                                                                - `core/state/gateway.py`
                                                                    新增 panel style 回退键白名单，
                                                                    `set_panel_style_updates` 仅允许
                                                                    白名单样式键走直写回退。
                                                                - 同时增加 panel style 总白名单门禁，
                                                                    样式入口先过滤键，再决定是否
                                                                    走兼容映射或直写回退。
                                                                - 即使是 `app_state` 已存在字段，
                                                                    若不在样式白名单内也会被忽略并告警，
                                                                    防止样式入口误写业务状态。
                                                                - `tests/test_gateway_set_attr_compatibility.py`
                                                                    扩展回归：验证已有但非样式字段
                                                                    不会通过 panel style 路径被修改。
                                - 第七十四批迁移清理（三元分类散点颜色容错与调色板同步）：
                                                                - `visualization/plotting/core.py`
                                                                    `_build_group_palette` 改为本地构建后
                                                                    通过 `state_gateway.set_current_palette` 回写，
                                                                    避免运行态调色板与 StateStore 快照失步。
                                                                - `visualization/plotting/rendering/common/scatter.py`
                                                                    分类散点取色从直接索引改为安全回退，
                                                                    并支持显式传入本轮渲染 palette，
                                                                    避免分类键缺失触发异常导致整类点丢失。
                                                                - `visualization/plotting/rendering/embedding_plot.py`
                                                                    调用散点渲染时显式传入 `new_palette`，
                                                                    保证同一轮渲染使用一致调色板视图。
                                                                - `tests/test_state_store.py`
                                                                    新增 `_build_group_palette` 回归测试，
                                                                    校验 palette 运行态与 Store 快照同步。
                                                                - 运行日志复核未再出现
                                                                    `Error plotting category` / `No data points plotted`。
                                - 第七十五批迁移清理（overlay 标签数据域纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `overlay_curve_label_data`、
                                                                    `paleoisochron_label_data`、
                                                                    `plumbotectonics_label_data`、
                                                                    `plumbotectonics_isoage_label_data`，
                                                                    并接入 dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 的
                                                                    `set_overlay_curve_label_data`、
                                                                    `set_paleoisochron_label_data`、
                                                                    `set_plumbotectonics_label_data`、
                                                                    `set_plumbotectonics_isoage_label_data`
                                                                    改为 action dispatch，移除业务域直写。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter、`set_attr` 兼容路径及
                                                                    `set_overlay_label_state` 的 Store 快照一致性。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    直写白名单移除上述 4 个标签数据字段，
                                                                    防止后续回退为 gateway 直写。
                                - 第七十六批迁移清理（PCA 诊断与图例快照纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `last_pca_variance`、`last_pca_components`、
                                                                    `current_feature_names`、`legend_last_title`、
                                                                    `legend_last_handles`、`legend_last_labels`，
                                                                    并接入 dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 的
                                                                    `set_pca_diagnostics` 与 `set_legend_snapshot`
                                                                    改为 action dispatch。
                                                                - `set_pca_diagnostics` 支持显式清空字段
                                                                    （可传 `None`），用于状态恢复场景。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与 `set_attr` 路径的
                                                                    Store 快照一致性。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    白名单移除上述 6 个字段，持续防止直写回退。
                                - 第七十七批迁移清理（嵌入快照与选中等时线数据纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `last_embedding`、`last_embedding_type`、
                                                                    `selected_isochron_data`，并接入
                                                                    dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 的
                                                                    `set_last_embedding` 与
                                                                    `set_selected_isochron_data`
                                                                    改为 action dispatch。
                                                                - `set_attr` 兼容映射新增
                                                                    `selected_isochron_data` 路由，
                                                                    统一走显式 setter。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与兼容路径的
                                                                    Store 快照一致性。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    白名单移除上述 3 个字段，
                                                                    持续防止 gateway 直写回退。
                                - 第七十八批迁移清理（异步嵌入任务状态纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `embedding_task_token`、
                                                                    `embedding_task_running`，
                                                                    并接入 dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 新增
                                                                    `set_embedding_task_token`、
                                                                    `set_embedding_task_running`，
                                                                    `set_embedding_worker` 内部改为
                                                                    复用上述显式 setter，移除业务域直写。
                                                                - `set_attr` 兼容映射新增
                                                                    `embedding_task_token`、
                                                                    `embedding_task_running` 路由。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与兼容路径的
                                                                    Store 快照一致性。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    白名单移除上述 2 个字段，
                                                                    持续防止直写回退。
                                - 第七十九批迁移清理（叠加图元容器与边缘 KDE 轴状态纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `overlay_artists`、`marginal_axes`，
                                                                    并接入 dispatch/snapshot/sync。
                                                                - `core/state/gateway.py` 的
                                                                    `set_overlay_artists`、`set_marginal_axes`
                                                                    改为 action dispatch，移除业务域直写。
                                                                - `set_attr` 兼容映射新增
                                                                    `marginal_axes` 路由，
                                                                    与 `overlay_artists` 一并走显式 setter。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与兼容路径的
                                                                    Store 快照一致性。
                                                                - `scripts/check_gateway_direct_state_assignments.py`
                                                                    白名单移除上述 2 个字段，
                                                                    持续防止直写回退。
                                - 第八十批迁移清理（活动子集索引纳入 StateStore）：
                                                                - `core/state/store.py` 新增状态域：
                                                                    `active_subset_indices`，
                                                                    并接入 dispatch/snapshot/sync。
                                                                - 增加子集索引归一化：
                                                                    统一为 `set[int] | None`，
                                                                    防止重复值与类型漂移。
                                                                - `core/state/gateway.py` 新增
                                                                    `set_active_subset_indices`，
                                                                    并将 `set_attr("active_subset_indices")`
                                                                    路由到显式 setter。
                                                                - 扩展 `tests/test_state_store.py` 与
                                                                    `tests/test_gateway_set_attr_compatibility.py`，
                                                                    覆盖显式 setter 与兼容路径的
                                                                    Store 快照一致性。
                                - 第八十一批迁移清理（兼容视图 setter 去旁路）：
                                                                - `core/state/app_state.py` 中
                                                                    `DataState`、`AlgorithmState`、
                                                                    `StyleState`、`InteractionState`
                                                                    的托管字段 setter 改为优先
                                                                    通过 `state_store.dispatch` 更新，
                                                                    避免兼容视图直接 `setattr`
                                                                    绕过 StateStore。
                                                                - 保留安全回退：
                                                                    若 `state_store` 尚未初始化，
                                                                    则退回原有 `setattr` 行为。
                                                                - 新增 `tests/test_state_store.py`
                                                                    回归用例，覆盖兼容视图写入路径
                                                                    的 Store 快照一致性。

## 架构现代化改造方案（2026-03-31 新增）

### 0. 现状审计摘要（基于代码检查）

当前工程已经完成部分模块化，但仍处于“单体 + 全局状态驱动”的架构阶段，主要瓶颈如下：

- 全局状态耦合高：`app_state` 仍被大量模块直接读写（跨 `ui/`、`visualization/`、`data/`）。
- 状态职责过重：`core/state.py` 仍承载大量数据、渲染、交互、UI 引用字段（含 `fig/ax`、selector、panel 引用等）。
- 大文件集中：`visualization/plotting/geo.py`（1733 行）、`visualization/plotting/render.py`（1196 行）、`visualization/events.py`（1041 行）、`ui/main_window.py`（1033 行）。
- 边界不清晰：`data/loader.py` 同时处理文件读取、对话框流程、清洗与状态写入，I/O、UI、领域逻辑混杂。
- 存在遗留路径：`Qt5ControlPanel` 标记为 deprecated，但仍保留较多兼容逻辑，增加维护负担。
- 基础设施薄弱：尚未落地自动化测试目录（`tests/` 缺失）与 CI 质量门禁。

### 1. 目标架构（PyQt 单体的现代化分层）

采用“分层整洁架构 + 事件驱动状态管理”的可渐进方案，在不推翻现有 UI 的前提下演进：

```text
presentation (PyQt Widgets/Dialog + ViewModel)
                ↓
application (UseCases / Commands / Queries)
                ↓
domain (Entities / ValueObjects / Domain Services)
                ↓
infrastructure (Pandas IO / Matplotlib adapter / Session store / Plugin loader)
```

关键原则：

1. 依赖方向只允许由外向内（UI 不直接依赖领域实现细节）。
2. 所有状态变更通过 Application 层命令执行，禁止 UI 层随意写 `app_state`。
3. 渲染与数据处理通过端口/适配器解耦（便于测试与替换）。
4. 新功能默认以模块化包落地，避免继续扩张超大文件。

### 2. 目标目录（建议）

```text
src/
├── presentation/
│   ├── qt/
│   │   ├── windows/
│   │   ├── dialogs/
│   │   └── viewmodels/
├── application/
│   ├── use_cases/
│   ├── dto/
│   └── services/
├── domain/
│   ├── model/
│   ├── services/
│   └── events/
├── infrastructure/
│   ├── data_io/
│   ├── plotting/
│   ├── session/
│   └── plugins/
└── shared/
        ├── contracts/
        └── errors/
```

说明：现阶段无需一次性物理迁移到 `src/`，可先在现有目录中建立同名子包并按能力逐步切换导入。

### 3. 分阶段改造路线（A1-A8）

#### A1 架构基线与质量门禁（1-2 周）

- 新增 `tests/` 基础骨架与 smoke 测试。
- 建立最小 CI（安装、导入、关键用例、打包冒烟）。
- 增加静态检查：`ruff` + `mypy(增量)`，先对 `core/`、`data/` 开启。

**验收：** PR 必须通过 lint + 最小测试后方可合并。

#### A2 状态管理现代化（2-3 周）

- 引入 `StateStore`（不可变快照 + action/reducer 风格），作为 `app_state` 的演进层。
- 将“数据加载、渲染模式、导出参数、选择集”迁移为第一批受控状态。
- 保留兼容适配器：旧代码可读写，但新代码只允许通过 action 更新。

**验收：** 新增功能 100% 通过 action 更新状态；`app_state` 直接写入点数量较基线下降 30%。

#### A3 Application 层落地（2-4 周）

- 抽取高频流程为 UseCase：
    - `LoadDatasetUseCase`
    - `RenderPlotUseCase`
    - `ExportImageUseCase`
    - `ExportTableUseCase`
- UI 回调改为调用 UseCase，不直接拼接业务流程。

**验收：** `ui/` 目录中不再出现跨层数据清洗与核心业务分支判断。

#### A4 可视化渲染管线拆分（3-4 周）

- 将 `visualization/events.py` 拆分为：交互控制器、命中测试、选择策略。
- 将 `visualization/plotting/geo.py` 拆为：模型计算、图元生成、标签布局三层。
- 引入 `PlotAdapter` 接口，隔离 Matplotlib 细节，降低 UI/算法对底层 API 的耦合。

**验收：** 单文件控制在 800 行以内；渲染相关核心函数具备可单测入口。

#### A5 数据层解耦（2-3 周）

- 将 `data/loader.py` 切分为：
    - `data_io`（读取器）
    - `schema`（列推断/校验）
    - `cleaning`（清洗与标准化）
    - `import_flow`（仅编排）
- UI 对话框输出 DTO，禁止数据层反向依赖 UI。

**验收：** 数据导入主流程可在无 UI 环境下运行（CLI/测试可复用）。

#### A6 插件系统与算法解耦（承接现有插件计划，2-4 周）

- 按既有 M1-M5 方案推进插件 API 冻结与内置算法迁移。
- 将 UMAP/t-SNE/XGBoost 的调用统一改为插件网关。

**验收：** 禁用单个插件不影响主程序启动；算法下拉框由注册表动态驱动。

#### A7 UI 架构升级（2-3 周）

- 引入 ViewModel 层（Qt 信号/槽仅绑定 VM 状态）。
- 清理 deprecated 控制面板旧路径，统一菜单对话框模式。
- 抽象公共组件（参数输入、状态提示、错误展示）形成可复用组件库。

**验收：** `ui/main_window.py` 降至 700 行以内；界面回调不直接操作底层绘图对象。

#### A8 发布工程化（1-2 周）

- 增加版本化迁移脚本（会话配置、插件目录、导出预设）。
- 建立性能基线（导入耗时、首帧渲染耗时、导出耗时）。
- 发布检查清单自动化（依赖、字体、SciencePlots 可用性、打包完整性）。

**验收：** 发布流程可一键执行并输出质量报告。

### 4. 架构 KPI（季度跟踪）

- 结构指标：
    - 超过 800 行文件数从当前基线降至 ≤ 2。
    - `app_state` 直接写入引用数较基线下降 ≥ 60%。
- 质量指标：
    - 核心模块（`core/data/visualization`）单元测试覆盖率 ≥ 55%。
    - 关键导出/加载/渲染链路具备回归测试。
- 体验指标：
    - 冷启动到首帧渲染时间下降 ≥ 20%。
    - 常用导出路径失败率持续低于 1%。

### 5. 风险与回滚策略

1. 迁移期间保持“旧入口 + 新入口”双轨，避免一次性切换导致大面积回归。
2. 每个 A 阶段均需提供 feature flag（默认关闭新链路，逐步灰度）。
3. 对外行为不变优先：UI 文案、导出结果、会话兼容性不得破坏。
4. 如任一阶段导致关键链路（加载/渲染/导出）回归，立即回退到上一稳定里程碑。

### 6. 与现有计划的关系

- 本节作为“跨模块架构主线”，优先级高于单点优化任务。
- 现有 1.1、2.1、2.2、2.3、插件 M1-M5 仍保留，但执行时需对齐 A1-A8 的阶段门禁。
- `ML 管线增强` 继续保持延期策略，待插件迁移完成后再进入性能/算法层深化。

## 架构计划执行化优化（2026-03-31 续）

### 0. 目标

将“架构现代化改造方案”从原则级文档升级为可排期、可验收、可回滚的执行计划，确保每一阶段都能独立交付并保持主线可用。

### 1. 周期与节奏（建议 16 周）

| 阶段 | 周期 | 目标 | 准出条件 |
| --- | --- | --- | --- |
| S0 准备 | 第 1-2 周 | 建立基线与门禁 | CI 可运行；基线报告生成 |
| S1 状态治理 | 第 3-5 周 | 完成 StateStore 第一批迁移 | 新增状态变更仅走 action；关键链路回归通过 |
| S2 用例分层 | 第 6-8 周 | 导入/渲染/导出进入 UseCase | UI 回调不含核心业务分支 |
| S3 渲染解耦 | 第 9-11 周 | 交互控制与渲染适配器拆分 | 关键渲染模块可单测；大文件显著下降 |
| S4 数据层重构 | 第 12-13 周 | loader 分层与 DTO 化 | 无 UI 环境可执行导入流程 |
| S5 插件接入与发布工程化 | 第 14-16 周 | 插件主线打通 + 发布自动化 | 一键发布检查通过；插件灰度机制可用 |

### 2. 关键路径（Critical Path）

1. S0 CI 与测试骨架落地。
2. S1 StateStore 与 action 机制稳定。
3. S2 UseCase 接管导入/渲染/导出主链路。
4. S3 PlotAdapter 完成并接入 UI。
5. S4 DataLoader 分层完成并通过无 UI 回归。
6. S5 插件网关接管算法入口。

说明：若第 2 步延期，第 3-5 步将整体顺延；因此 S1 为全计划最高风险点。

### 3. 里程碑准入/准出（Stage Gate）

#### G1（S0 -> S1）

- 准入：`tests/` 骨架、最小 CI、`ruff` 基础规则已提交。
- 准出：关键模块导入测试通过；生成“架构基线报告”并归档。

#### G2（S1 -> S2）

- 准入：StateStore 已覆盖数据加载与渲染模式。
- 准出：`app_state` 直接写入点较基线下降至少 20%。

#### G3（S2 -> S3）

- 准入：导入/渲染/导出均有对应 UseCase。
- 准出：UI 事件回调仅做参数采集与结果展示。

#### G4（S3 -> S4）

- 准入：`PlotAdapter` 接口稳定，事件控制器拆分完成。
- 准出：`visualization/events.py`、`visualization/plotting/geo.py` 任一文件行数下降到 900 行以内。

#### G5（S4 -> S5）

- 准入：导入流程可在无 Qt 环境运行。
- 准出：插件网关接管主要算法入口，发布检查脚本可一键执行。

### 4. 工作分解（WBS）

| 编号 | 工作包 | 主要输出 | 依赖 | 风险等级 |
| --- | --- | --- | --- | --- |
| WP-01 | 架构基线采集 | 依赖图、文件体量、状态写入热力图 | 无 | 中 |
| WP-02 | 测试与 CI 最小闭环 | `pytest` 冒烟 + lint 流水线 | WP-01 | 中 |
| WP-03 | StateStore 核心 | action/reducer/store 与兼容适配层 | WP-02 | 高 |
| WP-04 | UseCase 化导入 | `LoadDatasetUseCase` + DTO | WP-03 | 高 |
| WP-05 | UseCase 化渲染导出 | `RenderPlotUseCase`、`ExportImageUseCase`、`ExportTableUseCase` | WP-03 | 高 |
| WP-06 | 渲染管线拆分 | 控制器、命中测试、图元生成分层 | WP-05 | 高 |
| WP-07 | 数据层拆分 | `data_io/schema/cleaning/import_flow` | WP-04 | 中 |
| WP-08 | 插件网关接入 | 注册表驱动算法入口 | WP-05 | 中 |
| WP-09 | 发布工程化 | 质量报告、迁移脚本、发布检查 | WP-08 | 中 |

### 5. 两周执行计划（可立即开工）

#### Sprint-Next-1（第 1 周）

1. 建立 `tests/` 最小结构，落地 3 条 smoke：启动导入、渲染分发、导出调用。
2. 新增 `scripts/architecture_baseline.py`，输出：
    - 超大文件排行。
    - `app_state` 直接写入统计。
    - 模块间导入关系摘要。
3. 引入 `ruff` 基础规则并在 CI 中执行。

**验收：** 本周所有 PR 必须通过 lint + smoke。

#### Sprint-Next-2（第 2 周）

1. 新建 `core/state_store.py`，支持 `dispatch(action)` 与快照读取。
2. 迁移第一批状态域：
    - render mode
    - selected indices
    - export image options
3. 在 UI 层新增兼容桥接，保持旧调用不崩溃。

**验收：** 新增状态改动不得直接写入 `app_state` 原字段。

### 6. 质量与进度度量（每周更新）

| 指标 | 当前基线 | 4 周目标 | 8 周目标 | 16 周目标 |
| --- | --- | --- | --- | --- |
| 超过 900 行文件数 | 4 | 3 | 2 | ≤1 |
| `app_state` 直接写入点 | 100%（基线待脚本固化） | -20% | -40% | -60% |
| 核心链路自动化覆盖 | 低 | 冒烟覆盖 | 关键链路回归 | 覆盖率 ≥55% |
| 发布前人工检查项 | 高 | 部分脚本化 | 大部分脚本化 | 一键检查 |

### 7. 风险台账（执行版）

| 风险 | 触发条件 | 监测信号 | 缓解措施 | 回滚策略 |
| --- | --- | --- | --- | --- |
| 状态迁移导致行为漂移 | S1 大规模替换写路径 | 交互异常、导出参数失效 | 双写 + 快照对比 + feature flag | 关闭新 store，回落旧状态 |
| 渲染拆分引入性能回退 | S3 拆分后 draw 频率变化 | 首帧时间上升、卡顿 | 增量渲染 + 性能剖析基线 | 回退到旧渲染分发路径 |
| 插件接入稳定性不足 | 第三方插件异常 | 启动失败、算法列表空 | 启动降级 + 隔离失败插件 | 禁用插件模式启动 |
| CI 过慢影响迭代 | 检查项过多 | 合并队列堆积 | 分层流水线（快速/完整） | 临时降级为快速检查 |

### 8. 管理机制

1. 每周一次架构评审（30 分钟），仅检查 KPI 与阶段门，不讨论实现细节。
2. 每两周一次里程碑评审，决定是否进入下一阶段。
3. 每个工作包必须附带“变更影响面 + 回滚点 + 验收脚本”。
4. 所有重构 PR 必须绑定至少 1 条回归测试或 1 条 smoke 用例。

### 9. 文档联动要求

1. 目录或职责变更后，同步更新 `docs/architecture.md`。
2. 导出链路变更后，同步更新 `docs/export.md`。
3. UI 入口/交互变更后，同步更新 `docs/ui.md`。
4. 架构约束或流程变更后，同步更新 `docs/dev_conventions.md`（尤其是分层依赖、PR 门禁、分支策略）。
5. 本计划每周更新一次“完成度与偏差”。

---

## 阶段进展（2026-04-01）

- 已完成 A1（测试与 CI 最小门禁）首轮落地：
    - 新增 `tests/` 最小 smoke 集合，覆盖导出用例、选择/tooltip 用例、状态直写检查脚本调用。
    - 新增 `pyproject.toml` 中的 `pytest` 配置与 `dev` 可选依赖（`pytest`）。
    - 新增 GitHub Actions 工作流 `.github/workflows/quality-gate.yml`（Windows）执行：`pytest` + `scripts/check_state_mutations.py --fail-on-hits`。
    - 本地验证已通过：`8 passed`，状态直写检查保持 `TOTAL=0`。

- 已创建并推送架构改造总分支：`epic/architecture-modernization-2026q2`。
- 已完成 A3（Application 层）导出链路的一步到位迁移：
    - 新增 `application/use_cases/export_data.py`，统一承载导出 DataFrame 构建、CSV/Excel 写出、Excel 追加。
    - 新增 `application/use_cases/export_image.py`，统一承载图像导出预设、后缀归一化、保存参数解析与 `savefig` 调用。
    - `application/use_cases/export_dataframe.py` 转为兼容代理，避免旧引用断裂。
    - 导出 UI 层 `ui/panels/export/data_export.py` 与 `ui/panels/export/common.py` 已切换为调用应用层用例，UI 仅保留交互与反馈职责。
- 已完成 A3（Application 层）渲染编排迁移：
    - 新增 `application/use_cases/render_plot.py`，引入 `RenderPlotUseCase` 统一承载渲染模式校验、列选择修正、渲染分发与失败回退。
    - `visualization/events.py` 的 `on_slider_change` 已降级为薄入口，事件层保留异步任务管理和 UI 同步钩子。
    - Application 包已导出 `RenderPlotUseCase`，形成导入/渲染/导出三条主链路均可由 UseCase 编排的基础形态。
- 已完成 A2/A3 交界的数据导入编排迁移：
    - 新增 `application/use_cases/load_dataset.py`，将数据导入流程编排（文件/工作表选择、列配置、清洗、状态注入）上移到 Application 层。
    - `ui/app.py` 与 `ui/main_window.py` 已改为调用 `load_dataset`，UI 入口不再直接依赖 `data.loader.load_data`。
    - `data/loader.py` 的 `load_data` 已降级为兼容代理，`read_data_frame` 保留为数据读取工具函数。
- 已完成 A2（状态治理）第一步落地：
    - 新增 `core/state_gateway.py`，提供 `AppStateGateway` 与 `state_gateway`，作为导入/渲染链路的统一状态写入口。
    - `load_dataset` 与 `RenderPlotUseCase` 已切换关键状态写操作到 gateway，减少 UseCase 内部散落的字段级直接写入。
    - `visualization/events.py` 的渲染模式同步和异步 embedding 任务状态（token/worker/running）已切换到 gateway。
- 已完成 A2（状态治理）第二步收口：
    - `visualization/events.py` 中选择工具与等时线主链路状态写入已切换到 gateway。
    - 新增 gateway 写入口：rectangle/lasso selector、selection overlay/ellipse、selected isochron data、selection tool、visible groups。
    - `selected_indices` 的清空/增删也已通过 gateway 命令化封装（clear/add/remove），事件层不再直接调用集合变更方法。
    - 事件层中 `app_state.xxx = ...` 的残余已收敛为判断语句（无字段赋值）。
    - 导出子域状态写入已继续收口：`ui/panels/export/common.py`、`ui/panels/export/image_export.py`、`ui/panels/export/selection.py` 已切换到 gateway，移除导出链路中的字段级直接赋值与选择集合直接变更。
- 本次迁移目标：在不改变外部行为前提下，直接完成导出子域“规则下沉 + 责任分层”，作为后续 `LoadDatasetUseCase` / `RenderPlotUseCase` 迁移模板。
- 已完成 A2 提速批处理（状态直写快速收口）：
    - 新增 gateway 通用接口：`set_attr` / `set_attrs`，用于高频状态写入批量迁移。
    - 高价值入口文件完成收口：`ui/app.py`、`ui/main_window.py`、`visualization/plotting/render.py`、`visualization/plotting/core.py`。
    - 中小文件尾项收口完成：`ui/panels/analysis_panel.py`、`ui/panels/legend_panel.py`、`ui/panels/display_panel.py`、`ui/dialogs/line_style_dialog.py`、`visualization/plotting/geo.py`、`ui/dialogs/provenance_ml_dialog.py`、`ui/control_panel.py`、`ui/dialogs/data_import_dialog.py`、`ui/dialogs/endmember_dialog.py`、`visualization/plotting/kde.py`、`visualization/plotting/label_layout.py`、`core/localization.py`。
    - 大文件瓶颈收口完成：`ui/panels/data_panel.py` 与 `ui/panels/base_panel.py` 字段级直写已全部迁移至 gateway。
    - 可量化结果：`app_state.xxx = ...` 全仓计数已从 **294 降到 0**（净减少 294，完成率 **100%**）。
    - 新增基线检查脚本：`scripts/check_state_mutations.py`，支持本地与 CI 持续检查（可选 `--fail-on-hits`）。
- 已完成 A3（交互业务下沉）新一轮迁移：
    - 新增 `application/use_cases/selection_interaction.py`，承载矩形/套索圈选、最近邻索引匹配、工具切换策略、图例可见组计算等纯业务逻辑。
    - 新增 `application/use_cases/selected_isochron.py`，承载选中样本等时线结果计算与结果载荷构建。
    - 新增 `application/use_cases/tooltip_content.py`，承载 hover 提示文本拼装逻辑（默认字段、空列回退、选中状态标记）。
    - `visualization/events.py` 相关路径已改为调用 use case，事件层进一步收敛为交互编排与 UI 回调。
    - 新增 `visualization/selection_overlay.py`，将选中高亮圈与置信椭圆绘制从 events 模块拆分为独立渲染服务。
- 已完成 UI 大文件结构化拆分（DataPanel）：
    - `ui/panels/data_panel.py` 已收敛为薄组装器（18 行），仅负责 mixin 组合。
    - 新增 `ui/panels/data/` 子包并拆分职责：`build.py`（UI 构建）、`projection.py`（渲染/算法参数）、`geochem.py`（地球化学交互）、`grouping.py`（分组与 tooltip）。
    - 可量化结果：原 `ui/panels/data_panel.py` 约 1356 行已拆分为多个职责模块，降低单文件认知复杂度并与 `export/` 子包模式保持一致。
- 已完成 UI 面板第二轮结构化拆分（Analysis/Display/Legend）：
    - `ui/panels/analysis_panel.py`、`ui/panels/display_panel.py`、`ui/panels/legend_panel.py` 已收敛为薄组装器。
    - 新增子包：`ui/panels/analysis/`、`ui/panels/display/`、`ui/panels/legend/`，对应 `panel.py` 承载原业务逻辑。
    - 兼容性验证：原导入路径保持不变，面板类名保持不变。
- 已完成 Analysis 子包内部模块化拆分（第四轮）：
    - `ui/panels/analysis/panel.py` 已收敛为 mixin 组合层。
    - 新增 `ui/panels/analysis/build.py`、`diagnostics.py`、`selection.py`、`equations.py`、`mixing.py`。
    - 兼容性验证：`AnalysisPanelMixin` 对外名称不变，`ui/panels/analysis_panel.py` 调用路径不变。
- 已完成 UI 面板第三轮细化拆分（Display/Legend 内部模块）：
    - `ui/panels/display/panel.py` 已收敛为 mixin 组合层，新增 `ui/panels/display/build.py` 与 `ui/panels/display/themes.py`。
    - `ui/panels/legend/panel.py` 已收敛为 mixin 组合层，新增 `ui/panels/legend/build.py` 与 `ui/panels/legend/actions.py`。
    - 兼容性验证：`DisplayPanelMixin` / `LegendPanelMixin` 对外名称不变，`ui/panels/display_panel.py` 与 `ui/panels/legend_panel.py` 无需变更调用。
- 已完成对话框模块化拆分（DataImportDialog）：
    - `ui/dialogs/data_import_dialog.py` 已收敛为包装器（保留 `Qt5DataImportDialog` 与 `get_data_import_configuration` 兼容入口）。
    - `ui/dialogs/data_import/dialog.py` 已收敛为组合层。
    - 新增 `ui/dialogs/data_import/build.py`、`workflow.py`、`submit.py`，实现 UI 构建、导入流程、提交校验解耦。
    - 导入冒烟检查通过，UI 对外 API 无破坏性变更。
- 已完成主窗口模块化拆分（MainWindow）：
    - `ui/main_window.py` 已收敛为薄入口组合类（`Qt5MainWindow` 保持不变）。
    - 新增 `ui/main_window_parts/` 子包并拆分职责：`setup.py`（窗口/菜单/工具栏/状态栏）、`legend.py`（图例面板交互）、`canvas.py`（画布与工具操作）、`lifecycle.py`（会话与事件绑定）。
    - 兼容性验证：外部导入路径 `from ui.main_window import Qt5MainWindow` 无变化。
- 已完成应用启动层模块化拆分（Qt5Application）：
    - `ui/app.py` 已收敛为薄编排入口，职责拆分到 `ui/app_parts/`。
    - 新增 `ui/app_parts/styles.py`、`session.py`、`plotting.py`，分别承载样式与调试钩子、会话恢复、绘图构建与事件连接。
    - 兼容性验证：外部导入路径 `from ui.app import Qt5Application` 无变化，导入冒烟通过。
- 已完成主窗口图例模块二次拆分（Legend internals）：
    - `ui/main_window_parts/legend.py` 已收敛为组合入口。
    - 新增 `ui/main_window_parts/legend_core.py` 与 `legend_actions.py`，将图例排序核心与 UI 交互动作解耦。
    - 兼容性验证：`Qt5MainWindow` 外部行为不变，图例导入与启动冒烟通过。
- 已完成 Display/Legend 与 ProvenanceML 第四轮模块细化（2026-04-01 夜间）：
    - `ui/panels/display/build.py` 已剥离颜色与图例按钮辅助逻辑到 `ui/panels/display/helpers.py`，`DisplayPanelMixin` 更新为 build/themes/helpers 三层组合。
    - `ui/panels/legend/build.py` 已剥离色阶/形状编辑器逻辑到 `ui/panels/legend/editors.py`，`LegendPanelMixin` 更新为 build/editors/actions 三层组合。
    - `ui/dialogs/provenance_ml_dialog.py` 已收敛为兼容包装器，新增 `ui/dialogs/provenance_ml/dialog.py`、`build.py`、`workflow.py` 形成初始化/构建/执行分层。
    - 兼容性验证：`ProvenanceMLDialog` 与 `show_provenance_ml` 入口保持不变，导入冒烟通过。
- 已完成可视化绘图层双模块拆分（2026-04-01 夜间续）：
    - `visualization/plotting/render.py` 已抽离通用绘图辅助逻辑到 `visualization/plotting/render_helpers.py`，主文件聚焦 `plot_embedding` / `plot_2d_data` / `plot_3d_data` 主流程。
    - `visualization/plotting/geo.py` 已抽离覆盖层与 plumbotectonics 逻辑到 `visualization/plotting/geo_overlay_helpers.py`，主文件聚焦等时线拟合、模型年龄线、方程覆盖等核心计算。
    - 兼容性验证：`pytest`（8 passed）与导入冒烟通过，`scripts/check_state_mutations.py --fail-on-hits` 仍保持 `TOTAL=0`。
    - 量化结果：`render.py` 由约 1297 行降至 758 行；`geo.py` 由约 1733 行降至 1140 行。
- 已完成 plotting 包结构清理（2026-04-01 夜间补充）：
    - 删除未被引用的冗余模块 `visualization/plotting/overlay_helpers.py`，减少同类 helper 重叠。
    - 新增 `visualization/plotting/event_bridge.py`，统一 `plotting -> events` 的回调桥接，移除 `render.py` 与 `style.py` 的分散式动态导入。
    - `visualization/plotting/legend_model.py` 已改为直接依赖 `geo_overlay_helpers` 的元数据函数，减少对 `geo.py` 主模块的耦合。
    - 验证结果：`pytest` 全通过，改动文件错误检查通过。
- 已完成 plotting 子目录重组（2026-04-01 夜间续）：
    - 新增 `visualization/plotting/rendering/`，并迁移 `render_helpers.py`、`render_kde.py`、`render_geo_layers.py` 到子目录（分别为 `helpers.py`、`kde.py`、`geo_layers.py`）。
    - 新增 `visualization/plotting/styling/`，并迁移 `style_core.py`、`style_legend.py`、`style_overlays.py` 到子目录（分别为 `core.py`、`legend.py`、`overlays.py`）。
    - 新增 `visualization/plotting/geochem/`，并迁移 `geo_overlay_helpers.py` 到 `overlay_helpers.py`。
    - `render.py`、`style.py`、`geo.py`、`legend_model.py` 已完成导入路径切换，plotting 顶层文件堆积明显下降。
- 已完成 visualization 事件层拆分（2026-04-01 夜间续）：
    - 新增 `visualization/event_handlers/selection_interaction.py`，迁移 hover、点击、图例可见性切换、选择工具与选中等时线计算链路。
    - 新增 `visualization/event_handlers/__init__.py` 聚合交互事件公开函数，保留外部导入习惯。
    - `visualization/events.py` 已收敛为渲染触发与异步 embedding 编排入口（164 行），对外 API 名称保持不变。
    - 兼容性验证：`pytest` 全通过（8 passed），`from visualization.events import ...` 冒烟导入通过。
- 已完成 visualization 事件子包二次细拆（2026-04-01 夜间续）：
    - 新增 `visualization/event_handlers/shared.py`、`overlay.py`、`isochron.py`、`selection_tools.py`、`pointer_events.py`、`legend.py`，将共享状态、覆盖层刷新、等时线计算、选择工具、指针事件、图例事件进一步解耦。
    - `visualization/event_handlers/selection_interaction.py` 已收敛为兼容门面，继续保留原导入路径。
    - 兼容性验证：`pytest` 全通过（8 passed），`visualization.events` 与 `visualization.event_handlers.selection_interaction` 双路径导入冒烟通过。
- 已完成 geochem 等时线渲染模块细拆（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/isochron_rendering.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/isochron_fits.py`（等时线拟合主流程）、`selected_isochron_overlay.py`（选中等时线高亮）、`paleoisochron_overlays.py`（古等时线覆盖层）。
    - 兼容性验证：`pytest` 全通过（8 passed），`isochron_rendering` 与 `isochron_overlays` 双路径导入冒烟通过。
- 已完成 geochem 等时线拟合二次细拆（2026-04-01 夜间续）：
    - 新增 `visualization/plotting/geochem/isochron_fit_76.py` 与 `isochron_fit_86.py`，将 PB_EVOL_76/PB_EVOL_86 模式分支从主流程中解耦。
    - `visualization/plotting/geochem/isochron_fits.py` 已收敛为主流程编排层（分组循环 + 公共拟合预处理 + 分支分发）。
    - 兼容性验证：`pytest` 全通过（8 passed），`isochron_fits` 与 `isochron_rendering` 导入冒烟通过。
    - 验证结果：`pytest` 全通过（8 passed），导入冒烟通过。
- 已完成 geochem 第二轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geo.py` 已收敛为兼容门面，保留原函数导出以避免外部调用断裂。
    - 新增 `visualization/plotting/geochem/isochron_overlays.py`，承载等时线拟合、选中等时线、古等时线、模型年龄线、标签刷新。
    - 新增 `visualization/plotting/geochem/equation_overlays.py`，承载方程表达式安全求值与曲线叠加渲染。
    - 量化结果：`geo.py` 由约 1233 行降至 64 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 geochem 第三轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/isochron_overlays.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/isochron_labels.py`，承载等时线标签构建与标签重布局刷新。
    - 新增 `visualization/plotting/geochem/isochron_rendering.py`，承载等时线/选中等时线/古等时线渲染。
    - 新增 `visualization/plotting/geochem/model_age_lines.py`，承载模型年龄线与年龄解算逻辑。
    - 量化结果：`isochron_overlays.py` 由约 1021 行降至 27 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 rendering 第二轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/render.py` 已收敛为兼容门面，保留 `plot_embedding` / `plot_umap` / `plot_2d_data` / `plot_3d_data` 导出。
    - 新增 `visualization/plotting/rendering/embedding_plot.py`，承载 `plot_embedding` 主流程。
    - 新增 `visualization/plotting/rendering/raw_plots.py`，承载 `plot_2d_data` 与 `plot_3d_data`。
    - 量化结果：`render.py` 由约 902 行降至 17 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 geochem 第四轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/overlay_helpers.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/overlay_common.py`，承载通用覆盖层标签/样式辅助函数。
    - 新增 `visualization/plotting/geochem/model_overlays.py`，承载模型曲线与 Mu/Kappa 古等时线绘制。
    - 新增 `visualization/plotting/geochem/plumbotectonics.py`，承载 Plumbotectonics 分组元数据、曲线拟合与曲线/同龄线绘制。
    - 量化结果：`overlay_helpers.py` 由约 686 行降至 45 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。

## 全局改进计划

### 第一优先级：功能与性能

#### 1.1 图像导出能力建设（新）

**目标:** 将导出能力明确拆分为“数据导出”和“图像导出”，并为学术期刊投稿场景提供可复用的标准化输出。

**范围定义:**

- 数据导出：保持现有 CSV/Excel/追加导出能力。
- 图像导出：新增统一入口，支持位图（PNG/TIFF）与矢量（PDF/SVG/EPS）导出。

**核心要求（期刊适配）:**

- 导出时优先选择“期刊预设”，预设锁定尺寸与字体大小。
- 其余参数（线宽、标记大小、网格透明度、留白等）按预先定义模板自动应用，避免用户逐项调整。
- 提供最小可用预设集：
  - `Single Column`：约 `85 mm` 宽，适合单栏图。
  - `Double Column`：约 `180 mm` 宽，适合跨双栏图。
  - `Presentation`：用于报告/答辩，尺寸较宽，字体略大。
- 字体等级按预设固定：标题/坐标轴标题/刻度/图例四级联动。

**实现方案优先级（新增）:**

- 方案 A（优先）：基于 `SciencePlots` 组合样式实现期刊预设。
    - 依据：官方支持 `plt.style.use(['science', 'ieee'])` 与 `['science', 'nature']`，用于覆盖列宽与字体等级。
    - 适配策略：
        - 默认链路使用 `science + no-latex`，降低 LaTeX 依赖门槛。
        - 对 IEEE/Nature 预设追加对应 journal style。
        - 中文场景追加 CJK font style（按字体可用性回退）。
- 方案 B（回退）：不依赖外部包，使用内置 `rcParams` 预设（保持当前规划中的 `ExportProfile`）。

**实现路线（E1-E5）:**

1. E1 导出模型抽象
    - 新增 `ExportProfile` 数据结构（尺寸、DPI、字体等级、格式、背景策略）。
    - 在 `core/config.py` 或独立配置模块维护内置预设，支持后续外置配置。
2. E2 图像导出引擎
    - 封装 `figure.savefig(...)` 调用链，统一处理尺寸换算（mm/inch）、DPI 与 bbox。
    - 增加导出前样式快照与导出后恢复，避免污染当前交互视图。
3. E3 UI 接入
    - `ExportPanel` 拆分为 `Data Export` 与 `Image Export` 两个折叠区。
    - 图像导出区提供：预设选择、格式选择、输出路径、导出按钮。
    - 当检测到 `SciencePlots` 可用时显示“期刊模板来源: SciencePlots”；不可用时自动切回内置模板。
4. E4 质量与兼容性
    - 增加字体可用性检查与回退策略（Windows 字体缺失时自动回退并提示）。
    - 验证图内文本在常见缩放比例下不重叠（标题、轴标签、图例）。
5. E5 文档与回归
    - 新增 `docs/export.md`（预设说明、格式建议、投稿建议流程）。
    - 为关键导出路径补充最小回归脚本（不同格式 + 不同预设）。

**验收标准:**

- 用户在 3 步内完成期刊风格导出：选预设 -> 选格式 -> 导出。
- 同一图在不同机器上导出后，尺寸与字体等级与预设一致（允许极小字体渲染差异）。
- 图像导出不改变当前画布交互状态（导出前后视图一致）。

#### 1.2 ML 管线增强（延期）

**状态:** 延期，待插件功能完成后执行。

**延期原因:** ML 算法将转为插件化实现，当前直接改造主仓库会导致重复重构。

**重启条件:** 插件开发计划达到 M2（XGBoost/UMAP 等内置插件迁移完成）。

**后续实施要点（保留）:**

- 增加 train/valid/test 划分与固定随机种子报告。
- 增加交叉验证指标（macro-F1、balanced accuracy、AUC-ovr）。
- XGBoost 默认 `tree_method='hist'`，并在报告中标注训练耗时。
- 支持 per-label 阈值与阈值搜索结果导出。

### 第二优先级：代码质量

#### 2.1 类型注解补齐（部分完成）

**范围优先级:** `core/` > `data/` > `visualization/` > `ui/`

**要求:**

- 新增/重构公共函数必须含类型注解。
- 公共 API 使用 Google 风格 docstring（Args/Returns/Raises）。
- 剩余重点：`core/state.py`、`core/session.py`、`data/` 核心计算函数。

#### 2.2 AppState 分层拆分

**目标:** 将 `AppState` 按职责拆分为子状态对象，降低耦合。

**建议结构:**

```python
class AppState:
    data: DataState
    algorithm: AlgorithmState
    visual: VisualState
    geochem: GeochemState
    style: StyleState
    interaction: InteractionState
```

**实现状态:** 进行中（已新增分层兼容视图、可写属性与顶层别名；正在分批迁移调用方）

#### 2.3 数值稳定性统一（部分完成）

**目标:** 统一除零与无效值处理策略。

**实施要点:**

- 统一 `EPSILON` 常量来源，避免散落魔法数字。
- 在关键计算路径中使用 `np.errstate`。
- 所有外部输入统一 `pd.to_numeric(errors='coerce')`。
- 剩余重点：扩展到其余模块并补充相应回归验证。

### 当前阶段交付顺序（仅 P2）

1. P2-1：类型注解补齐（先 core/data）
2. P2-2：AppState 分层拆分
3. P2-3：数值稳定性统一收口

### 第三优先级：基础设施

#### 3.1 单元测试框架落地

**最小目标:** 建立可运行测试骨架并覆盖关键数值模块。

```text
tests/
├── test_geochemistry.py
├── test_cache.py
├── test_session.py
├── test_localization.py
├── test_endmember.py
├── test_mixing.py
└── test_provenance_ml.py
```

#### 3.2 配置外部化

支持用户配置文件 `~/.isotopes_analysis/config.json`，并与 `CONFIG` 合并。

```json
{
  "default_language": "zh",
  "figure_dpi": 150,
  "embedding_cache_size": 16,
  "xgboost_tree_method": "hist"
}
```

---

## 模块改进建议（进行中）

### data/ 模块

#### 高优先级

1. `provenance_ml.py` 增加交叉验证与测试集报告（延期，插件完成后执行）。
2. XGBoost 训练默认切换到 `tree_method='hist'`（延期，插件完成后执行）。

#### 中优先级

3. 列名规范化策略外置（导入配置或映射表）。
4. `GeochemistryEngine` 为后台线程场景增加并发保护。
5. `mixing.py` 增加误差传播能力（不确定度输入到权重区间）。

#### 低优先级

6. 清理 geochemistry 兼容别名函数（下个大版本）。
7. `endmember.py` 中阈值参数可配置化。

### visualization/ 模块

#### 高优先级

1. 补充渲染子函数级测试（覆盖散点/KDE/地球化学覆盖层/图例/标题路径）。
2. 继续增强 UI 进度展示与异常可视反馈（与后台任务联动）。

#### 中优先级

3. 诊断图增加“另存为”导出能力。
4. `refresh_plot_style()` 支持增量更新，避免全量遍历散点集合。
5. `calculate_selected_isochron()` 扩展 206-208 模式。

#### 低优先级

6. 完善渲染异常回滚测试，确保失败时 canvas 状态一致。

---

## 插件开发计划（扩展版）

### 目标

- 将机器学习能力从主仓库解耦为插件，降低核心代码耦合。
- 支持第三方算法快速接入，保持 UI 与数据层兼容。
- 保证插件 API 稳定、可发现、可诊断、可回退。

### 设计原则

1. **稳定接口优先**：先定义最小可用 API，再扩展能力。
2. **弱依赖核心**：插件只依赖公开接口，不直接访问内部状态。
3. **可观测性**：插件加载、执行、失败必须有结构化日志。
4. **兼容演进**：通过 API 版本协商避免一次性破坏升级。

### V1 插件范围

- `MLClassifierPlugin`：监督分类（训练/预测/概率输出）。
- `EmbeddingPlugin`：降维嵌入（fit_transform/transform）。
- `FeatureEngineeringPlugin`：特征构造与清洗。

### 目录与发现机制

```text
plugins/
├── __init__.py
├── api.py                 # 抽象接口、类型定义、错误类型
├── manager.py             # 插件发现、加载、生命周期管理
├── registry.py            # 已加载插件注册表
├── builtins/
│   ├── xgboost_plugin.py
│   └── umap_plugin.py
└── third_party/
    └── ...
```

**发现策略（按优先顺序）:**

1. 内置目录 `plugins/builtins/`
2. 用户目录 `~/.isotopes_analysis/plugins/`
3. 可选 entry points（后续版本）

### 接口草案（V1）

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PluginMeta:
    name: str
    version: str
    api_version: str
    plugin_type: str
    author: str = ""


class BasePlugin(Protocol):
    meta: PluginMeta

    def validate_environment(self) -> tuple[bool, str]:
        ...

    def get_default_params(self) -> dict[str, Any]:
        ...


class MLClassifierPlugin(BasePlugin, Protocol):
    def fit(self, x: Any, y: Any, **params: Any) -> dict[str, Any]:
        ...

    def predict(self, x: Any) -> Any:
        ...

    def predict_proba(self, x: Any) -> Any:
        ...
```

### 生命周期管理

1. `discover`：扫描插件并解析元数据。
2. `validate`：检查依赖、API 版本、运行环境。
3. `register`：写入注册表并暴露给 UI。
4. `execute`：统一调用并捕获异常。
5. `dispose`：释放资源并记录统计信息。

### 兼容性策略

- `api_version` 采用 `MAJOR.MINOR`。
- 主版本不匹配时拒绝加载并给出可读错误。
- 次版本不匹配时允许加载但记录 warning。
- 保留 `capabilities` 字段，支持按能力降级。

### 安全与隔离

- 默认与主进程同进程运行（V1）。
- 对插件异常做边界捕获，不允许异常穿透到 UI 事件循环。
- 严禁插件直接读写 `app_state` 内部字段；通过受控上下文对象访问。
- 对第三方插件开启“受限模式”标记（禁用敏感入口）。

### 开发者体验

- 提供 `plugins/examples/` 最小模板。
- 提供 `scripts/new_plugin.py` 脚手架命令。
- 提供插件自检命令：`uv run python -m plugins.manager --check`。
- 在 UI 中新增“插件管理”对话框（启用/禁用/诊断信息）。

### 里程碑

#### M1（接口冻结）

- 完成 `plugins/api.py` 与 `PluginMeta`。
- 实现 `PluginManager` 基础加载链路。

#### M2（内置插件迁移）

- 将当前 XGBoost 管线迁移为内置 `MLClassifierPlugin`。
- 将 UMAP/t-SNE 包装为 `EmbeddingPlugin`。

#### M3（UI 接入）

- 算法下拉框改为读取注册表。
- 新增插件状态与失败原因展示。

#### M4（第三方支持）

- 支持用户目录安装插件。
- 增加插件签名/来源标识字段。

#### M5（测试与文档）

- 增加插件加载、执行、回退、兼容性测试。
- 新增 `docs/plugins.md`（开发指南 + API 参考）。

### 验收标准

- 关闭/卸载某个插件不影响应用启动。
- 插件执行失败时 UI 不冻结，且有可检索日志。
- 至少 2 个内置插件完成迁移并通过回归验证。
- 插件接口升级时，旧插件可得到明确兼容性提示。

---

