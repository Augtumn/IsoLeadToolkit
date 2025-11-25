# Isotopes Analysis - 同位素数据可视化分析工具

一个强大的交互式同位素数据可视化分析工具，专为铅同位素等地球化学数据的降维分析和可视化而设计。

## 功能特点

### 核心功能
- **多维度降维算法支持**
  - UMAP（Uniform Manifold Approximation and Projection）
  - t-SNE（t-Distributed Stochastic Neighbor Embedding）
  
- **灵活的可视化模式**
  - 2D 散点图可视化
  - 3D 交互式可视化
  - 自定义维度选择

- **交互式数据探索**
  - 鼠标悬停显示详细信息
  - 点击选择样本
  - 批量导出选中样本数据
  - 图例点击切换显示/隐藏分组

- **参数实时调整**
  - UMAP 参数（邻居数、最小距离）
  - t-SNE 参数（困惑度、学习率）
  - 点大小调整
  - 随机种子控制

- **数据管理**
  - 支持 Excel 文件导入（.xlsx, .xls）
  - 多工作表选择
  - 灵活的数据列配置
  - 分组列自定义

- **会话持久化**
  - 自动保存参数设置
  - 文件路径记忆
  - 工作表配置保存

- **多语言支持**
  - 中文（默认）
  - English
  - 可扩展语言支持

## 系统要求

- Python >= 3.13
- 操作系统：Windows / macOS / Linux
- 依赖库详见 `pyproject.toml`

## 安装

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd IsotopesAnalyse
```

### 2. 安装依赖

推荐使用虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
.\venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -e .
```

或者使用 uv（推荐）：

```bash
uv sync
```

## 使用方法

### 启动应用

```bash
python main.py
```

### 工作流程

1. **数据加载**
   - 启动后会弹出文件选择对话框
   - 选择包含同位素数据的 Excel 文件
   - 选择对应的工作表

2. **数据配置**
   - 在配置对话框中选择：
     - **数据列**：用于降维分析的数值列（如同位素比值）
     - **分组列**：用于分组显示的分类列（如省份、时期等）
   - 选择渲染模式（2D 或 3D）

3. **可视化探索**
   - 使用控制面板调整参数
   - 通过滑块实时调整算法参数
   - 鼠标悬停查看样本详情
   - 点击样本进行选择/取消选择
   - 点击图例显示/隐藏特定分组

4. **导出数据**
   - 选中感兴趣的样本
   - 点击"Export Selected"按钮
   - 数据将导出到 `selected_samples.csv`

### 界面说明

#### 控制面板（右侧）
- **算法选择**：UMAP 或 t-SNE
- **分组选择**：切换不同的分组依据
- **参数调整滑块**：
  - UMAP：n_neighbors（邻居数）、min_dist（最小距离）
  - t-SNE：perplexity（困惑度）、learning_rate（学习率）
- **通用参数**：
  - Point Size：调整散点大小
  - Random State：控制随机种子以复现结果
- **功能按钮**：
  - Reconfigure Data：重新配置数据和列
  - Export Selected：导出选中的样本
  - Language：切换界面语言

#### 主画布
- **2D 模式**：二维散点图，支持缩放和平移
- **3D 模式**：三维交互视图，支持旋转和缩放

## 项目结构

```
IsotopesAnalyse/
├── main.py                 # 应用入口点
├── config.py              # 配置管理
├── state.py               # 全局应用状态
├── data.py                # 数据加载和处理
├── visualization.py       # 降维计算和绘图
├── events.py              # 事件处理器
├── session.py             # 会话参数持久化
├── control_panel.py       # 控制面板UI
├── file_dialog.py         # 文件选择对话框
├── sheet_dialog.py        # 工作表选择对话框
├── data_config.py         # 数据配置对话框
├── legend_dialog.py       # 图例管理
├── two_d_dialog.py        # 2D维度选择对话框
├── three_d_dialog.py      # 3D维度选择对话框
├── localization.py        # 多语言支持
├── locales/               # 语言文件目录
│   ├── en.json           # 英文翻译
│   └── zh.json           # 中文翻译
├── selected_samples.csv   # 导出的选中样本
├── pyproject.toml         # 项目依赖配置
└── README.md              # 项目文档
```

## 依赖库

