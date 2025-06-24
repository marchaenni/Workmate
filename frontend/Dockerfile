FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Kopiere requirements und installiere
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten App-Code inkl. templates
COPY . .

RUN useradd -m appuser && chown -R appuser /app

USER appuser

# Flask wird auf 0.0.0.0:5000 ausgeführt
CMD ["python", "app.py"]
