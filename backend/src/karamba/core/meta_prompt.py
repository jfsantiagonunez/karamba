"""
Meta-Prompting Module

Intelligent prompt construction that builds optimal prompts based on:
- Context chain state
- Domain expertise
- Quality criteria
- Sibling awareness
- Human writing guidelines
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MetaPromptConfig:
    """Configuration for meta-prompt generation"""
    include_context_chain: bool = True
    include_domain_expertise: bool = True
    include_quality_criteria: bool = True
    include_sibling_awareness: bool = True
    include_human_writing_guidelines: bool = True
    max_context_tokens: int = 2000


HUMAN_WRITING_GUIDELINES = """
CRITICAL: Write like a human expert, not an AI. Follow these rules:

1. NO AI-TELLS:
   - Never say "As an AI" or "I cannot"
   - Avoid "Certainly!", "Absolutely!", "Great question!"
   - Don't use "In conclusion" or "It's important to note"
   - Skip "Let me break this down" or "Let's explore"

2. NATURAL LANGUAGE:
   - Use contractions sometimes (it's, don't, we're)
   - Vary sentence length - mix short and long
   - Start some sentences with "And" or "But"
   - Use specific examples, not generic ones

3. FORMATTING:
   - Avoid excessive bullet points - use prose
   - Don't overuse em-dashes (—) - humans rarely use them
   - Keep structure simple and natural
   - Headers only when truly needed

4. VOICE:
   - Write with confidence, not hedging
   - Be direct, not flowery
   - Sound like a senior professional, not a helpful assistant
   - Show expertise through specifics, not generic advice

5. AUTHENTICITY:
   - Include minor imperfections (humans aren't perfect)
   - Reference real things (dates, names, places)
   - Show opinion where appropriate
   - Acknowledge complexity without over-qualifying
"""


FINANCIAL_DOMAIN_KNOWLEDGE = {
    "requirements": [
        "Quantify risk with specific metrics (VaR, CVaR, volatility, Sharpe ratio, beta)",
        "Consider market, credit, liquidity, and operational risk dimensions",
        "Reference regulatory frameworks (Basel III, Dodd-Frank, MiFID II) when applicable",
        "Distinguish between systematic and idiosyncratic risk",
        "Assess correlation and concentration risk in portfolios",
        "Consider time horizon and liquidity constraints",
        "Evaluate risk-adjusted returns, not just absolute returns",
        "Address tail risk and extreme scenarios",
        "Consider macroeconomic factors and market regime changes",
        "Provide actionable recommendations with clear risk/reward tradeoffs"
    ],
    "terminology": {
        "VaR": "Value at Risk - maximum expected loss over a time period at a given confidence level",
        "Sharpe Ratio": "Risk-adjusted return metric (excess return / volatility)",
        "Beta": "Systematic risk measure relative to market",
        "CVaR": "Conditional Value at Risk - expected loss beyond VaR threshold",
        "Duration": "Interest rate sensitivity measure for fixed income",
        "Credit Spread": "Yield difference reflecting default risk",
        "Liquidity Premium": "Additional return for holding less liquid assets",
        "Drawdown": "Peak-to-trough decline in investment value"
    },
    "best_practices": [
        "Always cite specific numbers and data from documents",
        "Use multiple valuation/risk methodologies for triangulation",
        "Clearly state assumptions and their sensitivity",
        "Consider both historical and forward-looking analysis",
        "Acknowledge data limitations and gaps",
        "Compare against relevant benchmarks and peers",
        "Provide concrete risk mitigation recommendations",
        "Use scenario analysis to test assumptions"
    ],
    "validation_criteria": [
        "All quantitative claims are supported by document citations",
        "Risk ratings are clearly justified with specific evidence",
        "Analysis considers multiple time horizons",
        "Recommendations are specific and actionable",
        "Limitations and caveats are explicitly stated"
    ]
}


class MetaPromptBuilder:
    """
    Builds intelligent prompts for AI generation.

    This is not just template filling - it's context-aware
    prompt construction that produces better outputs.
    """

    def __init__(self, config: MetaPromptConfig = None):
        self.config = config or MetaPromptConfig()

    def build_prompt(self,
                    task_description: str,
                    context: Dict[str, Any] = None,
                    domain_knowledge: Dict[str, Any] = None,
                    quality_criteria: List[str] = None,
                    sibling_summaries: List[str] = None,
                    output_format: str = "text") -> str:
        """
        Build an optimal prompt for the given task.

        Args:
            task_description: What needs to be generated
            context: Context from context chain
            domain_knowledge: Domain-specific knowledge
            quality_criteria: What makes this excellent
            sibling_summaries: What siblings are producing
            output_format: Expected output format

        Returns:
            Complete prompt string
        """

        parts = []

        # 1. Role and context
        parts.append(self._build_role_section(context))

        # 2. Task description
        parts.append(f"\n## TASK\n{task_description}")

        # 3. Domain expertise
        if self.config.include_domain_expertise and domain_knowledge:
            parts.append(self._build_domain_section(domain_knowledge))

        # 4. Quality criteria
        if self.config.include_quality_criteria and quality_criteria:
            parts.append(self._build_quality_section(quality_criteria))

        # 5. Sibling awareness
        if self.config.include_sibling_awareness and sibling_summaries:
            parts.append(self._build_sibling_section(sibling_summaries))

        # 6. Human writing guidelines
        if self.config.include_human_writing_guidelines:
            parts.append(f"\n## WRITING STYLE\n{HUMAN_WRITING_GUIDELINES}")

        # 7. Output format
        parts.append(self._build_output_section(output_format))

        return "\n".join(parts)

    def _build_role_section(self, context: Dict = None) -> str:
        """Build the role and context section"""

        role = "You are a senior professional creating high-quality deliverables."

        if context:
            genesis = context.get("genesis", {})
            if genesis.get("domain"):
                role = f"You are a senior {genesis['domain']} professional creating high-quality deliverables."

            if genesis.get("quality_bar"):
                role += f" The quality standard is: {genesis['quality_bar']}."

        return f"## ROLE\n{role}"

    def _build_domain_section(self, domain_knowledge: Dict) -> str:
        """Build domain expertise section"""

        parts = ["\n## DOMAIN EXPERTISE"]

        if "requirements" in domain_knowledge:
            parts.append("\nKey Requirements:")
            for req in domain_knowledge["requirements"][:10]:
                parts.append(f"- {req}")

        if "terminology" in domain_knowledge:
            parts.append("\nKey Terminology:")
            for term, definition in list(domain_knowledge["terminology"].items())[:5]:
                parts.append(f"- {term}: {definition}")

        if "best_practices" in domain_knowledge:
            parts.append("\nBest Practices:")
            for practice in domain_knowledge["best_practices"][:5]:
                parts.append(f"- {practice}")

        return "\n".join(parts)

    def _build_quality_section(self, criteria: List[str]) -> str:
        """Build quality criteria section"""

        parts = ["\n## QUALITY CRITERIA"]
        parts.append("This output must meet these standards:")

        for criterion in criteria[:10]:
            parts.append(f"- {criterion}")

        return "\n".join(parts)

    def _build_sibling_section(self, summaries: List[str]) -> str:
        """Build sibling awareness section"""

        parts = ["\n## CONTEXT FROM RELATED SECTIONS"]
        parts.append("Other sections being produced (ensure consistency):")

        for i, summary in enumerate(summaries[:5], 1):
            parts.append(f"{i}. {summary[:200]}")

        return "\n".join(parts)

    def _build_output_section(self, output_format: str) -> str:
        """Build output format section"""

        format_instructions = {
            "text": "Write in clear, professional prose.",
            "markdown": "Use markdown formatting with headers and structure.",
            "json": "Return valid JSON format.",
            "list": "Return as a structured list.",
            "table": "Return as a formatted table."
        }

        instruction = format_instructions.get(output_format, format_instructions["text"])

        return f"\n## OUTPUT FORMAT\n{instruction}\n\nNow produce the content:"

    def build_verification_criteria(self,
                                   task_description: str,
                                   domain_knowledge: Dict = None,
                                   quality_bar: str = "professional") -> List[str]:
        """
        Generate verification criteria for the task.

        These criteria will be used to validate the output.
        """

        criteria = [
            "Content is complete and addresses all aspects of the task",
            "Writing is professional and free of errors",
            "No AI-tells present (no 'As an AI', 'Certainly!', etc.)",
            "Uses natural language without excessive formatting",
            "Internally consistent with no contradictions"
        ]

        # Add domain-specific criteria
        if domain_knowledge and "validation_criteria" in domain_knowledge:
            criteria.extend(domain_knowledge["validation_criteria"][:5])

        # Add quality-bar specific criteria
        if quality_bar == "board_ready":
            criteria.append("Suitable for board-level presentation")
            criteria.append("Executive summary quality")
        elif quality_bar == "publication_ready":
            criteria.append("Publication-quality writing")
            criteria.append("Properly cited where needed")

        return criteria


def build_financial_risk_prompt(
    query: str,
    retrieved_context: str,
    benchmarks: str = None,
    analysis_plan: str = None,
    perspective: str = "balanced"
) -> str:
    """
    Build a meta-prompt specifically for financial risk assessment.

    Args:
        query: User's financial risk query
        retrieved_context: Retrieved document content
        benchmarks: Industry benchmarks from earlier phase
        analysis_plan: Analysis plan from earlier phase
        perspective: Analysis perspective (conservative, balanced, optimistic)

    Returns:
        Complete meta-prompt for financial risk analysis
    """

    perspective_roles = {
        "conservative": "a conservative risk analyst who focuses on downside scenarios",
        "balanced": "a balanced financial analyst who weighs risks against opportunities",
        "optimistic": "an optimistic analyst who evaluates risk management strengths"
    }

    role = perspective_roles.get(perspective, perspective_roles["balanced"])

    builder = MetaPromptBuilder()

    # Build context
    context = {
        "genesis": {
            "domain": "financial risk analysis",
            "quality_bar": "investment-grade"
        }
    }

    # Build task description
    task = f"""Analyze the following financial risk query from the perspective of {role}.

**Query**: {query}

**Retrieved Context**:
{retrieved_context[:1500]}
"""

    if benchmarks:
        task += f"\n**Industry Benchmarks**:\n{benchmarks[:500]}\n"

    if analysis_plan:
        task += f"\n**Analysis Plan**:\n{analysis_plan[:500]}\n"

    # Quality criteria specific to financial risk
    quality_criteria = [
        "Quantify risk using specific metrics from the documents",
        "Provide clear risk rating with justification",
        "Include actionable recommendations",
        "Cite specific sources for all claims",
        "Address both quantitative and qualitative factors",
        "Consider multiple time horizons",
        "Acknowledge limitations in data or analysis"
    ]

    return builder.build_prompt(
        task_description=task,
        context=context,
        domain_knowledge=FINANCIAL_DOMAIN_KNOWLEDGE,
        quality_criteria=quality_criteria,
        output_format="markdown"
    )


def build_meta_prompt(task: str, context: Dict = None,
                     domain: Dict = None, criteria: List[str] = None) -> str:
    """Convenience function to build a meta-prompt"""
    builder = MetaPromptBuilder()
    return builder.build_prompt(
        task_description=task,
        context=context,
        domain_knowledge=domain,
        quality_criteria=criteria
    )
