"""
Multi-Agent Framework for Karamba

Provides base abstractions and specialist agents for different use cases.
"""

from karamba.agents.base import BaseSpecialistAgent, AgentCapability
from karamba.agents.research import ResearchAgent
from karamba.agents.financial import FinancialRiskAgent
from karamba.agents.router import AgentRouter, AgentRegistry

__all__ = [
    'BaseSpecialistAgent',
    'AgentCapability',
    'ResearchAgent',
    'FinancialRiskAgent',
    'AgentRouter',
    'AgentRegistry',
]
