#!/bin/bash

# UFE Research Writer - Quick Start Script

set -e

echo "======================================"
echo "UFE Research Writer - Quick Start"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please edit it with your API keys:"
    echo "   - GOOGLE_API_KEY"
    echo "   - TAVILY_API_KEY"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/uploads
mkdir -p data/outputs
echo "✅ Data directories created"
echo ""

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.10 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Using Python: $(which python)"
echo ""

# Check Python dependencies
echo "📦 Checking Python dependencies..."
if ! python -c "import fastapi" > /dev/null 2>&1; then
    echo "📥 Installing Python dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    echo "✅ Dependencies installed"
else
    echo "✅ Python dependencies already installed"
fi
echo ""

# Initialize database
echo "🗄️  Initializing database..."
python -c "from src.database import Database; db = Database(); print('✅ Database initialized at', db.db_path)"
echo ""

# Check if frontend should be set up
read -p "Do you want to set up the frontend? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "frontend" ]; then
        cd frontend
        echo "📦 Installing frontend dependencies..."
        npm install
        echo "✅ Frontend dependencies installed"
        cd ..
    else
        echo "❌ Frontend directory not found"
    fi
fi
echo ""

# Ask how to run
echo "How would you like to run the application?"
echo "1) Backend only (API server)"
echo "2) Backend + Frontend (separate terminals)"
echo "3) Docker Compose (all services)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting API server..."
        echo "📍 Backend will be at: http://localhost:8000"
        echo "📍 API docs at: http://localhost:8000/docs"
        echo ""
        python run_api.py
        ;;
    2)
        echo ""
        echo "🚀 Starting services in separate terminals..."
        echo ""
        echo "Terminal 1: Backend API"
        echo "Run: source .venv/bin/activate && python run_api.py"
        echo ""
        echo "Terminal 2: Frontend Dev Server"
        echo "Run: cd frontend && npm run dev"
        echo ""
        echo "📍 Backend: http://localhost:8000"
        echo "📍 Frontend: http://localhost:5173"
        echo ""
        read -p "Press Enter to start backend in this terminal..."
        python run_api.py
        ;;
    3)
        echo ""
        echo "🐳 Starting with Docker Compose..."
        echo "📍 Backend: http://localhost:8000"
        echo "📍 Frontend: http://localhost:5173"
        echo ""
        docker-compose up
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
