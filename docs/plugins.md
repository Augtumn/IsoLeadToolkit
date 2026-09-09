# 插件开发指南

IsotopesAnalyse 的插件系统允许将分析功能作为独立模块加载，支持内置和用户自定义插件。

## 架构

```
plugins/
├── api.py           # 接口定义（PluginMeta, BasePlugin, MLClassifierPlugin）
├── manager.py       # PluginManager — 发现、加载、验证、生命周期
├── registry.py      # 全局 plugin_manager 单例
├── builtins/        # 内置插件（自动发现）
├── examples/        # 第三方模板
└── (用户目录)        # ~/.isotopes_analysis/plugins/
```

## 快速开始

```bash
# 使用脚手架创建插件
uv run python scripts/new_plugin.py my_analysis

# 生成的文件：~/.isotopes_analysis/plugins/my_analysis.py
```

## 接口

### PluginMeta

```python
@dataclass(frozen=True)
class PluginMeta:
    name: str              # 唯一标识符
    version: str           # 语义版本
    api_version: str       # API 版本（不匹配拒绝加载）
    plugin_type: str       # "analysis" | "classifier" | 自定义
    author: str
    description: str
    source: str            # 自动设置 "builtin" | "user"
    signature: str         # 可选完整性哈希
    restricted: bool       # 受限模式（第三方插件）
```

### BasePlugin（所有插件必须实现）

```python
class BasePlugin(Protocol):
    meta: PluginMeta

    def validate_environment(self) -> tuple[bool, str]:
        """检查依赖环境，返回 (ok, message)"""
        ...

    def get_default_params(self) -> dict[str, Any]:
        """返回默认参数"""
        ...

    def build_ui(self, parent=None, callback=None) -> QWidget | None:
        """可选：返回 QWidget 显示在分析面板，None 表示不显示 UI"""
        ...
```

### MLClassifierPlugin（分类器插件）

```python
class MLClassifierPlugin(BasePlugin, Protocol):
    def fit(self, x, y, **params) -> dict[str, Any]:
        """训练模型，返回元数据"""
        ...

    def predict(self, x) -> Any:
        """预测标签"""
        ...

    def predict_proba(self, x) -> Any:
        """预测概率"""
        ...
```

## 加载流程

1. **发现**：扫描 `plugins/builtins/` 和 `~/.isotopes_analysis/plugins/`
2. **加载**：动态导入模块（注册名 `plugins._loaded.<stem>`，避免用户插件遮蔽
   `plugins.api` 等真实模块），提取实现 BasePlugin 的类
3. **验证**：调用 `validate_environment()`，失败则跳过并记录
4. **注册**：加入 `plugin_manager.plugins` 字典，键为文件名 stem

保留名（`api`、`manager`、`registry`、`builtins`、`__init__`）拒绝加载。

启动时自动加载（`ui/app.py`），也可手动：

```python
from plugins.registry import plugin_manager
plugin_manager.load_all()
```

## 内置插件

`load_plugin()` 以文件 stem 为键，`get()` 也支持 `meta.name` 查询。

| 文件 stem | meta.name | 类型 | 功能 |
|------|------|------|------|
| `endmember_plugin` | `endmember` | analysis | PCA 端元识别 + geochron 斜率过滤 |
| `mixing_plugin` | `mixing` | analysis | 混合模型最小二乘 + 蒙特卡洛不确定度 |
| `clustering_plugin` | `hdbscan_clustering` | analysis | HDBSCAN 密度聚类 |
| `provenance_ml_plugin` | `provenance_ml` | classifier | XGBoost OvR 产地分类（SMOTE+DBSCAN） |
| `subset_plugin` | `subset_analysis` | analysis | 子集选择与重分析 |
| `neighborhood_plugin` | `neighborhood_search` | analysis | KD-tree 邻域搜索 |

## 完整示例

```python
# ~/.isotopes_analysis/plugins/hello.py
from __future__ import annotations
from typing import Any
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from plugins.api import BasePlugin, PluginMeta
from core import translate

class HelloPlugin(BasePlugin):
    meta = PluginMeta(
        name="hello", version="1.0", api_version="1.0",
        plugin_type="analysis", author="Your Name",
        description="A minimal example plugin",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {"greeting": "Hello"}

    def build_ui(self, parent=None, callback=None):
        group = QGroupBox(translate("Hello Plugin"))
        layout = QVBoxLayout()
        label = QLabel(translate("Click the button to run analysis."))
        label.setWordWrap(True)
        layout.addWidget(label)
        btn = QPushButton(translate("Run"))
        btn.clicked.connect(callback)  # callback triggers the analysis dialog
        layout.addWidget(btn, 0, Qt.AlignHCenter)
        group.setLayout(layout)
        return group
```

## 错误处理

- 插件加载失败不阻止应用启动
- 失败信息可通过 `plugin_manager.failure_info(name)` 获取
- 状态报告 `plugin_manager.get_status()` 返回 `{loaded: {...}, failed: {...}}`
- 日志级别 `logger.warning` 用于可恢复错误

## API 版本兼容

- `api_version` 采用 `MAJOR.MINOR` 格式
- 与宿主版本（**1.0**）不一致即拒绝加载，并记录到 `failure_info()`
  （`plugins/manager.py::load_plugin` 的兼容门；修改宿主版本需同步更新插件）
- 预留的语义化策略：主版本不匹配直接拒绝，次版本差异仅告警——当前尚未实现
