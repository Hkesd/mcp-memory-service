# Plus Extension - 扩展存储后端

> **注意**: 这是 mcp-memory-service 的社区扩展，提供额外的存储后端选项。不影响原项目代码。

## 概述

Plus Extension 为 MCP Memory Service 添加了 3 个额外的存储后端：

1. **ChromaDB** - 本地向量数据库
2. **DashVector** - 阿里云向量检索服务
3. **Hybrid Plus** - ChromaDB + DashVector 混合模式

## 快速开始

### 安装依赖

```bash
# 安装所有扩展依赖
pip install chromadb dashvector sentence-transformers

# 或单独安装
pip install chromadb              # ChromaDB 后端
pip install dashvector            # DashVector 后端
pip install sentence-transformers # 嵌入模型（DashVector 需要）
```

### 配置使用

#### 1. ChromaDB 后端

```bash
# 启动 ChromaDB 服务器
chroma run --host localhost --port 8000

# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=chromadb
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000

# 启动 MCP Memory Service
uv run memory server
```

#### 2. DashVector 后端

```bash
# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=dashvector
export DASHVECTOR_API_KEY=你的API密钥
export DASHVECTOR_ENDPOINT=你的服务端点

# 启动 MCP Memory Service
uv run memory server
```

#### 3. Hybrid Plus 后端（推荐）

```bash
# 启动 ChromaDB 服务器
chroma run --host localhost --port 8000

# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=hybrid_plus
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export DASHVECTOR_API_KEY=你的API密钥
export DASHVECTOR_ENDPOINT=你的服务端点

# 启动 MCP Memory Service
uv run memory server
```

## 特性对比

| 后端 | 读取延迟 | 写入延迟 | 存储位置 | 成本 | 多设备同步 |
|------|---------|---------|---------|------|-----------|
| ChromaDB | ~10ms | ~20ms | 本地磁盘 | 免费 | ❌ |
| DashVector | ~50ms | ~100ms | 阿里云 | 按量付费 | ✅ |
| Hybrid Plus | ~10ms | ~20ms | 本地+云 | 免费+按量 | ✅ |
| SQLite-vec（原生） | ~5ms | ~10ms | 本地磁盘 | 免费 | ❌ |

## 架构设计

### 最小侵入原则

Plus Extension 遵循最小侵入设计：

- ✅ 所有扩展代码在 `plus_extension/` 目录
- ✅ 只修改 `storage/factory.py` 两处（共 10 行代码）
- ✅ 不影响原有 3 个后端（SQLite-vec、Cloudflare、Hybrid）
- ✅ 通过环境变量控制，无需修改代码

### 代码修改点

**1. `storage/factory.py` - `get_storage_backend_class()` 函数：**

```python
elif backend in ["chromadb", "dashvector", "hybrid_plus"]:
    try:
        from ..plus_extension import get_plus_backend_class
        return get_plus_backend_class(backend)
    except ImportError as e:
        logger.error(f"Failed to import plus extension backend '{backend}': {e}")
        return _fallback_to_sqlite_vec()
```

**2. `storage/factory.py` - `create_storage_instance()` 函数：**

```python
elif StorageClass.__name__ in ["ChromaDBBackend", "DashVectorBackend", "HybridPlusBackend"]:
    from ..plus_extension import create_plus_instance
    storage = await create_plus_instance(StorageClass, sqlite_path)
    logger.info(f"Initialized {StorageClass.__name__}")
```

## 自动降级机制

所有扩展后端都实现了自动降级到 SQLite-vec：

```
ChromaDB 不可用 → SQLite-vec
DashVector 不可用 → SQLite-vec
Hybrid Plus:
  ChromaDB 不可用 → SQLite-vec
  DashVector 不可用 → 仅使用 ChromaDB
```

## 配置参考

### ChromaDB 环境变量

