"""
Tests for Telegram notification flow (iteration 30):
- Validates POST /api/track/registration with stage=inscricao_finalizada persists inscricao
- Validates Telegram message format via _build_telegram_message (default title = "NOVA INSCRIÇÃO BARCARENA")
- Validates send→edit flow: first call sets telegram_message_id, subsequent pix-* calls keep same ID
- Telegram is temporarily disabled (telegram_enabled=false) to avoid polluting the real chat.
"""
import os
import sys
import time
import pytest
import requests

# Load backend .env so MONGO_URL/DB_NAME are available
try:
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
except Exception:
    pass

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # fallback to .env file
    try:
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break
    except Exception:
        pass

ADMIN_USER = 'donas'
ADMIN_PASS = 'Seinao10@@'
TEST_CPF = '99988877766'  # CPF de teste único, não-real

# Add backend to import path for direct function tests
sys.path.insert(0, '/app/backend')


# ----------------- Fixtures -----------------
@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/admin/auth/login",
        json={'username': ADMIN_USER, 'password': ADMIN_PASS},
        timeout=10,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()['token']


@pytest.fixture(scope='module')
def auth_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}'}


@pytest.fixture(scope='module')
def original_settings(auth_headers):
    """Save current settings, then disable telegram for tests. Restore after."""
    r = requests.get(f"{BASE_URL}/api/admin/settings", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    saved = r.json()

    # Disable telegram to NOT pollute real chat
    requests.put(
        f"{BASE_URL}/api/admin/settings",
        headers=auth_headers,
        json={'telegram_enabled': False},
        timeout=10,
    )
    yield saved
    # Restore original settings (especially telegram_enabled=True)
    requests.put(
        f"{BASE_URL}/api/admin/settings",
        headers=auth_headers,
        json={'telegram_enabled': bool(saved.get('telegram_enabled', True))},
        timeout=10,
    )


@pytest.fixture(scope='module', autouse=True)
def cleanup_after(original_settings, auth_headers):
    """After tests, delete test inscription by CPF and reset telegram_message_id on it."""
    yield
    # delete any inscriptions for TEST_CPF directly via mongo through a script
    try:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME')
        if mongo_url and db_name:
            async def _clean():
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]
                await db.inscricoes.delete_many({'cpf': TEST_CPF})
                await db.cadastros.delete_many({'cpf': TEST_CPF})
                await db.registrations.delete_many({'cpf': TEST_CPF})
                await db.pix_generated.delete_many({'cpf': TEST_CPF})
                await db.pix_copied.delete_many({'cpf': TEST_CPF})
                await db.pix_downloaded.delete_many({'cpf': TEST_CPF})
                client.close()
            asyncio.run(_clean())
    except Exception as e:
        print(f"Cleanup error (non-fatal): {e}")


# ----------------- Tests -----------------
class TestTelegramMessageBuilder:
    """Direct unit tests on _build_telegram_message (no network)."""

    def test_default_title_is_barcarena(self):
        from admin_routes import _build_telegram_message
        msg = _build_telegram_message({'nome': 'João Teste', 'cpf': TEST_CPF, 'valor': 50.0}, settings={})
        assert 'NOVA INSCRIÇÃO BARCARENA' in msg, f"Title not Barcarena: {msg[:200]}"
        assert 'NOVA INSCRIÇÃO PND' not in msg, "Old title still present"

    def test_message_has_all_seven_lines(self):
        from admin_routes import _build_telegram_message
        insc = {
            'nome': 'Maria Silva',
            'cpf': TEST_CPF,
            'valor': 85.5,
            'device': 'mobile',
            'city': 'Barcarena',
            'uf': 'PA',
            'pix_status': 'PIX gerado',
        }
        msg = _build_telegram_message(insc, settings={})
        # 7 required lines (emojis + labels)
        assert '👤' in msg and 'Usuário' in msg, 'Missing Usuário line'
        assert '🔐' in msg and 'CPF' in msg, 'Missing CPF line'
        assert '📅' in msg and 'Data/hora' in msg, 'Missing Data/hora line'
        assert '📱' in msg and 'Dispositivo' in msg, 'Missing Dispositivo line'
        assert '📍' in msg and 'Local' in msg, 'Missing Local line'
        assert '💰' in msg and 'Valor' in msg, 'Missing Valor line'
        assert '📊' in msg and 'Status' in msg, 'Missing Status line'
        # HTML formatting
        assert '<b>' in msg and '</b>' in msg, 'Missing HTML bold tags'
        # Formatted CPF
        assert '999.888.777-66' in msg, f'CPF not formatted: {msg}'
        # Device
        assert 'Mobile' in msg
        # Local
        assert 'Barcarena' in msg and 'PA' in msg
        # Valor BRL
        assert 'R$' in msg and '85,50' in msg, f'Valor not formatted: {msg}'
        # Status with emoji
        assert 'PIX gerado' in msg and '🔵' in msg


