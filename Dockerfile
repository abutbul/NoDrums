# Use Python slim image as base
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg sox lame libsox-fmt-mp3 lame

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install additional dependencies for testing
RUN pip install --no-cache-dir pytest

# Copy application code
COPY . /app
WORKDIR /app

# Set PYTHONPATH environment variable
ENV PYTHONPATH="/app"

# Set up pre-trained models directory
#RUN mkdir -p /root/.config/spleeter/pretrained_models/4stems && \
#    tar -xzf /app/4stems.tar.gz -C /root/.config/spleeter/pretrained_models/4stems 

# Set MODEL_PATH environment variable this is used when packaged with the specific model file. otherwise it will be downloaded on first use
#ENV MODEL_PATH=/root/.config/spleeter/pretrained_models

# Default command for running tests
CMD ["pytest", "--junitxml=report.xml"]

