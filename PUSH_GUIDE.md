# 推送到远程仓库指南

**当前状态：** ✅ 代码开发完成，本地提交完成
**下一步：** 推送到 GitHub 远程仓库

## 📋 当前分支状态

```bash
# 查看当前分支
$ git branch
  main
* plus-extension

# 查看提交记录
$ git log --oneline -3
f1fa650 docs: add development summary for Plus Extension
37d4036 docs: add Quick Start guide for Plus Extension
07331ce feat: add Plus Extension storage backends (ChromaDB, DashVector, Hybrid Plus)

# 查看远程仓库
$ git remote -v
origin   git@github.com:Hkesd/mcp-memory-service.git (fetch)
origin   git@github.com:Hkesd/mcp-memory-service.git (push)
upstream https://github.com/doobidoo/mcp-memory-service.git (fetch)
upstream https://github.com/doobidoo/mcp-memory-service.git (push)
```

## 🚀 推送步骤

### 方法 1: 直接推送（推荐）

```bash
# 推送 plus-extension 分支到你的 GitHub fork
git push origin plus-extension

# 如果是第一次推送，设置上游分支
git push -u origin plus-extension
```

### 方法 2: 先更新 main，再推送

```bash
# 1. 切换到 main 分支
git checkout main

# 2. 拉取上游更新（可选）
git pull upstream main

# 3. 推送 main 到你的 fork
git push origin main

# 4. 切换回 plus-extension
git checkout plus-extension

# 5. rebase 到最新 main（可选）
git rebase main

# 6. 推送 plus-extension
git push origin plus-extension
```

## ✅ 推送后验证

### 在 GitHub 上检查

1. 访问: https://github.com/Hkesd/mcp-memory-service
2. 切换到 `plus-extension` 分支
3. 应该能看到：
   - ✅ PLUS_EXTENSION_README.md
   - ✅ QUICK_START_PLUS.md
   - ✅ DEVELOPMENT_SUMMARY.md
   - ✅ PUSH_GUIDE.md (本文件)
   - ✅ src/mcp_memory_service/storage/plus_extension/ 目录

### 提交历史验证

```bash
# 在 GitHub 上查看提交
# https://github.com/Hkesd/mcp-memory-service/commits/plus-extension

应该看到 3 个提交：
1. feat: add Plus Extension storage backends (ChromaDB, DashVector, Hybrid Plus)
2. docs: add Quick Start guide for Plus Extension
3. docs: add development summary for Plus Extension
4. docs: add push guide (本次提交)
```

## 📊 推送的内容

### 新增文件（13 个）

```
PLUS_EXTENSION_README.md                               # 中文完整文档
QUICK_START_PLUS.md                                    # 5分钟快速开始
DEVELOPMENT_SUMMARY.md                                 # 开发总结
PUSH_GUIDE.md                                          # 推送指南（本文件）
src/mcp_memory_service/storage/plus_extension/
├── __init__.py                                        # 工厂函数
├── chromadb_backend.py                                # ChromaDB 后端
├── dashvector_backend.py                              # DashVector 后端
├── hybrid_plus_backend.py                             # Hybrid Plus 后端
├── README.md                                          # 英文文档
├── .env.example                                       # 配置示例
└── setup.sh                                           # 安装脚本
```

### 修改文件（1 个）

```
src/mcp_memory_service/storage/factory.py             # +11 行（2 个 elif 块）
```

### 代码统计

```
Total files:      14
Total additions:  ~2100 lines
Code:             ~850 lines
Documentation:    ~1100 lines
Config/Scripts:   ~150 lines
```

## 🔄 后续同步上游

### 定期同步流程（建议每周）

```bash
# 1. 拉取上游更新
git checkout main
git pull upstream main

# 2. 推送到你的 fork
git push origin main

# 3. 合并到扩展分支
git checkout plus-extension
git rebase main

# 4. 解决冲突（如果有）
# 主要关注 storage/factory.py

# 5. 推送更新
git push origin plus-extension --force-with-lease
```

### 冲突处理示例

如果 `factory.py` 有冲突：

```python
# 保留你的扩展代码
elif backend in ["chromadb", "dashvector", "hybrid_plus"]:
    try:
        from .plus_extension import get_plus_backend_class
        return get_plus_backend_class(backend)
    except ImportError as e:
        logger.error(f"Failed to import plus extension backend '{backend}': {e}")
        return _fallback_to_sqlite_vec()

# 同时保留上游的新后端（如果有）
elif backend == "new_upstream_backend":
    # 上游新增的代码
    ...
```

## 🎯 下一步（可选）

### 选项 1: 创建 Pull Request

