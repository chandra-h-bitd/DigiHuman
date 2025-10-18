# Multi-stage build for optimized Python backend
FROM python:3.9.6-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies including GPT4All requirements
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgomp1 \
    libstdc++6 \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9.6-slim

# Create non-root user
RUN groupadd -r docqa && useradd -r -g docqa docqa

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY *.py ./

# Create storage directories and NLTK data directory
RUN mkdir -p /app/storage/documents /app/storage/embeddings /app/storage/sessions
RUN mkdir -p /home/docqa/nltk_data

# Download NLTK data as root
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Set ownership
RUN chown -R docqa:docqa /app /home/docqa

# Switch to non-root user
USER docqa

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "app.main"]
