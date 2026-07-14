"""Backend tests for streaming behavior of POST /api/admin/documents/export-zip.

Validates the SpooledTemporaryFile + StreamingResponse refactor:
- Response is streamed in chunks (Transfer-Encoding: chunked OR no Content-Length).
- CNH filter returns only the JOAO CNH ZIP.
- Headers X-Total-Files and X-Total-Candidates are present and correct.
- ZIP is still valid and openable.
"""
import io
import os
import zipfile

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'http://localhost:8001'

ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'

EXPORT_URL = f"{BASE_URL}/api/admin/documents/export-zip"
LOGIN_URL = f"{BASE_URL}/api/admin/auth/login"

CPF_MARIA = '11111111101'  # RG
CPF_JOAO = '22222222202'   # CNH
CPF_ANA = '33333333303'    # Passaporte


@pytest.fixture(scope='module')
def auth_headers():
    r = requests.post(LOGIN_URL, json={'username': ADMIN_USER, 'password': ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, f'login falhou: {r.status_code} {r.text[:200]}'
    tok = r.json().get('token') or r.json().get('access_token')
    assert tok
    return {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}


class TestStreamingBehavior:
    """Verifies SpooledTemporaryFile + StreamingResponse refactor."""

    def test_response_is_streamed_no_content_length(self, auth_headers):
        """StreamingResponse should not set Content-Length; should use Transfer-Encoding: chunked."""
        # use stream=True to inspect headers without buffering
        r = requests.post(EXPORT_URL, headers=auth_headers, json={}, timeout=60, stream=True)
        try:
            assert r.status_code == 200
            cl = r.headers.get('Content-Length')
            te = r.headers.get('Transfer-Encoding', '').lower()
            # Either chunked transfer-encoding OR absence of content-length indicates streaming
            assert (te == 'chunked') or (cl is None), (
                f"Esperado streaming (Transfer-Encoding chunked OU sem Content-Length). "
                f"Recebido Content-Length={cl} Transfer-Encoding={te}"
            )
            assert r.headers.get('content-type', '').startswith('application/zip')
            # verify headers X-Total-* exist
            assert int(r.headers.get('X-Total-Files', '0')) >= 5
            assert int(r.headers.get('X-Total-Candidates', '0')) >= 3
        finally:
            r.close()

    def test_streamed_zip_is_valid_when_read_in_chunks(self, auth_headers):
        """Read response iteratively in chunks and verify resulting ZIP is openable."""
        r = requests.post(EXPORT_URL, headers=auth_headers, json={}, timeout=60, stream=True)
        try:
            assert r.status_code == 200
            buf = io.BytesIO()
            chunks_read = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    buf.write(chunk)
                    chunks_read += 1
            buf.seek(0)
            zf = zipfile.ZipFile(buf)
            names = zf.namelist()
            assert len(names) >= 5
            # ZIP integrity check
            assert zf.testzip() is None, "ZIP file integrity check failed"
            assert chunks_read >= 1
        finally:
            r.close()


class TestCNHFilter:
    """Per review request: body {tipo:'CNH'} returns ZIP only with CNH JOÃO."""

    def test_filter_by_tipo_CNH_returns_only_CNH(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'tipo': 'CNH'}, timeout=30)
        assert r.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        # all files must start with CNH_
        for n in names:
            base = n.split('/')[1]
            assert base.startswith('CNH_'), f'arquivo não-CNH encontrado: {n}'
        # folder must be JOAO's CPF
        folders = {n.split('/')[0] for n in names if '/' in n}
        assert len(folders) == 1
        assert next(iter(folders)).startswith(CPF_JOAO + '_'), f'esperado pasta {CPF_JOAO}_*, recebido {folders}'
        # X-Total-Candidates = 1
        assert r.headers.get('X-Total-Candidates') == '1', r.headers.get('X-Total-Candidates')

    def test_filter_single_cpf_joao_returns_cnh_files(self, auth_headers):
        r = requests.post(EXPORT_URL, headers=auth_headers, json={'cpfs': [CPF_JOAO]}, timeout=30)
        assert r.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        folders = {n.split('/')[0] for n in names if '/' in n}
        assert len(folders) == 1
        assert next(iter(folders)).startswith(CPF_JOAO + '_')
        # CNH JOAO has frente + verso => 2 files
        assert len(names) == 2, f'esperado 2 arquivos CNH, recebido {names}'
        assert all(n.split('/')[1].startswith('CNH_') for n in names)
