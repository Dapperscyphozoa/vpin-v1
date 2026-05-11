# vpin-v1 — DEPRECATED

**Status:** suspended on Render 2026-05-11.

## Why

Bar-aggregate VPIN proxy (estimating buy/sell aggressor split from candle
anatomy) is fundamentally too crude:

- Original mechanic: `buy_frac = (close - low) / (high - low)`.
  This is a *guess* — not actual aggressor flow.
- Backtest results: 0 fires at v1 defaults; aggressive sweep got
  43 trades / PF 0.67 / sumR -1.73 over 60d. Losing strategy.
- HL `recentTrades` endpoint returns only last 10 trades — not historicisable
  for proper VPIN computation, and even live aggregation would need a
  background trade-tape collector.

## What's needed for a real VPIN engine

1. Background collector: subscribe to HL websocket `trades` channel,
   aggregate trade volume per side per bucket
2. Persist 100+ bars of historical trade-tape data
3. Rewrite signal_detector to read from the trade-tape, not candle anatomy

This is a 2-day build with persistent storage + websocket plumbing.
Not justified yet — push the existing 3 promote-candidates first.

## Replacement candidates (future engines)

- `cvd-divergence-v1` — Cumulative Volume Delta divergence (related, simpler)
- `orderbook-imbalance-v1` — L2 imbalance via HL `l2Book` (which IS free)
- Build only if backtest research confirms edge.

## Repo retained

Keeping the repo + code so the strategy stays diff-able when we revisit.
