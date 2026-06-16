#!/bin/bash
# SwasthAI API - Production Server Startup (Linux/Raspberry Pi)
# Run with: chmod +x start_server.sh && ./start_server.sh

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         SwasthAI - Anemia Detection API                        ║"
echo "║         Production Server (Linux/Raspberry Pi)                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv .venv"
    exit 1
fi

source .venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"
echo ""

# Set environment variables
export FLASK_ENV=production
export FLASK_APP=wsgi.py
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# Start with Gunicorn (production-grade WSGI server)
echo "🚀 Starting SwasthAI API Server..."
echo "   Server: Gunicorn WSGI"
echo "   Host: 0.0.0.0"
echo "   Port: 5000"
echo "   Workers: 4"
echo "   URL: http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

# Run Gunicorn with 4 worker processes
gunicorn \
    --workers=4 \
    --bind=0.0.0.0:5000 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info \
    wsgi:app

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Server failed to start"
    exit 1
fi
