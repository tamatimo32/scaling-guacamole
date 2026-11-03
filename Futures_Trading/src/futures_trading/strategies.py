from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .models import Candle, Signal


@dataclass(frozen=True)
class StrategyContext:
    index: int
    has_position: bool
    position_side: str | None
    previous_candle: Candle | None
    balance: float
    equity: float


class Strategy(Protocol):
    name: str

    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        ...


class BuyAndHoldStrategy:
    name = "buy_and_hold"

    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        if context.index == 0 and not context.has_position:
            return Signal(action="enter_long", reason="first_candle_close")
        return Signal.hold()


@dataclass(frozen=True)
class ThresholdStrategy:
    """Simple percentage strategy used as the first optimizer target.

    It can later be replaced by indicator strategies without changing the simulator.
    """

    entry_drop_pct: float = 0.004
    entry_rise_pct: float | None = None
    allow_short: bool = False
    name: str = "threshold"

    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        if context.has_position or context.previous_candle is None:
            return Signal.hold()

        previous_close = context.previous_candle.close
        if previous_close <= 0:
            return Signal.hold()

        change_pct = (candle.close / previous_close) - 1.0
        if change_pct <= -abs(self.entry_drop_pct):
            return Signal(
                action="enter_long",
                reason="entry_drop_threshold",
                metadata={"change_pct": change_pct},
            )

        if self.allow_short and self.entry_rise_pct is not None:
            if change_pct >= abs(self.entry_rise_pct):
                return Signal(
                    action="enter_short",
                    reason="entry_rise_threshold",
                    metadata={"change_pct": change_pct},
                )

        return Signal.hold()


@dataclass(frozen=True)
class CompositeStrategy:
    """Run several strategies together (for multi-signal / filter stacks).

    * ``all``: open only when every child returns the same ``enter_long`` or
      ``enter_short`` on the same candle (unanimous entries). If any child
      requests ``exit`` while flat, the exit is ignored; when a position is
      open, the first ``exit`` wins.
    * ``any``: first non-hold signal wins in *declaration order* (useful with
      a fast trigger like buy-and-hold followed by a gated rule set).
    Registered strategies can be appended later without changing this class.
    """

    strategies: tuple[Strategy, ...]
    combine: str = "all"
    name: str = "composite"

    def __post_init__(self) -> None:
        if not self.strategies:
            raise ValueError("CompositeStrategy requires at least one child strategy")
        if self.combine not in {"all", "any"}:
            raise ValueError("combine must be 'all' or 'any'")

    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        signals = [strategy.on_candle(candle, context) for strategy in self.strategies]

        if context.has_position:
            for signal in signals:
                if signal.action == "exit":
                    return signal
            return Signal.hold()

        if self.combine == "any":
            for signal in signals:
                if signal.action in {"enter_long", "enter_short"}:
                    return signal
            return Signal.hold()

        # all: unanimous entry only
        entries = [signal for signal in signals if signal.action in {"enter_long", "enter_short"}]
        if len(entries) != len(self.strategies):
            return Signal.hold()
        actions = {entry.action for entry in entries}
        if len(actions) != 1:
            return Signal.hold()
        return entries[0]


def strategy_display_names(stack: Sequence[Strategy]) -> str:
    """Human-readable stack label for optimizer rows and UIs."""

    return "+".join(getattr(strategy, "name", type(strategy).__name__) for strategy in stack)
