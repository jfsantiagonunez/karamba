"""Pre-built financial metrics and calculations.

Standard financial calculations that don't require code generation.
Fast, tested, and reliable.
"""

import math
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class MetricResult:
    """Result of a financial metric calculation."""
    value: float
    metric_name: str
    metadata: Dict[str, Any] = None


class FinancialMetrics:
    """
    Pre-built financial metrics calculator.

    Provides standard financial calculations without code generation.
    All methods are tested and optimized for performance.
    """

    def __init__(self):
        logger.info("FinancialMetrics initialized")

    # Risk Metrics

    def sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> MetricResult:
        """
        Calculate Sharpe Ratio.

        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (annualized)
            periods_per_year: Number of periods per year (252 for daily, 12 for monthly)

        Returns:
            MetricResult with Sharpe ratio
        """
        if not returns or len(returns) < 2:
            raise ValueError("Need at least 2 returns to calculate Sharpe ratio")

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return MetricResult(value=0.0, metric_name="sharpe_ratio",
                              metadata={"reason": "zero_volatility"})

        # Annualize
        annualized_return = mean_return * periods_per_year
        annualized_std = std_dev * math.sqrt(periods_per_year)

        sharpe = (annualized_return - risk_free_rate) / annualized_std

        logger.info(f"Calculated Sharpe ratio: {sharpe:.4f}")
        return MetricResult(
            value=sharpe,
            metric_name="sharpe_ratio",
            metadata={
                "annualized_return": annualized_return,
                "annualized_volatility": annualized_std,
                "risk_free_rate": risk_free_rate
            }
        )

    def volatility(self, returns: List[float], annualize: bool = True, periods_per_year: int = 252) -> MetricResult:
        """
        Calculate volatility (standard deviation of returns).

        Args:
            returns: List of periodic returns
            annualize: Whether to annualize the volatility
            periods_per_year: Number of periods per year

        Returns:
            MetricResult with volatility
        """
        if not returns or len(returns) < 2:
            raise ValueError("Need at least 2 returns to calculate volatility")

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        vol = math.sqrt(variance)

        if annualize:
            vol = vol * math.sqrt(periods_per_year)

        logger.info(f"Calculated volatility: {vol:.4f}")
        return MetricResult(
            value=vol,
            metric_name="volatility",
            metadata={"annualized": annualize, "periods": len(returns)}
        )

    def value_at_risk(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        investment_value: float = 1.0
    ) -> MetricResult:
        """
        Calculate Value at Risk (VaR) using historical method.

        Args:
            returns: List of historical returns
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            investment_value: Portfolio value

        Returns:
            MetricResult with VaR
        """
        if not returns:
            raise ValueError("Need returns to calculate VaR")

        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        var_return = sorted_returns[index] if index < len(sorted_returns) else sorted_returns[0]

        var_value = abs(var_return * investment_value)

        logger.info(f"Calculated VaR ({confidence_level:.0%}): {var_value:.2f}")
        return MetricResult(
            value=var_value,
            metric_name="value_at_risk",
            metadata={
                "confidence_level": confidence_level,
                "investment_value": investment_value,
                "var_return": var_return
            }
        )

    def max_drawdown(self, values: List[float]) -> MetricResult:
        """
        Calculate maximum drawdown from peak.

        Args:
            values: List of portfolio values over time

        Returns:
            MetricResult with max drawdown (as negative percentage)
        """
        if not values or len(values) < 2:
            raise ValueError("Need at least 2 values to calculate drawdown")

        max_dd = 0
        peak = values[0]
        peak_idx = 0
        trough_idx = 0

        for i, value in enumerate(values):
            if value > peak:
                peak = value
                peak_idx = i

            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd
                trough_idx = i

        logger.info(f"Calculated max drawdown: {max_dd:.2%}")
        return MetricResult(
            value=max_dd,
            metric_name="max_drawdown",
            metadata={
                "peak_index": peak_idx,
                "trough_index": trough_idx,
                "peak_value": peak
            }
        )

    # Return Metrics

    def total_return(self, start_value: float, end_value: float) -> MetricResult:
        """
        Calculate total return.

        Args:
            start_value: Starting portfolio value
            end_value: Ending portfolio value

        Returns:
            MetricResult with total return (as decimal, not percentage)
        """
        if start_value <= 0:
            raise ValueError("Start value must be positive")

        total_ret = (end_value - start_value) / start_value

        logger.info(f"Calculated total return: {total_ret:.2%}")
        return MetricResult(
            value=total_ret,
            metric_name="total_return",
            metadata={"start_value": start_value, "end_value": end_value}
        )

    def annualized_return(
        self,
        start_value: float,
        end_value: float,
        num_periods: int,
        periods_per_year: int = 252
    ) -> MetricResult:
        """
        Calculate annualized return (CAGR).

        Args:
            start_value: Starting value
            end_value: Ending value
            num_periods: Number of periods
            periods_per_year: Periods per year

        Returns:
            MetricResult with annualized return
        """
        if start_value <= 0 or num_periods <= 0:
            raise ValueError("Invalid inputs")

        years = num_periods / periods_per_year
        annualized_ret = (end_value / start_value) ** (1 / years) - 1

        logger.info(f"Calculated annualized return: {annualized_ret:.2%}")
        return MetricResult(
            value=annualized_ret,
            metric_name="annualized_return",
            metadata={"years": years, "periods": num_periods}
        )

    # Ratio Metrics

    def sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> MetricResult:
        """
        Calculate Sortino Ratio (uses downside deviation instead of total volatility).

        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate (annualized)
            periods_per_year: Periods per year

        Returns:
            MetricResult with Sortino ratio
        """
        if not returns or len(returns) < 2:
            raise ValueError("Need at least 2 returns")

        mean_return = sum(returns) / len(returns)

        # Downside deviation (only negative returns)
        downside_returns = [min(0, r - risk_free_rate / periods_per_year) for r in returns]
        downside_variance = sum(r ** 2 for r in downside_returns) / (len(returns) - 1)
        downside_std = math.sqrt(downside_variance)

        if downside_std == 0:
            return MetricResult(value=0.0, metric_name="sortino_ratio",
                              metadata={"reason": "zero_downside_deviation"})

        # Annualize
        annualized_return = mean_return * periods_per_year
        annualized_downside_std = downside_std * math.sqrt(periods_per_year)

        sortino = (annualized_return - risk_free_rate) / annualized_downside_std

        logger.info(f"Calculated Sortino ratio: {sortino:.4f}")
        return MetricResult(
            value=sortino,
            metric_name="sortino_ratio",
            metadata={
                "annualized_return": annualized_return,
                "downside_deviation": annualized_downside_std
            }
        )

    def information_ratio(
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float]
    ) -> MetricResult:
        """
        Calculate Information Ratio (excess return / tracking error).

        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns

        Returns:
            MetricResult with information ratio
        """
        if len(portfolio_returns) != len(benchmark_returns):
            raise ValueError("Return lists must be same length")

        if not portfolio_returns:
            raise ValueError("Need returns to calculate information ratio")

        # Calculate excess returns
        excess_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]

        mean_excess = sum(excess_returns) / len(excess_returns)
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
        tracking_error = math.sqrt(variance)

        if tracking_error == 0:
            return MetricResult(value=0.0, metric_name="information_ratio",
                              metadata={"reason": "zero_tracking_error"})

        info_ratio = mean_excess / tracking_error

        logger.info(f"Calculated information ratio: {info_ratio:.4f}")
        return MetricResult(
            value=info_ratio,
            metric_name="information_ratio",
            metadata={
                "mean_excess_return": mean_excess,
                "tracking_error": tracking_error
            }
        )

    # Utility Methods

    def calculate_returns(self, values: List[float]) -> List[float]:
        """
        Calculate simple returns from value series.

        Args:
            values: List of values

        Returns:
            List of returns
        """
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                ret = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(ret)

        return returns

    def get_available_metrics(self) -> List[str]:
        """
        Get list of available metric calculations.

        Returns:
            List of metric names
        """
        return [
            "sharpe_ratio", "sortino_ratio", "information_ratio",
            "volatility", "value_at_risk", "max_drawdown",
            "total_return", "annualized_return"
        ]
