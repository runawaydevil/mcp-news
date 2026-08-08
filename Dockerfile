# news-mcp — imagem do servidor MCP de notícias.
FROM python:3.12-slim

# Sem .pyc (rootfs é read-only no runtime) e logs sem buffer.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Usuário não-root (segurança: o container não roda como root).
RUN useradd --uid 10001 --create-home appuser

# Instala dependências primeiro (melhor cache de camadas).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código + um feeds.json padrão (o deploy sobrescreve montando o seu por cima).
COPY *.py ./
COPY feeds.json ./feeds.json

USER appuser
EXPOSE 17631

CMD ["python", "server.py"]
