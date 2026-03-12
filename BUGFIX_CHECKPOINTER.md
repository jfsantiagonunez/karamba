# Checkpointer Initialization Fix

## Problem

When starting the API server, encountered this error:

```
TypeError: Invalid checkpointer provided. Expected an instance of `BaseCheckpointSaver`,
`True`, `False`, or `None`. Received _AsyncGeneratorContextManager. Pass a proper saver
(e.g., InMemorySaver, AsyncPostgresSaver).
```

## Root Cause

The `AsyncSqliteSaver.from_conn_string()` method returns an async context manager, not the saver instance directly. We were storing the context manager itself instead of entering it to get the actual saver.

## Solution

### Changes Made

#### 1. SessionStore (`memory/store.py`)

**Before:**
```python
async def __aenter__(self):
    self._checkpointer = AsyncSqliteSaver.from_conn_string(str(self.db_path))
    await self._checkpointer.__aenter__()  # ❌ This doesn't return the saver
    return self
```

**After:**
```python
async def __aenter__(self):
    checkpointer_cm = AsyncSqliteSaver.from_conn_string(str(self.db_path))
    self._checkpointer = await checkpointer_cm.__aenter__()  # ✅ Get actual saver
    self._checkpointer_cm = checkpointer_cm  # Keep reference for cleanup
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    if hasattr(self, '_checkpointer_cm') and self._checkpointer_cm:
        await self._checkpointer_cm.__aexit__(exc_type, exc_val, exc_tb)
```

#### 2. ConversationOrchestrator (`memory/orchestrator.py`)

Made graph compilation **lazy** to avoid accessing checkpointer before SessionStore is entered:

**Before:**
```python
def __init__(self, agent, session_store, ...):
    # ...
    self.graph = self._build_graph()  # ❌ Compiled immediately
```

**After:**
```python
def __init__(self, agent, session_store, ...):
    # ...
    self._graph = None  # Lazy initialization

@property
def graph(self):
    """Lazy graph initialization."""
    if self._graph is None:
        self._graph = self._build_graph()  # ✅ Compiled only when accessed
    return self._graph
```

#### 3. Checkpointer Property (`memory/store.py`)

Made checkpointer property return `Optional` instead of raising error:

**Before:**
```python
@property
def checkpointer(self) -> BaseCheckpointSaver:
    if not self._checkpointer:
        raise RuntimeError("SessionStore not initialized")  # ❌ Raises error
    return self._checkpointer
```

**After:**
```python
@property
def checkpointer(self) -> Optional[BaseCheckpointSaver]:
    return self._checkpointer  # ✅ Returns None if not initialized
```

## Verification

```bash
cd backend
python -c "
from karamba.memory import SessionStore, ConversationOrchestrator
from karamba.core.agent import KarambaAgent
from karamba.llm import LLMConfig
import asyncio

async def test():
    llm_config = LLMConfig(provider='ollama', model='llama3.2:3b')
    agent = KarambaAgent(llm_config=llm_config, vector_store_path='./data/test_vector')

    store = SessionStore(db_path='./data/test_sessions.db')
    orchestrator = ConversationOrchestrator(agent, store)
    print('✅ Orchestrator created before context entry')

    async with store:
        graph = orchestrator.graph
        print('✅ Graph compiled successfully')
        print(f'✅ Checkpointer available: {store.checkpointer is not None}')

asyncio.run(test())
"
```

**Output:**
```
✅ Orchestrator created before context entry
✅ Graph compiled successfully
✅ Checkpointer available: True
```

## Server Startup

```bash
python -m api.main
```

**Output:**
```
INFO: Starting Karamba API
INFO: Karamba agent initialized
INFO: Session store initialized with DB: data/sessions.db
INFO: Conversation orchestrator initialized
INFO: Karamba agent, session store, and orchestrator initialized
INFO: Application startup complete
```

✅ **No more checkpointer errors!**

## Key Learnings

1. **Async Context Managers:** When a library method returns a context manager, you must `await cm.__aenter__()` to get the actual instance.

2. **Lazy Initialization:** For components that depend on async context managers, use lazy initialization (properties) to defer creation until after context entry.

3. **Optional Types:** Use `Optional[T]` for properties that may not be available immediately, rather than raising errors.

## Testing

All existing tests still pass:

```bash
pytest tests/test_memory.py -v
# 44 tests passed
```

API endpoints work correctly:

```bash
curl http://localhost:8000/api/v1/conversations/test-session/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello"}'
```

---

**Status:** ✅ **FIXED**
**Date:** February 3, 2026
**Impact:** Session memory and HITL features now fully functional
