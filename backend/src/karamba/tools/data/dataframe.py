"""DataFrame tool for Excel and tabular data analysis.

Provides standard operations on tabular data without requiring code generation.
For custom analysis, integrates with PythonExecutor.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class DataFrameResult:
    """Result of a DataFrame operation."""
    success: bool
    data: Optional[pd.DataFrame] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class DataFrameTool:
    """
    Tool for loading and analyzing tabular data (Excel, CSV).

    Philosophy:
    - Use pre-built methods for standard operations (fast, reliable)
    - Provide summary statistics for LLM context
    - Integrate with code executor for custom analysis
    - Never send full tables to LLM (use summaries)
    """

    def __init__(self, code_executor=None):
        """
        Initialize DataFrame tool.

        Args:
            code_executor: Optional PythonExecutor for custom operations
        """
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.code_executor = code_executor
        logger.info("DataFrameTool initialized")

    # Loading Methods

    def load_excel(
        self,
        file_path: str,
        sheet_name: Optional[Union[str, int]] = 0,
        df_name: str = "main"
    ) -> DataFrameResult:
        """
        Load Excel file into memory.

        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: first sheet)
            df_name: Name to store DataFrame under

        Returns:
            DataFrameResult with loaded data
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self.dataframes[df_name] = df

            summary = self._generate_summary(df, df_name)
            logger.info(f"Loaded Excel: {file_path} ({len(df)} rows, {len(df.columns)} cols)")

            return DataFrameResult(
                success=True,
                data=df,
                summary=summary,
                metadata={"file_path": file_path, "sheet_name": sheet_name, "rows": len(df)}
            )
        except Exception as e:
            logger.error(f"Failed to load Excel: {e}")
            return DataFrameResult(success=False, error=str(e))

    def load_csv(
        self,
        file_path: str,
        df_name: str = "main",
        **kwargs
    ) -> DataFrameResult:
        """
        Load CSV file into memory.

        Args:
            file_path: Path to CSV file
            df_name: Name to store DataFrame under
            **kwargs: Additional pandas read_csv arguments

        Returns:
            DataFrameResult with loaded data
        """
        try:
            df = pd.read_csv(file_path, **kwargs)
            self.dataframes[df_name] = df

            summary = self._generate_summary(df, df_name)
            logger.info(f"Loaded CSV: {file_path} ({len(df)} rows, {len(df.columns)} cols)")

            return DataFrameResult(
                success=True,
                data=df,
                summary=summary,
                metadata={"file_path": file_path, "rows": len(df)}
            )
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return DataFrameResult(success=False, error=str(e))

    def load_from_dict(
        self,
        data: Dict[str, List],
        df_name: str = "main"
    ) -> DataFrameResult:
        """
        Load DataFrame from dictionary.

        Args:
            data: Dictionary of column_name -> values
            df_name: Name to store DataFrame under

        Returns:
            DataFrameResult with loaded data
        """
        try:
            df = pd.DataFrame(data)
            self.dataframes[df_name] = df

            summary = self._generate_summary(df, df_name)
            logger.info(f"Loaded DataFrame from dict ({len(df)} rows, {len(df.columns)} cols)")

            return DataFrameResult(success=True, data=df, summary=summary)
        except Exception as e:
            logger.error(f"Failed to load from dict: {e}")
            return DataFrameResult(success=False, error=str(e))

    # Query Methods (LLM-friendly)

    def get_summary(self, df_name: str = "main") -> DataFrameResult:
        """
        Get LLM-friendly summary of DataFrame.

        Returns overview without sending entire table to LLM.

        Args:
            df_name: Name of DataFrame

        Returns:
            DataFrameResult with summary text
        """
        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]
        summary = self._generate_summary(df, df_name)

        return DataFrameResult(
            success=True,
            data=df,
            summary=summary,
            metadata={"df_name": df_name}
        )

    def get_sample(
        self,
        df_name: str = "main",
        n: int = 5,
        method: str = "head"
    ) -> DataFrameResult:
        """
        Get sample rows (safe to send to LLM).

        Args:
            df_name: Name of DataFrame
            n: Number of rows
            method: 'head', 'tail', or 'random'

        Returns:
            DataFrameResult with sample data
        """
        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]

        if method == "head":
            sample = df.head(n)
        elif method == "tail":
            sample = df.tail(n)
        elif method == "random":
            sample = df.sample(n=min(n, len(df)))
        else:
            return DataFrameResult(success=False, error=f"Unknown method: {method}")

        # Convert to LLM-friendly format
        summary = f"Sample {n} rows using '{method}' method:\n\n"
        summary += sample.to_string(index=False)

        return DataFrameResult(
            success=True,
            data=sample,
            summary=summary,
            metadata={"method": method, "n": n}
        )

    # Standard Operations (Pre-built)

    def filter_rows(
        self,
        df_name: str = "main",
        column: str = None,
        value: Any = None,
        condition: str = "equals"
    ) -> DataFrameResult:
        """
        Filter rows by condition.

        Args:
            df_name: Name of DataFrame
            column: Column to filter on
            value: Value to compare
            condition: 'equals', 'greater', 'less', 'contains'

        Returns:
            DataFrameResult with filtered data
        """
        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]

        try:
            if condition == "equals":
                filtered = df[df[column] == value]
            elif condition == "greater":
                filtered = df[df[column] > value]
            elif condition == "less":
                filtered = df[df[column] < value]
            elif condition == "contains":
                filtered = df[df[column].astype(str).str.contains(str(value), case=False)]
            else:
                return DataFrameResult(success=False, error=f"Unknown condition: {condition}")

            summary = f"Filtered {len(df)} rows to {len(filtered)} rows where {column} {condition} {value}"
            logger.info(summary)

            return DataFrameResult(
                success=True,
                data=filtered,
                summary=summary,
                metadata={"original_rows": len(df), "filtered_rows": len(filtered)}
            )
        except Exception as e:
            logger.error(f"Filter failed: {e}")
            return DataFrameResult(success=False, error=str(e))

    def aggregate(
        self,
        df_name: str = "main",
        group_by: Union[str, List[str]] = None,
        agg_column: str = None,
        agg_function: str = "sum"
    ) -> DataFrameResult:
        """
        Aggregate data by group.

        Args:
            df_name: Name of DataFrame
            group_by: Column(s) to group by
            agg_column: Column to aggregate
            agg_function: 'sum', 'mean', 'count', 'min', 'max'

        Returns:
            DataFrameResult with aggregated data
        """
        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]

        try:
            if group_by:
                grouped = df.groupby(group_by)[agg_column].agg(agg_function).reset_index()
            else:
                # Aggregate entire column
                result_value = df[agg_column].agg(agg_function)
                grouped = pd.DataFrame({agg_column: [result_value]})

            summary = f"Aggregated by {group_by} using {agg_function}:\n{grouped.to_string(index=False)}"
            logger.info(f"Aggregation complete: {len(grouped)} groups")

            return DataFrameResult(
                success=True,
                data=grouped,
                summary=summary,
                metadata={"groups": len(grouped)}
            )
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            return DataFrameResult(success=False, error=str(e))

    def get_statistics(
        self,
        df_name: str = "main",
        columns: Optional[List[str]] = None
    ) -> DataFrameResult:
        """
        Get descriptive statistics.

        Args:
            df_name: Name of DataFrame
            columns: Specific columns (None for all numeric)

        Returns:
            DataFrameResult with statistics
        """
        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]

        try:
            if columns:
                stats = df[columns].describe()
            else:
                stats = df.describe()

            summary = f"Descriptive Statistics:\n\n{stats.to_string()}"
            logger.info("Generated descriptive statistics")

            return DataFrameResult(
                success=True,
                data=stats,
                summary=summary
            )
        except Exception as e:
            logger.error(f"Statistics failed: {e}")
            return DataFrameResult(success=False, error=str(e))

    # Custom Analysis (via Code Executor)

    def execute_custom_analysis(
        self,
        code: str,
        df_name: str = "main"
    ) -> DataFrameResult:
        """
        Execute custom pandas code on DataFrame.

        Integrates with PythonExecutor for complex operations.

        Args:
            code: Python code to execute (has access to 'df' variable)
            df_name: Name of DataFrame to operate on

        Returns:
            DataFrameResult with code execution result
        """
        if not self.code_executor:
            return DataFrameResult(
                success=False,
                error="Code executor not available. Pass code_executor in __init__."
            )

        if df_name not in self.dataframes:
            return DataFrameResult(success=False, error=f"DataFrame '{df_name}' not found")

        df = self.dataframes[df_name]

        try:
            # Execute code with df available
            result = self.code_executor.execute(
                code,
                variables={"df": df, "pd": pd, "np": np},
                return_variable="result"
            )

            if result.success:
                summary = f"Custom analysis completed:\n{result.stdout or 'No output'}"
                return DataFrameResult(
                    success=True,
                    data=result.result if isinstance(result.result, pd.DataFrame) else None,
                    summary=summary,
                    metadata={"code_output": result.stdout}
                )
            else:
                return DataFrameResult(success=False, error=result.error)

        except Exception as e:
            logger.error(f"Custom analysis failed: {e}")
            return DataFrameResult(success=False, error=str(e))

    # Utility Methods

    def _generate_summary(self, df: pd.DataFrame, df_name: str) -> str:
        """Generate LLM-friendly summary of DataFrame."""
        summary_parts = [
            f"DataFrame: {df_name}",
            f"Rows: {len(df):,}",
            f"Columns: {len(df.columns)}",
            f"\nColumn Types:",
        ]

        for col, dtype in df.dtypes.items():
            summary_parts.append(f"  - {col}: {dtype}")

        # Add sample statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary_parts.append("\nNumeric Column Ranges:")
            for col in numeric_cols[:5]:  # Limit to 5
                summary_parts.append(
                    f"  - {col}: {df[col].min():.2f} to {df[col].max():.2f} (mean: {df[col].mean():.2f})"
                )

        # Add categorical info
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            summary_parts.append("\nCategorical Columns:")
            for col in categorical_cols[:5]:  # Limit to 5
                unique_count = df[col].nunique()
                summary_parts.append(f"  - {col}: {unique_count} unique values")

        return "\n".join(summary_parts)

    def list_dataframes(self) -> List[str]:
        """List all loaded DataFrames."""
        return list(self.dataframes.keys())

    def get_dataframe(self, df_name: str) -> Optional[pd.DataFrame]:
        """Get raw DataFrame (use carefully - don't send to LLM)."""
        return self.dataframes.get(df_name)
