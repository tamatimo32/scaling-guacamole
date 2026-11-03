from __future__ import annotations

from dataclasses import dataclass, field

from .models import BacktestResult, Candle, EquityPoint, MarketType, Side, Signal, Trade
from .strategies import Strategy, StrategyContext


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest configuration tuned to mirror Binance USD-M futures defaults.

    Defaults reflect Binance public fee/funding schedules so simulations stay
    close to live trading without forcing the caller to specify every value.
    """

    initial_balance: float = 10_000.0
    market_type: MarketType = "futures"
    position_size_pct: float = 0.25
    """Fraction of balance used as margin (futures) or notional (spot) when
    ``use_position_size_pct`` is True."""
    use_position_size_pct: bool = True
    """When False, each new position uses ``stake_usd`` (capped by available balance)."""
    stake_usd: float | None = None
    """Fixed margin (futures) or notional (spot) in account currency when
    ``use_position_size_pct`` is False."""
    leverage: float = 3.0
    fee_rate: float = 0.0005
    maker_fee_rate: float | None = 0.0002
    slippage_bps: float = 1.5
    spread_bps: float = 1.0
    stop_loss_pct: float | None = 0.008
    take_profit_pct: float | None = 0.012
    maintenance_margin_rate: float = 0.004
    funding_rate_per_interval: float = 0.0001
    funding_interval_hours: float = 8.0
    funding_enabled: bool = True
    """When False, perpetual-style funding accrual is skipped (research mode)."""
    close_open_position_at_end: bool = True

    def validate(self) -> None:
        if self.initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        if self.use_position_size_pct:
            if not 0 < self.position_size_pct <= 1:
                raise ValueError("position_size_pct must be between 0 and 1")
        else:
            if self.stake_usd is None or self.stake_usd <= 0:
                raise ValueError("stake_usd must be positive when use_position_size_pct is False")
        if self.market_type == "futures" and self.leverage <= 0:
            raise ValueError("leverage must be positive")
        if self.market_type == "spot" and self.leverage != 1.0:
            raise ValueError("spot backtests must use leverage 1.0")
        if self.fee_rate < 0:
            raise ValueError("fee_rate cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")
        if self.spread_bps < 0:
            raise ValueError("spread_bps cannot be negative")
        if self.funding_interval_hours <= 0:
            raise ValueError("funding_interval_hours must be positive")


@dataclass
class Position:
    symbol: str
    market_type: MarketType
    side: Side
    entry_time: int
    entry_price: float
    quantity: float
    margin: float
    entry_fee: float
    cost_basis: float
    funding_paid: float = 0.0
    bars_held: int = 0
    last_funding_ms: int = 0


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        config.validate()
        self.config = config

    def run(
        self,
        candles: list[Candle],
        strategy: Strategy,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> BacktestResult:
        if len(candles) < 2:
            raise ValueError("At least two candles are required for a backtest")

        candles = sorted(candles, key=lambda candle: candle.open_time)
        market_type = self.config.market_type
        symbol = symbol or candles[0].symbol
        timeframe = timeframe or candles[0].timeframe
        balance = self.config.initial_balance
        position: Position | None = None
        pending_signal = Signal.hold()
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        for index, candle in enumerate(candles):
            if pending_signal.action in {"enter_long", "enter_short", "exit"}:
                balance, position, maybe_trade = self._execute_signal(
                    pending_signal, candle, balance, position
                )
                if maybe_trade is not None:
                    trades.append(maybe_trade)
                pending_signal = Signal.hold()

            if position is not None:
                balance = self._apply_funding(position, candle, balance)
                position.bars_held += 1

            if position is not None:
                risk_exit = self._risk_exit_signal(candle, position)
                if risk_exit is not None:
                    balance, position, trade = self._close_position(
                        position=position,
                        candle=candle,
                        balance=balance,
                        raw_price=risk_exit[0],
                        reason=risk_exit[1],
                    )
                    trades.append(trade)

            equity = self._mark_to_market(balance, position, candle.close)
            equity_curve.append(
                EquityPoint(
                    time=candle.close_time,
                    balance=balance,
                    equity=equity,
                    close_price=candle.close,
                )
            )

            context = StrategyContext(
                index=index,
                has_position=position is not None,
                position_side=position.side if position else None,
                previous_candle=candles[index - 1] if index > 0 else None,
                balance=balance,
                equity=equity,
            )
            pending_signal = strategy.on_candle(candle, context)

        if position is not None and self.config.close_open_position_at_end:
            last = candles[-1]
            balance, position, trade = self._close_position(
                position=position,
                candle=last,
                balance=balance,
                raw_price=last.close,
                reason="end_of_backtest",
            )
            trades.append(trade)
            equity_curve.append(
                EquityPoint(
                    time=last.close_time,
                    balance=balance,
                    equity=balance,
                    close_price=last.close,
                )
            )

        return BacktestResult(
            symbol=symbol,
            market_type=market_type,
            timeframe=timeframe,
            initial_balance=self.config.initial_balance,
            final_balance=balance,
            trades=tuple(trades),
            equity_curve=tuple(equity_curve),
        )

    def _execute_signal(
        self,
        signal: Signal,
        candle: Candle,
        balance: float,
        position: Position | None,
    ) -> tuple[float, Position | None, Trade | None]:
        if signal.action == "exit" and position is not None:
            balance, position, trade = self._close_position(
                position=position,
                candle=candle,
                balance=balance,
                raw_price=candle.open,
                reason=signal.reason,
            )
            return balance, position, trade

        if position is not None:
            return balance, position, None

        if signal.action == "enter_long":
            position = self._open_position("long", candle, balance)
        elif signal.action == "enter_short":
            if self.config.market_type != "futures":
                return balance, position, None
            position = self._open_position("short", candle, balance)
        else:
            return balance, position, None

        balance -= position.margin + position.entry_fee
        return balance, position, None

    def _open_position(self, side: Side, candle: Candle, balance: float) -> Position:
        entry_price = self._apply_market_friction(candle.open, side, "entry")
        if self.config.market_type == "spot":
            if self.config.use_position_size_pct:
                notional = balance * self.config.position_size_pct
            else:
                max_n = balance / (1.0 + self.config.fee_rate)
                notional = min(self.config.stake_usd or 0.0, max_n)
            entry_fee = notional * self.config.fee_rate
            if notional + entry_fee > balance:
                notional = balance / (1.0 + self.config.fee_rate)
                entry_fee = notional * self.config.fee_rate
            margin = notional
            quantity = notional / entry_price
            cost_basis = notional + entry_fee
        else:
            if self.config.use_position_size_pct:
                margin = balance * self.config.position_size_pct
            else:
                max_margin = balance / (1.0 + self.config.leverage * self.config.fee_rate)
                margin = min(self.config.stake_usd or 0.0, max_margin)
            notional = margin * self.config.leverage
            entry_fee = notional * self.config.fee_rate
            quantity = notional / entry_price
            cost_basis = margin + entry_fee

        return Position(
            symbol=candle.symbol,
            market_type=self.config.market_type,
            side=side,
            entry_time=candle.open_time,
            entry_price=entry_price,
            quantity=quantity,
            margin=margin,
            entry_fee=entry_fee,
            cost_basis=cost_basis,
            last_funding_ms=candle.open_time,
        )

    def _apply_funding(
        self,
        position: Position,
        candle: Candle,
        balance: float,
    ) -> float:
        if self.config.market_type != "futures":
            return balance
        if not self.config.funding_enabled:
            return balance
        if self.config.funding_rate_per_interval == 0:
            return balance

        interval_ms = int(self.config.funding_interval_hours * 3_600_000)
        if interval_ms <= 0:
            return balance

        first_funding = self._next_funding_time(position.last_funding_ms, interval_ms)
        candle_end = candle.close_time
        notional = position.quantity * candle.close
        funding_count = 0
        funding_time = first_funding
        while funding_time <= candle_end:
            funding_count += 1
            funding_time += interval_ms
        if funding_count == 0:
            return balance

        funding_charge = notional * self.config.funding_rate_per_interval * funding_count
        if position.side == "short":
            funding_charge = -funding_charge
        balance -= funding_charge
        position.funding_paid += funding_charge
        position.last_funding_ms = first_funding + (funding_count - 1) * interval_ms
        return balance

    @staticmethod
    def _next_funding_time(last_funding_ms: int, interval_ms: int) -> int:
        offset = last_funding_ms % interval_ms
        if offset == 0:
            return last_funding_ms + interval_ms
        return last_funding_ms - offset + interval_ms

    def _close_position(
        self,
        position: Position,
        candle: Candle,
        balance: float,
        raw_price: float,
        reason: str,
    ) -> tuple[float, None, Trade]:
        exit_price = self._apply_market_friction(raw_price, position.side, "exit")
        exit_notional = position.quantity * exit_price
        exit_fee = exit_notional * self.config.fee_rate
        gross_pnl = self._gross_pnl(position, exit_price)

        if self.config.market_type == "spot":
            net_proceeds = exit_notional - exit_fee
            balance += net_proceeds
            net_pnl = net_proceeds - position.cost_basis
            denominator = position.cost_basis
        else:
            position_equity = position.margin + gross_pnl - exit_fee
            if reason == "liquidation":
                position_equity = max(0.0, position_equity)
            balance += position_equity
            net_pnl = position_equity - position.margin - position.entry_fee - position.funding_paid
            denominator = position.margin

        return_pct = (net_pnl / denominator * 100.0) if denominator > 0 else 0.0
        trade = Trade(
            symbol=position.symbol,
            market_type=position.market_type,
            side=position.side,
            entry_time=position.entry_time,
            exit_time=candle.open_time,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            margin=position.margin,
            entry_fee=position.entry_fee,
            exit_fee=exit_fee,
            funding_paid=position.funding_paid,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            return_pct=return_pct,
            bars_held=position.bars_held,
            exit_reason=reason,
        )
        return balance, None, trade

    def _risk_exit_signal(self, candle: Candle, position: Position) -> tuple[float, str] | None:
        liquidation = self._liquidation_price(position)
        stop_price = self._stop_loss_price(position)
        take_profit_price = self._take_profit_price(position)

        if position.side == "long":
            liquidation_hit = liquidation is not None and candle.low <= liquidation
            stop_hit = stop_price is not None and candle.low <= stop_price
            target_hit = take_profit_price is not None and candle.high >= take_profit_price
        else:
            liquidation_hit = liquidation is not None and candle.high >= liquidation
            stop_hit = stop_price is not None and candle.high >= stop_price
            target_hit = take_profit_price is not None and candle.low <= take_profit_price

        if stop_hit and liquidation_hit:
            if position.side == "long":
                return (max(stop_price, liquidation), "stop_loss")
            return (min(stop_price, liquidation), "stop_loss")
        if stop_hit:
            return stop_price, "stop_loss"
        if liquidation_hit:
            return liquidation, "liquidation"
        if target_hit:
            return take_profit_price, "take_profit"
        return None

    def _stop_loss_price(self, position: Position) -> float | None:
        if self.config.stop_loss_pct is None:
            return None
        pct = abs(self.config.stop_loss_pct)
        if position.side == "long":
            return position.entry_price * (1.0 - pct)
        return position.entry_price * (1.0 + pct)

    def _take_profit_price(self, position: Position) -> float | None:
        if self.config.take_profit_pct is None:
            return None
        pct = abs(self.config.take_profit_pct)
        if position.side == "long":
            return position.entry_price * (1.0 + pct)
        return position.entry_price * (1.0 - pct)

    def _liquidation_price(self, position: Position) -> float | None:
        if self.config.market_type != "futures":
            return None
        leverage = self.config.leverage
        maintenance = self.config.maintenance_margin_rate
        if leverage <= 0:
            return None
        if position.side == "long":
            return position.entry_price * (1.0 - 1.0 / leverage + maintenance)
        return position.entry_price * (1.0 + 1.0 / leverage - maintenance)

    def _mark_to_market(
        self,
        balance: float,
        position: Position | None,
        mark_price: float,
    ) -> float:
        if position is None:
            return balance
        if self.config.market_type == "spot":
            return balance + position.quantity * mark_price
        return balance + position.margin + self._gross_pnl(position, mark_price)

    def _gross_pnl(self, position: Position, price: float) -> float:
        if position.side == "long":
            return (price - position.entry_price) * position.quantity
        return (position.entry_price - price) * position.quantity

    def _apply_market_friction(self, price: float, side: Side, phase: str) -> float:
        slip = self.config.slippage_bps / 10_000.0
        spread_half = (self.config.spread_bps / 2.0) / 10_000.0
        cost = slip + spread_half
        if cost == 0:
            return price
        if phase == "entry":
            return price * (1 + cost) if side == "long" else price * (1 - cost)
        return price * (1 - cost) if side == "long" else price * (1 + cost)
