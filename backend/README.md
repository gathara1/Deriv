# Deriv.com Automated Trading Bot (Cloud Run + Firebase Backend)

## Architecture Overview

This backend is the **sole execution and signal generation authority** for the Deriv trading bot.
No trading logic or credentials exist on the client application.

```
┌────────────────────────────────────────────────────────┐
│ Cloud Run Persistent Python Service (bot_service.py)   │
│ ├─ WebSocket connection to Deriv API (ws.derivws.com) │
│ ├─ Secret Manager token retrieval (deriv-token-<uid>)  │
│ ├─ Deterministic Signal Logic (RSI, Dual EMA, BB %B)   │
│ ├─ Pre-trade Risk Enforcement Module                   │
│ └─ Lifecycle: authorize -> proposal -> buy             │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Firestore Admin SDK                                    │
│ ├─ users/{uid}/deriv_link   (link status only)         │
│ ├─ users/{uid}/signals/{id} (snapshot + Gemini reason) │
│ ├─ users/{uid}/trades/{id}  (open / won / lost / failed│
│ └─ users/{uid}/risk_state   (drawdown, open contracts) │
└───────────────────────▲────────────────────────────────┘
                        │ Realtime Listeners (Read-only)
┌───────────────────────┴────────────────────────────────┐
│ Android Client / Thin UI                               │
│ ├─ Firebase Auth identity                              │
│ ├─ 3 Callable Functions: requestTrade, pauseBot, resume│
│ └─ Push / Local notifications on trade events          │
└────────────────────────────────────────────────────────┘
```

## Security & Privacy Rules
- **No Token on Client**: Deriv tokens are fetched from Google Cloud Secret Manager (`deriv-token-{uid}`).
- **Firestore Security**:
  ```
  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      match /users/{uid}/{document=**} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }
    }
  }
  ```
- **Trade Lifecycle**:
  1. `authorize(token)`
  2. `proposal(fresh price, payout, proposal_id)`
  3. `buy(proposal_id)`
- **Risk Invariant**:
  - Max daily loss % checked.
  - Max concurrent open contracts enforced.
  - Max stake per trade enforced.
  - Violations rejected and logged explicitly to `risk_state.violations_history`.
