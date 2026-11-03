"""Static HTML/CSS/JS payload for the local trading dashboard.

The whole dashboard is shipped as one string so the server stays dependency
free and the page works fully offline. The placeholder ``__DEFAULT_DB__`` is
substituted with the on-disk SQLite path on every render.
"""

from __future__ import annotations


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Futures Trading Lab</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d9dee7;
      --line-strong: #c0c8d4;
      --accent: #0f766e;
      --accent-strong: #0b5f59;
      --blue: #1d4ed8;
      --bad: #b42318;
      --good: #047857;
      --warn: #b54708;
      --shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }

    [hidden] { display: none !important; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overflow-x: hidden;
    }

    header {
      background: #111827;
      color: #ffffff;
      padding: 16px 24px 0;
      border-bottom: 4px solid var(--accent);
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      flex-wrap: wrap;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.2px;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 16px;
      font-weight: 700;
    }

    .subtitle {
      color: #cbd5e1;
      font-size: 13px;
      margin-top: 4px;
    }

    nav.tabs {
      display: flex;
      gap: 6px;
      margin-top: 16px;
    }

    nav.tabs button {
      background: transparent;
      color: #cbd5e1;
      border: 0;
      border-radius: 6px 6px 0 0;
      padding: 10px 18px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }

    nav.tabs button:hover { background: rgba(255, 255, 255, 0.08); }

    nav.tabs button.active {
      background: var(--bg);
      color: var(--ink);
    }

    main {
      width: auto;
      margin: 16px 8px 32px;
      display: grid;
      gap: 16px;
    }

    section.panel {
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 16px;
      max-width: calc(100vw - 16px);
      min-width: 0;
    }

    .backtest-layout,
    .optimizer-dashboard {
      display: grid;
      grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }

    .backtest-results,
    .optimizer-results {
      display: grid;
      gap: 16px;
      min-width: 0;
    }

    .backtest-results > .panel,
    .backtest-results > .charts-grid,
    .backtest-results > .secondary-grid,
    .optimizer-results > .panel,
    .optimizer-results > .charts-grid {
      max-width: 100%;
    }

    .backtest-config-rail,
    .optimizer-config-rail {
      position: sticky;
      top: 12px;
      max-height: calc(100vh - 24px);
      overflow: auto;
      padding: 0;
    }

    .rail-header {
      padding: 14px 14px 12px;
      background: #111827;
      color: #ffffff;
      border-bottom: 4px solid var(--accent);
    }

    .rail-header h2 {
      margin: 0;
      color: #ffffff;
      font-size: 16px;
    }

    .rail-header p {
      margin: 6px 0 0;
      color: #d1d5db;
      font-size: 12px;
      line-height: 1.45;
    }

    .rail-form {
      display: grid;
      gap: 10px;
      padding: 12px;
    }

    .config-family {
      --family: var(--accent);
      border: 1px solid var(--line);
      border-left: 5px solid var(--family);
      border-radius: 8px;
      padding: 10px;
      margin: 0;
      background: #ffffff;
      display: grid;
      gap: 10px;
      min-width: 0;
    }

    .config-family legend {
      padding: 0 6px;
      color: var(--family);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }

    .family-market { --family: #2563eb; background: #eff6ff; }
    .family-strategy { --family: #7c3aed; background: #f5f3ff; }
    .family-capital { --family: #0f766e; background: #ecfdf5; }
    .family-costs { --family: #b45309; background: #fffbeb; }
    .family-risk { --family: #b42318; background: #fff1f2; }
    .family-ut { --family: #047857; background: #ecfdf5; }

    .rail-field {
      display: grid;
      gap: 4px;
      min-width: 0;
    }

    .rail-field input,
    .rail-field select {
      min-height: 34px;
    }

    .rail-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .rail-check {
      align-items: flex-start;
      line-height: 1.25;
      min-height: auto;
    }

    .field-help {
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
      font-weight: 500;
    }

    .rail-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      padding: 2px 0 4px;
    }

    .rail-actions .action {
      width: 100%;
      justify-content: center;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 12px;
      align-items: end;
      min-width: 0;
    }

    .form-grid.compact {
      grid-template-columns: repeat(5, minmax(120px, 1fr));
    }

    label {
      display: grid;
      gap: 5px;
      font-size: 12px;
      color: var(--muted);
      font-weight: 650;
    }

    .field-title {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }

    .help-tip {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 1px solid #94a3b8;
      background: #ffffff;
      color: #475467;
      font-size: 10px;
      line-height: 1;
      font-weight: 800;
      cursor: help;
    }

    .help-tip::after {
      content: attr(data-tip);
      position: absolute;
      left: 50%;
      bottom: calc(100% + 8px);
      z-index: 10;
      width: max-content;
      max-width: min(340px, calc(100vw - 48px));
      padding: 9px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #111827;
      color: #ffffff;
      box-shadow: var(--shadow);
      font-size: 12px;
      line-height: 1.35;
      font-weight: 600;
      white-space: normal;
      text-align: left;
      opacity: 0;
      pointer-events: none;
      transform: translate(-50%, 4px);
      transition: opacity 120ms ease, transform 120ms ease;
    }

    .help-tip:hover::after,
    .help-tip:focus::after {
      opacity: 1;
      transform: translate(-50%, 0);
    }

    input,
    select {
      width: 100%;
      min-height: 36px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #ffffff;
      color: var(--ink);
      padding: 7px 9px;
      font: inherit;
      font-size: 13px;
    }

    input:focus,
    select:focus {
      outline: 2px solid rgba(15, 118, 110, 0.25);
      border-color: var(--accent);
    }

    .check-label {
      min-height: 36px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--ink);
      font-size: 13px;
    }

    .check-label input { width: 16px; min-height: 16px; }

    .wide { grid-column: span 2; }

    .grid-builder {
      grid-column: 1 / -1;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: #f8fafc;
    }
    .optimizer-guide {
      background: #f0fdfa;
      border: 1px solid #99f6e4;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 13px;
      line-height: 1.55;
      color: var(--ink);
    }
    .optimizer-guide strong { color: #0f766e; }
    .optimizer-guide ul { margin: 10px 0 0 0; padding-left: 20px; }
    .optimizer-guide li { margin: 5px 0; }
    .optimizer-guide code {
      font-size: 11.5px;
      background: #ccfbf1;
      padding: 1px 5px;
      border-radius: 4px;
      font-weight: 600;
    }
    .grid-builder-head {
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 6px;
      margin-bottom: 8px;
      color: var(--ink);
      font-size: 13px;
      font-weight: 700;
    }
    .grid-builder-explainer {
      margin: 0;
      font-size: 12px;
      line-height: 1.45;
      font-weight: 500;
      color: var(--muted);
    }
    .grid-builder-syntax {
      font-size: 11px;
      color: var(--muted);
      font-weight: 650;
    }
    .grid-main-input {
      font-family: ui-monospace, Consolas, monospace;
      font-size: 12px;
    }
    .grid-builder-controls {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-end;
      margin-top: 8px;
    }
    .grid-builder-controls.grid-builder-compact-row {
      gap: 8px;
      margin-top: 6px;
    }
    .grid-builder-controls label {
      display: grid;
      gap: 3px;
      font-size: 11px;
      min-width: 72px;
    }
    .grid-builder-compact-row label {
      min-width: 0;
      gap: 4px;
      font-size: 10px;
      font-weight: 650;
    }
    .grid-builder-controls input { min-height: 32px; }
    .grid-builder-compact-row input[type="number"].grid-num-input {
      width: 4.9rem;
      min-width: 0;
      min-height: 34px;
      padding: 6px 4px;
      text-align: center;
      font-variant-numeric: tabular-nums;
    }
    .grid-sent-wrap {
      margin-top: 10px;
    }
    .grid-sent-hint {
      display: block;
      font-size: 11px;
      margin-bottom: 4px;
    }
    .grid-main-input--sent {
      max-width: 17rem;
      min-height: 34px;
      font-size: 12px;
    }
    .grid-presets {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
      align-items: center;
    }
    .grid-presets span {
      font-size: 11px;
      color: var(--muted);
      margin-right: 4px;
    }
    button.chip {
      padding: 4px 10px;
      font-size: 12px;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
    }
    button.chip:hover {
      border-color: var(--accent);
      background: rgba(15, 118, 110, 0.06);
    }
    .optimizer-layout {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .form-grid.optimizer-layout {
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 12px;
      align-items: end;
    }
    .form-grid.optimizer-layout > .optimizer-guide,
    .form-grid.optimizer-layout > .optimizer-layout,
    .form-grid.optimizer-layout > #opt-form-leg-preview-wrap,
    .form-grid.optimizer-layout > .actions {
      grid-column: 1 / -1;
    }
    .form-grid.optimizer-layout > .actions,
    .filter-actions {
      justify-content: center;
    }
    .optimizer-config-rail .form-grid.optimizer-layout {
      grid-template-columns: 1fr;
      gap: 10px;
    }
    .optimizer-config-rail form {
      padding: 12px;
    }
    .optimizer-config-rail .status {
      padding: 0 12px 12px;
    }
    .optimizer-config-rail .form-grid.optimizer-layout > *,
    .optimizer-config-rail .wide,
    .optimizer-config-rail .strategy-stack-panel,
    .optimizer-config-rail #opt-form-leg-preview-wrap,
    .optimizer-config-rail [data-opt-threshold-only],
    .optimizer-config-rail [data-opt-ut-only] {
      grid-column: 1 / -1;
    }
    .optimizer-config-rail .optimizer-guide {
      border-left: 5px solid #2563eb;
      border-radius: 8px;
      padding: 10px 12px;
      background: #eff6ff;
    }
    .optimizer-config-rail .grid-builder {
      border-left-width: 5px;
      border-left-color: #dc2626;
      background: #fff7ed;
    }
    .optimizer-config-rail [data-opt-threshold-only] {
      border-left-color: #7c3aed;
      background: #f5f3ff;
    }
    .optimizer-config-rail [data-opt-shared-grid] {
      border-left-color: #dc2626;
      background: #fff7ed;
    }
    .optimizer-config-rail [data-opt-ut-only] {
      border: 1px solid var(--line);
      border-left: 5px solid #4f46e5;
      border-radius: 8px;
      padding: 10px;
      background: #eef2ff;
    }
    .optimizer-config-rail [data-opt-ut-only] .grid-builder {
      background: #ffffff;
      border-left-color: #4f46e5;
    }
    .optimizer-config-rail .strategy-stack-panel {
      border-left: 5px solid #7c3aed;
      border-style: solid;
      background: #f5f3ff;
    }
    .optimizer-config-rail label {
      min-height: auto;
    }
    .optimizer-config-rail .toggle-row {
      align-items: flex-start;
      margin: 4px 0;
    }
    .optimizer-config-rail .opt-form-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      justify-content: stretch;
    }
    .optimizer-config-rail .opt-form-actions .action {
      width: 100%;
    }
    .strategy-stack-panel {
      grid-column: 1 / -1;
      border: 1px dashed #94a3b8;
      border-radius: 8px;
      padding: 12px 14px;
      background: #f1f5f9;
    }
    .strategy-stack-panel h3 {
      margin: 0 0 10px 0;
      font-size: 13px;
      color: var(--ink);
      font-weight: 750;
    }
    .toggle-row {
      display: flex;
      flex-wrap: wrap;
      gap: 14px 20px;
      align-items: center;
      margin: 8px 0;
    }

    .leg-cards {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }
    .leg-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: #ffffff;
    }
    .leg-card h4 {
      margin: 0 0 8px 0;
      font-size: 13px;
      color: var(--ink);
      font-weight: 750;
    }
    .param-dl {
      display: grid;
      grid-template-columns: minmax(100px, auto) 1fr;
      gap: 6px 12px;
      font-size: 12px;
      margin: 0;
    }
    .param-dl dt { color: var(--muted); margin: 0; font-weight: 650; }
    .param-dl dd { margin: 0; word-break: break-word; }
    .param-dl code {
      font-size: 11px;
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .strategy-ref details {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 10px;
      background: #ffffff;
    }
    .strategy-ref summary {
      cursor: pointer;
      font-weight: 750;
      font-size: 14px;
    }
    .strategy-ref .ex-buy {
      background: rgba(4, 120, 87, 0.08);
      border-left: 3px solid var(--good);
      padding: 10px 12px;
      margin: 10px 0 0 0;
      font-size: 13px;
      border-radius: 0 6px 6px 0;
    }
    .estimator-panel .estimator-disclaimer {
      font-size: 12px;
      line-height: 1.45;
      margin: 0 0 12px;
      max-width: 56rem;
    }
    .estimator-panel .estimator-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    #opt-row-legs-detail {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }

    .actions { display: flex; gap: 8px; align-items: end; flex-wrap: wrap; }

    .actions.wide {
      grid-column: 1 / -1;
      justify-content: center;
      justify-self: stretch;
      width: 100%;
    }

    .opt-form-actions {
      justify-content: center;
      margin-top: 12px;
    }

    #optimizer-form > .form-grid > .actions {
      grid-column: 1 / -1;
      justify-content: center;
      justify-self: stretch;
      width: 100%;
    }

    button.action {
      min-height: 36px;
      border: 1px solid var(--accent-strong);
      border-radius: 6px;
      background: var(--accent);
      color: #ffffff;
      padding: 7px 14px;
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }

    button.action.secondary {
      background: #ffffff;
      color: var(--ink);
      border-color: #cbd5e1;
    }

    button.action:disabled { opacity: 0.55; cursor: progress; }

    .status {
      margin-top: 12px;
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
    }

    .status.error { color: var(--bad); font-weight: 700; }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(8, minmax(120px, 1fr));
      gap: 1px;
      background: var(--line);
      border: 1px solid var(--line);
    }

    .metric {
      background: #ffffff;
      padding: 12px 14px;
      min-height: 76px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    .metric strong {
      display: block;
      margin-top: 6px;
      color: var(--ink);
      font-size: clamp(15px, 1.6vw, 22px);
      line-height: 1.05;
    }

    .metric strong.good { color: var(--good); }
    .metric strong.bad { color: var(--bad); }

    .metric.metric--pre strong {
      white-space: pre-line;
      font-size: 12px;
      line-height: 1.4;
      font-weight: 700;
    }

    .charts-grid {
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
      gap: 16px;
      max-width: calc(100vw - 16px);
      min-width: 0;
    }

    .chart-card {
      background: #ffffff;
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 12px 14px;
    }

    .chart-card h2 {
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--muted);
    }

    canvas {
      width: 100%;
      height: 280px;
      display: block;
    }

    canvas.tall { height: 320px; }
    canvas.short { height: 200px; }

    .secondary-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }

    .table-wrap {
      overflow: auto;
      max-height: 520px;
      border: 1px solid var(--line);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 1100px;
      background: #ffffff;
      font-size: 13px;
    }

    th, td {
      padding: 8px 10px;
      border-bottom: 1px solid #e8edf3;
      text-align: right;
      white-space: nowrap;
    }

    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #eef2f7;
      color: #344054;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      cursor: pointer;
    }

    th[data-sort-active="asc"]::after { content: " ▲"; }
    th[data-sort-active="desc"]::after { content: " ▼"; }

    th:first-child, td:first-child { text-align: left; }

    tbody tr:hover { background: #f8fafc; cursor: pointer; }

    tbody tr.selected { background: rgba(15, 118, 110, 0.08); }

    .good { color: var(--good); font-weight: 700; }
    .bad { color: var(--bad); font-weight: 700; }
    .muted { color: var(--muted); }

    .filter-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
    }

    .filter-actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
    }

    .pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.2px;
      text-transform: uppercase;
    }

    .pill.long { background: rgba(4, 120, 87, 0.15); color: var(--good); }
    .pill.short { background: rgba(180, 35, 24, 0.15); color: var(--bad); }
    .pill.tp { background: rgba(4, 120, 87, 0.15); color: var(--good); }
    .pill.sl { background: rgba(180, 35, 24, 0.15); color: var(--bad); }
    .pill.liq { background: rgba(146, 64, 14, 0.15); color: var(--warn); }
    .pill.end { background: rgba(29, 78, 216, 0.12); color: var(--blue); }

    @media (max-width: 1300px) {
      .form-grid, .form-grid.compact, .form-grid.optimizer-layout { grid-template-columns: repeat(3, minmax(130px, 1fr)); }
      .summary-grid { grid-template-columns: repeat(4, minmax(120px, 1fr)); }
      .charts-grid, .secondary-grid { grid-template-columns: 1fr; }
      .filter-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }

    @media (max-width: 1100px) {
      .backtest-layout,
      .optimizer-dashboard { grid-template-columns: 1fr; }
      .backtest-config-rail,
      .optimizer-config-rail {
        position: static;
        max-height: none;
      }
      .rail-row { grid-template-columns: 1fr 1fr; }
    }

    @media (max-width: 720px) {
      main { margin: 12px 8px 24px; }
      header { padding: 12px 16px 0; }
      .form-grid, .form-grid.compact, .form-grid.optimizer-layout, .summary-grid, .filter-grid { grid-template-columns: 1fr; }
      .wide { grid-column: span 1; }
      .rail-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="header-row">
      <div>
        <h1>Futures Trading Lab</h1>
        <div class="subtitle">Trading bot control center — backtest, optimize, and inspect strategies on Binance-history data.</div>
      </div>
      <div id="header-status" class="muted" style="font-size:12px"></div>
    </div>
    <nav class="tabs">
      <button data-tab="backtest" class="active">Backtest</button>
      <button data-tab="optimizer">Optimizer</button>
      <button data-tab="data">Market Data</button>
    </nav>
  </header>

  <main>
    <!-- BACKTEST TAB -->
    <div class="backtest-layout" data-tab-panel="backtest">
      <section class="panel backtest-config-rail">
        <div class="rail-header">
          <h2>Backtest Setup</h2>
          <p>All inputs live here. Families are color-coded so market source, strategy, capital, costs, and risk assumptions stay mentally separate.</p>
        </div>
        <form id="backtest-form" class="rail-form">
          <fieldset class="config-family family-market">
            <legend>Market Data</legend>
            <label class="rail-field">Database
              <input name="db_path" value="__DEFAULT_DB__">
              <span class="field-help">SQLite file used for candles. The dashboard reads this first; if too few candles exist, it can auto-fill from Binance or generated sample data.</span>
            </label>
            <div class="rail-row">
              <label class="rail-field">Exchange
                <input name="exchange" value="binance">
                <span class="field-help">Data namespace in SQLite. Use <strong>binance</strong> for live downloaded spot/futures candles, or <strong>sample</strong> for synthetic test data.</span>
              </label>
              <label class="rail-field">Symbol
                <input name="symbol" value="BTCUSDT">
                <span class="field-help">Instrument to test. Keep the quote currency consistent with your account balance assumptions.</span>
              </label>
            </div>
            <div class="rail-row">
              <label class="rail-field">Market
                <select name="market_type">
                  <option value="futures" selected>Futures</option>
                  <option value="spot">Spot</option>
                </select>
                <span class="field-help">Futures uses margin, leverage, shorting, liquidation checks, and funding. Spot buys the asset outright with leverage fixed to 1.</span>
              </label>
              <label class="rail-field">Timeframe
                <select name="timeframe">
                  <option value="1h" selected>1h</option>
                  <option value="4h">4h</option>
                  <option value="8h">8h</option>
                  <option value="12h">12h</option>
                </select>
                <span class="field-help">Candle size. Signals are evaluated once per candle; orders created by a signal execute on the next candle open.</span>
              </label>
            </div>
            <label class="rail-field">SQLite / Binance lookback (days)
              <input name="auto_download_days" type="number" step="1" min="2" max="400" value="90">
              <span class="field-help">Target trailing calendar history to fetch when SQLite is missing data. The actual run span is shown later from candle timestamps, not from PC clock runtime.</span>
            </label>
          </fieldset>

          <fieldset class="config-family family-strategy">
            <legend>Strategy</legend>
            <label class="rail-field">Primary strategy
              <select name="strategy_name" id="bt-strategy-select">
                <option value="threshold" selected>Threshold</option>
                <option value="ut-bot">UT Bot Alerts</option>
                <option value="buy-hold">Buy &amp; Hold</option>
              </select>
              <span class="field-help">Threshold reacts to one-candle percentage moves. UT Bot follows the ATR trailing-stop indicator. Buy &amp; Hold enters long once at the start.</span>
            </label>
            <label class="rail-field">Strategy combine
              <select name="combine_mode">
                <option value="all" selected>All agree (AND)</option>
                <option value="any">First signal (OR)</option>
              </select>
              <span class="field-help">When a companion is enabled, AND requires every leg to emit the same entry on the same candle; OR takes the first non-hold signal in stack order.</span>
            </label>
            <label class="check-label rail-check">
              <input name="companion_buy_hold" type="checkbox" value="true">
              <span>Stack Buy &amp; Hold with the primary strategy.<br><span class="field-help">Useful as a baseline companion. In OR mode it can enter immediately; in AND mode it acts like a very strict filter.</span></span>
            </label>
            <label class="rail-field">Entry drop (% vs prior close)
              <input name="entry_drop_pct" type="number" step="0.05" value="0.4" title="Minimum drop from previous close to trigger long, e.g. 0.4 = 0.4%">
              <span class="field-help">Threshold long entry. Example: 0.4 means this candle must close at least 0.40% below the previous close before the next candle open can buy.</span>
            </label>
            <label class="rail-field">Entry rise (% vs prior close)
              <input name="entry_rise_pct" type="number" step="0.05" value="0.4" title="Minimum rise from previous close to trigger short, e.g. 0.4 = 0.4%">
              <span class="field-help">Threshold short entry. Only used when shorts are allowed and market is futures. Spot ignores short entries.</span>
            </label>
            <label class="check-label rail-check">
              <input name="allow_short" type="checkbox" value="true">
              <span>Allow shorts.<br><span class="field-help">Only futures can open short positions. Spot mode stays long-only even if this is checked.</span></span>
            </label>
          </fieldset>

          <fieldset class="config-family family-capital">
            <legend>Capital &amp; Size</legend>
            <label class="rail-field">Initial Balance
              <input name="initial_balance" type="number" step="100" value="10000">
              <span class="field-help">Starting account equity in quote currency. All return percentages use this as the denominator.</span>
            </label>
            <label class="rail-field">Position size (% of balance)
              <input name="position_size_pct" type="number" step="1" min="0" max="100" value="25" title="Percent of account balance used as margin (futures) or notional (spot), e.g. 25 = 25%">
              <span class="field-help">If enabled, futures uses this percent as margin before leverage; spot uses it as purchase notional. Example: 25 on $10,000 means $2,500 margin/notional.</span>
            </label>
            <label class="rail-field">Stake ($ margin / spot notional)
              <input name="stake_usd" type="number" step="100" value="2500">
              <span class="field-help">Fixed trade size used only when the fixed-stake switch below is on. Futures treats this as margin; spot treats it as asset notional before fee.</span>
            </label>
            <label class="check-label rail-check">
              <input name="ignore_position_size_pct" type="checkbox" value="true">
              <span>Use fixed $ stake.<br><span class="field-help">Switches sizing from a changing balance percentage to the fixed stake above, capped by available cash/margin.</span></span>
            </label>
            <label class="rail-field">Leverage
              <input name="leverage" type="number" step="0.5" value="5">
              <span class="field-help">Futures notional multiplier. $2,500 margin at 5× controls $12,500 notional. Spot always runs at 1× regardless of this field.</span>
            </label>
          </fieldset>

          <fieldset class="config-family family-costs">
            <legend>Costs &amp; Funding</legend>
            <label class="rail-field">Fee (% per notional, each side)
              <input name="fee_rate" type="number" step="0.005" value="0.05" title="Taker-style fee as a percent of notional, e.g. 0.05 = 0.05% per side">
              <span class="field-help">Charged on entry and exit notional. For futures, fees are based on leveraged notional; for spot, fees are based on buy/sell value.</span>
            </label>
            <div class="rail-row">
              <label class="rail-field">Slippage (bps)
                <input name="slippage_bps" type="number" step="0.1" value="1.5">
                <span class="field-help">Execution price penalty. One basis point is 0.01% of price. Long entries/short exits get worse upward; long exits/short entries get worse downward.</span>
              </label>
              <label class="rail-field">Half-spread (bps)
                <input name="spread_bps" type="number" step="0.1" value="1.0">
                <span class="field-help">Bid/ask cost model added to slippage. It widens simulated fills without changing candle OHLC.</span>
              </label>
            </div>
            <label class="rail-field">Funding rate (% per interval)
              <input name="funding_rate_per_interval" type="number" step="0.001" value="0.01" title="Funding accrual per funding interval, e.g. 0.01 = 0.01%">
              <span class="field-help">Futures-only perpetual funding. Positive values charge longs and credit shorts at each interval; spot ignores funding entirely.</span>
            </label>
            <label class="rail-field">Funding Interval (h)
              <input name="funding_interval_hours" type="number" step="1" value="8">
              <span class="field-help">How often funding is applied while a futures position is open. Binance-style perpetuals commonly settle every 8 hours.</span>
            </label>
            <label class="check-label rail-check">
              <input name="ignore_funding" type="checkbox" value="true">
              <span>Ignore funding.<br><span class="field-help">Research switch that sets funding accrual to zero while keeping fee, slippage, and spread assumptions active.</span></span>
            </label>
          </fieldset>

          <fieldset class="config-family family-risk">
            <legend>Risk Exits</legend>
            <label class="rail-field">Stop loss (% from entry)
              <input name="stop_loss_pct" type="number" step="0.05" value="0.8" title="Distance to stop as a percent, e.g. 0.8 = 0.8%">
              <span class="field-help">Adverse distance from fill price. Long stops are below entry; short stops are above entry. Example: 0.8 means 0.80% away.</span>
            </label>
            <label class="rail-field">Take profit (% from entry)
              <input name="take_profit_pct" type="number" step="0.05" value="1.2" title="Distance to take-profit as a percent, e.g. 1.2 = 1.2%">
              <span class="field-help">Favorable distance from fill price. Long targets are above entry; short targets are below entry.</span>
            </label>
            <label class="rail-field">Maintenance margin (% of notional)
              <input name="maintenance_margin_rate" type="number" step="0.05" value="0.4" title="Maintenance margin rate, e.g. 0.4 = 0.4%">
              <span class="field-help">Futures liquidation approximation. Higher maintenance moves liquidation closer. Spot ignores liquidation entirely.</span>
            </label>
          </fieldset>

          <fieldset class="config-family family-ut" data-backtest-ut-only hidden>
            <legend>UT Bot Alerts</legend>
            <p class="field-help" style="margin:0">These mirror the Pine-style UT Bot inputs. Heikin Ashi closes are synthesized from stored OHLC, percent values use the same style as stop/take-profit, and session times are UTC.</p>
            <label class="rail-field">UT key value (× ATR)
              <input name="ut_key_value" type="number" step="0.1" value="2" title="Multiplier applied to ATR to build the UT trailing stop. Higher = wider/fewer signals; lower = tighter/more signals.">
              <span class="field-help">ATR multiplier for the trailing stop. Higher values reduce signals but may enter later; lower values react faster and can overtrade chop.</span>
            </label>
            <div class="rail-row">
              <label class="rail-field">UT ATR period
                <input name="ut_atr_period" type="number" step="1" min="1" value="7" title="Number of candles used to calculate ATR volatility. Larger = smoother; smaller = faster.">
                <span class="field-help">Volatility lookback for ATR. Larger is smoother; smaller responds faster.</span>
              </label>
              <label class="rail-field">UT LinReg period
                <input name="ut_lr_period" type="number" step="1" min="2" value="20" title="Number of candles for the linear-regression baseline used by timed exits.">
                <span class="field-help">Linear regression baseline used by timed exit checks.</span>
              </label>
            </div>
            <div class="rail-row">
              <label class="rail-field">UT exit deviation (%)
                <input name="ut_exit_pct" type="number" step="0.1" value="0.6" title="Percent distance from the LinReg baseline required for a timed exit. Example: 0.6 = 0.60%.">
                <span class="field-help">Distance from the LinReg baseline needed for a timed exit. Example: 0.6 means 0.60%.</span>
              </label>
              <label class="rail-field">UT exit delay (bars)
                <input name="ut_exit_delay" type="number" step="1" min="1" value="1" title="How many candles to wait before applying a timed UT exit after the condition appears.">
                <span class="field-help">Confirmation delay before timed UT exits can close a position.</span>
              </label>
            </div>
            <label class="rail-field">UT cooldown (minutes)
              <input name="ut_cooldown_minutes" type="number" step="1" min="1" value="5" title="Minimum time after any UT signal before another UT signal can fire, when cooldown is enabled.">
              <span class="field-help">Minimum quiet time after a UT signal before another UT signal may fire.</span>
            </label>
            <label class="rail-field">UT disable session (UTC HHMM-HHMM)
              <input name="ut_disable_session" value="2200-0500" title="UTC time window where UT signals are blocked when enabled. Example spans UTC 22:00 through 05:00 next day.">
              <span class="field-help">UTC window where UT signals are blocked when the time filter is on. Cross-midnight windows like 2200-0500 are supported.</span>
            </label>
            <label class="check-label rail-check">
              <input name="ut_use_heikin_ashi" type="checkbox" value="true" title="Use synthetic Heikin Ashi closes for UT calculations. This can smooth signals but differs from raw candle closes.">
              <span>Signals from Heikin Ashi closes.<br><span class="field-help">Smooths inputs with locally computed HA closes; it is not a separate exchange feed.</span></span>
            </label>
            <label class="check-label rail-check">
              <input name="ut_enable_exit_signals" type="checkbox" value="true" checked title="Allow LinReg timed exits in addition to opposite UT signals, stop loss, take profit, and liquidation.">
              <span>Enable UT timed exits vs LinReg bands.<br><span class="field-help">Adds indicator-style exit logic alongside stop loss, take profit, liquidation, and opposing UT signals.</span></span>
            </label>
            <label class="check-label rail-check">
              <input name="ut_enable_time_filter" type="checkbox" value="true" title="Block UT entries and exits inside the disable session. Leave off to trade every candle.">
              <span>Disable entries/exits inside UTC session.<br><span class="field-help">Blocks UT signals during the configured UTC window.</span></span>
            </label>
            <label class="check-label rail-check">
              <input name="ut_enable_cooldown" type="checkbox" value="true" title="Turn on a waiting period after any UT signal to reduce repeated signals during choppy moves.">
              <span>Enable signal cooldown.<br><span class="field-help">Reduces repeated signals during choppy conditions by waiting after each UT signal.</span></span>
            </label>
          </fieldset>

          <div class="rail-actions">
            <button class="action" id="run-backtest" type="submit">Run backtest</button>
            <button class="action secondary" id="copy-config" type="button">Copy config</button>
            <button class="action secondary" id="export-trades" type="button">Export trades CSV</button>
          </div>
        </form>
        <div id="backtest-status" class="status" style="padding:0 12px 12px"></div>
      </section>

      <div class="backtest-results">

    <section class="panel" data-tab-panel="backtest">
      <h2>Performance Snapshot</h2>
      <div class="summary-grid" id="bt-metrics">
        <div class="metric"><span>Net PnL</span><strong id="bt-net">-</strong></div>
        <div class="metric"><span>Total Return</span><strong id="bt-return">-</strong></div>
        <div class="metric metric--pre" title="Calendar span from first to last equity point, bar count, and stored candle UTC dates.">
          <span>Backtest span</span><strong id="bt-duration">-</strong>
        </div>
        <div class="metric"><span>Annualized</span><strong id="bt-annual">-</strong></div>
        <div class="metric"><span>Max Drawdown</span><strong id="bt-dd">-</strong></div>
        <div class="metric"><span>Sharpe</span><strong id="bt-sharpe">-</strong></div>
        <div class="metric"><span>Sortino</span><strong id="bt-sortino">-</strong></div>
        <div class="metric"><span>Calmar</span><strong id="bt-calmar">-</strong></div>
        <div class="metric"><span>Profit Factor</span><strong id="bt-pf">-</strong></div>
        <div class="metric"><span>Win Rate</span><strong id="bt-win">-</strong></div>
        <div class="metric"><span>Payoff</span><strong id="bt-payoff">-</strong></div>
        <div class="metric"><span>Expectancy</span><strong id="bt-exp">-</strong></div>
        <div class="metric"><span>Trades</span><strong id="bt-trades">-</strong></div>
        <div class="metric"><span>Long / Short</span><strong id="bt-sides">-</strong></div>
        <div class="metric"><span>Avg Bars Held</span><strong id="bt-bars">-</strong></div>
        <div class="metric"><span>Max Win Streak</span><strong id="bt-winstreak">-</strong></div>
        <div class="metric"><span>Max Loss Streak</span><strong id="bt-lossstreak">-</strong></div>
        <div class="metric"><span>Best Trade</span><strong id="bt-best">-</strong></div>
        <div class="metric"><span>Worst Trade</span><strong id="bt-worst">-</strong></div>
        <div class="metric"><span>Total Fees</span><strong id="bt-fees">-</strong></div>
        <div class="metric"><span>Total Funding</span><strong id="bt-funding">-</strong></div>
        <div class="metric"><span>PnL R²</span><strong id="bt-r2">-</strong></div>
        <div class="metric"><span>DD Bars</span><strong id="bt-ddbars">-</strong></div>
        <div class="metric"><span>Final Balance</span><strong id="bt-final">-</strong></div>
      </div>
    </section>

    <section class="panel estimator-panel" data-tab-panel="backtest">
      <h2>Gain estimator</h2>
      <p class="muted estimator-disclaimer">
        Projection uses one <strong>continuous equity CAGR</strong> over the chart&rsquo;s elapsed wall-clock time (same start/end timestamps as Duration), converted to an equivalent monthly factor.
        This does <strong>not</strong> extrapolate from per-bar/per-hour sampling density or from calendar-month buckets (those can distort partial months vs full months).
        You can apply a drawdown haircut to temper optimistic drift before compounding forward.
      </p>
      <div class="form-grid" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));max-width:940px">
        <label><span class="field-title">Total wallet ($)<span class="help-tip" tabindex="0" data-tip="Capital you actually trade with. Dollar balance and PnL in the projection are scaled from the backtest&rsquo;s initial balance toward this wallet; percentage return paths stay the same. Leave blank to match the run&rsquo;s initial balance.">?</span></span>
          <input id="gain-wallet" type="number" step="100" min="0" placeholder="Use initial balance" autocomplete="off">
        </label>
        <label>Horizon
          <select id="gain-horizon">
            <option value="3">3 months</option>
            <option value="6">6 months</option>
            <option value="12" selected>1 year</option>
            <option value="24">2 years</option>
            <option value="36">3 years</option>
          </select>
        </label>
        <label><span class="field-title">Max drawdown stress<span class="help-tip" tabindex="0" data-tip="Shrinks positive monthly drift using the observed max drawdown. None = geometric mean only. Larger stress means more pessimism (smaller compounded edge). Worst-case paths are never softened.">?</span></span>
          <select id="gain-dd-stress">
            <option value="0">None — clock-true monthly drift only</option>
            <option value="0.5">Mild — drift × max(0, 1 − ½×historical DD)</option>
            <option value="1" selected>Moderate — drift × max(0, 1 − historical DD)</option>
            <option value="1.5">Strong — drift × max(0, 1 − 1.5×historical DD)</option>
          </select>
        </label>
      </div>
      <div id="gain-estimator-body" class="muted" style="margin-top:10px;line-height:1.45;font-size:13px">
        Run a backtest to populate the gain estimator.
      </div>
    </section>

    <div class="charts-grid" data-tab-panel="backtest">
      <div class="chart-card">
        <h2>Price &amp; Trades</h2>
        <canvas id="bt-price-chart" class="tall" width="1100" height="320"></canvas>
      </div>
      <div class="chart-card">
        <h2>Equity Curve</h2>
        <canvas id="bt-equity-chart" class="tall" width="600" height="320"></canvas>
      </div>
    </div>

    <div class="secondary-grid" data-tab-panel="backtest">
      <div class="chart-card">
        <h2>Drawdown</h2>
        <canvas id="bt-drawdown-chart" width="500" height="220"></canvas>
      </div>
      <div class="chart-card">
        <h2>Trade PnL Distribution</h2>
        <canvas id="bt-pnldist-chart" width="500" height="220"></canvas>
      </div>
      <div class="chart-card">
        <h2>Monthly Returns</h2>
        <canvas id="bt-monthly-chart" width="500" height="220"></canvas>
      </div>
    </div>

    <section class="panel" data-tab-panel="backtest">
      <h2>Exit Reason Mix</h2>
      <div id="bt-exit-reasons" class="muted">Run a backtest to see how positions closed.</div>
    </section>

    <section class="panel" data-tab-panel="backtest">
      <h2>Trade Log</h2>
      <div class="table-wrap">
        <table id="bt-trades">
          <thead>
            <tr>
              <th>#</th>
              <th>Side</th>
              <th>Entry Time</th>
              <th>Exit Time</th>
              <th>Bars</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Qty</th>
              <th>Margin</th>
              <th>Net PnL</th>
              <th>Return %</th>
              <th>Fees</th>
              <th>Funding</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody id="bt-trades-body">
            <tr><td colspan="14" class="muted">Run a backtest to populate the trade log.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
      </div>
    </div>

    <!-- OPTIMIZER TAB -->
    <div class="optimizer-dashboard" data-tab-panel="optimizer" hidden>
    <section class="panel optimizer-config-rail">
      <div class="rail-header">
        <h2>Grid Optimizer Setup</h2>
        <p>Configure market data, sizing, costs, strategy grids, and run controls here. Results, filters, charts, and the ranked table stay on the right.</p>
      </div>
      <form id="optimizer-form" lang="en" class="rail-form">
        <div class="form-grid optimizer-layout">
          <div class="optimizer-guide">
            <strong>How percentages work here</strong>
            <ul>
              <li><strong>Position size</strong> is % of account balance (e.g. <code>25</code> = 25% of balance used as margin on futures or notional on spot).</li>
              <li><strong>Fee</strong> and <strong>funding rate</strong> are % of notional per fee event / per funding interval (e.g. <code>0.05</code> fee = 0.05% of notional each side).</li>
              <li><strong>Grids below</strong> use the same idea: <code>0.4</code> in a grid means a <strong>0.40%</strong> price move for that parameter. Lists use commas; ranges use <code>min:max:step</code> (all in %).</li>
              <li><strong>Slippage / spread</strong> are in <strong>basis points (bps)</strong> — 1 bps = 0.01% of price — not the same as the % fields above.</li>
            </ul>
            <p class="muted" style="margin:10px 0 0 0;font-size:12px">Values are converted automatically for the engine. Results columns <strong>Drop / Rise / TP / SL</strong> show the same % style.</p>
          </div>
          <label class="wide">Database
            <input name="db_path" value="__DEFAULT_DB__">
          </label>
          <label>Exchange
            <input name="exchange" value="binance">
          </label>
          <label>Symbol
            <input name="symbol" value="BTCUSDT">
          </label>
          <label>Market
            <select name="market_type">
              <option value="futures" selected>Futures</option>
              <option value="spot">Spot</option>
            </select>
          </label>
          <label>Timeframe
            <select name="timeframe">
              <option value="1h" selected>1h</option>
              <option value="4h">4h</option>
              <option value="8h">8h</option>
              <option value="12h">12h</option>
            </select>
          </label>

          <label class="wide">Optimizer core strategy
            <select name="optimizer_strategy" id="opt-strategy-select">
              <option value="threshold" selected>Threshold (percent grids)</option>
              <option value="ut_bot">UT Bot Alerts (indicator parity)</option>
            </select>
          </label>

          <label>Initial Balance
            <input name="initial_balance" type="number" step="100" value="10000">
          </label>
          <label>Position size (% of balance)
            <input name="position_size_pct" type="number" step="1" min="0" max="100" value="25" title="Percent of balance used as margin (futures) or notional (spot), e.g. 25 = 25%">
          </label>
          <label>Stake ($)
            <input name="stake_usd" type="number" step="100" value="2500">
          </label>
          <div class="wide toggle-row">
            <label class="check-label" style="min-height:auto">
              <input name="ignore_position_size_pct" type="checkbox" value="true">
              Use fixed $ stake (ignore %)
            </label>
            <label class="check-label" style="min-height:auto">
              <input name="ignore_funding" type="checkbox" value="true">
              Ignore funding
            </label>
          </div>
          <label>Leverage
            <input name="leverage" type="number" step="0.5" value="5">
          </label>
          <label>Fee (% per notional, each side)
            <input name="fee_rate" type="number" step="0.005" value="0.05" title="Taker-style fee as a percent of notional, e.g. 0.05 = 0.05% per side">
          </label>
          <label>Slippage (basis points)
            <input name="slippage_bps" type="number" step="0.1" value="1.5" title="1 bps = 0.01% of price; typical execution cost model, not a % of balance">
          </label>
          <label>Half-spread (basis points)
            <input name="spread_bps" type="number" step="0.1" value="1.0" title="Modeled as half bid–ask in bps (1 bps = 0.01% of price)">
          </label>
          <label>Funding rate (% per interval)
            <input name="funding_rate_per_interval" type="number" step="0.001" value="0.01" title="Funding accrual per interval, e.g. 0.01 = 0.01%">
          </label>
          <label><span class="field-title">SQLite / Binance lookback (days)<span class="help-tip" tabindex="0" data-tip="Optimizer loads the same SQLite window as Single Backtest. Short files are auto-filled toward this many trailing calendar days when exchange is Binance."></span></span>
            <input name="auto_download_days" type="number" step="1" min="2" max="400" value="90">
          </label>

          <div class="strategy-stack-panel wide">
            <h3>Strategy combination</h3>
            <p class="muted" style="margin:0 0 8px 0;font-size:12px">Core optimizer leg follows <strong>Optimizer core strategy</strong> above (Threshold grids vs UT Bot grids). Optional companions run in parallel; order matters for OR mode.</p>
            <label>Combine signals
              <select name="combine_mode">
                <option value="all" selected>All must agree (AND)</option>
                <option value="any">First fire wins (OR)</option>
              </select>
            </label>
            <label class="check-label" style="margin-top:10px">
              <input name="companion_buy_hold" type="checkbox" value="true">
              Include Buy &amp; Hold companion (reported as buy_and_hold in results)
            </label>
          </div>

          <label class="check-label">
            <input name="allow_short" type="checkbox" value="true">
            Allow Shorts
          </label>

          <div class="grid-builder" data-grid-editor data-opt-threshold-only>
            <div class="grid-builder-head">
              <strong>Entry drop grid (% vs prior close)</strong>
              <p class="grid-builder-explainer">Each trial is a minimum <strong>one-bar drop</strong> from the previous close to this close (long entry signal). Example: <code>0.4</code> means price must fall at least <strong>0.40%</strong> in that bar.</p>
              <span class="grid-builder-syntax">Use <strong>Min</strong>, <strong>Max</strong>, and <strong>Step</strong> (variability) for sweeps; the line below is what the server reads (auto-filled from the three boxes, or type a comma list).</span>
            </div>
            <div class="grid-builder-controls grid-builder-compact-row">
              <label>Min % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-min value="0.2" title="Range minimum in %"></label>
              <label>Max % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-max value="0.8" title="Range maximum in %"></label>
              <label>Step % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-step value="0.2" title="Step between trials (variability)"></label>
              <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
            </div>
            <div class="grid-sent-wrap">
              <span class="muted grid-sent-hint">Grid string sent to server</span>
              <input class="grid-main-input grid-main-input--sent" name="entry_drop_grid" data-grid-main value="0.2:0.8:0.2" title="Percent moves; 0.2:0.8:0.2 = try 0.2%, 0.4%, … 0.8%">
            </div>
            <div class="grid-presets">
              <span>Presets</span>
              <button type="button" class="chip" data-grid-preset="0.2,0.4,0.6">0.2–0.6%</button>
              <button type="button" class="chip" data-grid-preset="0.2:1.0:0.2">0.2–1.0%</button>
              <button type="button" class="chip" data-grid-preset="0.3,0.5,0.7">0.3–0.7%</button>
            </div>
          </div>

          <div class="grid-builder" data-grid-editor data-opt-threshold-only>
            <div class="grid-builder-head">
              <strong>Entry rise grid (% vs prior close, shorts)</strong>
              <p class="grid-builder-explainer">Used only if <strong>Allow shorts</strong> is on. Same idea as entry drop, but for a minimum <strong>rise</strong> vs the previous close (short entry signal).</p>
              <span class="grid-builder-syntax">Min / Max / Step in %, then optional comma list in the string field.</span>
            </div>
            <div class="grid-builder-controls grid-builder-compact-row">
              <label>Min % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-min value="0.2"></label>
              <label>Max % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-max value="0.8"></label>
              <label>Step % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-step value="0.2" title="Variability between trials"></label>
              <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
            </div>
            <div class="grid-sent-wrap">
              <span class="muted grid-sent-hint">Grid string sent to server</span>
              <input class="grid-main-input grid-main-input--sent" name="entry_rise_grid" data-grid-main value="0.2:0.8:0.2" title="Percent moves for short threshold grid">
            </div>
            <div class="grid-presets">
              <span>Presets</span>
              <button type="button" class="chip" data-grid-preset="0.2,0.4,0.6">0.2–0.6%</button>
              <button type="button" class="chip" data-grid-preset="0.3:0.9:0.3">0.3–0.9%</button>
            </div>
          </div>

          <div class="grid-builder" data-opt-shared-grid data-grid-editor>
            <div class="grid-builder-head">
              <strong>Take profit grid (% from entry)</strong>
              <p class="grid-builder-explainer">Distance from <strong>fill price to take-profit</strong> for each trial. <code>1.2</code> means exit target is <strong>1.20%</strong> in your favor from entry (same units as the backtest &ldquo;Take profit %&rdquo; field).</p>
              <span class="grid-builder-syntax">Min / Max / Step in % for TP distance; string field for comma lists.</span>
            </div>
            <div class="grid-builder-controls grid-builder-compact-row">
              <label>Min % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-min value="0.6"></label>
              <label>Max % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-max value="1.8"></label>
              <label>Step % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-step value="0.4" title="Variability between TP trials"></label>
              <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
            </div>
            <div class="grid-sent-wrap">
              <span class="muted grid-sent-hint">Grid string sent to server</span>
              <input class="grid-main-input grid-main-input--sent" name="take_profit_grid" data-grid-main value="0.6:1.8:0.4" title="TP distance from entry in %">
            </div>
            <div class="grid-presets">
              <span>Presets</span>
              <button type="button" class="chip" data-grid-preset="0.6,1.0,1.4">0.6–1.4%</button>
              <button type="button" class="chip" data-grid-preset="0.8:2.0:0.4">0.8–2.0%</button>
              <button type="button" class="chip" data-grid-preset="0.5,0.8,1.2">0.5–1.2%</button>
            </div>
          </div>

          <div class="grid-builder" data-opt-shared-grid data-grid-editor>
            <div class="grid-builder-head">
              <strong>Stop loss grid (% from entry)</strong>
              <p class="grid-builder-explainer">Maximum adverse move from entry before the engine closes the trade as a stop. <code>0.8</code> = stop <strong>0.80%</strong> away from entry (same units as backtest &ldquo;Stop loss %&rdquo;).</p>
              <span class="grid-builder-syntax">Min / Max / Step in % for stop distance; string field for comma lists.</span>
            </div>
            <div class="grid-builder-controls grid-builder-compact-row">
              <label>Min % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-min value="0.4"></label>
              <label>Max % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-max value="1.0"></label>
              <label>Step % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-step value="0.2" title="Variability between SL trials"></label>
              <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
            </div>
            <div class="grid-sent-wrap">
              <span class="muted grid-sent-hint">Grid string sent to server</span>
              <input class="grid-main-input grid-main-input--sent" name="stop_loss_grid" data-grid-main value="0.4:1.0:0.2" title="Stop distance from entry in %">
            </div>
            <div class="grid-presets">
              <span>Presets</span>
              <button type="button" class="chip" data-grid-preset="0.4,0.6,0.8">0.4–0.8%</button>
              <button type="button" class="chip" data-grid-preset="0.4:1.2:0.2">0.4–1.2%</button>
              <button type="button" class="chip" data-grid-preset="0.5,0.7,0.9">0.5–0.9%</button>
            </div>
          </div>

          <div class="wide optimizer-layout" data-opt-ut-only hidden>
            <div class="grid-builder" data-grid-editor>
              <div class="grid-builder-head">
                <strong>UT key value grid (multiplier × ATR)</strong>
                <p class="grid-builder-explainer">Matches Pine &ldquo;Key Value&rdquo;. Whole numbers work best.</p>
                <span class="grid-builder-syntax">Min / Max / Step, then string sent to server.</span>
              </div>
              <div class="grid-builder-controls grid-builder-compact-row">
                <label>Min <input class="grid-num-input" type="number" inputmode="decimal" step="0.5" data-grid-min value="2"></label>
                <label>Max <input class="grid-num-input" type="number" inputmode="decimal" step="0.5" data-grid-max value="4"></label>
                <label>Step <input class="grid-num-input" type="number" inputmode="decimal" step="0.5" data-grid-step value="1" title="Variability"></label>
                <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
              </div>
              <div class="grid-sent-wrap">
                <span class="muted grid-sent-hint">Grid string sent to server</span>
                <input class="grid-main-input grid-main-input--sent" name="ut_key_grid" data-grid-main value="2">
              </div>
              <div class="grid-presets">
                <span>Presets</span>
                <button type="button" class="chip" data-grid-preset="2,3">2–3</button>
                <button type="button" class="chip" data-grid-preset="2:4:1">2–4 step 1</button>
              </div>
            </div>

            <div class="grid-builder" data-grid-editor>
              <div class="grid-builder-head">
                <strong>UT ATR period grid</strong>
              </div>
              <div class="grid-builder-controls grid-builder-compact-row">
                <label>Min <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-min value="7"></label>
                <label>Max <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-max value="14"></label>
                <label>Step <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-step value="7" title="Variability"></label>
                <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
              </div>
              <div class="grid-sent-wrap">
                <span class="muted grid-sent-hint">Grid string sent to server</span>
                <input class="grid-main-input grid-main-input--sent" name="ut_atr_period_grid" data-grid-main value="7">
              </div>
              <div class="grid-presets">
                <span>Presets</span>
                <button type="button" class="chip" data-grid-preset="7">7</button>
                <button type="button" class="chip" data-grid-preset="7,10,14">7–14</button>
              </div>
            </div>

            <div class="grid-builder" data-grid-editor>
              <div class="grid-builder-head">
                <strong>UT LinReg period grid</strong>
              </div>
              <div class="grid-builder-controls grid-builder-compact-row">
                <label>Min <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-min value="20"></label>
                <label>Max <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-max value="40"></label>
                <label>Step <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-step value="10" title="Variability"></label>
                <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
              </div>
              <div class="grid-sent-wrap">
                <span class="muted grid-sent-hint">Grid string sent to server</span>
                <input class="grid-main-input grid-main-input--sent" name="ut_lr_period_grid" data-grid-main value="20">
              </div>
              <div class="grid-presets">
                <span>Presets</span>
                <button type="button" class="chip" data-grid-preset="20">20</button>
                <button type="button" class="chip" data-grid-preset="14,20,30">14–30</button>
              </div>
            </div>

            <div class="grid-builder" data-grid-editor>
              <div class="grid-builder-head">
                <strong>UT exit deviation grid (% vs LinReg mid)</strong>
                <span class="grid-builder-syntax">Percent points; Min / Max / Step + string field.</span>
              </div>
              <div class="grid-builder-controls grid-builder-compact-row">
                <label>Min % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-min value="0.4"></label>
                <label>Max % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-max value="0.8"></label>
                <label>Step % <input class="grid-num-input" type="number" inputmode="decimal" step="0.05" data-grid-step value="0.2" title="Variability"></label>
                <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
              </div>
              <div class="grid-sent-wrap">
                <span class="muted grid-sent-hint">Grid string sent to server</span>
                <input class="grid-main-input grid-main-input--sent" name="ut_exit_pct_grid" data-grid-main value="0.4:0.8:0.2">
              </div>
              <div class="grid-presets">
                <span>Presets</span>
                <button type="button" class="chip" data-grid-preset="0.4,0.6,0.8">0.4–0.8%</button>
              </div>
            </div>

            <div class="grid-builder" data-grid-editor>
              <div class="grid-builder-head">
                <strong>UT exit delay grid (bars)</strong>
              </div>
              <div class="grid-builder-controls grid-builder-compact-row">
                <label>Min <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-min value="1"></label>
                <label>Max <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-max value="3"></label>
                <label>Step <input class="grid-num-input" type="number" inputmode="numeric" step="1" data-grid-step value="1" title="Variability"></label>
                <button type="button" class="action secondary" data-grid-apply-range>Apply range</button>
              </div>
              <div class="grid-sent-wrap">
                <span class="muted grid-sent-hint">Grid string sent to server</span>
                <input class="grid-main-input grid-main-input--sent" name="ut_exit_delay_grid" data-grid-main value="1">
              </div>
              <div class="grid-presets">
                <span>Presets</span>
                <button type="button" class="chip" data-grid-preset="1">1</button>
                <button type="button" class="chip" data-grid-preset="1,2,3">1–3</button>
              </div>
            </div>

            <div class="strategy-stack-panel wide">
              <h3>UT Bot execution filters</h3>
              <p class="muted" style="margin:0 0 8px 0;font-size:12px">These mirror the Pine inputs and apply to every UT optimization trial.</p>
              <div class="toggle-row">
                <label class="check-label">
                  <input name="ut_use_heikin_ashi" type="checkbox" value="true">
                  Heikin Ashi closes (computed locally)
                </label>
                <label class="check-label">
                  <input name="ut_enable_exit_signals" type="checkbox" value="true" checked>
                  Enable timed exits vs LinReg bands
                </label>
                <label class="check-label">
                  <input name="ut_enable_time_filter" type="checkbox" value="true">
                  Disable signals inside UTC session window
                </label>
                <label class="check-label">
                  <input name="ut_enable_cooldown" type="checkbox" value="true">
                  Enable cooldown after UT signals
                </label>
              </div>
              <div class="form-grid" style="margin-top:10px">
                <label class="wide">UTC disable session (HHMM-HHMM)
                  <input name="ut_disable_session" value="2200-0500">
                </label>
                <label>Cooldown minutes
                  <input name="ut_cooldown_minutes" type="number" min="1" step="1" value="5">
                </label>
              </div>
            </div>
          </div>

          <div class="wide" id="opt-form-leg-preview-wrap">
            <h3 style="font-size:13px;margin:16px 0 8px 0">Per-strategy parameters (from form)</h3>
            <p class="muted" style="font-size:12px;margin:0 0 8px 0">Live summary in plain language. Grid lines show your <strong>% inputs</strong> read back as labeled percents; the server still runs on fractional math. After a run, click a results row to push that combo into the Backtest tab.</p>
            <div id="opt-form-leg-preview" class="leg-cards"></div>
            <div class="actions opt-form-actions">
              <button class="action" id="run-optimizer" type="submit">Run optimizer</button>
              <button class="action secondary" id="export-opt-csv" type="button">Export filtered CSV</button>
            </div>
          </div>
        </div>
      </form>
      <div id="opt-status" class="status"></div>
    </section>

    <div class="optimizer-results">
    <section class="panel" data-tab-panel="optimizer" hidden>
      <h2>Best Combinations</h2>
      <div class="summary-grid">
        <div class="metric"><span>Best Final</span><strong id="opt-best-final">-</strong></div>
        <div class="metric"><span>Best Return</span><strong id="opt-best-return">-</strong></div>
        <div class="metric"><span>Best Sharpe</span><strong id="opt-best-sharpe">-</strong></div>
        <div class="metric"><span>Best Sortino</span><strong id="opt-best-sortino">-</strong></div>
        <div class="metric"><span>Best Calmar</span><strong id="opt-best-calmar">-</strong></div>
        <div class="metric"><span>Best PnL R²</span><strong id="opt-best-r2">-</strong></div>
        <div class="metric"><span>Rows Shown</span><strong id="opt-rows-shown">-</strong></div>
        <div class="metric"><span>Total Combinations</span><strong id="opt-rows-total">-</strong></div>
      </div>
    </section>

    <div class="charts-grid" data-tab-panel="optimizer" hidden>
      <div class="chart-card">
        <h2>Parameter heatmap (mean total return %)</h2>
        <canvas id="opt-heatmap" class="tall" width="1100" height="320"></canvas>
      </div>
      <div class="chart-card">
        <h2>Sharpe vs total return (each point = one grid combo; return axis in %)</h2>
        <canvas id="opt-scatter" class="tall" width="600" height="320"></canvas>
      </div>
    </div>

    <section class="panel" data-tab-panel="optimizer" hidden>
      <h2>Filters</h2>
      <p class="muted" style="font-size:12px;margin:-4px 0 12px 0">All <strong>%</strong> thresholds here match the metrics table (e.g. min return <code>10</code> means at least <strong>+10%</strong> total return; max drawdown <code>30</code> means at most <strong>30%</strong> peak-to-trough equity drawdown).</p>
      <div class="filter-grid">
        <label>Min return (%)
          <input id="f-min-return" type="number" step="0.1" placeholder="-100">
        </label>
        <label>Max drawdown (%)
          <input id="f-max-drawdown" type="number" step="0.1" placeholder="100">
        </label>
        <label>Min Sharpe
          <input id="f-min-sharpe" type="number" step="0.01" placeholder="-10">
        </label>
        <label>Min Sortino
          <input id="f-min-sortino" type="number" step="0.01" placeholder="-10">
        </label>
        <label>Min Calmar
          <input id="f-min-calmar" type="number" step="0.01" placeholder="0">
        </label>
        <label>Min PnL R²
          <input id="f-min-r2" type="number" step="0.01" placeholder="0">
        </label>
        <label>Min win rate (%)
          <input id="f-min-win" type="number" step="0.1" placeholder="0">
        </label>
        <label>Min Trades
          <input id="f-min-trades" type="number" step="1" placeholder="0">
        </label>
        <label>Sort By
          <select id="f-sort">
            <option value="final_balance">Final balance</option>
            <option value="total_return_pct">Return %</option>
            <option value="annualized_return_pct">Annualized %</option>
            <option value="sharpe_ratio">Sharpe</option>
            <option value="sortino_ratio">Sortino</option>
            <option value="calmar_ratio">Calmar</option>
            <option value="pnl_r_squared">PnL R²</option>
            <option value="max_drawdown_pct">Drawdown</option>
            <option value="trade_count">Trades</option>
            <option value="win_rate_pct">Win rate</option>
            <option value="profit_factor">Profit factor</option>
          </select>
        </label>
        <label>Direction
          <select id="f-dir">
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </label>
      </div>
      <div class="filter-actions">
        <button class="action secondary" id="reset-filters" type="button">Reset filters</button>
        <button class="action secondary" id="load-best-into-backtest" type="button">Load best row into Backtest</button>
      </div>
    </section>

    <section class="panel strategy-ref" data-tab-panel="optimizer" hidden>
      <h2>Strategy reference</h2>
      <p class="muted" style="font-size:13px;margin-top:0">Each leg emits <strong>signals</strong> (enter long, enter short, hold, exit). The combine mode decides how multiple legs agree. Below: how a <strong>buy (long)</strong> can appear; shorts use the mirrored rule where noted.</p>

      <details open>
        <summary>Threshold</summary>
        <p style="font-size:13px;line-height:1.5">Compares this candle&rsquo;s <strong>close</strong> to the <strong>previous candle&rsquo;s close</strong>. Only acts when you are flat (no open position). In the dashboard, <strong>entry drop / rise</strong> are entered as everyday percents (e.g. <strong>0.4</strong> = 0.40% move); the server still stores them as fractions internally.</p>
        <ul style="font-size:13px;line-height:1.45">
          <li><strong>Long signal:</strong> one-bar drop from previous close by at least <code>entry_drop_pct</code> (sell-off bounce idea).</li>
          <li><strong>Short signal</strong> (if allowed): one-bar <strong>rise</strong> from previous close by at least <code>entry_rise_pct</code>.</li>
        </ul>
        <div class="ex-buy">
          <strong>Buy (long) example.</strong> Previous candle closed at $100,000. This candle closes at $99,600. Change = &minus;0.4%. If the form field <strong>Entry drop</strong> is <strong>0.4</strong> (meaning 0.40%), the drop is large enough: the strategy signals <em>enter long</em> for the next execution step (subject to combine mode if other legs are stacked).
        </div>
      </details>

      <details>
        <summary>Buy &amp; Hold</summary>
        <p style="font-size:13px;line-height:1.5">No percentage grids. On the <strong>first bar</strong> of the series (index 0), if there is no position, it signals <em>enter long</em> once.</p>
        <div class="ex-buy">
          <strong>Buy example.</strong> Backtest starts at the first downloaded candle. You start flat, so on bar 0 the leg requests a long entry at that bar&rsquo;s open (after spread/slippage in the engine). All later bars return <em>hold</em> for this leg.
        </div>
      </details>

      <details>
        <summary>UT Bot Alerts</summary>
        <p style="font-size:13px;line-height:1.5">Matches the Pine indicator supplied with this repo: ATR trailing stop + buffered UT entries, persistent bias state, LinReg band exits, optional session/cooldown filters, and optional Heikin Ashi closes computed from stored OHLC (no separate HA feed).</p>
        <ul style="font-size:13px;line-height:1.45">
          <li><strong>Entries:</strong> long on filtered buy buffer; short entries respect dashboard &ldquo;Allow shorts&rdquo;.</li>
          <li><strong>Exits:</strong> UT timed exits mirror Pine delays; opposing UT buffers flatten positions on the next signal.</li>
          <li><strong>Risk overlays:</strong> stop-loss / take-profit grids still apply via the execution engine.</li>
        </ul>
      </details>

      <p class="muted" style="font-size:12px;margin-bottom:0">Adding a new strategy in code: implement <code>on_candle</code>, register it in the server&rsquo;s companion factory, and document it here the same way.</p>
      </section>

    <section class="panel" data-tab-panel="optimizer" hidden>
      <h2>Optimizer Results (click a row to load it in the Backtest tab)</h2>
      <div class="table-wrap">
        <table id="opt-results">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Stack</th>
              <th>Mode</th>
              <th>Shorts</th>
              <th title="Min one-bar drop vs prior close (%)">Drop %</th>
              <th title="Min one-bar rise vs prior close for shorts (%)">Rise %</th>
              <th title="Take-profit distance from entry (%)">TP %</th>
              <th title="Stop distance from entry (%)">SL %</th>
              <th title="UT sensitivity key">UT Key</th>
              <th title="UT ATR period">UT ATR</th>
              <th title="UT LinReg period">UT LR</th>
              <th title="UT exit deviation vs LinReg (%)">UT Exit %</th>
              <th title="UT exit confirmation bars">UTDly</th>
              <th>Final</th>
              <th>Net PnL</th>
              <th>Return %</th>
              <th>Annualized</th>
              <th>Sharpe</th>
              <th>Sortino</th>
              <th>Calmar</th>
              <th>R²</th>
              <th>Max DD</th>
              <th>DD Bars</th>
              <th>Win %</th>
              <th>PF</th>
              <th>Payoff</th>
              <th>Expectancy</th>
              <th>Avg Bars</th>
              <th>Win Strk</th>
              <th>Loss Strk</th>
              <th>Trades</th>
            </tr>
          </thead>
          <tbody id="opt-results-body">
            <tr><td colspan="31" class="muted">Run the optimizer to populate results.</td></tr>
          </tbody>
        </table>
      </div>
      <div id="opt-row-legs-detail">
        <h3 style="font-size:13px;margin:16px 0 8px 0">Selected row — parameters by strategy</h3>
        <p class="muted" style="font-size:12px;margin:0 0 10px 0">Click any results row to load the backtest and see the exact parameter block for each leg in that combination.</p>
        <div id="opt-row-legs-body" class="leg-cards muted">No row selected yet.</div>
      </div>
    </section>
    </div>
    </div>

    <!-- DATA TAB -->
    <section class="panel" data-tab-panel="data" hidden>
      <h2>Stored Candle Inventory</h2>
      <form id="inventory-form" class="form-grid compact">
        <label>Database
          <input name="db_path" value="__DEFAULT_DB__">
        </label>
        <label>Exchange
          <input name="exchange" value="binance">
        </label>
        <label>Symbol
          <input name="symbol" value="BTCUSDT">
        </label>
        <label>Market
          <select name="market_type">
            <option value="futures" selected>Futures</option>
            <option value="spot">Spot</option>
          </select>
        </label>
        <div class="actions">
          <button class="action" id="refresh-data" type="submit">Refresh</button>
        </div>
      </form>
      <div class="table-wrap" style="margin-top:12px">
        <table id="data-inventory">
          <thead>
            <tr>
              <th>Timeframe</th>
              <th>Candles</th>
              <th>First Candle</th>
              <th>Last Candle</th>
            </tr>
          </thead>
          <tbody id="data-inventory-body">
            <tr><td colspan="4" class="muted">Refresh to load inventory.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel" data-tab-panel="data" hidden>
      <h2>Download Real Binance Candles</h2>
      <form id="download-form" class="form-grid compact">
        <label>Symbol
          <input name="symbol" value="BTCUSDT">
        </label>
        <label>Market
          <select name="market_type">
            <option value="futures" selected>Futures</option>
            <option value="spot">Spot</option>
          </select>
        </label>
        <label>Days
          <input name="days" type="number" step="1" value="90" min="1">
        </label>
        <label>Timeframes
          <input name="timeframes" value="1h,4h,8h,12h">
        </label>
        <div class="actions">
          <button class="action" id="run-download" type="submit">Download</button>
          <button class="action secondary" id="run-sample" type="button">Generate sample data</button>
        </div>
      </form>
      <div id="download-status" class="status"></div>
    </section>

    <section class="panel" data-tab-panel="data" hidden>
      <h2>Funding Rate History (Binance USD-M)</h2>
      <form id="funding-form" class="form-grid compact">
        <label>Symbol
          <input name="symbol" value="BTCUSDT">
        </label>
        <label>Days
          <input name="days" type="number" step="1" value="90" min="1">
        </label>
        <div class="actions">
          <button class="action" id="run-funding" type="submit">Fetch funding</button>
        </div>
      </form>
      <div id="funding-summary" class="muted" style="margin-top:12px"></div>
      <div class="chart-card" style="margin-top:12px">
        <canvas id="funding-chart" class="short" width="1100" height="200"></canvas>
      </div>
    </section>
  </main>

  <script>
    /* ===== Tab navigation ===== */
    const tabs = document.querySelectorAll("nav.tabs button");
    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabs.forEach((b) => b.classList.toggle("active", b === btn));
        const tabName = btn.dataset.tab;
        document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
          panel.hidden = panel.dataset.tabPanel !== tabName;
        });
        if (tabName === "data") refreshInventory();
      });
    });

    /* ===== Helpers ===== */
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    function setStatus(elementId, message, isError = false) {
      const el = document.getElementById(elementId);
      if (!el) return;
      el.textContent = message || "";
      el.classList.toggle("error", isError);
    }

    function setHeaderStatus(message) {
      const el = document.getElementById("header-status");
      if (el) el.textContent = message || "";
    }

    function readForm(form) {
      const data = Object.fromEntries(new FormData(form).entries());
      form.querySelectorAll("input[type='checkbox'][name]").forEach((cb) => {
        data[cb.name] = cb.checked;
      });
      return data;
    }

    const TRADING_FORM_PERCENT_SCALE_FIELDS = new Set([
      "stop_loss_pct",
      "take_profit_pct",
      "entry_drop_pct",
      "entry_rise_pct",
      "maintenance_margin_rate",
      "funding_rate_per_interval",
      "fee_rate",
      "ut_exit_pct",
    ]);

    function scalePercentPointsToFraction(value) {
      if (value === "" || value === undefined || value === null) return value;
      const n = Number(value);
      if (!Number.isFinite(n)) return value;
      return n / 100;
    }

    function scaleGridStringPercentToFraction(raw) {
      const s = String(raw ?? "").trim();
      if (!s) return s;
      const scaleToken = (tok) => {
        const n = parseNumLocale(String(tok).trim());
        return Number.isFinite(n) ? String(n / 100) : String(tok).trim();
      };
      if (s.includes(":")) {
        return s.split(":").map(scaleToken).join(":");
      }
      return s.split(",").map(scaleToken).join(",");
    }

    function transformFormDataToApi(data) {
      const out = { ...data };
      TRADING_FORM_PERCENT_SCALE_FIELDS.forEach((key) => {
        if (!(key in out)) return;
        const scaled = scalePercentPointsToFraction(out[key]);
        if (typeof scaled === "number" && Number.isFinite(scaled)) out[key] = scaled;
      });
      if ("position_size_pct" in out && out.position_size_pct !== "" && out.position_size_pct !== undefined) {
        const scaled = scalePercentPointsToFraction(out.position_size_pct);
        if (typeof scaled === "number" && Number.isFinite(scaled)) out.position_size_pct = scaled;
      }
      ["entry_drop_grid", "entry_rise_grid", "take_profit_grid", "stop_loss_grid", "ut_exit_pct_grid"].forEach((key) => {
        if (typeof out[key] === "string" && out[key].trim()) {
          out[key] = scaleGridStringPercentToFraction(out[key]);
        }
      });
      return out;
    }

    function readTradingForm(form) {
      return transformFormDataToApi(readForm(form));
    }

    function toggleBacktestUtPanel() {
      const sel = document.querySelector("#bt-strategy-select");
      const mode = sel ? sel.value : "threshold";
      document.querySelectorAll("[data-backtest-ut-only]").forEach((panel) => {
        panel.hidden = mode !== "ut-bot";
      });
    }

    function toggleOptimizerStrategyPanels() {
      const sel = document.querySelector("#opt-strategy-select");
      const mode = sel ? sel.value : "threshold";
      document.querySelectorAll("[data-opt-threshold-only]").forEach((panel) => {
        panel.hidden = mode !== "threshold";
      });
      document.querySelectorAll("[data-opt-ut-only]").forEach((panel) => {
        panel.hidden = mode !== "ut_bot";
      });
    }

    /** API fraction (e.g. 0.004) → value for percent-point form fields (e.g. "0.4"). */
    function fractionToPercentPointsInput(value) {
      const n = Number(value);
      if (!Number.isFinite(n)) return "";
      const scaled = n * 100;
      if (Number.isInteger(scaled)) return String(scaled);
      return String(+scaled.toFixed(8));
    }

    /** Format a stored fraction as a human percent label (e.g. 0.004 → "0.4%"). */
    function rateAsPercentLabel(frac, maxFractionDigits = 3) {
      const n = Number(frac);
      if (!Number.isFinite(n)) return "-";
      const pct = n * 100;
      return `${pct.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: maxFractionDigits })}%`;
    }

    function parseNumLocale(raw) {
      if (raw === "" || raw === undefined || raw === null) return NaN;
      return Number(String(raw).trim().replace(",", "."));
    }

    function parseGridTripleFromString(raw) {
      const s = String(raw ?? "").trim();
      if (!s.includes(":")) return null;
      const parts = s.split(":").map((p) => p.trim()).filter(Boolean);
      if (parts.length !== 3) return null;
      const nums = parts.map((p) => parseNumLocale(p));
      if (!nums.every(Number.isFinite)) return null;
      const [a, b, st] = nums;
      if (st <= 0 || a > b) return null;
      return { min: a, max: b, step: st };
    }

    function syncRangeFieldsFromMain(root) {
      const main = root.querySelector("[data-grid-main]");
      const minEl = root.querySelector("[data-grid-min]");
      const maxEl = root.querySelector("[data-grid-max]");
      const stepEl = root.querySelector("[data-grid-step]");
      if (!main || !minEl || !maxEl || !stepEl) return;
      const raw = String(main.value ?? "").trim();
      const t = parseGridTripleFromString(raw);
      if (t) {
        minEl.value = t.min;
        maxEl.value = t.max;
        stepEl.value = t.step;
        return;
      }
      if (raw.includes(",")) return;
      const single = parseNumLocale(raw);
      if (Number.isFinite(single)) {
        minEl.value = single;
        maxEl.value = single;
      }
    }

    function applyMainFromRangeFields(root) {
      const main = root.querySelector("[data-grid-main]");
      const minEl = root.querySelector("[data-grid-min]");
      const maxEl = root.querySelector("[data-grid-max]");
      const stepEl = root.querySelector("[data-grid-step]");
      if (!main || !minEl || !maxEl || !stepEl) return;
      const a = parseNumLocale(minEl.value);
      const b = parseNumLocale(maxEl.value);
      const s = parseNumLocale(stepEl.value);
      if (![a, b, s].every(Number.isFinite) || s <= 0 || a > b) return;
      main.value = `${a}:${b}:${s}`;
    }

    function wireGridEditors() {
      document.querySelectorAll("[data-grid-editor]").forEach((root) => {
        const main = root.querySelector("[data-grid-main]");
        const applyBtn = root.querySelector("[data-grid-apply-range]");
        if (!main) return;

        const bumpPreview = () => renderOptimizerFormLegPreview();

        const onRangeTyped = () => {
          applyMainFromRangeFields(root);
          bumpPreview();
        };
        root.querySelectorAll("[data-grid-min],[data-grid-max],[data-grid-step]").forEach((el) => {
          el.addEventListener("input", onRangeTyped);
          el.addEventListener("change", onRangeTyped);
        });

        main.addEventListener("input", bumpPreview);
        main.addEventListener("change", () => {
          syncRangeFieldsFromMain(root);
          bumpPreview();
        });

        syncRangeFieldsFromMain(root);

        if (applyBtn) {
          applyBtn.addEventListener("click", () => {
            applyMainFromRangeFields(root);
            bumpPreview();
          });
        }
        root.querySelectorAll("[data-grid-preset]").forEach((btn) => {
          btn.addEventListener("click", () => {
            const v = btn.getAttribute("data-grid-preset");
            if (v) main.value = v;
            syncRangeFieldsFromMain(root);
            bumpPreview();
          });
        });
      });
    }

    function money(value) {
      if (!Number.isFinite(Number(value))) return "-";
      return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function pct(value, maxFractionDigits = 2) {
      if (!Number.isFinite(Number(value))) return "-";
      const n = Number(value);
      return `${n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: maxFractionDigits })}%`;
    }

    function num(value, digits) {
      if (value === null || value === undefined) return "-";
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed.toFixed(digits) : "-";
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    /** Turn optimizer grid text (percent points, as typed) into a readable phrase. */
    function formatGridSpecHuman(raw) {
      const s = String(raw ?? "").trim();
      if (!s) return "—";
      const fmtToken = (tok) => {
        const n = parseNumLocale(String(tok).trim());
        if (!Number.isFinite(n)) return escapeHtml(String(tok).trim());
        const label = n.toLocaleString(undefined, { maximumFractionDigits: 6 });
        return `${label}%`;
      };
      if (s.includes(":")) {
        const parts = s.split(":").map((p) => p.trim()).filter((p) => p.length);
        if (parts.length === 3) {
          return `${fmtToken(parts[0])} → ${fmtToken(parts[1])}, step ${fmtToken(parts[2])}`;
        }
        return parts.map(fmtToken).join(" : ");
      }
      return s.split(",").map((t) => fmtToken(t.trim())).filter(Boolean).join(", ");
    }

    function formatParamValue(v) {
      if (typeof v === "boolean") return v ? "Yes" : "No";
      if (typeof v === "number") return Number.isFinite(v) ? String(v) : "-";
      if (typeof v === "string") return escapeHtml(v);
      return escapeHtml(JSON.stringify(v));
    }

    function formatLegParams(params) {
      if (!params || typeof params !== "object") {
        return "<p class=\"muted\">No parameters.</p>";
      }
      const rows = Object.entries(params).filter(([, val]) => val !== null && val !== undefined);
      if (!rows.length) return "<p class=\"muted\">No parameters.</p>";
      return `<dl class="param-dl">${rows.map(([k, val]) => `<dt>${escapeHtml(k)}</dt><dd>${formatParamValue(val)}</dd>`).join("")}</dl>`;
    }

    function renderSelectedRowLegs(row) {
      const host = document.querySelector("#opt-row-legs-body");
      if (!host) return;
      if (!row || !row.strategy_legs || !row.strategy_legs.length) {
        host.classList.add("muted");
        host.innerHTML = "<p>No leg metadata for this row.</p>";
        return;
      }
      host.classList.remove("muted");
      host.innerHTML = row.strategy_legs.map((leg) => `
        <div class="leg-card">
          <h4>${escapeHtml(leg.title || leg.id || "Leg")}</h4>
          ${formatLegParams(leg.params)}
        </div>
      `).join("");
    }

    function renderOptimizerFormLegPreview() {
      const f = document.querySelector("#optimizer-form");
      const host = document.querySelector("#opt-form-leg-preview");
      if (!f || !host) return;
      const core = f.elements.optimizer_strategy?.value || "threshold";
      const ed = f.elements.entry_drop_grid?.value?.trim() || "";
      const er = f.elements.entry_rise_grid?.value?.trim() || "";
      const tp = f.elements.take_profit_grid?.value?.trim() || "";
      const sl = f.elements.stop_loss_grid?.value?.trim() || "";
      const uk = f.elements.ut_key_grid?.value?.trim() || "";
      const ua = f.elements.ut_atr_period_grid?.value?.trim() || "";
      const ul = f.elements.ut_lr_period_grid?.value?.trim() || "";
      const ux = f.elements.ut_exit_pct_grid?.value?.trim() || "";
      const ud = f.elements.ut_exit_delay_grid?.value?.trim() || "";
      const mode = f.elements.combine_mode?.value || "all";
      const shorts = f.elements.allow_short?.checked;
      const bh = f.elements.companion_buy_hold?.checked;
      const legs = [];
      legs.push({
        title: "Sizing & costs (matches top of form)",
        params: {
          "Position size (% of balance)": f.elements.position_size_pct?.value !== "" && f.elements.position_size_pct?.value !== undefined
            ? `${f.elements.position_size_pct.value}%`
            : "—",
          "Fee (% of notional, each side)": f.elements.fee_rate?.value !== "" && f.elements.fee_rate?.value !== undefined
            ? `${f.elements.fee_rate.value}%`
            : "—",
          "Funding (% per interval)": f.elements.funding_rate_per_interval?.value !== "" && f.elements.funding_rate_per_interval?.value !== undefined
            ? `${f.elements.funding_rate_per_interval.value}%`
            : "—",
          "Slippage (bps)": f.elements.slippage_bps?.value ?? "—",
          "Half-spread (bps)": f.elements.spread_bps?.value ?? "—",
        },
      });
      if (core === "ut_bot") {
        legs.push({
          title: "UT Bot core (grid search)",
          params: {
            "Key value grid": escapeHtml(uk || "—"),
            "ATR period grid": escapeHtml(ua || "—"),
            "LinReg period grid": escapeHtml(ul || "—"),
            "Exit deviation grid": formatGridSpecHuman(ux),
            "Exit delay grid": escapeHtml(ud || "—"),
            "Short entries enabled": shorts,
            "Take profit grid": formatGridSpecHuman(tp),
            "Stop loss grid": formatGridSpecHuman(sl),
            "Heikin Ashi closes": !!f.elements.ut_use_heikin_ashi?.checked,
            "Timed exits vs LinReg": !!f.elements.ut_enable_exit_signals?.checked,
            "UTC session filter": !!f.elements.ut_enable_time_filter?.checked,
            "Cooldown gate": !!f.elements.ut_enable_cooldown?.checked,
            "UTC disable session": escapeHtml(String(f.elements.ut_disable_session?.value || "")),
            "Cooldown minutes": escapeHtml(String(f.elements.ut_cooldown_minutes?.value ?? "")),
          },
        });
      } else {
        legs.push({
          title: "Threshold (grid-optimized leg)",
          params: {
            "Entry drop (grid)": formatGridSpecHuman(ed),
            "Entry rise (grid, shorts)": shorts ? formatGridSpecHuman(er) : "(ignored — shorts off)",
            "Take profit (grid)": formatGridSpecHuman(tp),
            "Stop loss (grid)": formatGridSpecHuman(sl),
            "Short entries enabled": shorts,
          },
        });
      }
      if (bh) {
        legs.push({
          title: "Buy & Hold (companion)",
          params: { entry_rule: "Long on bar 0 when flat (no grid parameters)." },
        });
      }
      legs.push({
        title: "Combine mode",
        params: {
          mode,
          rule: mode === "any"
            ? "First leg in stack (top to bottom) that emits enter_long / enter_short wins."
            : "Every leg must emit the same entry side on the same candle.",
        },
      });
      host.innerHTML = legs.map((leg) => `
        <div class="leg-card">
          <h4>${escapeHtml(leg.title)}</h4>
          ${formatLegParams(leg.params)}
        </div>
      `).join("");
    }

    async function postJson(url, body) {
      let response;
      try {
        response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
      } catch (networkError) {
        throw new Error(`Cannot reach the dashboard server at ${url}. Make sure the dashboard process is running, then retry. (${networkError.message})`);
      }
      let payload = null;
      try { payload = await response.json(); } catch (_) { /* no body */ }
      if (!response.ok) {
        const message = payload && payload.error ? payload.error : `${response.status} ${response.statusText}`;
        throw new Error(message);
      }
      return payload;
    }

    async function getJson(url) {
      let response;
      try {
        response = await fetch(url);
      } catch (networkError) {
        throw new Error(`Cannot reach the dashboard server at ${url}. Make sure the dashboard process is running, then retry. (${networkError.message})`);
      }
      let payload = null;
      try { payload = await response.json(); } catch (_) { /* no body */ }
      if (!response.ok) {
        const message = payload && payload.error ? payload.error : `${response.status} ${response.statusText}`;
        throw new Error(message);
      }
      return payload;
    }

    function tagClass(value) { return value >= 0 ? "good" : "bad"; }

    function formatTime(ms) {
      if (!ms) return "-";
      return new Date(ms).toLocaleString();
    }

    function downloadCsv(filename, rows) {
      if (!rows.length) return;
      const headers = Object.keys(rows[0]);
      const csv = [
        headers.join(","),
        ...rows.map((row) => headers.map((key) => csvValue(row[key])).join(","))
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    }

    function csvValue(value) {
      if (value === null || value === undefined) return "";
      if (typeof value === "object") {
        const j = JSON.stringify(value);
        return `"${j.replaceAll('"', '""')}"`;
      }
      const text = String(value);
      if (text.includes(",") || text.includes('"') || text.includes("\n")) {
        return `"${text.replaceAll('"', '""')}"`;
      }
      return text;
    }

    /* ===== Charting ===== */
    function clearCanvas(canvas) {
      const ctx = canvas.getContext("2d");
      const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      const cssWidth = canvas.clientWidth || canvas.width;
      const cssHeight = canvas.clientHeight || canvas.height;
      canvas.width = Math.round(cssWidth * dpr);
      canvas.height = Math.round(cssHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssWidth, cssHeight);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, cssWidth, cssHeight);
      return { ctx, width: cssWidth, height: cssHeight };
    }

    function drawAxisLabel(ctx, text, x, y, color = "#667085") {
      ctx.fillStyle = color;
      ctx.font = "11px sans-serif";
      ctx.fillText(text, x, y);
    }

    function drawLineChart(canvas, series, options = {}) {
      const { ctx, width, height } = clearCanvas(canvas);
      const padding = options.padding || { left: 56, right: 16, top: 18, bottom: 36 };
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;
      let allValues = [];
      series.forEach((s) => s.points.forEach((p) => allValues.push(p.y)));
      const overlayValues = (options.overlay || []).flatMap((o) => o.points.map((p) => p.y));
      if (!allValues.length && !overlayValues.length) {
        drawAxisLabel(ctx, "No data", padding.left + 4, padding.top + 14);
        return;
      }
      const minY = options.minY ?? Math.min(...allValues);
      const maxY = options.maxY ?? Math.max(...allValues);
      const xs = series[0].points.map((p) => p.x);
      const minX = xs[0];
      const maxX = xs[xs.length - 1];
      function plotX(x) { return padding.left + ((x - minX) / Math.max(1, maxX - minX)) * innerW; }
      function plotY(y, lo = minY, hi = maxY) {
        return padding.top + innerH - ((y - lo) / Math.max(1e-9, hi - lo)) * innerH;
      }

      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = padding.top + (innerH * i) / 4;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + innerW, y);
        ctx.stroke();
        const v = maxY - ((maxY - minY) * i) / 4;
        drawAxisLabel(ctx, formatYAxis(v, options), padding.left - 6 - measureText(ctx, formatYAxis(v, options)), y + 3);
      }

      const ticks = 6;
      for (let i = 0; i <= ticks; i++) {
        const x = padding.left + (innerW * i) / ticks;
        const ts = minX + ((maxX - minX) * i) / ticks;
        ctx.beginPath();
        ctx.strokeStyle = "#f1f5f9";
        ctx.moveTo(x, padding.top);
        ctx.lineTo(x, padding.top + innerH);
        ctx.stroke();
        drawAxisLabel(ctx, shortDate(ts), x - 26, padding.top + innerH + 16);
      }

      series.forEach((s) => {
        ctx.strokeStyle = s.color || "#0f766e";
        ctx.lineWidth = s.lineWidth || 1.5;
        ctx.fillStyle = s.fillStyle;
        ctx.beginPath();
        s.points.forEach((point, idx) => {
          const x = plotX(point.x);
          const y = plotY(point.y);
          if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        if (s.fillStyle) {
          ctx.lineTo(plotX(s.points[s.points.length - 1].x), padding.top + innerH);
          ctx.lineTo(plotX(s.points[0].x), padding.top + innerH);
          ctx.closePath();
          ctx.fill();
        } else {
          ctx.stroke();
        }
      });

      if (options.overlay) {
        const overlayMin = Math.min(...overlayValues);
        const overlayMax = Math.max(...overlayValues);
        options.overlay.forEach((s) => {
          ctx.strokeStyle = s.color || "#1d4ed8";
          ctx.lineWidth = 1;
          ctx.beginPath();
          s.points.forEach((point, idx) => {
            const x = plotX(point.x);
            const y = plotY(point.y, overlayMin, overlayMax);
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.stroke();
        });
        drawAxisLabel(ctx, options.overlayLabel || "", padding.left + innerW - 70, padding.top + 12, "#1d4ed8");
      }

      if (options.markers) {
        options.markers.forEach((marker) => {
          const x = plotX(marker.x);
          const y = plotY(marker.y, options.markerOverlay ? Math.min(...overlayValues) : minY,
                          options.markerOverlay ? Math.max(...overlayValues) : maxY);
          ctx.beginPath();
          ctx.fillStyle = marker.color || "#0f766e";
          ctx.arc(x, y, marker.r || 4, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    }

    function formatYAxis(value, options) {
      if (options.formatY === "money") return money(value);
      if (options.formatY === "pct") return `${Number(value).toFixed(1)}%`;
      if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}k`;
      return Number(value).toFixed(2);
    }

    function shortDate(ms) {
      if (!ms) return "";
      const d = new Date(ms);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    }

    function measureText(ctx, text) {
      return ctx.measureText(text).width;
    }

    function drawBarChart(canvas, bars, options = {}) {
      const { ctx, width, height } = clearCanvas(canvas);
      const padding = options.padding || { left: 56, right: 16, top: 12, bottom: 32 };
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;
      if (!bars.length) {
        drawAxisLabel(ctx, "No data", padding.left + 4, padding.top + 14);
        return;
      }
      const values = bars.map((b) => b.value);
      const minV = Math.min(0, ...values);
      const maxV = Math.max(0, ...values);
      const range = Math.max(1e-9, maxV - minV);
      const barW = innerW / bars.length;

      const zeroY = padding.top + innerH - ((0 - minV) / range) * innerH;
      ctx.strokeStyle = "#e2e8f0";
      ctx.beginPath();
      ctx.moveTo(padding.left, zeroY);
      ctx.lineTo(padding.left + innerW, zeroY);
      ctx.stroke();

      bars.forEach((bar, idx) => {
        const x = padding.left + idx * barW;
        const y = padding.top + innerH - ((bar.value - minV) / range) * innerH;
        const color = bar.color || (bar.value >= 0 ? "rgba(4, 120, 87, 0.85)" : "rgba(180, 35, 24, 0.85)");
        ctx.fillStyle = color;
        const top = Math.min(y, zeroY);
        const h = Math.max(1, Math.abs(y - zeroY));
        ctx.fillRect(x + 1, top, Math.max(1, barW - 2), h);
      });

      ctx.fillStyle = "#475569";
      ctx.font = "10px sans-serif";
      bars.forEach((bar, idx) => {
        if (idx % Math.ceil(bars.length / 8) !== 0) return;
        const x = padding.left + idx * barW + barW / 2;
        ctx.fillText(bar.label || "", x - 14, padding.top + innerH + 14);
      });
      drawAxisLabel(ctx, formatYAxis(maxV, options), padding.left - 6 - measureText(ctx, formatYAxis(maxV, options)), padding.top + 8);
      drawAxisLabel(ctx, formatYAxis(minV, options), padding.left - 6 - measureText(ctx, formatYAxis(minV, options)), padding.top + innerH);
    }

    function drawHeatmap(canvas, cells, options = {}) {
      const { ctx, width, height } = clearCanvas(canvas);
      const padding = options.padding || { left: 78, right: 24, top: 18, bottom: 40 };
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;
      if (!cells.length) {
        drawAxisLabel(ctx, "No data", padding.left + 4, padding.top + 14);
        return;
      }
      const xs = Array.from(new Set(cells.map((c) => c.x))).sort((a, b) => a - b);
      const ys = Array.from(new Set(cells.map((c) => c.y))).sort((a, b) => a - b);
      const cellW = innerW / xs.length;
      const cellH = innerH / ys.length;
      const values = cells.map((c) => c.value).filter((v) => Number.isFinite(v));
      const lo = Math.min(...values, 0);
      const hi = Math.max(...values, 0);
      const span = Math.max(1e-9, hi - lo);
      cells.forEach((cell) => {
        const xi = xs.indexOf(cell.x);
        const yi = ys.indexOf(cell.y);
        const x = padding.left + xi * cellW;
        const y = padding.top + (ys.length - 1 - yi) * cellH;
        ctx.fillStyle = colorFromRange(cell.value, lo, hi);
        ctx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);
        ctx.fillStyle = "#0f172a";
        ctx.font = "10px sans-serif";
        const label = Number.isFinite(cell.value) ? `${cell.value.toFixed(1)}%` : "-";
        ctx.fillText(label, x + cellW / 2 - 16, y + cellH / 2 + 3);
      });
      ctx.fillStyle = "#475569";
      ctx.font = "10px sans-serif";
      const formatXTick = options.formatXTick || ((value) => `${(value * 100).toFixed(2)}%`);
      const formatYTick = options.formatYTick || ((value) => `${(value * 100).toFixed(2)}%`);
      xs.forEach((value, idx) => {
        ctx.fillText(formatXTick(value), padding.left + idx * cellW + 4, padding.top + innerH + 16);
      });
      ys.forEach((value, idx) => {
        const y = padding.top + (ys.length - 1 - idx) * cellH + cellH / 2 + 3;
        ctx.fillText(formatYTick(value), 6, y);
      });
      drawAxisLabel(ctx, options.xLabel || "Entry Drop %", padding.left + innerW - 80, padding.top + innerH + 30);
      ctx.save();
      ctx.translate(14, padding.top + innerH / 2);
      ctx.rotate(-Math.PI / 2);
      drawAxisLabel(ctx, options.yLabel || "Take Profit %", -40, 0);
      ctx.restore();
    }

    function drawScatter(canvas, points, options = {}) {
      const { ctx, width, height } = clearCanvas(canvas);
      const padding = options.padding || { left: 56, right: 18, top: 16, bottom: 36 };
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;
      if (!points.length) {
        drawAxisLabel(ctx, "No data", padding.left + 4, padding.top + 14);
        return;
      }
      const xs = points.map((p) => p.x);
      const ys = points.map((p) => p.y);
      const minX = Math.min(...xs); const maxX = Math.max(...xs);
      const minY = Math.min(...ys); const maxY = Math.max(...ys);
      ctx.strokeStyle = "#e2e8f0";
      ctx.beginPath();
      ctx.moveTo(padding.left, padding.top);
      ctx.lineTo(padding.left, padding.top + innerH);
      ctx.lineTo(padding.left + innerW, padding.top + innerH);
      ctx.stroke();
      points.forEach((point) => {
        const x = padding.left + ((point.x - minX) / Math.max(1e-9, maxX - minX)) * innerW;
        const y = padding.top + innerH - ((point.y - minY) / Math.max(1e-9, maxY - minY)) * innerH;
        const r = point.r || 4;
        ctx.fillStyle = point.color || (point.y >= 0 ? "rgba(4, 120, 87, 0.7)" : "rgba(180, 35, 24, 0.7)");
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      });
      drawAxisLabel(ctx, options.xLabel || "X", padding.left + innerW - 30, padding.top + innerH + 18);
      ctx.save();
      ctx.translate(14, padding.top + innerH / 2);
      ctx.rotate(-Math.PI / 2);
      drawAxisLabel(ctx, options.yLabel || "Y", -30, 0);
      ctx.restore();
    }

    function colorFromRange(value, lo, hi) {
      if (!Number.isFinite(value)) return "#e5e7eb";
      const mid = 0;
      if (value >= mid) {
        const t = Math.min(1, value / Math.max(1e-9, hi));
        return `rgba(4, 120, 87, ${0.15 + 0.6 * t})`;
      }
      const t = Math.min(1, value / Math.min(-1e-9, lo));
      return `rgba(180, 35, 24, ${0.15 + 0.6 * t})`;
    }

    /* ===== Backtest tab ===== */
    const backtestState = { result: null };
    const gainEstimatorUi = { walletTouched: false, wired: false };

    /** Product of (1+r_i)^(1/n) from calendar-month buckets (Monthly Returns)—optional compare only; edge months distort. */
    function geometricMeanMonthlyGrowthFactor(monthRows) {
      if (!monthRows || !monthRows.length) return NaN;
      let prodLog = 0;
      let n = 0;
      for (const row of monthRows) {
        const rp = Number(row.return_pct);
        if (!Number.isFinite(rp)) continue;
        const m = 1 + rp / 100;
        if (!(m > 0)) return NaN;
        prodLog += Math.log(m);
        n++;
      }
      if (n < 1) return NaN;
      return Math.exp(prodLog / n);
    }

    /** Scale positive monthly drift down using observed worst drawdown fraction (stress ≥ 1 is harsher). */
    function drawdownDriftMultiplier(maxDdPctPoints, stress) {
      const s = Number(stress);
      const dd = Math.max(0, Number(maxDdPctPoints) / 100);
      if (!(s > 0) || !Number.isFinite(dd)) return 1;
      return Math.max(0, 1 - s * dd);
    }

    function applyDdStressToGrowthFactor(rawFactor, driftMultiplier) {
      const f = Number(rawFactor);
      const m = Number(driftMultiplier);
      if (!(f > 0) || !Number.isFinite(f)) return NaN;
      if (!Number.isFinite(m)) return f;
      const excess = f - 1;
      if (excess >= 0) return 1 + excess * m;
      return f;
    }

    function maybeSyncGainEstimatorWallet(backtestPayload) {
      const input = $("#gain-wallet");
      if (!input || gainEstimatorUi.walletTouched) return;
      const ib = Number((backtestPayload.stats || {}).initial_balance);
      if (Number.isFinite(ib) && ib > 0) {
        input.value = String(ib);
      }
    }

    function refreshGainEstimator() {
      if (!backtestState.result) return;
      renderGainEstimator(backtestState.result);
    }

    function renderGainEstimator(payload) {
      const el = $("#gain-estimator-body");
      if (!el || !payload) return;

      const s = payload.stats || {};
      const monthRows = payload.monthly_returns || [];
      let walletRaw = parseNumLocale($("#gain-wallet").value);
      const initBal = Number(s.initial_balance);
      const finBal = Number(s.final_balance);
      if (!(walletRaw > 0) || !Number.isFinite(walletRaw)) {
        walletRaw = initBal > 0 && Number.isFinite(initBal) ? initBal : NaN;
      }
      const horizonMonths = Math.max(1, parseInt($("#gain-horizon").value, 10) || 12);
      const stress = parseFloat($("#gain-dd-stress").value) || 0;

      if (!(walletRaw > 0) || !Number.isFinite(walletRaw)) {
        el.innerHTML = "<span class='bad\">Enter a positive total wallet so projected balances are anchored to finite capital.</span>";
        return;
      }

      const m = payload.metadata || {};
      const wallDaysMeta = Number(m.candles_wall_span_days);
      const eqDaysSpan = Number(s.duration_days);
      /** Prefer full bar window (metadata) so gain math matches dashboard backtest span. */
      const daysSpan =
        Number.isFinite(wallDaysMeta) && wallDaysMeta > 1e-9 ? wallDaysMeta : eqDaysSpan;
      const monthsObserved =
        Number.isFinite(daysSpan) && daysSpan > 0 ? (daysSpan * 12) / 365 : NaN;

      let warnings = [];
      if (!(initBal > 0) || !Number.isFinite(initBal) || !(finBal > 0) || !Number.isFinite(finBal)) {
        el.innerHTML = "<span class=\"bad\">Need positive initial and final balances to derive a clock-true growth rate.</span>";
        return;
      }
      if (!(monthsObserved > 0)) {
        el.innerHTML = "<strong>No projection yet.</strong> Equity timestamps do not yield a usable span (need spaced curve points).";
        return;
      }

      const perMonthClockTrueRaw = (finBal / initBal) ** (1 / monthsObserved);

      if (monthsObserved < 0.5 || (Number.isFinite(daysSpan) && daysSpan > 0 && daysSpan < 14)) {
        warnings.push("<strong>Very short clock span:</strong> extrapolation stays speculative.");
      }

      let calMonthGmHtml = "";
      const gmfCalendar = geometricMeanMonthlyGrowthFactor(monthRows);
      if (monthRows.length >= 2 && Number.isFinite(gmfCalendar)) {
        calMonthGmHtml =
          "<br /><span>" +
          escapeHtml(
            `Monthly Returns cohort (equal UTC months) averages \u2248 ${pct((gmfCalendar - 1) * 100)}/mo\u2014often misleads versus clock-true drift when edge months are partial.`,
          ) +
          "</span>";
      }

      const driftM = drawdownDriftMultiplier(s.max_drawdown_pct, stress);
      const timeAdjMonthly = applyDdStressToGrowthFactor(perMonthClockTrueRaw, driftM);

      const btForm = document.querySelector("#backtest-form");
      const fixedStake =
        !!(btForm && btForm.elements.ignore_position_size_pct && btForm.elements.ignore_position_size_pct.checked);
      if (fixedStake) {
        warnings.push(
          "<strong>Fixed-dollar stake:</strong> percentages mirror %-of-equity path unless sizing tracks wallet.",
        );
      }

      let plannerFactor = timeAdjMonthly;

      const MONTHLY_CEIL_PLANNING = 1.08;
      let monthlyPlannerCapWarn = "";
      if (Number.isFinite(plannerFactor) && plannerFactor > MONTHLY_CEIL_PLANNING) {
        plannerFactor = MONTHLY_CEIL_PLANNING;
        monthlyPlannerCapWarn = ` Monthly compounded pace was clipped to <strong>+${((MONTHLY_CEIL_PLANNING - 1) * 100).toFixed(1)}%/mo</strong> for planning realism.`;
        warnings.push("<strong>Unusually high smoothed drift;</strong> long-run projection capped manually.");
      }

      const monthlyPlannerPct100 = (plannerFactor - 1) * 100;

      let annualizedMonthlyImpliedPct = NaN;
      if (monthlyPlannerPct100 >= -99.995) {
        annualizedMonthlyImpliedPct = ((plannerFactor ** 12) - 1) * 100;
      }

      const endWallet = walletRaw * plannerFactor ** horizonMonths;
      const pnlFwd = endWallet - walletRaw;
      const pctFwd = walletRaw !== 0 ? (pnlFwd / walletRaw) * 100 : 0;

      const scaleNote =
        Number.isFinite(initBal) && initBal > 0 ? `Wallet vs backtest balance: ×${(walletRaw / initBal).toFixed(4)}.` : "";

      let cagrCmp = "";
      const arNaive = Number(s.annualized_return_pct);
      const unstressedAnnualPct = Number.isFinite(perMonthClockTrueRaw)
        ? ((perMonthClockTrueRaw ** 12) - 1) * 100
        : NaN;
      if (Number.isFinite(arNaive) && Number.isFinite(unstressedAnnualPct) && Number.isFinite(annualizedMonthlyImpliedPct)) {
        cagrCmp = escapeHtml(
          `Annualized (${pct(arNaive)}) matches unstressed clock-true CAGR (${pct(unstressedAnnualPct)} over ${num(monthsObserved, 2)} equiv. mo). Stressed planner pace ≈ ${pct(annualizedMonthlyImpliedPct)}/yr if it held.`,
        );
      }

      const warnHtml = warnings.length ? `<div class="bad" style="margin:10px 0;font-size:12px">${warnings.join("<br />")}</div>` : "";

      const daysStr = Number.isFinite(daysSpan) ? `${daysSpan.toFixed(2)} cal. days` : "—";

      el.innerHTML = `
        ${warnHtml}
        <div class="estimator-metrics summary-grid">
          <div class="metric metric--pre"><span>Clock span · equiv. avg. mo.</span><strong>${escapeHtml(daysStr)} · ${num(monthsObserved, 2)} mo</strong></div>
          <div class="metric"><span>Clock-true mo. drift</span><strong>${pct((perMonthClockTrueRaw - 1) * 100)}</strong></div>
          <div class="metric"><span>After DD stress (${driftM.toFixed(3)}×)</span><strong>${pct((timeAdjMonthly - 1) * 100)}</strong></div>
          <div class="metric"><span>Planning drift (monthly)</span><strong>${pct((plannerFactor - 1) * 100)}</strong></div>
          <div class="metric"><span>${horizonMonths} mo compounded path</span><strong>${pct(pctFwd)}</strong></div>
          <div class="metric metric--pre"><span>Projected balance</span><strong>${money(endWallet)}</strong></div>
          <div class="metric"><span>Projected profit</span><strong class="${tagClass(pnlFwd)}">${money(pnlFwd)}</strong></div>
        </div>
        <p class="muted" style="margin:12px 0 0;font-size:12px">
          ${escapeHtml("(final ÷ initial)^(1 ÷ fractional months)")} · fractional months = ${escapeHtml("(elapsed calendar days × 12 / 365)")} from first/last equity timestamps—ignores bar spacing (e.g. hourly candles).${calMonthGmHtml}<br />
          Stress uses historical max DD ${pct(s.max_drawdown_pct)} on <strong>positive</strong> drift: <code>max(0, 1 − stress × DD)</code>, then planner ceiling.${scaleNote ? `<br />${escapeHtml(scaleNote)}` : ""}
          ${cagrCmp ? `<br /><span>${cagrCmp}</span>` : ""}
          ${monthlyPlannerCapWarn}
        </p>`;
    }

    function wireGainEstimator() {
      if (gainEstimatorUi.wired) return;
      const wEl = $("#gain-wallet");
      if (!wEl) return;
      gainEstimatorUi.wired = true;
      wEl.addEventListener("input", () => {
        gainEstimatorUi.walletTouched = true;
        refreshGainEstimator();
      });
      ["#gain-horizon", "#gain-dd-stress"].forEach((sel) => {
        const node = $(sel);
        if (node) node.addEventListener("change", refreshGainEstimator);
      });
    }

    document.querySelector("#backtest-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runBacktest();
    });

    document.querySelector("#copy-config").addEventListener("click", () => {
      const values = readTradingForm(document.querySelector("#backtest-form"));
      navigator.clipboard.writeText(JSON.stringify(values, null, 2)).then(() => {
        setStatus("backtest-status", "Config copied to clipboard.");
      });
    });

    document.querySelector("#export-trades").addEventListener("click", () => {
      if (!backtestState.result) return;
      downloadCsv("trades.csv", backtestState.result.trades);
    });

    function formatBacktestSpan(payload) {
      const s = payload.stats || {};
      const m = payload.metadata || {};
      const ec = payload.equity_curve || [];
      const wallD = Number(m.candles_wall_span_days);
      const eqD = Number(s.duration_days);
      const primary = Number.isFinite(wallD) && wallD > 1e-9 ? wallD : eqD;
      const primaryStr = Number.isFinite(primary) ? `${primary.toFixed(2)} d` : "-";
      const nBars = Number(m.candle_count) || ec.length || 0;
      let out = `${primaryStr} · ${nBars} bars`;
      if (m.first_candle && m.last_candle) {
        const a = String(m.first_candle).slice(0, 10);
        const b = String(m.last_candle).slice(0, 10);
        out += `\n${a} → ${b} (UTC candle opens)`;
      }
      if (
        Number.isFinite(wallD) &&
        Number.isFinite(eqD) &&
        Math.abs(wallD - eqD) > Math.max(wallD, eqD) * 0.05 + 0.005
      ) {
        out += `\nEquity timestep span: ${eqD.toFixed(2)} d`;
      }
      const histReq = Number(m.history_target_days_requested);
      if (Number.isFinite(histReq)) {
        out += `\nAuto history target: ${histReq} cal. days (Binance)`;
      }
      return out;
    }

    async function runBacktest() {
      setStatus("backtest-status", "Running backtest (auto-downloading data if needed)...");
      const button = document.querySelector("#run-backtest");
      button.disabled = true;
      try {
        const payload = await postJson("/api/backtest", readTradingForm(document.querySelector("#backtest-form")));
        backtestState.result = payload;
        renderBacktestStats(payload);
        renderBacktestCharts(payload);
        renderBacktestTrades(payload);
        renderBacktestExitReasons(payload);
        maybeSyncGainEstimatorWallet(payload);
        renderGainEstimator(payload);
        const note = payload.metadata && payload.metadata.auto_download_note;
        const summary = `${payload.metadata.symbol} ${payload.metadata.timeframe} → ${payload.stats.trade_count} trades, return ${pct(payload.stats.total_return_pct)}, Sharpe ${num(payload.stats.sharpe_ratio, 2)}`;
        setStatus("backtest-status", note ? `${note} ${summary}` : summary);
        const stackInfo = payload.metadata.strategy_stack ? ` • ${payload.metadata.strategy_stack} (${payload.metadata.combine_mode})` : "";
        const spanDays = Number(payload.stats.duration_days);
        const spanTxt = Number.isFinite(spanDays) ? ` · ${spanDays.toFixed(1)}d span` : "";
        setHeaderStatus(`${payload.metadata.symbol} ${payload.metadata.market_type} ${payload.metadata.timeframe} • ${payload.metadata.candle_count} candles${spanTxt}${stackInfo}`);
      } catch (error) {
        setStatus("backtest-status", error.message, true);
      } finally {
        button.disabled = false;
      }
    }

    function renderBacktestStats(payload) {
      const s = payload.stats;
      $("#bt-net").textContent = money(s.net_pnl);
      $("#bt-net").className = tagClass(s.net_pnl);
      $("#bt-return").textContent = pct(s.total_return_pct);
      $("#bt-return").className = tagClass(s.total_return_pct);
      $("#bt-duration").textContent = formatBacktestSpan(payload);
      $("#bt-annual").textContent = pct(s.annualized_return_pct);
      $("#bt-annual").className = tagClass(s.annualized_return_pct);
      $("#bt-dd").textContent = pct(s.max_drawdown_pct);
      $("#bt-dd").className = "bad";
      $("#bt-sharpe").textContent = num(s.sharpe_ratio, 3);
      $("#bt-sortino").textContent = num(s.sortino_ratio, 3);
      $("#bt-calmar").textContent = num(s.calmar_ratio, 3);
      $("#bt-pf").textContent = num(s.profit_factor, 3);
      $("#bt-win").textContent = pct(s.win_rate_pct);
      $("#bt-payoff").textContent = num(s.payoff_ratio, 3);
      $("#bt-exp").textContent = money(s.expectancy);
      $("#bt-exp").className = tagClass(s.expectancy);
      $("#bt-trades").textContent = s.trade_count;
      $("#bt-sides").textContent = `${s.long_trade_count ?? 0} / ${s.short_trade_count ?? 0}`;
      $("#bt-bars").textContent = num(s.average_bars_held, 1);
      $("#bt-winstreak").textContent = s.longest_win_streak;
      $("#bt-lossstreak").textContent = s.longest_loss_streak;
      $("#bt-best").textContent = money(s.best_trade_pnl);
      $("#bt-best").className = "good";
      $("#bt-worst").textContent = money(s.worst_trade_pnl);
      $("#bt-worst").className = "bad";
      $("#bt-fees").textContent = money(s.total_fees_paid);
      $("#bt-funding").textContent = money(s.total_funding_paid);
      $("#bt-r2").textContent = num(s.pnl_r_squared, 3);
      $("#bt-ddbars").textContent = s.max_drawdown_duration_bars;
      $("#bt-final").textContent = money(s.final_balance);
    }

    function renderBacktestCharts(payload) {
      const equity = payload.equity_curve;
      const trades = payload.trades;

      drawLineChart(
        document.querySelector("#bt-price-chart"),
        [{
          label: "Price",
          color: "#1d4ed8",
          points: equity.map((p) => ({ x: p.time, y: p.close_price }))
        }],
        {
          formatY: "money",
          markers: trades.flatMap((trade) => [
            { x: trade.entry_time, y: trade.entry_price, color: trade.side === "long" ? "rgba(4, 120, 87, 0.85)" : "rgba(180, 35, 24, 0.85)", r: 4 },
            { x: trade.exit_time, y: trade.exit_price, color: trade.net_pnl >= 0 ? "rgba(4, 120, 87, 0.55)" : "rgba(180, 35, 24, 0.55)", r: 3 }
          ])
        }
      );

      drawLineChart(
        document.querySelector("#bt-equity-chart"),
        [{
          label: "Equity",
          color: "#0f766e",
          fillStyle: "rgba(15, 118, 110, 0.12)",
          points: equity.map((p) => ({ x: p.time, y: p.equity }))
        }],
        { formatY: "money" }
      );

      drawLineChart(
        document.querySelector("#bt-drawdown-chart"),
        [{
          label: "Drawdown",
          color: "#b42318",
          fillStyle: "rgba(180, 35, 24, 0.18)",
          points: equity.map((p) => ({ x: p.time, y: -p.drawdown_pct }))
        }],
        { formatY: "pct", maxY: 0 }
      );

      drawBarChart(
        document.querySelector("#bt-pnldist-chart"),
        payload.trade_pnl_distribution.map((bucket) => ({
          label: `${money(bucket.start)}`,
          value: bucket.count
        }))
      );

      drawBarChart(
        document.querySelector("#bt-monthly-chart"),
        payload.monthly_returns.map((row) => ({
          label: row.label,
          value: row.return_pct,
          color: row.return_pct >= 0 ? "rgba(4, 120, 87, 0.85)" : "rgba(180, 35, 24, 0.85)"
        })),
        { formatY: "pct" }
      );
    }

    function renderBacktestTrades(payload) {
      const body = document.querySelector("#bt-trades-body");
      if (!payload.trades.length) {
        body.innerHTML = `<tr><td colspan="14" class="muted">No trades executed.</td></tr>`;
        return;
      }
      body.innerHTML = payload.trades.map((trade, idx) => `
        <tr>
          <td>${idx + 1}</td>
          <td><span class="pill ${trade.side}">${trade.side}</span></td>
          <td>${formatTime(trade.entry_time)}</td>
          <td>${formatTime(trade.exit_time)}</td>
          <td>${trade.bars_held}</td>
          <td>${money(trade.entry_price)}</td>
          <td>${money(trade.exit_price)}</td>
          <td>${num(trade.quantity, 4)}</td>
          <td>${money(trade.margin)}</td>
          <td class="${tagClass(trade.net_pnl)}">${money(trade.net_pnl)}</td>
          <td class="${tagClass(trade.return_pct)}">${pct(trade.return_pct)}</td>
          <td>${money(trade.entry_fee + trade.exit_fee)}</td>
          <td>${money(trade.funding_paid)}</td>
          <td><span class="pill ${exitClass(trade.exit_reason)}">${trade.exit_reason}</span></td>
        </tr>
      `).join("");
    }

    function exitClass(reason) {
      if (reason === "take_profit") return "tp";
      if (reason === "stop_loss") return "sl";
      if (reason === "liquidation") return "liq";
      return "end";
    }

    function renderBacktestExitReasons(payload) {
      const container = document.querySelector("#bt-exit-reasons");
      if (!payload.exit_reasons.length) {
        container.textContent = "No exits recorded.";
        return;
      }
      container.innerHTML = payload.exit_reasons.map((row) =>
        `<span class="pill ${exitClass(row.reason)}" style="margin-right:8px">${row.reason}: ${row.count}</span>`
      ).join("");
    }

    /* ===== Optimizer tab ===== */
    const optimizerState = { rows: [], filteredRows: [], metadata: null };

    document.querySelector("#optimizer-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runOptimizer();
    });

    const optimizerFormEl = document.querySelector("#optimizer-form");
    if (optimizerFormEl) {
      optimizerFormEl.addEventListener("input", renderOptimizerFormLegPreview);
      optimizerFormEl.addEventListener("change", renderOptimizerFormLegPreview);
    }

    document.querySelector("#export-opt-csv").addEventListener("click", () => {
      downloadCsv("optimizer_results.csv", optimizerState.filteredRows);
    });

    document.querySelector("#reset-filters").addEventListener("click", () => {
      ["f-min-return","f-max-drawdown","f-min-sharpe","f-min-sortino","f-min-calmar","f-min-r2","f-min-win","f-min-trades"].forEach((id) => {
        document.getElementById(id).value = "";
      });
      document.getElementById("f-sort").value = "final_balance";
      document.getElementById("f-dir").value = "desc";
      applyOptimizerFilters();
    });

    document.querySelector("#load-best-into-backtest").addEventListener("click", () => {
      const best = optimizerState.filteredRows[0];
      if (!best) return;
      copyOptimizerRowToBacktest(best);
    });

    ["f-min-return","f-max-drawdown","f-min-sharpe","f-min-sortino","f-min-calmar","f-min-r2","f-min-win","f-min-trades","f-sort","f-dir"].forEach((id) => {
      const el = document.getElementById(id);
      el.addEventListener("input", applyOptimizerFilters);
      el.addEventListener("change", applyOptimizerFilters);
    });

    async function runOptimizer() {
      setStatus("opt-status", "Running optimizer (auto-downloading data if needed)...");
      const button = document.querySelector("#run-optimizer");
      button.disabled = true;
      try {
        const payload = await postJson("/api/optimize", readTradingForm(document.querySelector("#optimizer-form")));
        optimizerState.rows = payload.rows || [];
        optimizerState.metadata = payload.metadata;
        applyOptimizerFilters();
        const meta = payload.metadata;
        const note = meta && meta.auto_download_note;
        const summary = `${meta.exchange} ${meta.symbol} ${meta.market_type} ${meta.timeframe}: ${meta.candle_count} candles, ${meta.combination_count} optimizer rows.`;
        setStatus("opt-status", note ? `${note} ${summary}` : summary);
      } catch (error) {
        setStatus("opt-status", error.message, true);
      } finally {
        button.disabled = false;
      }
    }

    function applyOptimizerFilters() {
      const minReturn = numberOrNull("f-min-return");
      const maxDrawdown = numberOrNull("f-max-drawdown");
      const minSharpe = numberOrNull("f-min-sharpe");
      const minSortino = numberOrNull("f-min-sortino");
      const minCalmar = numberOrNull("f-min-calmar");
      const minR2 = numberOrNull("f-min-r2");
      const minWin = numberOrNull("f-min-win");
      const minTrades = numberOrNull("f-min-trades");
      const sortKey = document.getElementById("f-sort").value;
      const dir = document.getElementById("f-dir").value === "asc" ? 1 : -1;

      optimizerState.filteredRows = optimizerState.rows
        .filter((row) => minReturn === null || row.total_return_pct >= minReturn)
        .filter((row) => maxDrawdown === null || row.max_drawdown_pct <= maxDrawdown)
        .filter((row) => minSharpe === null || finiteValue(row.sharpe_ratio, -Infinity) >= minSharpe)
        .filter((row) => minSortino === null || finiteValue(row.sortino_ratio, -Infinity) >= minSortino)
        .filter((row) => minCalmar === null || finiteValue(row.calmar_ratio, -Infinity) >= minCalmar)
        .filter((row) => minR2 === null || finiteValue(row.pnl_r_squared, -Infinity) >= minR2)
        .filter((row) => minWin === null || row.win_rate_pct >= minWin)
        .filter((row) => minTrades === null || row.trade_count >= minTrades)
        .sort((a, b) => compareRows(a, b, sortKey, dir));

      renderOptimizerSummary();
      renderOptimizerTable();
      renderOptimizerCharts();
    }

    function compareRows(a, b, key, dir) {
      const aValue = finiteValue(a[key], key === "max_drawdown_pct" ? Infinity : -Infinity);
      const bValue = finiteValue(b[key], key === "max_drawdown_pct" ? Infinity : -Infinity);
      if (aValue === bValue) return 0;
      return aValue > bValue ? dir : -dir;
    }

    function numberOrNull(id) {
      const value = document.getElementById(id).value;
      if (value === null || value === undefined || value === "") return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }

    function finiteValue(value, fallback) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : fallback;
    }

    function renderOptimizerSummary() {
      const rows = optimizerState.filteredRows;
      $("#opt-rows-shown").textContent = rows.length;
      $("#opt-rows-total").textContent = optimizerState.rows.length;
      const bestFinal = bestBy(rows, "final_balance");
      const bestSharpe = bestBy(rows, "sharpe_ratio");
      const bestSortino = bestBy(rows, "sortino_ratio");
      const bestCalmar = bestBy(rows, "calmar_ratio");
      const bestR2 = bestBy(rows, "pnl_r_squared");
      $("#opt-best-final").textContent = bestFinal ? money(bestFinal.final_balance) : "-";
      $("#opt-best-return").textContent = bestFinal ? pct(bestFinal.total_return_pct) : "-";
      $("#opt-best-sharpe").textContent = bestSharpe ? num(bestSharpe.sharpe_ratio, 3) : "-";
      $("#opt-best-sortino").textContent = bestSortino ? num(bestSortino.sortino_ratio, 3) : "-";
      $("#opt-best-calmar").textContent = bestCalmar ? num(bestCalmar.calmar_ratio, 3) : "-";
      $("#opt-best-r2").textContent = bestR2 ? num(bestR2.pnl_r_squared, 3) : "-";
    }

    function bestBy(rows, key) {
      let best = null;
      rows.forEach((row) => {
        const value = finiteValue(row[key], -Infinity);
        if (best === null || value > finiteValue(best[key], -Infinity)) best = row;
      });
      return best;
    }

    function renderOptimizerTable() {
      const body = document.querySelector("#opt-results-body");
      const rows = optimizerState.filteredRows;
      if (!rows.length) {
        body.innerHTML = `<tr><td colspan="31" class="muted">No rows match the current filters.</td></tr>`;
        return;
      }
      body.innerHTML = rows.map((row, idx) => `
        <tr data-row-index="${idx}">
          <td>${idx + 1}</td>
          <td style="max-width:140px;white-space:normal;text-align:left">${escapeHtml(row.strategy_stack || row.strategy_name || "-")}</td>
          <td>${escapeHtml(row.combine_mode || "all")}</td>
          <td>${row.allow_short ? "Yes" : "No"}</td>
          <td>${rateAsPercentLabel(row.entry_drop_pct)}</td>
          <td>${row.entry_rise_pct === null || row.entry_rise_pct === undefined ? "—" : rateAsPercentLabel(row.entry_rise_pct)}</td>
          <td>${rateAsPercentLabel(row.take_profit_pct)}</td>
          <td>${rateAsPercentLabel(row.stop_loss_pct)}</td>
          <td>${row.optimizer_strategy === "ut_bot" && row.ut_key_value !== null && row.ut_key_value !== undefined ? Number(row.ut_key_value).toFixed(3) : "—"}</td>
          <td>${row.optimizer_strategy === "ut_bot" && row.ut_atr_period !== null && row.ut_atr_period !== undefined ? row.ut_atr_period : "—"}</td>
          <td>${row.optimizer_strategy === "ut_bot" && row.ut_lr_period !== null && row.ut_lr_period !== undefined ? row.ut_lr_period : "—"}</td>
          <td>${row.optimizer_strategy === "ut_bot" && row.ut_exit_pct !== null && row.ut_exit_pct !== undefined ? rateAsPercentLabel(row.ut_exit_pct) : "—"}</td>
          <td>${row.optimizer_strategy === "ut_bot" && row.ut_exit_delay !== null && row.ut_exit_delay !== undefined ? row.ut_exit_delay : "—"}</td>
          <td>${money(row.final_balance)}</td>
          <td class="${tagClass(row.net_pnl)}">${money(row.net_pnl)}</td>
          <td class="${tagClass(row.total_return_pct)}">${pct(row.total_return_pct)}</td>
          <td class="${tagClass(row.annualized_return_pct)}">${pct(row.annualized_return_pct)}</td>
          <td>${num(row.sharpe_ratio, 3)}</td>
          <td>${num(row.sortino_ratio, 3)}</td>
          <td>${num(row.calmar_ratio, 3)}</td>
          <td>${num(row.pnl_r_squared, 3)}</td>
          <td>${pct(row.max_drawdown_pct)}</td>
          <td>${row.max_drawdown_duration_bars}</td>
          <td>${pct(row.win_rate_pct)}</td>
          <td>${num(row.profit_factor, 3)}</td>
          <td>${num(row.payoff_ratio, 3)}</td>
          <td>${money(row.expectancy)}</td>
          <td>${num(row.average_bars_held, 1)}</td>
          <td>${row.longest_win_streak}</td>
          <td>${row.longest_loss_streak}</td>
          <td>${row.trade_count}</td>
        </tr>
      `).join("");

      body.querySelectorAll("tr").forEach((tr) => {
        tr.addEventListener("click", () => {
          const idx = Number(tr.dataset.rowIndex);
          copyOptimizerRowToBacktest(rows[idx]);
        });
      });
    }

    function copyOptimizerRowToBacktest(row) {
      renderSelectedRowLegs(row);
      const form = document.querySelector("#backtest-form");
      const optimizerForm = document.querySelector("#optimizer-form");
      const sharedKeys = ["db_path","exchange","symbol","market_type","timeframe","initial_balance","position_size_pct","stake_usd","leverage","fee_rate","slippage_bps","spread_bps","funding_rate_per_interval","auto_download_days"];
      sharedKeys.forEach((key) => {
        if (form.elements[key] && optimizerForm.elements[key]) {
          form.elements[key].value = optimizerForm.elements[key].value;
        }
      });
      form.elements.ignore_position_size_pct.checked = optimizerForm.elements.ignore_position_size_pct.checked;
      form.elements.ignore_funding.checked = optimizerForm.elements.ignore_funding.checked;
      if (form.elements.combine_mode && optimizerForm.elements.combine_mode) {
        form.elements.combine_mode.value = row.combine_mode || optimizerForm.elements.combine_mode.value;
      }
      const stack = row.strategy_stack || "";
      if (form.elements.companion_buy_hold) {
        form.elements.companion_buy_hold.checked = stack.includes("buy_and_hold");
      }

      const utRow = row.optimizer_strategy === "ut_bot";
      if (optimizerForm.elements.optimizer_strategy) {
        optimizerForm.elements.optimizer_strategy.value = utRow ? "ut_bot" : "threshold";
        toggleOptimizerStrategyPanels();
        renderOptimizerFormLegPreview();
      }

      if (utRow) {
        form.elements.strategy_name.value = "ut-bot";
        toggleBacktestUtPanel();
        if (form.elements.ut_key_value && row.ut_key_value !== null && row.ut_key_value !== undefined) {
          form.elements.ut_key_value.value = String(row.ut_key_value);
        }
        if (form.elements.ut_atr_period && row.ut_atr_period !== null && row.ut_atr_period !== undefined) {
          form.elements.ut_atr_period.value = String(row.ut_atr_period);
        }
        if (form.elements.ut_lr_period && row.ut_lr_period !== null && row.ut_lr_period !== undefined) {
          form.elements.ut_lr_period.value = String(row.ut_lr_period);
        }
        if (form.elements.ut_exit_pct && row.ut_exit_pct !== null && row.ut_exit_pct !== undefined) {
          form.elements.ut_exit_pct.value = fractionToPercentPointsInput(row.ut_exit_pct);
        }
        if (form.elements.ut_exit_delay && row.ut_exit_delay !== null && row.ut_exit_delay !== undefined) {
          form.elements.ut_exit_delay.value = String(row.ut_exit_delay);
        }
        if (form.elements.ut_use_heikin_ashi) {
          form.elements.ut_use_heikin_ashi.checked = !!row.ut_use_heikin_ashi;
        }
      } else {
        form.elements.strategy_name.value = "threshold";
        toggleBacktestUtPanel();
        form.elements.entry_drop_pct.value = fractionToPercentPointsInput(row.entry_drop_pct);
        if (row.entry_rise_pct !== null && row.entry_rise_pct !== undefined) {
          form.elements.entry_rise_pct.value = fractionToPercentPointsInput(row.entry_rise_pct);
        }
      }

      form.elements.take_profit_pct.value = fractionToPercentPointsInput(row.take_profit_pct);
      form.elements.stop_loss_pct.value = fractionToPercentPointsInput(row.stop_loss_pct);
      form.elements.allow_short.checked = !!row.allow_short;
      tabs.forEach((b) => b.classList.toggle("active", b.dataset.tab === "backtest"));
      document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.tabPanel !== "backtest";
      });
      runBacktest();
    }

    function renderOptimizerCharts() {
      const rows = optimizerState.filteredRows.length ? optimizerState.filteredRows : optimizerState.rows;
      const cells = aggregateHeatmap(rows);
      const meta = optimizerState.metadata || {};
      const utMode = meta.optimizer_strategy === "ut_bot";
      drawHeatmap(document.querySelector("#opt-heatmap"), cells, {
        xLabel: utMode ? "UT key value" : "Entry drop (%)",
        yLabel: utMode ? "UT exit deviation (%)" : "Take profit (%)",
        formatXTick: utMode ? (value) => `${Number(value).toFixed(3)}` : undefined,
      });
      drawScatter(document.querySelector("#opt-scatter"),
        rows.map((row) => ({
          x: finiteValue(row.sharpe_ratio, 0),
          y: row.total_return_pct,
          r: 3 + Math.min(8, Math.max(0, row.pnl_r_squared || 0) * 8),
          color: row.total_return_pct >= 0 ? "rgba(4, 120, 87, 0.7)" : "rgba(180, 35, 24, 0.7)"
        })),
        { xLabel: "Sharpe", yLabel: "Total return (%)" }
      );
    }

    function aggregateHeatmap(rows) {
      const grouped = new Map();
      rows.forEach((row) => {
        let key;
        let xValue;
        let yValue;
        if (row.optimizer_strategy === "ut_bot") {
          xValue = Number(row.ut_key_value);
          yValue = Number(row.ut_exit_pct);
          key = `${xValue}|${yValue}|${row.strategy_stack || ""}|${row.combine_mode || ""}|ut`;
        } else {
          xValue = Number(row.entry_drop_pct);
          yValue = Number(row.take_profit_pct);
          key = `${xValue}|${yValue}|${row.strategy_stack || ""}|${row.combine_mode || ""}|th`;
        }
        const list = grouped.get(key) || [];
        list.push(row.total_return_pct);
        grouped.set(key, list);
      });
      const cells = [];
      grouped.forEach((values, key) => {
        const [x, y] = key.split("|").map(Number);
        const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
        cells.push({ x, y, value: avg });
      });
      return cells;
    }

    /* ===== Data tab ===== */
    document.querySelector("#inventory-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      refreshInventory();
    });

    document.querySelector("#download-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runDownload("/api/download");
    });

    document.querySelector("#run-sample").addEventListener("click", async () => {
      await runDownload("/api/sample-data");
    });

    document.querySelector("#funding-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runFundingFetch();
    });

    async function refreshInventory() {
      const values = readForm(document.querySelector("#inventory-form"));
      const query = new URLSearchParams({
        db_path: values.db_path,
        exchange: values.exchange,
        symbol: values.symbol,
        market_type: values.market_type,
        timeframes: "1h,4h,8h,12h"
      });
      const body = document.querySelector("#data-inventory-body");
      try {
        const payload = await getJson(`/api/data-summary?${query}`);
        if (!payload.rows.length) {
          body.innerHTML = `<tr><td colspan="4" class="muted">No stored data.</td></tr>`;
          return;
        }
        body.innerHTML = payload.rows.map((row) => `
          <tr>
            <td>${escapeHtml(row.timeframe)}</td>
            <td>${row.count}</td>
            <td>${row.first_candle ? new Date(row.first_candle).toLocaleString() : "-"}</td>
            <td>${row.last_candle ? new Date(row.last_candle).toLocaleString() : "-"}</td>
          </tr>
        `).join("");
      } catch (error) {
        body.innerHTML = `<tr><td colspan="4" class="bad">${escapeHtml(error.message)}</td></tr>`;
      }
    }

    async function runDownload(endpoint) {
      const values = readForm(document.querySelector("#download-form"));
      const dbInput = document.querySelector("#inventory-form").elements.db_path;
      const payload = { ...values, db_path: dbInput.value };
      setStatus("download-status", `Calling ${endpoint}...`);
      try {
        const json = await postJson(endpoint, payload);
        const summary = json.rows.map((row) => `${row.timeframe}: stored ${row.stored} (total ${row.count})`).join(" • ");
        setStatus("download-status", `Done. ${summary}`);
        await refreshInventory();
      } catch (error) {
        setStatus("download-status", error.message, true);
      }
    }

    async function runFundingFetch() {
      const values = readForm(document.querySelector("#funding-form"));
      const summary = document.querySelector("#funding-summary");
      summary.textContent = "Fetching Binance funding...";
      try {
        const query = new URLSearchParams({ symbol: values.symbol, days: values.days });
        const payload = await getJson(`/api/funding-rates?${query}`);
        summary.innerHTML = `
          <strong>${escapeHtml(payload.symbol)}</strong>: ${payload.sample_count} samples over ${payload.days} days.
          Average per-interval funding rate: <strong>${(payload.average_funding_rate * 100).toFixed(5)}%</strong>.
          Approx annualized cost paid by longs: <strong>${pct(payload.annualized_long_cost_pct)}</strong>.
        `;
        drawLineChart(
          document.querySelector("#funding-chart"),
          [{
            label: "Funding Rate",
            color: "#1d4ed8",
            points: payload.rows.map((row) => ({ x: row.funding_time, y: row.funding_rate * 10000 }))
          }],
          { formatY: "pct" }
        );
      } catch (error) {
        summary.innerHTML = `<span class="bad">${escapeHtml(error.message)}</span>`;
      }
    }

    wireGainEstimator();
    wireGridEditors();

    const btStrat = document.querySelector("#bt-strategy-select");
    if (btStrat) btStrat.addEventListener("change", toggleBacktestUtPanel);
    toggleBacktestUtPanel();

    const optStrat = document.querySelector("#opt-strategy-select");
    if (optStrat) {
      optStrat.addEventListener("change", () => {
        toggleOptimizerStrategyPanels();
        renderOptimizerFormLegPreview();
      });
    }
    toggleOptimizerStrategyPanels();

    renderOptimizerFormLegPreview();

    refreshInventory();
  </script>
</body>
</html>
"""