- **matplotlib** >= 3.10.7 - 绘图库
- **numpy** >= 2.3.5 - 数值计算
- **pandas** >= 2.3.3 - 数据处理
- **openpyxl** >= 3.1.5 - Excel 文件读取
- **seaborn** >= 0.13.2 - 统计可视化
- **scikit-learn** >= 1.5.2 - t-SNE 算法
- **umap-learn** >= 0.5.6 - UMAP 算法

## 配置说明

### 默认配置（config.py）

```python
CONFIG = {
    'export_csv': 'selected_samples.csv',        # 导出文件名
    'algorithm_options': ['UMAP', 'tSNE'],       # 算法选项
    'default_language': 'zh',                     # 默认语言
    'umap_params': {                              # UMAP 默认参数
        'n_neighbors': 10,
        'min_dist': 0.1,
        'random_state': 42,
        'n_components': 2
    },
    'tsne_params': {                              # t-SNE 默认参数
        'perplexity': 30,
        'learning_rate': 200,
        'random_state': 42,
        'n_components': 2
    },
    'point_size': 60,                             # 默认点大小
    'figure_size': (13, 9),                       # 图形尺寸
    'figure_dpi': 130,                            # 图形分辨率
    'preferred_plot_fonts': [                     # 首选字体（支持中文）
        'Microsoft YaHei',
        'SimHei',
        'PingFang SC',
        ...
    ]
}
```

### 会话文件位置

会话参数保存在用户目录下：
- Windows: `C:\Users\<username>\.isotopes_analysis\params.json`
- macOS/Linux: `~/.isotopes_analysis/params.json`

## 使用技巧

### UMAP 参数调整
- **n_neighbors（邻居数）**：
  - 较小值（5-10）：保留局部结构，适合发现小簇
  - 较大值（30-50）：保留全局结构，适合观察整体分布
  
- **min_dist（最小距离）**：
  - 较小值（0.0-0.1）：点更密集，聚类更紧凑
  - 较大值（0.3-0.5）：点更分散，更均匀分布

### t-SNE 参数调整
- **perplexity（困惑度）**：
  - 通常设置为 5-50
  - 小数据集使用较小值
  - 大数据集可以使用较大值
  
- **learning_rate（学习率）**：
  - 通常设置为 10-1000
  - 如果结果呈球状，尝试增大学习率
  - 如果结果过于分散，尝试减小学习率

### 数据准备建议
- Excel 文件应包含：
  - 数值型数据列（如同位素比值）
  - 分类列（如产地、时期、类型等）
- 避免缺失值
- 确保数值列格式正确

## 常见问题

### Q: 程序启动后窗口模糊？
A: Windows 系统会自动启用高 DPI 感知模式。如果仍有问题，检查系统显示设置。

### Q: 中文显示为方块？
A: 程序会自动查找系统中的中文字体。确保系统安装了微软雅黑、SimHei 等中文字体。

### Q: UMAP/t-SNE 计算很慢？
A: 这是正常现象，尤其是大数据集。程序会缓存计算结果，相同参数下第二次会更快。

### Q: 如何保存可视化结果？
A: 使用 Matplotlib 工具栏的保存按钮，或按 Ctrl+S（macOS: Cmd+S）。

### Q: 如何重置所有设置？
A: 删除 `~/.isotopes_analysis/params.json` 文件，下次启动将使用默认设置。

## 开发说明

### 模块化设计
项目采用模块化设计，各模块职责明确：
- **config.py**: 集中管理配置参数
- **state.py**: 全局状态管理，避免循环依赖
- **data.py**: 数据加载和验证
- **visualization.py**: 算法计算和绘图逻辑
- **events.py**: 用户交互事件处理
- **session.py**: 会话持久化
- **control_panel.py**: UI 控件创建和布局
- **localization.py**: 国际化支持

### 添加新语言
1. 在 `locales/` 目录下创建新的 JSON 文件（如 `ja.json`）
2. 参考 `zh.json` 或 `en.json` 的格式添加翻译
3. 在 `config.py` 的 `languages` 字典中添加语言选项
4. 重启应用即可使用

### 扩展功能
- 修改 `CONFIG` 字典添加新配置项
- 在 `events.py` 中添加新的事件处理器
- 在 `visualization.py` 中添加新的算法支持

## 许可证

本项目用于学术研究和教学目的。

## 贡献

欢迎提交 Issue 和 Pull Request。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 邮件联系项目维护者

---

**最后更新**: 2025年11月26日