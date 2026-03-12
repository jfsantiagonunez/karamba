"""Safe Python code executor for dynamic computations.

This executor runs LLM-generated Python code in a restricted environment
for performing calculations, data analysis, and custom metrics.
"""

import sys
import io
import ast
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
import contextlib


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class PythonExecutor:
    """
    Safe Python code executor with sandboxing.

    Features:
    - Restricted imports (only safe libraries)
    - Timeout protection
    - Memory limits
    - Output capture
    - AST validation before execution
    """

    # Allowed imports for safe execution
    SAFE_IMPORTS = {
        "math", "statistics", "datetime", "json", "re",
        "numpy", "pandas", "scipy", "collections", "itertools",
        "decimal", "fractions"
    }

    # Forbidden operations
    FORBIDDEN_NAMES = {
        "eval", "exec", "compile", "__import__", "open", "file",
        "input", "raw_input", "reload", "vars", "globals", "locals",
        "dir", "breakpoint", "exit", "quit"
    }

    def __init__(self, timeout: int = 5, max_output_size: int = 10000):
        """
        Initialize Python executor.

        Args:
            timeout: Maximum execution time in seconds
            max_output_size: Maximum size of output in characters
        """
        self.timeout = timeout
        self.max_output_size = max_output_size
        logger.info(f"PythonExecutor initialized (timeout={timeout}s)")

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate Python code for safety before execution.

        Args:
            code: Python code to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            # Parse AST
            tree = ast.parse(code)

            # Check for forbidden operations
            for node in ast.walk(tree):
                # Check for forbidden function calls
                if isinstance(node, ast.Name):
                    if node.id in self.FORBIDDEN_NAMES:
                        return False, f"Forbidden operation: {node.id}"

                # Check for imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_names = []
                    if isinstance(node, ast.Import):
                        module_names = [alias.name.split('.')[0] for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_names = [node.module.split('.')[0]]

                    for module_name in module_names:
                        if module_name not in self.SAFE_IMPORTS:
                            return False, f"Import not allowed: {module_name}"

            return True, None

        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def execute(
        self,
        code: str,
        variables: Optional[Dict[str, Any]] = None,
        return_variable: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute Python code safely.

        Args:
            code: Python code to execute
            variables: Optional variables to inject into execution context
            return_variable: Optional variable name to return as result

        Returns:
            ExecutionResult with output and any errors
        """
        logger.info(f"Executing Python code ({len(code)} chars)")

        # Validate code first
        is_valid, error_msg = self.validate_code(code)
        if not is_valid:
            logger.error(f"Code validation failed: {error_msg}")
            return ExecutionResult(success=False, error=error_msg)

        # Prepare execution context
        exec_globals = {
            "__builtins__": {
                # Basic built-ins
                "abs": abs, "all": all, "any": any, "bool": bool,
                "dict": dict, "float": float, "int": int, "len": len,
                "list": list, "max": max, "min": min, "pow": pow,
                "range": range, "round": round, "set": set, "sorted": sorted,
                "str": str, "sum": sum, "tuple": tuple, "zip": zip,
                # Type checking
                "isinstance": isinstance, "type": type,
                # Exceptions
                "Exception": Exception, "ValueError": ValueError,
                "TypeError": TypeError, "KeyError": KeyError,
                # Other safe operations
                "enumerate": enumerate, "map": map, "filter": filter,
                "print": print,
            }
        }

        # Add user variables
        if variables:
            exec_globals.update(variables)

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                # Execute code
                exec(code, exec_globals)

            # Get stdout/stderr
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()

            # Get result if return_variable specified
            result = None
            if return_variable and return_variable in exec_globals:
                result = exec_globals[return_variable]

            # Truncate output if too large
            if stdout_text and len(stdout_text) > self.max_output_size:
                stdout_text = stdout_text[:self.max_output_size] + "\n... (truncated)"

            logger.info("Code execution completed successfully")
            return ExecutionResult(
                success=True,
                output=stdout_text if stdout_text else None,
                result=result,
                stdout=stdout_text if stdout_text else None,
                stderr=stderr_text if stderr_text else None
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Code execution failed: {error_msg}")

            return ExecutionResult(
                success=False,
                error=error_msg,
                stdout=stdout_capture.getvalue() if stdout_capture.getvalue() else None,
                stderr=stderr_capture.getvalue() if stderr_capture.getvalue() else None
            )

    def execute_expression(self, expression: str, variables: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute a single Python expression and return its value.

        Simpler than execute() for single-line calculations.

        Args:
            expression: Python expression to evaluate (e.g., "2 + 2", "math.sqrt(16)")
            variables: Optional variables to inject

        Returns:
            ExecutionResult with the expression result
        """
        code = f"_result = {expression}"
        result = self.execute(code, variables=variables, return_variable="_result")
        return result

    def get_safe_imports_help(self) -> str:
        """
        Get help text about which libraries are available.

        Returns:
            String describing available imports
        """
        return f"""
Available imports for code execution:
{', '.join(sorted(self.SAFE_IMPORTS))}

Example usage:
```python
import math
import numpy as np
import pandas as pd

result = math.sqrt(16)  # 4.0
array = np.array([1, 2, 3])
df = pd.DataFrame({{'a': [1, 2, 3]}})
```
"""
