#!/bin/bash

echo "🚀 Setting up Karamba - Personal Research Assistant"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11+ is required but not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js 18+ is required but not installed${NC}"
    echo "Install from: https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js found: $NODE_VERSION${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is required but not installed${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm found: v$NPM_VERSION${NC}"

# Check pyenv (recommended)
if command -v pyenv &> /dev/null; then
    echo -e "${GREEN}✅ pyenv found${NC}"
    USING_PYENV=true
else
    echo -e "${YELLOW}⚠️  pyenv not found (recommended for Python version management)${NC}"
    USING_PYENV=false
fi

# Check Ollama (optional)
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama found${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama not found (optional - for local LLM)${NC}"
    echo "   Install from: https://ollama.ai"
fi

# ====================================
# BACKEND SETUP
# ====================================

echo ""
echo "🔧 Setting up Backend..."
cd backend || exit 1

# Set Python version with pyenv if available
if [ "$USING_PYENV" = true ]; then
    if ! pyenv versions | grep -q "3.11.10"; then
        echo "📦 Installing Python 3.11.10 with pyenv..."
        pyenv install 3.11.10
    fi
    pyenv local 3.11.10
    echo -e "${GREEN}✅ Set Python 3.11.10 for this project${NC}"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Created Python virtual environment${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Verify Python version
VENV_PYTHON_VERSION=$(python --version)
echo -e "${GREEN}✅ Using: $VENV_PYTHON_VERSION${NC}"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip -q

# Install Python dependencies
echo "📦 Installing Python dependencies..."
echo "   (This may take a few minutes...)"
pip install -r requirements.txt -q

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install backend dependencies${NC}"
    exit 1
fi

# Create data directories
mkdir -p data/uploads data/vector_store
echo -e "${GREEN}✅ Created data directories${NC}"

# Create .env file
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=

# Application
VECTOR_STORE_PATH=./data/vector_store
UPLOAD_DIR=./data/uploads
EOF
    echo -e "${GREEN}✅ Created backend .env file${NC}"
else
    echo -e "${GREEN}✅ Backend .env file already exists${NC}"
fi

# Test critical imports
echo "🧪 Testing critical Python imports..."
python -c "import fastapi, pydantic, pandas, chromadb, sentence_transformers" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All critical packages can be imported${NC}"
else
    echo -e "${RED}❌ Some packages failed to import${NC}"
    echo "Run: python -c 'import fastapi, pydantic, pandas, chromadb, sentence_transformers'"
fi

cd ..

# ====================================
# FRONTEND SETUP
# ====================================

echo ""
echo "🎨 Setting up Frontend..."
cd frontend || exit 1

# Install Node dependencies
echo "📦 Installing Node dependencies..."
echo "   (This may take a few minutes...)"
npm install

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
    exit 1
fi

# Install Tailwind CSS
echo "📦 Installing Tailwind CSS..."
npm install -D tailwindcss postcss autoprefixer

# Initialize Tailwind if config doesn't exist
if [ ! -f "tailwind.config.js" ]; then
    echo "⚙️  Initializing Tailwind CSS..."
    npx tailwindcss init -p
    echo -e "${GREEN}✅ Tailwind CSS initialized${NC}"
else
    echo -e "${GREEN}✅ Tailwind config already exists${NC}"
fi

# Ensure tailwind.config.js has correct content
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF
echo -e "${GREEN}✅ Updated tailwind.config.js${NC}"

# Ensure postcss.config.js exists
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF
echo -e "${GREEN}✅ Updated postcss.config.js${NC}"

# Create .env file for frontend
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
    echo -e "${GREEN}✅ Created frontend .env file${NC}"
else
    echo -e "${GREEN}✅ Frontend .env file already exists${NC}"
fi

cd ..

# ====================================
# FINAL INSTRUCTIONS
# ====================================

echo ""
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "=================================================="
echo "📚 Next Steps:"
echo "=================================================="
echo ""

if ! command -v ollama &> /dev/null; then
    echo "1️⃣  Install Ollama (for local LLM):"
    echo "   curl -fsSL https://ollama.ai/install.sh | sh"
    echo "   ollama pull llama3.2:3b"
    echo ""
fi

echo "2️⃣  Start Backend (Terminal 1):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   cd src"
echo "   uvicorn api.main:app --reload"
echo ""

echo "3️⃣  Start Frontend (Terminal 2):"
echo "   cd frontend"
echo "   npm run dev"
echo ""

echo "4️⃣  Open your browser:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000/docs"
echo ""

echo "=================================================="
echo ""
echo -e "${GREEN}📖 See README.md for detailed documentation${NC}"
echo -e "${GREEN}🐛 Run into issues? Check GETTING_STARTED.md${NC}"
echo ""
echo "Happy researching! 🎉"