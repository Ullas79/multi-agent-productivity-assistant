#!/bin/bash
echo "🚀 Starting FastAPI Backend in the background (Port 8000)..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

echo "🎨 Starting Streamlit UI (Port 8080)..."
streamlit run app.py --server.port ${PORT:-8080} --server.address 0.0.0.0