class TestTrackRegistrationFlow:
    """Tests for HTTP flow: POST /api/track/registration → inscricao persisted"""

    def test_registration_persists_inscricao(self, original_settings, auth_headers):
        # Telegram disabled in fixture; ensure clean slate for TEST_CPF
        payload = {
            'page': '/inscricao-passo2.html',
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605',
            'extra': {
                'stage': 'inscricao_finalizada',
                'nome': 'TEST Telegram Flow',
                'cpf': TEST_CPF,
                'cargo_codigo': 'TST001',
                'cargo_titulo': 'Cargo Teste',
                'localidade': 'Barcarena/PA',
                'valor': 50.0,
                'taxa': 'R$ 50,00',
                'protocolo': 'TST-99999',
                'concurso': 'ENARE 2026 Teste',
            },
        }
        r = requests.post(f"{BASE_URL}/api/track/registration", json=payload, timeout=15)
        assert r.status_code == 200, f"track/registration failed: {r.status_code} {r.text}"
        assert r.json().get('ok') is True

        # Verify persistence via admin endpoint
        time.sleep(0.5)
        r2 = requests.get(
            f"{BASE_URL}/api/admin/inscriptions",
            headers=auth_headers,
            params={'q': TEST_CPF},
            timeout=10,
        )
        assert r2.status_code == 200
        items = r2.json().get('items', [])
        match = [i for i in items if i.get('cpf') == TEST_CPF]
        assert len(match) >= 1, f"Inscricao not persisted for CPF {TEST_CPF}. Items: {items}"
        insc = match[0]
        assert insc.get('status') == 'Aguardando pagamento', f"Wrong initial status: {insc.get('status')}"
        assert insc.get('protocolo') == 'TST-99999'
        assert insc.get('cargo_titulo') == 'Cargo Teste'

    def test_pix_status_transitions(self, auth_headers):
        """After pix-generated / pix-copied / pix-downloaded, pix_status updates."""
        common_extra = {
            'cpf': TEST_CPF,
            'nome': 'TEST Telegram Flow',
            'cargo_codigo': 'TST001',
            'protocolo': 'TST-99999',
            'valor': 50.0,
        }

        for endpoint, expected in [
            ('/api/track/pix-generated', 'PIX gerado'),
            ('/api/track/pix-copied', 'PIX copiado'),
            ('/api/track/pix-downloaded', 'PIX baixado'),
        ]:
            r = requests.post(
                f"{BASE_URL}{endpoint}",
                json={'page': '/pagamento.html', 'extra': common_extra},
                timeout=15,
            )
            assert r.status_code == 200, f"{endpoint} failed: {r.text}"
            time.sleep(0.4)
            r2 = requests.get(
                f"{BASE_URL}/api/admin/inscriptions",
                headers=auth_headers,
                params={'q': TEST_CPF},
                timeout=10,
            )
            assert r2.status_code == 200
            items = [i for i in r2.json().get('items', []) if i.get('cpf') == TEST_CPF]
            assert items, f"Inscricao disappeared after {endpoint}"
            assert items[0].get('status') == expected, (
                f"Status after {endpoint}: expected '{expected}', got '{items[0].get('status')}'"
            )


