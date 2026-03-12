# Karamba - Personal Research Assistant Framework

A reusable, production-ready AI agent framework for document understanding and research assistance. Built with FastAPI, React, and local/cloud LLM support.

## 🎯 Features

- **Multi-Phase Agent Workflow**: Planning → Retrieval → Reasoning → Generation
- **Document Understanding**: PDF, DOCX, CSV, Excel support
- **Vector Search (RAG)**: Semantic search with ChromaDB + Sentence Transformers
- **LLM Abstraction**: Works with Ollama (local) or Claude/GPT (cloud)
- **Interactive UI**: React + TypeScript with real-time phase visualization
- **Verification System**: Rule-based validation at each phase
- **Testing Infrastructure**: Unit tests + LLM-as-judge evaluation
- **VS Code Integration**: Launch configs, debugging support

## 📁 Project Structure

```
karamba/
├── backend/          # FastAPI backend
│   ├── src/
│   │   ├── karamba/  # Core framework
│   │   │   ├── core/        # Agent, phase engine
│   │   │   ├── llm/         # LLM clients
│   │   │   ├── document/    # Processing, RAG
│   │   │   └── verification/
│   │   └── api/      # FastAPI routes
│   ├── tests/        # Unit & integration tests
│   └── config/       # Phase & prompt configs
├── frontend/         # React frontend
│   └── src/
│       ├── components/
│       ├── services/
│       └── hooks/
├── docker-compose.yml
└── .vscode/         # VS Code configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended)
- Ollama (for local LLM)

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone <your-repo>
cd karamba

# Install Ollama and pull model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
cd src
uvicorn api.main:app --reload
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## 🎮 VS Code Setup

1. Open project in VS Code
2. Install recommended extensions:
   - Python
   - Pylance
   - ESLint
   - Prettier

3. Use built-in launch configurations:
   - **Full Stack**: Start backend + frontend together
   - **Backend: FastAPI**: Start backend with debugging
   - **Backend: Tests**: Run pytest with coverage
   - **Frontend: Dev Server**: Start React dev server

Press `F5` and select "Full Stack" to run everything.

## 📖 Usage

### 1. Upload Documents

- Click "Documents" tab
- Drag & drop or select files (PDF, DOCX, CSV, XLSX)
- Documents are automatically processed and indexed

### 2. Ask Questions

- Click "Chat" tab
- Type your question
- Watch the agent work through phases:
  - **Planning**: Break down question
  - **Retrieval**: Find relevant information
  - **Reasoning**: Analyze and synthesize
- Get answer with citations

### Example Queries

```
"What are the key findings in the Q3 report?"
"Compare revenue across all uploaded documents"
"Summarize the main arguments in the research papers"
"Find all mentions of budget constraints"
```

## 🔧 Configuration

### LLM Configuration

**Use Local Ollama (default):**
```python
# backend/src/api/main.py
llm_config = LLMConfig(
    provider="ollama",
    model="llama3.2:3b",
    temperature=0.7
)
```

**Use Claude:**
```python
llm_config = LLMConfig(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    api_key="your-api-key"
)
```

### Environment Variables

Create `.env` file in backend/:
```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=your-key-here

# Application
VECTOR_STORE_PATH=./data/vector_store
UPLOAD_DIR=./data/uploads
```

### Phase Configuration

Edit `backend/config/phases.yaml` to customize workflow:

```yaml
phases:
  - name: "planning"
    type: "planning"
    prompt_file: "planning.txt"
    verification:
      - "not_empty"
      - "min_length"
    config:
      min_length: 100
      max_tokens: 1000
```

## 🧪 Testing

### Run Tests

```bash
cd backend

# All tests
pytest

# With coverage
pytest --cov=karamba --cov-report=html

# Specific test file
pytest tests/unit/test_agent.py -v
```

### LLM-as-Judge Evaluation

```python
# tests/evaluation/test_llm_judge.py
def test_answer_quality():
    response = agent.answer_question(request)
    
    judge = LLMJudge("claude-sonnet-4-5")
    score = judge.evaluate(
        answer=response.answer,
        criteria=["accuracy", "completeness", "citations"]
    )
    
    assert score.accuracy > 0.8
```

## 🔄 Extending Karamba

### Add New Document Type

```python
# backend/src/karamba/document/processor.py
@staticmethod
async def _process_custom(filename: str, path: Path) -> ProcessedDocument:
    # Your processing logic
    content = extract_custom_format(path)
    
    return ProcessedDocument(
        filename=filename,
        content=content,
        doc_type="custom"
    )
```

### Add New Phase

```python
# backend/src/karamba/core/agent.py
custom_phase = Phase(
    name="custom_analysis",
    phase_type=PhaseType.REASONING,
    prompt_template="Analyze this data: {context}",
    verification_rules=["not_empty"]
)

engine.add_phase(custom_phase)
```

### Create New Use Case

```python
# Example: Legal Assistant
from karamba.core.agent import KarambaAgent
from karamba.llm import LLMConfig

# Configure for legal domain
llm_config = LLMConfig(provider="anthropic", model="claude-opus-4")
agent = KarambaAgent(llm_config, config_path="config/legal_phases.yaml")

# Use same framework, different prompts!
```

## 📊 API Reference

### REST Endpoints

```
POST   /api/v1/agent/query          # Query agent
GET    /api/v1/agent/stats          # Get statistics

POST   /api/v1/documents/upload     # Upload document
GET    /api/v1/documents/list       # List documents
DELETE /api/v1/documents/{id}       # Delete document

WS     /ws/agent/{session_id}       # WebSocket streaming
```

### WebSocket Protocol

```typescript
// Send query
ws.send(JSON.stringify({
  type: 'query',
  query: 'Your question',
  document_ids: []
}));

// Receive phase results
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'phase_result') {
    console.log(data.phase, data.output);
  }
};
```

## 🛠️ Troubleshooting

### Ollama Connection Issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama  # Linux
# or restart Ollama app on Mac/Windows
```

### Vector Store Issues

```bash
# Clear and rebuild vector store
rm -rf backend/data/vector_store
# Re-upload documents
```

### Frontend Not Connecting

```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/src/api/main.py
```

## 📈 Performance

- **Local LLM (llama3.2:3b)**: ~2-5 seconds per query
- **Claude Sonnet**: ~1-3 seconds per query
- **Document Processing**: ~1-2 seconds per PDF page
- **Vector Search**: <100ms for most queries

## 🎯 Roadmap

- [ ] Multi-modal support (images, audio)
- [ ] Conversation memory across sessions
- [ ] Advanced verification rules
- [ ] Collaborative features
- [ ] Export to PDF/Word
- [ ] Mobile app

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md

## 📧 Support

- GitHub Issues: <your-repo>/issues
- Documentation: <your-docs-link>
- Email: support@example.com

---

**Built with ❤️ for reusable AI agents**