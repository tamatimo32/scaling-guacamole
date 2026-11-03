from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Candle, MarketType, datetime_to_ms


TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "8h": 8 * 60 * 60_000,
    "12h": 12 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


class BinanceKlineClient:
    """Small Binance public kline client for spot and USD-M futures candles."""

    SPOT_BASE_URL = "https://api.binance.com"
    FUTURES_BASE_URL = "https://fapi.binance.com"

    def fetch_candles(
        self,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
        start_ms: int,
        end_ms: int,
        exchange: str = "binance",
    ) -> list[Candle]:
        if timeframe not in TIMEFRAME_MS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        candles: list[Candle] = []
        cursor = start_ms
        while cursor < end_ms:
            rows = self._request_klines(symbol, market_type, timeframe, cursor, end_ms)
            if not rows:
                break
            batch = [
                self._parse_kline(exchange, symbol, market_type, timeframe, row)
                for row in rows
            ]
            candles.extend(candle for candle in batch if candle.open_time <= end_ms)
            next_cursor = int(rows[-1][0]) + TIMEFRAME_MS[timeframe]
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        return candles

    def _request_klines(
        self,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
        start_ms: int,
        end_ms: int,
    ) -> list[list[object]]:
        base_url = self.FUTURES_BASE_URL if market_type == "futures" else self.SPOT_BASE_URL
        path = "/fapi/v1/klines" if market_type == "futures" else "/api/v3/klines"
        query = urlencode(
            {
                "symbol": symbol.upper(),
                "interval": timeframe,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        request = Request(
            f"{base_url}{path}?{query}",
            headers={"User-Agent": "futures-trading-simulator/0.1"},
        )
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)

    @staticmethod
    def _parse_kline(
        exchange: str,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
        row: list[object],
    ) -> Candle:
        return Candle(
            exchange=exchange,
            symbol=symbol.upper(),
            market_type=market_type,
            timeframe=timeframe,
            open_time=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            close_time=int(row[6]),
        )

    def fetch_funding_rates(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
    ) -> list[dict[str, float | int | str]]:
        """Pull Binance USD-M funding rate history for `symbol`."""

        rows: list[dict[str, float | int | str]] = []
        cursor = start_ms
        while cursor < end_ms:
            query = urlencode(
                {
                    "symbol": symbol.upper(),
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                }
            )
            request = Request(
                f"{self.FUTURES_BASE_URL}/fapi/v1/fundingRate?{query}",
                headers={"User-Agent": "futures-trading-simulator/0.1"},
            )
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
            batch = json.loads(payload)
            if not batch:
                break
            for entry in batch:
                rows.append(
                    {
                        "symbol": symbol.upper(),
                        "funding_time": int(entry.get("fundingTime", 0)),
                        "funding_rate": float(entry.get("fundingRate", 0.0)),
                        "mark_price": float(entry.get("markPrice", 0.0)),
                    }
                )
            next_cursor = int(batch[-1].get("fundingTime", cursor)) + 1
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        return rows


def average_funding_rate(rows: list[dict[str, float | int | str]]) -> float:
    samples = [float(row["funding_rate"]) for row in rows if row.get("funding_rate") is not None]
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def last_days_range(days: int) -> tuple[int, int]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return datetime_to_ms(start), datetime_to_ms(end)


def generate_sample_candles(
    symbol: str,
    market_type: MarketType,
    timeframe: str,
    days: int,
    exchange: str = "sample",
    seed: int = 42,
    start_price: float = 65_000.0,
) -> list[Candle]:
    """Synthesize candles with regime shifts, vol clusters, and wick asymmetry.

    The generator stays deterministic for a given seed/symbol/timeframe so that
    optimizer runs are reproducible while still exercising trend, chop, and
    sudden-shock conditions that a percentage strategy must survive.
    """

    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    stable_offset = sum(ord(char) for char in f"{symbol}:{market_type}:{timeframe}")
    rng = random.Random(seed + stable_offset)
    interval_ms = TIMEFRAME_MS[timeframe]
    now = datetime.now(timezone.utc)
    end_ms = align_down_ms(datetime_to_ms(now), interval_ms)
    start_ms = end_ms - days * 24 * 60 * 60_000
    count = max(1, math.ceil((end_ms - start_ms) / interval_ms))

    bars_per_day = max(1, int(round(86_400_000 / interval_ms)))
    base_vol = 0.0035 + 0.0015 * math.sqrt(interval_ms / TIMEFRAME_MS["1h"])
    regime_length = max(8, int(bars_per_day * rng.uniform(2.5, 5.5)))

    price = start_price
    open_price = start_price
    candles: list[Candle] = []
    regime_drift = rng.gauss(0, 0.0008)
    vol = base_vol
    for index in range(count):
        open_time = start_ms + index * interval_ms
        close_time = open_time + interval_ms - 1

        if index % regime_length == 0:
            regime_drift = rng.gauss(0, 0.0010)
            vol = base_vol * rng.uniform(0.65, 1.6)
            regime_length = max(8, int(bars_per_day * rng.uniform(2.0, 6.5)))

        vol = max(base_vol * 0.4, vol * 0.92 + abs(rng.gauss(0, base_vol * 0.5)) * 0.4)
        intraday_cycle = 0.0006 * math.sin((open_time / 3_600_000) * math.pi / 12.0)
        shock = rng.gauss(0, vol)
        if rng.random() < 0.012:
            shock += rng.choice([-1.0, 1.0]) * vol * rng.uniform(2.0, 3.5)

        change = regime_drift + intraday_cycle + shock
        close = max(1.0, open_price * (1 + change))

        body_high = max(open_price, close)
        body_low = min(open_price, close)
        upper_wick = abs(rng.gauss(0, vol * 0.7))
        lower_wick = abs(rng.gauss(0, vol * 0.7))
        high = body_high * (1 + upper_wick)
        low = max(0.5, body_low * (1 - lower_wick))

        body_size = abs(close - open_price) / max(1e-9, open_price)
        volume = max(50.0, rng.gauss(1400 + body_size * 12_000, 350))

        candles.append(
            Candle(
                exchange=exchange,
                symbol=symbol.upper(),
                market_type=market_type,
                timeframe=timeframe,
                open_time=open_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                close_time=close_time,
            )
        )
        price = close
        open_price = close
    return candles


def align_down_ms(value_ms: int, interval_ms: int) -> int:
    return value_ms - (value_ms % interval_ms)


def merge_candle_batches(batches: Iterable[Iterable[Candle]]) -> list[Candle]:
    merged: dict[int, Candle] = {}
    for batch in batches:
        for candle in batch:
            merged[candle.open_time] = candle
    return [merged[key] for key in sorted(merged)]
