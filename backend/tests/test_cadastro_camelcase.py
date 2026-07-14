"""Tests: POST /api/track/registration with camelCase form_data persists correctly
and is returned by GET /api/admin/cadastros/{cpf}/details."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
TEST_CPF = '99988877766'
ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'

FORM_DATA = {
    'nome': 'TESTE CAMELCASE',
    'cpf': TEST_CPF,
    'nomeSocial': 'Testinho',
    'sexo': 'M',
    'nascimento': '15/03/1990',
    'nacionalidade': 'Brasileiro',
    'nomeMae': 'Maria Teste da Silva',
    'cep': '38400-000',
    'endereco': 'Rua das Acácias',
    'numero': '123',
    'complemento': 'Apto 45',
    'bairro': 'Centro',
    'cidade': 'Uberlândia',
    'uf': 'MG',
    'tel1': '(34) 3333-4444',
    'tel1Tipo': 'Fixo',
    'tel2': '(34) 99999-8888',
    'tel2Tipo': 'Celular',
    'email': 'teste@example.com',
    'pcd': 'Não',
}

EXPECTED_KEYS = [
    'nome', 'cpf', 'nomeSocial', 'sexo', 'nascimento', 'nacionalidade',
    'nomeMae', 'cep', 'endereco', 'numero', 'complemento', 'bairro',
    'cidade', 'uf', 'tel1', 'tel1Tipo', 'tel2', 'tel2Tipo', 'email', 'pcd',
]


@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(f"{BASE_URL}/api/admin/auth/login",
                      json={'username': ADMIN_USER, 'password': ADMIN_PASS},
                      timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tok = r.json().get('token')
    assert tok, "No token returned"
    return tok


@pytest.fixture(scope='module', autouse=True)
def cleanup(admin_token):
    # ensure clean state pre-test
    requests.delete(f"{BASE_URL}/api/admin/cadastros/{TEST_CPF}",
                    headers={'Authorization': f'Bearer {admin_token}'}, timeout=10)
    yield
    # cleanup post-test
    requests.delete(f"{BASE_URL}/api/admin/cadastros/{TEST_CPF}",
                    headers={'Authorization': f'Bearer {admin_token}'}, timeout=10)


def test_track_registration_persists_camelcase(admin_token):
    payload = {
        'page': '/inscricao-passo8.html',
        'user_agent': 'Mozilla/5.0 PytestRunner',
        'extra': {
            'nome': FORM_DATA['nome'],
            'cpf': TEST_CPF,
            'email': FORM_DATA['email'],
            'concurso': 'ENARE 2026',
            'stage': 'cadastro',
            'form_data': FORM_DATA,
        }
    }
    r = requests.post(f"{BASE_URL}/api/track/registration", json=payload, timeout=15)
    assert r.status_code == 200, f"track/registration failed: {r.status_code} {r.text}"
    assert r.json().get('ok') is True


def test_get_cadastro_details_returns_camelcase(admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/cadastros/{TEST_CPF}/details",
                     headers={'Authorization': f'Bearer {admin_token}'},
                     timeout=15)
    assert r.status_code == 200, f"details fetch failed: {r.status_code} {r.text}"
    doc = r.json()
    fd = doc.get('form_data') or {}
    assert fd, "form_data is empty or missing"
    missing = [k for k in EXPECTED_KEYS if k not in fd]
    assert not missing, f"Missing camelCase keys in form_data: {missing}"
    # value assertions for the critical fields the user reported broken
    assert fd['nascimento'] == FORM_DATA['nascimento']
    assert fd['nomeMae'] == FORM_DATA['nomeMae']
    assert fd['endereco'] == FORM_DATA['endereco']
    assert fd['cidade'] == FORM_DATA['cidade']
    assert fd['uf'] == FORM_DATA['uf']
    assert fd['tel1'] == FORM_DATA['tel1']
    assert fd['tel2'] == FORM_DATA['tel2']
    assert fd['tel1Tipo'] == FORM_DATA['tel1Tipo']
    assert fd['tel2Tipo'] == FORM_DATA['tel2Tipo']
    assert fd['pcd'] == FORM_DATA['pcd']
    assert fd['sexo'] == FORM_DATA['sexo']
    assert fd['cep'] == FORM_DATA['cep']
    assert fd['numero'] == FORM_DATA['numero']
    assert fd['complemento'] == FORM_DATA['complemento']
    assert fd['bairro'] == FORM_DATA['bairro']
    assert fd['email'] == FORM_DATA['email']
