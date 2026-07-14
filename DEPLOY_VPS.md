# Deploy na VPS — Guia Rápido

## 1. Requisitos da VPS
- Ubuntu 22.04+ (ou similar)
- Python 3.11+
- Node.js 18+ e Yarn
- MongoDB 6+ (local ou remoto)
- Nginx (para proxy reverso e HTTPS)

## 2. Estrutura do projeto
```
/app/
├── backend/         # FastAPI (Python)
│   ├── server.py
│   ├── admin_routes.py
│   ├── requirements.txt
│   └── .env
├── frontend/        # React + páginas HTML estáticas
│   ├── src/
│   ├── public/      # home.html, inscricao-*.html, protocolo.html, pagamento.html, farpapainel/, farpainel/
│   └── .env
```

## 3. Variáveis de ambiente

### `/app/backend/.env`
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="pmsp_producao"   # ou o nome que quiser
CORS_ORIGINS="https://seudominio.com.br"   # restrinja em produção
```

### `/app/frontend/.env`
```
REACT_APP_BACKEND_URL=https://seudominio.com.br
```

## 4. Instalação

```bash
# Backend
cd /app/backend
pip install -r requirements.txt   # já tem emergentintegrations comentado
pip install bcrypt Pillow "qrcode[pil]"

# Frontend (build para produção)
cd /app/frontend
yarn install
yarn build
```

## 5. Executar backend

Use gunicorn ou uvicorn com workers:
```bash
cd /app/backend
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

Ou crie um serviço systemd (recomendado):
```
[Unit]
Description=PMSP Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/app/backend
EnvironmentFile=/app/backend/.env
ExecStart=/usr/local/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

## 6. Servir frontend + páginas estáticas

O React foi buildado em `/app/frontend/build/`. As páginas estáticas
(`home.html`, `inscricao-*.html`, `protocolo.html`, `pagamento.html`,
`farpapainel/`, `farpainel/`) ficam em `/app/frontend/build/` também
após o `yarn build` (public/ é copiado para build/).

## 7. Nginx (exemplo)

```nginx
server {
    listen 443 ssl http2;
    server_name seudominio.com.br;

    ssl_certificate     /etc/letsencrypt/live/seudominio.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seudominio.com.br/privkey.pem;

    # API para o backend
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20M;   # uploads de RG frente/verso
    }

    # Uploads de documentos (servidos pelo backend)
    location /uploads/ {
        proxy_pass http://localhost:8001;
    }

    # Redirect / -> /home.html
    location = / {
        return 302 /home.html;
    }

    # Frontend estático (SPA + páginas HTML)
    location / {
        root /app/frontend/build;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=3600";
    }
}

server {
    listen 80;
    server_name seudominio.com.br;
    return 301 https://$host$request_uri;
}
```

## 8. HTTPS (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seudominio.com.br
```

## 9. Credenciais iniciais

Após primeiro start do backend, um admin `farpa` é criado automaticamente
com a senha `Ads102030`. Você pode:
- **Trocar a senha** logando no painel `/farpapainel` e usando o menu de conta
- **Ou** apagar esse admin e criar um novo via seed no MongoDB

Admin root também é criado automaticamente com base nas envs `ADMIN_USERNAME`
e `ADMIN_PASSWORD` (padrão: `donas` / `Seinao10@@`). **Troque antes de subir!**

Adicione no `/app/backend/.env`:
```
ADMIN_USERNAME=seu_admin
ADMIN_PASSWORD=SuaSenhaForteAqui!
```

## 10. Configurações no painel `/farpapainel`

Depois de deployar, entre no painel e configure:
- **Telegram Bot**: Bot Token + Chat ID (para receber notificações)
- **PIX**: chave PIX, nome do beneficiário, cidade
- **Título das notificações**: "NOVA INSCRIÇÃO PM SP" (ou o que preferir)

## 11. Rotas principais
| Rota | Descrição |
|---|---|
| `/home.html` | Homepage pública (com tracking de acesso) |
| `/inscricao-pmsp2601.html` | Formulário Aluno-Soldado PM (R$ 100) |
| `/inscricao-pmsp2602.html` | Formulário Cadete PM (R$ 200) |
| `/protocolo.html` | Comprovante gerado após inscrição |
| `/pagamento.html` | Tela de pagamento com QR PIX |
| `/farpapainel/` | Painel administrativo |
| `/api/*` | API do backend |

## 12. Backup do MongoDB
```bash
# Backup diário via cron
0 3 * * * mongodump --db pmsp_producao --out /var/backups/mongo/$(date +\%Y\%m\%d)
```
