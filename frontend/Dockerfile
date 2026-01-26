FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including all Playwright browser dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    # Additional missing dependencies
    libgobject-2.0-0 \
    libglib2.0-0 \
    libnss3-dev \
    libnssutil3 \
    libsmime3 \
    libgio-2.0-0 \
    libexpat1 \
    libxcb1 \
    libatspi2.0-0 \
    libx11-6 \
    libxext6 \
    # Fonts for rendering
    fonts-liberation \
    fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Expose port 8000
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]