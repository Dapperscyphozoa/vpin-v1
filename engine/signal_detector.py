"""
vpin-v1 — Volume-synchronized PIN (toxicity).
Approximates VPIN from 1m candle aggressor flow inferred from close vs mid.
Fires reversal at swing extremes when VPIN > threshold AND direction
opposes price trend.

Note: true tick VPIN needs trade-by-trade data. This bar-aggregate proxy
trades off precision for free data. Tune VPIN_THRESHOLD aggressively.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Optional
from .config import STRATEGY_PARAMS, TRADE_PARAMS


def _aggressor_vol(o, h, l, c, v):
    """Estimate buy/sell aggressor split from candle anatomy."""
    rng = h - l
    if rng <= 0: return v * 0.5, v * 0.5
    buy_frac = (c - l) / rng
    sell_frac = (h - c) / rng
    s = buy_frac + sell_frac
    if s == 0: return v * 0.5, v * 0.5
    return v * (buy_frac / s), v * (sell_frac / s)


def calc_atr(highs, lows, closes, period: int = 14) -> float:
    h_s = pd.Series(highs); l_s = pd.Series(lows); pc = pd.Series(closes).shift(1)
    tr = pd.concat([h_s - l_s, (h_s - pc).abs(), (l_s - pc).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def evaluate_latest_bar(df: pd.DataFrame) -> Optional[dict]:
    WIN = STRATEGY_PARAMS.get("vpin_window", 50)
    THRESH = STRATEGY_PARAMS.get("vpin_threshold", 0.55)
    SWING_LB = STRATEGY_PARAMS.get("swing_lookback", 24)
    EXT_PCT = STRATEGY_PARAMS.get("extreme_proximity_pct", 0.005)
    if df is None or len(df) < WIN + 5: return None

    opens = df["open"].values; highs = df["high"].values
    lows = df["low"].values; closes = df["close"].values
    vols = df["volume"].values if "volume" in df.columns else np.ones(len(df))

    buy_v = np.zeros(len(df)); sell_v = np.zeros(len(df))
    for i in range(len(df)):
        b, s = _aggressor_vol(opens[i], highs[i], lows[i], closes[i], vols[i])
        buy_v[i] = b; sell_v[i] = s

    win_buy = float(buy_v[-WIN:].sum()); win_sell = float(sell_v[-WIN:].sum())
    win_tot = win_buy + win_sell
    if win_tot <= 0: return None
    vpin = abs(win_buy - win_sell) / win_tot
    if vpin < THRESH: return None
    flow_dir = 1 if win_buy > win_sell else -1   # net buyer = +1

    last_c = float(closes[-1])
    sw_hi = float(np.max(highs[-SWING_LB:-1]))
    sw_lo = float(np.min(lows[-SWING_LB:-1]))

    is_long = None
    if last_c >= sw_hi * (1 - EXT_PCT) and flow_dir == -1:
        # at high, net selling = SHORT
        is_long = False
    elif last_c <= sw_lo * (1 + EXT_PCT) and flow_dir == 1:
        is_long = True
    else:
        return None

    atr = calc_atr(highs, lows, closes, TRADE_PARAMS["atr_period"])
    if not atr or atr <= 0: return None
    sl_m = TRADE_PARAMS["sl_atr_mult"]; tp_m = TRADE_PARAMS["tp_atr_mult"]
    if is_long: sl_p = last_c - sl_m * atr; tp_p = last_c + tp_m * atr
    else:       sl_p = last_c + sl_m * atr; tp_p = last_c - tp_m * atr

    return {
        "fire_ts": df.index[-1], "ref_price": last_c, "atr": atr,
        "trade_side": "B" if is_long else "A", "is_long": is_long,
        "sl_px": float(sl_p), "tp_px": float(tp_p),
        "max_hold_bars": TRADE_PARAMS["max_hold_bars"],
        "fire_reason": f"vpin_{vpin:.2f}_flow_{flow_dir}",
        "raw_direction": "LONG" if is_long else "SHORT",
        "fade_direction": "LONG" if is_long else "SHORT",
        "vpin": float(vpin), "flow_dir": int(flow_dir),
    }
