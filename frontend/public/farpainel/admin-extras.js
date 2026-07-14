/* global IdecanNotice, WorkerGlobalScope, __REACT_DEVTOOLS_GLOBAL_HOOK__ */
/* eslint-disable */
/* oxlint-disable */
/* ============================================================
   IDECAN — Painel Admin (Donnas): extras
   Adiciona um botão "Limpar Cadastros" na página /farpainel/cadastro
   sem precisar mexer no build React.
   ============================================================ */
(function () {
  var API = '/api';
  var BTN_ID = 'admin-extra-limpar-cadastros';

  function getToken() {
    var keys = ['donas_admin_token', 'donas_token', 'admin_token', 'token', 'authToken', 'jwt'];
    for (var i = 0; i < keys.length; i++) {
      var v = localStorage.getItem(keys[i]) || sessionStorage.getItem(keys[i]);
      if (v && v.length > 10) return v.replace(/^"|"$/g, '');
    }
    return null;
  }

  function injectStyles() {
    if (document.getElementById('admin-extras-css')) return;
    var s = document.createElement('style');
    s.id = 'admin-extras-css';
    s.textContent = ''
      + '#' + BTN_ID + '{display:inline-flex;align-items:center;gap:8px;'
      + 'padding:10px 16px;border-radius:10px;background:linear-gradient(180deg,#ef4444,#b91c1c);'
      + 'color:#fff;font-weight:600;font-size:13.5px;cursor:pointer;border:0;'
      + 'box-shadow:0 6px 14px rgba(220,38,38,.35);transition:transform .12s, box-shadow .12s;'
      + 'font-family:inherit;margin-left:8px}'
      + '#' + BTN_ID + ':hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(220,38,38,.45)}'
      + '#' + BTN_ID + ':disabled{opacity:.6;cursor:not-allowed;transform:none}'
      /* botão Exibir na linha do candidato */
      + '.adm-view-btn{display:inline-flex;align-items:center;justify-content:center;'
      + 'width:34px;height:34px;border-radius:8px;background:#eef0ff;color:#5b21b6;border:1px solid #d6dafd;'
      + 'cursor:pointer;margin-right:6px;font-size:15px;line-height:1;transition:transform .1s, background .1s}'
      + '.adm-view-btn:hover{background:#dde0ff;transform:translateY(-1px)}'
      /* modal de detalhes */
      + '#adm-details-back{position:fixed;inset:0;background:rgba(8,16,32,.55);'
      + 'display:flex;align-items:center;justify-content:center;z-index:2147483646;'
      + 'opacity:0;transition:opacity .18s ease;padding:16px;'
      + 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}'
      + '#adm-details-back.show{opacity:1}'
      + '#adm-details{background:#fff;border-radius:14px;max-width:680px;width:100%;max-height:90vh;'
      + 'overflow:auto;box-shadow:0 24px 60px rgba(0,0,0,.35);transform:translateY(8px) scale(.98);'
      + 'transition:transform .22s cubic-bezier(.2,.8,.2,1)}'
      + '#adm-details-back.show #adm-details{transform:translateY(0) scale(1)}'
      + '#adm-details .adm-d-head{display:flex;align-items:center;justify-content:space-between;'
      + 'padding:18px 22px;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;border-radius:14px 14px 0 0}'
      + '#adm-details .adm-d-head h3{margin:0;font-size:17px;font-weight:700}'
      + '#adm-details .adm-d-close{background:rgba(255,255,255,.2);border:0;color:#fff;width:32px;height:32px;'
      + 'border-radius:50%;cursor:pointer;font-size:16px;font-family:inherit;line-height:1}'
      + '#adm-details .adm-d-close:hover{background:rgba(255,255,255,.35)}'
      + '#adm-details .adm-d-body{padding:18px 22px 22px}'
      + '#adm-details .adm-d-section{margin-bottom:18px}'
      + '#adm-details .adm-d-section h4{margin:0 0 8px;color:#5b21b6;font-size:13px;font-weight:700;'
      + 'text-transform:uppercase;letter-spacing:.5px}'
      + '#adm-details .adm-d-row{display:flex;gap:8px;padding:6px 0;border-bottom:1px dashed #e5e7eb;font-size:14px}'
      + '#adm-details .adm-d-row:last-child{border-bottom:0}'
      + '#adm-details .adm-d-row b{min-width:170px;color:#374151;font-weight:600}'
      + '#adm-details .adm-d-row span{color:#111827;flex:1;word-break:break-word}';
    document.head.appendChild(s);
  }

  function isCadastroPage() {
    // Suporta tanto rota antiga (pathname) quanto HashRouter (location.hash)
    return /\/farpainel\/cadastro(\b|$|\/)/.test(location.pathname)
        || /^#\/cadastro(\b|$|\/)/.test(location.hash);
  }
  function isInscricoesPage() {
    return location.pathname.indexOf('/farpainel/inscri') === 0
        || location.hash.indexOf('#/inscri') === 0;
  }

  function ensureNoticeLib(cb) {
    // Fallback nativo: usa window.confirm/alert quando a lib externa não está disponível.
    if (!window.IdecanConfirm) {
      window.IdecanConfirm = function (msg, opts) {
        opts = opts || {};
        var title = opts.title ? opts.title + '\n\n' : '';
        return Promise.resolve(window.confirm(title + msg));
      };
    }
    if (!window.IdecanNotice) {
      window.IdecanNotice = function (msg, opts) {
        opts = opts || {};
        var title = opts.title ? opts.title + '\n\n' : '';
        window.alert(title + msg);
        return Promise.resolve(true);
      };
    }
    cb();
  }

  function findActionsContainer() {
    // O React render coloca os botões "Buscar / Atualizar / Salvar .txt" próximos do header.
    // Vamos procurar pelo botão "Atualizar" (mais estável) e anexar do lado dele.
    var btns = document.querySelectorAll('button');
    var target = null;
    btns.forEach(function (b) {
      var t = (b.textContent || '').trim().toLowerCase();
      if (t === 'salvar .txt' || t.startsWith('salvar .txt')) target = b;
    });
    if (target && target.parentElement) return target.parentElement;
    // fallback: lado do Atualizar
    btns.forEach(function (b) {
      var t = (b.textContent || '').trim().toLowerCase();
      if (t === 'atualizar') target = b;
    });
    return target ? target.parentElement : null;
  }

  function findCountBadge() {
    // Procura por um elemento com "candidatos" e número (ex.: "80 cadastros")
    var nodes = document.querySelectorAll('strong, b, span, p');
    for (var i = 0; i < nodes.length; i++) {
      var t = (nodes[i].textContent || '').trim();
      if (/^\d+\s+cadastros?\.?$/i.test(t)) return nodes[i];
    }
    return null;
  }

  function handleAuthError(status) {
    // 401/403 — apenas avisa, sem redirecionar (usuário pode estar com cache de token velho)
    if (status === 401 || status === 403) {
      if (window.IdecanNotice) {
        IdecanNotice('Sua sessão precisa ser renovada. Saia e entre novamente no painel para continuar.', { title: 'Token expirado' });
      }
      return true;
    }
    return false;
  }

  function handleClick(btn) {
    var token = getToken();
    if (!token) {
      handleAuthError(401);
      return;
    }
    ensureNoticeLib(function () {
      window.IdecanConfirm(
        'Esta ação irá apagar TODOS os cadastros (candidatos) do banco. As inscrições NÃO serão afetadas. Continuar?',
        { title: 'Limpar todos os cadastros?', okLabel: 'Sim, limpar tudo', cancelLabel: 'Cancelar' }
      ).then(function (ok) {
        if (!ok) return;
        btn.disabled = true;
        var orig = btn.textContent;
        btn.textContent = 'Limpando…';
        // Tenta DELETE primeiro; se reverse-proxy bloquear (404/405/501) ou
        // se houver problema de método (alguns servidores), faz fallback para POST.
        function doRequest(method, url) {
          return fetch(API + url, {
            method: method,
            headers: { 'Authorization': 'Bearer ' + token }
          });
        }
        doRequest('DELETE', '/admin/cadastros').then(function (r) {
          if (r.ok) return r.json();
          // Fallback para POST quando DELETE é rejeitado pelo proxy
          if ([404, 405, 501, 502, 503].indexOf(r.status) !== -1) {
            return doRequest('POST', '/admin/cadastros/clear-all').then(function (r2) {
              if (!r2.ok) {
                if (handleAuthError(r2.status)) return null;
                throw new Error('HTTP ' + r2.status);
              }
              return r2.json();
            });
          }
          if (handleAuthError(r.status)) return null;
          throw new Error('HTTP ' + r.status);
        }).then(function (j) {
          if (!j) return;
          var n = (j && j.deleted) || 0;
          window.IdecanNotice(
            n + ' cadastro(s) removido(s) com sucesso. A página será recarregada.',
            { title: 'Limpeza concluída' }
          ).then(function () { location.reload(); });
        }).catch(function (e) {
          btn.disabled = false;
          btn.textContent = orig;
          window.IdecanNotice('Erro ao limpar cadastros: ' + e.message, { title: 'Falha' });
        });
      });
    });
  }

  function ensureButton() {
    // Limpa botão "Limpar Cadastros" se não estiver na página de cadastro
    if (!isCadastroPage()) {
      var existing = document.getElementById(BTN_ID);
      if (existing) existing.remove();
    } else if (!document.getElementById(BTN_ID)) {
      var container = findActionsContainer();
      if (container) {
        injectStyles();
        var btn = document.createElement('button');
        btn.id = BTN_ID;
        btn.type = 'button';
        btn.setAttribute('data-testid', 'btn-limpar-cadastros');
        btn.innerHTML = '<span aria-hidden="true">🗑</span><span>Limpar Cadastros</span>';
        btn.addEventListener('click', function () { handleClick(btn); });
        container.appendChild(btn);
      }
    }
    // Lógica que se aplica a múltiplas páginas do painel
    injectStyles();
    if (isCadastroPage()) {
      injectViewButtons();
      overrideExportButton();
    }
    if (isInscricoesPage()) {
      enrichInscriptionRows();
    }
  }

  /* ====== Enriquece linhas da página de Inscrições: nome completo + vaga ====== */
  var _inscCache = null;
  var _inscCacheAt = 0;
  function fetchInscCache() {
    var now = Date.now();
    if (_inscCache && (now - _inscCacheAt) < 6000) return Promise.resolve(_inscCache);
    var token = getToken();
    if (!token) return Promise.resolve(null);
    return fetch(API + '/admin/inscriptions?limit=10000', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (r) { return r.json(); }).then(function (d) {
      var items = (d && (d.items || d.inscriptions)) || (Array.isArray(d) ? d : []);
      var byCpf = {};
      items.forEach(function (it) {
        var c = (it.cpf || '').replace(/\D/g, '');
        if (!byCpf[c]) byCpf[c] = [];
        byCpf[c].push(it);
      });
      _inscCache = byCpf; _inscCacheAt = now;
      return _inscCache;
    }).catch(function () { return null; });
  }

  function enrichInscriptionRows() {
    if (!isInscricoesPage()) return;
    fetchInscCache().then(function (byCpf) {
      if (!byCpf) return;
      injectInscStyles();
      // Estratégia simplificada: para cada DIV/SPAN folha com texto contendo "@",
      // sobe até achar um ancestor com CPF formatado e VALOR, e substitui o email pelo cargo.
      var candidates = document.querySelectorAll('div, span, p, td');
      candidates.forEach(function (el) {
        if (el.children.length) return;
        if (el.classList && el.classList.contains('adm-vaga-inline')) return;
        var t = (el.textContent || '').trim();
        if (!t || t.indexOf('@') < 0 || t.length > 100) return;
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t)) return;
        // sobe DOM procurando o CPF e o valor
        var row = el.parentElement;
        for (var i = 0; i < 8 && row && row !== document.body; i++) {
          if (row.hasAttribute && row.hasAttribute('data-adm-enriched')) return;
          var rt = (row.textContent || '');
          var cpfMatch = rt.match(/\d{3}\.\d{3}\.\d{3}-\d{2}/);
          var valMatch = rt.match(/R\$\s*([\d.,]+)/);
          if (cpfMatch && valMatch && rt.length < 1500) {
            var cpfDigits = cpfMatch[0].replace(/\D/g, '');
            var inscs = byCpf[cpfDigits] || [];
            if (!inscs.length) return;
            var ins = inscs[0];
            if (inscs.length > 1) {
              var rowVal = parseFloat(valMatch[1].replace(/\./g,'').replace(',','.'));
              var found = inscs.find(function (x) { return Math.abs((x.valor || 0) - rowVal) < 0.5; });
              if (found) ins = found;
            }
            var cargo = (ins.cargo_titulo || ins.cargo_codigo || '').trim();
            if (cargo) {
              el.textContent = cargo;
              el.classList.add('adm-vaga-inline');
              row.setAttribute('data-adm-enriched', '1');
            }
            return;
          }
          row = row.parentElement;
        }
      });
    });
  }

  function injectInscStyles() {
    if (document.getElementById('adm-insc-css')) return;
    var s = document.createElement('style');
    s.id = 'adm-insc-css';
    s.textContent = ''
      + '.adm-full-name{font-weight:600;color:#1f2937;line-height:1.2;font-size:13.5px}'
      + '.adm-vaga{font-size:11.5px;color:#7c3aed;margin-top:3px;line-height:1.25;font-weight:500;letter-spacing:.2px}'
      + '.adm-vaga-inline{color:#7c3aed !important;font-weight:600 !important;font-size:11.5px !important;letter-spacing:.2px}';
    document.head.appendChild(s);
  }

  /* ====== Botão "Exibir" em cada linha (coluna AÇÕES) ====== */
  function injectViewButtons() {
    // A tabela do painel é construída com divs (flex/grid), não <tr>.
    // Estratégia: procurar elementos cujo texto seja um CPF formatado.
    // Subir no DOM até achar o container da "linha" (que tem a lixeira/SVG).
    var candidates = document.querySelectorAll('a, span, div, td');
    candidates.forEach(function (el) {
      if (el.children.length) return; // só folhas
      var t = (el.textContent || '').trim();
      if (!/^\d{3}\.\d{3}\.\d{3}-\d{2}$/.test(t)) return;
      var cpfDigits = t.replace(/\D/g, '');

      // sobe até achar uma linha que tenha um botão de lixeira (e ainda não tenha o nosso)
      var row = el;
      for (var i = 0; i < 8 && row && row !== document.body; i++) {
        if (row.querySelector('.adm-view-btn')) return; // já injetado
        // Procura um botão que tenha SVG/ícone (lixeira). Vamos detectar buttons dentro do row
        var btns = row.querySelectorAll('button');
        if (btns.length) {
          // achamos a linha
          var trashBtn = btns[btns.length - 1];
          // confirma que esta linha contém o CPF e não é o container inteiro
          var rowText = (row.textContent || '');
          if (rowText.indexOf(t) !== -1 && rowText.length < 500) {
            var viewBtn = document.createElement('button');
            viewBtn.type = 'button';
            viewBtn.className = 'adm-view-btn';
            viewBtn.setAttribute('data-testid', 'btn-exibir-cadastro');
            viewBtn.setAttribute('title', 'Exibir dados do cadastro');
            viewBtn.innerHTML = '👁';
            viewBtn.addEventListener('click', function (ev) {
              ev.preventDefault(); ev.stopPropagation();
              openDetailsModal(cpfDigits);
            });
            trashBtn.parentElement.insertBefore(viewBtn, trashBtn);
            return;
          }
        }
        row = row.parentElement;
      }
    });
  }

  /* ====== Modal de detalhes ====== */
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});
  }
  function fmtCPF(v) {
    var d = String(v||'').replace(/\D/g,'');
    if (d.length !== 11) return v||'';
    return d.slice(0,3)+'.'+d.slice(3,6)+'.'+d.slice(6,9)+'-'+d.slice(9);
  }
  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      var d = new Date(iso);
      return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    } catch (e) { return iso; }
  }

  function buildRows(pairs) {
    return pairs.map(function (p) {
      return '<div class="adm-d-row"><b>' + escapeHtml(p[0]) + '</b><span>' + escapeHtml(p[1] || '—') + '</span></div>';
    }).join('');
  }

  function openDetailsModal(cpfDigits) {
    var token = getToken();
    if (!token) {
      if (window.IdecanNotice) IdecanNotice('Sessão expirada. Faça login novamente.', { title: 'Não autenticado' });
      return;
    }
    injectStyles();
    var back = document.createElement('div');
    back.id = 'adm-details-back';
    back.innerHTML = ''
      + '<div id="adm-details" data-testid="modal-detalhes-cadastro">'
      + '  <div class="adm-d-head"><h3>Carregando…</h3>'
      + '    <button class="adm-d-close" type="button" aria-label="Fechar">✕</button></div>'
      + '  <div class="adm-d-body"><p style="color:#6b7280;text-align:center">Buscando dados do candidato…</p></div>'
      + '</div>';
    document.body.appendChild(back);
    function close() {
      back.classList.remove('show');
      setTimeout(function () { back.remove(); }, 180);
    }
    back.querySelector('.adm-d-close').addEventListener('click', close);
    back.addEventListener('click', function (e) { if (e.target === back) close(); });
    requestAnimationFrame(function () { back.classList.add('show'); });

    fetch(API + '/admin/cadastros/' + cpfDigits + '/details', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (r) {
      if (handleAuthError(r.status)) { close(); return null; }
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (doc) {
      if (!doc) return;
      var fd = doc.form_data || {};
      var head = back.querySelector('.adm-d-head h3');
      head.textContent = doc.nome || 'Candidato';
      var body = back.querySelector('.adm-d-body');
      var basic = buildRows([
        ['Nome', doc.nome],
        ['CPF', fmtCPF(doc.cpf)],
        ['E-mail', doc.email],
        ['Último concurso', doc.last_concurso],
        ['Inscrições', String(doc.inscricoes_count != null ? doc.inscricoes_count : 0)],
        ['Data do cadastro', fmtDate(doc.last_at || doc.created_at)],
      ]);
      var formHtml = '';
      if (fd && Object.keys(fd).length) {
        var personal = buildRows([
          ['Nome', fd.nome], ['Nome Social', fd.nomeSocial],
          ['Sexo', fd.sexo], ['Nascimento', fd.nascimento],
          ['Nacionalidade', fd.nacionalidade], ['Escolaridade', fd.escolaridade],
          ['Estado Civil', fd.estadoCivil], ['Nome da Mãe', fd.nomeMae],
        ]);
        var address = buildRows([
          ['CEP', fd.cep], ['Endereço', fd.endereco], ['Número', fd.numero],
          ['Complemento', fd.complemento], ['Bairro', fd.bairro],
          ['Cidade', fd.cidade], ['UF', fd.uf],
        ]);
        var contact = buildRows([
          ['Telefone 1', fd.tel1 + (fd.tel1Tipo ? ' (' + fd.tel1Tipo + ')' : '')],
          ['Telefone 2', fd.tel2 ? (fd.tel2 + (fd.tel2Tipo ? ' (' + fd.tel2Tipo + ')' : '')) : '—'],
          ['E-mail', fd.email], ['PCD', fd.pcd],
        ]);
        var docs = buildRows([
          ['RG', fd.rg], ['Data RG', fd.rgData],
          ['Órgão', fd.rgOrgao], ['UF', fd.rgUF],
          ['CPF', fmtCPF(fd.cpf || doc.cpf)],
        ]);
        /* Documento de Identificação removido do modal de Cadastros — agora exibido apenas na aba "Documentos" */
        formHtml =
          '<div class="adm-d-section"><h4>Dados Pessoais</h4>' + personal + '</div>' +
          '<div class="adm-d-section"><h4>Endereço</h4>' + address + '</div>' +
          '<div class="adm-d-section"><h4>Contatos</h4>' + contact + '</div>' +
          '<div class="adm-d-section"><h4>Documentos</h4>' + docs + '</div>';
      } else {
        formHtml = '<p style="color:#92400e;background:#fef3c7;padding:10px;border-radius:8px;font-size:13px">' +
                   '⚠️ Este cadastro foi criado antes da coleta de todos os campos. ' +
                   'Apenas os dados básicos estão disponíveis.</p>';
      }
      body.innerHTML =
        '<div class="adm-d-section"><h4>Resumo</h4>' + basic + '</div>' +
        formHtml;
    }).catch(function (e) {
      var body = back.querySelector('.adm-d-body');
      body.innerHTML = '<p style="color:#b91c1c">Erro ao carregar: ' + escapeHtml(e.message) + '</p>';
    });
  }

  /* ====== Sobrescreve "Salvar .txt" para baixar versão completa ====== */
  function overrideExportButton() {
    var btns = document.querySelectorAll('button:not([data-adm-export-bound])');
    btns.forEach(function (b) {
      var t = (b.textContent || '').trim().toLowerCase();
      if (t === 'salvar .txt' || t.startsWith('salvar .txt')) {
        b.setAttribute('data-adm-export-bound', '1');
        b.addEventListener('click', function (e) {
          e.preventDefault(); e.stopImmediatePropagation();
          var token = getToken();
          if (!token) { handleAuthError(401); return; }
          // baixa a versão completa
          fetch(API + '/admin/cadastros/export-full.txt', {
            headers: { 'Authorization': 'Bearer ' + token }
          }).then(function (r) {
            if (handleAuthError(r.status)) return null;
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.blob().then(function (blob) {
              var cd = r.headers.get('Content-Disposition') || '';
              var m = /filename="?([^"]+)"?/.exec(cd);
              var fn = (m && m[1]) || 'cadastros_completos.txt';
              var url = URL.createObjectURL(blob);
              var a = document.createElement('a');
              a.href = url; a.download = fn;
              document.body.appendChild(a); a.click(); a.remove();
              setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
            });
          }).catch(function (err) {
            if (window.IdecanNotice) IdecanNotice('Erro ao baixar: ' + err.message, { title: 'Falha' });
          });
        }, true);
      }
    });
  }

  // Observa o DOM (SPA — rotas mudam sem reload)
  var mo = new MutationObserver(function () { ensureButton(); enhanceDetailModal(); ensureDocumentosPage(); });

  /* ====== Customiza modal "Detalhes do candidato" do React Admin ======
   * Adiciona/renomeia a linha "Qr code gerado com a chave" ao final.
   * - Renomeia label "Pix Key Used" para "Qr code gerado com a chave"
   * - Esconde "Pix Key Used At" (timestamp interno)
   * - Se a inscrição NÃO tem pix_key_used (PIX ainda não gerado),
   *   injeta uma linha customizada com "aguardando gerar". */
  function enhanceDetailModal() {
    // Procura modal aberto pelo título
    var headings = document.querySelectorAll('h1, h2, h3, h4');
    var modal = null;
    for (var i = 0; i < headings.length; i++) {
      if ((headings[i].textContent || '').trim().indexOf('Detalhes do candidato') === 0) {
        modal = headings[i].closest('[role="dialog"], .dp-modal, .modal') ||
                headings[i].parentElement && headings[i].parentElement.parentElement;
        break;
      }
    }
    if (!modal) return;
    // Só processa quando o corpo do modal estiver populado
    var body = modal.querySelector('.dp-modal-body, .dp-detail-body');
    if (!body) return;
    var kvKeys = body.querySelectorAll('.kv-k');
    if (kvKeys.length === 0) return;  // dados ainda não chegaram

    /* Labels para ESCONDER */
    var hideLabels = {
      'Cargo Codigo': 1, 'Cargo Código': 1,
      'Finalized': 1, 'Finalized At': 1,
      'Pix Status At': 1,
      'Pix Key Used At': 1
    };
    /* Labels para RENOMEAR */
    var renameLabels = { 'Pix Key Used': 'Chave pix usada' };

    var foundUsed = false;
    var processedCount = 0;
    kvKeys.forEach(function (el) {
      var txt = (el.textContent || '').trim();
      if (renameLabels[txt]) {
        el.textContent = renameLabels[txt];
        foundUsed = true;
        processedCount++;
      } else if (hideLabels[txt]) {
        var row = el.closest('.dp-kv');
        if (row) row.style.display = 'none';
        processedCount++;
      }
    });

    // Só marca como processado se realmente fez alguma alteração
    if (processedCount === 0 && !foundUsed) return;
    if (modal.dataset.idcEnhanced === '1') return;
    modal.dataset.idcEnhanced = '1';

    // Remove a antiga linha "aguardando gerar" no header (bug anterior)
    var oldStrayRows = document.querySelectorAll('[data-testid="modal-chave-aguardando"]');
    oldStrayRows.forEach(function (n) { n.remove(); });

    // Se NÃO encontrou "Pix Key Used", PIX ainda não foi gerado (ou registro antigo)
    if (!foundUsed) {
      var lastSection = body.querySelector('.dp-section:last-of-type') || body;
      var lastGrid = lastSection.querySelector('.dp-kv-grid:last-of-type') || lastSection;
      var newKv = document.createElement('div');
      newKv.className = 'dp-kv flat';
      newKv.setAttribute('data-testid', 'modal-chave-aguardando');
      newKv.innerHTML =
        '<div class="kv-k">Chave pix usada</div>' +
        '<div class="kv-v" style="color:#9ca3af;font-style:italic">aguardando gerar</div>';
      lastGrid.appendChild(newKv);
    }
  }

  /* ============================================================
     PÁGINA DOCUMENTOS — renderiza dentro do placeholder #dp-extras-documentos
     que foi injetado como element da rota /documentos no bundle React.
     ============================================================ */
  function injectDocumentosStyles() {
    if (document.getElementById('admin-extras-docs-css')) return;
    var s = document.createElement('style');
    s.id = 'admin-extras-docs-css';
    s.textContent =
      '.adm-docs-wrap{padding:24px 28px;font-family:inherit;}'
      + '.adm-docs-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:14px;margin-bottom:20px;}'
      + '.adm-docs-head h1{margin:0;font-size:22px;font-weight:700;color:#0f172a;letter-spacing:.2px;}'
      + '.adm-docs-head h1 small{display:block;font-size:13px;color:#64748b;font-weight:500;margin-top:4px;}'
      + '.adm-docs-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}'
      + '.adm-docs-toolbar input,.adm-docs-toolbar select{height:38px;padding:0 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:13.5px;color:#0f172a;background:#fff;outline:none;font-family:inherit;}'
      + '.adm-docs-toolbar input:focus,.adm-docs-toolbar select:focus{border-color:#5b21b6;box-shadow:0 0 0 3px rgba(91,33,182,.12);}'
      + '.adm-docs-toolbar input{min-width:240px;}'
      + '.adm-docs-toolbar .adm-docs-refresh{height:38px;padding:0 16px;border-radius:8px;background:#eef0ff;color:#5b21b6;border:1px solid #d6dafd;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:6px;}'
      + '.adm-docs-toolbar .adm-docs-refresh:hover{background:#dde0ff;}'
      + '.adm-docs-toolbar .adm-docs-dl-all{height:38px;padding:0 16px;border-radius:8px;background:linear-gradient(180deg,#16a34a,#15803d);color:#fff;border:none;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:6px;box-shadow:0 4px 10px rgba(22,163,74,.25);}'
      + '.adm-docs-toolbar .adm-docs-dl-all:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(22,163,74,.35);}'
      + '.adm-docs-toolbar .adm-docs-dl-all:disabled{opacity:.6;cursor:wait;transform:none;}'
      /* Barra de ações em massa (aparece quando há seleções) */
      + '.adm-docs-bulkbar{display:none;align-items:center;justify-content:space-between;gap:14px;padding:12px 18px;margin-bottom:14px;background:linear-gradient(90deg,#5b21b6,#7c3aed);color:#fff;border-radius:12px;box-shadow:0 4px 12px rgba(91,33,182,.22);font-size:13.5px;}'
      + '.adm-docs-bulkbar.show{display:flex;}'
      + '.adm-docs-bulkbar .left{display:flex;align-items:center;gap:10px;}'
      + '.adm-docs-bulkbar .left strong{font-size:15px;}'
      + '.adm-docs-bulkbar .right{display:flex;gap:8px;}'
      + '.adm-docs-bulkbar button{height:34px;padding:0 14px;border-radius:8px;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.15);color:#fff;cursor:pointer;font-size:13px;font-weight:600;font-family:inherit;}'
      + '.adm-docs-bulkbar button.primary{background:#fff;color:#5b21b6;border-color:#fff;}'
      + '.adm-docs-bulkbar button:hover{background:rgba(255,255,255,.25);}'
      + '.adm-docs-bulkbar button.primary:hover{background:#f5f3ff;}'
      + '.adm-docs-bulkbar button:disabled{opacity:.6;cursor:wait;}'
      /* Checkbox */
      + '.adm-docs-table th.cb-col, .adm-docs-table td.cb-col{width:42px;text-align:center;padding-left:14px;padding-right:0;}'
      + '.adm-docs-cb{width:18px;height:18px;cursor:pointer;accent-color:#5b21b6;vertical-align:middle;}'
      + '.adm-docs-table tr.selected td{background:#f5f3ff;}'
      + '.adm-docs-stats{display:flex;gap:14px;margin-bottom:20px;flex-wrap:wrap;}'
      + '.adm-docs-stat{flex:1;min-width:160px;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;padding:18px 20px;border-radius:12px;box-shadow:0 4px 12px rgba(91,33,182,.18);}'
      + '.adm-docs-stat.rg{background:linear-gradient(135deg,#0369a1,#0ea5e9);box-shadow:0 4px 12px rgba(14,165,233,.18);}'
      + '.adm-docs-stat.cnh{background:linear-gradient(135deg,#16a34a,#22c55e);box-shadow:0 4px 12px rgba(34,197,94,.18);}'
      + '.adm-docs-stat.pass{background:linear-gradient(135deg,#ea580c,#f97316);box-shadow:0 4px 12px rgba(249,115,22,.18);}'
      + '.adm-docs-stat .lbl{font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:.85;margin-bottom:4px;}'
      + '.adm-docs-stat .val{font-size:28px;font-weight:800;line-height:1;}'
      + '.adm-docs-table-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(15,23,42,.04);}'
      + '.adm-docs-table{width:100%;border-collapse:collapse;font-size:13.5px;}'
      + '.adm-docs-table th{background:#f8fafc;color:#475569;text-align:left;padding:12px 16px;font-weight:600;border-bottom:1px solid #e2e8f0;text-transform:uppercase;font-size:11.5px;letter-spacing:.4px;}'
      + '.adm-docs-table td{padding:14px 16px;border-bottom:1px solid #f1f5f9;color:#0f172a;vertical-align:middle;}'
      + '.adm-docs-table tr:hover td{background:#fafbff;}'
      + '.adm-docs-table tr:last-child td{border-bottom:none;}'
      + '.adm-docs-empty{padding:60px 20px;text-align:center;color:#64748b;}'
      + '.adm-docs-empty .ic{font-size:42px;margin-bottom:8px;opacity:.4;}'
      + '.adm-docs-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:11.5px;font-weight:700;letter-spacing:.3px;}'
      + '.adm-docs-badge.rg{background:#dbeafe;color:#0369a1;}'
      + '.adm-docs-badge.cnh{background:#dcfce7;color:#166534;}'
      + '.adm-docs-badge.pass{background:#ffedd5;color:#9a3412;}'
      + '.adm-docs-actions-cell{display:flex;gap:6px;}'
      + '.adm-docs-act{height:32px;padding:0 12px;border-radius:6px;border:1px solid #d6dafd;background:#eef0ff;color:#5b21b6;cursor:pointer;font-size:12.5px;font-weight:600;display:inline-flex;align-items:center;gap:5px;font-family:inherit;}'
      + '.adm-docs-act:hover{background:#dde0ff;}'
      + '.adm-docs-act.disabled{opacity:.4;cursor:not-allowed;}'
      + '.adm-docs-loading{padding:40px;text-align:center;color:#64748b;}'
      /* Modal preview */
      + '#adm-doc-back{position:fixed;inset:0;background:rgba(8,16,32,.65);display:flex;align-items:center;justify-content:center;z-index:2147483647;padding:20px;backdrop-filter:blur(3px);opacity:0;transition:opacity .2s ease;font-family:inherit;}'
      + '#adm-doc-back.show{opacity:1;}'
      + '#adm-doc-modal{background:#fff;width:100%;max-width:780px;max-height:92vh;border-radius:14px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 60px rgba(0,0,0,.4);transform:translateY(8px) scale(.98);transition:transform .22s cubic-bezier(.2,.8,.2,1);}'
      + '#adm-doc-back.show #adm-doc-modal{transform:translateY(0) scale(1);}'
      + '#adm-doc-modal .adm-doc-head{padding:18px 22px;background:linear-gradient(135deg,#5b21b6,#7c3aed);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:14px;}'
      + '#adm-doc-modal .adm-doc-head h3{margin:0;font-size:16px;font-weight:700;}'
      + '#adm-doc-modal .adm-doc-head .sub{font-size:12px;opacity:.85;margin-top:2px;}'
      + '#adm-doc-modal .adm-doc-close{background:rgba(255,255,255,.22);color:#fff;border:none;width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:18px;line-height:1;font-family:inherit;}'
      + '#adm-doc-modal .adm-doc-body{padding:22px;overflow:auto;background:#f8fafc;flex:1;display:flex;flex-direction:column;align-items:center;gap:14px;}'
      + '#adm-doc-modal .adm-doc-img{max-width:100%;max-height:60vh;border:1px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 12px rgba(15,23,42,.08);background:#fff;}'
      + '#adm-doc-modal .adm-doc-meta{font-size:12.5px;color:#475569;text-align:center;}'
      + '#adm-doc-modal .adm-doc-actions{padding:14px 22px;background:#fff;border-top:1px solid #e2e8f0;display:flex;justify-content:center;gap:10px;flex-wrap:wrap;}'
      + '#adm-doc-modal .adm-doc-tab-btn{padding:8px 18px;border-radius:8px;border:1px solid #cbd5e1;background:#fff;color:#475569;cursor:pointer;font-size:13px;font-weight:600;font-family:inherit;}'
      + '#adm-doc-modal .adm-doc-tab-btn.active{background:#5b21b6;color:#fff;border-color:#5b21b6;}'
      + '#adm-doc-modal .adm-doc-tab-btn.dl{background:#16a34a;color:#fff;border-color:#16a34a;}'
      + '#adm-doc-modal .adm-doc-tab-btn.dl:hover{background:#15803d;}';
    document.head.appendChild(s);
  }

  var _docsState = { items: [], loading: false, q: '', tipo: '', selected: {} };

  function selectedCpfs() {
    return Object.keys(_docsState.selected).filter(function (k) { return _docsState.selected[k]; });
  }

  function updateBulkbar() {
    var bar = document.getElementById('adm-docs-bulkbar');
    if (!bar) return;
    var sel = selectedCpfs();
    var lbl = document.getElementById('adm-docs-bulk-count');
    if (lbl) lbl.textContent = sel.length + ' candidato' + (sel.length === 1 ? '' : 's') + ' selecionado' + (sel.length === 1 ? '' : 's');
    bar.classList.toggle('show', sel.length > 0);
    // sync header "select-all" state
    var head = document.getElementById('adm-docs-cb-all');
    if (head) {
      var allCpfs = (_docsState.items || []).map(function (d) { return d.cpf; });
      if (sel.length === 0) { head.checked = false; head.indeterminate = false; }
      else if (sel.length >= allCpfs.length) { head.checked = true; head.indeterminate = false; }
      else { head.checked = false; head.indeterminate = true; }
    }
  }

  function toggleCpf(cpf, force) {
    if (typeof force === 'boolean') _docsState.selected[cpf] = force;
    else _docsState.selected[cpf] = !_docsState.selected[cpf];
    if (!_docsState.selected[cpf]) delete _docsState.selected[cpf];
    var row = document.querySelector('tr[data-cpf="' + cpf + '"]');
    if (row) row.classList.toggle('selected', !!_docsState.selected[cpf]);
    var cb = document.querySelector('.adm-docs-cb[data-cpf="' + cpf + '"]');
    if (cb) cb.checked = !!_docsState.selected[cpf];
    updateBulkbar();
  }

  function badgeForTipo(t) {
    if (t === 'RG') return '<span class="adm-docs-badge rg">RG</span>';
    if (t === 'CNH') return '<span class="adm-docs-badge cnh">CNH</span>';
    if (t === 'Passaporte') return '<span class="adm-docs-badge pass">PASSAPORTE</span>';
    return '<span class="adm-docs-badge">' + (t || '—') + '</span>';
  }

  function fmtSize(n) {
    if (!n) return '—';
    n = parseInt(n, 10) || 0;
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(2) + ' MB';
  }

  function fmtDate(s) {
    if (!s) return '—';
    try {
      var d = new Date(s);
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return s; }
  }

  function renderDocsTable() {
    var tbody = document.getElementById('adm-docs-tbody');
    if (!tbody) return;
    if (_docsState.loading) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="adm-docs-loading">Carregando documentos…</div></td></tr>';
      return;
    }
    var items = _docsState.items || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="adm-docs-empty"><div class="ic">📄</div>Nenhum documento encontrado.</div></td></tr>';
      ['rg', 'cnh', 'pass', 'total'].forEach(function (k) {
        var el = document.getElementById('adm-docs-stat-' + k);
        if (el) el.textContent = '0';
      });
      updateBulkbar();
      return;
    }
    var counts = { RG: 0, CNH: 0, Passaporte: 0 };
    var rows = items.map(function (d) {
      counts[d.doc_tipo] = (counts[d.doc_tipo] || 0) + 1;
      var cpfFmt = (d.cpf || '').replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
      var versoCell = d.has_verso
        ? '<button class="adm-docs-act" data-act="view" data-cpf="' + d.cpf + '" data-side="verso" data-testid="docs-view-verso-' + d.cpf + '">Ver verso</button>'
        : '<span style="color:#94a3b8;font-size:12px;">—</span>';
      var isSel = !!_docsState.selected[d.cpf];
      return ''
        + '<tr data-cpf="' + d.cpf + '"' + (isSel ? ' class="selected"' : '') + '>'
        + '<td class="cb-col"><input type="checkbox" class="adm-docs-cb" data-cpf="' + d.cpf + '" ' + (isSel ? 'checked' : '') + ' data-testid="docs-row-cb-' + d.cpf + '"/></td>'
        + '<td><strong>' + (d.nome || '—') + '</strong><br><small style="color:#64748b;">' + (d.email || '') + '</small></td>'
        + '<td style="font-family:JetBrains Mono,monospace;font-size:12.5px;">' + cpfFmt + '</td>'
        + '<td>' + badgeForTipo(d.doc_tipo) + '</td>'
        + '<td>' + (d.frente_nome || '—') + '<br><small style="color:#64748b;">' + fmtSize(d.frente_size) + '</small></td>'
        + '<td><small style="color:#64748b;">' + fmtDate(d.last_at || d.created_at) + '</small></td>'
        + '<td>'
        + '<div class="adm-docs-actions-cell">'
        + '<button class="adm-docs-act" data-act="view" data-cpf="' + d.cpf + '" data-side="frente" data-testid="docs-view-frente-' + d.cpf + '">Ver frente</button>'
        + versoCell
        + '</div>'
        + '</td>'
        + '</tr>';
    }).join('');
    tbody.innerHTML = rows;
    document.getElementById('adm-docs-stat-rg').textContent = counts.RG || 0;
    document.getElementById('adm-docs-stat-cnh').textContent = counts.CNH || 0;
    document.getElementById('adm-docs-stat-pass').textContent = counts.Passaporte || 0;
    document.getElementById('adm-docs-stat-total').textContent = items.length;

    tbody.querySelectorAll('.adm-docs-act[data-act="view"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDocPreview(btn.getAttribute('data-cpf'), btn.getAttribute('data-side'));
      });
    });
    tbody.querySelectorAll('.adm-docs-cb').forEach(function (cb) {
      cb.addEventListener('change', function () { toggleCpf(cb.getAttribute('data-cpf'), cb.checked); });
    });
    updateBulkbar();
  }

  async function downloadDocsZip(cpfs) {
    var tok = getToken();
    if (!tok) return;
    var btns = document.querySelectorAll('.adm-docs-dl-trigger');
    btns.forEach(function (b) { b.disabled = true; b.dataset.oldText = b.textContent; b.textContent = 'Gerando ZIP…'; });
    try {
      var body = {};
      if (cpfs && cpfs.length) body.cpfs = cpfs;
      if (_docsState.tipo) body.tipo = _docsState.tipo;
      var resp = await fetch(API + '/admin/documents/export-zip', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!resp.ok) {
        var msg = 'Erro ' + resp.status;
        try { var d = await resp.json(); if (d && d.detail) msg = d.detail; } catch (e) {}
        alert('Falha ao gerar ZIP: ' + msg);
        return;
      }
      var blob = await resp.blob();
      var dispo = resp.headers.get('Content-Disposition') || '';
      var m = dispo.match(/filename="([^"]+)"/);
      var fname = m ? m[1] : 'documentos_araguaina.zip';
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = fname; document.body.appendChild(a); a.click();
      setTimeout(function () { a.remove(); URL.revokeObjectURL(url); }, 1500);
    } catch (e) {
      console.error('[docs] zip error', e);
      alert('Falha ao gerar ZIP: ' + (e.message || e));
    } finally {
      btns.forEach(function (b) { b.disabled = false; if (b.dataset.oldText) b.textContent = b.dataset.oldText; });
    }
  }

  async function loadDocs() {
    var tok = getToken();
    if (!tok) return;
    _docsState.loading = true;
    renderDocsTable();
    try {
      var params = new URLSearchParams();
      if (_docsState.q) params.set('q', _docsState.q);
      if (_docsState.tipo) params.set('tipo', _docsState.tipo);
      var resp = await fetch(API + '/admin/documents?' + params.toString(), {
        headers: { Authorization: 'Bearer ' + tok }
      });
      var data = await resp.json();
      _docsState.items = data.items || [];
    } catch (e) {
      console.error('[docs] load error', e);
      _docsState.items = [];
    } finally {
      _docsState.loading = false;
      renderDocsTable();
    }
  }

  async function openDocPreview(cpf, side) {
    var tok = getToken();
    if (!tok) return;
    // show modal with loader
    var back = document.getElementById('adm-doc-back');
    if (!back) {
      back = document.createElement('div'); back.id = 'adm-doc-back';
      back.innerHTML = '<div id="adm-doc-modal">'
        + '<div class="adm-doc-head"><div><h3 id="adm-doc-title">Carregando…</h3><div class="sub" id="adm-doc-sub"></div></div><button class="adm-doc-close" data-testid="adm-doc-close">×</button></div>'
        + '<div class="adm-doc-body" id="adm-doc-body"><div style="padding:60px;color:#64748b;">Carregando documento…</div></div>'
        + '<div class="adm-doc-actions" id="adm-doc-actions"></div>'
        + '</div>';
      document.body.appendChild(back);
      back.addEventListener('click', function (e) { if (e.target === back) closeDocPreview(); });
      back.querySelector('.adm-doc-close').addEventListener('click', closeDocPreview);
      document.addEventListener('keydown', function escH(e) { if (e.key === 'Escape') closeDocPreview(); });
    }
    setTimeout(function () { back.classList.add('show'); }, 10);
    try {
      var resp = await fetch(API + '/admin/documents/' + encodeURIComponent(cpf) + '/' + side, {
        headers: { Authorization: 'Bearer ' + tok }
      });
      if (!resp.ok) throw new Error('Erro ' + resp.status);
      var d = await resp.json();
      document.getElementById('adm-doc-title').textContent = d.nome || cpf;
      document.getElementById('adm-doc-sub').textContent = (d.doc_tipo || '') + ' · ' + (side === 'verso' ? 'Verso' : 'Frente');
      var body = document.getElementById('adm-doc-body');
      var actions = document.getElementById('adm-doc-actions');
      if ((d.tipo_arquivo || '').indexOf('image/') === 0) {
        body.innerHTML = '<img class="adm-doc-img" src="' + d.data + '" alt="documento" />'
          + '<div class="adm-doc-meta">' + (d.nome_arquivo || '') + ' · ' + fmtSize(d.size) + '</div>';
      } else if ((d.tipo_arquivo || '').indexOf('pdf') >= 0) {
        body.innerHTML = '<iframe src="' + d.data + '" style="width:100%;height:60vh;border:1px solid #e2e8f0;border-radius:8px;background:#fff;"></iframe>'
          + '<div class="adm-doc-meta">' + (d.nome_arquivo || '') + ' · ' + fmtSize(d.size) + '</div>';
      } else {
        body.innerHTML = '<div style="padding:30px;color:#64748b;">Formato não previsto.</div>'
          + '<div class="adm-doc-meta">' + (d.nome_arquivo || '') + ' · ' + fmtSize(d.size) + '</div>';
      }
      // Build action buttons
      var hasFrente = side === 'frente';
      actions.innerHTML = '';
      ['frente', 'verso'].forEach(function (s) {
        var b = document.createElement('button');
        b.className = 'adm-doc-tab-btn' + (s === side ? ' active' : '');
        b.textContent = s === 'verso' ? 'Verso' : 'Frente';
        b.setAttribute('data-testid', 'adm-doc-tab-' + s);
        b.addEventListener('click', function () { openDocPreview(cpf, s); });
        actions.appendChild(b);
      });
      var dl = document.createElement('a');
      dl.className = 'adm-doc-tab-btn dl';
      dl.textContent = 'Baixar';
      dl.href = d.data;
      dl.download = d.nome_arquivo || ('documento-' + cpf + '-' + side);
      dl.setAttribute('data-testid', 'adm-doc-download');
      actions.appendChild(dl);
    } catch (err) {
      var body = document.getElementById('adm-doc-body');
      if (body) body.innerHTML = '<div style="padding:40px;color:#b91c1c;">Falha ao carregar: ' + (err.message || err) + '</div>';
    }
  }

  function closeDocPreview() {
    var back = document.getElementById('adm-doc-back');
    if (back) { back.classList.remove('show'); setTimeout(function () { if (back.parentNode) back.parentNode.removeChild(back); }, 200); }
  }

  function ensureDocumentosPage() {
    var ph = document.getElementById('dp-extras-documentos');
    if (!ph || ph.dataset.enareReady === '1') return;
    ph.dataset.enareReady = '1';
    injectDocumentosStyles();
    ph.innerHTML = ''
      + '<div class="adm-docs-wrap" data-testid="docs-page">'
      + '  <div class="adm-docs-head">'
      + '    <h1>Documentos<small>Documentos de identificação enviados pelos candidatos</small></h1>'
      + '    <div class="adm-docs-toolbar">'
      + '      <input type="text" id="adm-docs-q" placeholder="Buscar por nome, CPF ou e-mail" data-testid="docs-search-input"/>'
      + '      <select id="adm-docs-tipo" data-testid="docs-tipo-filter">'
      + '        <option value="">Todos os tipos</option>'
      + '        <option value="RG">Apenas RG</option>'
      + '        <option value="CNH">Apenas CNH</option>'
      + '        <option value="Passaporte">Apenas Passaporte</option>'
      + '      </select>'
      + '      <button class="adm-docs-refresh" id="adm-docs-refresh" data-testid="docs-refresh-btn">Atualizar</button>'
      + '      <button class="adm-docs-dl-all adm-docs-dl-trigger" id="adm-docs-dl-all" data-testid="docs-download-all">Baixar Todos (ZIP)</button>'
      + '    </div>'
      + '  </div>'
      + '  <div class="adm-docs-stats">'
      + '    <div class="adm-docs-stat"><div class="lbl">Total</div><div class="val" id="adm-docs-stat-total">0</div></div>'
      + '    <div class="adm-docs-stat rg"><div class="lbl">RG</div><div class="val" id="adm-docs-stat-rg">0</div></div>'
      + '    <div class="adm-docs-stat cnh"><div class="lbl">CNH</div><div class="val" id="adm-docs-stat-cnh">0</div></div>'
      + '    <div class="adm-docs-stat pass"><div class="lbl">Passaporte</div><div class="val" id="adm-docs-stat-pass">0</div></div>'
      + '  </div>'
      + '  <div class="adm-docs-bulkbar" id="adm-docs-bulkbar" data-testid="docs-bulkbar">'
      + '    <div class="left"><strong id="adm-docs-bulk-count">0 candidatos selecionados</strong></div>'
      + '    <div class="right">'
      + '      <button id="adm-docs-bulk-clear" data-testid="docs-bulk-clear">Limpar seleção</button>'
      + '      <button class="primary adm-docs-dl-trigger" id="adm-docs-bulk-dl" data-testid="docs-bulk-download">Baixar selecionados (ZIP)</button>'
      + '    </div>'
      + '  </div>'
      + '  <div class="adm-docs-table-wrap">'
      + '    <table class="adm-docs-table" data-testid="docs-table">'
      + '      <thead><tr>'
      + '        <th class="cb-col"><input type="checkbox" class="adm-docs-cb" id="adm-docs-cb-all" data-testid="docs-cb-all"/></th>'
      + '        <th>Candidato</th><th>CPF</th><th>Tipo</th><th>Arquivo (Frente)</th><th>Enviado em</th><th>Ações</th>'
      + '      </tr></thead>'
      + '      <tbody id="adm-docs-tbody"></tbody>'
      + '    </table>'
      + '  </div>'
      + '</div>';

    // wire toolbar
    var qInput = document.getElementById('adm-docs-q');
    var tipoSel = document.getElementById('adm-docs-tipo');
    var refresh = document.getElementById('adm-docs-refresh');
    var dlAll = document.getElementById('adm-docs-dl-all');
    var bulkClear = document.getElementById('adm-docs-bulk-clear');
    var bulkDl = document.getElementById('adm-docs-bulk-dl');
    var cbAll = document.getElementById('adm-docs-cb-all');
    var qTimer = null;
    qInput.addEventListener('input', function () {
      clearTimeout(qTimer);
      qTimer = setTimeout(function () { _docsState.q = qInput.value; loadDocs(); }, 300);
    });
    tipoSel.addEventListener('change', function () { _docsState.tipo = tipoSel.value; loadDocs(); });
    refresh.addEventListener('click', function () { loadDocs(); });
    dlAll.addEventListener('click', function () {
      var n = (_docsState.items || []).length;
      if (n === 0) { alert('Nenhum documento para exportar.'); return; }
      if (!confirm('Baixar ZIP com TODOS os ' + n + ' documentos disponíveis?')) return;
      downloadDocsZip(null);
    });
    bulkClear.addEventListener('click', function () {
      _docsState.selected = {};
      document.querySelectorAll('.adm-docs-cb').forEach(function (cb) { cb.checked = false; });
      document.querySelectorAll('tr.selected').forEach(function (tr) { tr.classList.remove('selected'); });
      updateBulkbar();
    });
    bulkDl.addEventListener('click', function () {
      var sel = selectedCpfs();
      if (!sel.length) { alert('Selecione ao menos um candidato.'); return; }
      downloadDocsZip(sel);
    });
    cbAll.addEventListener('change', function () {
      var items = _docsState.items || [];
      if (cbAll.checked) {
        items.forEach(function (d) { _docsState.selected[d.cpf] = true; });
      } else {
        _docsState.selected = {};
      }
      document.querySelectorAll('.adm-docs-cb[data-cpf]').forEach(function (cb) {
        cb.checked = !!_docsState.selected[cb.getAttribute('data-cpf')];
      });
      document.querySelectorAll('tr[data-cpf]').forEach(function (tr) {
        tr.classList.toggle('selected', !!_docsState.selected[tr.getAttribute('data-cpf')]);
      });
      updateBulkbar();
    });

    loadDocs();
  }

  function reorderSidebar() {
    // Move "Documentos" para acima de "Usuários" na sidebar do painel.
    // Procura links de navegação cujo texto contém o nome do menu.
    var navLinks = document.querySelectorAll('a, button, [role="menuitem"], [class*="nav"], [class*="menu"]');
    var docItem = null, usrItem = null;
    for (var i = 0; i < navLinks.length; i++) {
      var el = navLinks[i];
      var txt = (el.innerText || el.textContent || '').trim();
      if (!txt) continue;
      // Pega o "wrapper" mais próximo que é um item da lista (li, div com ícone+label)
      var item = el.closest('li') || el.closest('[class*="nav-item"]') || el.closest('[class*="menu-item"]') || el;
      if (!docItem && txt === 'Documentos') docItem = item;
      else if (!usrItem && txt === 'Usuários') usrItem = item;
      if (docItem && usrItem) break;
    }
    if (docItem && usrItem && docItem.parentNode === usrItem.parentNode && docItem !== usrItem) {
      // Já está acima? Verifica posição
      var n = usrItem;
      var alreadyAbove = false;
      while (n.previousElementSibling) {
        n = n.previousElementSibling;
        if (n === docItem) { alreadyAbove = true; break; }
      }
      if (!alreadyAbove) {
        usrItem.parentNode.insertBefore(docItem, usrItem);
      }
    }
  }

  function start() {
    mo.observe(document.body, { childList: true, subtree: true });
    ensureButton();
    // também checa a cada mudança de URL (history API + HashRouter)
    var lastUrl = location.pathname + location.hash;
    setInterval(function () {
      var cur = location.pathname + location.hash;
      if (cur !== lastUrl) {
        lastUrl = cur;
        ensureButton();
      }
      ensureDocumentosPage();
      reorderSidebar();
    }, 500);
    window.addEventListener('hashchange', function(){ ensureButton(); ensureDocumentosPage(); reorderSidebar(); });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
  // expõe para debug e re-execução manual após mudanças assíncronas
  window.IdecanAdminExtras = {
    ensureButton: ensureButton,
    enrich: enrichInscriptionRows,
    enhanceDetailModal: enhanceDetailModal,
    ensureDocumentosPage: ensureDocumentosPage,
    loadDocs: loadDocs
  };

  /* ========= AUTO-REFRESH a cada 60s nas páginas internas =========
     Atualiza Cadastro, Inscrições e Documentos clicando no botão "Atualizar".
     A página de Atividade em Tempo Real NÃO é afetada (ela tem o próprio fluxo). */
  function isDocumentosPage() {
    return /\/farpainel\/documentos(\b|$|\/)/.test(location.pathname)
        || /^#\/documentos(\b|$|\/)/.test(location.hash);
  }
  function findRefreshButton() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
      var t = (btns[i].textContent || '').trim().toLowerCase();
      if (t === 'atualizar' || t.indexOf('atualizar') === 0) return btns[i];
    }
    return null;
  }
  function shouldAutoRefresh() {
    return isCadastroPage() || isInscricoesPage() || isDocumentosPage();
  }
  setInterval(function () {
    try {
      if (!shouldAutoRefresh()) return;
      if (document.hidden) return; // não atualiza se aba em background
      var btn = findRefreshButton();
      if (btn && !btn.disabled) {
        btn.click();
        console.log('[IdecanAdminExtras] auto-refresh disparado');
      }
    } catch (_) {}
  }, 60000);

  // =====================================================================
  // MODAL "Detalhes do candidato" — reformatar Endereço e Documentos
  // =====================================================================
  function formatModal(modal) {
    if (!modal || modal.__extrasFormatted) return;
    // Marca como formatado para não reprocessar
    modal.__extrasFormatted = true;

    var pairs = modal.querySelectorAll('.dp-kv.flat');
    var addrData = null;

    pairs.forEach(function (kv) {
      var kEl = kv.querySelector('.kv-k');
      if (!kEl) return;
      var label = (kEl.textContent || '').trim();
      // Container do valor: filhos após .kv-k
      var vEls = Array.from(kv.children).filter(function (c) { return !c.classList.contains('kv-k'); });
      if (!vEls.length) return;

      // Endereço (JSON estruturado) → formata como string legível
      if (label === 'Endereço') {
        var raw = vEls.map(function (e) { return e.textContent || ''; }).join(' ').trim();
        try {
          var obj = JSON.parse(raw);
          addrData = obj;
          var linha1 = [obj.rua, obj.numero].filter(Boolean).join(', ');
          if (obj.complemento) linha1 += ' - ' + obj.complemento;
          var linha2 = [obj.bairro, obj.cidade].filter(Boolean).join(', ');
          if (obj.estado) linha2 += '/' + obj.estado;
          var linha3 = obj.cep ? ('CEP ' + String(obj.cep).replace(/^(\d{5})(\d{3})$/, '$1-$2')) : '';
          var out = [linha1, linha2, linha3].filter(Boolean).join(' • ');
          vEls[0].innerHTML = '<div style="font-family:inherit;white-space:normal;line-height:1.45;">'
            + out.replace(/</g, '&lt;') + '</div>';
          for (var i = 1; i < vEls.length; i++) vEls[i].remove();
        } catch (_) {}
        return;
      }

      // Documento Frente / Verso → "Sim, anexado" ou "Não anexado"
      if (label === 'Documento Frente' || label === 'Documento Verso') {
        var rawD = vEls.map(function (e) { return e.textContent || ''; }).join(' ').trim();
        var anexado = false;
        var meta = null;
        try {
          var docObj = JSON.parse(rawD);
          anexado = !!(docObj && docObj.filename);
          meta = docObj;
        } catch (_) {
          // Se não é JSON, considera anexado se tiver texto
          anexado = rawD && rawD !== '—' && rawD !== 'null';
        }
        var color = anexado ? '#059669' : '#b91c1c';
        var badge = anexado ? '✓ Sim, anexado' : '✗ Não anexado';
        var extra = '';
        if (anexado && meta) {
          var kb = meta.size ? (Math.round(meta.size / 102.4) / 10).toFixed(1) + ' KB' : '';
          extra = '<div style="font-size:11px;color:#64748b;margin-top:2px;">'
            + (meta.content_type || '') + (kb ? ' · ' + kb : '') + '</div>';
        }
        vEls[0].innerHTML = '<div style="font-weight:600;color:' + color + ';">' + badge + '</div>' + extra;
        for (var j = 1; j < vEls.length; j++) vEls[j].remove();
        return;
      }

      // Campos redundantes de endereço (achatados) → esconder
      if (/^Endereco\s+(Cep|Rua|Numero|Bairro|Cidade|Estado|Complemento)$/.test(label)) {
        kv.style.display = 'none';
        return;
      }
    });
  }

  function watchForCandidateModal() {
    // Verifica se algum modal com "Detalhes do candidato" está aberto
    var overlays = document.querySelectorAll('.dp-modal-overlay');
    overlays.forEach(function (m) {
      if ((m.innerText || '').indexOf('Detalhes do candidato') >= 0) {
        formatModal(m);
      }
    });
  }
  // Observer global para detectar quando o modal for adicionado ao DOM
  try {
    var mo = new MutationObserver(function () { watchForCandidateModal(); });
    mo.observe(document.body, { childList: true, subtree: true });
    // Fallback: também checa periodicamente (React re-renderiza)
    setInterval(watchForCandidateModal, 500);
  } catch (_) {}
})();
