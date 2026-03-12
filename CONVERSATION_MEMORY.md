# Conversation Memory & Human-in-the-Loop Guide

This guide explains how to use Karamba's new conversation memory and human-in-the-loop (HITL) features powered by LangGraph.

## Architecture Overview

Karamba now uses a hybrid architecture:

```
┌─────────────────────────────────────────┐
│   LangGraph Conversation Orchestrator   │
│  (Memory, HITL, Checkpointing, Future:  │
│   Reflection, Tool Calling)             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Existing Karamba Phase Engine        │
│  (Planning → Retrieval → Reasoning)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       BaseLLM Abstraction               │
│  (Ollama, Anthropic, OpenAI)            │
└─────────────────────────────────────────┘
```

**Key Benefits:**
- ✅ **Preserves existing phase engine** - Your custom workflow stays intact
- ✅ **Adds conversation memory** - Multi-turn conversations with history
- ✅ **Enables HITL** - Pause for human approval when needed
- ✅ **Foundation for future** - Ready for reflection & tool calling

---

## Feature 1: Session-Based Conversations

### API Endpoints

#### Start a Conversation
```bash
POST /api/v1/conversations/{session_id}/query
```

**Request:**
```json
{
  "query": "What is climate change?",
  "document_ids": ["climate_report.pdf"],
  "approved": false
}
```

**Response:**
```json
{
  "session_id": "session-123",
  "answer": "Climate change refers to...",
  "phase_results": [...],
  "citations": [...],
  "requires_approval": false
}
```

#### Continue Conversation
```bash
POST /api/v1/conversations/{session_id}/query
```

**Request:**
```json
{
  "query": "What are the main causes?",
  "document_ids": []
}
```

The agent **automatically remembers** previous context!

#### Get Conversation History
```bash
GET /api/v1/conversations/{session_id}/history?limit=10
```

**Response:**
```json
{
  "session_id": "session-123",
  "messages": [
    {
      "role": "user",
      "content": "What is climate change?",
      "timestamp": "2026-02-03T17:00:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "Climate change refers to...",
      "timestamp": "2026-02-03T17:00:05Z",
      "metadata": {"citations": [...]}
    }
  ],
  "message_count": 2
}
```

---

## Feature 2: Human-in-the-Loop (HITL)

### How It Works

Certain queries automatically trigger approval requests:

**Triggers:**
- Queries containing "delete", "remove", "clear all"
- Custom business logic (extend in `orchestrator.py`)

### Example Flow

1. **User asks potentially destructive query:**
```bash
POST /api/v1/conversations/session-123/query
{
  "query": "Delete all documents about finance"
}
```

2. **System pauses and requests approval:**
```json
{
  "session_id": "session-123",
  "answer": "",
  "requires_approval": true,
  "pending_action": {
    "action_id": "action_session-123",
    "action_type": "query_execution",
    "query": "Delete all documents about finance",
    "reason": "Query contains potentially destructive operations"
  }
}
```

3. **Human reviews and approves:**
```bash
POST /api/v1/conversations/session-123/approve
{
  "action_id": "action_session-123"
}
```

4. **System continues execution:**
```json
{
  "session_id": "session-123",
  "answer": "Deleted 5 documents about finance",
  "requires_approval": false
}
```

### Check Approval Status

```bash
GET /api/v1/conversations/{session_id}/status
```

**Response:**
```json
{
  "session_id": "session-123",
  "thread_id": "thread_session-123",
  "message_count": 10,
  "document_count": 3,
  "has_pending_approval": true,
  "pending_approval": {
    "action_id": "action_session-123",
    "action_type": "query_execution",
    "query": "Delete all documents"
  },
  "created_at": "2026-02-03T16:00:00Z",
  "last_activity": "2026-02-03T17:00:00Z"
}
```

---

## Feature 3: Session Management

### List All Sessions
```bash
GET /api/v1/conversations/
```

**Response:**
```json
{
  "sessions": ["session-123", "session-456"],
  "total_count": 2
}
```

### Clear Conversation History
```bash
DELETE /api/v1/conversations/{session_id}/history
```

Keeps session but clears messages.

### Delete Session Completely
```bash
DELETE /api/v1/conversations/{session_id}
```

---

## Python SDK Usage

### Basic Conversation

```python
from karamba.memory import SessionStore, ConversationOrchestrator
from karamba.core.agent import KarambaAgent
from karamba.llm import LLMConfig

# Initialize components
llm_config = LLMConfig(provider="ollama", model="llama3.2:3b")
agent = KarambaAgent(llm_config=llm_config)

async with SessionStore() as store:
    orchestrator = ConversationOrchestrator(
        agent=agent,
        session_store=store
    )

    # First query
    result1 = await orchestrator.query(
        session_id="my-session",
        query="What is machine learning?"
    )
    print(result1["answer"])

    # Follow-up query (remembers context!)
    result2 = await orchestrator.query(
        session_id="my-session",
        query="What are its applications?"
    )
    print(result2["answer"])

    # Get conversation history
    history = await orchestrator.get_conversation("my-session")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")
```

