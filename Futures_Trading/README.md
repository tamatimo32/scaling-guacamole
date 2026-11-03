# Futures Trading Lab

A Python research lab for replaying historical Binance crypto candles as if a
live bot were trading them. The project runs entirely on the Python standard
library — no external dependencies — and ships with:

- A Binance USD-M futures and spot candle downloader.
- A SQLite candle store covering `1h`, `4h`, `8h`, and `12h` intervals.
- A backtest engine that models taker fees, bid/ask spread, slippage, leverage,
  initial and maintenance margin, liquidations, and Binance-style funding
  payments every 8 hours.
- A funding rate downloader that pulls real Binance USD-M funding history.
- A grid optimizer that searches percentage-based entry/take-profit/stop-loss
  rules.
- A multi-tab HTML dashboard (`Backtest`, `Optimizer`, `Market Data`) with
  equity curve, drawdown, monthly returns heatmap, parameter heatmap,
  Sharpe/Sortino/Calmar metrics, full trade log, and CSV export — ready for new
  indicator strategies.

## Project Shape

```text
src/futures_trading/
  cli.py            Command line entry point
  config.py         Defaults and runtime config
  data_sources.py   Binance candle and funding downloader
  grids.py          Grid string parser
  models.py         Core dataclasses and metrics
  optimizer.py      Grid search optimizer
  simulator.py      Spot/futures backtest engine with funding
  storage.py        SQLite candle store
  strategies.py     Strategy interface and reference strategies
  web.py            Local dashboard HTTP server
  web_html.py       Dashboard HTML/CSS/JS
tests/
  test_grids.py
  test_optimizer.py
  test_simulator.py
  test_web.py
```

## First Setup

From this folder:

```powershell
$env:PYTHONPATH = "src"
```

Then initialize the local SQLite store:

```powershell
python -m futures_trading.cli init-db
```

If `python` is not on your terminal path, configure the interpreter in PyCharm
or use the bundled venv: `.\.venv\Scripts\python.exe -m futures_trading.cli ...`.

## Download 3 Months Of Real Binance Candles

Default futures source is Binance USD-M futures (`BTCUSDT`):

```powershell
python -m futures_trading.cli download --symbol BTCUSDT --market-type futures --days 90 --timeframes 1h 4h 8h 12h
```

For spot:

```powershell
python -m futures_trading.cli download --symbol BTCUSDT --market-type spot --days 90 --timeframes 1h 4h 8h 12h
```

The data is stored at:

```text
data/market_data.sqlite
```

## Inspect Stored Data

```powershell
python -m futures_trading.cli show-data --symbol BTCUSDT --market-type futures --timeframes 1h 4h 8h 12h
```

## Funding Rate History

```powershell
python -m futures_trading.cli download-funding --symbol BTCUSDT --days 90
```

Prints the average per-8h funding rate and the implied annualized cost paid by
long positions. Use the value to set `--funding-rate-per-interval` on the
backtest or optimizer commands when you want to mirror the recent regime.

## Offline Sample Data

Use this if you want to test the simulator without hitting the network:

```powershell
python -m futures_trading.cli generate-sample-data --symbol BTCUSDT --market-type futures --timeframes 1h 4h 8h 12h --days 90
```

The generator now produces multi-regime candles with volatility clustering and
occasional shocks so dip-buying and breakout strategies are exercised
realistically.

## Run A Backtest

Example futures backtest using the threshold strategy with realistic Binance
fees, spread, slippage, and 8-hour funding:

```powershell
python -m futures_trading.cli backtest `
  --symbol BTCUSDT `
  --market-type futures `
  --timeframe 1h `
  --strategy threshold `
  --entry-drop-pct 0.004 `
  --take-profit-pct 0.012 `
  --stop-loss-pct 0.006 `
  --leverage 5
```

Spot mode uses the same backtest command with `--market-type spot`.

The CLI prints net PnL, total return, annualized return, Sharpe, Sortino,
Calmar, profit factor, payoff ratio, expectancy, max drawdown duration,
longest win/loss streaks, total funding, and total fees.

## Run The Optimizer

```powershell
python -m futures_trading.cli optimize `
  --symbol BTCUSDT `
  --market-type futures `
  --timeframe 1h `
  --entry-drop-grid 0.002:0.008:0.002 `
  --take-profit-grid 0.006:0.014:0.004 `
  --stop-loss-grid 0.004:0.008:0.002 `
  --leverage 5