class TestNotifyOrUpdateLogic:
    """Direct integration test: verifies first call SENDS, subsequent calls EDIT.
    We monkeypatch _telegram_send and _telegram_edit to avoid hitting real Telegram API.
    """

    def test_send_then_edit_keeps_message_id(self, monkeypatch, original_settings, auth_headers):
        # Enable telegram with FAKE creds + monkeypatched send/edit
        requests.put(
            f"{BASE_URL}/api/admin/settings",
            headers=auth_headers,
            json={'telegram_enabled': True, 'telegram_bot_token': 'FAKE_TOKEN', 'telegram_chat_id': '111'},
            timeout=10,
        )
        try:
            import asyncio
            import admin_routes
            from motor.motor_asyncio import AsyncIOMotorClient

            mongo_url = os.environ.get('MONGO_URL')
            db_name = os.environ.get('DB_NAME')
            assert mongo_url and db_name, "MONGO_URL/DB_NAME not set"

            send_calls = []
            edit_calls = []

            async def fake_send(token, chat, text):
                send_calls.append({'text': text})
                return {'ok': True, 'message_id': 424242}

            async def fake_edit(token, chat, message_id, text):
                edit_calls.append({'message_id': message_id, 'text': text})
                return {'ok': True}

            monkeypatch.setattr(admin_routes, '_telegram_send', fake_send)
            monkeypatch.setattr(admin_routes, '_telegram_edit', fake_edit)

            async def _run():
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]
                admin_routes.set_db(db)
                # Ensure inscricao exists for TEST_CPF and reset telegram_message_id
                await db.inscricoes.update_one(
                    {'cpf': TEST_CPF},
                    {'$unset': {'telegram_message_id': ''}}
                )
                # 1st call: should SEND and persist message_id
                await admin_routes.notify_or_update_telegram(TEST_CPF, request=None, extra={'protocolo': 'TST-99999'})
                insc1 = await db.inscricoes.find_one({'cpf': TEST_CPF})
                msg_id_after_send = insc1.get('telegram_message_id') if insc1 else None

                # 2nd & 3rd calls: should EDIT (no new send)
                await admin_routes.notify_or_update_telegram(TEST_CPF, request=None, extra={'protocolo': 'TST-99999'})
                await admin_routes.notify_or_update_telegram(TEST_CPF, request=None, extra={'protocolo': 'TST-99999'})
                insc3 = await db.inscricoes.find_one({'cpf': TEST_CPF})
                msg_id_final = insc3.get('telegram_message_id') if insc3 else None
                client.close()
                return msg_id_after_send, msg_id_final

            msg_id_after_send, msg_id_final = asyncio.run(_run())

            # Assertions
            assert len(send_calls) == 1, f"Expected 1 send, got {len(send_calls)}"
            assert len(edit_calls) == 2, f"Expected 2 edits, got {len(edit_calls)}"
            assert msg_id_after_send == 424242, f"message_id not persisted: {msg_id_after_send}"
            assert msg_id_final == 424242, f"message_id changed: {msg_id_final}"
            # First send message must contain BARCARENA title
            assert 'NOVA INSCRIÇÃO BARCARENA' in send_calls[0]['text']
        finally:
            # restore telegram settings to original
            requests.put(
                f"{BASE_URL}/api/admin/settings",
                headers=auth_headers,
                json={
                    'telegram_enabled': False,  # keep disabled during rest of session; final restore in fixture
                    'telegram_bot_token': original_settings.get('telegram_bot_token', ''),
                    'telegram_chat_id': original_settings.get('telegram_chat_id', ''),
                },
                timeout=10,
            )
