"""Tests for phase execution engine."""
import pytest
from pathlib import Path

from karamba.core.phase_engine import Phase, PhaseEngine
from karamba.core.models import PhaseType, PhaseStatus
from karamba.llm import LLMMessage


class TestPhase:
    """Tests for Phase class."""

    def test_create_phase(self):
        """Test creating a phase."""
        phase = Phase(
            name="planning",
            phase_type=PhaseType.PLANNING,
            prompt_template="Plan for: {query}",
            verification_rules=["not_empty"],
            config={"max_tokens": 1000}
        )

        assert phase.name == "planning"
        assert phase.phase_type == PhaseType.PLANNING
        assert phase.prompt_template == "Plan for: {query}"
        assert "not_empty" in phase.verification_rules
        assert phase.config["max_tokens"] == 1000

    def test_phase_defaults(self):
        """Test Phase default values."""
        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Test"
        )

        assert phase.verification_rules == []
        assert phase.config == {}

    @pytest.mark.asyncio
    async def test_phase_execute(self, mock_llm):
        """Test executing a phase."""
        phase = Phase(
            name="test_phase",
            phase_type=PhaseType.PLANNING,
            prompt_template="Test prompt: {query}",
            verification_rules=["not_empty"]
        )

        context = {"query": "What is AI?"}
        result = await phase.execute(mock_llm, context)

        assert result.phase_name == "test_phase"
        assert result.status == PhaseStatus.COMPLETED
        assert result.output is not None
        assert len(result.verification_results) > 0

    @pytest.mark.asyncio
    async def test_phase_execute_with_missing_context(self, mock_llm):
        """Test phase execution with missing context variables."""
        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Query: {query}, Missing: {missing_var}"
        )

        context = {"query": "test"}
        result = await phase.execute(mock_llm, context)

        # Should still complete despite missing context variable
        assert result.status == PhaseStatus.COMPLETED

    def test_render_prompt(self):
        """Test prompt rendering."""
        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Query: {query}, Session: {session_id}"
        )

        context = {"query": "test query", "session_id": "sess-123"}
        rendered = phase._render_prompt(context)

        assert "test query" in rendered
        assert "sess-123" in rendered

    @pytest.mark.asyncio
    async def test_verify_output_not_empty(self):
        """Test not_empty verification rule."""
        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Test",
            verification_rules=["not_empty"]
        )

        # Test with non-empty output
        results = await phase._verify_output("Some output", {})
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].rule_name == "not_empty"

        # Test with empty output
        results = await phase._verify_output("", {})
        assert results[0].passed is False

        # Test with None output
        results = await phase._verify_output(None, {})
        assert results[0].passed is False

    @pytest.mark.asyncio
    async def test_verify_output_min_length(self):
        """Test min_length verification rule."""
        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Test",
            verification_rules=["min_length"],
            config={"min_length": 100}
        )

        # Test with sufficient length
        long_output = "x" * 150
        results = await phase._verify_output(long_output, {})
        assert results[0].passed is True

        # Test with insufficient length
        short_output = "short"
        results = await phase._verify_output(short_output, {})
        assert results[0].passed is False

    @pytest.mark.asyncio
    async def test_phase_execution_failure(self, mock_llm):
        """Test phase execution with LLM failure."""
        # Create a mock LLM that raises an error
        failing_llm = mock_llm
        failing_llm.generate = lambda *args, **kwargs: (_ for _ in ()).throw(
            Exception("LLM error")
        )

        phase = Phase(
            name="test",
            phase_type=PhaseType.PLANNING,
            prompt_template="Test"
        )

        result = await phase.execute(failing_llm, {})

        assert result.status == PhaseStatus.FAILED
        assert result.error is not None
        assert "LLM error" in result.error


