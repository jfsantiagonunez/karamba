# Automatic Tool Integration for All Agents

## The Problem (Before)

Each agent had to manually integrate tools:

```python
class FinancialRiskAgent(BaseSpecialistAgent):
    def __init__(self, dataframe_tool, search_service, ...):
        self.df_tool = dataframe_tool
        self.search_service = search_service

    async def process_query(self, request):
        # Manual routing logic (50+ lines)
        if has_excel_file and "calculate" in query:
            df_tool.load_excel(...)
            result = df_tool.filter_rows(...)
        elif "current" in query:
            search_service.search(...)
        # ... complex logic in EVERY agent!
```

**Problems:**
- Every agent reimplements tool routing
- Code duplication
- Easy to forget tools
- Inconsistent behavior across agents

## The Solution ✅ ToolAwareAgent

**All agents inherit from `ToolAwareAgent` and get tools automatically!**

```python
from karamba.agents.tool_aware import ToolAwareAgent

class FinancialRiskAgent(ToolAwareAgent):  # Inherit!
    def __init__(self, agent_id, ...):
        super().__init__(
            agent_id=agent_id,
            # Tools injected automatically via registry
        )

    async def process_query(self, request):
        # 🎯 Automatic tool routing - NO manual code!
        tool_results = await self.process_query_with_tools(request)

        # Tool results automatically available:
        if "dataframe" in tool_results:
            df_summary = tool_results["dataframe"]["summary"]
            # Use summary in LLM prompt

        if "web_search" in tool_results:
            web_info = tool_results["web_search"]["results"]
            # Use web info in analysis

        # Agent focuses on domain logic, not tool plumbing!
```

## How It Works

### 1. Automatic Detection

The base class **automatically** detects:
- ✅ What document types are in the session (Excel, PDF, CSV, etc.)
- ✅ What the query is asking for (calculation, search, analysis)
- ✅ Which tools are available
- ✅ Which tools to use

```python
# Behind the scenes (you don't write this!)
doc_context = self._detect_document_context(request)
# → Detects: has_tabular=True, tabular_files=["portfolio.xlsx"]

needs_tabular = self._query_needs_tabular_analysis(request.query)
# → Query: "Calculate Sharpe ratio" → True

needs_web = self._query_needs_web_search(request.query)
# → Query: "Current market trends" → True
```

### 2. Automatic Routing

Based on detection, routes to appropriate tools:

```python
# Automatic routing (you don't write this!)
if doc_context.has_tabular and needs_tabular:
    df_result = await self._route_to_dataframe_tool(request, doc_context)
    # → Loads Excel, gets summary, returns LLM-safe results

if needs_web:
    web_result = await self._route_to_web_search(request)
    # → Performs search, returns formatted results

# Returns all results to agent
return {
    "dataframe": {...},
    "web_search": {...}
}
```

### 3. Agent Uses Results

Agent just uses the pre-processed results:

```python
async def process_query(self, request):
    # Get tool results automatically
    tools = await self.process_query_with_tools(request)

    # Build context for LLM
    context = {"query": request.query}

    if "dataframe" in tools:
        context["data_summary"] = tools["dataframe"]["summary"]
        # LLM sees: "10,000 rows, 20 columns, sectors: Tech, Finance..."

    if "web_search" in tools:
        context["current_info"] = tools["web_search"]["results"]
        # LLM sees: "Latest market trends: ..."

    # Agent focuses on analysis, not tool management!
    return await self._perform_analysis(context)
```

## Example: Agent Before vs. After

### Before (50+ lines of tool logic) ❌

```python
class FinancialRiskAgent(BaseSpecialistAgent):
    def __init__(self, df_tool, search, metrics, ...):
        self.df_tool = df_tool
        self.search = search
        self.metrics = metrics

    async def process_query(self, request):
        # Detect document types (10 lines)
        has_excel = False
        for doc_id in request.document_ids:
            if doc_id.endswith('.xlsx'):
                has_excel = True

        # Detect query intent (10 lines)
        needs_calculation = "calculate" in request.query
        needs_web = "current" in request.query

        # Route to tools (20 lines)
        if has_excel and needs_calculation:
            self.df_tool.load_excel(...)
            summary = self.df_tool.get_summary()
            # ... handle errors, edge cases

        if needs_web:
            results = await self.search.search(...)
            # ... format, handle errors

        # Finally do actual agent work (10 lines)
        return await self._analyze(...)
```

