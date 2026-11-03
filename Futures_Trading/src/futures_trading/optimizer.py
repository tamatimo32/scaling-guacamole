from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from collections.abc import Callable

from .models import BacktestResult, Candle
from .simulator import BacktestConfig, BacktestEngine
from .strategies import (
    BuyAndHoldStrategy,
    CompositeStrategy,
    Strategy,
    ThresholdStrategy,
    strategy_display_names,
)
from .strategies_ut_bot import UtBotStrategy


@dataclass(frozen=True)
class OptimizationRow:
    strategy_name: str
    strategy_stack: str
    combine_mode: str
    allow_short: bool
    entry_drop_pct: float
    entry_rise_pct: float | None
    take_profit_pct: float
    stop_loss_pct: float
    final_balance: float
    net_pnl: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    max_drawdown_duration_bars: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    pnl_r_squared: float
    win_rate_pct: float
    profit_factor: float
    payoff_ratio: float
    expectancy: float
    average_trade_pnl: float
    average_trade_return_pct: float
    average_bars_held: float
    average_win_pnl: float
    average_loss_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float
    longest_win_streak: int
    longest_loss_streak: int
    total_funding_paid: float
    total_fees_paid: float
    trade_count: int
    optimizer_strategy: str = "threshold"
    ut_key_value: float | None = None
    ut_atr_period: int | None = None
    ut_lr_period: int | None = None
    ut_exit_pct: float | None = None
    ut_exit_delay: int | None = None
    ut_use_heikin_ashi: bool | None = None


@dataclass(frozen=True)
class OptimizationResult:
    rows: tuple[OptimizationRow, ...]

    @property
    def best(self) -> OptimizationRow | None:
        if not self.rows:
            return None
        return max(
            self.rows,
            key=lambda row: (
                row.final_balance,
                -row.max_drawdown_pct,
                row.profit_factor,
            ),
        )


def _optimizer_companion_from_tag(tag: str) -> Strategy:
    key = tag.replace("_", "-").strip().lower()
    if key in {"buy-hold", "buyhold"}:
        return BuyAndHoldStrategy()
    raise ValueError(f"Unsupported optimizer companion '{tag}'")