### HITL Workflow

```python
# Query that requires approval
result = await orchestrator.query(
    session_id="my-session",
    query="Delete all old reports"
)

if result["requires_approval"]:
    print("⚠️  Approval required!")
    print(f"Action: {result['pending_action']}")

    # Human reviews...
    user_input = input("Approve? (y/n): ")

    if user_input.lower() == 'y':
        # Continue execution
        result = await orchestrator.approve_and_continue(
            session_id="my-session",
            action_id=result["pending_action"]["action_id"]
        )
        print(f"✅ Completed: {result['answer']}")
    else:
        print("❌ Cancelled")
```

---

## Future Enhancements

### 1. Reflection Pattern (Coming Soon)

Enable self-critique and iterative improvement:

```python
orchestrator = ConversationOrchestrator(
    agent=agent,
    session_store=store,
    enable_reflection=True,
    max_reflection_iterations=2
)
```

**How it works:**
1. Agent generates initial answer
2. Reflects on quality and accuracy
3. If quality < threshold, regenerates with improvements
4. Continues until quality acceptable or max iterations

### 2. Tool Calling (Planned)

Extend agent with external tools:

```python
from karamba.tools import WebSearchTool, CalculatorTool

orchestrator = ConversationOrchestrator(
    agent=agent,
    session_store=store,
    tools=[WebSearchTool(), CalculatorTool()]
)
```

### 3. Multi-Agent Collaboration (Planned)

Different agents for different tasks:

```python
orchestrator = MultiAgentOrchestrator(
    agents={
        "research": research_agent,
        "summarization": summary_agent,
        "fact_check": fact_check_agent
    },
    session_store=store
)
```

---

## Configuration

### Environment Variables

```bash
# Session database location
SESSION_DB_PATH=./data/sessions.db

# Enable/disable features
ENABLE_REFLECTION=false
MAX_REFLECTION_ITERATIONS=2

# Conversation settings
MAX_HISTORY_LENGTH=50
CONVERSATION_TIMEOUT_MINUTES=60
```

### Customizing HITL Triggers

Edit `backend/src/karamba/memory/orchestrator.py`:

```python
async def _check_approval_node(self, state: GraphState) -> GraphState:
    """Check if query requires approval (HITL)."""
    query_lower = state["query"].lower()

    # Add your custom triggers
    requires_approval = any(keyword in query_lower for keyword in [
        "delete", "remove", "clear all",
        "drop table",  # Database operations
        "shutdown",    # System operations
        "transfer",    # Financial operations
    ])

    # Or use ML-based classification
    # requires_approval = sensitive_query_classifier.predict(query)

    state["requires_approval"] = requires_approval
    ...
```

---

## Testing

Run memory tests:

```bash
cd backend
pytest tests/test_memory.py -v
```

**Test Coverage:**
- ✅ Conversation history management
- ✅ Session state persistence
- ✅ Message storage and retrieval
- ✅ HITL approval workflow
- ✅ Multi-turn context handling

---

## Migration Guide

### Existing Code

```python
# Old way (single query, no memory)
response = await agent.answer_question(request)
```

### New Code

```python
# New way (with conversation memory)
async with SessionStore() as store:
    orchestrator = ConversationOrchestrator(agent, store)
    result = await orchestrator.query(
        session_id="user-123",
        query=request.query
    )
```

**Benefits:**
- 🔄 Multi-turn conversations
- 💾 Persistent history
- ⏸️  HITL support
- 🔮 Future-ready for reflection & tools

---

## Performance Considerations

- **Memory Usage:** Each session stores full conversation history in memory
- **Database:** SQLite checkpoint storage (can switch to Postgres for scale)
- **Recommendation:** Clear old sessions periodically

```python
# Cleanup old sessions
async def cleanup_old_sessions(store: SessionStore, days: int = 7):
    sessions = await store.list_sessions()
    for session_id in sessions:
        state = await store.get_session(session_id)
        if (datetime.now() - state.last_activity).days > days:
            await store.delete_session(session_id)
```

---

## Troubleshooting

### Issue: "Session store not initialized"

**Solution:** Ensure you're using the async context manager:

```python
async with SessionStore() as store:
    # Your code here
    pass
```

### Issue: Approval never completes

**Check:** Is `interrupt_before` enabled in graph?

```python
self.graph = workflow.compile(
    checkpointer=self.session_store.checkpointer,
    interrupt_before=["check_approval"]  # Must be enabled
)
```

---

## Next Steps

1. ✅ **Try the examples** - Test conversation memory
2. ✅ **Customize HITL triggers** - Add business logic
3. 🔄 **Enable reflection** - When ready for quality improvements
4. 🛠️  **Add tools** - Extend agent capabilities
5. 🚀 **Scale up** - Switch to Postgres for production

For questions or issues, see the main [README](README.md) or open an issue on GitHub.
