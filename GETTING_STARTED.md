# Getting Started with Karamba

This guide will walk you through setting up and running Karamba for the first time.

## Complete File Structure to Create

Here's every file you need to create. I've provided the core ones in artifacts above, but here's the complete checklist:

### Backend Files ✅ (Already Provided)

```
backend/
├── src/
│   ├── karamba/
│   │   ├── __init__.py (empty file)
│   │   ├── core/
│   │   │   ├── __init__.py (empty)
│   │   │   ├── agent.py ✅
│   │   │   ├── phase_engine.py ✅
│   │   │   ├── models.py ✅
│   │   │   ├── memory.py (create empty for now)
│   │   │   └── config.py (create empty for now)
│   │   ├── llm/
│   │   │   ├── __init__.py ✅
│   │   │   ├── base.py ✅
│   │   │   ├── ollama_client.py ✅
│   │   │   └── anthropic_client.py ✅
│   │   ├── document/
│   │   │   ├── __init__.py (empty)
│   │   │   ├── processor.py ✅
│   │   │   ├── chunker.py ✅
│   │   │   ├── embeddings.py ✅
│   │   │   └── retriever.py ✅
│   │   └── verification/
│   │       ├── __init__.py (empty)
│   │       ├── rule_engine.py (create empty for now)
│   │       └── validators.py (create empty for now)
│   └── api/
│       ├── __init__.py (empty)
│       ├── main.py ✅
│       ├── routes/
│       │   ├── __init__.py (empty)
│       │   ├── agent.py ✅
│       │   ├── documents.py ✅
│       │   └── websocket.py ✅
│       └── models/ (can skip for now)
├── config/
│   └── phases.yaml (see below)
├── tests/ (create later)
├── requirements.txt ✅
├── pyproject.toml ✅
└── Dockerfile ✅
```

### Frontend Files (Need to Create)

The artifacts above provide the main structure. Here are the remaining files you need:

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatContainer.tsx ✅
│   │   │   ├── MessageList.tsx (see below)
│   │   │   ├── MessageInput.tsx (see below)
│   │   │   └── Message.tsx (see below)
│   │   ├── Documents/
│   │   │   ├── DocumentUpload.tsx (see below)
│   │   │   ├── DocumentLibrary.tsx (see below)
│   │   │   └── DocumentViewer.tsx (can skip for MVP)
│   │   └── Agent/
│   │       ├── PhaseIndicator.tsx (see below)
│   │       ├── RetrievedChunks.tsx (can skip)
│   │       └── CitationLink.tsx (can skip)
│   ├── services/
│   │   └── api.ts ✅
│   ├── hooks/ (can skip for MVP)
│   ├── types/ (can skip, using inline types)
│   ├── App.tsx ✅
│   ├── main.tsx (see below)
│   └── index.css (see below)
├── public/ (empty for now)
├── index.html (see below)
├── package.json ✅
├── tsconfig.json (see below)
├── vite.config.ts (see below)
├── tailwind.config.js (see below)
├── postcss.config.js (see below)
└── Dockerfile (optional for now)
```

## Step-by-Step Setup

### Step 1: Create Project Structure

```bash
# Create main directory
mkdir karamba
cd karamba

# Create backend structure
mkdir -p backend/src/karamba/{core,llm,document,verification}
mkdir -p backend/src/api/routes
mkdir -p backend/config
mkdir -p backend/tests
mkdir -p backend/data/{uploads,vector_store}

# Create frontend structure
mkdir -p frontend/src/{components/{Chat,Documents,Agent},services,hooks,types}
mkdir -p frontend/public

# Create other directories
mkdir -p .vscode
```

### Step 2: Copy Backend Files

Copy the backend files from the artifacts I provided above. Here are the empty `__init__.py` files:

```python
# Create empty __init__.py files
touch backend/src/karamba/__init__.py
touch backend/src/karamba/core/__init__.py
touch backend/src/karamba/llm/__init__.py
touch backend/src/karamba/document/__init__.py
touch backend/src/karamba/verification/__init__.py
touch backend/src/api/__init__.py
touch backend/src/api/routes/__init__.py
```

### Step 3: Essential Missing Files

**backend/config/phases.yaml:**
```yaml
phases:
  - name: "planning"
    type: "planning"
    prompt_file: "planning.txt"
    verification:
      - "not_empty"
    config:
      max_tokens: 1000

  - name: "retrieval"
    type: "retrieval"
    prompt_file: "retrieval.txt"
    verification:
      - "not_empty"
    config:
      max_tokens: 500

  - name: "reasoning"
    type: "reasoning"
    prompt_file: "reasoning.txt"
    verification:
      - "not_empty"
      - "min_length"
    config:
      min_length: 100
      max_tokens: 2000
```

**frontend/src/main.tsx:**
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**frontend/src/index.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}
```