class GridSearchOptimizer:
    def __init__(self, base_config: BacktestConfig):
        self.base_config = base_config

    def run(
        self,
        candles: list[Candle],
        entry_drop_grid: list[float],
        take_profit_grid: list[float],
        stop_loss_grid: list[float],
        entry_rise_grid: list[float | None] | None = None,
        allow_short: bool = False,
        build_strategy: Callable[..., Strategy] | None = None,
        strategy_stack_label: str = "threshold",
        combine_mode: str = "all",
    ) -> OptimizationResult:
        rows: list[OptimizationRow] = []
        if entry_rise_grid is None:
            entry_rise_grid = [None]
        if allow_short and entry_rise_grid == [None]:
            entry_rise_grid = [*entry_drop_grid]

        def default_strategy(
            entry_drop: float,
            entry_rise: float | None,
            take_profit: float,
            stop_loss: float,
        ) -> Strategy:
            return ThresholdStrategy(
                entry_drop_pct=entry_drop,
                entry_rise_pct=entry_rise,
                allow_short=allow_short,
            )

        maker = build_strategy or default_strategy

        for entry_drop, entry_rise, take_profit, stop_loss in product(
            entry_drop_grid,
            entry_rise_grid,
            take_profit_grid,
            stop_loss_grid,
        ):
            config = BacktestConfig(
                initial_balance=self.base_config.initial_balance,
                market_type=self.base_config.market_type,
                position_size_pct=self.base_config.position_size_pct,
                use_position_size_pct=self.base_config.use_position_size_pct,
                stake_usd=self.base_config.stake_usd,
                leverage=self.base_config.leverage,
                fee_rate=self.base_config.fee_rate,
                maker_fee_rate=self.base_config.maker_fee_rate,
                slippage_bps=self.base_config.slippage_bps,
                spread_bps=self.base_config.spread_bps,
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit,
                maintenance_margin_rate=self.base_config.maintenance_margin_rate,
                funding_rate_per_interval=self.base_config.funding_rate_per_interval,
                funding_interval_hours=self.base_config.funding_interval_hours,
                funding_enabled=self.base_config.funding_enabled,
                close_open_position_at_end=self.base_config.close_open_position_at_end,
            )
            core = maker(entry_drop, entry_rise, take_profit, stop_loss)
            if isinstance(core, CompositeStrategy):
                stack_label = strategy_display_names(core.strategies)
                row_combine = core.combine
            else:
                stack_label = getattr(core, "name", strategy_stack_label)
                row_combine = combine_mode
            result = BacktestEngine(config).run(candles, core)
            rows.append(
                self._row_from_result(
                    entry_drop=entry_drop,
                    entry_rise=entry_rise,
                    allow_short=allow_short,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    result=result,
                    strategy_stack=stack_label,
                    combine_mode=row_combine,
                    optimizer_strategy="threshold",
                )
            )
        return OptimizationResult(tuple(sorted(rows, key=lambda row: row.final_balance, reverse=True)))

    def run_ut_bot(
        self,
        candles: list[Candle],
        *,
        key_grid: list[float],
        atr_period_grid: list[int],
        lr_period_grid: list[int],
        exit_pct_grid: list[float],
        exit_delay_grid: list[int],
        take_profit_grid: list[float],
        stop_loss_grid: list[float],
        allow_short: bool,
        use_heikin_ashi: bool,
        enable_exit_signals: bool,
        enable_time_range_disable: bool,
        disable_session: str,
        enable_cooldown: bool,
        cooldown_minutes: int,
        companions: tuple[str, ...] = (),
        combine_mode: str = "all",
    ) -> OptimizationResult:
        rows: list[OptimizationRow] = []
        mode = "any" if combine_mode == "any" else "all"

        def build_ut(
            key_value: float,
            atr_period: int,
            lr_period: int,
            exit_pct: float,
            exit_delay: int,
            take_profit: float,
            stop_loss: float,
        ) -> Strategy:
            core = UtBotStrategy(
                key_value=key_value,
                atr_period=atr_period,
                use_heikin_ashi=use_heikin_ashi,
                lr_period=lr_period,
                exit_pct=exit_pct,
                enable_exit_signals=enable_exit_signals,
                exit_delay=exit_delay,
                enable_time_range_disable=enable_time_range_disable,
                disable_session=disable_session,
                enable_cooldown=enable_cooldown,
                cooldown_minutes=cooldown_minutes,
                allow_short=allow_short,
            )
            if not companions:
                return core
            others = [_optimizer_companion_from_tag(tag) for tag in companions]
            return CompositeStrategy((core, *others), combine=mode)

        for key_value, atr_period, lr_period, exit_pct, exit_delay, take_profit, stop_loss in product(
            key_grid,
            atr_period_grid,
            lr_period_grid,
            exit_pct_grid,
            exit_delay_grid,
            take_profit_grid,
            stop_loss_grid,
        ):
            config = BacktestConfig(
                initial_balance=self.base_config.initial_balance,
                market_type=self.base_config.market_type,
                position_size_pct=self.base_config.position_size_pct,
                use_position_size_pct=self.base_config.use_position_size_pct,
                stake_usd=self.base_config.stake_usd,
                leverage=self.base_config.leverage,
                fee_rate=self.base_config.fee_rate,
                maker_fee_rate=self.base_config.maker_fee_rate,
                slippage_bps=self.base_config.slippage_bps,
                spread_bps=self.base_config.spread_bps,
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit,
                maintenance_margin_rate=self.base_config.maintenance_margin_rate,
                funding_rate_per_interval=self.base_config.funding_rate_per_interval,
                funding_interval_hours=self.base_config.funding_interval_hours,
                funding_enabled=self.base_config.funding_enabled,
                close_open_position_at_end=self.base_config.close_open_position_at_end,
            )
            core = build_ut(key_value, atr_period, lr_period, exit_pct, exit_delay, take_profit, stop_loss)
            if isinstance(core, CompositeStrategy):
                stack_label = strategy_display_names(core.strategies)
                row_combine = core.combine
            else:
                stack_label = core.name
                row_combine = combine_mode
            result = BacktestEngine(config).run(candles, core)
            rows.append(
                self._row_from_result(
                    entry_drop=0.0,
                    entry_rise=None,
                    allow_short=allow_short,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    result=result,
                    strategy_stack=stack_label,
                    combine_mode=row_combine,
                    optimizer_strategy="ut_bot",
                    ut_key_value=key_value,
                    ut_atr_period=atr_period,
                    ut_lr_period=lr_period,
                    ut_exit_pct=exit_pct,
                    ut_exit_delay=exit_delay,
                    ut_use_heikin_ashi=use_heikin_ashi,
                )
            )

        return OptimizationResult(tuple(sorted(rows, key=lambda row: row.final_balance, reverse=True)))

    @staticmethod
    def _row_from_result(
        entry_drop: float,
        entry_rise: float | None,
        allow_short: bool,
        take_profit: float,
        stop_loss: float,
        result: BacktestResult,
        strategy_stack: str,
        combine_mode: str,
        *,
        optimizer_strategy: str = "threshold",
        ut_key_value: float | None = None,
        ut_atr_period: int | None = None,
        ut_lr_period: int | None = None,
        ut_exit_pct: float | None = None,
        ut_exit_delay: int | None = None,
        ut_use_heikin_ashi: bool | None = None,
    ) -> OptimizationRow:
        stack_lower = strategy_stack.lower()
        core_token = stack_lower.split("+")[0].strip()
        core_name = "composite" if "+" in strategy_stack else core_token
        return OptimizationRow(
            strategy_name=core_name,
            strategy_stack=strategy_stack,
            combine_mode=combine_mode,
            allow_short=allow_short,
            entry_drop_pct=entry_drop,
            entry_rise_pct=entry_rise,
            take_profit_pct=take_profit,
            stop_loss_pct=stop_loss,
            final_balance=result.final_balance,
            net_pnl=result.net_pnl,
            total_return_pct=result.total_return_pct,
            annualized_return_pct=result.annualized_return_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            max_drawdown_duration_bars=result.max_drawdown_duration_bars,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            calmar_ratio=result.calmar_ratio,
            pnl_r_squared=result.pnl_r_squared,
            win_rate_pct=result.win_rate_pct,
            profit_factor=result.profit_factor,
            payoff_ratio=result.payoff_ratio,
            expectancy=result.expectancy,
            average_trade_pnl=result.average_trade_pnl,
            average_trade_return_pct=result.average_trade_return_pct,
            average_bars_held=result.average_bars_held,
            average_win_pnl=result.average_win_pnl,
            average_loss_pnl=result.average_loss_pnl,
            best_trade_pnl=result.best_trade_pnl,
            worst_trade_pnl=result.worst_trade_pnl,
            longest_win_streak=result.longest_win_streak,
            longest_loss_streak=result.longest_loss_streak,
            total_funding_paid=result.total_funding_paid,
            total_fees_paid=result.total_fees_paid,
            trade_count=len(result.trades),
            optimizer_strategy=optimizer_strategy,
            ut_key_value=ut_key_value,
            ut_atr_period=ut_atr_period,
            ut_lr_period=ut_lr_period,
            ut_exit_pct=ut_exit_pct,
            ut_exit_delay=ut_exit_delay,
            ut_use_heikin_ashi=ut_use_heikin_ashi,
        )
