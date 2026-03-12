# Tools Usage Guide

## Overview

Karamba provides two types of computation tools:

1. **Pre-built Tools** - Fast, tested functions for common operations
2. **Code Executor** - Dynamic code generation for custom computations

## Architecture Decision Tree

```
Need to do a calculation?
│
├─ Is it a standard metric? (Sharpe, VaR, etc.)
│  └─ YES → Use FinancialMetrics (pre-built)
│     ✓ Faster
│     ✓ More reliable
│     ✓ No LLM overhead
│
└─ Is it custom/complex logic?
   └─ YES → Use PythonExecutor (dynamic)
      ✓ Flexible
      ✓ Handles unpredictable needs
      ✓ Agent generates code on demand
```

## 1. Pre-Built Financial Metrics

### Available Metrics

- **Risk**: Sharpe Ratio, Sortino Ratio, Volatility, VaR, Max Drawdown
- **Return**: Total Return, Annualized Return (CAGR)
- **Comparison**: Information Ratio

### Usage in Agent

```python
# In your agent's __init__
def __init__(self, financial_metrics=None):
    self.financial_metrics = financial_metrics

# In your agent's process_query
if self.financial_metrics:
    # Calculate Sharpe ratio
    result = self.financial_metrics.sharpe_ratio(
        returns=[0.01, 0.02, -0.01, 0.03],
        risk_free_rate=0.02
    )
    sharpe = result.value  # 1.234
    metadata = result.metadata  # {'annualized_return': ..., 'annualized_volatility': ...}

    # Calculate VaR
    var_result = self.financial_metrics.value_at_risk(
        returns=[...],
        confidence_level=0.95,
        investment_value=1000000
    )
```

### Example: Adding to an Agent

```python
# In main.py
financial_agent = FinancialRiskAgent(
    financial_metrics=tool_registry.get_financial_metrics(),
    code_executor=tool_registry.get_code_executor()
)
```

## 2. Python Code Executor

### When to Use

- Custom calculations not in pre-built metrics
- Complex data transformations
- Agent needs to generate logic based on user query
- Scenario analysis or simulations

### Safety Features

- ✅ Restricted imports (only safe libraries: numpy, pandas, math, etc.)
- ✅ Forbidden operations (no file I/O, no eval/exec)
- ✅ AST validation before execution
- ✅ Output size limits
- ✅ Timeout protection

### Usage in Agent

```python
# Simple expression
result = code_executor.execute_expression(
    "math.sqrt(16) + 5",
    variables={"x": 10}
)
print(result.result)  # 9.0

# Full code execution
code = '''
import numpy as np

returns = np.array(data)
mean_return = np.mean(returns)
std_return = np.std(returns)
sharpe = mean_return / std_return
print(f"Sharpe: {sharpe}")
'''

result = code_executor.execute(
    code,
    variables={"data": [0.01, 0.02, -0.01]},
    return_variable="sharpe"
)
print(result.stdout)  # "Sharpe: 0.577"
print(result.result)  # 0.577
```

### Agent Integration Pattern

```python
async def process_query(self, request):
    # Agent decides it needs custom calculation
    if "custom_metric" in query.lower():
        # Agent generates Python code using LLM
        code = await self.llm.generate(
            messages=[{"role": "user", "content": f"Generate Python code to: {request.query}"}]
        )

        # Execute safely
        result = self.code_executor.execute(code.content)

        if result.success:
            return f"Result: {result.result}"
        else:
            return f"Calculation failed: {result.error}"
```

## 3. Hybrid Approach Example

```python
class SmartFinancialAgent:
    def __init__(self, financial_metrics, code_executor):
        self.metrics = financial_metrics
        self.executor = code_executor

    async def calculate(self, metric_name: str, data: dict):
        # Try pre-built metrics first (faster)
        if metric_name == "sharpe_ratio":
            return self.metrics.sharpe_ratio(data['returns'])

        elif metric_name == "volatility":
            return self.metrics.volatility(data['returns'])

        # Fall back to code executor for custom metrics
        else:
            code = f'''
import numpy as np
# Agent-generated code for custom metric
result = custom_calculation(data)
'''
            return self.executor.execute(code, variables={"data": data})
```

## 4. Available Tools in Registry

```python
# Get all available tools
tools = tool_registry.list_tools()
# ['web_search', 'code_executor', 'financial_metrics']

# Access tools
web_search = tool_registry.get_web_search()
code_executor = tool_registry.get_code_executor()
financial_metrics = tool_registry.get_financial_metrics()
```

## 5. Best Practices

### Use Pre-Built When Possible
```python
# ✅ GOOD - Use pre-built
sharpe = financial_metrics.sharpe_ratio(returns)

# ❌ BAD - Generate code unnecessarily
code = "def calc_sharpe(returns): ..."
result = code_executor.execute(code)
```

### Use Code Executor for Flexibility
```python
# ✅ GOOD - Custom logic
code = '''
import pandas as pd
df = pd.DataFrame(data)
result = df.groupby('sector').apply(custom_analysis)
'''

# ❌ BAD - Try to pre-build every possible metric
# (Too rigid, can't handle unexpected queries)
```

### Error Handling
```python
# Always check execution results
result = code_executor.execute(code)
if not result.success:
    logger.error(f"Execution failed: {result.error}")
    # Fall back to alternative approach
```

## 6. Adding New Tools

### Add Pre-Built Tool
```python
# In tools/finance/metrics.py
def my_custom_metric(self, data):
    # Your calculation
    return MetricResult(value=result, metric_name="custom")
```

### Register New Tool
```python
# In tools/registry.py create_tool_registry()
my_tool = MyCustomTool()
registry.register_tool("my_tool", my_tool)
```

## Summary

| Tool Type | Use Case | Speed | Flexibility | Safety |
|-----------|----------|-------|-------------|--------|
| **FinancialMetrics** | Standard calculations | ⚡ Fast | Limited | ✅ Very Safe |
| **CodeExecutor** | Custom/dynamic needs | 🐢 Slower | 🎨 High | ⚠️ Sandboxed |
| **Web Search** | Current information | 🌐 Network | 🔍 Search | ✅ Safe |

**Recommendation**: Use pre-built tools when possible, fall back to code executor for custom needs.