### After (10 lines total) ✅

```python
class FinancialRiskAgent(ToolAwareAgent):  # Inherit!
    async def process_query(self, request):
        # Get all tools automatically (1 line!)
        tools = await self.process_query_with_tools(request)

        # Use tool results (5 lines)
        context = {
            "query": request.query,
            "data": tools.get("dataframe", {}).get("summary"),
            "web": tools.get("web_search", {}).get("results")
        }

        # Focus on domain logic (4 lines)
        return await self._perform_risk_analysis(context)
```

## Tool Injection (Automatic via Registry)

In `main.py`, all agents automatically get tools:

```python
# Get all tools from registry
tool_registry = create_tool_registry()

# Create agent - tools injected automatically!
financial_agent = FinancialRiskAgent(
    agent_id="financial_risk_agent",
    llm_config=llm_config,
    # Tools are injected by base class via **kwargs or explicit params
    dataframe_tool=tool_registry.get_dataframe_tool(),
    code_executor=tool_registry.get_code_executor(),
    financial_metrics=tool_registry.get_financial_metrics(),
    search_service=tool_registry.get_web_search()
)
```

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Code per agent** | 50+ lines tool logic | 0 lines (automatic!) |
| **Consistency** | Each agent different | All agents same behavior |
| **Maintenance** | Update every agent | Update base class once |
| **New tools** | Add to each agent | Automatic for all agents |
| **Testing** | Test each agent | Test base class once |

## Detection Keywords

The base class automatically detects intent:

### Tabular Analysis Keywords
```
"calculate", "compute", "aggregate", "sum", "average",
"filter", "group by", "count", "sharpe", "volatility",
"portfolio", "returns", "statistics", "correlation"
```

### Web Search Keywords
```
"current", "latest", "recent", "today", "now",
"news", "market", "price", "stock"
```

### Calculation Keywords
```
"calculate", "compute", "simulate", "model",
"forecast", "predict", "estimate"
```

## Advanced: Override Detection

Agents can override detection logic if needed:

```python
class CustomAgent(ToolAwareAgent):
    def _query_needs_tabular_analysis(self, query: str) -> bool:
        # Custom logic for this agent
        if "my_custom_keyword" in query:
            return True
        # Fall back to default
        return super()._query_needs_tabular_analysis(query)
```

## Migration Guide

To migrate existing agents:

### Step 1: Change inheritance
```python
# Before
class MyAgent(BaseSpecialistAgent):

# After
class MyAgent(ToolAwareAgent):
```

### Step 2: Update __init__ to accept tools
```python
def __init__(self, agent_id, dataframe_tool=None, ...):
    super().__init__(
        agent_id=agent_id,
        dataframe_tool=dataframe_tool,
        # ... other tools
    )
```

### Step 3: Use automatic routing
```python
async def process_query(self, request):
    # Add this line to get automatic tool results
    tools = await self.process_query_with_tools(request)

    # Use tool results in your logic
    if "dataframe" in tools:
        data_summary = tools["dataframe"]["summary"]
```

### Step 4: Remove manual tool logic
```python
# Remove all manual detection and routing code!
# The base class handles it automatically
```

## Summary

**Why automatic?**

✅ **DRY**: Don't Repeat Yourself across agents
✅ **Consistency**: All agents behave the same way
✅ **Maintainability**: Fix bugs once, all agents benefit
✅ **Extensibility**: Add new tools, all agents get them
✅ **Focus**: Agents focus on domain logic, not plumbing

**How?**

1. Inherit from `ToolAwareAgent` instead of `BaseSpecialistAgent`
2. Call `process_query_with_tools()` to get automatic routing
3. Use tool results without worrying about detection/routing
4. Tools are injected via registry (already set up!)

**Result:**
- 50+ lines of boilerplate → 0 lines
- Every agent automatically gets intelligent tool routing
- Add new tools → all agents benefit immediately
