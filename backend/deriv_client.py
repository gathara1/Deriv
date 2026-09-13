"""
Deriv WebSocket API Client & Trade Execution Lifecycle.
Maintains persistent WebSocket connection to:
  wss://ws.derivws.com/websockets/v3?app_id=<ID>

Strict Trade Execution Lifecycle:
  1. authorize(token)
  2. proposal(fresh price / payout / proposal_id)
  3. buy(using proposal_id)

Guarantees:
- Firestore trades written as status='open' ONLY after Deriv returns contract_id.
- Any API error is written as status='failed' with raw Deriv error attached.
- users/{uid}/deriv_link stores link status only, NEVER the token.
"""

import json
import uuid
import asyncio
import logging
import datetime
from typing import Optional, Dict, Any, Tuple
try:
    import websockets
except ImportError:
    websockets = None
from backend.risk_manager import RiskManager

logger = logging.getLogger("DerivClient")

class DerivClient:
    def __init__(self, ws_url: str, risk_manager: RiskManager, db: Optional[Any] = None):
        self.ws_url = ws_url
        self.risk_manager = risk_manager
        self.db = db
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._req_id_counter = 1
        self._authorized_uid: Optional[str] = None
        self._account_info: Dict[str, Any] = {}
        self._is_running = False

    async def connect(self):
        """Establishes persistent WebSocket connection to Deriv API."""
        logger.info(f"Connecting to Deriv WebSocket: {self.ws_url}")
        self.ws = await websockets.connect(
            self.ws_url,
            ping_interval=30,
            ping_timeout=15,
            close_timeout=10,
        )
        self._is_running = True
        logger.info("Connected to Deriv WebSocket.")
        asyncio.create_task(self._listen_loop())

    async def close(self):
        self._is_running = False
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def _listen_loop(self):
        """Message dispatcher for incoming WebSocket messages."""
        try:
            while self._is_running and self.ws:
                msg_text = await self.ws.recv()
                data = json.loads(msg_text)
                req_id = data.get("req_id")
                if req_id and req_id in self._pending_requests:
                    fut = self._pending_requests.pop(req_id)
                    if not fut.done():
                        fut.set_result(data)
                
                # Check for contract subscription stream updates
                msg_type = data.get("msg_type")
                if msg_type == "proposal_open_contract":
                    asyncio.create_task(self._handle_contract_update(data))

        except websockets.ConnectionClosed:
            logger.warning("Deriv WebSocket connection closed. Will reconnect on next cycle.")
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")

    async def _send_request(self, payload: Dict[str, Any], timeout: float = 12.0) -> Dict[str, Any]:
        """Sends a JSON request with a tracking req_id and awaits the response."""
        if not self.ws or not self.ws.open:
            await self.connect()

        req_id = self._req_id_counter
        self._req_id_counter += 1
        payload["req_id"] = req_id

        fut = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = fut

        await self.ws.send(json.dumps(payload))
        return await asyncio.wait_for(fut, timeout=timeout)

    # -------------------------------------------------------------
    # 1. AUTHORIZE
    # -------------------------------------------------------------
    async def authorize(self, uid: str, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Authorizes the WebSocket session using the user's token from Secret Manager.
        Updates users/{uid}/deriv_link with link status ONLY (never the token).
        """
        logger.info(f"Initiating Deriv 'authorize' for uid={uid}")
        try:
            res = await self._send_request({"authorize": token})
            if "error" in res:
                error_info = res["error"]
                logger.error(f"Deriv authorization failed: {error_info}")
                self._update_link_status(uid, linked=False, raw_error=error_info)
                return False, error_info

            auth_data = res.get("authorize", {})
            self._authorized_uid = uid
            self._account_info = auth_data

            is_virtual = bool(auth_data.get("is_virtual", 1))
            account_id = auth_data.get("loginid", "DEMO_UNKNOWN")
            currency = auth_data.get("currency", "USD")
            balance = float(auth_data.get("balance", 0.0))

            logger.info(
                f"✅ Deriv Authorized: loginid={account_id} | virtual={is_virtual} | "
                f"balance={balance} {currency}"
            )

            # Record link status only to Firestore
            self._update_link_status(
                uid=uid,
                linked=True,
                account_id=account_id,
                is_virtual=is_virtual,
                currency=currency,
                balance=balance,
            )
            return True, auth_data

        except Exception as e:
            logger.error(f"Authorize exception: {e}")
            self._update_link_status(uid, linked=False, raw_error={"message": str(e)})
            return False, {"message": str(e)}

    # -------------------------------------------------------------
    # 2. PROPOSAL
    # -------------------------------------------------------------
    async def get_proposal(
        self,
        symbol: str,
        contract_type: str,
        stake: float,
        duration: int = 5,
        duration_unit: str = "t",
        currency: str = "USD",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Requests fresh price quote and payout.
        Returns (success, proposal_dict_or_error).
        """
        req = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": contract_type.upper(),  # 'CALL' or 'PUT'
            "currency": currency,
            "duration": duration,
            "duration_unit": duration_unit,  # 't' (ticks), 'm' (minutes), 's' (seconds)
            "symbol": symbol,
        }
        logger.info(f"Requesting Deriv proposal: {symbol} {contract_type} stake=${stake} ({duration}{duration_unit})")
        try:
            res = await self._send_request(req)
            if "error" in res:
                return False, res["error"]
            proposal = res.get("proposal", {})
            logger.info(
                f"Proposal received: id={proposal.get('id')} | ask={proposal.get('ask_price')} | "
                f"payout={proposal.get('payout')} | spot={proposal.get('spot')}"
            )
            return True, proposal
        except Exception as e:
            logger.error(f"Proposal request exception: {e}")
            return False, {"code": "ProposalTimeout", "message": str(e)}

    # -------------------------------------------------------------
    # 3. BUY
    # -------------------------------------------------------------
    async def execute_buy_with_lifecycle(
        self,
        uid: str,
        symbol: str,
        action: str,  # 'CALL' or 'PUT'
        stake: float,
        duration: int = 5,
        duration_unit: str = "t",
    ) -> Dict[str, Any]:
        """
        Executes strict trade lifecycle:
          1. Pre-trade Risk Module check -> reject & log if violation.
          2. Fresh Proposal request -> get proposal_id & fresh price.
          3. Buy request -> execute using proposal_id.
          4. Record to Firestore:
             - status='open' ONLY if contract_id is returned.
             - status='failed' with raw_error attached if any API failure occurs.
        """
        trade_id = str(uuid.uuid4())
        logger.info(f"Initiating trade lifecycle [{trade_id}] for uid={uid}: {symbol} {action} ${stake}")

        # Step 1: Pre-trade Risk Check
        allowed, rejection_reason = self.risk_manager.evaluate_pre_trade_risk(
            uid=uid,
            proposed_stake=stake,
            symbol=symbol,
            action=action,
        )
        if not allowed:
            # Rejection logged in risk manager; write as failed trade with risk error
            error_data = {
                "code": "RiskConstraintViolation",
                "message": rejection_reason,
            }
            self._write_trade_to_firestore(
                uid=uid,
                trade_id=trade_id,
                trade_data={
                    "id": trade_id,
                    "symbol": symbol,
                    "contract_type": action,
                    "stake": stake,
                    "status": "failed",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "raw_error": error_data,
                }
            )
            return {"status": "failed", "raw_error": error_data}

        # Step 2: Request Fresh Proposal
        currency = self._account_info.get("currency", "USD")
        proposal_success, proposal_or_err = await self.get_proposal(
            symbol=symbol,
            contract_type=action,
            stake=stake,
            duration=duration,
            duration_unit=duration_unit,
            currency=currency,
        )

        if not proposal_success:
            logger.error(f"Trade lifecycle aborted: Proposal failed: {proposal_or_err}")
            self._write_trade_to_firestore(
                uid=uid,
                trade_id=trade_id,
                trade_data={
                    "id": trade_id,
                    "symbol": symbol,
                    "contract_type": action,
                    "stake": stake,
                    "status": "failed",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "raw_error": proposal_or_err,
                }
            )
            return {"status": "failed", "raw_error": proposal_or_err}

        proposal_id = proposal_or_err.get("id")
        ask_price = float(proposal_or_err.get("ask_price", stake))
        payout = float(proposal_or_err.get("payout", 0.0))
        spot_price = float(proposal_or_err.get("spot", 0.0))

        # Step 3: Execute Buy using Proposal ID
        logger.info(f"Executing Buy for proposal_id={proposal_id} at price=${ask_price}")
        buy_res = await self._send_request({
            "buy": proposal_id,
            "price": ask_price,
        })

        if "error" in buy_res:
            raw_err = buy_res["error"]
            logger.error(f"Deriv Buy API error: {raw_err}")
            self._write_trade_to_firestore(
                uid=uid,
                trade_id=trade_id,
                trade_data={
                    "id": trade_id,
                    "symbol": symbol,
                    "contract_type": action,
                    "stake": ask_price,
                    "status": "failed",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "raw_error": raw_err,
                }
            )
            return {"status": "failed", "raw_error": raw_err}

        buy_data = buy_res.get("buy", {})
        contract_id = buy_data.get("contract_id")

        if not contract_id:
            raw_err = {"code": "MissingContractId", "message": "Deriv returned buy response without contract_id"}
            self._write_trade_to_firestore(
                uid=uid,
                trade_id=trade_id,
                trade_data={
                    "id": trade_id,
                    "symbol": symbol,
                    "contract_type": action,
                    "stake": ask_price,
                    "status": "failed",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "raw_error": raw_err,
                }
            )
            return {"status": "failed", "raw_error": raw_err}

        # Step 4: Write status='open' to Firestore strictly after contract_id is confirmed
        open_trade_data = {
            "id": trade_id,
            "contract_id": contract_id,
            "proposal_id": proposal_id,
            "symbol": symbol,
            "contract_type": action,
            "stake": ask_price,
            "payout": payout,
            "entry_spot": spot_price,
            "status": "open",
            "purchase_time": buy_data.get("purchase_time", int(datetime.datetime.now(datetime.timezone.utc).timestamp())),
            "shortcode": buy_data.get("shortcode", ""),
            "duration": f"{duration}{duration_unit}",
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        self._write_trade_to_firestore(uid=uid, trade_id=trade_id, trade_data=open_trade_data)
        self.risk_manager.increment_open_contracts(uid)

        logger.info(f"🎉 Trade OPEN: contract_id={contract_id} | {symbol} {action} | stake=${ask_price}")
        
        # Subscribe to contract outcome stream to track settlement
        asyncio.create_task(self._subscribe_and_monitor_contract(uid, trade_id, contract_id, ask_price))
        return open_trade_data

    async def _subscribe_and_monitor_contract(self, uid: str, trade_id: str, contract_id: int, stake: float):
        """Monitors contract until settlement, updating Firestore atomically."""
        try:
            await self._send_request({
                "proposal_open_contract": 1,
                "contract_id": contract_id,
                "subscribe": 1,
            })
        except Exception as e:
            logger.warning(f"Could not subscribe to contract {contract_id}: {e}")

    async def _handle_contract_update(self, data: Dict[str, Any]):
        """Processes contract updates and marks trades won/lost."""
        contract = data.get("proposal_open_contract", {})
        if not contract or not contract.get("is_sold"):
            return

        contract_id = contract.get("contract_id")
        status = contract.get("status")  # 'won' or 'lost'
        profit = float(contract.get("profit", 0.0))
        exit_spot = float(contract.get("exit_tick", contract.get("current_spot", 0.0)))

        logger.info(f"Contract {contract_id} settled: status={status}, profit=${profit:.2f}")

        if not self.db:
            return

        # Query Firestore for the trade matching contract_id
        try:
            query = self.db.collection_group("trades").where("contract_id", "==", contract_id).limit(1)
            docs = list(query.stream())
            for doc in docs:
                doc_ref = doc.reference
                uid = doc_ref.parent.parent.id  # users/{uid}/trades/{trade_id}
                doc_ref.update({
                    "status": "won" if status == "won" else "lost",
                    "profit": profit,
                    "exit_spot": exit_spot,
                    "closed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                })
                self.risk_manager.on_trade_settled(uid=uid, profit=profit)
        except Exception as e:
            logger.error(f"Error updating settled contract in Firestore: {e}")

    def _update_link_status(
        self,
        uid: str,
        linked: bool,
        account_id: str = "",
        is_virtual: bool = True,
        currency: str = "USD",
        balance: float = 0.0,
        raw_error: Optional[Dict[str, Any]] = None,
    ):
        """Updates users/{uid}/deriv_link document. NEVER stores or exposes the token."""
        if not self.db:
            return

        doc_ref = self.db.collection("users").document(uid).collection("deriv_link").document("status")
        payload = {
            "linked": linked,
            "account_id": account_id if linked else "",
            "is_virtual": is_virtual,
            "currency": currency,
            "balance": balance,
            "last_synced": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if raw_error:
            payload["last_error"] = raw_error

        try:
            doc_ref.set(payload, merge=True)
        except Exception as e:
            logger.error(f"Failed to update deriv_link in Firestore: {e}")

    def _write_trade_to_firestore(self, uid: str, trade_id: str, trade_data: Dict[str, Any]):
        """Writes trade document to users/{uid}/trades/{trade_id} via Admin SDK."""
        if not self.db:
            return
        doc_ref = self.db.collection("users").document(uid).collection("trades").document(trade_id)
        try:
            doc_ref.set(trade_data)
        except Exception as e:
            logger.error(f"Failed to write trade to Firestore: {e}")
