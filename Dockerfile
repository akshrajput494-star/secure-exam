FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source code
COPY backend ./backend
COPY frontend ./frontend
COPY database ./database

# Ensure upload directory exists
RUN mkdir -p backend/uploads

EXPOSE 5000

ENV PORT=5000
ENV FLASK_ENV=production

CMD ["gunicorn", "--chdir", "backend", "server:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
