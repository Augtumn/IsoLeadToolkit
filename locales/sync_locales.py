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
        "Available Columns": "可用列",
        "Available Sheets": "可用工作表",
        "Box Select": "框选",
        "Circle (o)": "圆形 (o)",
        "Configure": "配置",
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
        "Failed to compute mixing: {error}": "计算混合失败：{error}",
        "Failed to export data: {error}": "导出数据失败：{error}",
        "Failed to load Excel file: {error}": "加载 Excel 文件失败：{error}",
        "Failed to load geochemistry model: {error}": "加载地球化学模型失败：{error}",
        "Failed to open KDE style dialog: {error}": "打开 KDE 样式对话框失败：{error}",
        "Failed to open marginal KDE style dialog: {error}": "打开边际 KDE 样式对话框失败：{error}",
        "Failed to open tooltip configuration: {error}": "打开提示配置失败：{error}",
        "Failed to reload data": "重新加载数据失败",
        "Failed to reset parameters: {error}": "重置参数失败：{error}",
        "Failed to show PCA loadings: {error}": "显示 PCA 载荷失败：{error}",
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
        "Mixtures: {count}": "混合：{count}",
        "No data selected for analysis.": "未选择用于分析的数据。",
        "No data selected. Please select data points first.": "未选择数据。请先选择数据点。",
        "No mixing groups defined": "未定义混合分组",
        "Opacity: {value:.2f}": "透明度：{value:.2f}",
        "PB_EVOL_76": "PB_EVOL_76",
        "PB_EVOL_86": "PB_EVOL_86",
        "PB_KAPPA_AGE": "PB_KAPPA_AGE",
        "PB_MU_AGE": "PB_MU_AGE",
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
        "Render Mode": "渲染模式",
        "Results": "结果",
        "RobustPCA": "稳健PCA",
        "RobustPCA Parameters": "稳健PCA参数",
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
        "T1 (1st Stage):": "T1（第一阶段）：",
        "T2 (Earth Age):": "T2（地球年龄）：",
        "Tooltip Settings": "提示设置",
        "Triangle Down (v)": "倒三角 (v)",
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
