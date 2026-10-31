FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# requirements-lock.txt is the version set verified on Python 3.12.
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY src ./src
COPY api ./api
COPY web ./web
COPY data/provinces.csv data/provinces.sources.md ./data/
COPY models ./models

# CLI demo helpers also work inside the container.
COPY run_pipeline.py run_wp1.py ./
COPY scripts ./scripts
COPY demo ./demo
COPY tests ./tests
COPY pytest.ini ./

RUN mkdir -p /app/outputs/runtime

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
