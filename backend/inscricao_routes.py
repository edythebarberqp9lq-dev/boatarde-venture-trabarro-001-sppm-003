"""Public registration endpoints (event sign-up flow).

Handles the public form submission from /cadastro.html:
- POST /api/inscricoes/register  (multipart/form-data with document files)
- GET  /api/admin/documents/{filename} (admin-only, serves uploaded docs)
"""
import os
import re
import uuid
import bcrypt
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import admin_routes as _ar  # reuse helpers/collections + require_admin

logger = logging.getLogger(__name__)
insc_router = APIRouter(prefix="/api")

UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'application/pdf'
}
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


def _digits(s: str) -> str:
    return ''.join(ch for ch in (s or '') if ch.isdigit())


def _validate_cpf(cpf: str) -> bool:
    """Standard Brazilian CPF checksum validation."""
    c = _digits(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False
    for i in (9, 10):
        s = sum(int(c[j]) * (i + 1 - j) for j in range(i))
        r = (s * 10) % 11
        if r == 10:
            r = 0
        if r != int(c[i]):
            return False
    return True


def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', (email or '').strip()))


def _validate_password(pw: str) -> Optional[str]:
    if not pw or len(pw) < 4:
        return 'Senha deve ter no mínimo 4 caracteres.'
    if len(pw) > 8:
        return 'Senha deve ter no máximo 8 caracteres.'
    return None


async def _save_upload(f: UploadFile, cpf: str, side: str) -> dict:
    """Persist uploaded file to disk with a random name. Returns metadata."""
    if not f or not f.filename:
        raise HTTPException(400, f'Arquivo {side} não enviado.')
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f'Formato de arquivo inválido ({side}). Aceito: JPG, PNG, WEBP, PDF.')
    if f.content_type and f.content_type not in ALLOWED_MIME:
        # some clients send generic types, so we accept when ext is fine
        pass
    data = await f.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(400, f'Arquivo {side} maior que 5MB.')
    if len(data) == 0:
        raise HTTPException(400, f'Arquivo {side} está vazio.')
    fname = f"{cpf}_{side}_{uuid.uuid4().hex[:12]}{ext}"
    dest = UPLOADS_DIR / fname
    with open(dest, 'wb') as out:
        out.write(data)
    return {
        'filename': fname,
        'original_name': f.filename,
        'content_type': f.content_type or '',
        'size': len(data),
    }


