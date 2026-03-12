"""API dependencies."""
from typing import Optional
from karamba.core.agent import KarambaAgent
from karamba.agents.router import AgentRouter
from karamba.memory import ConversationOrchestrator, SessionStore

# Global instances
agent_instance: Optional[KarambaAgent] = None
router_instance: Optional[AgentRouter] = None
session_store_instance: Optional[SessionStore] = None
orchestrator_instance: Optional[ConversationOrchestrator] = None


def get_agent() -> KarambaAgent:
    """Dependency to get agent instance."""
    if agent_instance is None:
        raise RuntimeError("Agent not initialized")
    return agent_instance


def set_agent(agent: KarambaAgent) -> None:
    """Set the global agent instance."""
    global agent_instance
    agent_instance = agent


def get_session_store() -> SessionStore:
    """Dependency to get session store instance."""
    if session_store_instance is None:
        raise RuntimeError("Session store not initialized")
    return session_store_instance


def set_session_store(store: SessionStore) -> None:
    """Set the global session store instance."""
    global session_store_instance
    session_store_instance = store


def get_orchestrator() -> ConversationOrchestrator:
    """Dependency to get conversation orchestrator instance."""
    if orchestrator_instance is None:
        raise RuntimeError("Orchestrator not initialized")
    return orchestrator_instance


def set_orchestrator(orchestrator: ConversationOrchestrator) -> None:
    """Set the global orchestrator instance."""
    global orchestrator_instance
    orchestrator_instance = orchestrator


def get_router() -> AgentRouter:
    """Dependency to get agent router instance."""
    if router_instance is None:
        raise RuntimeError("Router not initialized")
    return router_instance


def set_router(router: AgentRouter) -> None:
    """Set the global router instance."""
    global router_instance
    router_instance = router