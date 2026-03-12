# Context-Aware Human-in-the-Loop (HITL)

## Overview

The HITL system now intelligently determines when human approval is needed based on:
1. **Agent-level policies** - Each agent declares its approval requirements
2. **Phase-based risk detection** - Planning phase analyzes for risky actions

This prevents unnecessary interruptions while catching genuinely risky operations.

---

## Architecture

### 1. Agent Approval Policies

**Location**: [backend/src/karamba/agents/base.py](backend/src/karamba/agents/base.py)

Each agent now declares an `ApprovalPolicy`:

```python
class ApprovalPolicy(BaseModel):
    requires_approval: bool = False  # Always require approval?
    approval_triggers: List[str] = []  # Keywords that trigger approval
    risky_actions: List[str] = []  # Action types that need approval
```

**Example - Research Agent**:
```python
approval_policy=ApprovalPolicy(
    requires_approval=False,  # Research queries don't need approval
    approval_triggers=["delete", "remove"],  # But deletion does
    risky_actions=["delete_document", "clear_data"]
)
```

### 2. Agent Approval Check Method

**Location**: [backend/src/karamba/agents/base.py](backend/src/karamba/agents/base.py#L95-L125)

```python
def requires_approval(
    self,
    query: str,
    detected_actions: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> tuple[bool, Optional[str]]:
    """Check if query requires approval based on agent policy."""
```

The method checks:
1. Does the agent always require approval?
2. Does the query contain approval trigger keywords?
3. Do detected actions match risky action patterns?

Returns: `(requires_approval: bool, reason: Optional[str])`

---

### 3. Phase-Based Risk Detection

**Location**: [backend/src/karamba/core/phase_engine.py](backend/src/karamba/core/phase_engine.py#L11-L38)

The planning phase now analyzes its output for risky actions:

```python
def detect_risky_actions(text: str) -> List[str]:
    """Detect potentially risky actions in planning output."""

    risk_patterns = {
        "delete_document": r"\b(delete|remove|erase)\b.*\b(document|file)\b",
        "clear_data": r"\b(clear|wipe|purge)\b.*\b(data|database)\b",
        "modify_data": r"\b(update|modify|change)\b.*\b(data|database)\b",
        "external_api": r"\b(call|invoke|request)\b.*\b(api|external)\b",
        "file_operation": r"\b(write|create|delete)\b.*\b(file|directory)\b",
    }
```

Detected actions are added to the planning phase result metadata:
```python
metadata["detected_risky_actions"] = ["delete_document", "modify_data"]
```

---

### 4. Updated Check Approval Node

**Location**: [backend/src/karamba/memory/orchestrator.py](backend/src/karamba/memory/orchestrator.py#L189-L234)

The orchestrator's approval check now:

1. **Gets the selected agent** from the router
2. **Calls agent.requires_approval()** with the query
3. **Logs the decision** with reason
4. **Requests approval if needed** via session store

```python
if self.use_router:
    selected_agent = self.agent.registry.get(agent_id)
    requires_approval, reason = selected_agent.requires_approval(
        query=state["query"],
        detected_actions=None,  # Future: pass from planning phase
        context={"session_id": state["session_id"]}
    )
```

---

## How It Works

### Normal Research Query

**Query**: "What is AI?"

```
1. Router selects: research_agent
2. Check approval:
   - Agent policy: requires_approval=False
   - No trigger keywords found
   - Result: ✅ No approval needed
3. Execute normally
```

### Deletion Query

**Query**: "Delete the old report document"

```
1. Router selects: research_agent
2. Check approval:
   - Agent policy: requires_approval=False
   - Trigger found: "delete"
   - Result: ⚠️ Approval required
3. Planning phase detects:
   - Risky action: "delete_document"
4. Request approval before execution
```

### Future: Phase-Detected Risks

**Query**: "Update the database with new values"

```
1. Router selects: research_agent
2. Check approval:
   - Agent policy: No triggers
   - Result: ✅ Continue
3. Planning phase detects:
   - Risky action: "modify_data"
   - (Future) Pause and request approval
```

---

## Agent Examples

### Research Agent (Low Risk)
```python
approval_policy=ApprovalPolicy(
    requires_approval=False,
    approval_triggers=["delete", "remove"],
    risky_actions=["delete_document", "clear_data"]
)
```
- ✅ Research queries: No approval
- ⚠️ Deletion queries: Approval required

### Financial Risk Agent (High Risk)
```python
approval_policy=ApprovalPolicy(
    requires_approval=True,  # Always require approval
    risky_actions=["portfolio_change", "risk_calculation", "financial_advice"]
)
```
- ⚠️ All queries: Approval required

---

## Benefits

### 1. Reduced Friction
- ✅ Normal queries execute immediately
- ⚠️ Only risky operations pause for approval
- No more blanket interrupts

### 2. Agent-Specific Policies
- Research agents: Permissive
- Financial agents: Restrictive
- Custom agents: Configurable

### 3. Phase-Level Intelligence
- Planning detects risky actions
- Provides context for approval decision
- Can catch subtle risks keyword matching misses

### 4. Clear Audit Trail
- Every approval decision is logged
- Reason is provided
- Trackable in session store

---

## Current State

### ✅ Implemented
- Agent approval policies
- Agent-level approval checking
- Phase-based risk detection
- Updated orchestrator approval node
- Research agent example policy

### 🚧 Future Enhancements
1. **Confidence-based approval**
   - Low routing confidence triggers approval
   - Uncertainty in planning triggers review

2. **User preferences**
   - Per-user approval settings
   - "Always approve for me" mode
   - Risk tolerance levels

3. **Two-stage approval**
   - Pre-execution: Agent-level check (current)
   - Post-planning: Action-level check (future)

4. **Approval UI**
   - Frontend modal for approval requests
   - Show detected risks
   - One-click approve/deny

---

## Testing

### Test Scenario 1: Normal Query
```bash
# Query: "What is machine learning?"
# Expected: No approval, executes immediately
```

### Test Scenario 2: Deletion Query
```bash
# Query: "Delete the old reports"
# Expected: Approval requested with reason "Query contains trigger word: 'delete'"
```

### Test Scenario 3: Planning Detection
```bash
# Query: "Update all records in the database"
# Expected: Planning detects "modify_data", logs detected risky actions
```

---

## Configuration

### Disable HITL Entirely
```python
# In orchestrator.py line 137
interrupt_before=None  # Disable all interrupts
```

### Enable HITL with Smart Interrupts
```python
# Future: Conditional interrupt based on approval requirement
interrupt_before=["check_approval"] if requires_approval else None
```

---

## Migration Guide

### Adding Approval Policy to New Agent

1. Import `ApprovalPolicy`:
```python
from karamba.agents.base import ApprovalPolicy
```

2. Add to metadata:
```python
@property
def metadata(self) -> AgentMetadata:
    return AgentMetadata(
        name="My Agent",
        # ... other fields ...
        approval_policy=ApprovalPolicy(
            requires_approval=False,
            approval_triggers=["trigger_word"],
            risky_actions=["action_type"]
        )
    )
```

3. Test approval behavior:
```python
agent = MyAgent()
requires, reason = agent.requires_approval("delete files")
print(f"Requires approval: {requires}, Reason: {reason}")
```

---

## Summary

The context-aware HITL system provides intelligent approval gating that:
- ✅ Respects agent-specific risk profiles
- ✅ Analyzes planning output for risky actions
- ✅ Provides clear reasoning for approval requests
- ✅ Maintains audit trail of decisions
- ✅ Minimizes friction for normal operations

This makes HITL practical and user-friendly while maintaining safety for risky operations.
