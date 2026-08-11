# utils/ 模块开发文档

## 模块概述

`utils/` 提供日志相关工具函数。

**文件清单**

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块入口，导出 `setup_logging`, `LoggerWriter` |
| `logger.py` | 旋转文件日志 + stdout/stderr 重定向 |

---

## 1. logger.py — 日志系统

### 职责
配置旋转文件日志（主日志 + 错误日志），重定向 stdout/stderr 到日志文件，
启动时归档历史日志，并提供控制台输出。

### LoggerWriter 类

```python
class LoggerWriter:
    """同时写入日志文件和原始控制台流的自定义 writer"""

    def __init__(self, logger, level, original_stream)
    def write(self, buf)   # 写入控制台 + 缓冲写入日志
    def fileno(self)       # 返回原始流的 fileno，支持 faulthandler
    def flush(self)
```

- 按行缓冲: 遇到 `\n` 时将完整行写入 logger
- 保留原始控制台输出 (通过 `original_stream`)
- stdout → INFO 级别, stderr → ERROR 级别
- `fileno()` 委托给 `original_stream`，使 `faulthandler` 可正常工作

### setup_logging 函数

```python
def setup_logging(log_filename='isotopes_analyse.log',
                  max_bytes=50*1024*1024,    # 50MB
                  backup_count=2,
                  *,
                  archive=True,               # 启动时归档旧主日志
                  console_level=None,          # 控制台级别，默认 INFO
                  use_color=True)              # tty 时启用 ANSI 颜色
```

**配置内容:**
1. **主日志** `RotatingFileHandler` — 50MB 旋转，保留 2 个备份，DEBUG 级别
2. **错误日志** `isotopes_analyse.error.log` — 独立旋转文件，仅 ERROR 及以上（事后排查）
3. **控制台** `StreamHandler(stderr)` — 默认 INFO，tty 时带级别颜色
4. 格式: `%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d: %(message)s`
   （含级别名，8 字符左对齐）
5. 日志级别可通过环境变量 `ISOTOPES_LOG_LEVEL` 配置 (默认 DEBUG)
6. **启动归档**: `archive=True` 时把上次主日志重命名为
   `isotopes_analyse.<YYYYMMDD-HHMMSS>.log`，最多保留 5 份历史
7. 静默第三方噪声日志：matplotlib、matplotlib.font_manager、numba、PIL（WARNING）
8. 重定向 `sys.stdout` → LoggerWriter(INFO)、`sys.stderr` → LoggerWriter(ERROR)
9. handler 安装幂等（重复调用替换而非堆叠）

### 日志文件
| 文件 | 级别 | 用途 |
|------|------|------|
| `isotopes_analyse.log` | DEBUG | 全量运行日志（含 print 捕获） |
| `isotopes_analyse.error.log` | ERROR+ | 仅错误/崩溃，快速定位 |
| `isotopes_analyse.<ts>.log` | — | 历史会话归档（启动时生成，保留 5 份） |

- 开发环境: `项目根目录/`
- 打包环境: 可执行文件同目录

### 应用内日志查看器
UI 菜单 `文件 > 查看日志...`（`ui/dialogs/log_viewer.py`）：
- 主日志 / 错误日志切换，行数可调（50–5000 行尾部）
- 刷新、打开文件（系统默认编辑器）、ANSI 码剥离

---

## 2. 图标与色块工具迁移

- 图标与色块渲染工具已迁移到 `ui/icons.py`
- `utils/` 不再维护 `icons.py`

---

## 依赖关系

```
logger.py (无内部依赖)
  ↑
main.py (启动时调用 setup_logging())
  ↑
ui/dialogs/log_viewer.py (读取主日志/错误日志，只读)
```

---

## 改进建议

改进建议已迁移至 `docs/development_plan.md`。
