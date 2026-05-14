FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose standard execution port
EXPOSE 8000

# Start Uvicorn server production-ready
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
