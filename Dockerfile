# Dockerfile – AgentFlow multi-agent AI system
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install streamlit requests

# Copy application code
COPY . .

RUN chmod +x start.sh

ENV PORT=8080
CMD ["./start.sh"]
