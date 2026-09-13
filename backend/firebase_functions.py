"""
Firebase Cloud Functions (Callable).
The ONLY client-facing surface to the trading backend.
Contains EXACTLY three functions:
1. requestTrade
2. pauseBot
3. resumeBot

No other client-to-backend path exists.
"""

import asyncio
import datetime
import logging
from typing import Any, Dict
from firebase_functions import https_fn, options
from backend.config import get_firestore_client, get_deriv_token_from_secret_manager, DERIV_WS_URL
from backend.risk_manager import RiskManager
from backend.deriv_client import DerivClient

logger = logging.getLogger("FirebaseCallableFunctions")

def _get_authenticated_uid(req: https_fn.CallableRequest) -> str:
    """Verifies Firebase Auth token; raises HTTPS exception if unauthenticated."""
    if not req.auth or not req.auth.uid:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.UNAUTHENTICATED,
            message="User must be authenticated with Firebase Auth to invoke bot commands."
        )
    return req.auth.uid

@https_fn.on_call(cors=options.CorsOptions(cors_origins=["*"], max_age_seconds=3600))
def request_trade(req: https_fn.CallableRequest) -> Dict[str, Any]:
    """
    Client Callable 1: requestTrade
    Triggers an on-demand trade execution lifecycle on the backend.
    """
    uid = _get_authenticated_uid(req)
    data = req.data or {}
    
    symbol = data.get("symbol", "R_100")
    contract_type = data.get("contract_type", "CALL").upper()
    stake = float(data.get("stake", 10.0))
    duration = int(data.get("duration", 5))
    duration_unit = data.get("duration_unit", "t")

    token = get_deriv_token_from_secret_manager(uid)
    if not token:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
            message="Deriv account not linked or token missing from Secret Manager."
        )

    db = get_firestore_client()
    risk_manager = RiskManager(db=db)
    client = DerivClient(ws_url=DERIV_WS_URL, risk_manager=risk_manager, db=db)

    async def _run():
        await client.connect()
        authorized, _ = await client.authorize(uid=uid, token=token)
        if not authorized:
            await client.close()
            raise https_fn.HttpsError(
                code=https_fn.FunctionsErrorCode.UNAUTHENTICATED,
                message="Deriv authorization rejected user token."
            )

        result = await client.execute_buy_with_lifecycle(
            uid=uid,
            symbol=symbol,
            action=contract_type,
            stake=stake,
            duration=duration,
            duration_unit=duration_unit,
        )
        await client.close()
        return result

    try:
        trade_result = asyncio.run(_run())
        return {
            "success": trade_result.get("status") == "open",
            "trade": trade_result,
        }
    except https_fn.HttpsError:
        raise
    except Exception as e:
        logger.error(f"Error handling requestTrade: {e}")
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INTERNAL,
            message=str(e)
        )

@https_fn.on_call(cors=options.CorsOptions(cors_origins=["*"], max_age_seconds=3600))
def pause_bot(req: https_fn.CallableRequest) -> Dict[str, Any]:
    """
    Client Callable 2: pauseBot
    Atomically pauses execution for the calling user.
    """
    uid = _get_authenticated_uid(req)
    db = get_firestore_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        user_ref = db.collection("users").document(uid)
        user_ref.set({
            "bot_state": {
                "status": "PAUSED",
                "last_modified": now_iso,
                "paused_by": "client_callable",
            }
        }, merge=True)
        
        logger.info(f"Bot PAUSED for uid={uid}")
        return {"success": True, "bot_status": "PAUSED", "timestamp": now_iso}
    except Exception as e:
        logger.error(f"Error in pauseBot: {e}")
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.INTERNAL, message=str(e))

@https_fn.on_call(cors=options.CorsOptions(cors_origins=["*"], max_age_seconds=3600))
def resume_bot(req: https_fn.CallableRequest) -> Dict[str, Any]:
    """
    Client Callable 3: resumeBot
    Atomically resumes autonomous execution for the calling user.
    """
    uid = _get_authenticated_uid(req)
    db = get_firestore_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        user_ref = db.collection("users").document(uid)
        user_ref.set({
            "bot_state": {
                "status": "RUNNING",
                "last_modified": now_iso,
                "resumed_by": "client_callable",
            }
        }, merge=True)
        
        logger.info(f"Bot RESUMED for uid={uid}")
        return {"success": True, "bot_status": "RUNNING", "timestamp": now_iso}
    except Exception as e:
        logger.error(f"Error in resumeBot: {e}")
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.INTERNAL, message=str(e))