**frontend/index.html:**
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Karamba - Personal Research Assistant</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**frontend/tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**frontend/vite.config.ts:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  }
})
```

**frontend/tailwind.config.js:**
```javascript
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
```

**frontend/postcss.config.js:**
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### Step 4: Minimal Frontend Components

**frontend/src/components/Chat/MessageList.tsx:**
```typescript
import { Message } from './ChatContainer';
import ReactMarkdown from 'react-markdown';

interface Props {
  messages: Message[];
}

export default function MessageList({ messages }: Props) {
  return (
    <div className="flex-1 overflow-auto p-6 space-y-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-3xl rounded-lg p-4 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200'
            }`}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
            
            {message.citations && message.citations.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-sm font-semibold mb-2">Sources:</p>
                {message.citations.map((citation, idx) => (
                  <div key={idx} className="text-sm text-gray-600 mb-1">
                    • {citation.document_id} (score: {citation.score.toFixed(2)})
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**frontend/src/components/Chat/MessageInput.tsx:**
```typescript
import { useState } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex space-x-2">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question about your documents..."
        disabled={disabled}
        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
      >
        <Send size={20} />
        <span>Send</span>
      </button>
    </form>
  );
}
```

**frontend/src/components/Agent/PhaseIndicator.tsx:**
```typescript
import { CheckCircle, Circle, Loader2 } from 'lucide-react';

interface Phase {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

interface Props {
  phases: Phase[];
}

export default function PhaseIndicator({ phases }: Props) {
  return (
    <div className="flex items-center space-x-4">
      {phases.map((phase, idx) => (
        <div key={phase.name} className="flex items-center">
          <div className="flex items-center space-x-2">
            {phase.status === 'completed' && <CheckCircle className="text-green-500" size={20} />}
            {phase.status === 'running' && <Loader2 className="text-blue-500 animate-spin" size={20} />}
            {phase.status === 'pending' && <Circle className="text-gray-300" size={20} />}
            <span className={`capitalize ${phase.status === 'running' ? 'font-semibold' : ''}`}>
              {phase.name}
            </span>
          </div>
          {idx < phases.length - 1 && <div className="w-8 h-0.5 bg-gray-300 mx-2" />}
        </div>
      ))}
    </div>
  );
}
```

**frontend/src/components/Documents/DocumentUpload.tsx:**
```typescript
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadDocument } from '../../services/api';
import { Upload } from 'lucide-react';

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setFile(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Upload Document</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <Upload className="mx-auto text-gray-400 mb-2" size={48} />
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            accept=".pdf,.docx,.csv,.xlsx,.txt,.md"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <p className="text-sm text-gray-500 mt-2">
            Supported: PDF, DOCX, CSV, XLSX, TXT, MD
          </p>
        </div>
        <button
          type="submit"
          disabled={!file || uploadMutation.isPending}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
}
```

**frontend/src/components/Documents/DocumentLibrary.tsx:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { listDocuments } from '../../services/api';
import { FileText } from 'lucide-react';

export default function DocumentLibrary() {
  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Document Library</h2>
      {data?.documents && data.documents.length > 0 ? (
        <div className="space-y-2">
          {data.documents.map((doc) => (
            <div key={doc.filename} className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg">
              <FileText size={20} className="text-gray-400" />
              <span className="flex-1">{doc.filename}</span>
              <span className="text-sm text-gray-500">
                {(doc.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500">No documents uploaded yet</p>
      )}
    </div>
  );
}
```

### Step 5: Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

### Step 6: Start Services

**Option A: Docker Compose**
```bash
docker-compose up -d
```

**Option B: Manual**

Terminal 1 (Backend):
```bash
cd backend
source venv/bin/activate
cd src
uvicorn api.main:app --reload
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### Step 7: Verify Everything Works

1. Open http://localhost:5173
2. You should see the Karamba interface
3. Go to Documents tab and upload a PDF
4. Go to Chat tab and ask a question
5. Watch the agent process your request!

## Troubleshooting

**Issue: Ollama not found**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.2:3b

# Verify
ollama list
```

**Issue: Python dependencies fail**
```bash
# Upgrade pip
pip install --upgrade pip

# Install build tools
# Ubuntu/Debian:
sudo apt-get install python3-dev build-essential

# macOS:
xcode-select --install
```

**Issue: Frontend won't start**
```bash
# Clear node_modules
rm -rf frontend/node_modules
rm frontend/package-lock.json

# Reinstall
cd frontend
npm install
```

## Next Steps

Once you have the basic system running:

1. **Customize Phases**: Edit `backend/config/phases.yaml`
2. **Add Tests**: Create tests in `backend/tests/`
3. **Try Different LLMs**: Switch between Ollama and Claude
4. **Extend for Your Use Case**: Modify prompts and add domain-specific logic

Enjoy building with Karamba! 🎉