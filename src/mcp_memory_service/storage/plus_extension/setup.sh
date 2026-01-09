#!/bin/bash
# Quick setup script for Plus Extension backends

set -e

echo "🚀 MCP Memory Service Plus Extension Setup"
echo "==========================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install dependencies
install_dependencies() {
    echo "📦 Installing dependencies..."

    if command_exists pip; then
        pip install chromadb dashvector sentence-transformers
    elif command_exists pip3; then
        pip3 install chromadb dashvector sentence-transformers
    else
        echo "❌ Error: pip not found. Please install pip first."
        exit 1
    fi

    echo "✅ Dependencies installed"
}

# Function to setup ChromaDB
setup_chromadb() {
    echo ""
    echo "🔧 Setting up ChromaDB backend..."

    read -p "ChromaDB host (default: localhost): " CHROMA_HOST
    CHROMA_HOST=${CHROMA_HOST:-localhost}

    read -p "ChromaDB port (default: 8000): " CHROMA_PORT
    CHROMA_PORT=${CHROMA_PORT:-8000}

    echo "export MCP_MEMORY_STORAGE_BACKEND=chromadb" >> .env
    echo "export CHROMADB_HOST=$CHROMA_HOST" >> .env
    echo "export CHROMADB_PORT=$CHROMA_PORT" >> .env
    echo "export CHROMADB_COLLECTION=mcp_memory" >> .env

    echo "✅ ChromaDB configured"
    echo ""
    echo "To start ChromaDB server, run:"
    echo "  chroma run --host $CHROMA_HOST --port $CHROMA_PORT"
}

# Function to setup DashVector
setup_dashvector() {
    echo ""
    echo "🔧 Setting up DashVector backend..."

    read -p "DashVector API Key: " DASH_API_KEY
    read -p "DashVector Endpoint: " DASH_ENDPOINT

    echo "export MCP_MEMORY_STORAGE_BACKEND=dashvector" >> .env
    echo "export DASHVECTOR_API_KEY=$DASH_API_KEY" >> .env
    echo "export DASHVECTOR_ENDPOINT=$DASH_ENDPOINT" >> .env
    echo "export DASHVECTOR_COLLECTION=mcp_memory" >> .env

    echo "✅ DashVector configured"
}

# Function to setup Hybrid Plus
setup_hybrid_plus() {
    echo ""
    echo "🔧 Setting up Hybrid Plus backend..."

    read -p "ChromaDB host (default: localhost): " CHROMA_HOST
    CHROMA_HOST=${CHROMA_HOST:-localhost}

    read -p "ChromaDB port (default: 8000): " CHROMA_PORT
    CHROMA_PORT=${CHROMA_PORT:-8000}

    read -p "DashVector API Key: " DASH_API_KEY
    read -p "DashVector Endpoint: " DASH_ENDPOINT

    echo "export MCP_MEMORY_STORAGE_BACKEND=hybrid_plus" >> .env
    echo "export CHROMADB_HOST=$CHROMA_HOST" >> .env
    echo "export CHROMADB_PORT=$CHROMA_PORT" >> .env
    echo "export DASHVECTOR_API_KEY=$DASH_API_KEY" >> .env
    echo "export DASHVECTOR_ENDPOINT=$DASH_ENDPOINT" >> .env

    echo "✅ Hybrid Plus configured"
    echo ""
    echo "To start ChromaDB server, run:"
    echo "  chroma run --host $CHROMA_HOST --port $CHROMA_PORT"
}

# Main menu
echo "Select backend to configure:"
echo "1) ChromaDB (local vector database)"
echo "2) DashVector (Alibaba Cloud)"
echo "3) Hybrid Plus (ChromaDB + DashVector)"
echo "4) Install dependencies only"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        install_dependencies
        setup_chromadb
        ;;
    2)
        install_dependencies
        setup_dashvector
        ;;
    3)
        install_dependencies
        setup_hybrid_plus
        ;;
    4)
        install_dependencies
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Source the environment: source .env"
echo "2. Start MCP Memory Service: uv run memory server"
echo ""
echo "For more information, see:"
echo "  src/mcp_memory_service/plus_extension/README.md"
echo "========================================="
