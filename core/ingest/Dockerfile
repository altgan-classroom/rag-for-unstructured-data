FROM python:3.13-slim

# Install build-essential for a C compiler and other build tools
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install system dependencies for Tesseract and image processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and any other necessary files
COPY core/ingest/requirements.txt .

# Install pip and the dependencies
RUN pip install --no-cache-dir -r requirements.txt