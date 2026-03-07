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
配置旋转文件日志，重定向 stdout/stderr 到日志文件。

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
                  backup_count=1)
```

**配置内容:**
1. `RotatingFileHandler` — 50MB 旋转，保留 1 个备份
2. 格式: `%(asctime)s [%(name)s:%(lineno)d] %(message)s`
3. 日志级别可通过环境变量 `ISOTOPES_LOG_LEVEL` 配置 (默认 DEBUG)
4. 静默 matplotlib 日志 (`WARNING` 级别)
5. 静默 numba 日志 (`WARNING` 级别)
6. 重定向 `sys.stdout` → LoggerWriter(INFO)
7. 重定向 `sys.stderr` → LoggerWriter(ERROR)

### 日志文件位置
- 开发环境: `项目根目录/isotopes_analyse.log`
- 打包环境: 可执行文件同目录

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
```

---

## 改进建议

改进建议已迁移至 `docs/development_plan.md`。
