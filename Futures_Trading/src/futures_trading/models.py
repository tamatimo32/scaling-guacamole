from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Literal


MarketType = Literal["spot", "futures"]
Side = Literal["long", "short"]
SignalAction = Literal["hold", "enter_long", "enter_short", "exit"]


@dataclass(frozen=True)
class Candle:
    exchange: str
    symbol: str
    market_type: MarketType
    timeframe: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int

    @property
    def open_datetime(self) -> datetime:
        return ms_to_datetime(self.open_time)

    @property
    def close_datetime(self) -> datetime:
        return ms_to_datetime(self.close_time)


@dataclass(frozen=True)
class Signal:
    action: SignalAction = "hold"
    reason: str = "hold"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def hold(cls) -> "Signal":
        return cls()


@dataclass(frozen=True)
class EquityPoint:
    time: int
    balance: float
    equity: float
    close_price: float


@dataclass(frozen=True)
class Trade:
    symbol: str
    market_type: MarketType
    side: Side
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    margin: float
    entry_fee: float
    exit_fee: float
    funding_paid: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    bars_held: int
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    market_type: MarketType
    timeframe: str
    initial_balance: float
    final_balance: float
    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]

    @property
    def total_return_pct(self) -> float:
        if self.initial_balance <= 0:
            return 0.0
        return (self.final_balance / self.initial_balance - 1.0) * 100.0

    @property
    def win_rate_pct(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for trade in self.trades if trade.net_pnl > 0)
        return wins / len(self.trades) * 100.0

    @property
    def max_drawdown_pct(self) -> float:
        peak = None
        max_drawdown = 0.0
        for point in self.equity_curve:
            if peak is None or point.equity > peak:
                peak = point.equity
            if peak and peak > 0:
                drawdown = (peak - point.equity) / peak * 100.0
                max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown

    @property
    def profit_factor(self) -> float:
        gross_wins = sum(trade.net_pnl for trade in self.trades if trade.net_pnl > 0)
        gross_losses = abs(sum(trade.net_pnl for trade in self.trades if trade.net_pnl < 0))
        if gross_losses == 0:
            return float("inf") if gross_wins > 0 else 0.0
        return gross_wins / gross_losses

    @property
    def net_pnl(self) -> float:
        return self.final_balance - self.initial_balance

    @property
    def gross_profit(self) -> float:
        return sum(trade.net_pnl for trade in self.trades if trade.net_pnl > 0)

    @property
    def gross_loss(self) -> float:
        return sum(trade.net_pnl for trade in self.trades if trade.net_pnl < 0)

    @property
    def average_trade_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.net_pnl for trade in self.trades) / len(self.trades)

    @property
    def average_trade_return_pct(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.return_pct for trade in self.trades) / len(self.trades)

    @property
    def average_win_pnl(self) -> float:
        wins = [trade.net_pnl for trade in self.trades if trade.net_pnl > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def average_loss_pnl(self) -> float:
        losses = [trade.net_pnl for trade in self.trades if trade.net_pnl < 0]
        return sum(losses) / len(losses) if losses else 0.0

    @property
    def payoff_ratio(self) -> float:
        average_loss = abs(self.average_loss_pnl)
        if average_loss == 0:
            return float("inf") if self.average_win_pnl > 0 else 0.0
        return self.average_win_pnl / average_loss

    @property
    def sharpe_ratio(self) -> float:
        returns = self._equity_returns()
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        if std_dev == 0:
            return 0.0
        return mean_return / std_dev * math.sqrt(periods_per_year(self.timeframe))

    @property
    def sortino_ratio(self) -> float:
        returns = self._equity_returns()
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        downside = [value for value in returns if value < 0.0]
        if len(downside) < 1:
            return float("inf") if mean_return > 0 else 0.0
        downside_dev = math.sqrt(sum(value * value for value in downside) / len(downside))
        if downside_dev == 0:
            return 0.0
        return mean_return / downside_dev * math.sqrt(periods_per_year(self.timeframe))

    @property
    def calmar_ratio(self) -> float:
        annualized = self.annualized_return_pct
        max_dd = self.max_drawdown_pct
        if max_dd <= 0:
            return float("inf") if annualized > 0 else 0.0
        return annualized / max_dd

    @property
    def annualized_return_pct(self) -> float:
        years = self.duration_days / 365.0
        if years <= 0 or self.initial_balance <= 0 or self.final_balance <= 0:
            return 0.0
        ratio = self.final_balance / self.initial_balance
        return (ratio ** (1.0 / years) - 1.0) * 100.0

    @property
    def duration_days(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        first = self.equity_curve[0].time
        last = self.equity_curve[-1].time
        return max(0.0, (last - first) / 86_400_000.0)

    @property
    def max_drawdown_duration_bars(self) -> int:
        peak = None
        peak_index = 0
        worst_duration = 0
        for index, point in enumerate(self.equity_curve):
            if peak is None or point.equity > peak:
                peak = point.equity
                peak_index = index
            elif point.equity < peak:
                worst_duration = max(worst_duration, index - peak_index)
        return worst_duration

    @property
    def expectancy(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.net_pnl for trade in self.trades) / len(self.trades)

    @property
    def expectancy_pct(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.return_pct for trade in self.trades) / len(self.trades)

    @property
    def best_trade_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return max(trade.net_pnl for trade in self.trades)

    @property
    def worst_trade_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return min(trade.net_pnl for trade in self.trades)

    @property
    def longest_win_streak(self) -> int:
        return _longest_streak(self.trades, lambda trade: trade.net_pnl > 0)

    @property
    def longest_loss_streak(self) -> int:
        return _longest_streak(self.trades, lambda trade: trade.net_pnl < 0)

    @property
    def total_funding_paid(self) -> float:
        return sum(trade.funding_paid for trade in self.trades)

    @property
    def total_fees_paid(self) -> float:
        return sum(trade.entry_fee + trade.exit_fee for trade in self.trades)

    @property
    def average_bars_held(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.bars_held for trade in self.trades) / len(self.trades)

    @property
    def pnl_r_squared(self) -> float:
        if len(self.trades) < 2:
            return 0.0
        cumulative = []
        running = 0.0
        for trade in self.trades:
            running += trade.net_pnl
            cumulative.append(running)
        return linear_r_squared(cumulative)

    def _equity_returns(self) -> list[float]:
        returns: list[float] = []
        previous_equity: float | None = None
        for point in self.equity_curve:
            if previous_equity is not None and previous_equity > 0:
                returns.append(point.equity / previous_equity - 1.0)
            previous_equity = point.equity
        return returns


def ms_to_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def datetime_to_ms(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def periods_per_year(timeframe: str) -> float:
    value = timeframe.strip().lower()
    units = {
        "m": 365 * 24 * 60,
        "h": 365 * 24,
        "d": 365,
        "w": 52,
    }
    suffix = value[-1:]
    if suffix not in units:
        return 365.0
    try:
        amount = float(value[:-1])
    except ValueError:
        return 365.0
    if amount <= 0:
        return 365.0
    return units[suffix] / amount


def _longest_streak(trades, predicate) -> int:
    longest = 0
    current = 0
    for trade in trades:
        if predicate(trade):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def linear_r_squared(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        return 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / ss_xx
    intercept = mean_y - slope * mean_x
    ss_total = sum((y - mean_y) ** 2 for y in values)
    if ss_total == 0:
        return 0.0
    ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, values))
    return max(0.0, min(1.0, 1.0 - ss_residual / ss_total))
