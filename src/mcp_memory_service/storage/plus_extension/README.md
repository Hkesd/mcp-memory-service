# Plus Extension Storage Backends

This directory contains additional storage backends for MCP Memory Service:

## Available Backends

### 1. ChromaDB Backend
**Local vector database with persistent storage**

```bash
# Environment Configuration
export MCP_MEMORY_STORAGE_BACKEND=chromadb
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export CHROMADB_COLLECTION=mcp_memory

# Install ChromaDB
pip install chromadb

# Start ChromaDB server
chroma run --host localhost --port 8000
```

**Features:**
- ✅ Fast local vector search
- ✅ Persistent storage
- ✅ Automatic fallback to SQLite-vec
- ✅ Metadata filtering

### 2. DashVector Backend
**Alibaba Cloud vector search service**

```bash
# Environment Configuration
export MCP_MEMORY_STORAGE_BACKEND=dashvector
export DASHVECTOR_API_KEY=your-api-key
export DASHVECTOR_ENDPOINT=your-endpoint
export DASHVECTOR_COLLECTION=mcp_memory

# Install DashVector SDK
pip install dashvector
```

**Features:**
- ✅ Cloud-based vector search
- ✅ Scalable and managed
- ✅ Automatic fallback to SQLite-vec
- ✅ Cross-device sync

### 3. Hybrid Plus Backend
**Combined ChromaDB (local) + DashVector (cloud)**

```bash
# Environment Configuration
export MCP_MEMORY_STORAGE_BACKEND=hybrid_plus
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export DASHVECTOR_API_KEY=your-api-key
export DASHVECTOR_ENDPOINT=your-endpoint

# Install both
pip install chromadb dashvector
```

**Features:**
- ✅ Primary: ChromaDB (fast local reads)
- ✅ Backup: DashVector (cloud sync)
- ✅ Background sync every 5 minutes
- ✅ Intelligent routing
- ✅ Triple fallback: ChromaDB → DashVector → SQLite-vec

## Installation

### Quick Install
```bash
# Install all plus extension dependencies
pip install chromadb dashvector sentence-transformers

# Or install individually
pip install chromadb              # For ChromaDB backend
pip install dashvector            # For DashVector backend
pip install sentence-transformers # For embeddings (required by DashVector)
```

### Verify Installation
```bash
# Test ChromaDB
python -c "import chromadb; print('ChromaDB OK')"

# Test DashVector
python -c "import dashvector; print('DashVector OK')"
```

## Usage Examples

### ChromaDB Backend
```bash
# Start ChromaDB server
chroma run --host localhost --port 8000

# Configure MCP Memory Service
export MCP_MEMORY_STORAGE_BACKEND=chromadb
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000

# Start MCP Memory Service
uv run memory server
```

### DashVector Backend
```bash
# Configure with your DashVector credentials
export MCP_MEMORY_STORAGE_BACKEND=dashvector
export DASHVECTOR_API_KEY=your-api-key
export DASHVECTOR_ENDPOINT=https://your-endpoint.dashvector.cn-hangzhou.aliyuncs.com

# Start MCP Memory Service
uv run memory server
```

### Hybrid Plus Backend
```bash
# Start ChromaDB server
chroma run --host localhost --port 8000

# Configure both backends
export MCP_MEMORY_STORAGE_BACKEND=hybrid_plus
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export DASHVECTOR_API_KEY=your-api-key
export DASHVECTOR_ENDPOINT=https://your-endpoint.dashvector.cn-hangzhou.aliyuncs.com

# Start MCP Memory Service
uv run memory server
```

## Architecture

### ChromaDB Backend
```
┌─────────────────┐
│  MCP Memory     │
│  Service        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  ChromaDB       │─────▶│  SQLite-vec  │
│  (Primary)      │      │  (Fallback)  │
└─────────────────┘      └──────────────┘
```

### DashVector Backend
```
┌─────────────────┐
│  MCP Memory     │
│  Service        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  DashVector     │─────▶│  SQLite-vec  │
│  (Cloud)        │      │  (Fallback)  │
└─────────────────┘      └──────────────┘
```

### Hybrid Plus Backend
```
┌─────────────────┐
│  MCP Memory     │
│  Service        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐      ┌──────────────┐
│  ChromaDB       │─────▶│  DashVector  │─────▶│  SQLite-vec  │
│  (Primary)      │      │  (Sync)      │      │  (Fallback)  │
└─────────────────┘      └──────────────┘      └──────────────┘
         │                        ▲
         └────────────────────────┘
              Background Sync (5min)
```

## Configuration Reference

### ChromaDB Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMADB_HOST` | `localhost` | ChromaDB server host |
| `CHROMADB_PORT` | `8000` | ChromaDB server port |
| `CHROMADB_COLLECTION` | `mcp_memory` | Collection name |

### DashVector Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `DASHVECTOR_API_KEY` | ✅ Yes | DashVector API key |
| `DASHVECTOR_ENDPOINT` | ✅ Yes | DashVector service endpoint |
| `DASHVECTOR_COLLECTION` | No | Collection name (default: `mcp_memory`) |

### Hybrid Plus Environment Variables
Combines all ChromaDB and DashVector variables above.

## Troubleshooting

### ChromaDB Connection Failed
```bash
# Check if ChromaDB server is running
curl http://localhost:8000/api/v1/heartbeat

# Start ChromaDB server
chroma run --host localhost --port 8000

# Check logs
tail -f ~/.chroma/chroma.log
```

### DashVector Authentication Failed
```bash
# Verify credentials
echo $DASHVECTOR_API_KEY
echo $DASHVECTOR_ENDPOINT

# Test connection
python -c "
import dashvector
client = dashvector.Client(api_key='$DASHVECTOR_API_KEY', endpoint='$DASHVECTOR_ENDPOINT')
print('Connection OK')
"
```

### Fallback to SQLite-vec
If you see "falling back to SQLite-vec" in logs:
- ✅ This is expected behavior when backends are unavailable
- ✅ Service continues to work with local SQLite-vec storage
- ⚠️  Check backend configuration and connectivity

## Performance Comparison

| Backend | Read Latency | Write Latency | Storage | Cost |
|---------|--------------|---------------|---------|------|
| ChromaDB | ~10ms | ~20ms | Local disk | Free |
| DashVector | ~50ms | ~100ms | Cloud | Pay-per-use |
| Hybrid Plus | ~10ms (read) | ~20ms (write) | Local + Cloud | Free + Pay-per-use |
| SQLite-vec | ~5ms | ~10ms | Local disk | Free |

## Development

### Adding New Backends
1. Create new backend class in `plus_extension/`
2. Inherit from `MemoryStorage` base class
3. Implement required methods: `initialize`, `store_memory`, `search_memories`, etc.
4. Update `__init__.py` factory functions
5. No changes needed to `storage/factory.py` (auto-detected)

### Testing
```bash
# Test ChromaDB backend
pytest tests/test_chromadb_backend.py

# Test DashVector backend
pytest tests/test_dashvector_backend.py

# Test Hybrid Plus backend
pytest tests/test_hybrid_plus_backend.py
```

## License

Same as MCP Memory Service (Apache 2.0)
