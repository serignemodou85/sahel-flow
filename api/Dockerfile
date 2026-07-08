FROM python:3.12-slim

WORKDIR /

COPY api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# shared/ est copié depuis la racine du projet (context: . dans docker-compose.yml).
# Sans cette ligne, "from shared.config import get_settings" échoue dans le container.
COPY shared/ shared/
COPY api/app/ app/

# PYTHONPATH=/ permet à Python de résoudre "shared.config" → /shared/config.py
ENV PYTHONPATH=/

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
