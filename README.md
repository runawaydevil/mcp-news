# news-mcp

Servidor MCP de noticias via RSS. Um coletor baixa os feeds do feeds.json de tempos em tempos, guarda tudo num banco SQLite e responde pelas ferramentas do MCP. Nao precisa de token de terceiros nem servico pago.

Ferramentas:

- list_sources: lista as fontes por categoria
- get_latest_news: ultimas noticias (todas, por categoria ou por fonte)
- search_news: busca por palavra-chave
- get_stats: total de artigos e hora da ultima coleta

Categorias das fontes: tech, programação, segurança, ciência, linux, windows, news.

Rodar local:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python server.py

O servidor sobe em http://127.0.0.1:17631/mcp. O coletor roda uma vez ao subir e depois a cada 30 minutos.

Rodar com Docker:

    cp .env.example .env
    (edite o .env e defina NEWS_MCP_TOKEN)
    docker compose up -d --build

A porta fica presa em 127.0.0.1:17631, atras de um proxy reverso (nginx) com HTTPS. O nginx deve repassar todas as rotas (proxy_pass para 127.0.0.1:17631), nao so /mcp, porque o OAuth usa /authorize, /token, /register e /.well-known. O banco fica num volume Docker (newsdata) e persiste; o container roda como usuario nao-root e o volume ja nasce com a dona certa. Editar o feeds.json vale na proxima coleta, sem rebuild.

Configuracao pelo .env: NEWS_MCP_TOKEN, NEWS_MCP_PORT, POLL_INTERVAL_MIN, RETENTION_DAYS, NEWS_MCP_ISSUER_URL, NEWS_MCP_AUTH_PASSWORD.

Trocar as fontes: edite o feeds.json. Cada fonte tem id, name, url e category.

Conectar no Claude Code / Desktop (transporte http com bearer token):

    news https://mcpnews.grupomurad.net/mcp
    header: Authorization: Bearer SEU_TOKEN

Conectar no claude.ai (web/celular) via OAuth: defina NEWS_MCP_ISSUER_URL (ex: https://mcpnews.grupomurad.net) e NEWS_MCP_AUTH_PASSWORD no .env. No claude.ai, adicione um conector personalizado com a URL https://mcpnews.grupomurad.net/mcp; o navegador vai pedir a senha do /authorize para autorizar.
