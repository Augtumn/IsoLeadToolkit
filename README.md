# Isotopes Analyse

一个基于 PyQt5 的同位素数据分析与可视化桌面应用程序。

## 功能特性

- **数据导入与处理**：支持 Excel 文件导入，自动识别和转换数据列
- **降维分析**：支持 UMAP、t-SNE、PCA、Robust PCA 等多种降维算法
- **地球化学可视化**：铅同位素比值图、三元图、模型曲线叠加
- **交互式绘图**：基于 Matplotlib 的交互式数据探索
- **多语言支持**：中文/英文界面切换
- **会话管理**：自动保存和恢复分析会话
- **主题定制**：可保存和加载自定义绘图主题

## 系统要求

- Python >= 3.13
- Windows / macOS / Linux

## 安装

### 使用 pip

```bash
# 克隆仓库
git clone <repository-url>
cd IsotopesAnalyse

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

### 使用 uv（推荐）

```bash
# 安装 uv
pip install uv

# 安装项目依赖
uv pip install -e .
```

## 运行

```bash
python main.py
```

## 主要依赖

- **PyQt5** >= 5.15：GUI 框架
- **matplotlib** >= 3.10：绘图库
- **pandas** >= 2.3：数据处理
- **numpy** >= 2.3：数值计算
- **scikit-learn** >= 1.5：机器学习算法
- **umap-learn** >= 0.5：UMAP 降维
- **seaborn** >= 0.13：统计可视化
- **mpltern** >= 1.0：三元图绘制

完整依赖列表见 [pyproject.toml](pyproject.toml)。

## 项目结构

```
IsotopesAnalyse/
├── main.py                 # 应用入口
├── ui/                     # 用户界面模块
│   ├── app.py             # Qt5 应用类
│   ├── main_window.py     # 主窗口
│   ├── control_panel.py   # 控制面板
│   └── dialogs/           # 对话框组件
├── core/                   # 核心功能
│   ├── state.py           # 应用状态管理
│   ├── session.py         # 会话管理
│   ├── config.py          # 配置管理
│   └── localization.py    # 国际化
├── data/                   # 数据处理
│   ├── loader.py          # 数据加载
│   ├── geochemistry.py    # 地球化学计算
│   └── mixing.py          # 混合模型
├── visualization/          # 可视化模块
│   ├── plotting.py        # 主绘图逻辑
│   ├── plotting_embed.py  # 降维可视化
│   ├── plotting_style.py  # 样式管理
│   └── events.py          # 交互事件
├── utils/                  # 工具函数
├── locales/               # 语言文件
│   ├── zh.json           # 中文
│   └── en.json           # 英文
├── assets/                # 资源文件
└── docs/                  # 文档
```

## 使用说明

### 1. 导入数据

启动应用后，通过"文件"菜单或对话框选择 Excel 文件：
- 支持多工作表选择
- 自动识别数值列和分类列
- 可配置 X、Y、Z 轴和分组列

### 2. 降维分析

在控制面板中选择降维算法：
- **UMAP**：适合保留全局和局部结构
- **t-SNE**：适合发现局部聚类
- **PCA**：线性降维，快速
- **Robust PCA**：对异常值鲁棒

调整参数后点击"更新图表"查看结果。

### 3. 地球化学可视化

- 选择铅同位素比值（如 206Pb/204Pb vs 207Pb/204Pb）
- 启用模型曲线（Stacey & Kramers 等）
- 添加古等时线和模型年龄线
- 自定义方程叠加

### 4. 交互功能

- **缩放**：鼠标滚轮或工具栏
- **平移**：拖动图表
- **选择**：框选数据点查看详情
- **导出**：保存为 PNG、PDF、SVG 等格式

### 5. 主题定制

在"样式设置"面板中：
- 调整字体、颜色、标记样式
- 保存为自定义主题
- 加载预设或自定义主题

## 打包发布

使用 PyInstaller 打包为独立可执行文件：

```bash
pyinstaller build.spec
```

生成的可执行文件位于 `dist/IsotopesAnalyse/` 目录。

## 开发

### 添加新功能

1. 在相应模块中实现功能
2. 在 `ui/control_panel.py` 中添加控制组件
3. 更新 `locales/zh.json` 和 `locales/en.json` 添加翻译
4. 运行 `python locales/sync_locales.py` 同步翻译

### 代码风格

- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 添加必要的注释和文档字符串

### 日志

应用使用 Python logging 模块，日志文件保存在 `isotopes_analyse.log`（最大 50MB）。

## 常见问题

### Q: 应用启动失败？
A: 检查 Python 版本（需要 >= 3.13）和依赖是否正确安装。

### Q: 图表显示异常？
A: 尝试在"样式设置"中重置为默认主题。

### Q: 数据导入失败？
A: 确保 Excel 文件格式正确，包含数值列。

### Q: 如何切换语言？
A: 在"设置"菜单中选择"语言"。

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
