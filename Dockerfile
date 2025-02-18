FROM python:3.9-slim
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]