如果你想将扩展贡献回原项目：

```bash
# 1. 在 GitHub 上点击 "Compare & pull request"
# 2. 选择 base: doobidoo/mcp-memory-service:main
# 3. 选择 compare: Hkesd/mcp-memory-service:plus-extension
# 4. 填写 PR 描述
# 5. 提交 PR
```

**PR 标题建议：**
```
feat: Add Plus Extension storage backends (ChromaDB, DashVector, Hybrid Plus)
```

**PR 描述建议：**
```markdown
## Summary
Add three new storage backends through minimal-invasive plus_extension module.

## New Features
- ChromaDB backend (local vector database)
- DashVector backend (Alibaba Cloud vector search)
- Hybrid Plus backend (ChromaDB + DashVector sync)

## Implementation
- Only 11 lines added to factory.py (minimal invasive)
- All extension code isolated in storage/plus_extension/
- Auto-fallback to SQLite-vec for high availability

## Documentation
- Chinese: PLUS_EXTENSION_README.md
- English: src/.../plus_extension/README.md
- Quick Start: QUICK_START_PLUS.md

## Testing
- ✅ Syntax validation passed
- ⏳ Integration tests pending (requires actual backends)
```

### 选项 2: 保持独立分支

如果你只想自己使用：

```bash
# 定期同步上游更新即可
git checkout main
git pull upstream main
git checkout plus-extension
git rebase main
git push origin plus-extension --force-with-lease
```

## 🧪 推送后测试

### 克隆测试（推荐）

```bash
# 在另一个目录克隆并测试
cd /tmp
git clone git@github.com:Hkesd/mcp-memory-service.git test-plus-extension
cd test-plus-extension
git checkout plus-extension

# 验证文件存在
ls -la PLUS_EXTENSION_README.md
ls -la src/mcp_memory_service/storage/plus_extension/

# 运行语法检查
python3 -m py_compile src/mcp_memory_service/storage/plus_extension/*.py

# 清理
cd /tmp && rm -rf test-plus-extension
```

### 功能测试（需要依赖）

```bash
# 安装依赖
pip install chromadb dashvector sentence-transformers

# 测试 ChromaDB 后端（需要启动 ChromaDB 服务）
export MCP_MEMORY_STORAGE_BACKEND=chromadb
uv run memory server

# 测试 DashVector 后端（需要凭证）
export MCP_MEMORY_STORAGE_BACKEND=dashvector
export DASHVECTOR_API_KEY=your-key
export DASHVECTOR_ENDPOINT=your-endpoint
uv run memory server
```

## 📝 推送检查清单

推送前请确认：

- [x] 所有文件已提交 (`git status` 显示干净)
- [x] 提交信息清晰有意义
- [x] 语法验证通过
- [x] 文档完整（中英双语）
- [x] 配置示例正确
- [x] 远程仓库地址正确

推送后请验证：

- [ ] GitHub 上能看到 plus-extension 分支
- [ ] 所有文件都已推送
- [ ] 提交历史正确
- [ ] 可以克隆并运行

## ⚠️  注意事项

1. **不要推送到 upstream**
   ```bash
   # ❌ 错误
   git push upstream plus-extension

   # ✅ 正确
   git push origin plus-extension
   ```

2. **使用 --force-with-lease 而不是 --force**
   ```bash
   # ❌ 危险
   git push origin plus-extension --force

   # ✅ 安全
   git push origin plus-extension --force-with-lease
   ```

3. **推送前检查当前分支**
   ```bash
   git branch  # 确保在 plus-extension 分支
   ```

## 🆘 常见问题

### Q: 推送失败 "Permission denied"
```bash
# 检查 SSH 密钥
ssh -T git@github.com

# 如果失败，重新配置 SSH 或使用 HTTPS
git remote set-url origin https://github.com/Hkesd/mcp-memory-service.git
```

### Q: 推送被拒绝 "non-fast-forward"
```bash
# 拉取远程更新
git pull origin plus-extension --rebase

# 或强制推送（谨慎）
git push origin plus-extension --force-with-lease
```

### Q: 如何撤销推送
```bash
# 1. 重置到上一个提交
git reset --hard HEAD~1

# 2. 强制推送
git push origin plus-extension --force-with-lease

# 注意：这会删除远程提交，谨慎操作！
```

## 📞 需要帮助？

- 📖 Git 文档: https://git-scm.com/doc
- 💬 GitHub 社区: https://github.community/
- 🐛 问题反馈: 在 GitHub 仓库创建 Issue

---

**准备好了吗？执行推送：**

```bash
git push origin plus-extension
```

🎉 推送成功后，你的 Plus Extension 就可以被全世界使用了！
