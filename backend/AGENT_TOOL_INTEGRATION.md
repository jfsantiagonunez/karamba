# Agent & Tool Integration Guide

## Problem: How Should Agents Use DataFrameTool?

When a user uploads `portfolio.xlsx`, should the agent:
1. **Auto-detect** and use DataFrameTool? (✅ Recommended)
2. **Manually decide** based on query? (⚠️ Complex)
3. **Treat as text** and chunk it? (❌ Bad)

## ✅ Recommended: Intelligent Routing

### Architecture Overview

```
User uploads file
    ↓
DocumentProcessor detects type
    ↓
    ├─ PDF/DOCX → Extract text → Chunk → Vector Store → Agent uses retrieval
    │
    └─ Excel/CSV → Store file path → Metadata DB → Agent uses DataFrameTool
                                              ↓
                                        Agent sees both sources
                                              ↓
                                   Query decides which tool to use
```

### Implementation Pattern

#### 1. Document Processor (Detection)

```python
# In document processor
class ProcessedDocument:
    filename: str
    content: str  # For text docs
    doc_type: str
    is_tabular: bool = False  # NEW FLAG
    file_path: Optional[str] = None  # Store path for tabular files
    metadata: dict = {}

# Processing
if suffix in [".xlsx", ".xls", ".csv"]:
    # DON'T convert to text and chunk!
    return ProcessedDocument(
        filename=filename,
        content="",  # No text content
        doc_type="tabular",
        is_tabular=True,
        file_path=str(file_path),  # Keep file path
        metadata={
            "sheet_names": [...],
            "row_count": 10000,
            "column_count": 20
        }
    )
```

#### 2. Agent Integration (Automatic Routing)

```python
class FinancialRiskAgent:
    def __init__(self, dataframe_tool, financial_metrics, ...):
        self.df_tool = dataframe_tool
        self.metrics = financial_metrics
        # ... other tools

    async def process_query(self, request):
        # Check if session has tabular documents
        tabular_docs = self._get_tabular_documents(request.document_ids)
        text_docs = self._get_text_documents(request.document_ids)

        # SMART ROUTING based on document types
        if tabular_docs and self._query_needs_tabular_analysis(request.query):
            # Use DataFrameTool pathway
            return await self._analyze_tabular_data(request, tabular_docs)

        elif text_docs:
            # Use traditional retrieval pathway
            return await self._analyze_text_documents(request, text_docs)

        else:
            # Hybrid: use both!
            return await self._hybrid_analysis(request, tabular_docs, text_docs)

    def _query_needs_tabular_analysis(self, query: str) -> bool:
        """Detect if query requires tabular operations."""
        tabular_keywords = [
            "calculate", "aggregate", "sum", "average", "filter",
            "group by", "count", "max", "min", "statistics",
            "correlation", "portfolio", "returns", "sharpe"
        ]
        return any(kw in query.lower() for kw in tabular_keywords)

    async def _analyze_tabular_data(self, request, tabular_docs):
        """Handle queries on Excel/CSV files."""
        # Load data into DataFrameTool
        for doc in tabular_docs:
            result = self.df_tool.load_excel(doc.file_path)

        # Get summary for LLM (NOT raw data!)
        summary = self.df_tool.get_summary()

        # LLM decides what analysis to perform
        analysis_plan = await self.llm.generate(f'''
        Data summary: {summary.summary}
        User query: {request.query}

        What operations should I perform? Return as:
        - filter: column, value, condition
        - aggregate: group_by, agg_column, function
        - custom: pandas code
        ''')

        # Execute operations (no LLM needed here!)
        if "filter" in analysis_plan:
            result = self.df_tool.filter_rows(...)
        elif "aggregate" in analysis_plan:
            result = self.df_tool.aggregate(...)
        elif "custom" in analysis_plan:
            code = self._extract_code_from_plan(analysis_plan)
            result = self.df_tool.execute_custom_analysis(code)

        # Calculate financial metrics if needed
        if "sharpe" in request.query.lower():
            returns = result.data['returns'].tolist()
            sharpe = self.metrics.sharpe_ratio(returns)

        # LLM formats final answer (with results, not raw data!)
        return await self._format_response(result, sharpe)
```

#### 3. Metadata Storage

```python
# Store document metadata with type info
class DocumentMetadata:
    document_id: str
    filename: str
    doc_type: str  # "pdf", "docx", "tabular"
    is_tabular: bool
    file_path: Optional[str]  # For tabular files
    session_id: str
    uploaded_at: datetime

# When uploading
if doc.is_tabular:
    # Store file path, don't chunk
    store_tabular_metadata(doc)
else:
    # Chunk and store in vector DB
    chunks = chunker.chunk_text(doc.content)
    vector_store.add_chunks(chunks)
```

