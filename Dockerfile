FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.health .

# Install minimal dependencies (health server uses only stdlib)
RUN pip install --upgrade pip

# Copy application files
COPY . .

# Expose port
EXPOSE 8080

# Command to run the application
CMD ["python", "ultra_simple_bot.py"]
