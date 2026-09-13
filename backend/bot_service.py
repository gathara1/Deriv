"""
Persistent Cloud Run Trading Bot Service.
Runs 24/7 in Python independently of any client app.
Holding Deriv WebSocket connection, evaluating deterministic signals,
enforcing risk checks, and writing state to Firestore via Admin SDK.
"""

import os
import uuid
import asyncio
import logging
import datetime
from typing import Dict, List
from backend.config import DERIV_WS_URL, get_firestore_client, get_deriv_token_from_secret_manager
from backend.signals import evaluate_signal
from backend.gemini_explainer import generate_signal_explanation
from backend.risk_manager import RiskManager
from backend.deriv_client import DerivClient

logger = logging.getLogger("BotService")

class TradingBotService:
    def __init__(self):
        self.db = None
        try:
            self.db = get_firestore_client()
        except Exception as e:
            logger.warning(f"Running without remote Firestore (testing mode): {e}")

        self.risk_manager = RiskManager(db=self.db)
        self.deriv_client = DerivClient(ws_url=DERIV_WS_URL, risk_manager=self.risk_manager, db=self.db)
        self.is_running = True
        
        # In-memory price buffers for technical analysis calculations
        # Symbol -> list of recent tick prices (e.g. Volatility 100 (1s) Index)
        self.price_history: Dict[str, List[float]] = {
            "R_100": [
                1140.2, 1140.8, 1139.5, 1138.9, 1137.4, 1136.2, 1135.0, 1133.8,
                1132.5, 1131.2, 1130.0, 1128.5, 1127.1, 1125.8, 1124.0, 1122.5,
                1121.0, 1119.5, 1118.2, 1117.0, 1116.5, 1116.0, 1115.8, 1115.2, 1115.0
            ],
            "1HZ100V": [
                2450.1, 2451.0, 2449.5, 2448.2, 2447.0, 2445.5, 2444.2, 2443.0,
                2441.5, 2440.0, 2438.5, 2437.0, 2435.8, 2434.2, 2433.0, 2431.5,
                2430.0, 2428.5, 2427.0, 2426.0, 2425.5, 2425.0, 2424.8, 2424.2, 2424.0
            ]
        }

    async def start(self):
        """Starts the persistent background bot service."""
        logger.info("Starting Deriv 24/7 Cloud Run Persistent Bot Engine...")
        await self.deriv_client.connect()

        # Main orchestration loop
        while self.is_running:
            try:
                await self._process_active_users_cycle()
            except Exception as e:
                logger.error(f"Error in bot processing cycle: {e}")
            
            # Non-blocking cycle interval (evaluates every 15 seconds)
            await asyncio.sleep(15)

    async def _process_active_users_cycle(self):
        """Checks registered users and executes autonomous deterministic trading."""
        active_uids = []
        if self.db:
            try:
                users_ref = self.db.collection("users")
                # Look for users whose bot status is 'RUNNING'
                query = users_ref.where("bot_state.status", "==", "RUNNING")
                for doc in query.stream():
                    active_uids.append(doc.id)
            except Exception as e:
                logger.warning(f"Firestore query for active users skipped or failed: {e}")

        # Fallback to test demo user if running standalone
        if not active_uids:
            active_uids = [os.environ.get("DERIV_DEMO_UID", "demo_user_uid")]

        for uid in active_uids:
            await self._run_evaluation_for_user(uid)

    async def _run_evaluation_for_user(self, uid: str):
        """Evaluates signals and executes lifecycle for a single user."""
        token = get_deriv_token_from_secret_manager(uid)
        if not token:
            logger.debug(f"No Deriv token found in Secret Manager for uid={uid}")
            return

        # Ensure authorized
        auth_success, _ = await self.deriv_client.authorize(uid=uid, token=token)
        if not auth_success:
            logger.warning(f"Could not authorize Deriv session for uid={uid}")
            return

        # Scan monitored symbols
        for symbol, prices in self.price_history.items():
            now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
            signal_result = evaluate_signal(symbol=symbol, prices=prices, timestamp=now_ts)

            if signal_result.action in ("CALL", "PUT"):
                logger.info(
                    f"🎯 Deterministic Signal fired: {symbol} -> {signal_result.action} "
                    f"({signal_result.confidence_pct}% confidence via {signal_result.strategy_name})"
                )

                # Optional Server-side Gemini plain-English technical explanation
                gemini_explanation = generate_signal_explanation(
                    symbol=symbol,
                    action=signal_result.action,
                    confidence_pct=signal_result.confidence_pct,
                    strategy_name=signal_result.strategy_name,
                    indicators=signal_result.indicators,
                )

                # Save signal to Firestore users/{uid}/signals/{id}
                signal_id = str(uuid.uuid4())
                signal_doc = signal_result.to_dict()
                signal_doc["id"] = signal_id
                signal_doc["gemini_explanation"] = gemini_explanation

                if self.db:
                    self.db.collection("users").document(uid).collection("signals").document(signal_id).set(signal_doc)

                # Execute Deriv Trade Lifecycle (subject to pre-trade risk checks)
                default_stake = 10.0
                await self.deriv_client.execute_buy_with_lifecycle(
                    uid=uid,
                    symbol=symbol,
                    action=signal_result.action,
                    stake=default_stake,
                    duration=5,
                    duration_unit="t",
                )

if __name__ == "__main__":
    bot = TradingBotService()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot service stopped by administrator.")
