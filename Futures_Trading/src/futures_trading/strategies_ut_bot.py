"""UT Bot Alerts strategy (Pine parity).

Heikin Ashi closes are synthesized from regular OHLC so no separate candle feed is required.
"""

from __future__ import annotations

from collections import deque

from .models import Candle, Signal
from .strategies import StrategyContext


def _utc_minute_of_day(open_time_ms: int) -> int:
    ms_per_day = 86_400_000
    return int((open_time_ms % ms_per_day) // 60_000)


def disabled_session_matches(open_time_ms: int, session_spec: str) -> bool:
    """True when candle open UTC falls inside a Pine-like ``HHMM-HHMM`` session (cross-midnight OK)."""

    spec = session_spec.strip()
    if not spec:
        return False
    parts = spec.replace("–", "-").split("-", 1)
    if len(parts) != 2:
        return False
    try:
        start_hm = int(parts[0].strip())
        end_hm = int(parts[1].strip())
    except ValueError:
        return False
    start_min = (start_hm // 100) * 60 + (start_hm % 100)
    end_min = (end_hm // 100) * 60 + (end_hm % 100)
    now = _utc_minute_of_day(open_time_ms)
    if start_min <= end_min:
        return start_min <= now <= end_min
    return now >= start_min or now <= end_min


def linreg_endpoint(values: list[float]) -> float:
    """Regression fitted value at the final sample (``ta.linreg(..., offset=0)`` endpoint)."""

    n = len(values)
    if n < 2:
        return values[-1] if values else 0.0
    xs = list(range(n))
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        return mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / ss_xx
    intercept = mean_y - slope * mean_x
    return slope * (n - 1) + intercept


def _calc_trailing_stop(prev_stop: float, src: float, src_prev: float, n_loss: float) -> float:
    """Mirrors Pine ``f_calcTrailingStop`` with ``nz(prev,0)`` semantics."""

    p = prev_stop
    if src > p and src_prev > p:
        return max(p, src - n_loss)
    if src < p and src_prev < p:
        return min(p, src + n_loss)
    if src > p:
        return src - n_loss
    return src + n_loss


class UtBotStrategy:
    """Stateful UT Bot Alerts strategy aligned with the user's Pine indicator."""

    name = "ut_bot"

    def __init__(
        self,
        *,
        key_value: float = 2.0,
        atr_period: int = 7,
        use_heikin_ashi: bool = False,
        lr_period: int = 20,
        exit_pct: float = 0.006,
        enable_exit_signals: bool = True,
        exit_delay: int = 1,
        enable_time_range_disable: bool = False,
        disable_session: str = "2200-0500",
        enable_cooldown: bool = False,
        cooldown_minutes: int = 5,
        allow_short: bool = False,
    ) -> None:
        if atr_period < 1:
            raise ValueError("atr_period must be >= 1")
        if lr_period < 2:
            raise ValueError("lr_period must be >= 2")
        if exit_delay < 1:
            raise ValueError("exit_delay must be >= 1")
        self.key_value = float(key_value)
        self.atr_period = int(atr_period)
        self.use_heikin_ashi = bool(use_heikin_ashi)
        self.lr_period = int(lr_period)
        self.exit_pct = float(exit_pct)
        self.enable_exit_signals = bool(enable_exit_signals)
        self.exit_delay = int(exit_delay)
        self.enable_time_range_disable = bool(enable_time_range_disable)
        self.disable_session = str(disable_session)
        self.enable_cooldown = bool(enable_cooldown)
        self.cooldown_minutes = int(cooldown_minutes)
        self.allow_short = bool(allow_short)

        self._prev_regular_close: float | None = None
        self._ha_open: float | None = None
        self._ha_close: float | None = None

        self._atr_rma: float | None = None
        self._tr_seed_sum = 0.0
        self._tr_seed_count = 0

        self._trail_prev = 0.0
        self._src_prev: float | None = None
        self._ema_prev: float | None = None

        self._ut_signal = 0

        self._exit_short_counter = 0
        self._exit_long_counter = 0
        self._exit_long_fired = False
        self._exit_short_fired = False

        self._last_signal_time_ms = 0

        self._had_exit_long_prev = False
        self._had_exit_short_prev = False

        self._src_window: deque[float] = deque(maxlen=self.lr_period)
        self._warmup_required = max(self.lr_period, self.atr_period)
        self._processed_bars = 0

    def _heikin_step(self, candle: Candle) -> tuple[float, float, float, float]:
        ha_close = (candle.open + candle.high + candle.low + candle.close) / 4.0
        if self._ha_open is None:
            ha_open = (candle.open + candle.close) / 2.0
        else:
            ha_open = (self._ha_open + self._ha_close) / 2.0  # type: ignore[operator]
        ha_high = max(candle.high, ha_open, ha_close)
        ha_low = min(candle.low, ha_open, ha_close)
        self._ha_open = ha_open
        self._ha_close = ha_close
        return ha_open, ha_high, ha_low, ha_close

    def _update_atr(self, candle: Candle) -> float:
        prev_close = self._prev_regular_close
        if prev_close is None:
            tr = candle.high - candle.low
        else:
            tr = max(
                candle.high - candle.low,
                abs(candle.high - prev_close),
                abs(candle.low - prev_close),
            )

        period = self.atr_period
        self._prev_regular_close = candle.close

        if self._atr_rma is None:
            self._tr_seed_sum += tr
            self._tr_seed_count += 1
            if self._tr_seed_count < period:
                return self._tr_seed_sum / self._tr_seed_count
            self._atr_rma = self._tr_seed_sum / period
            return self._atr_rma

        self._atr_rma = (self._atr_rma * (period - 1) + tr) / period
        return self._atr_rma

    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        _, _, _, ha_close = self._heikin_step(candle)
        src = ha_close if self.use_heikin_ashi else candle.close

        x_atr = self._update_atr(candle)
        n_loss = self.key_value * x_atr

        trail_prev = self._trail_prev
        if self._src_prev is None:
            trail = trail_prev
        else:
            trail = _calc_trailing_stop(trail_prev, src, self._src_prev, n_loss)
        self._trail_prev = trail

        ema_val = src  # ``ta.ema(src, 1)`` collapses to ``src``
        ema_prev = self._ema_prev if self._ema_prev is not None else ema_val

        strong_buy = (
            ema_prev <= trail_prev
            and ema_val > trail
            and src > trail
            and ema_val > ema_prev
        )
        strong_sell = (
            ema_prev >= trail_prev
            and ema_val < trail
            and src < trail
            and ema_val < ema_prev
        )

        buy_buffer = strong_buy and src > trail + 0.2 * x_atr
        sell_buffer = strong_sell and src < trail - 0.2 * x_atr

        prev_ut = self._ut_signal
        if buy_buffer:
            self._ut_signal = 1
        elif sell_buffer:
            self._ut_signal = -1

        self._src_window.append(src)
        lr_line = linreg_endpoint(list(self._src_window)) if len(self._src_window) >= self.lr_period else src

        exit_short_cond = self._ut_signal == -1 and src > lr_line * (1.0 + self.exit_pct)
        exit_long_cond = self._ut_signal == 1 and src < lr_line * (1.0 - self.exit_pct)

        if exit_short_cond:
            self._exit_short_counter += 1
        else:
            self._exit_short_counter = 0

        if exit_long_cond:
            self._exit_long_counter += 1
        else:
            self._exit_long_counter = 0

        exit_long = self.enable_exit_signals and self._exit_long_counter >= self.exit_delay
        exit_short = self.enable_exit_signals and self._exit_short_counter >= self.exit_delay

        exit_long_once = exit_long and not self._had_exit_long_prev
        exit_short_once = exit_short and not self._had_exit_short_prev

        self._had_exit_long_prev = exit_long
        self._had_exit_short_prev = exit_short

        if self._ut_signal != prev_ut:
            self._exit_long_fired = False
            self._exit_short_fired = False

        exit_long_once_final = exit_long_once and not self._exit_long_fired
        exit_short_once_final = exit_short_once and not self._exit_short_fired

        if exit_long_once_final:
            self._exit_long_fired = True
        if exit_short_once_final:
            self._exit_short_fired = True

        in_disabled_session = (
            self.enable_time_range_disable and disabled_session_matches(candle.open_time, self.disable_session)
        )
        cooldown_active = self.enable_cooldown and (
            candle.open_time - self._last_signal_time_ms < self.cooldown_minutes * 60_000
        )
        disable_signals = in_disabled_session or cooldown_active

        filtered_buy = buy_buffer and not disable_signals
        filtered_sell = sell_buffer and not disable_signals
        filtered_exit_long = exit_long_once_final and not disable_signals
        filtered_exit_short = exit_short_once_final and not disable_signals

        if filtered_buy or filtered_sell or filtered_exit_long or filtered_exit_short:
            self._last_signal_time_ms = candle.open_time

        self._src_prev = src
        self._ema_prev = ema_val

        self._processed_bars += 1
        warmup = self._processed_bars < self._warmup_required
        if warmup:
            return Signal.hold()

        if context.has_position:
            side = context.position_side
            if side == "long":
                if filtered_exit_long:
                    return Signal(action="exit", reason="ut_exit_long")
                if filtered_sell:
                    return Signal(action="exit", reason="ut_short_signal")
            elif side == "short":
                if filtered_exit_short:
                    return Signal(action="exit", reason="ut_exit_short")
                if filtered_buy:
                    return Signal(action="exit", reason="ut_long_signal")

        if context.has_position:
            return Signal.hold()

        if filtered_buy:
            return Signal(action="enter_long", reason="ut_buy_buffer")
        if filtered_sell and self.allow_short:
            return Signal(action="enter_short", reason="ut_sell_buffer")

        return Signal.hold()
