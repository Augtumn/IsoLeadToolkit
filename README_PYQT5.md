# IsotopesAnalyse - PyQt5 版本

> 同位素分析可视化工具 - PyQt5 现代化版本

---

## 🎯 版本说明

本项目现在提供两个版本：

### 1. **PyQt5 版本**（推荐）
- ✅ 现代化的 UI 设计
- ✅ 更好的性能和响应速度
- ✅ 完整的事件处理系统
- ✅ 丰富的交互功能
- ✅ 跨平台支持更好

**运行命令：**
```bash
python main_qt5.py
```

### 2. **Tkinter 版本**（传统）
- 原始版本
- 稳定可靠
- 功能完整

**运行命令：**
```bash
python main.py
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 PyQt5（仅 PyQt5 版本需要）
pip install pyqt5>=5.15.10 pyqt5-qt5>=5.15.11

# 或使用 uv（推荐）
uv pip install pyqt5>=5.15.10 pyqt5-qt5>=5.15.11
```

### 2. 运行应用

```bash
# PyQt5 版本（推荐）
python main_qt5.py

# Tkinter 版本
python main.py
```

---

## 📚 文档

### PyQt5 版本文档
- [使用指南](docs/PYQT5_USAGE.md) - 详细的使用说明
- [迁移方案](docs/PYQT5_MIGRATION_PLAN.md) - 技术迁移方案
- [进度跟踪](docs/PYQT5_PROGRESS.md) - 开发进度
- [当前状态](docs/PYQT5_STATUS.md) - 功能状态

### 功能对比

| 功能 | Tkinter 版本 | PyQt5 版本 |
|------|-------------|-----------|
| 数据加载 | ✅ | ✅ |
| 数据配置 | ✅ | ✅ |
| UMAP/t-SNE/PCA | ✅ | ✅ |
| 2D/3D/Ternary 绘图 | ✅ | ✅ |
| 控制面板 | ✅ | ✅ 更强大 |
| 事件处理 | ✅ | ✅ 更流畅 |
| 导出功能 | ✅ | ✅ |
| 图例管理 | ✅ | ✅ 更灵活 |
| 地球化学功能 | ✅ | ✅ |
| UI 美观度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 响应速度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🎨 PyQt5 版本特色

### 1. 现代化 UI
- 清爽的界面设计
- 统一的配色方案
- 流畅的动画效果

### 2. 强大的控制面板
- 5 个功能分区（Modeling/Display/Legend/Tools/Geochemistry）
- 完整的参数控制
- 实时预览

### 3. 丰富的交互
- 鼠标悬停显示详情
- 点击选择数据点
- 图例交互切换
- 矩形框选工具

### 4. 灵活的导出
- 支持 CSV/Excel 格式
- 导出选中数据
- 高质量图像导出

---

## 📦 依赖要求

### 共同依赖
- Python >= 3.8
- matplotlib
- pandas
- numpy
- scikit-learn
- umap-learn

### PyQt5 版本额外依赖
- PyQt5 >= 5.15.10
- PyQt5-Qt5 >= 5.15.11

---

## 🔧 开发

### 项目结构

```
IsotopesAnalyse/
├── main.py                    # Tkinter 版本入口
├── main_qt5.py               # PyQt5 版本入口
├── ui/
│   ├── qt5_app.py           # PyQt5 应用
│   ├── qt5_main_window.py   # PyQt5 主窗口
│   ├── qt5_control_panel.py # PyQt5 控制面板
│   ├── qt5_dialogs/         # PyQt5 对话框
│   ├── panel/               # Tkinter 控制面板
│   └── dialogs/             # Tkinter 对话框
├── data/
│   ├── loader.py            # Tkinter 数据加载
│   └── qt5_loader.py        # PyQt5 数据加载
├── visualization/
│   ├── plotting.py          # 绘图功能
│   └── events.py            # 事件处理
├── core/
│   ├── state.py             # 全局状态
│   └── localization.py      # 国际化
└── docs/
    ├── PYQT5_USAGE.md       # PyQt5 使用指南
    ├── PYQT5_MIGRATION_PLAN.md
    ├── PYQT5_PROGRESS.md
    └── PYQT5_STATUS.md
```

### 测试

```bash
# 测试 PyQt5 导入
python test_qt5_imports.py

# 测试 PyQt5 应用
python main_qt5.py
```

---

## 🐛 已知问题

### PyQt5 版本
1. 国际化翻译刷新逻辑待完善
2. 工具栏图标使用文本按钮（待添加图标资源）

### 解决方案
- 大部分功能已完整实现
- 剩余问题不影响核心功能使用
- 持续改进中

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 如何贡献
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

---

## 📄 许可证

[项目许可证]

---

## 📞 联系

- 问题反馈：[GitHub Issues]
- 文档：[Documentation]

---

> **推荐使用 PyQt5 版本以获得最佳体验！**
>
> 最后更新：2026-02-09
