# ---------------------------------------------------------------------------
# Stage 1 — dependency installation
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS deps

WORKDIR /build

# Install pip tools then project dependencies into a dedicated prefix
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .

# ---------------------------------------------------------------------------
# Stage 2 — runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /install /usr/local

# Copy application source
COPY app/ ./app/

USER appuser

EXPOSE 8000

# Uvicorn with 2 workers; adjust --workers based on CPU cores in production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
