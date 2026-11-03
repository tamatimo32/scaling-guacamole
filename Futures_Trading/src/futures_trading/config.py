from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXCHANGE = "binance"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_MARKET_TYPE = "futures"
DEFAULT_TIMEFRAMES = ("1h", "4h", "8h", "12h")
DEFAULT_DB_PATH = Path("data") / "market_data.sqlite"


@dataclass(frozen=True)
class RuntimeConfig:
    db_path: Path = DEFAULT_DB_PATH
    exchange: str = DEFAULT_EXCHANGE
    symbol: str = DEFAULT_SYMBOL
    market_type: str = DEFAULT_MARKET_TYPE
    timeframes: tuple[str, ...] = DEFAULT_TIMEFRAMES


def normalize_market_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"spot", "futures"}:
        raise ValueError("market_type must be 'spot' or 'futures'")
    return normalized
