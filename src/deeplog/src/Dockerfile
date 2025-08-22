# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyTorch, Redis, and other libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (create this separately or inline below)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose Prometheus metrics port
EXPOSE 8000

# Command to run the application
CMD ["python","-m", "deeplog_prometheus.py"]