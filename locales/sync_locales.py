"""Sync locale files with code translation keys and fill missing entries."""
from __future__ import annotations

import ast
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _iter_python_files(root: Path) -> list[Path]:
    ignore_dirs = {
        ".venv",
        "__pycache__",
        "reference",
        "build",
        "dist",
        ".git",
        "assets",
        "docs",
        "locales",
    }
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignore_dirs for part in path.parts):
            continue
        paths.append(path)
    return paths


def _collect_translate_keys(py_path: Path) -> set[str]:
    try:
        source = py_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    try:
        tree = ast.parse(source, filename=str(py_path))
    except SyntaxError:
        return set()

    keys: set[str] = set()
    passthrough_calls = {"make_group"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and (func.id == "translate" or func.id in passthrough_calls):
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.add(first.value)
    return keys


def _merge_with_missing(base: dict, keys: set[str], default_value: str | None = None) -> dict:
    merged = dict(base)
    for key in sorted(keys):
        if key not in merged:
            merged[key] = default_value if default_value is not None else key
    return merged


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    locales_dir = repo_root / "locales"
    en_path = locales_dir / "en.json"
    zh_path = locales_dir / "zh.json"

    en_data = _load_json(en_path)
    zh_data = _load_json(zh_path)

    code_keys: set[str] = set()
    for py_path in _iter_python_files(repo_root):
        code_keys.update(_collect_translate_keys(py_path))

    expected_keys = set(en_data.keys()) | set(zh_data.keys()) | code_keys

    zh_translations = {
        "2D Scatter Parameters": "二维散点参数",
        "68% (1σ)": "68%（1σ）",
        "95% (2σ)": "95%（2σ）",
        "99% (3σ)": "99%（3σ）",
        "All mixing groups cleared.": "已清除所有混合分组。",
        "A training run is already in progress.": "训练已在运行中。",
        "A clustering run is already in progress.": "聚类已在运行中。",
        "An endmember search is already in progress.": "端元搜索已在运行中。",
        "A mixing calculation is already in progress.": "混合计算已在运行中。",
        "Clear all endmember and mixture groups?": "清除所有端元和混合分组？",
        "Subset analysis plugin is not available.": "子集分析插件不可用。",
        "Subset applied: {count} samples.": "已应用子集：{count} 个样本。",
        "Failed to apply subset: {error}": "应用子集失败：{error}",
        "Subset cleared.": "已清除子集。",
        "Failed to reset subset: {error}": "重置子集失败：{error}",
        "MSWD": "MSWD",
        "R²": "R²",
        "Available Columns": "可用列",
        "Available Sheets": "可用工作表",
        "Box Select": "框选",
        "Lock Axis Scale": "锁定坐标轴刻度",
        "Lock the axis scale so new data is drawn on the same ranges. While it is on, the lock wins over a ternary zoom.": "锁定坐标轴刻度，使新数据绘制在相同范围内。锁定时以锁定范围为准，三元图缩放将被覆盖。",
        "Axis scale locked - new data is drawn on these axes.": "坐标轴刻度已锁定 - 新数据将绘制在同一坐标轴上。",
        "Axis scale unlocked - the axes fit the data again.": "坐标轴刻度已解锁 - 坐标轴将重新适应数据。",
        "Circle (o)": "圆形 (o)",
        "Configure": "配置",
        "Clustering plugin is not available. Check the log for details.": "聚类插件不可用。请检查日志了解详情。",
        "Cross (x)": "叉号 (x)",
        "Data exported successfully to {file}": "数据已成功导出到 {file}",
        "Data reloaded successfully": "数据已重新加载",
        "Data reset will be implemented.": "数据重置功能将会实现。",
        "Diamond (D)": "菱形 (D)",
        "Endmember '{name}' set with {count} samples.": "端元“{name}”已设置，包含 {count} 个样本。",
        "Endmembers: {count}": "端元：{count}",
        "Enter group name": "输入分组名称",
        "Exit": "退出",
        "Export Selected": "导出选中",
        "Export Session...": "导出会话...",
        "Failed to export session: {error}": "导出会话失败：{error}",
        "Failed to import session: {error}": "导入会话失败：{error}",
        "Export Selected Data as CSV": "将选中数据导出为 CSV",
        "Export Selected Data as Excel": "将选中数据导出为 Excel",
        "Failed to apply parameters: {error}": "应用参数失败：{error}",
        "Failed to apply theme: {error}": "应用主题失败：{error}",
        "Failed to compute mixing: {error}": "计算混合失败：{error}",
        "Failed to export data: {error}": "导出数据失败：{error}",
        "Failed to load Excel file: {error}": "加载 Excel 文件失败：{error}",
        "Failed to load geochemistry model: {error}": "加载地球化学模型失败：{error}",
        "Failed to open KDE style dialog: {error}": "打开 KDE 样式对话框失败：{error}",
        "Failed to open marginal KDE style dialog: {error}": "打开边缘 KDE 样式对话框失败：{error}",
        "Failed to open tooltip configuration: {error}": "打开提示配置失败：{error}",
        "Nothing was imported.": "没有导入任何数据。",
        "Failed to reset parameters: {error}": "重置参数失败：{error}",
        "Failed to show PCA loadings: {error}": "显示 PCA 载荷失败：{error}",
        "Failed to show axis correlation: {error}": "显示轴相关性失败：{error}",
        "Failed to show correlation heatmap: {error}": "显示相关性热图失败：{error}",
        "Failed to show Shepard diagram: {error}": "显示 Shepard 图失败：{error}",
        "Failed to show scree plot: {error}": "显示碎石图失败：{error}",
        "Failed to start isochron selection: {error}": "启动等时线选择失败：{error}",
        "Geochemistry Model": "地球化学模型",
        "Geochemistry parameters applied successfully.": "地球化学参数应用成功。",
        "Group Visibility": "分组可见性",
        "Import Session": "导入会话",
        "Import Session...": "导入会话...",
        "Importing a session will replace current settings. Continue?": "导入会话将覆盖当前设置。是否继续？",
        "Isotope Session Archive (*.zip)": "同位素会话归档 (*.zip)",
        "Hide All": "全部隐藏",
        "Lasso Select": "套索选择",
        "Legend Columns": "图例列数",
        "Legend Position": "图例位置",
        "Loadings": "载荷",
        "Mixture '{name}' set with {count} samples.": "混合“{name}”已设置，包含 {count} 个样本。",
        "Mixing plugin is not available. Check the log for details.": "混合插件不可用。请检查日志了解详情。",
        "Mixtures: {count}": "混合：{count}",
        "No data selected for analysis.": "未选择用于分析的数据。",
        "No data selected. Please select data points first.": "未选择数据。请先选择数据点。",
        "No mixing groups defined": "未定义混合分组",
        "Opacity: {value:.2f}": "透明度：{value:.2f}",
        "PB_EVOL_76": "Pb 演化图 206-207",
        "PB_EVOL_86": "Pb 演化图 206-208",
        "PB_KAPPA_AGE": "Pb κ 年龄",
        "PB_MU_AGE": "Pb μ 年龄",
        "PLUMBOTECTONICS_76": "地体构造 206-207",
        "PLUMBOTECTONICS_86": "地体构造 206-208",
        "V1V2": "地化-V1V2判别图",
        "tSNE": "t-SNE",
        "PCA": "PCA",
        "Parameters reset to defaults.": "参数已重置为默认值。",
        "Pentagon (P)": "五边形 (P)",
        "Please define at least one endmember.": "请至少定义一个端元。",
        "Please define at least one mixture.": "请至少定义一个混合。",
        "Please enter a group name.": "请输入分组名称。",
        "Please select data points first.": "请先选择数据点。",
        "Plus (+)": "加号 (+)",
        "Primordial (T1/T2):": "原始（T1/T2）：",
        "Ready": "就绪",
        "Recalculate": "重新计算",
        "Plot type": "绘图类型",
        "Results": "结果",
        "RobustPCA": "稳健 PCA",
        "RobustPCA Parameters": "稳健 PCA 参数",
        "Scree Plot": "碎石图",
        "Select Model:": "选择模型：",
        "Show All": "全部显示",
        "Size: {value}": "大小：{value}",
        "Square (s)": "方形 (s)",
        "Stacey-Kramers 2nd Stage:": "Stacey-Kramers 第二阶段：",
        "Save Session": "保存会话",
        "Session exported to {path}": "会话已导出到 {path}",
        "Session imported successfully.": "会话导入成功。",
        "Session settings were imported, but the saved data could not be restored.": "已导入会话设置，但无法恢复其中保存的数据。",
        "The session file is not valid or was created by a newer version.": "会话文件无效，或由更新版本创建。",
        "Standardize data": "标准化数据",
        "Star (*)": "星形 (*)",
        "Subset Analysis": "子集分析",
        "Subset analysis will be implemented.": "子集分析将会实现。",
        "SilverQuest Provenance": "SilverQuest 产地溯源",
        "Run SilverQuest Provenance": "运行 SilverQuest 产地溯源",
        "Pick a grouping column, then assign its values to the sample and reference roles.": "选择分组列，再把它各个取值指派为样品或参考。",
        "Analysis Parameters": "分析参数",
        "Normalization:": "归一化方式：",
        "Normalise the ratios to 204Pb or to 206Pb.": "将比值归一化到 204Pb 或 206Pb。",
        "Maximum distance:": "最大距离：",
        "Maximum distance between ore and analysis. Larger values keep more hits.": "矿样与分析之间的最大距离。数值越大保留的命中越多。",
        "Apply Jitter": "应用抖动",
        "Jitter:": "抖动：",
        "Jitter Radius:": "抖动半径：",
        "Browse...": "浏览...",
        "Select Galena Database": "选择方铅矿数据库",
        "Excel Files (*.xlsx *.xls)": "Excel 文件 (*.xlsx *.xls)",
        "Database not found: {path}": "未找到数据库：{path}",
        "Database could not be read: {error}": "无法读取数据库：{error}",
        "Database loaded: {count} ore analyses.": "数据库已加载：{count} 条矿样分析。",
        "Missing columns for SilverQuest: {error}": "SilverQuest 缺少列：{error}",
        "No usable Pb-isotope rows in the current data.": "当前数据中没有可用的铅同位素行。",
        "SilverQuest plugin not loaded.": "SilverQuest 插件未加载。",
        "SilverQuest search failed: {error}": "SilverQuest 检索失败：{error}",
        "Colour indices exceeded the ramp and were clamped; lower the maximum distance.": "颜色索引超出色带已被截断；请降低最大距离。",
        "Grouping": "分组",
        "Grouping Column:": "分组列：",
        "Column whose distinct values are assigned to the sample and reference roles.": "其不同取值被分配为样品与参考角色的列。",
        "Offer only the groups currently visible in the legend": "仅提供图例中当前可见的分组",
        "Sample and Reference Groups": "样品分组与参考分组",
        "Sample Groups": "样品分组",
        "Reference Groups": "参考分组",
        "Samples to look up.": "需要溯源的样品。",
        "Ores the samples are compared against.": "用于对比样品的矿源。",
        "Optional Extra References": "可选的额外参考",
        "Add the galena reference database": "加入方铅矿参考数据库",
        "Used when no reference group is selected, or in addition to the reference groups.": "未选择参考分组时使用，或作为参考分组的补充。",
        "Path to Pb_DB_20240310AllGalenas.xlsx.": "Pb_DB_20240310AllGalenas.xlsx 的路径。",
        "All": "全部",
        "plus the galena database": "外加方铅矿数据库",
        "groups selected on both sides are used as references": "两侧同时选中的分组将按参考使用",
        "Samples: {groups} group(s), {rows} row(s)": "样品：{groups} 个分组，{rows} 行",
        "References: {groups} group(s), {rows} row(s)": "参考：{groups} 个分组，{rows} 行",
        "{group} ({count} rows)": "{group}（{count} 行）",
        "Search Pb-isotope samples against reference groups of your grouping column.": "按分组列选出的参考分组检索铅同位素样品。",
        "Please select a grouping column.": "请选择一个分组列。",
        "Please select at least one sample group.": "请至少选择一个样品分组。",
        "Please select at least one reference group or enable the galena database.": "请至少选择一个参考分组，或启用方铅矿数据库。",
        "A SilverQuest search is already running.": "SilverQuest 检索已在运行中。",
        "Apply to Data": "应用到数据",
        "Write the roles back as a group column and make it active.": "把角色写回为分组列并设为当前分组。",
        "The data changed since the search; run it again before applying.": "数据在检索后已改变；请重新运行后再应用。",
        "Roles added as group column {column}.": "角色已添加为分组列 {column}。",
        "Samples: {entered} in the search, {matched} matched, {unmatched} unmatched.": "样品：{entered} 个进入检索，{matched} 个匹配，{unmatched} 个未匹配。",
        "References: {entered} in the search, {matched} matched, {unmatched} unmatched.": "参考：{entered} 个进入检索，{matched} 个被命中，{unmatched} 个未被命中。",
        "Samples: {excluded} row(s) left out (unusable Pb ratios).": "样品：{excluded} 行因铅比值不可用未进入检索。",
        "References: {excluded} row(s) left out (unusable Pb ratios).": "参考：{excluded} 行因铅比值不可用未进入检索。",
        "references: {count} selected row(s)": "参考：所选 {count} 行",
        "references: galena database ({count} rows)": "参考：方铅矿数据库（{count} 行）",
        "references: none": "参考：无",
        "SilverQuest ({summary}, {source}): {total} hits.": "SilverQuest（{summary}，{source}）：{total} 个命中。",
        "SilverQuest ({summary}, {source}): showing the {shown} closest of {total} hits; export for the full list.": "SilverQuest（{summary}，{source}）：显示 {total} 个命中中最近的 {shown} 个；导出可获取完整列表。",
        "Export Hits": "导出命中",
        "Analysis": "分析",
        "Country": "国家",
        "Latitude": "纬度",
        "Longitude": "经度",
        "Distance": "距离",
        "Fractionation": "分馏量",
        "T1 (1st Stage):": "T1（第一阶段）：",
        "T2 (Earth Age):": "T2（地球年龄）：",
        "Tooltip Settings": "提示设置",
        "Triangle down (v)": "倒三角 (v)",
        "Triangle Up (^)": "上三角 (^)",
        "Tsec (2nd Stage):": "Tsec（第二阶段）：",
        "U Ratio (235/238):": "U 比值 (235/238)：",
        "X (X)": "X (X)",
        "a0 (206/204):": "a0 (206/204)：",
        "a1 (206/204):": "a1 (206/204)：",
        "b0 (207/204):": "b0 (207/204)：",
        "b1 (207/204):": "b1 (207/204)：",
        "c0 (208/204):": "c0 (208/204)：",
        "c1 (208/204):": "c1 (208/204)：",
        "learning_rate: {value}": "学习率：{value}",
        "metric:": "度量：",
        "min_dist: {value:.3f}": "最小距离：{value:.3f}",
        "n_components:": "主成分数：",
        "n_neighbors: {value}": "邻居数：{value}",
        "perplexity: {value}": "困惑度：{value}",
        "random_state:": "随机种子：",
        "random_state: {value}": "随机种子：{value}",
        "support_fraction: {value:.2f}": "支持比例：{value:.2f}",
        "{param}: {value:.3f}": "{param}：{value:.3f}",
        "{param}: {value}": "{param}：{value}",
        "λ (232Th):": "λ (232Th)：",
        "λ (235U):": "λ (235U)：",
        "λ (238U):": "λ (238U)：",
        "μ (Mantle):": "μ（地幔）：",
        "ω (Mantle):": "ω（地幔）：",
    }

    en_data = _merge_with_missing(en_data, expected_keys)
    zh_data = _merge_with_missing(zh_data, expected_keys)

    for key, value in zh_translations.items():
        if key in zh_data:
            zh_data[key] = value

    _write_json(en_path, en_data)
    _write_json(zh_path, zh_data)
    print("Locales synced successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
