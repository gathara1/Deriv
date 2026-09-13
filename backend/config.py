"""
Backend Configuration & Secret Manager Accessor.
Strictly adheres to architectural requirements:
- Deriv tokens stored in Google Cloud Secret Manager keyed by Firebase UID (deriv-token-<UID>).
- Tokens are NEVER sent to or stored on any client.
- No hardcoded IPs or open debug ports.
"""

import os
import logging
from typing import Optional
from google.cloud import secretmanager
import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DerivBotConfig")

# Environment & Project Configuration
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "deriv-trading-bot-prod"))
DERIV_APP_ID = os.environ.get("DERIV_APP_ID", "1089")  # 1089 is default official Deriv demo test app ID
DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"

# Initialize Firebase Admin SDK (if not already initialized)
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.warning(f"Default Firebase Admin init failed, running in local/test mode: {e}")

def get_firestore_client():
    """Returns Firestore client using Application Default Credentials."""
    return firestore.client()

def get_deriv_token_from_secret_manager(uid: str) -> Optional[str]:
    """
    Fetches the user's Deriv token directly from GCP Secret Manager.
    Keyed by Firebase UID: 'deriv-token-{uid}'.
    Tokens never touch client applications.
    """
    secret_id = f"deriv-token-{uid}"
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        token = response.payload.data.decode("UTF-8").strip()
        logger.info(f"Retrieved Deriv token for uid={uid[:6]}*** from Secret Manager.")
        return token
    except Exception as e:
        logger.error(f"Failed to access Secret Manager for {secret_id}: {e}")
        # Check fallback environment for local automated testing
        fallback = os.environ.get(f"DERIV_TOKEN_{uid.upper().replace('-', '_')}") or os.environ.get("DERIV_DEMO_TOKEN")
        if fallback:
            logger.info("Using configured local environment token fallback for automated test harness.")
            return fallback
        return None

def store_deriv_token_in_secret_manager(uid: str, token: str) -> bool:
    """
    Stores an authorized Deriv token from OAuth redirect in Secret Manager.
    Called only by the server-side OAuth callback endpoint.
    """
    secret_id = f"deriv-token-{uid}"
    try:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{GCP_PROJECT_ID}"
        # Check if secret already exists
        try:
            client.get_secret(request={"name": f"{parent}/secrets/{secret_id}"})
        except Exception:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        # Add secret version
        client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_id}",
                "payload": {"data": token.encode("UTF-8")},
            }
        )
        logger.info(f"Successfully stored token in Secret Manager for uid={uid}")
        return True
    except Exception as e:
        logger.error(f"Failed to store secret {secret_id}: {e}")
        return False
