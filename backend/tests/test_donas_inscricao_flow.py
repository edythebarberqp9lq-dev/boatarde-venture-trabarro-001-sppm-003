"""E2E test for donas inscricao registration flow + admin listing.

Covers:
 - POST /api/inscricoes/register with valid CPF + multipart uploads
 - Duplicate CPF -> 409
 - Admin login + GET /api/admin/inscriptions returns the record with expected fields
"""

import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
CPF_OK = "11144477735"

# tiny valid PNG (1x1) generated once for both files
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626000000000ffff030000060005575adaa30000000049454e44ae426082"
)


def _files():
    return {
        "doc_frente": ("f.png", io.BytesIO(PNG_BYTES), "image/png"),
        "doc_verso": ("v.png", io.BytesIO(PNG_BYTES), "image/png"),
    }


def _payload(nome="JOAO DA SILVA TESTE"):
    return {
        "nome": nome,
        "cpf": CPF_OK,
        "data_nascimento": "15/06/1990",
        "sexo": "M",
        "email": "joao@teste.com",
        "tipo_documento": "RG",
        "endereco_cep": "01310100",
        "endereco_rua": "AVENIDA PAULISTA",
        "endereco_numero": "1000",
        "endereco_complemento": "",
        "endereco_bairro": "BELA VISTA",
        "endereco_cidade": "SÃO PAULO",
        "endereco_estado": "SP",
        "celular": "11987654321",
        "senha": "Test1234A",
        "senha2": "Test1234A",
        "flag_deficiente": "1",
    }


# ------------------------- Registration ---------------------------
class TestInscricaoRegister:
    def test_register_ok(self):
        r = requests.post(
            f"{BASE_URL}/api/inscricoes/register",
            data=_payload(),
            files=_files(),
            timeout=30,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") is True or data.get("success") is True or "id" in data or "protocolo" in data, data

    def test_register_duplicate_cpf(self):
        r = requests.post(
            f"{BASE_URL}/api/inscricoes/register",
            data=_payload(),
            files=_files(),
            timeout=30,
        )
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
        body = r.text
        assert "CPF" in body or "cpf" in body


# ------------------------- Admin ---------------------------------
class TestAdminInscriptions:
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(
            f"{BASE_URL}/api/admin/auth/login",
            json={"username": "donas", "password": "Seinao10@@"},
            timeout=15,
        )
        assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
        tok = r.json().get("token") or r.json().get("access_token")
        assert tok, f"no token in response: {r.json()}"
        return tok

    def test_inscriptions_listing_contains_new_record(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/inscriptions",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        payload = r.json()
        items = payload if isinstance(payload, list) else payload.get("items") or payload.get("data") or []
        assert isinstance(items, list) and len(items) >= 1, f"no items returned: {payload}"

        # find our CPF (accept both masked and unmasked variants)
        target = None
        for it in items:
            cpf_val = str(it.get("cpf", "")).replace(".", "").replace("-", "")
            if cpf_val == CPF_OK:
                target = it
                break
        assert target is not None, f"CPF {CPF_OK} not found among {[i.get('cpf') for i in items]}"

        assert (target.get("nome") or "").upper() == "JOAO DA SILVA TESTE"
        assert target.get("tipo_documento") == "RG"
        # deficiente flag can be under different names
        defic = target.get("flag_deficiente")
        if defic is None:
            defic = target.get("deficiente") or target.get("pcd")
        assert defic in (True, "1", 1, "true", "True"), f"flag_deficiente not true: {defic}"

        endereco = target.get("endereco") or {}
        rua = (endereco.get("rua") or target.get("endereco_rua") or "").upper()
        cidade = (endereco.get("cidade") or target.get("endereco_cidade") or "").upper()
        assert "PAULISTA" in rua, f"rua not persisted: {rua}"
        assert "SÃO PAULO" in cidade or "SAO PAULO" in cidade, f"cidade not persisted: {cidade}"