## Example Workflow

### Scenario: User uploads `portfolio.xlsx` and asks about risk

```python
# 1. Upload
user uploads "portfolio.xlsx"
    ↓
processor detects Excel file
    ↓
returns ProcessedDocument(is_tabular=True, file_path="...")
    ↓
stores metadata (NOT in vector store)

# 2. Query: "What's the Sharpe ratio of my portfolio?"
    ↓
agent sees: tabular_docs=["portfolio.xlsx"], text_docs=[]
    ↓
agent detects: query has "sharpe" + "portfolio" → needs tabular analysis
    ↓
agent route: _analyze_tabular_data()
    ↓
    ├─ Load: df_tool.load_excel("portfolio.xlsx")
    ├─ Summary: df_tool.get_summary() → "10K rows, columns: [date, price, returns]"
    ├─ LLM: "To calculate Sharpe, I need returns column"
    ├─ Extract: returns = df_tool.get_dataframe().['returns'].tolist()
    ├─ Calculate: sharpe = financial_metrics.sharpe_ratio(returns)
    └─ Format: "Your portfolio Sharpe ratio is 1.23..."
```

### Scenario: User uploads both PDF report and Excel data

```python
# User has: "annual_report.pdf" + "portfolio.xlsx"
# Query: "Based on the report and my portfolio, what's my risk?"

agent sees:
    tabular_docs = ["portfolio.xlsx"]
    text_docs = ["annual_report.pdf"]

agent route: _hybrid_analysis()
    ↓
    ├─ Text analysis: retrieval from PDF
    │   summary = retrieve_from_vector_store("risk factors")
    │
    └─ Tabular analysis: calculate from Excel
        df_tool.load_excel("portfolio.xlsx")
        sharpe = calculate_metrics()
    ↓
LLM combines both:
    "Based on the annual report's risk factors (interest rate risk, market volatility)
     and your portfolio's Sharpe ratio of 1.23, your risk level is..."
```

## Code Changes Needed

### 1. Update ProcessedDocument Model
```python
# backend/src/karamba/document/processor.py
class ProcessedDocument(BaseModel):
    filename: str
    content: str
    doc_type: str
    is_tabular: bool = False  # NEW
    file_path: Optional[str] = None  # NEW
    num_pages: Optional[int] = None
    metadata: dict = {}
```

### 2. Update Document Ingestion
```python
# backend/src/karamba/agents/financial.py
async def ingest_document(self, file_path: Path, file_content: Optional[bytes] = None):
    doc = await self.processor.process_file(file_path, file_content)

    if doc.is_tabular:
        # DON'T chunk tabular data!
        # Just store metadata
        logger.info(f"Tabular document: {doc.filename} - stored path only")
        return doc.filename
    else:
        # Traditional text document - chunk and store
        chunks = self.chunker.chunk_text(doc.content, doc.filename)
        self.retriever.add_chunks(chunks)
        logger.info(f"Text document ingested: {doc.filename} ({len(chunks)} chunks)")
        return doc.filename
```

### 3. Add Routing Logic to Agent
```python
# Add to FinancialRiskAgent
def __init__(self, ..., dataframe_tool=None):
    self.df_tool = dataframe_tool

async def process_query(self, request):
    # Detect document types in this session
    session_docs = self._get_session_documents(request.document_ids)

    if self._has_tabular_data(session_docs) and self._query_needs_structured_data(request.query):
        # Use DataFrameTool pathway
        return await self._process_tabular_query(request, session_docs)
    else:
        # Use traditional retrieval pathway
        return await self._process_text_query(request)
```

## Summary

**Answer to your question:**

> "Do we need changes to agents to make sure it uses that approach?"

**Yes, but minimal changes:**

1. ✅ **Document Processor**: Already detects Excel/CSV, just add `is_tabular` flag
2. ✅ **Agent**: Add routing logic to detect tabular vs. text documents
3. ✅ **Agent**: Use DataFrameTool when tabular documents present
4. ✅ **Agent**: Pass tools via dependency injection (already done!)

**The agent intelligently routes based on:**
- Document type (tabular vs. text)
- Query intent (structured analysis vs. text search)
- Available tools (DataFrameTool, retrieval, metrics)

**No manual delegation needed** - the agent figures it out automatically! 🎯