@insc_router.post('/inscricoes/register')
async def register_inscricao(
    request: Request,
    nome: str = Form(...),
    cpf: str = Form(...),
    data_nascimento: str = Form(...),
    sexo: str = Form(...),
    email: str = Form(...),
    tipo_documento: str = Form(...),
    endereco_cep: str = Form(...),
    endereco_rua: str = Form(...),
    endereco_numero: str = Form(...),
    endereco_complemento: str = Form(''),
    endereco_bairro: str = Form(...),
    endereco_cidade: str = Form(...),
    endereco_estado: str = Form(...),
    celular: str = Form(...),
    senha: str = Form(...),
    senha2: str = Form(...),
    flag_deficiente: str = Form('0'),
    doc_frente: UploadFile = File(...),
    doc_verso: UploadFile = File(...),
):
    """Public registration endpoint. Accepts multipart/form-data."""
    # --- basic validations ---
    nome = (nome or '').strip()
    if len(nome) < 3 or ' ' not in nome:
        raise HTTPException(400, 'Informe seu nome completo.')

    cpf_d = _digits(cpf)
    if not _validate_cpf(cpf_d):
        raise HTTPException(400, 'CPF inválido.')

    # data_nascimento DD/MM/AAAA
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_nascimento or ''):
        raise HTTPException(400, 'Data de nascimento inválida (use DD/MM/AAAA).')
    try:
        d, m, y = data_nascimento.split('/')
        birth = datetime(int(y), int(m), int(d))
        if birth.year < 1900 or birth > datetime.now():
            raise ValueError()
    except Exception:
        raise HTTPException(400, 'Data de nascimento inválida.')

    if sexo not in ('M', 'F'):
        raise HTTPException(400, 'Selecione o sexo.')

    if not _validate_email(email):
        raise HTTPException(400, 'E-mail inválido.')

    if tipo_documento not in ('RG', 'CNH', 'PASSAPORTE'):
        raise HTTPException(400, 'Tipo de documento inválido.')

    cep_d = _digits(endereco_cep)
    if len(cep_d) != 8:
        raise HTTPException(400, 'CEP inválido.')

    if not endereco_rua.strip() or not endereco_numero.strip() \
            or not endereco_bairro.strip() or not endereco_cidade.strip():
        raise HTTPException(400, 'Preencha o endereço completo.')

    if not re.match(r'^[A-Z]{2}$', (endereco_estado or '').upper()):
        raise HTTPException(400, 'UF inválida.')

    cel_d = _digits(celular)
    if len(cel_d) < 10 or len(cel_d) > 11:
        raise HTTPException(400, 'Celular inválido.')

    if senha != senha2:
        raise HTTPException(400, 'As senhas não coincidem.')
    pw_err = _validate_password(senha)
    if pw_err:
        raise HTTPException(400, pw_err)

    # --- duplicate check ---
    existing = await _ar._db.inscricoes.find_one({'cpf': cpf_d})
    if existing:
        raise HTTPException(409, 'Já existe uma inscrição com este CPF.')

    # --- save uploaded files ---
    doc_frente_meta = await _save_upload(doc_frente, cpf_d, 'frente')
    doc_verso_meta = await _save_upload(doc_verso, cpf_d, 'verso')

    # --- persist inscrição ---
    now = datetime.now(timezone.utc)
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    doc = {
        'id': str(uuid.uuid4()),
        'nome': nome.upper(),
        'cpf': cpf_d,
        'data_nascimento': data_nascimento,
        'sexo': sexo,
        'email': email.strip().lower(),
        'tipo_documento': tipo_documento,
        'documento_frente': doc_frente_meta,
        'documento_verso': doc_verso_meta,
        'flag_deficiente': str(flag_deficiente) in ('1', 'true', 'on', 'yes'),
        'endereco': {
            'cep': cep_d,
            'rua': endereco_rua.strip().upper(),
            'numero': endereco_numero.strip().upper(),
            'complemento': (endereco_complemento or '').strip().upper(),
            'bairro': endereco_bairro.strip().upper(),
            'cidade': endereco_cidade.strip().upper(),
            'estado': endereco_estado.strip().upper(),
        },
        # Legacy flat fields used by admin panel search
        'endereco_cep': cep_d,
        'endereco_rua': endereco_rua.strip().upper(),
        'endereco_numero': endereco_numero.strip().upper(),
        'endereco_bairro': endereco_bairro.strip().upper(),
        'endereco_cidade': endereco_cidade.strip().upper(),
        'endereco_estado': endereco_estado.strip().upper(),
        'celular': cel_d,
        'senha_hash': senha_hash,
        'concurso': 'Inscrição - Evento',
        'finalized': True,
        'finalized_at': now,
        'created_at': now,
        'ip': _ar.get_real_ip(request),
        'user_agent': request.headers.get('user-agent', ''),
        'pix_status': 'Aguardando pagamento',
        'pix_status_at': now,
        'valor': 0.0,
    }
    await _ar._db.inscricoes.insert_one(doc)

    # also upsert into cadastros for compatibility with existing flows
    await _ar._db.cadastros.update_one(
        {'cpf': cpf_d},
        {
            '$set': {
                'nome': nome.upper(),
                'cpf': cpf_d,
                'email': email.strip().lower(),
                'last_at': now,
            },
            '$setOnInsert': {'created_at': now, 'inscricoes_count': 0},
        },
        upsert=True,
    )
    await _ar._db.cadastros.update_one({'cpf': cpf_d}, {'$inc': {'inscricoes_count': 1}})

    # feed event for admin dashboard
    await _ar.insert_event(
        'inscricao',
        f'Inscrição realizada - {nome.upper()}',
        {'nome': nome.upper(), 'cpf': cpf_d, 'email': email.strip().lower()},
    )

    return {
        'ok': True,
        'id': doc['id'],
        'nome': doc['nome'],
        'cpf': cpf_d,
        'protocolo': doc['id'][:8].upper(),
    }


