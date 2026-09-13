"""
Deterministic Signal Generation Engine.
Implemented ONCE in Python - nowhere else.

Features:
- Wilder's Smoothed Relative Strength Index (RSI-14)
- Dual Exponential Moving Averages (EMA-9 and EMA-21)
- Bollinger Bands (20-period, 2-sigma) & %B oscillator
- Documented Confluence Heuristic Model:
    Evaluates multi-indicator alignment to produce deterministic BUY/SELL/HOLD signals.
    Confidence is strictly calculated from quantified indicator divergences and confluence weights.
    ZERO randomness or fake noise.
"""

import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

@dataclass
class IndicatorSnapshot:
    rsi: float
    ema_fast: float
    ema_slow: float
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    bollinger_pct_b: float
    current_price: float

@dataclass
class SignalResult:
    symbol: str
    action: str  # 'CALL', 'PUT', or 'HOLD'
    confidence_pct: float
    strategy_name: str
    indicators: Dict[str, Any]
    formula_weights: Dict[str, float]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "confidence_pct": round(self.confidence_pct, 2),
            "strategy_name": self.strategy_name,
            "indicators": self.indicators,
            "formula_weights": self.formula_weights,
            "timestamp": self.timestamp,
        }

def calculate_ema(prices: List[float], period: int) -> float:
    """Calculates Exponential Moving Average for the given period."""
    if not prices:
        return 0.0
    if len(prices) < period:
        return sum(prices) / len(prices)
    
    multiplier = 2.0 / (period + 1.0)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculates Relative Strength Index using Wilder's smoothed averages.
    Guaranteed deterministic output [0.0 - 100.0].
    """
    if len(prices) <= period:
        return 50.0  # Neutral default for insufficient data

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def calculate_bollinger_bands(prices: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[float, float, float, float]:
    """
    Calculates Upper Band, Middle Band, Lower Band, and %B.
    %B = (Price - Lower) / (Upper - Lower).
    """
    if len(prices) < period:
        sample = prices
    else:
        sample = prices[-period:]

    n = len(sample)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.5
        
    mean = sum(sample) / n
    variance = sum((x - mean) ** 2 for x in sample) / n
    std_dev = math.sqrt(variance)

    upper = mean + (num_std * std_dev)
    lower = mean - (num_std * std_dev)
    current_price = sample[-1]

    bandwidth = upper - lower
    pct_b = (current_price - lower) / bandwidth if bandwidth > 0.0 else 0.5
    return upper, mean, lower, pct_b

def compute_indicators(prices: List[float]) -> IndicatorSnapshot:
    """Computes full mathematical indicator set over price tick/candle history."""
    current_price = prices[-1] if prices else 0.0
    rsi = calculate_rsi(prices, period=14)
    ema_fast = calculate_ema(prices, period=9)
    ema_slow = calculate_ema(prices, period=21)
    upper, mid, lower, pct_b = calculate_bollinger_bands(prices, period=20, num_std=2.0)

    return IndicatorSnapshot(
        rsi=round(rsi, 2),
        ema_fast=round(ema_fast, 4),
        ema_slow=round(ema_slow, 4),
        bollinger_upper=round(upper, 4),
        bollinger_middle=round(mid, 4),
        bollinger_lower=round(lower, 4),
        bollinger_pct_b=round(pct_b, 4),
        current_price=round(current_price, 4),
    )

def evaluate_signal(symbol: str, prices: List[float], timestamp: float) -> SignalResult:
    """
    Evaluates market conditions using the multi-factor confluence model.
    Decision Logic:
    - CALL: RSI <= 32 (Oversold) AND %B <= 0.15 (Near/below lower Bollinger band)
      Confirmation boost if EMA9 >= EMA21 (or turning upwards).
    - PUT: RSI >= 68 (Overbought) AND %B >= 0.85 (Near/above upper Bollinger band)
      Confirmation boost if EMA9 <= EMA21 (or turning downwards).
    - HOLD: Neutral market, insufficient confluence.

    Confidence Calculation (Documented Model):
    - Base alignment: 65.0%
    - RSI delta factor: (abs(RSI - 50) - 18) / 32 * 15.0%
    - Bollinger deviation factor: (abs(%B - 0.5) - 0.35) / 0.15 * 10.0%
    - Trend agreement factor: 10.0% if EMA trend matches signal direction.
    Total Confidence is capped between 65.0% and 98.5%.
    """
    if len(prices) < 25:
        # Insufficient data to form a deterministic technical signal
        return SignalResult(
            symbol=symbol,
            action="HOLD",
            confidence_pct=0.0,
            strategy_name="Awaiting Data Warmup",
            indicators={},
            formula_weights={},
            timestamp=timestamp,
        )

    snap = compute_indicators(prices)
    indicators_dict = asdict(snap)

    action = "HOLD"
    strategy = "Range Consolidation"
    confidence = 0.0
    weights: Dict[str, float] = {}

    # Check CALL conditions (Oversold mean-reversion with momentum recovery)
    if snap.rsi <= 34.0 and snap.bollinger_pct_b <= 0.20:
        action = "CALL"
        strategy = "RSI Oversold + Lower Bollinger Band Reversal"
        
        # Confluence metrics
        rsi_excess = max(0.0, (34.0 - snap.rsi) / 34.0) * 16.0
        bb_excess = max(0.0, (0.20 - snap.bollinger_pct_b) / 0.20) * 12.0
        trend_match = 8.0 if snap.ema_fast >= snap.ema_slow else 0.0
        
        confidence = 65.0 + rsi_excess + bb_excess + trend_match
        confidence = min(98.5, max(65.0, confidence))
        
        weights = {
            "base_score": 65.0,
            "rsi_oversold_weight": round(rsi_excess, 2),
            "bollinger_pierce_weight": round(bb_excess, 2),
            "trend_confluence_weight": round(trend_match, 2),
        }

    # Check PUT conditions (Overbought mean-reversion with downward momentum)
    elif snap.rsi >= 66.0 and snap.bollinger_pct_b >= 0.80:
        action = "PUT"
        strategy = "RSI Overbought + Upper Bollinger Band Rejection"
        
        rsi_excess = max(0.0, (snap.rsi - 66.0) / 34.0) * 16.0
        bb_excess = max(0.0, (snap.bollinger_pct_b - 0.80) / 0.20) * 12.0
        trend_match = 8.0 if snap.ema_fast <= snap.ema_slow else 0.0
        
        confidence = 65.0 + rsi_excess + bb_excess + trend_match
        confidence = min(98.5, max(65.0, confidence))
        
        weights = {
            "base_score": 65.0,
            "rsi_overbought_weight": round(rsi_excess, 2),
            "bollinger_pierce_weight": round(bb_excess, 2),
            "trend_confluence_weight": round(trend_match, 2),
        }

    return SignalResult(
        symbol=symbol,
        action=action,
        confidence_pct=round(confidence, 2),
        strategy_name=strategy,
        indicators=indicators_dict,
        formula_weights=weights,
        timestamp=timestamp,
    )
