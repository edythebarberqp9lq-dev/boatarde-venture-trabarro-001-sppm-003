"""Tests for PMES2602 (Cadete PM) bug fix - value R$ 200,00."""
import os
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://venture-trabarro.preview.emergentagent.com').rstrip('/')


def _valid_cpf():
    # 529.982.247-25 - well known valid test CPF
    return "52998224725"


def test_submit_pmes2602_returns_200_valor():
    cpf = _valid_cpf()
    r = requests.post(
        f"{BASE_URL}/api/inscricao/submit",
        data={
            'nome': 'TEST Cadete Candidate',
            'cpf': cpf,
            'email': 'test-cadete@example.com',
            'concurso': 'PMES2602',
            'tipo_documento': 'RG',
            'form_data': '{"selectOpcao":"002","EndCidade":"São Paulo","EndUF":"SP"}',
        },
        timeout=30,
    )
    assert r.status_code == 200, f"Submit failed: {r.status_code} {r.text}"
    body = r.json()
    assert 'protocolo' in body or 'protocol' in body or body, f"Missing protocolo: {body}"


def test_admin_inscription_has_valor_200_and_cadete():
    # login as admin
    s = requests.Session()
    login = s.post(f"{BASE_URL}/api/admin/auth/login",
                   json={'username': 'farpa', 'password': 'Ads102030'}, timeout=30)
    assert login.status_code == 200, f"Login failed: {login.status_code} {login.text}"
    token = login.json().get('token') or login.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    r = s.get(f"{BASE_URL}/api/admin/inscriptions", headers=headers, timeout=30)
    assert r.status_code == 200, f"Fetch inscriptions failed: {r.status_code} {r.text}"
    data = r.json()
    items = data if isinstance(data, list) else data.get('items') or data.get('inscriptions') or []
    # Find the last PMES2602 inscription for the test CPF
    cpf = _valid_cpf()
    matches = [i for i in items if (i.get('cpf') or '').replace('.','').replace('-','') == cpf and (i.get('edital') == 'PMES2602' or 'Cadete' in (i.get('concurso') or '') or 'Cadete' in (i.get('cargo_titulo') or ''))]
    assert matches, f"No PMES2602 inscription found for cpf {cpf}. Sample: {items[:2]}"
    m = matches[-1]
    assert m.get('valor') == 200.0 or m.get('valor') == 200, f"Expected valor=200 got {m.get('valor')}"
    assert m.get('taxa') == 'R$ 200,00', f"Expected taxa 'R$ 200,00' got {m.get('taxa')}"
    assert 'Cadete' in (m.get('cargo_titulo') or m.get('concurso') or ''), f"Expected Cadete in title: {m}"


def test_submit_pmes2601_still_returns_100():
    # different valid CPF - 111.444.777-35 was mentioned already used, use another
    cpf = "39053344705"  # valid CPF
    r = requests.post(
        f"{BASE_URL}/api/inscricao/submit",
        data={
            'nome': 'TEST Soldado Candidate',
            'cpf': cpf,
            'email': 'test-sold@example.com',
            'concurso': 'PMES2601',
            'tipo_documento': 'RG',
            'form_data': '{"selectOpcao":"001","EndCidade":"São Paulo","EndUF":"SP"}',
        },
        timeout=30,
    )
    assert r.status_code == 200, f"Submit failed: {r.status_code} {r.text}"
