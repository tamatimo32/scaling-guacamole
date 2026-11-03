from __future__ import annotations

from contextlib import closing
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .models import Candle, MarketType


SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market_type TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open_time INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    close_time INTEGER NOT NULL,
    PRIMARY KEY (exchange, symbol, market_type, timeframe, open_time)
);

CREATE INDEX IF NOT EXISTS idx_candles_lookup
ON candles(exchange, symbol, market_type, timeframe, open_time);
"""


class CandleStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def upsert_candles(self, candles: Iterable[Candle]) -> int:
        rows = [
            (
                candle.exchange,
                candle.symbol,
                candle.market_type,
                candle.timeframe,
                candle.open_time,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
                candle.close_time,
            )
            for candle in candles
        ]
        if not rows:
            return 0
        self.initialize()
        with closing(self._connect()) as conn:
            conn.executemany(
                """
                INSERT INTO candles (
                    exchange, symbol, market_type, timeframe, open_time,
                    open, high, low, close, volume, close_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exchange, symbol, market_type, timeframe, open_time)
                DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    close_time = excluded.close_time
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[Candle]:
        self.initialize()
        clauses = [
            "exchange = ?",
            "symbol = ?",
            "market_type = ?",
            "timeframe = ?",
        ]
        params: list[object] = [exchange, symbol, market_type, timeframe]
        if start_ms is not None:
            clauses.append("open_time >= ?")
            params.append(start_ms)
        if end_ms is not None:
            clauses.append("open_time <= ?")
            params.append(end_ms)
        where = " AND ".join(clauses)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"""
                SELECT exchange, symbol, market_type, timeframe, open_time,
                       open, high, low, close, volume, close_time
                FROM candles
                WHERE {where}
                ORDER BY open_time ASC
                """,
                params,
            ).fetchall()
        return [
            Candle(
                exchange=row["exchange"],
                symbol=row["symbol"],
                market_type=row["market_type"],
                timeframe=row["timeframe"],
                open_time=row["open_time"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                close_time=row["close_time"],
            )
            for row in rows
        ]

    def count_candles(
        self,
        exchange: str,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
    ) -> int:
        self.initialize()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM candles
                WHERE exchange = ? AND symbol = ? AND market_type = ? AND timeframe = ?
                """,
                (exchange, symbol, market_type, timeframe),
            ).fetchone()
        return int(row["count"])

    def get_time_bounds(
        self,
        exchange: str,
        symbol: str,
        market_type: MarketType,
        timeframe: str,
    ) -> tuple[int | None, int | None]:
        self.initialize()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT MIN(open_time) AS first_open, MAX(open_time) AS last_open
                FROM candles
                WHERE exchange = ? AND symbol = ? AND market_type = ? AND timeframe = ?
                """,
                (exchange, symbol, market_type, timeframe),
            ).fetchone()
        return row["first_open"], row["last_open"]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
