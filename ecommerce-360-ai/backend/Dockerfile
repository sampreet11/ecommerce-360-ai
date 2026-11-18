FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
COPY database /app/database
COPY data/processed /app/data/processed
EXPOSE 8000
CMD ["sh", "-c", "python -m app.database.setup && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
