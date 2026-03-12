"""Core Karamba agent implementation."""
from pathlib import Path
from typing import AsyncIterator, List, Optional
from loguru import logger

from ..llm import BaseLLM, LLMMessage, create_llm, LLMConfig
from ..document import VectorRetriever, DocumentProcessor, TextChunker
from .phase_engine import PhaseEngine, Phase
from .models import (
    AgentRequest, AgentResponse, PhaseResult, PhaseType,
    ResearchPlan, PhaseStatus
)


class KarambaAgent:
    """Main Karamba research assistant agent."""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        reasoning_llm_config: Optional[LLMConfig] = None,
        vector_store_path: str = "./vector_store",
        config_path: Optional[Path] = None
    ):
        self.llm = create_llm(llm_config)
        self.retriever = VectorRetriever(persist_directory=vector_store_path)
        self.processor = DocumentProcessor()
        self.chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        # Initialize reasoning LLM (Claude for complex analysis)
        self.reasoning_llm = None
        if reasoning_llm_config is not None:
            try:
                self.reasoning_llm = create_llm(reasoning_llm_config)
                logger.info(f"Reasoning LLM initialized: {reasoning_llm_config.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize reasoning LLM: {e}. Using default LLM.")
                self.reasoning_llm = None

        # Initialize phase engine
        if config_path:
            self.phase_engine = PhaseEngine(self.llm, config_path)
        else:
            self.phase_engine = self._create_default_phases()

        logger.info("Karamba agent initialized")
    
    def _create_default_phases(self) -> PhaseEngine:
        """Create default research assistant phases."""
        engine = PhaseEngine(self.llm)
        
        # Phase 1: Planning
        planning_phase = Phase(
            name="planning",
            phase_type=PhaseType.PLANNING,
            prompt_template="""You are a research assistant. Analyze this question and create a research plan.

Question: {query}

Available documents: {document_list}

Create a structured research plan:
1. Break down the question into sub-questions
2. Identify which documents are most relevant
3. Outline the approach to answer the question

Provide your plan in a clear, structured format.""",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 100}
        )
        
        # Phase 2: Retrieval
        retrieval_phase = Phase(
            name="retrieval",
            phase_type=PhaseType.RETRIEVAL,
            prompt_template="""Based on the research plan, we need to retrieve relevant information.

Query: {query}
Research Plan: {planning_output}

This phase retrieves relevant document chunks.""",
            verification_rules=["not_empty"]
        )
        
        # Phase 3: Reasoning (use Claude if available for complex analysis)
        reasoning_phase = Phase(
            name="reasoning",
            phase_type=PhaseType.REASONING,
            prompt_template="""You are analyzing information to answer a user's question. You have access to multiple sources of information.

Question: {query}

Retrieved Information:
{retrieved_context}

{dataframe_section}

{web_search_section}

**Instructions:**
When tabular data is provided above, analyze it thoroughly:
- Describe the structure (rows, columns, data types)
- Identify key patterns, trends, or insights
- Note any financial metrics, scenarios, or calculations present
- Explain what the data represents and its business context

Provide a comprehensive answer based on ALL the information above. Include:
1. Direct answer to the question
2. Supporting evidence from the documents and data
3. Specific insights from any tabular data
4. Any limitations or caveats
5. Relevant citations""",
            verification_rules=["not_empty", "min_length"],
            config={"min_length": 200},
            llm=self.reasoning_llm  # Use Claude for complex reasoning
        )
        
        engine.add_phase(planning_phase)
        engine.add_phase(retrieval_phase)
        engine.add_phase(reasoning_phase)
        
        return engine
    
    async def ingest_document(
        self,
        file_path: Path,
        file_content: Optional[bytes] = None
    ) -> str:
        """Ingest a document into the system."""
        logger.info(f"Ingesting document: {file_path.name}")
        
        # Process document
        doc = await self.processor.process_file(file_path, file_content)
        
        # Chunk document
        chunks = self.chunker.chunk_text(doc.content, doc.filename)
        
        # Add to vector store
        self.retriever.add_chunks(chunks)
        
        logger.info(f"Document ingested: {doc.filename} ({len(chunks)} chunks)")
        return doc.filename
    
    async def query(self, request: AgentRequest) -> AsyncIterator[PhaseResult]:
        """Process a query through the agent pipeline."""
        logger.info(f"Processing query: {request.query}")

        # Build context
        context = {
            "query": request.query,
            "document_list": ", ".join(request.document_ids) if request.document_ids else "All documents",
            "session_id": request.session_id
        }

        # Add tool results to context if available (from ToolAwareAgent)
        if "tool_results" in request.config:
            tool_results = request.config["tool_results"]
            logger.info(f"Adding tool results to context: {list(tool_results.keys())}")

            # Build DataFrame section for prompt
            if "dataframe" in tool_results:
                context["dataframe_section"] = f"""
Tabular Data Analysis (Automatic Tool):
{tool_results["dataframe"]["summary"]}

The above summary describes the structure and content of the uploaded tabular file(s).
Use this information to answer questions about the data.
"""
                logger.info(f"Added DataFrame summary to context ({len(tool_results['dataframe']['summary'])} chars)")
            else:
                context["dataframe_section"] = ""

            # Build web search section for prompt
            if "web_search" in tool_results:
                context["web_search_section"] = f"""
Current Web Information (Automatic Tool):
{tool_results["web_search"]["results"]}

The above information was retrieved from web search to provide current context.
"""
                logger.info(f"Added web search results to context")
            else:
                context["web_search_section"] = ""

            # Track which tools were used
            context["tool_results_available"] = list(tool_results.keys())
        else:
            # No tool results available
            context["dataframe_section"] = ""
            context["web_search_section"] = ""
        
        phase_results = []
        
        async for result in self.phase_engine.execute_phases(context):
            phase_results.append(result)
            
            # Special handling for retrieval phase
            if result.phase_name == "retrieval" and result.status == PhaseStatus.COMPLETED:
                # Perform actual retrieval - only from documents linked to this session
                retrieved = self.retriever.retrieve(
                    request.query,
                    top_k=5,
                    document_ids=request.document_ids if request.document_ids else None
                )
                
                # Format retrieved chunks for context
                retrieved_context = "\n\n".join([
                    f"[Source: {chunk.chunk.document_id}, Score: {chunk.score:.2f}]\n{chunk.chunk.content}"
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
            
            yield result
        
        logger.info("Query processing complete")
    
    async def answer_question(self, request: AgentRequest) -> AgentResponse:
        """Get complete answer to a question."""
        phase_results = []
        final_answer = ""
        citations = []

        async for result in self.query(request):
            phase_results.append(result)
            logger.info(f"Phase result: {result.phase_name}, status: {result.status}, output length: {len(result.output) if result.output else 0}")

            # Extract final answer from reasoning phase
            if result.phase_name == "reasoning" and result.status == PhaseStatus.COMPLETED:
                final_answer = result.output
                logger.info(f"Extracted final answer from reasoning phase: {len(final_answer)} chars")
                logger.info(f"Final answer preview: {final_answer[:200] if final_answer else '(empty)'}")

                # Extract citations from retrieved chunks
                if "retrieved_chunks" in result.metadata:
                    citations = result.metadata["chunks"]

        logger.info(f"Returning answer: {len(final_answer)} chars, {len(citations)} citations")
        return AgentResponse(
            answer=final_answer,
            phase_results=phase_results,
            citations=citations
        )
    
    def get_document_stats(self) -> dict:
        """Get statistics about ingested documents."""
        return self.retriever.get_stats()
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document from the system."""
        self.retriever.delete_document(document_id)
        logger.info(f"Document deleted: {document_id}")