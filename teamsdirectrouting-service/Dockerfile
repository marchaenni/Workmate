FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser /app

USER appuser

EXPOSE 5005
CMD ["python", "teamsdirectrouting_service.py"]
