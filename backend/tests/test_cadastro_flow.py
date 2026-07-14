"""
Regression tests for the public /cadastro.html flow:
- POST /api/track/registration (stage=cadastro) persists in _db.cadastros
- GET /api/cadastro/{cpf} returns saved form_data (autofill source)
- Admin: GET /api/admin/cadastros lists the CPF
- Admin: GET /api/admin/documents lists candidate with doc data
"""
import os
import base64
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'
TEST_CPF = '11144477735'  # valid CPF digits
TEST_NOME = 'Maria Teste Silva'
TEST_EMAIL = 'maria@teste.com'

TINY_PNG_B64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAFRAwpaAAAA'
    'AElFTkSuQmCC'
)
DATA_URL = f'data:image/png;base64,{TINY_PNG_B64}'


@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(
        f'{BASE_URL}/api/admin/auth/login',
        json={'username': ADMIN_USER, 'password': ADMIN_PASS},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    tok = r.json().get('token')
    assert tok
    return tok


@pytest.fixture(scope='module')
def submitted_form_data():
    """Submits the cadastro payload (mirrors what /cadastro.html sends)."""
    form_data = {
        'nome': TEST_NOME,
        'cpf': '111.444.777-35',
        'nascimento': '10/02/1995',
        'sexo': 'Feminino',
        'escolaridade': 'Ensino Superior',
        'nomeMae': 'Ana Silva Teste',
        'cep': '77804-020',
        'endereco': 'Rua Gaúcha',
        'numero': '100',
        'bairro': 'Setor Central',
        'cidade': 'Araguaína',
        'uf': 'TO',
        'tel1': '(63) 99888-7777',
        'email': TEST_EMAIL,
        'pcd': 'Não',
        'docTipo': 'RG',
        'docNumero': '1234567',
        'rg': '1234567',
        'docArquivoData': DATA_URL,
        'docArquivoNome': 'frente.png',
        'docArquivoTipo': 'image/png',
        'docArquivoSize': 69,
        'docArquivoVersoData': DATA_URL,
        'docArquivoVersoNome': 'verso.png',
        'docArquivoVersoTipo': 'image/png',
        'docArquivoVersoSize': 69,
    }
    payload = {
        'page': '/cadastro.html',
        'extra': {
            'stage': 'cadastro',
            'nome': TEST_NOME,
            'cpf': TEST_CPF,
            'email': TEST_EMAIL,
            'concurso': '',
            'form_data': form_data,
        },
    }
    r = requests.post(f'{BASE_URL}/api/track/registration', json=payload, timeout=20)
    assert r.status_code == 200, r.text
    return form_data


# -------------- Autofill endpoint --------------
class TestCadastroPublic:
    def test_get_cadastro_returns_form_data(self, submitted_form_data):
        r = requests.get(f'{BASE_URL}/api/cadastro/{TEST_CPF}', timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data['ok'] is True
        assert data['cpf'] == TEST_CPF
        assert data['nome'] == TEST_NOME
        assert data['email'] == TEST_EMAIL
        fd = data.get('form_data') or {}
        # Required autofill fields
        assert fd.get('nome') == TEST_NOME
        assert fd.get('nascimento') == '10/02/1995'
        assert fd.get('sexo') == 'Feminino'
        assert fd.get('cidade') == 'Araguaína'
        assert fd.get('uf') == 'TO'
        assert fd.get('tel1') == '(63) 99888-7777'
        assert fd.get('email') == TEST_EMAIL
        assert fd.get('docTipo') == 'RG'
        assert fd.get('docNumero') == '1234567'
        # Document data (base64 non-empty)
        assert fd.get('docArquivoData', '').startswith('data:image/')
        assert fd.get('docArquivoVersoData', '').startswith('data:image/')

    def test_get_cadastro_invalid_cpf_400(self):
        r = requests.get(f'{BASE_URL}/api/cadastro/12345', timeout=15)
        assert r.status_code == 400

    def test_get_cadastro_unknown_cpf_404(self):
        r = requests.get(f'{BASE_URL}/api/cadastro/99999999999', timeout=15)
        assert r.status_code == 404


# -------------- Admin listings --------------
class TestAdminIntegration:
    def test_admin_cadastros_lists_cpf(self, admin_token, submitted_form_data):
        r = requests.get(
            f'{BASE_URL}/api/admin/cadastros',
            params={'q': TEST_CPF},
            headers={'Authorization': f'Bearer {admin_token}'},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get('items', [])
        assert data['total'] >= 1
        match = [it for it in items if it.get('cpf') == TEST_CPF]
        assert match, f'CPF {TEST_CPF} not in cadastros list'
        assert match[0].get('nome') == TEST_NOME
        assert match[0].get('email') == TEST_EMAIL

    def test_admin_documents_lists_candidate(self, admin_token, submitted_form_data):
        r = requests.get(
            f'{BASE_URL}/api/admin/documents',
            params={'q': TEST_CPF},
            headers={'Authorization': f'Bearer {admin_token}'},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get('items', [])
        match = [it for it in items if it.get('cpf') == TEST_CPF]
        assert match, f'CPF {TEST_CPF} not in documents list'
        it = match[0]
        assert it.get('doc_tipo') == 'RG'
        assert it.get('frente_nome') == 'frente.png'
        assert it.get('has_verso') is True

    def test_admin_documents_requires_auth(self):
        r = requests.get(f'{BASE_URL}/api/admin/documents', timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_cadastros_requires_auth(self):
        r = requests.get(f'{BASE_URL}/api/admin/cadastros', timeout=15)
        assert r.status_code in (401, 403)
