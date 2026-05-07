FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1-mesa-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ddddocr
COPY . /ddddocr

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7777
CMD ["python", "server.py"]
