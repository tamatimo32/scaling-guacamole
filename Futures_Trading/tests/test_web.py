import tempfile
import unittest
from pathlib import Path

from futures_trading.data_sources import generate_sample_candles
from futures_trading.storage import CandleStore
from futures_trading.web import (
    run_backtest_request,
    run_optimizer_request,
    run_sample_data_request,
    sanitize_json,
)


class WebDashboardTests(unittest.TestCase):
    def test_optimizer_request_returns_dashboard_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            store = CandleStore(db_path)
            store.upsert_candles(
                generate_sample_candles(
                    symbol="BTCUSDT",
                    market_type="futures",
                    timeframe="1h",
                    days=3,
                    exchange="sample",
                    seed=99,
                )
            )

            response = run_optimizer_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "entry_drop_grid": "0.002,0.004",
                    "take_profit_grid": "0.006",
                    "stop_loss_grid": "0.004",
                },
                db_path,
            )

            self.assertEqual(response["metadata"]["combination_count"], 2)
            self.assertEqual(len(response["rows"]), 2)
            self.assertIn("sharpe_ratio", response["rows"][0])
            self.assertIn("pnl_r_squared", response["rows"][0])
            self.assertIn("strategy_legs", response["rows"][0])
            self.assertTrue(len(response["rows"][0]["strategy_legs"]) >= 1)

    def test_optimizer_request_accepts_range_inputs_and_short_grid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            store = CandleStore(db_path)
            store.upsert_candles(
                generate_sample_candles(
                    symbol="BTCUSDT",
                    market_type="futures",
                    timeframe="1h",
                    days=3,
                    exchange="sample",
                    seed=100,
                )
            )

            response = run_optimizer_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "allow_short": True,
                    "entry_drop_grid": "0.002:0.004:0.002",
                    "entry_rise_grid": "0.003:0.005:0.002",
                    "take_profit_grid": "0.006",
                    "stop_loss_grid": "0.004",
                },
                db_path,
            )

            self.assertEqual(response["metadata"]["combination_count"], 4)
            self.assertEqual(len(response["rows"]), 4)
            self.assertTrue(all(row["allow_short"] for row in response["rows"]))


    def test_backtest_request_returns_full_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            store = CandleStore(db_path)
            store.upsert_candles(
                generate_sample_candles(
                    symbol="BTCUSDT",
                    market_type="futures",
                    timeframe="1h",
                    days=4,
                    exchange="sample",
                    seed=123,
                )
            )

            response = run_backtest_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "strategy_name": "threshold",
                    "entry_drop_pct": 0.003,
                    "stop_loss_pct": 0.006,
                    "take_profit_pct": 0.012,
                    "leverage": 5,
                },
                db_path,
            )

            self.assertIn("stats", response)
            self.assertIn("equity_curve", response)
            self.assertIn("trades", response)
            self.assertIn("monthly_returns", response)
            self.assertIn("trade_pnl_distribution", response)
            self.assertIn("exit_reasons", response)
            self.assertGreater(len(response["equity_curve"]), 0)
            stats = response["stats"]
            self.assertIn("sortino_ratio", stats)
            self.assertIn("calmar_ratio", stats)
            self.assertIn("total_funding_paid", stats)
            self.assertIn("duration_days", stats)
            self.assertGreater(stats["duration_days"], 0)
            self.assertEqual(response["metadata"]["strategy_stack"], "threshold")
            self.assertEqual(response["metadata"]["combine_mode"], "all")

    def test_optimizer_with_companion_reports_composite_stack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            store = CandleStore(db_path)
            store.upsert_candles(
                generate_sample_candles(
                    symbol="BTCUSDT",
                    market_type="futures",
                    timeframe="1h",
                    days=4,
                    exchange="sample",
                    seed=55,
                )
            )
            response = run_optimizer_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "entry_drop_grid": "0.004",
                    "take_profit_grid": "0.01",
                    "stop_loss_grid": "0.006",
                    "companion_buy_hold": True,
                    "combine_mode": "any",
                },
                db_path,
            )
            stack = response["rows"][0]["strategy_stack"]
            self.assertIn("threshold", stack)
            self.assertIn("buy_and_hold", stack)

    def test_backtest_respects_fixed_stake_and_funding_toggles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            store = CandleStore(db_path)
            store.upsert_candles(
                generate_sample_candles(
                    symbol="BTCUSDT",
                    market_type="futures",
                    timeframe="1h",
                    days=4,
                    exchange="sample",
                    seed=77,
                )
            )
            response = run_backtest_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "strategy_name": "threshold",
                    "entry_drop_pct": 0.003,
                    "stop_loss_pct": 0.006,
                    "take_profit_pct": 0.012,
                    "leverage": 5,
                    "ignore_position_size_pct": True,
                    "stake_usd": 1200.0,
                    "ignore_funding": True,
                },
                db_path,
            )
            cfg = response["metadata"]["config"]
            self.assertFalse(cfg["use_position_size_pct"])
            self.assertEqual(cfg["stake_usd"], 1200.0)
            self.assertFalse(cfg["funding_enabled"])

    def test_backtest_request_auto_generates_data_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            response = run_backtest_request(
                {
                    "db_path": str(db_path),
                    "exchange": "sample",
                    "symbol": "ETHUSDT",
                    "market_type": "futures",
                    "timeframe": "1h",
                    "strategy_name": "threshold",
                    "auto_download_days": 5,
                    "entry_drop_pct": 0.003,
                    "stop_loss_pct": 0.006,
                    "take_profit_pct": 0.012,
                    "leverage": 3,
                },
                db_path,
            )
            self.assertGreater(response["metadata"]["candle_count"], 50)
            self.assertIsNotNone(response["metadata"]["auto_download_note"])
            store = CandleStore(db_path)
            self.assertGreater(
                store.count_candles("sample", "ETHUSDT", "futures", "1h"),
                50,
            )

    def test_sample_data_request_writes_candles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "candles.sqlite"
            response = run_sample_data_request(
                {
                    "db_path": str(db_path),
                    "symbol": "BTCUSDT",
                    "market_type": "futures",
                    "timeframes": "1h,4h",
                    "days": 3,
                    "exchange": "sample",
                },
                db_path,
            )
            self.assertGreater(response["total_stored"], 0)
            self.assertEqual(len(response["rows"]), 2)

    def test_sanitize_json_replaces_non_finite_floats(self):
        cleaned = sanitize_json(
            {
                "value": float("inf"),
                "nested": [float("nan"), 1.5, {"key": float("-inf")}],
                "ok": "string",
            }
        )
        self.assertIsNone(cleaned["value"])
        self.assertIsNone(cleaned["nested"][0])
        self.assertEqual(cleaned["nested"][1], 1.5)
        self.assertIsNone(cleaned["nested"][2]["key"])
        self.assertEqual(cleaned["ok"], "string")


if __name__ == "__main__":
    unittest.main()
