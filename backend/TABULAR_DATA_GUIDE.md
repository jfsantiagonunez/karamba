# Tabular Data Best Practices

## ❌ Don't: Send Full Tables to LLM

```python
# BAD - Expensive, hits token limits, hallucination risk
df = pd.read_excel("large_file.xlsx")
response = llm.generate(f"Analyze this: {df.to_string()}")
```

**Problems:**
- 10,000 rows × 20 columns = 200K+ tokens ($$$)
- Claude/Llama context limits (200K tokens)
- LLM might hallucinate numbers
- Slow (multiple API calls)

## ✅ Do: Use DataFrameTool + Summaries

```python
# GOOD - Fast, accurate, LLM-friendly
df_tool = tool_registry.get_dataframe_tool()

# Load data
result = df_tool.load_excel("portfolio.xlsx")

# Get LLM-friendly summary (NOT the full table!)
summary = df_tool.get_summary()
# "DataFrame: main
#  Rows: 10,000
#  Columns: 20
#  Column Types:
#    - symbol: object
#    - price: float64
#    - volume: int64
#  Numeric Ranges:
#    - price: 10.50 to 450.25 (mean: 125.33)"

# LLM works with summary, NOT raw data
response = llm.generate(f"Based on this summary: {summary.summary}, what should I analyze?")
```

## Architecture Pattern: **Hybrid Approach**

### 1. Use DataFrameTool for Standard Operations

```python
# Load Excel
df_tool.load_excel("financials.xlsx", sheet_name="Income Statement")

# Filter (no LLM needed!)
result = df_tool.filter_rows(
    column="sector",
    value="Technology",
    condition="equals"
)

# Aggregate (no LLM needed!)
result = df_tool.aggregate(
    group_by="sector",
    agg_column="revenue",
    agg_function="sum"
)

# Get statistics
stats = df_tool.get_statistics(columns=["revenue", "profit"])
```

### 2. Use Code Executor for Custom Analysis

```python
# When pre-built operations aren't enough
code = '''
import pandas as pd

# Calculate custom metric
df['profit_margin'] = (df['profit'] / df['revenue']) * 100

# Complex filtering
high_margin = df[df['profit_margin'] > 20]

result = high_margin[['company', 'profit_margin']].head(10)
'''

result = df_tool.execute_custom_analysis(code, df_name="main")
```

### 3. LLM Only for Understanding Intent

```python
# User query: "Show me tech companies with high revenue"

# Step 1: LLM understands intent
intent = llm.generate("Extract: sector and threshold from 'Show me tech companies with high revenue'")
# -> sector="Technology", metric="revenue", condition="high"

# Step 2: Tool does the actual work (no LLM!)
result = df_tool.filter_rows(column="sector", value="Technology", condition="equals")

# Step 3: LLM formats the answer
summary = f"Found {len(result.data)} tech companies"
response = llm.generate(f"Format this result naturally: {summary}")
```

## Example: Financial Portfolio Analysis

```python
class FinancialAgent:
    def __init__(self, df_tool, financial_metrics):
        self.df_tool = df_tool
        self.metrics = financial_metrics

    async def analyze_portfolio(self, excel_file: str):
        # Step 1: Load data (tool)
        result = self.df_tool.load_excel(excel_file)

        if not result.success:
            return f"Error loading: {result.error}"

        # Step 2: Get summary for LLM context
        summary = self.df_tool.get_summary()

        # Step 3: LLM decides what to analyze
        analysis_plan = await self.llm.generate(f'''
        Portfolio summary:
        {summary.summary}

        What analysis should I perform?
        ''')

        # Step 4: Execute analysis WITHOUT sending raw data to LLM

        # Calculate returns (tool, no LLM!)
        returns_code = '''
        df['daily_return'] = df['price'].pct_change()
        result = df['daily_return'].tolist()
        '''
        returns_result = self.df_tool.execute_custom_analysis(returns_code)

        # Calculate Sharpe (pre-built, no LLM!)
        sharpe = self.metrics.sharpe_ratio(returns_result.result)

        # Step 5: LLM formats final answer
        response = await self.llm.generate(f'''
        Present these findings:
        - Portfolio has {summary.metadata['rows']} positions
        - Sharpe Ratio: {sharpe.value:.2f}
        ''')

        return response
```

## Decision Tree

```
User asks about Excel data
│
├─ Need to LOAD file?
│  └─ Use: df_tool.load_excel() or df_tool.load_csv()
│
├─ Need to UNDERSTAND what user wants?
│  └─ Use: LLM with summary (NOT full data!)
│
├─ Need STANDARD operation? (filter, aggregate, stats)
│  └─ Use: df_tool pre-built methods
│     ✓ Fast (no code generation)
│     ✓ Reliable (tested)
│     ✓ No LLM cost
│
├─ Need CUSTOM analysis?
│  └─ Use: df_tool.execute_custom_analysis() + code executor
│     - LLM generates pandas code
│     - Code executor runs it safely
│     - Returns result (NOT full table!)
│
└─ Need to FORMAT result?
   └─ Use: LLM with summary/aggregated data (NOT raw rows!)
```

## Anti-Patterns to Avoid

### ❌ Sending Raw Data to LLM
```python
# BAD
df = pd.read_excel("big_file.xlsx")
llm.generate(f"Analyze: {df.to_csv()}")  # 💸💸💸
```

### ❌ Generating Code for Simple Operations
```python
# BAD - Why generate code for this?
code = llm.generate("Write code to filter df where sector=='Tech'")
exec(code)

# GOOD - Use pre-built operation
df_tool.filter_rows(column="sector", value="Tech")
```

### ❌ Multiple Round Trips for Standard Ops
```python
# BAD
llm_call_1: "What columns exist?"
llm_call_2: "Filter by column X"
llm_call_3: "Calculate average"

# GOOD - Direct operations
summary = df_tool.get_summary()  # Gets all info at once
filtered = df_tool.filter_rows(...)
stats = df_tool.get_statistics(...)
```

## Performance Comparison

| Approach | Speed | Cost | Accuracy |
|----------|-------|------|----------|
| **Send full table to LLM** | 🐢 30s+ | 💰💰💰 $2-10 | ⚠️ May hallucinate |
| **DataFrameTool (pre-built)** | ⚡ <100ms | 💰 $0 | ✅ 100% accurate |
| **Code Executor (custom)** | 🏃 1-3s | 💰 $0.01 | ✅ Accurate (if code is correct) |
| **Hybrid (tool + LLM summary)** | ⚡ <1s | 💰 $0.01-0.05 | ✅ Best of both |

## Summary

**Best Practice: Hybrid Approach**

1. ✅ **Load with tool**: `df_tool.load_excel()`
2. ✅ **Get summary for LLM**: `df_tool.get_summary()` (NOT raw data!)
3. ✅ **Standard ops with tool**: `filter_rows()`, `aggregate()`, `get_statistics()`
4. ✅ **Custom ops with executor**: `execute_custom_analysis(code)`
5. ✅ **LLM for understanding & formatting**: Work with summaries, not raw tables

**Never:**
- ❌ Send full tables to LLM
- ❌ Generate code for standard operations
- ❌ Trust LLM with numerical calculations

**Tool Registration:**
```python
# Automatically registered in tool registry
df_tool = tool_registry.get_dataframe_tool()

# Pass to agents
financial_agent = FinancialRiskAgent(
    dataframe_tool=df_tool
)
```
