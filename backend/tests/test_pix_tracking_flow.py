"""Iter 11: verify pix-generated and pix-copied tracking endpoints update inscricao pix_status and increment KPIs."""
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL
ADMIN_USER, ADMIN_PASS = "donas", "Seinao10@@"
TEST_CPF = "11144477735"

@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/admin/auth/login", json={"username":ADMIN_USER,"password":ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]

@pytest.fixture(scope="session")
def hdr(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session", autouse=True)
def seed_inscricao():
    # Create a finalized inscricao via /api/track/registration so pix_status defaults exist
    payload = {"page":"pagamento","user_agent":"pytest","extra":{
        "cpf":TEST_CPF,"nome":"JOAO SILVA TESTE","email":"joao@teste.com",
        "concurso":"PREFEITURA ALTOS","edital":"01/2026","cargo_codigo":"AGENTE_ADM",
        "cargo_titulo":"AGENTE ADMINISTRATIVO","valor":110,"stage":"inscricao_finalizada","finalized":True}}
    r = requests.post(f"{BASE_URL}/api/track/registration", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    time.sleep(0.4)

def test_pix_generated_endpoint(hdr):
    payload = {"page":"pagamento","user_agent":"pytest","extra":{
        "cpf":TEST_CPF,"nome":"JOAO SILVA TESTE","valor":110,"cargo_codigo":"AGENTE_ADM","vaga":"AGENTE ADMINISTRATIVO"}}
    r = requests.post(f"{BASE_URL}/api/track/pix-generated", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    time.sleep(0.4)
    # Verify pix_status == 'PIX gerado' via admin listing
    r2 = requests.get(f"{BASE_URL}/api/admin/inscriptions", headers=hdr, params={"q":TEST_CPF,"limit":10}, timeout=20)
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    found = [i for i in items if i.get("cpf")==TEST_CPF]
    assert found, f"no inscricao for {TEST_CPF}"
    assert found[0].get("pix_status") == "PIX gerado", f"got {found[0].get('pix_status')}"

def test_pix_copied_endpoint(hdr):
    payload = {"page":"pagamento","user_agent":"pytest","extra":{
        "cpf":TEST_CPF,"nome":"JOAO SILVA TESTE","valor":110,"cargo_codigo":"AGENTE_ADM","vaga":"AGENTE ADMINISTRATIVO"}}
    r = requests.post(f"{BASE_URL}/api/track/pix-copied", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    time.sleep(0.4)
    r2 = requests.get(f"{BASE_URL}/api/admin/inscriptions", headers=hdr, params={"q":TEST_CPF,"limit":10}, timeout=20)
    items = r2.json().get("items", [])
    found = [i for i in items if i.get("cpf")==TEST_CPF]
    assert found and found[0].get("pix_status") == "PIX copiado", f"got {found and found[0].get('pix_status')}"

def test_kpis_reflect_pix_counts(hdr):
    r = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=hdr, timeout=15)
    assert r.status_code == 200
    k = r.json()
    assert int(k.get("pix_gerados",0)) >= 1, k
    assert int(k.get("pix_copiados",0)) >= 1, k

def test_pagamento_html_has_tracking_calls():
    r = requests.get(f"{BASE_URL}/pagamento.html", timeout=20)
    assert r.status_code == 200
    txt = r.text
    assert "/api/track/pix-generated" in txt, "pagamento.html missing pix-generated call"
    assert "/api/track/pix-copied" in txt, "pagamento.html missing pix-copied call"
    assert "pgto-copiar" in txt
