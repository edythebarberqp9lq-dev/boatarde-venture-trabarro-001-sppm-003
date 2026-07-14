"""Tests for admin documents endpoints (GET /api/admin/documents and /api/admin/documents/{cpf}/{side}).
Covers: list, filtering by tipo/q, fetch frente/verso, 404 for passaporte verso and invalid CPF.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'

SEEDED = {
    '11111111101': {'tipo': 'RG', 'has_verso': True, 'nome_part': 'MARIA'},
    '22222222202': {'tipo': 'CNH', 'has_verso': True, 'nome_part': 'JOAO'},
    '33333333303': {'tipo': 'Passaporte', 'has_verso': False, 'nome_part': 'ANA'},
}


@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(f"{BASE_URL}/api/admin/auth/login",
                      json={'username': ADMIN_USER, 'password': ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get('token') or r.json().get('access_token')
    assert token, f"No token in login response: {r.json()}"
    return token


@pytest.fixture(scope='module')
def auth_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}'}


# ---------------- LIST ----------------
class TestListDocuments:
    def test_list_returns_items_and_total(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert 'items' in body and 'total' in body
        assert isinstance(body['items'], list)
        assert body['total'] >= 3
        cpfs = {item['cpf'] for item in body['items']}
        for cpf in SEEDED:
            assert cpf in cpfs, f"Seeded CPF {cpf} missing in list. Got: {cpfs}"

    def test_list_item_shape(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = {it['cpf']: it for it in r.json()['items']}
        for cpf, exp in SEEDED.items():
            it = items[cpf]
            assert it['doc_tipo'] == exp['tipo']
            assert it['frente_nome'], f"frente_nome missing for {cpf}"
            assert it['frente_tipo'], f"frente_tipo missing for {cpf}"
            assert it['frente_size'] is not None
            assert it['has_verso'] == exp['has_verso'], (
                f"has_verso mismatch for {cpf}: got {it['has_verso']} expected {exp['has_verso']}"
            )
            if exp['has_verso']:
                assert it['verso_nome'], f"verso_nome missing for {cpf}"
            assert it.get('created_at')
            assert it.get('last_at')

    def test_filter_tipo_rg(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents?tipo=RG", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()['items']
        assert len(items) >= 1
        for it in items:
            assert it['doc_tipo'] == 'RG', f"Unexpected tipo in filter=RG: {it}"
        assert any(it['cpf'] == '11111111101' for it in items)

    def test_filter_tipo_cnh(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents?tipo=CNH", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        for it in r.json()['items']:
            assert it['doc_tipo'] == 'CNH'

    def test_filter_tipo_passaporte(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents?tipo=Passaporte", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        for it in r.json()['items']:
            assert it['doc_tipo'] == 'Passaporte'

    def test_search_q_maria(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents?q=MARIA", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()['items']
        assert len(items) >= 1
        assert any('MARIA' in (it.get('nome') or '').upper() for it in items)

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/documents", timeout=30)
        assert r.status_code in (401, 403), f"Should require auth, got {r.status_code}"


# ---------------- FILE FETCH ----------------
class TestDocumentFile:
    def test_get_frente_rg(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/11111111101/frente",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b['data'].startswith('data:'), f"Expected data-URL, got: {b['data'][:60]}"
        assert ';base64,' in b['data']
        assert b['side'] == 'frente'
        assert b['doc_tipo'] == 'RG'
        assert b['cpf'] == '11111111101'
        assert b.get('nome_arquivo') is not None
        assert b.get('tipo_arquivo') is not None
        assert b.get('size') is not None

    def test_get_verso_cnh(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/22222222202/verso",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b['data'].startswith('data:')
        assert b['side'] == 'verso'
        assert b['doc_tipo'] == 'CNH'

    def test_passaporte_verso_404(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/33333333303/verso",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 404, f"Expected 404 for passaporte verso, got {r.status_code} {r.text}"

    def test_passaporte_frente_ok(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/33333333303/frente",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()['doc_tipo'] == 'Passaporte'

    def test_invalid_cpf_404(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/99999999999/frente",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 404

    def test_invalid_side_400(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents/11111111101/lateral",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (400, 422)

    def test_requires_auth_file(self):
        r = requests.get(f"{BASE_URL}/api/admin/documents/11111111101/frente", timeout=30)
        assert r.status_code in (401, 403)
