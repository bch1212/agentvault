FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway reads PORT from env; Python reads it via os.getenv
CMD ["python", "-m", "api.main"]
