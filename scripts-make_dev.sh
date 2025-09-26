#!/bin/bash
# Development server script with auto-reload

set -e

echo "🚀 Starting bot-swarm memory system (Stage 1)"
echo "Server will run at http://localhost:8000"
echo "Swagger docs: http://localhost:8000/docs (if DEBUG=true)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review settings if needed."
    echo ""
fi

# Check if data directory will be created
source .env 2>/dev/null || true
DB_PATH=${DB_PATH:-"./data/memory.db"}
DB_DIR=$(dirname "$DB_PATH")

if [ ! -d "$DB_DIR" ]; then
    echo "📁 Database directory '$DB_DIR' will be created automatically"
    echo ""
fi

# Start uvicorn with auto-reload
echo "🔄 Starting with auto-reload (files: src/)"
exec uvicorn src.api.main:app --reload --port 8000 --reload-dir src