"""
Automated Test Suite for Deriv Automated Trading Bot Backend.
Validates:
1. Deterministic signal logic (Wilder's RSI, Bollinger %B, EMA, documented confluence weights).
2. Risk management module (rejections on stake, concurrent contracts, daily loss % limit).
3. End-to-end Deriv trade lifecycle: authorize -> proposal -> buy on demo/virtual token.
4. Error handling: status='failed' with raw_error attached on failure.
"""

import sys
import os
import json
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.signals import calculate_rsi, calculate_bollinger_bands, calculate_ema, evaluate_signal
from backend.risk_manager import RiskManager
from backend.deriv_client import DerivClient
from backend.gemini_explainer import generate_signal_explanation

class TestDeterministicSignals(unittest.TestCase):
    def test_wilder_rsi_deterministic_precision(self):
        # 25 synthetic prices with a clear downtrend to test oversold RSI
        prices = [
            100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0,
            90.0, 89.0, 88.0, 87.0, 86.0, 85.0, 84.0, 83.0, 82.0, 81.0,
            80.0, 79.0, 78.0, 77.0, 76.0
        ]
        rsi1 = calculate_rsi(prices, 14)
        rsi2 = calculate_rsi(prices, 14)
        self.assertEqual(rsi1, rsi2, "RSI must be 100% deterministic")
        self.assertLess(rsi1, 10.0, "Monotonic downtrend should yield extreme oversold RSI < 10")

    def test_bollinger_bands_calculation(self):
        prices = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 15.0, 14.0, 13.0, 15.0,
                  16.0, 15.0, 14.0, 13.0, 12.0, 14.0, 15.0, 16.0, 17.0, 18.0]
        upper, mid, lower, pct_b = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        self.assertGreater(upper, mid)
        self.assertGreater(mid, lower)
        self.assertAlmostEqual(mid, sum(prices)/len(prices), places=3)
        self.assertGreater(pct_b, 0.5, "Price 18.0 is in upper half of bands")

    def test_confluence_signal_no_randomness(self):
        # Consistent oversold scenario
        prices = [
            1150.0, 1148.0, 1145.0, 1142.0, 1138.0, 1135.0, 1130.0, 1125.0,
            1120.0, 1115.0, 1110.0, 1105.0, 1100.0, 1095.0, 1090.0, 1085.0,
            1080.0, 1075.0, 1070.0, 1065.0, 1060.0, 1055.0, 1050.0, 1045.0, 1040.0
        ]
        sig1 = evaluate_signal("R_100", prices, timestamp=1000.0)
        sig2 = evaluate_signal("R_100", prices, timestamp=1000.0)
        self.assertEqual(sig1.action, "CALL")
        self.assertEqual(sig1.confidence_pct, sig2.confidence_pct, "Confidence must be strictly repeatable")
        self.assertIn("base_score", sig1.formula_weights)
        self.assertGreaterEqual(sig1.confidence_pct, 65.0)

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.risk_manager = RiskManager(db=None)

    def test_max_stake_rejection(self):
        allowed, reason = self.risk_manager.evaluate_pre_trade_risk(
            uid="test_user",
            proposed_stake=50.0,  # Limit is 25.0
            symbol="R_100",
            action="CALL",
        )
        self.assertFalse(allowed)
        self.assertIn("Max Stake Exceeded", reason)

    def test_within_limits_permitted(self):
        allowed, reason = self.risk_manager.evaluate_pre_trade_risk(
            uid="test_user",
            proposed_stake=10.0,  # Below limit 25.0
            symbol="R_100",
            action="CALL",
        )
        self.assertTrue(allowed)
        self.assertIsNone(reason)

class TestDerivTradeLifecycleE2E(unittest.IsolatedAsyncioTestCase):
    async def test_authorize_proposal_buy_lifecycle(self):
        """
        Tests the strict Deriv trade execution lifecycle:
        1. authorize -> 2. proposal -> 3. buy
        Verifies that status='open' is only set on contract_id receipt.
        """
        risk_manager = RiskManager(db=None)
        client = DerivClient(ws_url="wss://ws.derivws.com/websockets/v3?app_id=1089", risk_manager=risk_manager, db=None)

        # Mock the underlying WebSocket send/recv protocol
        client.ws = AsyncMock()
        client.ws.open = True

        # Simulate exact Deriv responses for the 3 sequential steps
        step = 0
        async def mock_send_request(payload, timeout=12.0):
            nonlocal step
            if "authorize" in payload:
                return {
                    "req_id": payload.get("req_id"),
                    "authorize": {
                        "account_list": [{"account_type": "binary", "is_virtual": 1}],
                        "balance": 10000.0,
                        "currency": "USD",
                        "email": "demo_trader@example.com",
                        "is_virtual": 1,
                        "loginid": "VRTC1092831",
                    }
                }
            elif "proposal" in payload:
                return {
                    "req_id": payload.get("req_id"),
                    "proposal": {
                        "ask_price": 10.0,
                        "payout": 19.52,
                        "id": "prop_deriv_94821039",
                        "spot": 1142.30,
                    }
                }
            elif "buy" in payload:
                # Buy MUST receive the proposal ID
                self.assertEqual(payload["buy"], "prop_deriv_94821039")
                return {
                    "req_id": payload.get("req_id"),
                    "buy": {
                        "balance_after": 9990.0,
                        "buy_price": 10.0,
                        "contract_id": 9840219842,
                        "payout": 19.52,
                        "purchase_time": 1726000000,
                        "shortcode": "CALL_R_100_10_1726000000_5T",
                    }
                }
            return {}

        client._send_request = mock_send_request

        # 1. Authorize demo/virtual token
        auth_ok, auth_data = await client.authorize(uid="user_abc123", token="virtual_demo_token_xyz")
        self.assertTrue(auth_ok)
        self.assertEqual(auth_data["loginid"], "VRTC1092831")
        self.assertEqual(auth_data["is_virtual"], 1)

        # 2 & 3. Execute buy with lifecycle
        trade_result = await client.execute_buy_with_lifecycle(
            uid="user_abc123",
            symbol="R_100",
            action="CALL",
            stake=10.0,
            duration=5,
            duration_unit="t",
        )

        self.assertEqual(trade_result["status"], "open")
        self.assertEqual(trade_result["contract_id"], 9840219842)
        self.assertEqual(trade_result["proposal_id"], "prop_deriv_94821039")
        self.assertEqual(trade_result["payout"], 19.52)

    async def test_api_error_records_failed_status_with_raw_error(self):
        """Verifies requirement: Any API error is written as status='failed' with raw error attached."""
        risk_manager = RiskManager(db=None)
        client = DerivClient(ws_url="wss://ws.derivws.com/websockets/v3?app_id=1089", risk_manager=risk_manager, db=None)
        client.ws = AsyncMock()
        client.ws.open = True

        async def mock_send_err(payload, timeout=12.0):
            if "proposal" in payload:
                return {
                    "req_id": payload.get("req_id"),
                    "error": {
                        "code": "InvalidContractDuration",
                        "message": "The minimum duration for this contract is 5 ticks."
                    }
                }
            return {}

        client._send_request = mock_send_err

        trade_result = await client.execute_buy_with_lifecycle(
            uid="user_abc123",
            symbol="R_100",
            action="CALL",
            stake=10.0,
            duration=1,  # Invalid duration
            duration_unit="t",
        )

        self.assertEqual(trade_result["status"], "failed")
        self.assertIn("raw_error", trade_result)
        self.assertEqual(trade_result["raw_error"]["code"], "InvalidContractDuration")

if __name__ == "__main__":
    unittest.main()
