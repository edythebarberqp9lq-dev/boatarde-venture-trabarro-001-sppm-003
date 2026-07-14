"""Backend tests for POST /api/admin/documents/export-zip.

Tests ZIP export endpoint with multiple selection / filtering scenarios.
"""
import io
import os
import zipfile

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # fallback for backend-only execution
    BASE_URL = 'http://localhost:8001'

ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'

EXPORT_URL = f"{BASE_URL}/api/admin/documents/export-zip"
LOGIN_URL = f"{BASE_URL}/api/admin/auth/login"

CPF_MARIA = '11111111101'  # RG
CPF_JOAO = '22222222202'   # CNH
CPF_ANA = '33333333303'    # Passaporte


@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(LOGIN_URL, json={'username': ADMIN_USER, 'password': ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, f'login falhou: {r.status_code} {r.text[:200]}'
    tok = r.json().get('token') or r.json().get('access_token')
    assert tok, f'token ausente na resposta: {r.json()}'
    return tok


@pytest.fixture(scope='module')
def auth_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}


def _open_zip(content: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(content))


class TestExportZipAuth:
    def test_no_auth_returns_401_or_403(self):
        r = requests.post(EXPORT_URL, json={}, timeout=20)
        assert r.status_code in (401, 403), f'esperado 401/403, recebido {r.status_code}'


class TestExportZipAll:
    def test_empty_body_returns_zip_with_all_candidates(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={}, timeout=60)
        assert r.status_code == 200, f'{r.status_code} {r.text[:300]}'
        assert r.headers.get('content-type', '').startswith('application/zip')
        cd = r.headers.get('content-disposition', '')
        assert 'documentos_pnd_' in cd and '.zip' in cd, f'CD inválido: {cd}'
        zf = _open_zip(r.content)
        names = zf.namelist()
        # deve conter ao menos 3 candidatos seedados
        cpfs_presentes = {n.split('/')[0].split('_')[0] for n in names if '/' in n}
        for cpf in (CPF_MARIA, CPF_JOAO, CPF_ANA):
            assert cpf in cpfs_presentes, f'cpf {cpf} ausente no zip. namelist={names}'
        # X-Total-Files header
        assert int(r.headers.get('X-Total-Files', '0')) >= 5

    def test_filter_single_cpf_maria_returns_frente_and_verso(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'cpfs': [CPF_MARIA]}, timeout=30)
        assert r.status_code == 200
        zf = _open_zip(r.content)
        names = zf.namelist()
        # somente 1 pasta com CPF_MARIA
        folders = {n.split('/')[0] for n in names if '/' in n}
        assert len(folders) == 1
        assert next(iter(folders)).startswith(CPF_MARIA + '_')
        # 2 arquivos: frente + verso
        assert len(names) == 2, f'esperado 2 arquivos, recebido {names}'
        assert any('_frente' in n for n in names)
        assert any('_verso' in n for n in names)
        # ambos com prefixo RG
        assert all(n.split('/')[1].startswith('RG_') for n in names), names

    def test_filter_passaporte_ana_returns_only_frente(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'cpfs': [CPF_ANA]}, timeout=30)
        assert r.status_code == 200
        zf = _open_zip(r.content)
        names = zf.namelist()
        folders = {n.split('/')[0] for n in names if '/' in n}
        assert len(folders) == 1 and next(iter(folders)).startswith(CPF_ANA + '_')
        assert len(names) == 1, f'passaporte esperado 1 arquivo, recebido {names}'
        assert '_frente' in names[0]

    def test_inexistent_cpf_returns_404(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'cpfs': ['00000000000']}, timeout=20)
        assert r.status_code == 404
        msg = r.json().get('detail') or ''
        assert 'Nenhum documento encontrado' in msg

    def test_filter_by_tipo_RG_returns_only_RG(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'tipo': 'RG'}, timeout=30)
        assert r.status_code == 200
        zf = _open_zip(r.content)
        names = zf.namelist()
        # todos arquivos devem ter prefixo RG_
        for n in names:
            base = n.split('/')[1]
            assert base.startswith('RG_'), f'arquivo não-RG encontrado: {n}'
        # deve incluir pasta da MARIA
        folders = {n.split('/')[0] for n in names if '/' in n}
        assert any(f.startswith(CPF_MARIA + '_') for f in folders)

    def test_unknown_tipo_returns_404(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'tipo': 'XYZ_INEXISTENTE'}, timeout=20)
        assert r.status_code == 404
