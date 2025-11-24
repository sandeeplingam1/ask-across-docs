#!/bin/bash

# Audit App - Setup Script
# This script helps you set up the backend environment

set -e

echo "🚀 Audit App - Backend Setup"
echo "=============================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit backend/.env and add your Azure OpenAI credentials!"
    echo ""
    echo "Required variables:"
    echo "  - AZURE_OPENAI_ENDPOINT"
    echo "  - AZURE_OPENAI_API_KEY"
    echo "  - AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    echo "  - AZURE_OPENAI_CHAT_DEPLOYMENT"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your Azure OpenAI credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python -m uvicorn app.main:app --reload"
echo ""
