FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# IMPORTANTE: usar el puerto asignado por Hugging Face (${PORT}) y escuchar en 0.0.0.0
CMD ["bash", "-lc", "streamlit run streamlit_app.py --server.port ${PORT:-7860} --server.address 0.0.0.0"]
