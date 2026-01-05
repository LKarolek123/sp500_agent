# Use Python 3.11 slim (smaller, Oracle Free Tier friendly)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment to use credentials from env vars
# (Alpaca connector will read from ALPACA_API_KEY, ALPACA_SECRET_KEY)
ENV PYTHONUNBUFFERED=1

# Run the bot (--auto-start skips confirmation prompt)
CMD ["python", "src/live/live_trader_alpaca.py", "--symbol", "SPY", "--check-interval", "60", "--auto-start"]
