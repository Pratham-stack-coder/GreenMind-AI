FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train ML models at build time.
# WARN-007 FIX: train.py uses `from generate_dataset import generate_series`
# (relative import), so it must run from the directory containing generate_dataset.py.
# Running via `python -m app.ml.train` from /app fails because the CWD is /app
# and generate_dataset.py is in /app/app/ml/, not /app.
# Solution: cd into the ml directory before running train.py directly.
RUN cd /app/app/ml && python train.py || echo "WARNING: ML model training failed. Models must be trained separately."

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