class TestPhaseEngine:
    """Tests for PhaseEngine class."""

    def test_create_phase_engine(self, mock_llm):
        """Test creating a phase engine."""
        engine = PhaseEngine(mock_llm)

        assert engine.llm == mock_llm
        assert engine.phases == []

    def test_add_phase(self, mock_llm):
        """Test adding a phase to the engine."""
        engine = PhaseEngine(mock_llm)

        phase1 = Phase("phase1", PhaseType.PLANNING, "Template 1")
        phase2 = Phase("phase2", PhaseType.RETRIEVAL, "Template 2")

        engine.add_phase(phase1)
        engine.add_phase(phase2)

        assert len(engine.phases) == 2
        assert engine.phases[0].name == "phase1"
        assert engine.phases[1].name == "phase2"

    @pytest.mark.asyncio
    async def test_execute_phases(self, mock_llm):
        """Test executing multiple phases."""
        engine = PhaseEngine(mock_llm)

        phase1 = Phase("planning", PhaseType.PLANNING, "Plan: {query}")
        phase2 = Phase("reasoning", PhaseType.REASONING, "Reason: {query}")

        engine.add_phase(phase1)
        engine.add_phase(phase2)

        context = {"query": "test query"}
        results = []

        async for result in engine.execute_phases(context):
            results.append(result)

        assert len(results) == 2
        assert results[0].phase_name == "planning"
        assert results[1].phase_name == "reasoning"

    @pytest.mark.asyncio
    async def test_execute_phases_updates_context(self, mock_llm):
        """Test that phase execution updates context."""
        engine = PhaseEngine(mock_llm)

        phase1 = Phase("phase1", PhaseType.PLANNING, "Test")
        engine.add_phase(phase1)

        context = {"query": "test"}

        async for result in engine.execute_phases(context):
            pass

        # Context should contain phase output
        assert "phase1_output" in context
        assert "phase1_result" in context

    @pytest.mark.asyncio
    async def test_execute_phases_stops_on_failure(self, mock_llm):
        """Test that execution stops when a phase fails."""
        engine = PhaseEngine(mock_llm)

        # Create a phase that will fail verification
        failing_phase = Phase(
            "failing",
            PhaseType.PLANNING,
            "Test",
            verification_rules=["min_length"],
            config={"min_length": 10000}  # Impossibly high
        )

        phase2 = Phase("phase2", PhaseType.REASONING, "Test")

        engine.add_phase(failing_phase)
        engine.add_phase(phase2)

        results = []
        async for result in engine.execute_phases({"query": "test"}):
            results.append(result)

        # Should stop after first phase fails
        assert len(results) == 1
        assert results[0].status == PhaseStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_single_phase(self, mock_llm):
        """Test executing a single named phase."""
        engine = PhaseEngine(mock_llm)

        phase1 = Phase("phase1", PhaseType.PLANNING, "Template 1")
        phase2 = Phase("phase2", PhaseType.REASONING, "Template 2")

        engine.add_phase(phase1)
        engine.add_phase(phase2)

        result = await engine.execute_single_phase("phase2", {"query": "test"})

        assert result.phase_name == "phase2"

    @pytest.mark.asyncio
    async def test_execute_single_phase_not_found(self, mock_llm):
        """Test executing a non-existent phase."""
        engine = PhaseEngine(mock_llm)

        with pytest.raises(ValueError, match="Phase not found"):
            await engine.execute_single_phase("nonexistent", {})

    def test_load_config_file_not_found(self, mock_llm, temp_test_dir):
        """Test loading config from non-existent file."""
        config_path = temp_test_dir / "config" / "phases.yaml"

        with pytest.raises(FileNotFoundError):
            engine = PhaseEngine(mock_llm, config_path)

    def test_load_config(self, mock_llm, temp_test_dir):
        """Test loading phase configuration from YAML."""
        # Create config directory and files
        config_dir = temp_test_dir / "config"
        config_dir.mkdir(exist_ok=True)

        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        # Create prompt files
        (prompts_dir / "planning.txt").write_text("Planning prompt: {query}")
        (prompts_dir / "reasoning.txt").write_text("Reasoning prompt: {query}")

        # Create config YAML
        config_path = config_dir / "phases.yaml"
        config_content = """
phases:
  - name: planning
    type: planning
    prompt_file: planning.txt
    verification:
      - not_empty
      - min_length
    config:
      max_tokens: 1000
      min_length: 100

  - name: reasoning
    type: reasoning
    prompt_file: reasoning.txt
    verification:
      - not_empty
    config:
      max_tokens: 2000
"""
        config_path.write_text(config_content)

        engine = PhaseEngine(mock_llm, config_path)

        assert len(engine.phases) == 2
        assert engine.phases[0].name == "planning"
        assert engine.phases[1].name == "reasoning"
        assert "not_empty" in engine.phases[0].verification_rules
        assert engine.phases[0].config["max_tokens"] == 1000
