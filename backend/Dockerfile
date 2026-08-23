FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, test suite, pytest config, and dataset
COPY app ./app
COPY data ./data
COPY tests ./tests
COPY pytest.ini .

# Force unbuffered Python output and add current directory to PYTHONPATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=.

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
