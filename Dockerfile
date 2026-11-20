FROM python:3.12-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Código da API, módulo de atributos compartilhado e o modelo exportado pelo notebook.
COPY src ./src
COPY api ./api
COPY models/modelo.joblib models/metadata.json ./models/

# Plataformas como Render e Hugging Face definem a porta pela variável PORT.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
