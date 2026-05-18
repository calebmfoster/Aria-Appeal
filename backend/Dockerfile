FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (e.g. for pydub/AudioEditor if needed, though pydub needs ffmpeg)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 8000

# Default command (overridden by docker-compose usually)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
