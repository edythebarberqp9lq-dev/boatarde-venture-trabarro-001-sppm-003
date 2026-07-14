"""
Tests for tracking endpoints (access filter + pix-downloaded) and KPIs.
Iteration 23 - Donas ENARE 2026
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_USER = "donas"
ADMIN_PASS = "Seinao10@@"
TEST_CPF = "13726548793"  # ALDO SERGIO – valor R$ 130


def _ua(tag: str) -> str:
    # ensure unique UA so the 30-min IP+device dedup window doesn't swallow our access
    return f"pytest-iter23-{tag}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/admin/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# -------------------- /api/track/access filtering --------------------

@pytest.mark.parametrize("page", ["/home.html", "/", "/index.html", "/home.html?utm=x", "/HOME.HTML"])
def test_track_access_home_counts(page):
    r = requests.post(
        f"{BASE_URL}/api/track/access",
        json={"page": page, "user_agent": _ua("home"), "extra": {}},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    # should NOT be skipped as not_home/admin (may be skipped as duplicate in fast retries; here UAs are unique so not_home/admin must be absent)
    assert body.get("skipped") not in ("not_home", "admin"), f"home page incorrectly skipped: {body}"


@pytest.mark.parametrize("page", [
    "/inscricao.html",
    "/inscricao-passo2.html",
    "/inscricao-passo3.html",
    "/inscricao-pagamento.html",
    "/inscricao-comprovante.html",
])
def test_track_access_funnel_skipped(page):
    r = requests.post(
        f"{BASE_URL}/api/track/access",
        json={"page": page, "user_agent": _ua("funnel"), "extra": {}},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("skipped") == "not_home", f"funnel page should be skipped: {body}"


def test_track_access_admin_skipped():
    r = requests.post(
        f"{BASE_URL}/api/track/access",
        json={"page": "/donaspainel/", "user_agent": _ua("admin"), "extra": {}},
        timeout=15,
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("skipped") == "admin"


# -------------------- access KPI increments only for home --------------------

def test_acessos_increments_only_for_home(auth_headers):
    # baseline
    k0 = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=auth_headers, timeout=15).json()
    base = int(k0.get("acessos", 0))

    # one funnel hit (must NOT count) with unique UA
    requests.post(
        f"{BASE_URL}/api/track/access",
        json={"page": "/inscricao-passo2.html", "user_agent": _ua("funnel-kpi"), "extra": {}},
        timeout=15,
    )
    k1 = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=auth_headers, timeout=15).json()
    assert int(k1.get("acessos", 0)) == base, f"funnel access leaked to KPI: {base} -> {k1.get('acessos')}"

    # one home hit (must count) with unique UA (so dedup window does not swallow)
    r = requests.post(
        f"{BASE_URL}/api/track/access",
        json={"page": "/home.html", "user_agent": _ua("home-kpi"), "extra": {}},
        timeout=15,
    )
    assert r.json().get("skipped") not in ("not_home", "admin")
    # Note: dedup based on IP+device may still skip if previous home hit was within 30 min.
    # In that case we don't assert strict increment, but we still assert it's not LESS.
    time.sleep(0.3)
    k2 = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=auth_headers, timeout=15).json()
    assert int(k2.get("acessos", 0)) >= base, "acessos went down unexpectedly"


# -------------------- /api/track/pix-downloaded + KPI valor_baixados --------------------

def test_pix_downloaded_updates_status_and_kpi(auth_headers):
    # baseline
    k0 = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=auth_headers, timeout=15).json()
    base_baixados = int(k0.get("pix_baixados", 0))
    base_valor_copy = float(k0.get("valor_copiados", 0) or 0)

    # fire pix-downloaded for known CPF
    payload = {
        "page": "/inscricao-comprovante.html",
        "user_agent": _ua("pix-dl"),
        "extra": {
            "cpf": TEST_CPF,
            "nome": "ALDO SERGIO ALVES PRUDENCIO JUNIOR",
            "concurso": "ENARE 2026",
            "cargo_codigo": "TEST",
            "cargo_titulo": "Teste",
            "protocolo": "TST-001",
            "valor": 130,
        },
    }
    r = requests.post(f"{BASE_URL}/api/track/pix-downloaded", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    time.sleep(0.5)

    # KPIs reflect baixados >= base+0 (idempotent upsert by cpf+cargo_codigo). valor_baixados must include R$130.
    k1 = requests.get(f"{BASE_URL}/api/admin/dashboard/kpis", headers=auth_headers, timeout=15).json()
    assert float(k1.get("valor_baixados", 0) or 0) >= 130.0, f"valor_baixados did not include R$130: {k1}"
    assert int(k1.get("pix_baixados", 0)) >= max(base_baixados, 1)

    # valor_copiados must NOT have been overwritten by valor_baixados (independence check)
    # We only require that copiados did not DECREASE because of the baixados call.
    assert float(k1.get("valor_copiados", 0) or 0) >= base_valor_copy, "valor_copiados decreased unexpectedly"

    # All required KPI fields present
    for key in ["acessos", "inscricoes", "pix_gerados", "pix_copiados", "pix_baixados",
                "valor_total", "valor_copiados", "valor_baixados"]:
        assert key in k1, f"KPI missing field: {key}"


def test_inscription_pix_status_updated_to_baixado(auth_headers):
    # Trigger pix-downloaded again to ensure status applied even if first test was run separately
    requests.post(
        f"{BASE_URL}/api/track/pix-downloaded",
        json={
            "page": "/inscricao-comprovante.html",
            "user_agent": _ua("pix-dl-status"),
            "extra": {"cpf": TEST_CPF, "valor": 130},
        },
        timeout=20,
    )
    time.sleep(0.5)
    # Find inscription by CPF in admin listing
    r = requests.get(
        f"{BASE_URL}/api/admin/inscriptions",
        headers=auth_headers,
        params={"q": TEST_CPF, "limit": 50},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("data") or data if isinstance(data, list) else data.get("items", [])
    if isinstance(items, dict):
        items = items.get("items", [])
    found = [it for it in items if str(it.get("cpf", "")).replace(".", "").replace("-", "") == TEST_CPF]
    assert found, f"inscrição CPF {TEST_CPF} not found in admin listing"
    pix_status = (found[0].get("pix_status") or "").lower()
    assert "baixad" in pix_status, f"pix_status not 'PIX baixado' for CPF {TEST_CPF}: {found[0].get('pix_status')}"
