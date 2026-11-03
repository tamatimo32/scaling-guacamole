from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

from .config import DEFAULT_DB_PATH, DEFAULT_TIMEFRAMES, normalize_market_type
from .data_sources import (
    BinanceKlineClient,
    average_funding_rate,
    generate_sample_candles,
    last_days_range,
)
from .grids import parse_float_grid, parse_optional_float_grid
from .models import ms_to_datetime
from .optimizer import GridSearchOptimizer
from .simulator import BacktestConfig, BacktestEngine
from .storage import CandleStore
from .strategies import BuyAndHoldStrategy, ThresholdStrategy


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="futures-trading")
    db_parent = argparse.ArgumentParser(add_help=False)
    db_parent.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(required=True)

    init_db = subparsers.add_parser("init-db", parents=[db_parent], help="Create the SQLite schema")
    init_db.set_defaults(func=cmd_init_db)

    download = subparsers.add_parser("download", parents=[db_parent], help="Download candles into SQLite")
    add_market_args(download)
    download.add_argument("--days", type=int, default=90)
    download.add_argument("--timeframes", nargs="+", default=list(DEFAULT_TIMEFRAMES))
    download.set_defaults(func=cmd_download)

    funding = subparsers.add_parser(
        "download-funding",
        parents=[db_parent],
        help="Download Binance USD-M funding history for a symbol",
    )
    funding.add_argument("--symbol", default="BTCUSDT")
    funding.add_argument("--days", type=int, default=90)
    funding.set_defaults(func=cmd_download_funding)

    sample = subparsers.add_parser(
        "generate-sample-data",
        parents=[db_parent],
        help="Generate offline sample candles",
    )
    add_market_args(sample)
    sample.add_argument("--days", type=int, default=90)
    sample.add_argument("--timeframes", nargs="+", default=list(DEFAULT_TIMEFRAMES))
    sample.add_argument("--exchange", default="sample")
    sample.set_defaults(func=cmd_generate_sample_data)

    show = subparsers.add_parser("show-data", parents=[db_parent], help="Show stored candle counts")
    add_market_args(show)
    show.add_argument("--timeframes", nargs="+", default=list(DEFAULT_TIMEFRAMES))
    show.add_argument("--exchange", default=None)
    show.set_defaults(func=cmd_show_data)

    backtest = subparsers.add_parser("backtest", parents=[db_parent], help="Run one backtest")
    add_market_args(backtest)
    add_backtest_args(backtest)
    backtest.add_argument("--timeframe", default="1h")
    backtest.add_argument("--exchange", default=None)
    backtest.add_argument("--strategy", choices=["buy-hold", "threshold"], default="threshold")
    backtest.add_argument("--entry-drop-pct", type=float, default=0.004)
    backtest.add_argument("--entry-rise-pct", type=float, default=None)
    backtest.add_argument("--allow-short", action="store_true")
    backtest.set_defaults(func=cmd_backtest)

    optimize = subparsers.add_parser(
        "optimize",
        parents=[db_parent],
        help="Grid search percentage strategy settings",
    )
    add_market_args(optimize)
    add_backtest_args(optimize)
    optimize.add_argument("--timeframe", default="1h")
    optimize.add_argument("--exchange", default=None)
    optimize.add_argument("--entry-drop-grid", default="0.002,0.004,0.006")
    optimize.add_argument("--entry-rise-grid", default=None)
    optimize.add_argument("--allow-short", action="store_true")
    optimize.add_argument("--take-profit-grid", default="0.006,0.01,0.014")
    optimize.add_argument("--stop-loss-grid", default="0.004,0.006,0.008")
    optimize.add_argument("--csv-out", type=Path, default=None)
    optimize.set_defaults(func=cmd_optimize)

    dashboard = subparsers.add_parser(
        "dashboard",
        parents=[db_parent],
        help="Run the local optimizer HTML dashboard",
    )
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8770)
    dashboard.add_argument("--open-browser", action="store_true")
    dashboard.set_defaults(func=cmd_dashboard)

    return parser


def add_market_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--market-type", choices=["spot", "futures"], default="futures")


def add_backtest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--initial-balance", type=float, default=10_000.0)
    parser.add_argument("--position-size-pct", type=float, default=0.25)
    parser.add_argument("--leverage", type=float, default=3.0)
    parser.add_argument("--fee-rate", type=float, default=0.0005)
    parser.add_argument("--slippage-bps", type=float, default=1.5)
    parser.add_argument("--spread-bps", type=float, default=1.0)
    parser.add_argument("--stop-loss-pct", type=float, default=0.008)
    parser.add_argument("--take-profit-pct", type=float, default=0.012)
    parser.add_argument("--maintenance-margin-rate", type=float, default=0.004)
    parser.add_argument("--funding-rate-per-interval", type=float, default=0.0001)
    parser.add_argument("--funding-interval-hours", type=float, default=8.0)


