"""
Financial Risk Agent

Specialist agent for financial risk assessment and analysis.
"""

from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path
from loguru import logger

from karamba.agents.base import AgentCapability, AgentMetadata, ApprovalPolicy
from karamba.agents.tool_aware import ToolAwareAgent
from karamba.core.models import AgentRequest, AgentResponse, PhaseResult, PhaseType, PhaseStatus
from karamba.core.phase_engine import PhaseEngine, Phase
from karamba.core.meta_prompt import build_financial_risk_prompt, FINANCIAL_DOMAIN_KNOWLEDGE
from karamba.document import VectorRetriever, DocumentProcessor, TextChunker
from karamba.llm import BaseLLM, create_llm, LLMConfig
from karamba.tools.search import WebSearchService
from karamba.tools.search.duckduckgo import DuckDuckGoProvider


class FinancialRiskAgent(ToolAwareAgent):
    """
    Specialist agent for financial risk assessment and analysis.

    Capabilities:
    - Financial risk analysis
    - Portfolio assessment
    - Risk metrics calculation
    - Investment evaluation
    """

    def __init__(
        self,
        agent_id: str = "financial_risk_agent",
        llm_config: Optional[LLMConfig] = None,
        reasoning_llm_config: Optional[LLMConfig] = None,
        vector_store_path: str = "./vector_store",
        enable_reflection: bool = False,
        # Automatic tool injection via ToolAwareAgent
        search_service: Optional[WebSearchService] = None,
        dataframe_tool=None,
        code_executor=None,
        financial_metrics=None,
        upload_dir: str = "./data/uploads"
    ):
        # Initialize ToolAwareAgent with automatic tool support
        super().__init__(
            agent_id=agent_id,
            enable_reflection=enable_reflection,
            search_service=search_service,
            dataframe_tool=dataframe_tool,
            code_executor=code_executor,
            financial_metrics=financial_metrics,
            upload_dir=upload_dir
        )

        # Initialize default LLM (Llama for fast operations)
        if llm_config is None:
            llm_config = LLMConfig(
                provider="ollama",
                model="llama3.2:latest"
            )

        self.llm = create_llm(llm_config)

        # Initialize reasoning LLM (Claude for complex reasoning)
        # Falls back to default LLM if not provided or if API key is missing
        self.reasoning_llm = None
        if reasoning_llm_config is not None:
            try:
                self.reasoning_llm = create_llm(reasoning_llm_config)
                logger.info(f"Reasoning LLM initialized: {reasoning_llm_config.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize reasoning LLM: {e}. Using default LLM.")
                self.reasoning_llm = None

        # Initialize document processing components
        self.retriever = VectorRetriever(persist_directory=vector_store_path)
        self.processor = DocumentProcessor()
        self.chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        # Backward compatibility: create search service if not provided
        if self.search_service is None:
            self.search_service = WebSearchService()
            ddg_provider = DuckDuckGoProvider()
            self.search_service.register_provider(ddg_provider, set_as_default=True)
            logger.info("Created local web search service (fallback)")

        # Initialize specialized phase engine for financial analysis
        self.phase_engine = self._create_financial_phases()

        # Log available tools (from ToolAwareAgent)
        available_tools = self.get_available_tools()
        logger.info(f"FinancialRiskAgent initialized with tools: {available_tools}")

    def _create_financial_phases(self) -> PhaseEngine:
        """Create specialized phases for financial risk assessment with enhanced quality controls."""
        engine = PhaseEngine(self.llm)

        # Phase 0: Industry Benchmarking (Research Excellence)
        benchmark_phase = Phase(
            name="benchmarking",
            phase_type=PhaseType.PLANNING,
            prompt_template="""You are a financial risk assessment specialist. Before analyzing the specific query, establish industry standards and best practices.

Query: {query}

TASK: Research what constitutes excellent financial risk analysis for this type of query.

1. **Industry Standards**:
   - What frameworks are typically used? (Basel III, COSO ERM, ISO 31000, etc.)
   - What key metrics and ratios are standard?
   - What regulatory requirements apply?

2. **Best Practices**:
   - How do leading financial institutions approach this type of analysis?
   - What level of detail and rigor is expected?
   - What common pitfalls should be avoided?

3. **Quality Criteria**:
   - What makes a financial risk assessment "excellent"?
   - What evidence and documentation standards apply?
   - What peer review or validation processes are typical?

Provide a benchmark framework that will guide our analysis to meet or exceed industry standards.""",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 200}
        )

        # Phase 1: Financial Context Analysis & Task Decomposition
        context_phase = Phase(
            name="financial_context",
            phase_type=PhaseType.PLANNING,
            prompt_template="""You are a financial risk assessment specialist. Analyze this query and decompose it into specific, actionable tasks.

Query: {query}
Available documents: {document_list}
Industry Benchmarks: {benchmarking_output}

**CONTEXT ANALYSIS**:
1. Type of analysis required (risk assessment, portfolio evaluation, due diligence, etc.)
2. Key stakeholders and their concerns
3. Regulatory and compliance considerations
4. Time horizon and market conditions

**TASK DECOMPOSITION**:
Break down the analysis into specific tasks:

A. **Data Requirements**:
   - What financial data must be extracted?
   - What metrics need to be calculated?
   - What ratios and indicators are required?

B. **Risk Categories to Assess**:
   - Market risk (price volatility, correlation)
   - Credit risk (default probability, exposure)
   - Liquidity risk (funding, market liquidity)
   - Operational risk (processes, systems, people)
   - Regulatory/compliance risk

C. **Analysis Tasks**:
   - Quantitative analysis steps
   - Qualitative assessment steps
   - Comparative analysis requirements
   - Scenario/stress testing needs

D. **Validation Tasks**:
   - What checks are needed?
   - What assumptions must be tested?
   - What alternative viewpoints should be considered?

Provide a clear, structured analysis plan with prioritized tasks and success criteria for each.""",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 250}
        )

        # Phase 2: Web Search (for current market data and news)
        web_search_phase = Phase(
            name="web_search",
            phase_type=PhaseType.RETRIEVAL,
            prompt_template="""Based on the financial context analysis, identify key search queries for current market information.

Query: {query}
Financial Context: {financial_context_output}

Generate 2-3 focused search queries to find:
- Current market conditions and trends
- Recent news affecting the entity/sector
- Latest financial data and metrics
- Regulatory updates or changes
- Industry comparisons and benchmarks

Output the search queries as a numbered list, one per line.""",
            verification_rules=["not_empty"]
        )

        # Phase 3: Data Retrieval (from uploaded documents)
        retrieval_phase = Phase(
            name="financial_retrieval",
            phase_type=PhaseType.RETRIEVAL,
            prompt_template="""Based on the financial context analysis, retrieve relevant financial data.

Query: {query}
Financial Context: {financial_context_output}

This phase retrieves relevant financial information, metrics, and risk indicators from documents.""",
            verification_rules=["not_empty"]
        )

        # Phase 4: Risk Assessment with Meta-Prompting & Consensus
        # Note: The actual meta-prompt is built dynamically in process_query
        # Use reasoning LLM (Claude) if available for better analysis
        risk_phase = Phase(
            name="risk_assessment",
            phase_type=PhaseType.REASONING,
            prompt_template="{risk_meta_prompt}",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 400},
            llm=self.reasoning_llm  # Use Claude for complex reasoning
        )

        # Phase 5: Quality Validation Loop
        # Use reasoning LLM (Claude) if available for thorough validation
        validation_phase = Phase(
            name="validation",
            phase_type=PhaseType.REASONING,
            prompt_template="""Validate the quality and completeness of the financial risk assessment.

Benchmarks: {benchmarking_output}
Analysis Plan: {financial_context_output}
Risk Assessment: {risk_assessment_output}

**VALIDATION CHECKLIST**:

1. **Completeness Check**:
   - ✓ Are all tasks from the analysis plan addressed?
   - ✓ Are all required risk categories covered?
   - ✓ Are quantitative and qualitative aspects balanced?

2. **Evidence Quality**:
   - ✓ Are all claims supported by document citations?
   - ✓ Is the data analysis rigorous and accurate?
   - ✓ Are calculations and metrics properly derived?

3. **Benchmark Compliance**:
   - ✓ Does the analysis meet industry standards?
   - ✓ Are best practices followed?
   - ✓ Is the level of rigor appropriate?

4. **Logic & Consistency**:
   - ✓ Are conclusions logically derived from evidence?
   - ✓ Are different sections consistent with each other?
   - ✓ Are assumptions clearly stated and reasonable?

5. **Red Flags & Gaps**:
   - Any contradictions or inconsistencies?
   - Missing data or analysis gaps?
   - Unsupported assumptions or claims?
   - Areas needing further investigation?

6. **Actionability**:
   - Are recommendations specific and actionable?
   - Is the risk rating clearly justified?
   - Can stakeholders act on this information?

**OUTPUT**:
- Overall Quality Score: [Excellent / Good / Acceptable / Needs Improvement]
- Key Strengths: (What's done well)
- Areas for Enhancement: (What could be improved)
- Critical Gaps: (What's missing)
- Final Validation Status: [APPROVED / APPROVED WITH NOTES / NEEDS REVISION]

If validation fails, specify exactly what needs to be corrected.""",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 200},
            llm=self.reasoning_llm  # Use Claude for quality validation
        )

        # Add all phases to engine in order
        engine.add_phase(benchmark_phase)
        engine.add_phase(context_phase)
        engine.add_phase(web_search_phase)
        engine.add_phase(retrieval_phase)
        engine.add_phase(risk_phase)
        engine.add_phase(validation_phase)

        return engine

    @property
    def metadata(self) -> AgentMetadata:
        """Return metadata describing this agent's capabilities"""
        return AgentMetadata(
            name="Financial Risk Analyst",
            description="Specialist agent for financial risk assessment, portfolio analysis, and investment evaluation with multi-perspective consensus analysis",
            capabilities=[
                AgentCapability.FINANCIAL_ANALYSIS,
                AgentCapability.RISK_ASSESSMENT
            ],
            keywords=[
                "risk", "financial", "investment", "portfolio", "return",
                "volatility", "sharpe", "var", "value at risk", "equity",
                "stock", "bonds", "assets", "liabilities", "credit",
                "market risk", "diversification", "exposure", "performance"
            ],
            example_queries=[
                "Assess the financial risk of this equity portfolio",
                "What are the key risk factors in these investment documents?",
                "Evaluate the credit risk of this company",
                "Analyze the volatility and return profile of these assets",
                "What is the overall risk rating for this investment?"
            ],
            approval_policy=ApprovalPolicy(
                requires_approval=False,  # Run automatically, only request approval when needed
                approval_triggers=[
                    # Trigger approval for actionable recommendations
                    "recommend buying", "recommend selling", "should buy", "should sell",
                    "allocate", "divest", "invest in", "avoid investing"
                ],
                risky_actions=[
                    "portfolio_change", "financial_recommendation", "investment_advice",
                    "risk_calculation", "financial_decision"
                ]
            )
        )

    async def process_query(
        self,
        request: AgentRequest,
        session_context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a financial risk query.

        Args:
            request: The incoming agent request
            session_context: Optional session context

        Returns:
            AgentResponse with financial risk assessment
        """
        logger.info(f"FinancialRiskAgent processing query: {request.query}")

        # 🎯 AUTOMATIC TOOL ROUTING - Get tools based on query and documents
        tool_results = await self.process_query_with_tools(request)
        logger.info(f"Automatic tool routing used: {list(tool_results.keys())}")

        # Build context
        context = {
            "query": request.query,
            "document_list": ", ".join(request.document_ids) if request.document_ids else "All financial documents",
            "session_id": request.session_id,
            # Include automatic tool results
            "tool_results": tool_results
        }

        # If dataframe tool was used, include summary in context
        if "dataframe" in tool_results:
            context["data_summary"] = tool_results["dataframe"]["summary"]
            logger.info("DataFrameTool results available in context")

        # If web search was used, include results in context
        if "web_search" in tool_results:
            context["web_info"] = tool_results["web_search"]["results"]
            logger.info("Web search results available in context")

        phase_results = []
        final_answer = ""
        citations = []

        # Execute phases
        async for result in self.phase_engine.execute_phases(context):
            phase_results.append(result)

            # Special handling for web search phase
            if result.phase_name == "web_search" and result.status == PhaseStatus.COMPLETED:
                # Extract search queries from LLM output
                search_queries_text = result.output
                logger.info(f"Web search queries generated: {search_queries_text[:200]}")

                # Parse search queries (expect numbered list)
                search_queries = []
                for line in search_queries_text.split('\n'):
                    line = line.strip()
                    # Match lines like "1. query text" or "- query text"
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Remove numbering/bullets
                        query_text = line.lstrip('0123456789.-•').strip()
                        if query_text:
                            search_queries.append(query_text)

                # Perform web searches
                web_results_combined = []
                for search_query in search_queries[:3]:  # Limit to top 3 queries
                    logger.info(f"Performing web search: {search_query}")
                    search_results = await self.search_service.search(
                        search_query,
                        max_results=3
                    )
                    web_results_combined.extend(search_results)

                # Format web search results for context
                if web_results_combined:
                    web_context = self.search_service.format_results(web_results_combined)
                    context["web_search_results"] = web_context
                    logger.info(f"Web search completed: {len(web_results_combined)} results")
                else:
                    context["web_search_results"] = "No web search results available."
                    logger.warning("Web search returned no results")

                # Store web results in metadata
                result.metadata["search_results"] = [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.snippet[:150] + "..."
                    }
                    for r in web_results_combined[:5]
                ]

            # Special handling for retrieval phase
            if result.phase_name == "financial_retrieval" and result.status == PhaseStatus.COMPLETED:
                # Perform actual retrieval with emphasis on financial terms
                # Only retrieve from documents linked to this session
                retrieved = self.retriever.retrieve(
                    request.query,
                    top_k=5,
                    document_ids=request.document_ids if request.document_ids else None
                )

                # Format retrieved chunks
                retrieved_context = "\n\n".join([
                    f"[Source: {chunk.chunk.document_id}, Relevance: {chunk.score:.2f}]\n{chunk.chunk.content}"
                    for chunk in retrieved
                ])

                context["retrieved_context"] = retrieved_context
                context["retrieved_chunks"] = retrieved

                # Update result with retrieved chunks
                result.metadata["chunks"] = [
                    {
                        "content": chunk.chunk.content[:200] + "...",
                        "document_id": chunk.chunk.document_id,
                        "score": chunk.score
                    }
                    for chunk in retrieved
                ]

                # Extract citations
                citations = result.metadata["chunks"]

                # Build meta-prompt for risk assessment using retrieved context and web results
                logger.info("Building meta-prompt for risk assessment phase")

                # Combine document context with web search results
                full_context = retrieved_context
                if context.get("web_search_results"):
                    full_context += "\n\n## Current Market Information (Web Search)\n\n"
                    full_context += context["web_search_results"]

                context["risk_meta_prompt"] = build_financial_risk_prompt(
                    query=request.query,
                    retrieved_context=full_context,
                    benchmarks=context.get("benchmarking_output", ""),
                    analysis_plan=context.get("financial_context_output", ""),
                    perspective="balanced"
                )
                logger.info(f"Meta-prompt built: {len(context['risk_meta_prompt'])} characters")

            # Store risk assessment for final assembly
            if result.phase_name == "risk_assessment" and result.status == PhaseStatus.COMPLETED:
                context["risk_assessment"] = result.output

            # Extract validation results and assemble final answer
            if result.phase_name == "validation" and result.status == PhaseStatus.COMPLETED:
                validation_output = result.output
                risk_assessment = context.get("risk_assessment", "")

                # Assemble comprehensive final answer
                final_answer = f"""# Financial Risk Assessment Report

## Executive Summary
{risk_assessment[:500]}...

---

## Detailed Risk Analysis
{risk_assessment}

---

## Quality Validation
{validation_output}

---

**Assessment Quality**: This analysis follows industry best practices and has been validated against established benchmarks.
**Methodology**: Multi-perspective consensus analysis with quantitative and qualitative assessment.
**Confidence**: All findings are supported by document citations and evidence-based reasoning.
"""

        # If validation didn't complete, use risk assessment directly
        if not final_answer and context.get("risk_assessment"):
            final_answer = context["risk_assessment"]

        # Build response
        response = AgentResponse(
            answer=final_answer,
            phase_results=phase_results,
            citations=citations,
            metadata={
                "agent_id": self.agent_id,
                "agent_type": "financial_risk",
                "phases_completed": len([r for r in phase_results if r.status == PhaseStatus.COMPLETED]),
                "validation_status": context.get("validation_status", "unknown")
            }
        )

        logger.info("FinancialRiskAgent completed query processing")
        return response

    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given query.

        Financial agent has high confidence for queries containing financial/risk keywords.

        Args:
            query: The user's query
            context: Optional context about the query

        Returns:
            Confidence score (0.0 to 1.0)
        """
        query_lower = query.lower()

        # Financial/risk-specific keywords
        high_confidence_keywords = [
            "risk", "financial risk", "investment risk", "portfolio risk",
            "credit risk", "market risk", "var", "value at risk"
        ]

        medium_confidence_keywords = [
            "financial", "investment", "portfolio", "equity", "stock",
            "bonds", "assets", "return", "volatility", "sharpe",
            "diversification", "exposure", "performance"
        ]

        # Check for high confidence matches
        for keyword in high_confidence_keywords:
            if keyword in query_lower:
                return 0.95

        # Check for medium confidence matches
        match_count = sum(1 for kw in medium_confidence_keywords if kw in query_lower)

        if match_count >= 3:
            return 0.9
        elif match_count >= 2:
            return 0.8
        elif match_count >= 1:
            return 0.7

        # Low confidence if no financial keywords
        return 0.2

    async def ingest_document(self, file_path: Path, file_content: Optional[bytes] = None):
        """Ingest a financial document into the system"""
        logger.info(f"Ingesting financial document: {file_path.name}")

        # Process document
        doc = await self.processor.process_file(file_path, file_content)

        # Chunk document
        chunks = self.chunker.chunk_text(doc.content, doc.filename)

        # Add to vector store
        self.retriever.add_chunks(chunks)

        logger.info(f"Financial document ingested: {doc.filename} ({len(chunks)} chunks)")
        return doc.filename

    def get_document_stats(self):
        """Get statistics about ingested financial documents"""
        return self.retriever.get_stats()

    def delete_document(self, document_id: str):
        """Delete a financial document from the system"""
        self.retriever.delete_document(document_id)
        logger.info(f"Financial document deleted: {document_id}")
