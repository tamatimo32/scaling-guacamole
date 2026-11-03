import unittest

from futures_trading.models import Candle
from futures_trading.simulator import BacktestConfig, BacktestEngine
from futures_trading.strategies import BuyAndHoldStrategy


def make_candles():
    return [
        Candle("test", "BTCUSDT", "futures", "1h", 0, 100.0, 101.0, 99.0, 100.0, 1.0, 1),
        Candle("test", "BTCUSDT", "futures", "1h", 2, 100.0, 106.0, 99.5, 105.0, 1.0, 3),
        Candle("test", "BTCUSDT", "futures", "1h", 4, 105.0, 106.0, 104.0, 105.5, 1.0, 5),
    ]


def make_hourly_flat_candles():
    hour = 3_600_000
    return [
        Candle("test", "BTCUSDT", "futures", "1h", 0, 100.0, 100.0, 100.0, 100.0, 1.0, hour - 1),
        Candle("test", "BTCUSDT", "futures", "1h", hour, 100.0, 100.0, 100.0, 100.0, 1.0, 2 * hour - 1),
        Candle("test", "BTCUSDT", "futures", "1h", 2 * hour, 100.0, 100.0, 100.0, 100.0, 1.0, 3 * hour - 1),
    ]


class BacktestEngineTests(unittest.TestCase):
    def test_futures_take_profit_closes_trade(self):
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="futures",
            position_size_pct=0.5,
            leverage=2.0,
            fee_rate=0.0,
            slippage_bps=0.0,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
        )
        result = BacktestEngine(config).run(make_candles(), BuyAndHoldStrategy())

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].exit_reason, "take_profit")
        self.assertGreater(result.final_balance, result.initial_balance)
        self.assertIsInstance(result.sharpe_ratio, float)
        self.assertEqual(result.pnl_r_squared, 0.0)

    def test_futures_pnl_returns_margin_plus_pnl_minus_fees(self):
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="futures",
            position_size_pct=0.5,
            leverage=2.0,
            fee_rate=0.001,
            slippage_bps=0.0,
            spread_bps=0.0,
            stop_loss_pct=None,
            take_profit_pct=None,
            funding_enabled=False,
        )
        result = BacktestEngine(config).run(make_candles(), BuyAndHoldStrategy())

        trade = result.trades[0]
        self.assertAlmostEqual(trade.margin, 500.0)
        self.assertAlmostEqual(trade.quantity, 10.0)
        self.assertAlmostEqual(trade.gross_pnl, 55.0)
        self.assertAlmostEqual(trade.entry_fee, 1.0)
        self.assertAlmostEqual(trade.exit_fee, 1.055)
        self.assertAlmostEqual(trade.net_pnl, 52.945)
        self.assertAlmostEqual(result.final_balance, 1052.945)

    def test_spot_pnl_uses_cash_proceeds_minus_cost_basis(self):
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="spot",
            position_size_pct=0.5,
            leverage=1.0,
            fee_rate=0.001,
            slippage_bps=0.0,
            spread_bps=0.0,
            stop_loss_pct=None,
            take_profit_pct=None,
        )
        result = BacktestEngine(config).run(make_candles(), BuyAndHoldStrategy())

        trade = result.trades[0]
        self.assertAlmostEqual(trade.margin, 500.0)
        self.assertAlmostEqual(trade.quantity, 5.0)
        self.assertAlmostEqual(trade.gross_pnl, 27.5)
        self.assertAlmostEqual(trade.entry_fee, 0.5)
        self.assertAlmostEqual(trade.exit_fee, 0.5275)
        self.assertAlmostEqual(trade.net_pnl, 26.4725)
        self.assertAlmostEqual(result.final_balance, 1026.4725)

    def test_futures_funding_is_included_once_in_net_pnl(self):
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="futures",
            position_size_pct=0.5,
            leverage=2.0,
            fee_rate=0.0,
            slippage_bps=0.0,
            spread_bps=0.0,
            stop_loss_pct=None,
            take_profit_pct=None,
            funding_rate_per_interval=0.01,
            funding_interval_hours=1.0,
        )
        result = BacktestEngine(config).run(make_hourly_flat_candles(), BuyAndHoldStrategy())

        trade = result.trades[0]
        self.assertAlmostEqual(trade.gross_pnl, 0.0)
        self.assertAlmostEqual(trade.funding_paid, 10.0)
        self.assertAlmostEqual(trade.net_pnl, -10.0)
        self.assertAlmostEqual(result.final_balance, 990.0)


if __name__ == "__main__":
    unittest.main()
