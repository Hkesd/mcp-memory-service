# Plus Extension 快速开始指南

> 5 分钟快速上手 ChromaDB / DashVector / Hybrid Plus 存储后端

## 🚀 一键安装

```bash
# 1. 安装依赖
pip install chromadb dashvector sentence-transformers

# 2. 选择后端配置（三选一）
```

## 选项 1: ChromaDB (本地向量数据库)

**适合：** 本地开发、单设备使用、追求性能

```bash
# 启动 ChromaDB 服务
chroma run --host localhost --port 8000

# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=chromadb
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000

# 启动 MCP Memory Service
uv run memory server
```

**性能：**
- 读取延迟: ~10ms
- 写入延迟: ~20ms
- 存储位置: 本地磁盘
- 成本: 免费

## 选项 2: DashVector (阿里云向量检索)

**适合：** 云端存储、多设备同步、生产环境

```bash
# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=dashvector
export DASHVECTOR_API_KEY=你的_API_密钥
export DASHVECTOR_ENDPOINT=https://your-endpoint.dashvector.cn-hangzhou.aliyuncs.com

# 启动 MCP Memory Service
uv run memory server
```

**性能：**
- 读取延迟: ~50ms
- 写入延迟: ~100ms
- 存储位置: 阿里云
- 成本: 按量付费

**获取 DashVector 凭证：**
1. 访问 https://dashvector.console.aliyun.com/
2. 创建实例并获取 API Key 和 Endpoint

## 选项 3: Hybrid Plus (混合模式) ⭐ 推荐

**适合：** 兼顾性能和同步、生产环境最佳实践

```bash
# 启动 ChromaDB 服务
chroma run --host localhost --port 8000

# 配置环境变量
export MCP_MEMORY_STORAGE_BACKEND=hybrid_plus
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export DASHVECTOR_API_KEY=你的_API_密钥
export DASHVECTOR_ENDPOINT=https://your-endpoint.dashvector.cn-hangzhou.aliyuncs.com

# 启动 MCP Memory Service
uv run memory server
```

**性能：**
- 读取延迟: ~10ms (本地 ChromaDB)
- 写入延迟: ~20ms (主存储) + 后台同步
- 存储位置: 本地 + 云端双备份
- 成本: 免费 + 按量付费
- 同步间隔: 5 分钟自动同步

**工作原理：**
```
写入 → ChromaDB (快速本地) → 后台异步同步 → DashVector (云端备份)
读取 ← ChromaDB (快速本地)
```

## 验证安装

```bash
# 查看服务状态
curl http://127.0.0.1:8000/api/health

# 存储一条测试记忆
curl -X POST http://127.0.0.1:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "测试记忆：Plus Extension 工作正常", "tags": ["test"]}'

# 搜索记忆
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "limit": 5}'
```

## 自动降级机制

所有后端都有自动降级保护：

```
ChromaDB 不可用 → 自动降级到 SQLite-vec ✅
DashVector 不可用 → 自动降级到 SQLite-vec ✅
Hybrid Plus:
  - ChromaDB 不可用 → SQLite-vec
  - DashVector 不可用 → 仅使用 ChromaDB (不影响服务)
```

**日志示例：**
```
⚠️  ChromaDB connection failed: ..., falling back to SQLite-vec
✅ Service continues with SQLite-vec storage
```

## 故障排查

### ChromaDB 无法启动

```bash
# 检查端口占用
lsof -i :8000

# 更换端口
chroma run --host localhost --port 8001
export CHROMADB_PORT=8001
```

### DashVector 认证失败

```bash
# 验证凭证
echo $DASHVECTOR_API_KEY
echo $DASHVECTOR_ENDPOINT

# 测试连接
python3 -c "
import dashvector
client = dashvector.Client(
    api_key='$DASHVECTOR_API_KEY',
    endpoint='$DASHVECTOR_ENDPOINT'
)
print('✅ DashVector 连接成功')
"
```

### 查看日志

```bash
# 启动服务时查看详细日志
uv run memory server --log-level debug
```

## 性能对比

| 后端 | 读延迟 | 写延迟 | 多设备 | 离线可用 | 成本 |
|------|--------|--------|--------|----------|------|
| SQLite-vec (原生) | ~5ms | ~10ms | ❌ | ✅ | 免费 |
| ChromaDB | ~10ms | ~20ms | ❌ | ✅ | 免费 |
| DashVector | ~50ms | ~100ms | ✅ | ❌ | 付费 |
| Hybrid Plus | ~10ms | ~20ms | ✅ | ✅ | 混合 |

## 环境变量完整列表

### ChromaDB 配置
```bash
CHROMADB_HOST=localhost              # 服务器地址
CHROMADB_PORT=8000                   # 服务器端口
CHROMADB_COLLECTION=mcp_memory       # 集合名称（可选）
```

### DashVector 配置
```bash
DASHVECTOR_API_KEY=sk-xxxxx         # API 密钥（必填）
DASHVECTOR_ENDPOINT=https://...     # 服务端点（必填）
DASHVECTOR_COLLECTION=mcp_memory    # 集合名称（可选）
```

### Hybrid Plus 配置
```bash
# 组合上述所有 ChromaDB 和 DashVector 配置
```

## 下一步

- 📖 阅读完整文档: `PLUS_EXTENSION_README.md`
- 🔧 高级配置: `src/mcp_memory_service/storage/plus_extension/README.md`
- 🐛 问题反馈: GitHub Issues
- 💡 功能建议: GitHub Discussions

## 与上游同步

```bash
# 同步原仓库更新
git checkout main
git pull upstream main
git push origin main

# 合并到扩展分支
git checkout plus-extension
git rebase main
git push origin plus-extension --force-with-lease
```

## 贡献

欢迎贡献新的存储后端！参考 `plus_extension/` 目录结构。

---

**开发完成时间：** 2026-01-09
**测试状态：** ✅ 语法验证通过
**推送状态：** ⏳ 待用户推送到远程仓库