```

The optimizer accepts comma lists and inclusive ranges. These are equivalent:

```text
0.002,0.004,0.006,0.008
0.002:0.008:0.002
```

For short-side testing with the threshold strategy:

```powershell
python -m futures_trading.cli optimize `
  --symbol BTCUSDT `
  --market-type futures `
  --timeframe 1h `
  --allow-short `
  --entry-drop-grid 0.002:0.008:0.002 `
  --entry-rise-grid 0.002:0.008:0.002 `
  --take-profit-grid 0.006:0.014:0.004 `
  --stop-loss-grid 0.004:0.008:0.002 `
  --leverage 5
```

The optimizer currently searches simple percentage rules. Later, your
indicators can be added as new strategy classes in `strategies.py` and
optimized with the same engine.

## Run The Dashboard

PyCharm-friendly option:

```text
Right-click run_dashboard.py -> Run
```

That starts the local server and opens the dashboard in Edge or your default
browser. If port `8770` is busy, the launcher automatically tries the next
free port.

Command-line option:

```powershell
python -m futures_trading.cli dashboard --db data/market_data.sqlite --host 127.0.0.1 --port 8770 --open-browser
```

Then open:

```text
http://127.0.0.1:8770
```

If port `8770` is already in use, the dashboard now exits immediately with a
message that tells you which port to retry. Just pass any free port with
`--port 8771` (etc.).

If you press **Run Backtest** or **Run Optimizer** and the requested
exchange/symbol/timeframe is missing from SQLite, the dashboard will
auto-download 90 days of Binance candles for that combination and then run
the simulation – you do not have to click **Download** yourself.

The dashboard has three tabs:

### Backtest

- Full configuration form for market, fees, spread, slippage, leverage,
  funding, stop loss, take profit, and the threshold strategy parameters.
- Performance Snapshot card with 24 metrics: net PnL, total return,
  annualized return, max drawdown, max drawdown duration in bars, Sharpe,
  Sortino, Calmar, profit factor, win rate, payoff ratio, expectancy,
  trade counts (long / short), average bars held, longest win and loss streaks,
  best and worst trade, total fees, total funding, PnL R², final balance,
  duration in days.
- Charts: price line with entry and exit markers, equity curve, drawdown,
  trade PnL distribution, and monthly returns bar chart.
- Exit reason badge mix (take profit, stop loss, liquidation, end of backtest).
- Full trade log with side, entry/exit times, bars held, prices, quantity,
  margin, net PnL, return %, fees, funding, and exit reason.
- "Export trades CSV" button.

### Optimizer

- Grid form with entry drop, entry rise (when shorts are allowed), take profit,
  stop loss, plus the same fee, spread, slippage, leverage, and funding
  controls.
- "Best Combinations" cards by final balance, return, Sharpe, Sortino, Calmar,
  and PnL R².
- Parameter heatmap (entry drop x take profit, color-coded by total return).
- Sharpe vs return scatter (point size scales with PnL R²).
- Filter row for return, drawdown, Sharpe, Sortino, Calmar, R², win rate, and
  trade count, with sort key and direction.
- Click any optimizer row to load its parameters into the Backtest tab and
  rerun it.

### Market Data

- Stored Candle Inventory table with row counts and date ranges per timeframe.
- "Download Real Binance Candles" form (symbol, market, days, timeframes) and a
  "Generate sample data" button that backfills SQLite from the offline
  generator.
- "Funding Rate History (Binance USD-M)" form with summary line and a chart of
  the recent per-interval funding rates.

## Notes On Realism

- Default fee rate is 0.05% (Binance USD-M futures taker). Maker fee is also
  configurable via the API.
- A bid/ask spread is applied as a half-spread on top of slippage on every
  entry and exit.
- Funding is charged or credited every 8 hours while a position is open.
  Long positions pay positive funding rates and shorts receive them; flip the
  sign with a negative `--funding-rate-per-interval` to mirror periods of
  inverted funding.
- Stop loss, take profit, and liquidation prices are checked against candle
  high/low ranges. If both stop loss and take profit are touched in the same
  candle, the engine takes the conservative stop-loss path.
- This is still candle-level simulation. It is realistic enough for first
  research, but not the same as tick-level order book replay. The architecture
  leaves room to add order book snapshots, partial fills, and indicator
  pipelines later.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -v tests
```
