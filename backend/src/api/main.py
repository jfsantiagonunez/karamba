"""FastAPI application for Karamba agent."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os
from dotenv import load_dotenv

from karamba.llm import LLMConfig, create_llm
from karamba.core.agent import KarambaAgent
from karamba.agents import ResearchAgent, FinancialRiskAgent, AgentRegistry, AgentRouter
from karamba.memory import SessionStore, ConversationOrchestrator
from karamba.tools import create_tool_registry
from api.dependencies import set_agent, set_session_store, set_orchestrator, set_router
from api.routes import agent, documents, websocket, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Karamba API with Multi-Agent System")

    # Load environment variables
    load_dotenv()

    # Initialize LLM configuration (Llama for fast operations)
    llm_config = LLMConfig(
        provider="ollama",
        model="llama3.2:3b",
        temperature=0.7
    )

    # Initialize reasoning LLM configuration (Claude for complex reasoning)
    # Only if ANTHROPIC_API_KEY is available in environment
    reasoning_llm_config = None
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        reasoning_llm_config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            temperature=0.7,
            api_key=anthropic_api_key
        )
        logger.info("Claude reasoning LLM configured for complex reasoning phases")
    else:
        logger.info("ANTHROPIC_API_KEY not found - using Llama for all phases")

    # Create LLM instance for router
    llm = create_llm(llm_config)

    # Initialize shared tool registry
    logger.info("Initializing shared tool registry...")
    tool_registry = create_tool_registry()
    logger.info(f"Tool registry initialized with tools: {tool_registry.list_tools()}")

    # Initialize Multi-Agent System
    logger.info("Initializing specialist agents...")

    # Get upload directory from environment
    upload_dir = os.getenv("UPLOAD_DIR", "./data/uploads")

    # Create specialist agents
    research_agent = ResearchAgent(
        agent_id="research_agent",
        llm_config=llm_config,
        reasoning_llm_config=reasoning_llm_config,  # Claude for complex reasoning (especially tabular data)
        vector_store_path="./data/vector_store",
        enable_reflection=False,
        # Automatic tool injection from registry
        search_service=tool_registry.get_web_search(),
        dataframe_tool=tool_registry.get_dataframe_tool(),
        code_executor=tool_registry.get_code_executor(),
        financial_metrics=tool_registry.get_financial_metrics(),
        upload_dir=upload_dir
    )

    financial_agent = FinancialRiskAgent(
        agent_id="financial_risk_agent",
        llm_config=llm_config,
        reasoning_llm_config=reasoning_llm_config,  # Claude for risk assessment & validation
        vector_store_path="./data/vector_store",
        enable_reflection=False,
        # Automatic tool injection from registry
        search_service=tool_registry.get_web_search(),
        dataframe_tool=tool_registry.get_dataframe_tool(),
        code_executor=tool_registry.get_code_executor(),
        financial_metrics=tool_registry.get_financial_metrics(),
        upload_dir=upload_dir
    )

    # Create agent registry and register agents
    registry = AgentRegistry()
    registry.register(research_agent)
    registry.register(financial_agent)

    # Create agent router with LLM-based intent classification
    router = AgentRouter(
        llm=llm,
        registry=registry,
        use_llm_routing=True  # Enable LLM-based routing
    )

    # Set global router (for API access to agent information)
    set_router(router)

    # For backward compatibility, also set a legacy single agent reference
    # This allows old endpoints to continue working
    agent_instance = KarambaAgent(
        llm_config=llm_config,
        vector_store_path="./data/vector_store"
    )
    set_agent(agent_instance)

    logger.info(f"Multi-agent system initialized with {len(registry.list_agents())} agents")

    # Initialize session store with context manager
    session_store = SessionStore(db_path="./data/sessions.db")
    await session_store.__aenter__()
    set_session_store(session_store)

    # Initialize conversation orchestrator with multi-agent router
    orchestrator = ConversationOrchestrator(
        agent=router,  # Pass router instead of single agent
        session_store=session_store,
        enable_reflection=False  # Enable later when implementing reflection
    )
    set_orchestrator(orchestrator)

    logger.info("Multi-agent orchestrator initialized with automatic routing")

    yield

    # Shutdown
    logger.info("Shutting down Karamba API")
    await session_store.__aexit__(None, None, None)


# Create FastAPI app
app = FastAPI(
    title="Karamba API",
    description="Personal Research Assistant with Document Understanding",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Karamba API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    from .dependencies import get_agent
    
    try:
        agent = get_agent()
        stats = agent.get_document_stats()
    except RuntimeError:
        stats = {}
    
    return {
        "status": "healthy",
        "agent_initialized": True,
        "vector_store": stats
    }


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)