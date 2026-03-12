# Multi-Agent System with Automatic Routing

## Overview

Karamba now features an intelligent multi-agent system with automatic query routing. Instead of requiring users to manually select which agent to use, the system automatically analyzes each query and routes it to the most appropriate specialist agent.

**Key Feature**: Users simply ask questions naturally, and the system automatically determines whether to use the Research Assistant or Financial Risk Analyst based on the query content.

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              AgentRouter (Intent Classifier)             │
│  • LLM-based query classification                        │
│  • Rule-based confidence scoring                         │
│  • Automatic agent selection                             │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────────┐   ┌──────────────────────┐
│ Research Agent   │   │ Financial Risk Agent │
│ (General Q&A)    │   │ (Risk Assessment)    │
└──────────────────┘   └──────────────────────┘
```

### Specialist Agents

1. **Research Agent** (`research_agent`)
   - General-purpose research and document Q&A
   - Information synthesis and summarization
   - Knowledge extraction
   - **Phases**: Planning → Retrieval → Reasoning

2. **Financial Risk Agent** (`financial_risk_agent`)
   - Financial risk assessment and analysis
   - Portfolio evaluation
   - Investment analysis
   - Risk metrics calculation
   - **Phases**: Financial Context → Retrieval → Risk Assessment

---

## How It Works

### 1. Automatic Query Routing

When a user sends a query, the system:

1. **Analyzes the query** using both LLM-based classification and rule-based keyword matching
2. **Selects the best agent** based on confidence scores
3. **Routes the query** to the selected specialist agent
4. **Returns the response** with metadata about which agent answered

### 2. Intent Classification

The router uses a **hybrid approach**:

- **LLM-based classification (70% weight)**: Uses the language model to understand the semantic intent of the query
- **Rule-based scoring (30% weight)**: Matches keywords and patterns for fast, reliable baseline scoring

#### Example Routing Decisions

| Query | Selected Agent | Confidence | Reasoning |
|-------|---------------|------------|-----------|
| "What is artificial intelligence?" | Research Agent | 0.85 | General information query with research keywords |
| "Assess the financial risk of this portfolio" | Financial Risk Agent | 0.95 | Contains explicit financial risk assessment request |
| "Analyze the volatility of these stocks" | Financial Risk Agent | 0.90 | Financial metrics analysis |
| "Explain quantum computing" | Research Agent | 0.80 | General knowledge question |
| "What are the key findings in this paper?" | Research Agent | 0.88 | Document Q&A and summarization |

---

## Implementation Details

### Backend Structure

```
backend/src/karamba/agents/
├── __init__.py           # Exports all agents and router
├── base.py               # BaseSpecialistAgent abstract class
├── research.py           # ResearchAgent implementation
├── financial.py          # FinancialRiskAgent implementation
└── router.py             # AgentRouter and AgentRegistry
```

### Key Classes

#### BaseSpecialistAgent

Abstract base class for all specialist agents.

```python
class BaseSpecialistAgent(ABC):
    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return metadata describing this agent's capabilities"""
        pass

    @abstractmethod
    async def process_query(
        self,
        request: AgentRequest,
        session_context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process a query using this specialist agent"""
        pass

    @abstractmethod
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Determine confidence (0.0-1.0) that this agent can handle the query"""
        pass
```

#### AgentRouter

Automatically routes queries to the appropriate agent.

```python
class AgentRouter:
    def __init__(self, llm: BaseLLM, registry: AgentRegistry, use_llm_routing: bool = True):
        """Initialize router with LLM and agent registry"""

    async def route(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RouteDecision:
        """
        Route a query to the most appropriate specialist agent.
        Returns: RouteDecision with agent_id, confidence, and reasoning
        """
```

#### AgentRegistry

Manages the collection of available specialist agents.

```python
class AgentRegistry:
    def register(self, agent: BaseSpecialistAgent) -> None:
        """Register a specialist agent"""

    def get(self, agent_id: str) -> Optional[BaseSpecialistAgent]:
        """Get an agent by ID"""

    def list_agents(self) -> List[BaseSpecialistAgent]:
        """List all registered agents"""
```

---

## Specialist Agent Details

### Research Agent

**Capabilities**:
- General research questions
- Document question-answering
- Summarization
- Information synthesis

**Keywords**: research, question, what, how, why, explain, summarize, describe, tell me about, information

**Example Queries**:
- "What are the key findings in the research papers?"
- "Explain the concept of quantum computing"
- "Summarize the main points from the uploaded documents"
- "How does machine learning work?"

**Phase Pipeline**:
1. **Planning**: Analyze the question and create a research plan
2. **Retrieval**: Retrieve relevant document chunks
3. **Reasoning**: Synthesize information and provide comprehensive answer

---

### Financial Risk Agent

**Capabilities**:
- Financial risk analysis
- Portfolio assessment
- Risk metrics calculation
- Investment evaluation

**Keywords**: risk, financial, investment, portfolio, return, volatility, sharpe, var, equity, stock, bonds, credit

**Example Queries**:
- "Assess the financial risk of this equity portfolio"
- "What are the key risk factors in these investment documents?"
- "Evaluate the credit risk of this company"
- "Analyze the volatility and return profile of these assets"

**Phase Pipeline**:
1. **Financial Context**: Establish context and identify required analysis
2. **Retrieval**: Retrieve relevant financial data and metrics
3. **Risk Assessment**: Perform comprehensive risk analysis with:
   - Risk identification and categorization
   - Quantitative analysis (metrics, trends)
   - Qualitative analysis (governance, controls)
   - Risk rating (Low/Medium/High)
   - Recommendations and mitigation strategies

---

## API Endpoints

### Query with Automatic Routing

```http
POST /api/v1/conversations/{session_id}/query
```

**Request**:
```json
{
  "query": "What is the risk profile of this portfolio?",
  "document_ids": ["doc1", "doc2"],
  "approved": false
}
```

**Response**:
```json
{
  "session_id": "session123",
  "answer": "Based on the analysis...",
  "phase_results": [...],
  "citations": [...],
  "agent_id": "financial_risk_agent",
  "agent_name": "Financial Risk Analyst",
  "routing_confidence": 0.95,
  "routing_reasoning": "Query explicitly requests financial risk assessment",
  "requires_approval": false
}
```

### Get Available Agents

```http
GET /api/v1/conversations/agents
```

**Response**:
```json
{
  "agents": [
    {
      "agent_id": "research_agent",
      "name": "Research Assistant",
      "description": "General-purpose research agent...",
      "capabilities": ["research", "document_qa", "summarization"],
      "keywords": ["research", "question", "what", "how", "why"],
      "example_queries": [
        "What are the key findings...",
        "Explain the concept of..."
      ]
    },
    {
      "agent_id": "financial_risk_agent",
      "name": "Financial Risk Analyst",
      "description": "Specialist agent for financial risk assessment...",
      "capabilities": ["financial_analysis", "risk_assessment"],
      "keywords": ["risk", "financial", "investment", "portfolio"],
      "example_queries": [
        "Assess the financial risk...",
        "Evaluate the credit risk..."
      ]
    }
  ],
  "total_count": 2
}
```

---

## Frontend Integration

### Agent Badge Display

The frontend automatically displays which agent responded to each query:

- **Research Assistant** badge: 📚 (blue)
- **Financial Risk Analyst** badge: 📊 (green)

### Updated Message Interface

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  phaseResults?: any[];
  citations?: any[];
  agentId?: string;          // NEW: Which agent responded
  agentName?: string;        // NEW: Agent display name
  routingConfidence?: number; // NEW: Routing confidence score
  routingReasoning?: string;  // NEW: Why this agent was selected
}
```

### User Experience

1. User types a question naturally
2. System automatically routes to the best agent
3. Response shows which agent answered (via badge)
4. No manual agent selection required!

**Example**:

```
User: "What are the key findings in these research papers?"
  ↓
[📚 Research Assistant badge]
Response: "Based on the research papers, the key findings include..."

User: "What is the financial risk of this portfolio?"
  ↓
[📊 Financial Risk Analyst badge]
Response: "Based on the portfolio analysis, the overall risk rating is..."
```

---

## Configuration

### Initialize Multi-Agent System

In [backend/src/api/main.py](backend/src/api/main.py):

```python
# Create LLM
llm = create_llm(llm_config)

# Create specialist agents
research_agent = ResearchAgent(
    agent_id="research_agent",
    llm_config=llm_config,
    vector_store_path="./data/vector_store"
)

financial_agent = FinancialRiskAgent(
    agent_id="financial_risk_agent",
    llm_config=llm_config,
    vector_store_path="./data/vector_store"
)

# Create registry and register agents
registry = AgentRegistry()
registry.register(research_agent)
registry.register(financial_agent)

# Create router
router = AgentRouter(
    llm=llm,
    registry=registry,
    use_llm_routing=True  # Enable LLM-based routing
)

# Initialize orchestrator with router
orchestrator = ConversationOrchestrator(
    agent=router,  # Pass router instead of single agent
    session_store=session_store
)
```

---

## Adding New Specialist Agents

To add a new specialist agent to the system:

### 1. Create Agent Class

```python
# backend/src/karamba/agents/your_agent.py

from karamba.agents.base import BaseSpecialistAgent, AgentCapability, AgentMetadata

class YourSpecialistAgent(BaseSpecialistAgent):
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="Your Agent Name",
            description="What this agent does",
            capabilities=[AgentCapability.YOUR_CAPABILITY],
            keywords=["keyword1", "keyword2"],
            example_queries=["Example query 1", "Example query 2"]
        )

    async def process_query(self, request: AgentRequest, session_context=None):
        # Your agent logic here
        pass

    def can_handle(self, query: str, context=None) -> float:
        # Return confidence score 0.0-1.0
        pass
```

### 2. Register Agent

```python
# In main.py
your_agent = YourSpecialistAgent(
    agent_id="your_agent_id",
    llm_config=llm_config
)

registry.register(your_agent)
```

### 3. Update Frontend Badge (optional)

```typescript
// In MessageList.tsx
const badgeColor = agentId === 'research_agent'
  ? 'bg-blue-100 text-blue-800'
  : agentId === 'financial_risk_agent'
  ? 'bg-green-100 text-green-800'
  : agentId === 'your_agent_id'
  ? 'bg-purple-100 text-purple-800'  // Add your color
  : 'bg-gray-100 text-gray-800';

const icon = agentId === 'financial_risk_agent' ? '📊'
  : agentId === 'your_agent_id' ? '🎯'  // Add your icon
  : '📚';
```

---

## Testing

### Test Agent Routing

```bash
# Start the backend
cd backend
python -m uvicorn src.api.main:app --reload

# Test with curl
curl -X POST http://localhost:8000/api/v1/conversations/test-session/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the financial risk of investing in tech stocks?",
    "document_ids": []
  }'
```

### Expected Response

```json
{
  "answer": "Based on the analysis of tech stock investments...",
  "agent_id": "financial_risk_agent",
  "agent_name": "Financial Risk Analyst",
  "routing_confidence": 0.92,
  "routing_reasoning": "Query contains financial risk assessment keywords",
  ...
}
```

---

## Benefits

### For Users

✅ **No manual agent selection** - Just ask questions naturally
✅ **Automatic expert routing** - Questions go to the right specialist
✅ **Transparent** - See which agent answered via badges
✅ **Seamless experience** - Same interface, smarter backend

### For Developers

✅ **Extensible** - Easy to add new specialist agents
✅ **Maintainable** - Each agent has isolated logic
✅ **Testable** - Agents can be tested independently
✅ **Flexible** - Supports both single-agent and multi-agent modes

### For the System

✅ **Specialized expertise** - Each agent optimized for its domain
✅ **Better quality** - Domain-specific prompts and phases
✅ **Scalable** - Add agents without changing core infrastructure
✅ **Intelligent** - LLM + rule-based hybrid routing

---

## Future Enhancements

### Short-term

- Add confidence threshold warnings (e.g., "I'm not sure, but I'll try...")
- Support agent handoff (start with one, switch to another)
- Add agent performance metrics and analytics

### Medium-term

- Add more specialist agents:
  - Legal document analysis agent
  - Medical research agent
  - Code review agent
- Implement reflection pattern per agent
- Add agent collaboration (multiple agents working together)

### Long-term

- Multi-turn agent conversations
- Dynamic agent creation based on user needs
- Agent learning from user feedback
- Hierarchical agent systems (meta-agents coordinating specialists)

---

## Migration from Single Agent

The system maintains **backward compatibility**:

- Old endpoints still work with a single default agent
- Existing code can be migrated incrementally
- No breaking changes to the API contract

To migrate existing code:

1. Update API calls to use conversation endpoints
2. Update frontend to display agent badges
3. Enjoy automatic routing! 🎉

---

## Troubleshooting

### Agent not routing correctly

- Check agent keywords and can_handle() logic
- Review LLM routing prompt in router.py
- Increase logging to see routing decisions

### TypeScript errors

- Ensure all interfaces are updated with agent fields
- Run `npm install` in frontend directory
- Check types.ts and api.ts for consistency

### Agent not found error

- Verify agent is registered in main.py
- Check agent_id matches exactly (case-sensitive)
- Ensure registry is passed to router

---

## Summary

### Files Modified

**Backend**:
- ✅ [backend/src/karamba/agents/__init__.py](backend/src/karamba/agents/__init__.py) - Created agent module
- ✅ [backend/src/karamba/agents/base.py](backend/src/karamba/agents/base.py) - Base agent class
- ✅ [backend/src/karamba/agents/research.py](backend/src/karamba/agents/research.py) - Research agent
- ✅ [backend/src/karamba/agents/financial.py](backend/src/karamba/agents/financial.py) - Financial agent
- ✅ [backend/src/karamba/agents/router.py](backend/src/karamba/agents/router.py) - Agent router
- ✅ [backend/src/karamba/memory/orchestrator.py](backend/src/karamba/memory/orchestrator.py) - Updated for routing
- ✅ [backend/src/api/main.py](backend/src/api/main.py) - Initialize multi-agent system
- ✅ [backend/src/api/dependencies.py](backend/src/api/dependencies.py) - Added router dependency
- ✅ [backend/src/api/routes/conversations.py](backend/src/api/routes/conversations.py) - Updated responses + new endpoint

**Frontend**:
- ✅ [frontend/src/types.ts](frontend/src/types.ts) - Added agent interfaces
- ✅ [frontend/src/services/api.ts](frontend/src/services/api.ts) - Updated QueryResponse
- ✅ [frontend/src/components/Chat/ChatContainer.tsx](frontend/src/components/Chat/ChatContainer.tsx) - Added agent info
- ✅ [frontend/src/components/Chat/MessageList.tsx](frontend/src/components/Chat/MessageList.tsx) - Agent badges

### Status

✅ **Implemented** - February 4, 2026
✅ **Tested** - Ready for integration testing
✅ **Production-Ready** - Fully functional with automatic routing

---

**The multi-agent system is now live! Users can simply ask questions naturally, and Karamba will automatically route them to the most appropriate specialist agent. No manual selection required!** 🚀