| 变量 | 默认值 | 说明 |
|-----|--------|------|
| `CHROMADB_HOST` | `localhost` | ChromaDB 服务器地址 |
| `CHROMADB_PORT` | `8000` | ChromaDB 服务器端口 |
| `CHROMADB_COLLECTION` | `mcp_memory` | 集合名称 |

### DashVector 环境变量

| 变量 | 必填 | 说明 |
|-----|------|------|
| `DASHVECTOR_API_KEY` | ✅ | DashVector API 密钥 |
| `DASHVECTOR_ENDPOINT` | ✅ | DashVector 服务端点 |
| `DASHVECTOR_COLLECTION` | ❌ | 集合名称（默认: `mcp_memory`）|

### Hybrid Plus 环境变量

组合上述 ChromaDB 和 DashVector 的所有变量。

## 故障排查

### ChromaDB 连接失败

```bash
# 检查 ChromaDB 服务是否运行
curl http://localhost:8000/api/v1/heartbeat

# 启动 ChromaDB 服务
chroma run --host localhost --port 8000
```

### DashVector 认证失败

```bash
# 验证凭证
echo $DASHVECTOR_API_KEY
echo $DASHVECTOR_ENDPOINT

# 测试连接
python -c "
import dashvector
client = dashvector.Client(api_key='$DASHVECTOR_API_KEY', endpoint='$DASHVECTOR_ENDPOINT')
print('连接成功')
"
```

### 自动降级到 SQLite-vec

如果日志显示 "falling back to SQLite-vec"：

- ✅ 这是预期行为，服务会继续使用本地存储
- ⚠️ 检查后端配置和网络连接
- 📝 查看日志了解具体失败原因

## 开发新后端

### 添加自定义后端的步骤

1. 在 `plus_extension/` 创建新后端文件
2. 继承 `MemoryStorage` 基类
3. 实现必需方法：
   - `initialize()`
   - `store_memory()`
   - `search_memories()`
   - `get_memory()`
   - `delete_memory()`
   - `list_memories()`
   - `close()`
4. 更新 `plus_extension/__init__.py` 工厂函数
5. **无需修改** `storage/factory.py`（自动检测）

### 示例代码

```python
from ..storage.base import MemoryStorage

class MyCustomBackend(MemoryStorage):
    async def initialize(self):
        # 初始化连接
        pass

    async def store_memory(self, content, tags=None, metadata=None):
        # 存储记忆
        pass

    # ... 实现其他方法
```

然后在 `plus_extension/__init__.py` 添加：

```python
def get_plus_backend_class(backend: str):
    if backend == "my_custom":
        from .my_custom_backend import MyCustomBackend
        return MyCustomBackend
    # ...
```

## 与原仓库同步

### 仓库配置

```bash
# 添加上游原始仓库
git remote add upstream https://github.com/doobidoo/mcp-memory-service.git

# 查看远程仓库
git remote -v
# origin    git@github.com:你的用户名/mcp-memory-service.git
# upstream  https://github.com/doobidoo/mcp-memory-service.git
```

### 同步上游更新

```bash
# 1. 拉取上游更新
git checkout main
git pull upstream main
git push origin main

# 2. 合并到扩展分支
git checkout plus-extension
git rebase main

# 3. 解决冲突（如果有）
# 主要可能冲突的文件：storage/factory.py
# 保留你的 plus_extension 检测代码

# 4. 推送更新
git push origin plus-extension --force-with-lease
```

### 冲突处理

如果 `storage/factory.py` 有冲突：

1. 打开文件查看冲突标记
2. 保留你的扩展代码（`plus_extension` 检测部分）
3. 合并上游的其他更改
4. 测试确保两者都能正常工作

## 许可证

与 MCP Memory Service 相同（Apache 2.0）

## 贡献

欢迎贡献新的存储后端！

1. Fork 仓库
2. 创建功能分支
3. 实现新后端
4. 提交 Pull Request

## 支持

- 📚 文档：`src/mcp_memory_service/plus_extension/`
- 🐛 问题反馈：GitHub Issues
- 💬 讨论：GitHub Discussions
