
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import subprocess
from threading import Timer
from urllib.parse import parse_qs, urlparse
import webbrowser

from .config import DEFAULT_DB_PATH, normalize_market_type
from .data_sources import (
    BinanceKlineClient,
    TIMEFRAME_MS,
    average_funding_rate,
    generate_sample_candles,
    last_days_range,
)
from .grids import parse_float_grid, parse_int_grid, parse_optional_float_grid
from .models import BacktestResult, Trade, ms_to_datetime
from .optimizer import GridSearchOptimizer, OptimizationRow
from .simulator import BacktestConfig, BacktestEngine
from .storage import CandleStore
from .strategies import (
    BuyAndHoldStrategy,
    CompositeStrategy,
    Strategy,
    ThresholdStrategy,
    strategy_display_names,
)
from .strategies_ut_bot import UtBotStrategy
from .web_html import DASHBOARD_HTML


MAX_GRID_COMBINATIONS = 5_000

MS_PER_DAY = 86_400_000
"""Milliseconds in a UTC day (dashboard + history windows)."""


def _candles_wall_span_ms(candles: list) -> int:
    """Wall-clock chart span from the open of bar 1 through the close of the last bar."""

    if len(candles) < 2:
        return 0
    return max(0, candles[-1].close_time - candles[0].open_time)


def _stored_open_bounds_span_ms(candles: list) -> int:
    if len(candles) < 2:
        return 0
    return max(0, candles[-1].open_time - candles[0].open_time)


def _maybe_expand_binance_history(
    *,
    store: CandleStore,
    candles: list,
    exchange: str,
    symbol: str,
    market_type: str,
    timeframe: str,
    requested_days: int,
) -> tuple[list, str | None]:
    """If SQLite already contains candles but the series is shorter than requested_days, merge Binance."""

    exchange_l = exchange.strip().lower()
    resolved_mt = normalize_market_type(str(market_type or "futures"))
    tf = timeframe.strip()
    if exchange_l != "binance" or len(candles) < 2 or tf not in TIMEFRAME_MS:
        return candles, None
    days = max(1, int(requested_days))
    target_ms = int(days * MS_PER_DAY)
    have_ms = _stored_open_bounds_span_ms(candles)
    if target_ms <= 0 or have_ms <= 0:
        return candles, None
    if have_ms >= int(target_ms * 0.92):
        return candles, None

    days_observed = round(have_ms / MS_PER_DAY, 4)
    try:
        client = BinanceKlineClient()
        start_ms, end_ms = last_days_range(days)
        fetched = client.fetch_candles(
            symbol=symbol,
            market_type=resolved_mt,
            timeframe=tf,
            start_ms=start_ms,
            end_ms=end_ms,
            exchange=exchange_l,
        )
        if not fetched:
            return candles, (
                f"SQLite only had ~{days_observed} calendar days on file for "
                f"{symbol} {tf}; Binance returned no extra rows."
            )
        store.upsert_candles(fetched)
        refreshed = store.get_candles(exchange_l, symbol, resolved_mt, tf)
        fresh_ms = _stored_open_bounds_span_ms(refreshed)
        nd = round(fresh_ms / MS_PER_DAY, 2) if fresh_ms else days_observed
        note = (
            f"SQLite history was shorter than ~{days} requested days (~{days_observed} d on disk); "
            f"merged Binance into the database (~{len(fetched)} fetched rows → ~{nd} d contiguous open-time span)."
        )
        return refreshed, note
    except Exception as exc:
        return candles, (
            f"SQLite only had ~{days_observed} days for this symbol/tf; Binance refill failed ({exc}). "
            "Use Market Data tab to pull more candles."
        )
class DashboardServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets two unrelated processes silently bind to the
    # same port; one wins and the browser ends up talking to the wrong server.
    # Disabling it makes the bind fail loudly so the user can pick a free port.
    allow_reuse_address = False

    def __init__(self, server_address: tuple[str, int], default_db_path: Path):
        self.default_db_path = default_db_path
        super().__init__(server_address, DashboardHandler)


class DashboardHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_dashboard(self.server.default_db_path))
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if parsed.path == "/api/data-summary":
            self._handle_get_query(parsed.query, build_data_summary)
            return
        if parsed.path == "/api/funding-rates":
            self._handle_get_query(parsed.query, fetch_funding_summary)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        routes = {
            "/api/optimize": run_optimizer_request,
            "/api/backtest": run_backtest_request,
            "/api/download": run_download_request,
            "/api/sample-data": run_sample_data_request,
        }
        if parsed.path not in routes:
            self.send_error(404)
            return
        try:
            payload = self._read_json()
            response = routes[parsed.path](payload, self.server.default_db_path)
            self._send_json(200, response)
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _handle_get_query(self, query: str, handler) -> None:
        try:
            payload = {key: values[-1] for key, values in parse_qs(query).items()}
            response = handler(payload, self.server.default_db_path)
            self._send_json(200, response)
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        cleaned = sanitize_json(payload)
        body = json.dumps(cleaned, default=_json_default, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8770,
    db_path: str | Path = DEFAULT_DB_PATH,
    open_browser: bool = False,
) -> None:
    try:
        server = DashboardServer((host, port), Path(db_path))
    except OSError as exc:
        raise SystemExit(
            f"Port {port} on {host} is already in use ({exc}). "
            f"Pick another port with --port (e.g. --port {port + 1})."
        ) from exc
    url = f"http://{host}:{port}"
    print(f"Trading lab dashboard running at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if open_browser:
        Timer(0.5, open_dashboard_browser, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("", flush=True)
    finally:
        server.server_close()


def open_dashboard_browser(url: str) -> None:
    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for edge_path in edge_paths:
        if edge_path.exists():
            subprocess.Popen([str(edge_path), url])
            return
    webbrowser.open(url)


def render_dashboard(default_db_path: Path) -> str:
    return DASHBOARD_HTML.replace("__DEFAULT_DB__", escape(str(default_db_path)))


def run_optimizer_request(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    db_path = Path(str(payload.get("db_path") or default_db_path))
    exchange = str(payload.get("exchange") or "binance").strip().lower()
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    market_type = normalize_market_type(str(payload.get("market_type") or "futures"))
    timeframe = str(payload.get("timeframe") or "1h").strip()

    optimizer_strategy = str(payload.get("optimizer_strategy") or "threshold").strip().lower().replace("-", "_")

    auto_download_days = max(1, int(payload.get("auto_download_days") or 90))
    candles, store, auto_download_note = _load_candles_or_download(
        db_path,
        exchange,
        symbol,
        market_type,
        timeframe,
        auto_download_days,
    )
    combine_mode = _normalize_combine_mode(payload.get("combine_mode"))
    companions = _companion_strategies_from_payload(payload)
    companion_tags = tuple(companions)

    config = _build_config_from_payload(payload, market_type)
    allow_short = payload_bool(payload, "allow_short", False)

    if optimizer_strategy == "ut_bot":
        key_grid = parse_float_grid(str(payload.get("ut_key_grid") or "2"))
        atr_period_grid = parse_int_grid(str(payload.get("ut_atr_period_grid") or "7"))
        lr_period_grid = parse_int_grid(str(payload.get("ut_lr_period_grid") or "20"))
        exit_pct_grid = parse_float_grid(str(payload.get("ut_exit_pct_grid") or "0.004,0.006"))
        exit_delay_grid = parse_int_grid(str(payload.get("ut_exit_delay_grid") or "1"))
        take_profit_grid = parse_float_grid(str(payload.get("take_profit_grid") or "0.006,0.01,0.014"))
        stop_loss_grid = parse_float_grid(str(payload.get("stop_loss_grid") or "0.004,0.006,0.008"))
        combination_count = (
            len(key_grid)
            * len(atr_period_grid)
            * len(lr_period_grid)
            * len(exit_pct_grid)
            * len(exit_delay_grid)
            * len(take_profit_grid)
            * len(stop_loss_grid)
        )
        if combination_count > MAX_GRID_COMBINATIONS:
            raise ValueError(
                f"Grid has {combination_count} combinations; reduce it below {MAX_GRID_COMBINATIONS}."
            )

        result = GridSearchOptimizer(config).run_ut_bot(
            candles,
            key_grid=key_grid,
            atr_period_grid=atr_period_grid,
            lr_period_grid=lr_period_grid,
            exit_pct_grid=exit_pct_grid,
            exit_delay_grid=exit_delay_grid,
            take_profit_grid=take_profit_grid,
            stop_loss_grid=stop_loss_grid,
            allow_short=allow_short,
            use_heikin_ashi=payload_bool(payload, "ut_use_heikin_ashi", False),
            enable_exit_signals=payload_bool(payload, "ut_enable_exit_signals", True),
            enable_time_range_disable=payload_bool(payload, "ut_enable_time_filter", False),
            disable_session=str(payload.get("ut_disable_session") or "2200-0500"),
            enable_cooldown=payload_bool(payload, "ut_enable_cooldown", False),
            cooldown_minutes=max(1, payload_int(payload, "ut_cooldown_minutes", 5)),
            companions=companion_tags,
            combine_mode=combine_mode,
        )
        rows = [enrich_optimizer_row(row) for row in result.rows]
        first_open, last_open = store.get_time_bounds(exchange, symbol, market_type, timeframe)
        return {
            "metadata": {
                "db_path": str(db_path),
                "exchange": exchange,
                "symbol": symbol,
                "market_type": market_type,
                "timeframe": timeframe,
                "candle_count": len(candles),
                "first_candle": ms_to_datetime(first_open).isoformat() if first_open is not None else None,
                "last_candle": ms_to_datetime(last_open).isoformat() if last_open is not None else None,
                "combination_count": combination_count,
                "auto_download_note": auto_download_note,
                "combine_mode": combine_mode,
                "strategy_companions": companions,
                "optimizer_strategy": "ut_bot",
            },
            "rows": rows,
            "best": rows[0] if rows else None,
        }

    entry_drop_grid = parse_float_grid(str(payload.get("entry_drop_grid") or "0.002,0.004,0.006"))
    entry_rise_grid = (
        parse_optional_float_grid(
            str(payload.get("entry_rise_grid") or ""),
            default=",".join(str(value) for value in entry_drop_grid),
        )
        if allow_short
        else [None]
    )
    take_profit_grid = parse_float_grid(str(payload.get("take_profit_grid") or "0.006,0.01,0.014"))
    stop_loss_grid = parse_float_grid(str(payload.get("stop_loss_grid") or "0.004,0.006,0.008"))
    combination_count = (
        len(entry_drop_grid)
        * len(entry_rise_grid)
        * len(take_profit_grid)
        * len(stop_loss_grid)
    )
    if combination_count > MAX_GRID_COMBINATIONS:
        raise ValueError(
            f"Grid has {combination_count} combinations; reduce it below {MAX_GRID_COMBINATIONS}."
        )

    strategy_maker = _make_optimizer_strategy_factory(allow_short, combine_mode, companions)

    result = GridSearchOptimizer(config).run(
        candles=candles,
        entry_drop_grid=entry_drop_grid,
        entry_rise_grid=entry_rise_grid,
        take_profit_grid=take_profit_grid,
        stop_loss_grid=stop_loss_grid,
        allow_short=allow_short,
        build_strategy=strategy_maker,
        combine_mode=combine_mode,
    )
    rows = [enrich_optimizer_row(row) for row in result.rows]
    first_open, last_open = store.get_time_bounds(exchange, symbol, market_type, timeframe)
    return {
        "metadata": {
            "db_path": str(db_path),
            "exchange": exchange,
            "symbol": symbol,
            "market_type": market_type,
            "timeframe": timeframe,
            "candle_count": len(candles),
            "first_candle": ms_to_datetime(first_open).isoformat() if first_open is not None else None,
            "last_candle": ms_to_datetime(last_open).isoformat() if last_open is not None else None,
            "combination_count": combination_count,
            "auto_download_note": auto_download_note,
            "combine_mode": combine_mode,
            "strategy_companions": companions,
            "optimizer_strategy": "threshold",
        },
        "rows": rows,
        "best": rows[0] if rows else None,
    }


def run_backtest_request(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    db_path = Path(str(payload.get("db_path") or default_db_path))
    exchange = str(payload.get("exchange") or "binance").strip().lower()
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    market_type = normalize_market_type(str(payload.get("market_type") or "futures"))
    timeframe = str(payload.get("timeframe") or "1h").strip()
    strategy_name = str(payload.get("strategy_name") or "threshold").strip().lower()
    auto_download_days = max(1, int(payload.get("auto_download_days") or 90))

    candles, store, auto_download_note = _load_candles_or_download(
        db_path,
        exchange,
        symbol,
        market_type,
        timeframe,
        auto_download_days,
    )
    config = _build_config_from_payload(payload, market_type)
    strategy = _build_backtest_strategy(payload)
    result = BacktestEngine(config).run(
        candles,
        strategy,
        symbol=symbol,
        timeframe=timeframe,
    )
    first_open, last_open = store.get_time_bounds(exchange, symbol, market_type, timeframe)
    wall_ms = _candles_wall_span_ms(candles)
    open_bounds_ms = _stored_open_bounds_span_ms(candles)
    wall_days = round(wall_ms / MS_PER_DAY, 8) if wall_ms else None
    open_bounds_days = round(open_bounds_ms / MS_PER_DAY, 8) if open_bounds_ms else None
    if isinstance(strategy, CompositeStrategy):
        stack_label = strategy_display_names(strategy.strategies)
        combine_m = strategy.combine
    else:
        stack_label = getattr(strategy, "name", strategy_name)
        combine_m = _normalize_combine_mode(payload.get("combine_mode"))
    return {
        "metadata": {
            "db_path": str(db_path),
            "exchange": exchange,
            "symbol": symbol,
            "market_type": market_type,
            "timeframe": timeframe,
            "strategy_name": strategy_name,
            "strategy_stack": stack_label,
            "combine_mode": combine_m,
            "candle_count": len(candles),
            "first_candle": ms_to_datetime(first_open).isoformat() if first_open is not None else None,
            "last_candle": ms_to_datetime(last_open).isoformat() if last_open is not None else None,
            "history_target_days_requested": auto_download_days,
            "candles_wall_span_days": wall_days,
            "candles_open_bounds_days": open_bounds_days,
            "config": _config_to_json(config),
            "auto_download_note": auto_download_note,
        },
        "stats": _stats_from_result(result),
        "equity_curve": _equity_curve_payload(result),
        "trades": [_trade_to_json(trade) for trade in result.trades],
        "trade_pnl_distribution": _trade_pnl_buckets(result.trades),
        "monthly_returns": _monthly_returns(result),
        "exit_reasons": _exit_reason_counts(result.trades),
        "candles": _candle_summary(candles),
    }


def run_download_request(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    db_path = Path(str(payload.get("db_path") or default_db_path))
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    market_type = normalize_market_type(str(payload.get("market_type") or "futures"))
    days = max(1, int(payload.get("days") or 90))
    timeframes = _parse_timeframe_list(payload.get("timeframes")) or ["1h", "4h", "8h", "12h"]

    start_ms, end_ms = last_days_range(days)
    store = CandleStore(db_path)
    client = BinanceKlineClient()
    rows: list[dict[str, object]] = []
    total = 0
    for timeframe in timeframes:
        candles = client.fetch_candles(
            symbol=symbol,
            market_type=market_type,
            timeframe=timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            exchange="binance",
        )
        written = store.upsert_candles(candles)
        total += written
        first_open, last_open = store.get_time_bounds("binance", symbol, market_type, timeframe)
        rows.append(
            {
                "timeframe": timeframe,
                "stored": written,
                "count": store.count_candles("binance", symbol, market_type, timeframe),
                "first_candle": ms_to_datetime(first_open).isoformat() if first_open is not None else None,
                "last_candle": ms_to_datetime(last_open).isoformat() if last_open is not None else None,
            }
        )
    return {
        "rows": rows,
        "total_stored": total,
        "symbol": symbol,
        "market_type": market_type,
        "days": days,
    }


def run_sample_data_request(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    db_path = Path(str(payload.get("db_path") or default_db_path))
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    market_type = normalize_market_type(str(payload.get("market_type") or "futures"))
    days = max(1, int(payload.get("days") or 90))
    timeframes = _parse_timeframe_list(payload.get("timeframes")) or ["1h", "4h", "8h", "12h"]
    exchange = str(payload.get("exchange") or "sample").strip().lower()

    store = CandleStore(db_path)
    rows: list[dict[str, object]] = []
    total = 0
    for timeframe in timeframes:
        candles = generate_sample_candles(
            symbol=symbol,
            market_type=market_type,
            timeframe=timeframe,
            days=days,
            exchange=exchange,
        )
        written = store.upsert_candles(candles)
        total += written
        first_open, last_open = store.get_time_bounds(exchange, symbol, market_type, timeframe)
        rows.append(
            {
                "timeframe": timeframe,
                "stored": written,
                "count": store.count_candles(exchange, symbol, market_type, timeframe),
                "first_candle": ms_to_datetime(first_open).isoformat() if first_open is not None else None,
                "last_candle": ms_to_datetime(last_open).isoformat() if last_open is not None else None,
            }
        )
    return {
        "rows": rows,
        "total_stored": total,
        "symbol": symbol,
        "market_type": market_type,
        "exchange": exchange,
        "days": days,
    }


def build_data_summary(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    db_path = Path(str(payload.get("db_path") or default_db_path))
    exchange = str(payload.get("exchange") or "binance").strip().lower()
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    market_type = normalize_market_type(str(payload.get("market_type") or "futures"))
    timeframes = _parse_timeframe_list(payload.get("timeframes")) or ["1h", "4h", "8h", "12h"]

    store = CandleStore(db_path)
    rows = []
    for timeframe in timeframes:
        count = store.count_candles(exchange, symbol, market_type, timeframe)
        first, last = store.get_time_bounds(exchange, symbol, market_type, timeframe)
        rows.append(
            {
                "timeframe": timeframe,
                "count": count,
                "first_candle": ms_to_datetime(first).isoformat() if first is not None else None,
                "last_candle": ms_to_datetime(last).isoformat() if last is not None else None,
            }
        )
    return {"rows": rows, "exchange": exchange, "symbol": symbol, "market_type": market_type}


def fetch_funding_summary(payload: dict[str, object], default_db_path: Path) -> dict[str, object]:
    symbol = str(payload.get("symbol") or "BTCUSDT").strip().upper()
    days = max(1, int(payload.get("days") or 90))
    start_ms, end_ms = last_days_range(days)
    client = BinanceKlineClient()
    rows = client.fetch_funding_rates(symbol, start_ms, end_ms)
    average = average_funding_rate(rows)
    annualized_long_cost_pct = average * (24 / 8) * 365 * 100
    sample_rows = [
        {
            "funding_time": int(row["funding_time"]),
            "funding_time_iso": ms_to_datetime(int(row["funding_time"])).isoformat(),
            "funding_rate": float(row["funding_rate"]),
            "mark_price": float(row["mark_price"]),
        }
        for row in rows[-90:]
    ]
    return {
        "symbol": symbol,
        "days": days,
        "sample_count": len(rows),
        "average_funding_rate": average,
        "annualized_long_cost_pct": annualized_long_cost_pct,
        "rows": sample_rows,
    }


def _build_config_from_payload(payload: dict[str, object], market_type: str) -> BacktestConfig:
    leverage = payload_float(payload, "leverage", 3.0)
    if market_type == "spot":
        leverage = 1.0
    ignore_position_pct = payload_bool(payload, "ignore_position_size_pct", False)
    use_pct = not ignore_position_pct
    stake = payload_float(payload, "stake_usd", 2_500.0)
    funding_enabled = not payload_bool(payload, "ignore_funding", False)
    return BacktestConfig(
        initial_balance=payload_float(payload, "initial_balance", 10_000.0),
        market_type=market_type,
        position_size_pct=payload_float(payload, "position_size_pct", 0.25),
        use_position_size_pct=use_pct,
        stake_usd=stake if not use_pct else None,
        leverage=leverage,
        fee_rate=payload_float(payload, "fee_rate", 0.0005),
        maker_fee_rate=payload_float(payload, "maker_fee_rate", 0.0002),
        slippage_bps=payload_float(payload, "slippage_bps", 1.5),
        spread_bps=payload_float(payload, "spread_bps", 1.0),
        stop_loss_pct=payload_float(payload, "stop_loss_pct", 0.008),
        take_profit_pct=payload_float(payload, "take_profit_pct", 0.012),
        maintenance_margin_rate=payload_float(payload, "maintenance_margin_rate", 0.004),
        funding_rate_per_interval=payload_float(payload, "funding_rate_per_interval", 0.0001),
        funding_interval_hours=payload_float(payload, "funding_interval_hours", 8.0),
        funding_enabled=funding_enabled,
    )


def _normalize_combine_mode(value: object) -> str:
    choice = str(value or "all").strip().lower()
    if choice == "any":
        return "any"
    return "all"


def _companion_strategies_from_payload(payload: dict[str, object]) -> list[str]:
    raw = payload.get("strategy_companions")
    names: list[str] = []
    if isinstance(raw, list):
        names = [str(item).strip().lower() for item in raw if str(item).strip()]
    elif isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                names = [str(item).strip().lower() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            names = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if payload_bool(payload, "companion_buy_hold", False) and "buy-hold" not in names:
        names.append("buy-hold")
    return names


def _companion_strategy_from_name(name: str) -> Strategy:
    key = name.replace("_", "-")
    if key in {"buy-hold", "buyhold"}:
        return BuyAndHoldStrategy()
    raise ValueError(
        f"Unknown companion strategy '{name}'. Extend _companion_strategy_from_name when you add one."
    )


def _make_optimizer_strategy_factory(
    allow_short: bool,
    combine_mode: str,
    companions: list[str],
):
    if not companions:

        def single(
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

        return single

    mode = "any" if combine_mode == "any" else "all"

    def stacked(
        entry_drop: float,
        entry_rise: float | None,
        take_profit: float,
        stop_loss: float,
    ) -> Strategy:
        threshold = ThresholdStrategy(
            entry_drop_pct=entry_drop,
            entry_rise_pct=entry_rise,
            allow_short=allow_short,
        )
        others = [_companion_strategy_from_name(n) for n in companions]
        return CompositeStrategy((threshold, *others), combine=mode)

    return stacked


def _build_backtest_strategy(payload: dict[str, object]) -> Strategy:
    strategy_name = str(payload.get("strategy_name") or "threshold").strip().lower()
    companions = _companion_strategies_from_payload(payload)
    combine_mode = _normalize_combine_mode(payload.get("combine_mode"))
    primary = _build_strategy(strategy_name, payload)

    if not companions:
        return primary

    if strategy_name == "buy-hold":
        raise ValueError(
            "Buy & Hold cannot be stacked with companions. Pick Threshold or UT Bot as the primary strategy."
        )
    others = [_companion_strategy_from_name(name) for name in companions]
    mode = "any" if combine_mode == "any" else "all"
    return CompositeStrategy((primary, *others), combine=mode)


def _build_strategy(name: str, payload: dict[str, object]):
    if name == "buy-hold":
        return BuyAndHoldStrategy()
    if name in {"ut-bot", "ut_bot"}:
        return _build_ut_bot_strategy(payload)
    return ThresholdStrategy(
        entry_drop_pct=payload_float(payload, "entry_drop_pct", 0.004),
        entry_rise_pct=(
            payload_float(payload, "entry_rise_pct", 0.0)
            if payload_bool(payload, "allow_short", False)
            else None
        ),
        allow_short=payload_bool(payload, "allow_short", False),
    )


def _build_ut_bot_strategy(payload: dict[str, object]) -> UtBotStrategy:
    return UtBotStrategy(
        key_value=payload_float(payload, "ut_key_value", 2.0),
        atr_period=payload_int(payload, "ut_atr_period", 7),
        use_heikin_ashi=payload_bool(payload, "ut_use_heikin_ashi", False),
        lr_period=payload_int(payload, "ut_lr_period", 20),
        exit_pct=payload_float(payload, "ut_exit_pct", 0.006),
        enable_exit_signals=payload_bool(payload, "ut_enable_exit_signals", True),
        exit_delay=payload_int(payload, "ut_exit_delay", 1),
        enable_time_range_disable=payload_bool(payload, "ut_enable_time_filter", False),
        disable_session=str(payload.get("ut_disable_session") or "2200-0500"),
        enable_cooldown=payload_bool(payload, "ut_enable_cooldown", False),
        cooldown_minutes=max(1, payload_int(payload, "ut_cooldown_minutes", 5)),
        allow_short=payload_bool(payload, "allow_short", False),
    )


def _load_candles(
    db_path: Path,
    exchange: str,
    symbol: str,
    market_type: str,
    timeframe: str,
):
    store = CandleStore(db_path)
    candles = store.get_candles(exchange, symbol, market_type, timeframe)
    if len(candles) < 2:
        raise ValueError(
            f"Not enough candles for {exchange} {symbol} {market_type} {timeframe}. "
            "Download data or generate sample data first."
        )
    return candles, store


def _load_candles_or_download(
    db_path: Path,
    exchange: str,
    symbol: str,
    market_type: str,
    timeframe: str,
    days: int,
):
    """Load candles, downloading from Binance (or generating samples) if absent."""

    store = CandleStore(db_path)
    candles = store.get_candles(exchange, symbol, market_type, timeframe)
    note: str | None = None
    if len(candles) >= 2:
        candles, refill_note = _maybe_expand_binance_history(
            store=store,
            candles=candles,
            exchange=exchange,
            symbol=symbol,
            market_type=market_type,
            timeframe=timeframe,
            requested_days=days,
        )
        if refill_note:
            note = refill_note
        return candles, store, note

    if exchange == "binance":
        try:
            client = BinanceKlineClient()
            start_ms, end_ms = last_days_range(days)
            fetched = client.fetch_candles(
                symbol=symbol,
                market_type=market_type,
                timeframe=timeframe,
                start_ms=start_ms,
                end_ms=end_ms,
                exchange=exchange,
            )
            if fetched:
                store.upsert_candles(fetched)
                note = (
                    f"Auto-downloaded {len(fetched)} {timeframe} candles for "
                    f"{symbol} {market_type} from Binance ({days} days)."
                )
        except Exception as exc:
            note = (
                f"Could not auto-download {timeframe} candles from Binance ({exc}); "
                "generated synthetic data instead."
            )
            generated = generate_sample_candles(
                symbol=symbol,
                market_type=market_type,
                timeframe=timeframe,
                days=days,
                exchange=exchange,
            )
            store.upsert_candles(generated)
    else:
        generated = generate_sample_candles(
            symbol=symbol,
            market_type=market_type,
            timeframe=timeframe,
            days=days,
            exchange=exchange,
        )
        store.upsert_candles(generated)
        note = (
            f"Generated {len(generated)} synthetic {timeframe} candles for {symbol} "
            f"{market_type} on '{exchange}' ({days} days)."
        )

    candles = store.get_candles(exchange, symbol, market_type, timeframe)
    if len(candles) < 2:
        raise ValueError(
            f"Could not obtain candles for {exchange} {symbol} {market_type} {timeframe}. "
            "Use the Market Data tab to download or generate data, then retry."
        )
    return candles, store, note


def _stats_from_result(result: BacktestResult) -> dict[str, object]:
    long_trades = [trade for trade in result.trades if trade.side == "long"]
    short_trades = [trade for trade in result.trades if trade.side == "short"]
    return {
        "initial_balance": result.initial_balance,
        "final_balance": result.final_balance,
        "net_pnl": result.net_pnl,
        "total_return_pct": result.total_return_pct,
        "annualized_return_pct": result.annualized_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "max_drawdown_duration_bars": result.max_drawdown_duration_bars,
        "sharpe_ratio": _safe_finite(result.sharpe_ratio),
        "sortino_ratio": _safe_finite(result.sortino_ratio),
        "calmar_ratio": _safe_finite(result.calmar_ratio),
        "pnl_r_squared": result.pnl_r_squared,
        "win_rate_pct": result.win_rate_pct,
        "profit_factor": _safe_finite(result.profit_factor),
        "payoff_ratio": _safe_finite(result.payoff_ratio),
        "expectancy": result.expectancy,
        "expectancy_pct": result.expectancy_pct,
        "average_trade_pnl": result.average_trade_pnl,
        "average_trade_return_pct": result.average_trade_return_pct,
        "average_bars_held": result.average_bars_held,
        "average_win_pnl": result.average_win_pnl,
        "average_loss_pnl": result.average_loss_pnl,
        "best_trade_pnl": result.best_trade_pnl,
        "worst_trade_pnl": result.worst_trade_pnl,
        "longest_win_streak": result.longest_win_streak,
        "longest_loss_streak": result.longest_loss_streak,
        "total_funding_paid": result.total_funding_paid,
        "total_fees_paid": result.total_fees_paid,
        "duration_days": result.duration_days,
        "trade_count": len(result.trades),
        "long_trade_count": len(long_trades),
        "short_trade_count": len(short_trades),
    }


def _equity_curve_payload(result: BacktestResult) -> list[dict[str, object]]:
    if not result.equity_curve:
        return []
    peak = -math.inf
    payload: list[dict[str, object]] = []
    for point in result.equity_curve:
        peak = max(peak, point.equity)
        drawdown_pct = 0.0
        if peak > 0:
            drawdown_pct = (peak - point.equity) / peak * 100.0
        payload.append(
            {
                "time": point.time,
                "balance": point.balance,
                "equity": point.equity,
                "close_price": point.close_price,
                "drawdown_pct": drawdown_pct,
            }
        )
    return payload


def _trade_to_json(trade: Trade) -> dict[str, object]:
    return {
        "side": trade.side,
        "entry_time": trade.entry_time,
        "exit_time": trade.exit_time,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "quantity": trade.quantity,
        "margin": trade.margin,
        "entry_fee": trade.entry_fee,
        "exit_fee": trade.exit_fee,
        "funding_paid": trade.funding_paid,
        "gross_pnl": trade.gross_pnl,
        "net_pnl": trade.net_pnl,
        "return_pct": trade.return_pct,
        "bars_held": trade.bars_held,
        "exit_reason": trade.exit_reason,
    }


def _trade_pnl_buckets(trades: tuple[Trade, ...]) -> list[dict[str, object]]:
    if not trades:
        return []
    pnls = [trade.net_pnl for trade in trades]
    lo, hi = min(pnls), max(pnls)
    if lo == hi:
        return [{"start": lo, "end": hi, "count": len(pnls)}]
    bucket_count = min(20, max(6, len(pnls) // 4 or 6))
    width = (hi - lo) / bucket_count
    buckets = [{"start": lo + i * width, "end": lo + (i + 1) * width, "count": 0} for i in range(bucket_count)]
    for value in pnls:
        index = min(int((value - lo) / width), bucket_count - 1)
        buckets[index]["count"] = int(buckets[index]["count"]) + 1
    return buckets


def _monthly_returns(result: BacktestResult) -> list[dict[str, object]]:
    if not result.equity_curve:
        return []
    by_month: dict[tuple[int, int], list] = {}
    for point in result.equity_curve:
        dt = ms_to_datetime(point.time)
        key = (dt.year, dt.month)
        by_month.setdefault(key, []).append(point.equity)
    rows = []
    sorted_keys = sorted(by_month.keys())
    previous_close: float | None = None
    for key in sorted_keys:
        values = by_month[key]
        first = values[0]
        last = values[-1]
        start_balance = previous_close if previous_close is not None else first
        if start_balance > 0:
            return_pct = (last / start_balance - 1.0) * 100.0
        else:
            return_pct = 0.0
        previous_close = last
        rows.append(
            {
                "year": key[0],
                "month": key[1],
                "label": f"{key[0]}-{key[1]:02d}",
                "start_equity": start_balance,
                "end_equity": last,
                "return_pct": return_pct,
            }
        )
    return rows


def _exit_reason_counts(trades: tuple[Trade, ...]) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for trade in trades:
        counts[trade.exit_reason] = counts.get(trade.exit_reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in sorted(counts.items())]


def _candle_summary(candles) -> list[dict[str, object]]:
    """Downsample candles to keep the JSON payload small for charts."""

    if not candles:
        return []
    max_points = 600
    step = max(1, len(candles) // max_points)
    sampled = candles[::step]
    return [
        {
            "time": candle.open_time,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in sampled
    ]


def _config_to_json(config: BacktestConfig) -> dict[str, object]:
    data = asdict(config)
    return {key: value for key, value in data.items()}


def _parse_timeframe_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        part.strip()
        for part in str(value).replace(" ", ",").split(",")
        if part.strip()
    ]


def payload_float(payload: dict[str, object], key: str, default: float) -> float:
    value = payload.get(key)
    if value is None or value == "":
        return default
    return float(value)


def payload_int(payload: dict[str, object], key: str, default: int) -> int:
    value = payload.get(key)
    if value is None or value == "":
        return default
    return int(value)


def payload_bool(payload: dict[str, object], key: str, default: bool) -> bool:
    value = payload.get(key)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def row_to_json(row: OptimizationRow) -> dict[str, object]:
    data = asdict(row)
    for key, value in list(data.items()):
        if isinstance(value, float) and not math.isfinite(value):
            data[key] = None
    return data


def _strategy_legs_from_optimizer_row(row: OptimizationRow) -> list[dict[str, object]]:
    """Split a result row into per-strategy parameter blocks for the dashboard."""

    legs: list[dict[str, object]] = []
    for raw in row.strategy_stack.split("+"):
        sid = raw.strip()
        if not sid:
            continue
        if sid == "threshold":
            legs.append(
                {
                    "id": "threshold",
                    "title": "Threshold (grid-optimized leg)",
                    "params": {
                        "entry_drop_pct": row.entry_drop_pct,
                        "entry_rise_pct": row.entry_rise_pct,
                        "allow_short": row.allow_short,
                        "take_profit_pct": row.take_profit_pct,
                        "stop_loss_pct": row.stop_loss_pct,
                        "note": "Stop / take-profit percentages apply to any position the engine opens; "
                        "they are shared execution rules for this backtest row.",
                    },
                }
            )
        elif sid == "buy_and_hold":
            legs.append(
                {
                    "id": "buy_and_hold",
                    "title": "Buy & Hold (companion)",
                    "params": {
                        "entry_rule": "If flat at bar index 0, signal enter long on that candle.",
                        "grid_params": None,
                    },
                }
            )
        elif sid == "ut_bot":
            legs.append(
                {
                    "id": "ut_bot",
                    "title": "UT Bot Alerts",
                    "params": {
                        "key_value": row.ut_key_value,
                        "atr_period": row.ut_atr_period,
                        "lr_period": row.ut_lr_period,
                        "exit_pct": row.ut_exit_pct,
                        "exit_delay": row.ut_exit_delay,
                        "use_heikin_ashi": row.ut_use_heikin_ashi,
                        "allow_short": row.allow_short,
                        "take_profit_pct": row.take_profit_pct,
                        "stop_loss_pct": row.stop_loss_pct,
                        "note": "Heikin Ashi closes are synthesized from stored OHLC when enabled.",
                    },
                }
            )
        else:
            legs.append({"id": sid, "title": sid, "params": {}})
    return legs


def enrich_optimizer_row(row: OptimizationRow) -> dict[str, object]:
    data = row_to_json(row)
    data["strategy_legs"] = _strategy_legs_from_optimizer_row(row)
    return data


def _safe_finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def sanitize_json(value):
    if isinstance(value, dict):
        return {key: sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
