"""
Gemini Technical Rationale Generator.
Server-side only.
CRITICAL MANDATE:
- Called AFTER deterministic signal has already fired.
- Generates a short plain-English technical breakdown of the indicators for user auditability.
- Gemini NEVER influences or modifies the trade decision.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("GeminiExplainer")

def generate_signal_explanation(
    symbol: str,
    action: str,
    confidence_pct: float,
    strategy_name: str,
    indicators: Dict[str, Any]
) -> Optional[str]:
    """
    Generates a concise plain-English explanation of the mathematical technical setup.
    Stored under users/{uid}/signals/{id}/gemini_explanation.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Deterministic fallback explanation if offline or key not in environment
    rsi = indicators.get("rsi", 50.0)
    pct_b = indicators.get("bollinger_pct_b", 0.5)
    ema_fast = indicators.get("ema_fast", 0.0)
    ema_slow = indicators.get("ema_slow", 0.0)
    current_price = indicators.get("current_price", 0.0)

    fallback_text = (
        f"Deterministic signal '{action}' triggered for {symbol} at spot {current_price}. "
        f"RSI-14 is at {rsi} combined with Bollinger %B at {pct_b:.2f}, indicating "
        f"{'an oversold mean-reversion rebound' if action == 'CALL' else 'an overbought exhaustion rejection'} "
        f"with EMA-9 ({ema_fast}) aligning with EMA-21 ({ema_slow}). Model confluence: {confidence_pct}%."
    )

    if not api_key:
        logger.info("GEMINI_API_KEY not found in environment, using deterministic technical rationale.")
        return fallback_text

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
You are an algorithmic quantitative analyst reviewing an automated technical indicator trigger.
Produce a concise, professional 2-sentence plain-English explanation of this signal for the trader:

Asset: {symbol}
Action: {action}
Strategy: {strategy_name}
Deterministic Confluence Score: {confidence_pct}%
Indicators:
- RSI (14 periods): {rsi} (Range 0-100, <34 oversold, >66 overbought)
- Bollinger Bands %B: {pct_b} (<0.20 near lower band, >0.80 near upper band)
- EMA 9: {ema_fast} vs EMA 21: {ema_slow}
- Current Spot: {current_price}

Do not provide financial advice. Focus purely on technical indicator confluence.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            cleaned = response.text.strip()
            logger.info("Generated Gemini server-side technical explanation successfully.")
            return cleaned
        return fallback_text
    except Exception as e:
        logger.warning(f"Gemini API call encountered error: {e}. Falling back to deterministic rationale.")
        return fallback_text
