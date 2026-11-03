import unittest

from futures_trading.data_sources import generate_sample_candles
from futures_trading.optimizer import GridSearchOptimizer
from futures_trading.simulator import BacktestConfig


class OptimizerTests(unittest.TestCase):
    def test_optimizer_returns_best_row(self):
        candles = generate_sample_candles(
            symbol="BTCUSDT",
            market_type="futures",
            timeframe="1h",
            days=5,
            exchange="test",
            seed=10,
        )
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="futures",
            position_size_pct=0.25,
            leverage=3.0,
        )
        result = GridSearchOptimizer(config).run(
            candles,
            entry_drop_grid=[0.002, 0.004],
            take_profit_grid=[0.006],
            stop_loss_grid=[0.004, 0.008],
        )

        self.assertIsNotNone(result.best)
        self.assertEqual(len(result.rows), 4)
        self.assertTrue(hasattr(result.best, "sharpe_ratio"))
        self.assertTrue(0.0 <= result.best.pnl_r_squared <= 1.0)

    def test_optimizer_covers_short_strategy_parameters(self):
        candles = generate_sample_candles(
            symbol="BTCUSDT",
            market_type="futures",
            timeframe="1h",
            days=3,
            exchange="test",
            seed=11,
        )
        config = BacktestConfig(
            initial_balance=1000.0,
            market_type="futures",
            position_size_pct=0.25,
            leverage=3.0,
        )
        result = GridSearchOptimizer(config).run(
            candles,
            entry_drop_grid=[0.002, 0.004],
            entry_rise_grid=[0.003, 0.005],
            take_profit_grid=[0.006],
            stop_loss_grid=[0.004],
            allow_short=True,
        )

        self.assertEqual(len(result.rows), 4)
        self.assertTrue(all(row.allow_short for row in result.rows))
        self.assertEqual({row.entry_rise_pct for row in result.rows}, {0.003, 0.005})

    def test_ut_bot_optimizer_runs_small_grid(self):
        candles = generate_sample_candles(
            symbol="BTCUSDT",
            market_type="futures",
            timeframe="1h",
            days=5,
            exchange="test",
            seed=21,
        )
        config = BacktestConfig(initial_balance=1000.0, market_type="futures", position_size_pct=0.25, leverage=3.0)
        result = GridSearchOptimizer(config).run_ut_bot(
            candles,
            key_grid=[2.0],
            atr_period_grid=[7],
            lr_period_grid=[20],
            exit_pct_grid=[0.006],
            exit_delay_grid=[1],
            take_profit_grid=[0.01],
            stop_loss_grid=[0.008],
            allow_short=False,
            use_heikin_ashi=False,
            enable_exit_signals=True,
            enable_time_range_disable=False,
            disable_session="2200-0500",
            enable_cooldown=False,
            cooldown_minutes=5,
        )
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].optimizer_strategy, "ut_bot")
        self.assertEqual(result.rows[0].ut_key_value, 2.0)


if __name__ == "__main__":
    unittest.main()
