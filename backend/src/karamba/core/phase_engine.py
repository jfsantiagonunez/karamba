"""Phase execution engine for Karamba agent."""
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path
import yaml
import re
from loguru import logger

from ..llm import BaseLLM, LLMMessage
from .models import PhaseResult, PhaseStatus, PhaseType, VerificationResult


def detect_risky_actions(text: str) -> List[str]:
    """
    Detect potentially risky actions in planning phase output.

    Args:
        text: Planning phase output text

    Returns:
        List of detected risky action types
    """
    risky_actions = []
    text_lower = text.lower()

    # Define risky action patterns
    risk_patterns = {
        "delete_document": r"\b(delete|remove|erase)\b.*\b(document|file)\b",
        "clear_data": r"\b(clear|wipe|purge)\b.*\b(data|database|collection)\b",
        "modify_data": r"\b(update|modify|change|alter)\b.*\b(data|database|record)\b",
        "external_api": r"\b(call|invoke|request)\b.*\b(api|endpoint|external|service)\b",
        "file_operation": r"\b(write|create|delete)\b.*\b(file|directory)\b",
    }

    for action_type, pattern in risk_patterns.items():
        if re.search(pattern, text_lower):
            risky_actions.append(action_type)

    return risky_actions


class Phase:
    """Single phase in agent workflow."""

    def __init__(
        self,
        name: str,
        phase_type: PhaseType,
        prompt_template: str,
        verification_rules: List[str] = None,
        config: dict = None,
        llm: Optional[BaseLLM] = None
    ):
        self.name = name
        self.phase_type = phase_type
        self.prompt_template = prompt_template
        self.verification_rules = verification_rules or []
        self.config = config or {}
        self.llm = llm  # Optional phase-specific LLM
    
    async def execute(
        self,
        llm: BaseLLM,
        context: Dict[str, Any],
        **kwargs: Any
    ) -> PhaseResult:
        """Execute this phase."""
        # Use phase-specific LLM if provided, otherwise use default
        active_llm = self.llm if self.llm is not None else llm
        logger.info(f"Executing phase: {self.name} using {active_llm.model}")

        try:
            # Load prompt template
            prompt = self._render_prompt(context)

            # Generate with LLM
            messages = [LLMMessage(role="user", content=prompt)]
            response = await active_llm.generate(
                messages=messages,
                max_tokens=self.config.get("max_tokens", 2000)
            )

            output = response.content

            # Verify output
            verification_results = await self._verify_output(output, context)

            status = PhaseStatus.COMPLETED
            if any(not v.passed for v in verification_results):
                status = PhaseStatus.FAILED

            # Risk detection for planning phase
            metadata = {"model": active_llm.model}
            if self.phase_type == PhaseType.PLANNING:
                detected_actions = detect_risky_actions(output)
                if detected_actions:
                    metadata["detected_risky_actions"] = detected_actions
                    logger.info(f"Planning phase detected risky actions: {detected_actions}")

            return PhaseResult(
                phase_name=self.name,
                phase_type=self.phase_type,
                status=status,
                output=output,
                verification_results=verification_results,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Phase {self.name} failed: {e}")
            return PhaseResult(
                phase_name=self.name,
                phase_type=self.phase_type,
                status=PhaseStatus.FAILED,
                output=None,
                error=str(e)
            )
    
    def _render_prompt(self, context: Dict[str, Any]) -> str:
        """Render prompt template with context."""
        try:
            return self.prompt_template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing context key: {e}, using template as-is")
            return self.prompt_template
    
    async def _verify_output(
        self,
        output: Any,
        context: Dict[str, Any]
    ) -> List[VerificationResult]:
        """Verify phase output against rules."""
        results = []
        
        for rule_name in self.verification_rules:
            # Basic built-in verifications
            if rule_name == "not_empty":
                passed = bool(output and str(output).strip())
                results.append(VerificationResult(
                    passed=passed,
                    rule_name=rule_name,
                    message="Output is not empty" if passed else "Output is empty"
                ))
            elif rule_name == "min_length":
                min_len = self.config.get("min_length", 50)
                passed = len(str(output)) >= min_len
                results.append(VerificationResult(
                    passed=passed,
                    rule_name=rule_name,
                    message=f"Output length >= {min_len}" if passed else f"Output too short"
                ))
        
        return results


class PhaseEngine:
    """Engine for executing multi-phase workflows."""
    
    def __init__(self, llm: BaseLLM, config_path: Optional[Path] = None):
        self.llm = llm
        self.phases: List[Phase] = []
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: Path) -> None:
        """Load phase configuration from YAML."""
        logger.info(f"Loading phase config from {config_path}")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        prompts_dir = config_path.parent / "prompts"
        
        for phase_config in config.get("phases", []):
            # Load prompt template
            prompt_file = prompts_dir / phase_config["prompt_file"]
            prompt_template = prompt_file.read_text() if prompt_file.exists() else ""
            
            phase = Phase(
                name=phase_config["name"],
                phase_type=PhaseType(phase_config["type"]),
                prompt_template=prompt_template,
                verification_rules=phase_config.get("verification", []),
                config=phase_config.get("config", {})
            )
            
            self.phases.append(phase)
        
        logger.info(f"Loaded {len(self.phases)} phases")
    
    def add_phase(self, phase: Phase) -> None:
        """Add a phase to the engine."""
        self.phases.append(phase)
    
    async def execute_phases(
        self,
        context: Dict[str, Any]
    ) -> AsyncIterator[PhaseResult]:
        """Execute all phases in sequence."""
        logger.info(f"Executing {len(self.phases)} phases")

        for phase in self.phases:
            # Yield "started" event before execution
            yield PhaseResult(
                phase_name=phase.name,
                phase_type=phase.phase_type,
                status=PhaseStatus.RUNNING,
                output=None,
                metadata={"started": True}
            )

            # Execute the phase
            result = await phase.execute(self.llm, context)

            # Update context with phase output
            context[f"{phase.name}_output"] = result.output
            context[f"{phase.name}_result"] = result

            # Yield completion/failure event
            yield result

            # Stop if phase failed
            if result.status == PhaseStatus.FAILED:
                logger.error(f"Phase {phase.name} failed, stopping execution")
                break
    
    async def execute_single_phase(
        self,
        phase_name: str,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Execute a single named phase."""
        phase = next((p for p in self.phases if p.name == phase_name), None)
        
        if not phase:
            raise ValueError(f"Phase not found: {phase_name}")
        
        return await phase.execute(self.llm, context)