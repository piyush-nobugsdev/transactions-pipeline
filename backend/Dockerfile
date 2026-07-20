FROM python:3.12-slim

WORKDIR /code

# Install dependencies first so Docker caches this layer
# and only re-installs when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
