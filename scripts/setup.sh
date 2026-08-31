#!/usr/bin/env bash
# Secure Exam — ARM64 macOS Development Setup
# Tested on: macOS 14+ (Sonoma), Apple Silicon (M1/M2/M3/M4)

set -euo pipefail

echo "=== Secure Exam Development Environment Setup ==="
echo "Target: ARM64 macOS (Apple Silicon)"
echo ""

# 1. Check prerequisites
echo "Checking prerequisites..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if [[ $(uname -m) != "arm64" ]]; then
    echo "Warning: Not running on an ARM64 machine. Proceeding anyway, but expect potential issues."
fi

# 2. Install system dependencies via Homebrew
echo "Installing system dependencies..."
brew install python@3.12 librdkafka postgresql@16 docker docker-compose
# Note: librdkafka is required for confluent-kafka Python package on ARM64

# 3. Python virtual environment
echo "Setting up Python virtual environment..."
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

if [ -f "backend/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    # ARM64 needs explicit paths for librdkafka
    C_INCLUDE_PATH=/opt/homebrew/include LIBRARY_PATH=/opt/homebrew/lib pip install -r backend/requirements.txt
else
    echo "backend/requirements.txt not found, skipping pip install."
fi

# 4. Flutter SDK
echo "Checking Flutter SDK..."
if ! command -v flutter &> /dev/null; then
    echo "Flutter not found. Installing via Homebrew..."
    brew install --cask flutter
fi
flutter doctor

if [ -d "client_app" ]; then
    echo "Getting Flutter dependencies..."
    (cd client_app && flutter pub get)
fi

# 5. Generate .env from template
echo "Setting up environment variables..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example."
fi

# 6. Start Docker services
echo "Starting Docker services..."
docker-compose -f docker/docker-compose.yml up -d

# 7. Wait for services to be healthy
echo "Waiting for Docker services to be healthy..."
sleep 10 # Basic wait, could be improved with a loop checking `docker ps`

# 8. Create Kafka topics
echo "Creating Kafka topics..."
docker exec secure-exam-kafka-1 /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic exam.lifecycle --bootstrap-server kafka:9092 --partitions 3 --replication-factor 1
docker exec secure-exam-kafka-1 /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic exam.keys --bootstrap-server kafka:9092 --partitions 6 --replication-factor 1
docker exec secure-exam-kafka-1 /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic exam.audit --bootstrap-server kafka:9092 --partitions 3 --replication-factor 1

# 9. Run database migrations
echo "Running database migrations..."
if [ -d "backend" ] && [ -f "backend/alembic.ini" ]; then
    (cd backend && alembic upgrade head)
fi

# 10. Verify everything
echo "Verifying setup..."
if [ -d "backend/app" ]; then
    python -c "
try:
    from app.crypto.engine import CryptoEngine
    print('Crypto engine OK')
except Exception as e:
    print('Crypto engine check failed:', e)
"
fi
echo "Attempting to reach backend health endpoint..."
curl -s http://localhost:8000/health || echo "Backend not available yet, run uvicorn manually or wait."

echo ""
echo "=== Setup Complete ==="
echo "Backend API:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/docs"
echo "Kafka UI:     http://localhost:8080"
echo "PostgreSQL:   localhost:5432"