def cmd_init_db(args: argparse.Namespace) -> int:
    store = CandleStore(args.db)
    store.initialize()
    print(f"Initialized candle store: {args.db}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    market_type = normalize_market_type(args.market_type)
    start_ms, end_ms = last_days_range(args.days)
    store = CandleStore(args.db)
    client = BinanceKlineClient()

    total = 0
    for timeframe in args.timeframes:
        candles = client.fetch_candles(
            symbol=args.symbol,
            market_type=market_type,
            timeframe=timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            exchange="binance",
        )
        written = store.upsert_candles(candles)
        total += written
        print(f"{timeframe}: stored {written} candles")
    print(f"Done. Stored {total} total candles in {args.db}")
    return 0


def cmd_download_funding(args: argparse.Namespace) -> int:
    start_ms, end_ms = last_days_range(args.days)
    client = BinanceKlineClient()
    rows = client.fetch_funding_rates(args.symbol, start_ms, end_ms)
    if not rows:
        print(f"No funding rates returned for {args.symbol}")
        return 0
    average = average_funding_rate(rows)
    annualized = average * (24 / 8) * 365 * 100
    print(f"{args.symbol}: {len(rows)} funding samples")
    print(f"Average per 8h funding: {average * 100:.5f}%")
    print(f"Approx annualized funding cost (long): {annualized:.2f}%")
    return 0


def cmd_generate_sample_data(args: argparse.Namespace) -> int:
    market_type = normalize_market_type(args.market_type)
    store = CandleStore(args.db)
    total = 0
    for timeframe in args.timeframes:
        candles = generate_sample_candles(
            symbol=args.symbol,
            market_type=market_type,
            timeframe=timeframe,
            days=args.days,
            exchange=args.exchange,
        )
        written = store.upsert_candles(candles)
        total += written
        print(f"{timeframe}: stored {written} sample candles")
    print(f"Done. Stored {total} total sample candles in {args.db}")
    return 0


def cmd_show_data(args: argparse.Namespace) -> int:
    market_type = normalize_market_type(args.market_type)
    exchange = args.exchange or ("binance" if market_type in {"spot", "futures"} else "sample")
    store = CandleStore(args.db)
    for timeframe in args.timeframes:
        count = store.count_candles(exchange, args.symbol.upper(), market_type, timeframe)
        first, last = store.get_time_bounds(exchange, args.symbol.upper(), market_type, timeframe)
        if first is None or last is None:
            print(f"{exchange} {args.symbol.upper()} {market_type} {timeframe}: 0 candles")
        else:
            print(
                f"{exchange} {args.symbol.upper()} {market_type} {timeframe}: "
                f"{count} candles, {ms_to_datetime(first)} -> {ms_to_datetime(last)}"
            )
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    candles = load_candles_for_command(args)
    strategy = build_strategy(args)
    result = BacktestEngine(build_backtest_config(args)).run(
        candles,
        strategy,
        symbol=args.symbol.upper(),
        timeframe=args.timeframe,
    )
    print_result(result)
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    candles = load_candles_for_command(args)
    optimizer = GridSearchOptimizer(build_backtest_config(args))
    result = optimizer.run(
        candles=candles,
        entry_drop_grid=parse_float_grid(args.entry_drop_grid),
        entry_rise_grid=(
            parse_optional_float_grid(args.entry_rise_grid, default=args.entry_drop_grid)
            if args.allow_short
            else [None]
        ),
        take_profit_grid=parse_float_grid(args.take_profit_grid),
        stop_loss_grid=parse_float_grid(args.stop_loss_grid),
        allow_short=args.allow_short,
    )
    if args.csv_out is not None:
        write_optimizer_csv(args.csv_out, result.rows)
        print(f"Wrote optimizer results: {args.csv_out}")
    print_optimizer_result(result)
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    from .web import run_dashboard

    run_dashboard(host=args.host, port=args.port, db_path=args.db, open_browser=args.open_browser)
    return 0


def load_candles_for_command(args: argparse.Namespace):
    market_type = normalize_market_type(args.market_type)
    exchange = args.exchange or "binance"
    store = CandleStore(args.db)
    candles = store.get_candles(
        exchange=exchange,
        symbol=args.symbol.upper(),
        market_type=market_type,
        timeframe=args.timeframe,
    )
    if not candles and exchange != "sample":
        candles = store.get_candles(
            exchange="sample",
            symbol=args.symbol.upper(),
            market_type=market_type,
            timeframe=args.timeframe,
        )
        if candles:
            print("No Binance candles found; using sample candles.")
    if len(candles) < 2:
        raise ValueError(
            "Not enough candles found. Run download or generate-sample-data first."
        )
    return candles


def build_backtest_config(args: argparse.Namespace) -> BacktestConfig:
    market_type = normalize_market_type(args.market_type)
    leverage = 1.0 if market_type == "spot" else args.leverage
    return BacktestConfig(
        initial_balance=args.initial_balance,
        market_type=market_type,
        position_size_pct=args.position_size_pct,
        leverage=leverage,
        fee_rate=args.fee_rate,
        slippage_bps=args.slippage_bps,
        spread_bps=args.spread_bps,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        maintenance_margin_rate=args.maintenance_margin_rate,
        funding_rate_per_interval=args.funding_rate_per_interval,
        funding_interval_hours=args.funding_interval_hours,
    )


def build_strategy(args: argparse.Namespace):
    if args.strategy == "buy-hold":
        return BuyAndHoldStrategy()
    return ThresholdStrategy(
        entry_drop_pct=args.entry_drop_pct,
        entry_rise_pct=args.entry_rise_pct,
        allow_short=args.allow_short,
    )


def print_result(result) -> None:
    print(f"Symbol: {result.symbol}")
    print(f"Market type: {result.market_type}")
    print(f"Timeframe: {result.timeframe}")
    print(f"Initial balance: {result.initial_balance:.2f}")
    print(f"Final balance: {result.final_balance:.2f}")
    print(f"Net PnL: {result.net_pnl:.2f}")
    print(f"Total return: {result.total_return_pct:.2f}%")
    print(f"Annualized return: {result.annualized_return_pct:.2f}%")
    print(f"Max drawdown: {result.max_drawdown_pct:.2f}% (over {result.max_drawdown_duration_bars} bars)")
    print(f"Win rate: {result.win_rate_pct:.2f}%")
    print(f"Profit factor: {result.profit_factor:.3f}")
    print(f"Payoff ratio: {result.payoff_ratio:.3f}")
    print(f"Sharpe: {result.sharpe_ratio:.3f}")
    print(f"Sortino: {result.sortino_ratio:.3f}")
    print(f"Calmar: {result.calmar_ratio:.3f}")
    print(f"PnL R2: {result.pnl_r_squared:.3f}")
    print(f"Expectancy: {result.expectancy:.2f}")
    print(f"Best/Worst trade: {result.best_trade_pnl:.2f} / {result.worst_trade_pnl:.2f}")
    print(f"Win/Loss streaks: {result.longest_win_streak} / {result.longest_loss_streak}")
    print(f"Total fees: {result.total_fees_paid:.2f}")
    print(f"Total funding: {result.total_funding_paid:.2f}")
    print(f"Trades: {len(result.trades)} (avg bars held {result.average_bars_held:.1f})")
    for trade in result.trades[-5:]:
        print(
            "Trade "
            f"{trade.side} entry={trade.entry_price:.2f} exit={trade.exit_price:.2f} "
            f"net={trade.net_pnl:.2f} return={trade.return_pct:.2f}% "
            f"bars={trade.bars_held} reason={trade.exit_reason}"
        )


def print_optimizer_result(result) -> None:
    best = result.best
    if best is None:
        print("No optimizer rows.")
        return
    print("Best result:")
    entry_rise = "none" if best.entry_rise_pct is None else f"{best.entry_rise_pct:.4f}"
    print(
        f"strategy={best.strategy_name} stack={best.strategy_stack} mode={best.combine_mode} "
        f"allow_short={best.allow_short} "
        f"entry_drop={best.entry_drop_pct:.4f} "
        f"entry_rise={entry_rise} "
        f"take_profit={best.take_profit_pct:.4f} "
        f"stop_loss={best.stop_loss_pct:.4f} "
        f"final={best.final_balance:.2f} "
        f"return={best.total_return_pct:.2f}% "
        f"sharpe={best.sharpe_ratio:.3f} "
        f"pnl_r2={best.pnl_r_squared:.3f} "
        f"drawdown={best.max_drawdown_pct:.2f}% "
        f"trades={best.trade_count}"
    )
    print("")
    print("Top 10:")
    for row in result.rows[:10]:
        print(
            f"{row.final_balance:10.2f} | return {row.total_return_pct:7.2f}% | "
            f"sharpe {row.sharpe_ratio:7.3f} | r2 {row.pnl_r_squared:5.3f} | "
            f"dd {row.max_drawdown_pct:6.2f}% | win {row.win_rate_pct:6.2f}% | "
            f"trades {row.trade_count:4d} | "
            f"entry {row.entry_drop_pct:.4f} rise {format_optional_pct(row.entry_rise_pct)} "
            f"tp {row.take_profit_pct:.4f} sl {row.stop_loss_pct:.4f}"
        )


def format_optional_pct(value: float | None) -> str:
    return "none" if value is None else f"{value:.4f}"


def write_optimizer_csv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


if __name__ == "__main__":
    raise SystemExit(main())
