#!/bin/bash

echo "🔧 Fixing __init__.py files..."

# karamba/document/__init__.py
cat > src/karamba/document/__init__.py << 'EOF'
"""Document processing module for Karamba."""
from .processor import DocumentProcessor, ProcessedDocument
from .chunker import TextChunker, DocumentChunk
from .embeddings import EmbeddingGenerator
from .retriever import VectorRetriever, RetrievedChunk

__all__ = [
    "DocumentProcessor",
    "ProcessedDocument",
    "TextChunker",
    "DocumentChunk",
    "EmbeddingGenerator",
    "VectorRetriever",
    "RetrievedChunk",
]
EOF

# karamba/core/__init__.py
cat > src/karamba/core/__init__.py << 'EOF'
"""Core agent module for Karamba."""
from .agent import KarambaAgent
from .phase_engine import PhaseEngine, Phase
from .models import (
    PhaseStatus,
    PhaseType,
    VerificationResult,
    PhaseResult,
    AgentRequest,
    AgentResponse,
    ResearchPlan,
)

__all__ = [
    "KarambaAgent",
    "PhaseEngine",
    "Phase",
    "PhaseStatus",
    "PhaseType",
    "VerificationResult",
    "PhaseResult",
    "AgentRequest",
    "AgentResponse",
    "ResearchPlan",
]
EOF

# karamba/verification/__init__.py
cat > src/karamba/verification/__init__.py << 'EOF'
"""Verification module for Karamba."""
__all__ = []
EOF

# karamba/__init__.py
cat > src/karamba/__init__.py << 'EOF'
"""Karamba - Personal Research Assistant Framework."""
__version__ = "0.1.0"

from .core import KarambaAgent
from .llm import create_llm, LLMConfig

__all__ = [
    "KarambaAgent",
    "create_llm",
    "LLMConfig",
]
EOF

# api/__init__.py
cat > src/api/__init__.py << 'EOF'
"""API module for Karamba."""
__all__ = []
EOF

# api/routes/__init__.py
cat > src/api/routes/__init__.py << 'EOF'
"""API routes for Karamba."""
__all__ = []
EOF

echo "✅ All __init__.py files created!"