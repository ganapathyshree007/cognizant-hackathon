# ─────────────────────────────────────────────────────────────
#  Dockerfile — UC07 Care Manager Backend
#  Target platform: Render (or any OCI-compatible host)
#
#  All secrets (Supabase keys, LLM keys) are injected at runtime
#  via environment variables — NOTHING is baked into this image.
# ─────────────────────────────────────────────────────────────

# scikit-learn 1.7.2 requires Python ≥ 3.10; 3.11-slim gives a
# small, fast image with all needed system libraries.
FROM python:3.11-slim

# ── System deps needed by LightGBM, pandas, and reportlab ────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python deps first (layer-cache friendly) ─────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────────
COPY . .

# ── Render assigns PORT dynamically; default to 8000 locally ──
ENV PORT=8000

# Expose for documentation purposes (Render ignores this,
# but it helps local docker run -p mapping).
EXPOSE 8000

# ── Start the server ──────────────────────────────────────────
# • host 0.0.0.0  → reachable from outside the container
# • $PORT         → uses the value Render injects at runtime
# • --workers 1   → single worker keeps SQLite usage safe;
#                   scale horizontally via Render replicas if needed
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers 1"]
