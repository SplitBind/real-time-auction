FROM python:3.11-slim

# Install system dependencies (Nginx and Tor)
RUN apt-get update && apt-get install -y \
    nginx \
    tor \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and configurations
COPY main.py .
COPY nginx.conf /etc/nginx/sites-available/default
COPY torrc /etc/tor/torrc
COPY entrypoint.sh .

# Expose ports (Optional: Tor doesn't strictly need ports exposed externally to work)
EXPOSE 80

# Run entrypoint script
CMD ["./entrypoint.sh"]
