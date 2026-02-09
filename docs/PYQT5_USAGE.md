# PyQt5 版本使用指南

> 版本：1.0
> 日期：2026-02-09
> 状态：可用

---

## 📋 目录

1. [快速开始](#快速开始)
2. [安装依赖](#安装依赖)
3. [运行应用](#运行应用)
4. [功能说明](#功能说明)
5. [常见问题](#常见问题)
6. [开发指南](#开发指南)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 pip
pip install pyqt5>=5.15.10 pyqt5-qt5>=5.15.11

# 或使用 uv（推荐）
uv pip install pyqt5>=5.15.10 pyqt5-qt5>=5.15.11
```

### 2. 运行应用

```bash
python main_qt5.py
```

---

## 📦 安装依赖

### 必需依赖

- **PyQt5** >= 5.15.10
- **PyQt5-Qt5** >= 5.15.11
- **matplotlib** (已在项目中)
- **pandas** (已在项目中)
- **numpy** (已在项目中)
- **scikit-learn** (已在项目中)
- **umap-learn** (已在项目中)

### 安装命令

```bash
# 完整安装
pip install -r requirements.txt

# 或仅安装 PyQt5
pip install pyqt5>=5.15.10 pyqt5-qt5>=5.15.11
```

---

## 🎮 运行应用

### 基本运行

```bash
python main_qt5.py
```

### 带数据文件运行

应用启动后会自动：
1. 尝试加载上次的会话数据
2. 如果没有会话数据，显示文件选择对话框
3. 加载数据后显示主窗口和可视化

### 命令行选项

```bash
# 查看帮助
python main_qt5.py --help

# 指定数据文件
python main_qt5.py --file data.xlsx

# 指定工作表
python main_qt5.py --file data.xlsx --sheet Sheet1
```

---

## 🎯 功能说明

### 1. 数据加载

#### 支持的文件格式
- **Excel** (.xlsx, .xls)
- **CSV** (.csv)

#### 加载流程
1. 点击 **文件 → 加载数据** 或使用快捷键
2. 选择数据文件
3. 如果是 Excel 文件，选择工作表
4. 配置分组列和数据列
5. 数据加载完成

### 2. 控制面板

控制面板分为 5 个主要部分：

#### 2.1 Modeling（建模）
- **渲染模式选择**：UMAP / t-SNE / PCA / 2D / 3D / Ternary
- **UMAP 参数**：
  - n_neighbors (2-200)
  - min_dist (0.0-1.0)
  - metric (euclidean, manhattan, cosine, correlation)
- **t-SNE 参数**：
  - perplexity (5-50)
  - learning_rate (10-1000)
- **PCA 参数**：
  - n_components (2-10)
  - standardize (是/否)

#### 2.2 Display（显示）
- **点大小**：调整散点图点的大小
- **网格显示**：显示/隐藏网格
- **KDE 显示**：显示/隐藏核密度估计
- **边际 KDE**：显示/隐藏边际 KDE
- **椭圆显示**：显示/隐藏置信椭圆
- **颜色方案**：选择配色方案

#### 2.3 Legend（图例）
- **分组可见性**：管理各分组的显示/隐藏
- **显示全部/隐藏全部**：快速切换所有分组
- **图例位置**：选择图例位置（11 个选项）
- **图例列数**：设置图例列数（1-5）

#### 2.4 Tools（工具）
- **导出选中数据**：导出选中的数据点为 CSV/Excel

#### 2.5 Geochemistry（地球化学）
- **模型曲线**：显示/隐藏模型曲线
- **等时线**：显示/隐藏等时线
- **计算等时线年龄**：计算选中点的等时线年龄
- **V1/V2 参数**：设置地球化学参数

### 3. 交互功能

#### 3.1 鼠标悬停（Hover）
- 鼠标悬停在数据点上时显示详细信息
- 显示样本编号、发现地点、时期等信息

#### 3.2 点击选择（Click）
- 双击数据点选择/取消选择
- 选中的点会高亮显示

#### 3.3 图例交互（Legend Click）
- 点击图例项切换该分组的可见性
- 图例文本和标记会变灰表示隐藏

#### 3.4 矩形选择
- 启用选择工具后，拖动鼠标框选数据点
- 框选的点会被添加到选中集合

### 4. 导出功能

#### 4.1 导出选中数据
1. 选择数据点（双击或框选）
2. 打开控制面板 → Tools
3. 点击 **导出选中数据**
4. 选择保存位置和格式（CSV/Excel）

#### 4.2 导出图像
- 使用 matplotlib 工具栏的保存按钮
- 支持 PNG, PDF, SVG 等格式

---

## ❓ 常见问题

### Q1: 应用启动失败

**A:** 检查以下几点：
1. 确认已安装 PyQt5：`pip list | grep PyQt5`
2. 检查 Python 版本：需要 Python 3.8+
3. 查看错误日志：运行时的错误信息

### Q2: 数据加载失败

**A:** 可能的原因：
1. 文件格式不支持（仅支持 Excel 和 CSV）
2. 文件损坏或格式错误
3. 缺少必需的列（需要至少一个分组列和两个数据列）

### Q3: 控制面板不显示

**A:** 解决方法：
1. 点击 **视图 → 控制面板** 或使用快捷键
2. 检查控制面板是否被最小化
3. 重启应用

### Q4: 图形不更新

**A:** 尝试：
1. 调整任意参数触发重绘
2. 切换渲染模式
3. 重新加载数据

### Q5: 中文显示乱码

**A:** 解决方法：
1. 确认系统支持中文字体
2. 检查 matplotlib 字体配置
3. 在设置中选择合适的字体

---

## 🛠️ 开发指南

### 项目结构

```
IsotopesAnalyse/
├── main_qt5.py                 # PyQt5 版本入口
├── ui/
│   ├── qt5_app.py             # Qt5 应用程序类
│   ├── qt5_main_window.py     # Qt5 主窗口
│   ├── qt5_control_panel.py   # Qt5 控制面板
│   └── qt5_dialogs/           # Qt5 对话框
│       ├── file_dialog.py
│       ├── sheet_dialog.py
│       ├── data_config.py
│       ├── two_d_dialog.py
│       ├── three_d_dialog.py
│       ├── ternary_dialog.py
│       └── progress_dialog.py
├── data/
│   └── qt5_loader.py          # Qt5 数据加载器
├── visualization/
│   └── events.py              # 事件处理器
└── core/
    └── state.py               # 全局状态管理
```

### 添加新功能

#### 1. 添加新的控制参数

在 `ui/qt5_control_panel.py` 中：

```python
# 在相应的 _build_xxx_section() 方法中添加控件
def _build_display_section(self):
    # ... 现有代码 ...

    # 添加新参数
    new_param_group = QGroupBox(translate("New Parameter"))
    new_param_layout = QVBoxLayout()

    self.new_param_slider = QSlider(Qt.Horizontal)
    self.new_param_slider.setMinimum(0)
    self.new_param_slider.setMaximum(100)
    self.new_param_slider.valueChanged.connect(self._on_new_param_change)
    new_param_layout.addWidget(self.new_param_slider)

    new_param_group.setLayout(new_param_layout)
    layout.addWidget(new_param_group)

# 添加事件处理器
def _on_new_param_change(self, value):
    app_state.new_param = value
    self._on_change()
```

#### 2. 添加新的对话框

创建新文件 `ui/qt5_dialogs/new_dialog.py`：

```python
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
from core.localization import translate

class Qt5NewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(translate("New Dialog"))
        layout = QVBoxLayout(self)

        # 添加控件
        ok_btn = QPushButton(translate("OK"))
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

def show_new_dialog():
    dialog = Qt5NewDialog()
    return dialog.exec_() == QDialog.Accepted
```

#### 3. 添加新的事件处理器

在 `visualization/events.py` 中：

```python
def on_new_event(event):
    """处理新事件"""
    try:
        # 事件处理逻辑
        pass
    except Exception as e:
        print(f"[WARN] New event handler error: {e}", flush=True)
```

在 `ui/qt5_main_window.py` 中连接：

```python
def _connect_event_handlers(self, canvas):
    # ... 现有代码 ...
    canvas.mpl_connect('new_event', on_new_event)
```

### 调试技巧

#### 1. 启用调试日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. 检查状态

```python
from core.state import app_state
print(f"Current state: {app_state.__dict__}")
```

#### 3. 测试单个组件

```python
from PyQt5.QtWidgets import QApplication
from ui.qt5_control_panel import Qt5ControlPanel

app = QApplication([])
panel = Qt5ControlPanel()
panel.show()
app.exec_()
```

---

## 📚 参考资料

### 官方文档
- [PyQt5 官方文档](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [Qt5 文档](https://doc.qt.io/qt-5/)
- [matplotlib 文档](https://matplotlib.org/stable/contents.html)

### 项目文档
- [迁移方案](PYQT5_MIGRATION_PLAN.md)
- [进度跟踪](PYQT5_PROGRESS.md)
- [当前状态](PYQT5_STATUS.md)

### 相关资源
- [PyQt5 教程](https://www.pythonguis.com/pyqt5-tutorial/)
- [Qt Designer 使用指南](https://doc.qt.io/qt-5/qtdesigner-manual.html)

---

## 🤝 贡献指南

### 报告问题

如果发现 bug 或有功能建议，请：
1. 检查是否已有相关 issue
2. 创建新 issue，包含：
   - 问题描述
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（Python 版本、PyQt5 版本等）

### 提交代码

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -m "feat: add new feature"`
4. 推送到分支：`git push origin feature/new-feature`
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 添加必要的注释和文档字符串
- 确保所有测试通过
- 更新相关文档

---

## 📄 许可证

与主项目保持一致

---

## 📞 联系方式

- 项目地址：[GitHub Repository]
- 问题反馈：[Issues]
- 文档：[Documentation]

---

> 最后更新：2026-02-09
> 维护者：Claude Code
> 版本：1.0
