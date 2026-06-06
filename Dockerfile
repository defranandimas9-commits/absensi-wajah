FROM python:3.11.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libx11-6 \
    libxcb1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