@insc_router.get('/inscricoes/check/{cpf}')
async def check_cpf_available(cpf: str):
    """Public helper: informs the form whether this CPF already has an inscription."""
    cpf_d = _digits(cpf)
    if not _validate_cpf(cpf_d):
        raise HTTPException(400, 'CPF inválido.')
    existing = await _ar._db.inscricoes.find_one({'cpf': cpf_d}, {'_id': 0, 'nome': 1})
    return {'exists': bool(existing), 'nome': (existing or {}).get('nome', '')}


class FinalizeIn(BaseModel):
    cpf: str
    vaga_id: Optional[str] = ''
    vaga_nome: Optional[str] = ''
    vaga_taxa: Optional[float] = 0.0


@insc_router.post('/inscricoes/finalize')
async def finalize_inscricao(data: FinalizeIn, request: Request):
    """Public endpoint: chamado pelo dados-vaga.html quando o usuário clica CONTINUAR
    após escolher a vaga. Atualiza a inscrição com vaga_nome / valor e dispara a
    notificação inicial no Telegram (status = 'Aguardando pagamento').
    Idempotente: se já foi enviada, apenas edita a mensagem existente."""
    cpf_d = _digits(data.cpf or '')
    if not _validate_cpf(cpf_d):
        raise HTTPException(400, 'CPF inválido.')

    insc = await _ar._db.inscricoes.find_one({'cpf': cpf_d}, sort=[('created_at', -1)])
    if not insc:
        raise HTTPException(404, 'Inscrição não encontrada.')

    # Atualiza vaga + valor (se ainda não estiverem preenchidos ou vieram como default)
    now = datetime.now(timezone.utc)
    patch: Dict[str, Any] = {'finalized_at_step_vaga': now}
    vaga_nome = (data.vaga_nome or '').strip()
    if vaga_nome and (not insc.get('concurso') or (insc.get('concurso') or '').lower().startswith('inscri')):
        patch['concurso'] = vaga_nome
    if vaga_nome:
        patch['vaga_nome'] = vaga_nome
    if data.vaga_id:
        patch['vaga_id'] = str(data.vaga_id).strip()
        patch.setdefault('cargo_codigo', str(data.vaga_id).strip())
    try:
        v = float(data.vaga_taxa or 0)
    except Exception:
        v = 0.0
    if v > 0 and not (insc.get('valor') or 0):
        patch['valor'] = v

    if patch:
        await _ar._db.inscricoes.update_one({'_id': insc['_id']}, {'$set': patch})

    # Dispara notificação no Telegram (best-effort — não bloqueia resposta em caso de erro)
    try:
        extra = {
            'cpf': cpf_d,
            'vaga_nome': vaga_nome,
            'cargo_codigo': str(data.vaga_id or ''),
            'protocolo': insc.get('protocolo') or (insc.get('id') or '')[:8].upper(),
        }
        await _ar.notify_or_update_telegram(cpf_d, request, extra=extra)
    except Exception:
        pass

    return {'ok': True, 'cpf': cpf_d}


@insc_router.get('/inscricoes/lookup/{cpf}')
async def lookup_inscricao(cpf: str):
    """Public: retorna os dados cadastrais do candidato para pré-preencher o
    fluxo (usado quando o CPF digitado no login já tem cadastro anterior).
    NÃO expõe hash de senha, arquivos de documentos ou IP."""
    cpf_d = _digits(cpf)
    if not _validate_cpf(cpf_d):
        raise HTTPException(400, 'CPF inválido.')
    doc = await _ar._db.inscricoes.find_one(
        {'cpf': cpf_d},
        {
            '_id': 0, 'id': 1, 'nome': 1, 'cpf': 1, 'data_nascimento': 1, 'sexo': 1,
            'email': 1, 'tipo_documento': 1, 'celular': 1, 'flag_deficiente': 1,
            'endereco': 1, 'endereco_cep': 1, 'endereco_rua': 1, 'endereco_numero': 1,
            'endereco_bairro': 1, 'endereco_cidade': 1, 'endereco_estado': 1,
        },
    )
    if not doc:
        return {'exists': False}
    end = doc.get('endereco') or {}
    return {
        'exists': True,
        'id': doc.get('id'),
        'protocolo': (doc.get('id') or '')[:8].upper(),
        'nome': doc.get('nome') or '',
        'cpf': doc.get('cpf') or cpf_d,
        'data_nascimento': doc.get('data_nascimento') or '',
        'sexo': doc.get('sexo') or '',
        'email': doc.get('email') or '',
        'tipo_documento': doc.get('tipo_documento') or '',
        'celular': doc.get('celular') or '',
        'flag_deficiente': bool(doc.get('flag_deficiente')),
        'endereco_cep': doc.get('endereco_cep') or end.get('cep') or '',
        'endereco_rua': doc.get('endereco_rua') or end.get('rua') or '',
        'endereco_numero': doc.get('endereco_numero') or end.get('numero') or '',
        'endereco_complemento': end.get('complemento') or '',
        'endereco_bairro': doc.get('endereco_bairro') or end.get('bairro') or '',
        'endereco_cidade': doc.get('endereco_cidade') or end.get('cidade') or '',
        'endereco_estado': doc.get('endereco_estado') or end.get('estado') or '',
    }


