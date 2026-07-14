# PRD - Projeto Sedes/DF Concursos (Quadrix)

## Problem Statement
Clonar projeto existente do GitHub: https://github.com/rominazapata666-del/prohjetorincencina900-df-sedes-001 (branch main), instalar dependências e configurar o ambiente para continuar o desenvolvimento.

## Architecture
- **Backend**: FastAPI (Python 3.11) + MongoDB (motor async driver)
- **Frontend**: React 19 + CRACO + Tailwind CSS + Radix UI (shadcn-style)
- **Auth**: JWT-based admin auth (bcrypt) - admin user seeded automatically
- **Extras**: PIX generator (qrcode), Telegram notifications, document uploads

## Estrutura do Backend
- `server.py` - App FastAPI principal, monta routers `/api`
- `admin_routes.py` - Rotas administrativas (seed admin `donas`)
- `inscricao_routes.py` - Rotas públicas de inscrição em concurso
- `pix_generator.py` - Geração de pagamentos PIX/QR Code
- `tests/` - Testes pytest do backend
- `uploads/` - Documentos enviados (fotos frente/verso)

## Estrutura do Frontend
- `src/App.js`, `src/index.js` - Entry points React
- `src/components/`, `src/hooks/`, `src/lib/`, `src/constants/` - App code
- `public/` - HTML estáticos (home, cadastro, inscricao, farpainel, documentos)
- `plugins/health-check` - Plugin interno

## Status - Clone e Setup (12/07/2026)
- ✓ Repositório clonado (branch main) preservando `.git` e `.emergent`
- ✓ Dependências Python instaladas (`pip install -r requirements.txt`)
- ✓ Dependências Frontend instaladas (`yarn install`)
- ✓ Arquivos `.env` preservados (MONGO_URL, DB_NAME, REACT_APP_BACKEND_URL)
- ✓ Supervisor: backend + frontend rodando em portas 8001/3000
- ✓ Backend responde em `/api/` → "Painel Administrativo API"
- ✓ Frontend carrega corretamente (título "Quadrix", página de concurso Sedes/DF)
- ✓ Admin `donas` foi seeded automaticamente no MongoDB

## Backlog (aguardando direção do usuário)
- Nenhuma alteração de código feita nesta etapa
- Próximo passo: usuário indicar features/ajustes a implementar

## Update — 2026-02-12 — Responsividade Mobile (Fase concluída)
- Criado `/app/frontend/public/assets/mobile-fix.css` com @media (max-width: 820px) e @media (max-width: 400px)
- Neutralizado anti-pattern `body *{overflow:hidden}` que causava clipping silencioso em `confirmar-inscricao.html`
- Substituídas larguras fixas (980/770/470/450/280/200px) por `width:100%` no mobile (desktop 100% preservado)
- Tap targets ≥ 44px (WCAG 2.5.5) em botões e inputs
- Link do CSS injetado em todas 7 páginas: home, inscricao, cadastro, confirmar-inscricao, resumo-inscricao, pagamento-pix, comprovante-inscricao
- Validado via Playwright em iPhone 14 (390x844) e Pixel 7 (412x915): 0 overflow horizontal, título do concurso renderiza integralmente, botões ≥ 44px, inputs ≥ 44px
