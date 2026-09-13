"""
Risk Management Module.
Runs strictly before every Deriv `buy` call.
Enforces:
1. Max Daily Loss %
2. Max Concurrent Contracts
3. Max Stake Per Trade

Violations are ALWAYS explicitly rejected and logged to Firestore, never silently skipped.
"""

import logging
import datetime
from typing import Tuple, Dict, Any, Optional

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

logger = logging.getLogger("RiskManager")

DEFAULT_RISK_LIMITS = {
    "max_daily_loss_pct": 5.0,        # 5% max drawdown allowed per day
    "max_concurrent_contracts": 3,    # Max 3 simultaneously open trades
    "max_stake_per_trade": 25.0,      # Max $25 USD per individual contract
    "daily_loss_counter": 0.0,
    "open_contracts_count": 0,
    "starting_daily_balance": 1000.0, # Initial equity benchmark
    "last_reset_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "violations_history": [],
}

class RiskManager:
    def __init__(self, db: Optional[Any] = None):
        self.db = db

    def get_user_risk_state(self, uid: str) -> Dict[str, Any]:
        """Fetches current risk state document from Firestore users/{uid}/risk_state."""
        if not self.db:
            return DEFAULT_RISK_LIMITS.copy()

        doc_ref = self.db.collection("users").document(uid).collection("risk_state").document("current")
        doc = doc_ref.get()
        if not doc.exists:
            # Initialize default risk state
            initial_state = DEFAULT_RISK_LIMITS.copy()
            doc_ref.set(initial_state)
            return initial_state

        state = doc.to_dict() or DEFAULT_RISK_LIMITS.copy()
        
        # Check if daily reset is needed (UTC day change)
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if state.get("last_reset_date") != today:
            logger.info(f"Resetting daily loss counter for uid={uid} for new day: {today}")
            state["daily_loss_counter"] = 0.0
            state["last_reset_date"] = today
            doc_ref.update({
                "daily_loss_counter": 0.0,
                "last_reset_date": today,
            })
            
        return state

    def evaluate_pre_trade_risk(
        self,
        uid: str,
        proposed_stake: float,
        symbol: str,
        action: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Runs before every `buy` call.
        Returns:
            (True, None) if permitted.
            (False, rejection_reason) if a risk constraint is breached.
        """
        risk_state = self.get_user_risk_state(uid)

        max_stake = float(risk_state.get("max_stake_per_trade", 25.0))
        max_concurrent = int(risk_state.get("max_concurrent_contracts", 3))
        max_daily_loss_pct = float(risk_state.get("max_daily_loss_pct", 5.0))
        
        current_open_contracts = int(risk_state.get("open_contracts_count", 0))
        daily_loss = float(risk_state.get("daily_loss_counter", 0.0))
        starting_balance = float(risk_state.get("starting_daily_balance", 1000.0))
        
        current_loss_pct = (daily_loss / starting_balance * 100.0) if starting_balance > 0 else 0.0

        # Violation Check 1: Max Stake per trade
        if proposed_stake > max_stake:
            reason = f"Max Stake Exceeded: Proposed stake ${proposed_stake:.2f} exceeds limit of ${max_stake:.2f}"
            self._log_and_record_violation(uid, reason, proposed_stake, symbol, action, risk_state)
            return False, reason

        # Violation Check 2: Max Concurrent Contracts
        if current_open_contracts >= max_concurrent:
            reason = f"Max Concurrent Contracts Reached: Active={current_open_contracts}, Limit={max_concurrent}"
            self._log_and_record_violation(uid, reason, proposed_stake, symbol, action, risk_state)
            return False, reason

        # Violation Check 3: Max Daily Loss %
        if current_loss_pct >= max_daily_loss_pct:
            reason = f"Daily Loss Limit Breached: Current drawdown {current_loss_pct:.2f}% >= Allowed {max_daily_loss_pct:.2f}%"
            self._log_and_record_violation(uid, reason, proposed_stake, symbol, action, risk_state)
            return False, reason

        # Check if this trade's potential loss would push past the daily loss limit
        projected_loss_pct = ((daily_loss + proposed_stake) / starting_balance * 100.0) if starting_balance > 0 else 0.0
        if projected_loss_pct > (max_daily_loss_pct * 1.05):  # 5% buffer tolerance
            reason = f"Projected Drawdown Risk: Potential loss of ${proposed_stake:.2f} would breach daily loss ceiling of {max_daily_loss_pct:.2f}%"
            self._log_and_record_violation(uid, reason, proposed_stake, symbol, action, risk_state)
            return False, reason

        logger.info(f"Risk checks PASSED for uid={uid}: stake=${proposed_stake}, open={current_open_contracts}/{max_concurrent}")
        return True, None

    def _log_and_record_violation(
        self,
        uid: str,
        reason: str,
        stake: float,
        symbol: str,
        action: str,
        state: Dict[str, Any],
    ):
        """Logs the violation and records it atomically to Firestore users/{uid}/risk_state."""
        logger.warning(f"🚨 RISK REJECTION [uid={uid}]: {reason}")

        if not self.db:
            return

        violation_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "reason": reason,
            "stake": stake,
            "symbol": symbol,
            "action": action,
            "open_contracts": state.get("open_contracts_count", 0),
            "daily_loss_counter": state.get("daily_loss_counter", 0.0),
        }

        doc_ref = self.db.collection("users").document(uid).collection("risk_state").document("current")
        try:
            doc_ref.update({
                "violations_history": firestore.ArrayUnion([violation_entry]),
                "last_violation": violation_entry,
            })
        except Exception as e:
            logger.error(f"Failed to record violation to Firestore: {e}")

    def increment_open_contracts(self, uid: str):
        """Atomically increments the count of open contracts."""
        if not self.db:
            return
        doc_ref = self.db.collection("users").document(uid).collection("risk_state").document("current")
        doc_ref.update({"open_contracts_count": firestore.Increment(1)})

    def on_trade_settled(self, uid: str, profit: float):
        """
        Atomically decrements open contracts count and updates daily loss if trade was a loss.
        """
        if not self.db:
            return
        doc_ref = self.db.collection("users").document(uid).collection("risk_state").document("current")
        updates: Dict[str, Any] = {
            "open_contracts_count": firestore.Increment(-1)
        }
        if profit < 0:
            updates["daily_loss_counter"] = firestore.Increment(abs(profit))

        doc_ref.update(updates)
