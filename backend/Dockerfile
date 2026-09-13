# Deriv Automated Trading Bot - Cloud Run Persistent Service
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency definition
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY backend/ /app/backend/

# Run persistent Python service
# Holds Deriv WebSocket connection, evaluates deterministic signals,
# enforces risk constraints, and records trades to Firestore.
CMD ["python", "-m", "backend.bot_service"]
