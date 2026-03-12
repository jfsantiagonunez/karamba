#!/usr/bin/env python3
"""Test Python 3.13 compatibility for Karamba."""
import sys

print(f"Python version: {sys.version}")

try:
    import fastapi
    print("✅ FastAPI")
except ImportError as e:
    print(f"❌ FastAPI: {e}")

try:
    import pydantic
    print("✅ Pydantic")
except ImportError as e:
    print(f"❌ Pydantic: {e}")

try:
    import chromadb
    print("✅ ChromaDB")
except ImportError as e:
    print(f"❌ ChromaDB: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("✅ Sentence Transformers")
except ImportError as e:
    print(f"❌ Sentence Transformers: {e}")

try:
    import pypdfium2
    print("✅ PyPDFium2")
except ImportError as e:
    print(f"❌ PyPDFium2: {e}")

print("\n✨ If all packages show ✅, you're ready to use Python 3.13!")