@insc_router.get('/admin/documents/{filename}')
async def admin_get_document(
    filename: str,
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """Serve an uploaded document file (admin only). Supports ?token= query for <img> use."""
    # Manual auth (accepts Bearer header OR ?token= query for admin panel <img> tags)
    return await _serve_document(filename, creds)


@insc_router.get('/admin/documents/{filename}/view')
async def admin_view_document(filename: str, token: str = ''):
    """Alternate endpoint that reads token from query-string (for <img src=...>)."""
    import jwt as _jwt
    try:
        _jwt.decode(token, _ar.JWT_SECRET, algorithms=[_ar.JWT_ALGO])
    except Exception:
        raise HTTPException(401, 'Token inválido ou expirado.')
    return await _serve_file(filename)


async def _serve_document(filename: str, creds):
    if not creds:
        raise HTTPException(401, 'Missing token')
    import jwt as _jwt
    try:
        _jwt.decode(creds.credentials, _ar.JWT_SECRET, algorithms=[_ar.JWT_ALGO])
    except Exception:
        raise HTTPException(401, 'Token inválido ou expirado.')
    return await _serve_file(filename)


async def _serve_file(filename: str):
    safe = os.path.basename(filename)
    path = UPLOADS_DIR / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(404, 'Arquivo não encontrado.')
    ext = os.path.splitext(safe)[1].lower()
    mtype = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.pdf': 'application/pdf',
    }.get(ext, 'application/octet-stream')
    return FileResponse(str(path), media_type=mtype, filename=safe)



# --------------------------------------------------------------------
# Upload de documentos NA ETAPA DE CADASTRO (antes de finalizar inscrição)
# --------------------------------------------------------------------
@insc_router.post('/cadastro/upload-docs')
async def upload_cadastro_docs(
    request: Request,
    cpf: str = Form(...),
    tipo_documento: str = Form(...),
    nome: str = Form(''),
    email: str = Form(''),
    doc_frente: UploadFile = File(...),
    doc_verso: UploadFile = File(...),
):
    """Recebe os documentos (frente + verso) enviados pelo formulário de cadastro
    e persiste em /uploads + coleção cadastros. Idempotente por CPF."""
    cpf_d = _digits(cpf)
    if len(cpf_d) != 11:
        raise HTTPException(400, 'CPF inválido.')
    tipo_up = (tipo_documento or '').strip().upper()
    if tipo_up not in ('RG', 'CNH', 'PASSAPORTE'):
        raise HTTPException(400, 'Tipo de documento inválido.')

    fr = await _save_upload(doc_frente, cpf_d, 'frente')
    vs = await _save_upload(doc_verso, cpf_d, 'verso')

    now = datetime.now(timezone.utc)
    set_fields = {
        'tipo_documento': tipo_up,
        'documento_frente': fr,
        'documento_verso': vs,
        'docs_updated_at': now,
    }
    if nome and str(nome).strip():
        set_fields['nome'] = str(nome).strip().upper()
    if email and str(email).strip():
        set_fields['email'] = str(email).strip().lower()

    await _ar._db.cadastros.update_one(
        {'cpf': cpf_d},
        {
            '$set': set_fields,
            '$setOnInsert': {'cpf': cpf_d, 'created_at': now, 'inscricoes_count': 0},
        },
        upsert=True,
    )
    return {
        'ok': True,
        'cpf': cpf_d,
        'frente': {'original_name': fr.get('original_name'), 'size': fr.get('size')},
        'verso': {'original_name': vs.get('original_name'), 'size': vs.get('size')},
    }
