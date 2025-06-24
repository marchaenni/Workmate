FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads && \
    useradd -m appuser && chown -R appuser /app

USER appuser

EXPOSE 5002
CMD ["python", "file_service.py"]
