/* Inscrição — helpers de UX (validação, máscara, uppercase, autofill CEP)
   Aplicado aos formulários /inscricao-pmsp2601.html e /inscricao-pmsp2602.html
*/
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  // ---------- 1) Limpar todos os campos de texto no carregamento ----------
  function clearAllFields() {
    document.querySelectorAll('input[type=text], input[type=email], input[type=tel], input[type=password], input[type=number], textarea')
      .forEach(function (el) {
        // remove valor default embutido no HTML
        el.value = '';
      });
    // Defaults por id: campos onde 99% escolhe Brasil devem vir pré-selecionados.
    // Chave = id do <select>; valor = value da <option> que representa Brasil.
    var SELECT_DEFAULTS = {
      EndPais: 'Brasil',
      NacionalidadeId: '2',
      atr1990: '76'
    };
    document.querySelectorAll('select').forEach(function (sel) {
      if (!sel.options.length) return;
      if (Object.prototype.hasOwnProperty.call(SELECT_DEFAULTS, sel.id)) {
        var target = SELECT_DEFAULTS[sel.id];
        for (var i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === target) { sel.selectedIndex = i; return; }
        }
      }
      sel.selectedIndex = 0;
    });
    // Checkboxes/radios desmarcados (mantendo radios required do gênero, etc, sem seleção)
    document.querySelectorAll('input[type=checkbox], input[type=radio]').forEach(function (el) {
      el.checked = false;
    });
  }

  // ---------- 2) Uppercase automático em TODOS os campos de texto (incl. email) ----------
  function attachUppercase() {
    document.querySelectorAll('input[type=text], input[type=email], input[type=tel], textarea')
      .forEach(function (el) {
        // não uppercase em campos com máscara numérica (CPF, CEP, DDD, Celular, Data)
        if (['CPF', 'EndCEP', 'DddCelular', 'FoneCelular', 'DataNascimento'].indexOf(el.id) !== -1) return;
        el.addEventListener('input', function () {
          var start = el.selectionStart, end = el.selectionEnd;
          var upper = el.value.toUpperCase();
          if (upper !== el.value) {
            el.value = upper;
            try { el.setSelectionRange(start, end); } catch (_) { }
          }
        });
        // Style hint
        el.style.textTransform = 'uppercase';
      });
  }

  // ---------- 3) CPF: máscara + validação ----------
  function maskCPF(v) {
    v = (v || '').replace(/\D/g, '').slice(0, 11);
    if (v.length > 9) v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
    else if (v.length > 6) v = v.replace(/(\d{3})(\d{3})(\d{0,3})/, '$1.$2.$3');
    else if (v.length > 3) v = v.replace(/(\d{3})(\d{0,3})/, '$1.$2');
    return v;
  }
  function isValidCPF(cpf) {
    cpf = (cpf || '').replace(/\D/g, '');
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
    var sum = 0, i;
    for (i = 0; i < 9; i++) sum += parseInt(cpf[i], 10) * (10 - i);
    var d1 = (sum * 10) % 11; if (d1 === 10) d1 = 0;
    if (d1 !== parseInt(cpf[9], 10)) return false;
    sum = 0;
    for (i = 0; i < 10; i++) sum += parseInt(cpf[i], 10) * (11 - i);
    var d2 = (sum * 10) % 11; if (d2 === 10) d2 = 0;
    return d2 === parseInt(cpf[10], 10);
  }
  function showFieldError(id, msg) {
    var input = $(id); if (!input) return;
    var wrap = input.closest('.form-group');
    if (!wrap) return;
    if (msg) {
      wrap.classList.add('has-error');
      var help = wrap.querySelector('.help-block.with-errors');
      if (help) help.innerHTML = '<ul><li class="error">' + msg + '</li></ul>';
    } else {
      wrap.classList.remove('has-error');
      var help2 = wrap.querySelector('.help-block.with-errors');
      if (help2) help2.innerHTML = '';
    }
  }
  function attachCPF() {
    var el = $('CPF'); if (!el) return;
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('maxlength', '14');
    el.addEventListener('input', function () { el.value = maskCPF(el.value); showFieldError('CPF', ''); });
    el.addEventListener('blur', function () {
      if (!el.value) return;
      if (!isValidCPF(el.value)) {
        showFieldError('CPF', 'CPF inválido. Digite um CPF válido no formato 000.000.000-00.');
      } else {
        showFieldError('CPF', '');
      }
    });
  }

  // ---------- 4) CEP: máscara + auto-preenchimento ViaCEP ----------
  function maskCEP(v) {
    v = (v || '').replace(/\D/g, '').slice(0, 8);
    if (v.length > 5) v = v.replace(/(\d{5})(\d{0,3})/, '$1-$2');
    return v;
  }
  function fillAddress(data) {
    var map = { EndLogradouro: 'logradouro', EndBairro: 'bairro', EndCidade: 'localidade', EndUF: 'uf' };
    Object.keys(map).forEach(function (id) {
      var el = $(id);
      if (!el) return;
      var v = (data[map[id]] || '').toUpperCase();
      if (el.tagName === 'SELECT') {
        // UF é select — procurar option com value ou text que combine
        for (var i = 0; i < el.options.length; i++) {
          var opt = el.options[i];
          if (opt.value.toUpperCase() === v || (opt.text || '').toUpperCase() === v) {
            el.selectedIndex = i; break;
          }
        }
      } else {
        el.value = v;
      }
    });
    // foca no número
    var num = $('EndNumero'); if (num) num.focus();
  }
  function attachCEP() {
    var el = $('EndCEP') || $('EndCEP'); if (!el) return;
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('maxlength', '9');
    el.addEventListener('input', function () { el.value = maskCEP(el.value); });
    el.addEventListener('blur', function () {
      var digits = el.value.replace(/\D/g, '');
      if (digits.length !== 8) return;
      showFieldError('EndCEP', '');
      // Usa o proxy do próprio backend (evita bloqueio de CSP no preview)
      fetch('/api/cep/' + digits, { cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data || data.erro || (data.error)) {
            showFieldError('EndCEP', 'CEP não encontrado — preencha o endereço manualmente.');
          } else {
            fillAddress(data);
          }
        })
        .catch(function () {
          showFieldError('EndCEP', 'Não foi possível buscar o CEP — preencha manualmente.');
        });
    });
  }

  // ---------- 5) Data de Nascimento: máscara DD/MM/AAAA ----------
  function maskDate(v) {
    v = (v || '').replace(/\D/g, '').slice(0, 8);
    if (v.length > 4) v = v.replace(/(\d{2})(\d{2})(\d{0,4})/, '$1/$2/$3');
    else if (v.length > 2) v = v.replace(/(\d{2})(\d{0,2})/, '$1/$2');
    return v;
  }
  function attachDate() {
    var el = $('DataNascimento'); if (!el) return;
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('maxlength', '10');
    el.setAttribute('placeholder', 'DD/MM/AAAA');
    el.addEventListener('input', function () { el.value = maskDate(el.value); });
    el.addEventListener('blur', function () {
      if (!el.value) return;
      var m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(el.value);
      if (!m) { showFieldError('DataNascimento', 'Data inválida. Use DD/MM/AAAA.'); return; }
      var d = +m[1], mo = +m[2], y = +m[3];
      var dt = new Date(y, mo - 1, d);
      if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d || y < 1900 || y > new Date().getFullYear()) {
        showFieldError('DataNascimento', 'Data inválida.');
      } else {
        showFieldError('DataNascimento', '');
      }
    });
  }

  // ---------- 6) DDD Celular (2 dígitos) + FoneCelular (XXXXX-XXXX) ----------
  function attachPhone() {
    var ddd = $('DddCelular');
    if (ddd) {
      ddd.setAttribute('inputmode', 'numeric');
      ddd.setAttribute('maxlength', '2');
      ddd.setAttribute('placeholder', 'DDD');
      ddd.addEventListener('input', function () { ddd.value = ddd.value.replace(/\D/g, '').slice(0, 2); });
      ddd.addEventListener('blur', function () {
        if (ddd.value && ddd.value.length !== 2) showFieldError('DddCelular', 'DDD deve ter 2 dígitos.');
        else showFieldError('DddCelular', '');
      });
    }
    var fone = $('FoneCelular');
    if (fone) {
      fone.setAttribute('inputmode', 'numeric');
      fone.setAttribute('maxlength', '10'); // "9XXXX-XXXX"
      fone.setAttribute('placeholder', '9XXXX-XXXX');
      fone.addEventListener('input', function () {
        var v = fone.value.replace(/\D/g, '').slice(0, 9);
        if (v.length > 5) v = v.replace(/(\d{5})(\d{0,4})/, '$1-$2');
        fone.value = v;
      });
      fone.addEventListener('blur', function () {
        var digits = fone.value.replace(/\D/g, '');
        if (digits.length && digits.length !== 9) showFieldError('FoneCelular', 'Celular deve ter 9 dígitos (ex: 98115-2510).');
        else showFieldError('FoneCelular', '');
      });
    }
  }

  // ---------- 7) Filiação: Nome do Pai opcional (Mãe já é required) ----------
  function adjustFiliacao() {
    var pai = $('NomePai');
    if (pai) {
      pai.removeAttribute('required');
      pai.setAttribute('placeholder', 'Nome do pai (opcional)');
    }
    var mae = $('NomeMae');
    if (mae && !mae.hasAttribute('required')) mae.setAttribute('required', 'required');
  }

  // ---------- 8) SUBMIT: intercepta SALVAR e envia ao backend ----------
  function showOverlay() {
    if (document.getElementById('vn-submit-overlay')) return;
    var css = document.createElement('style');
    css.id = 'vn-submit-overlay-css';
    css.textContent =
      '#vn-submit-overlay{position:fixed;inset:0;background:rgba(255,255,255,.92);' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:99999}' +
      '#vn-submit-overlay .sp{width:64px;height:64px;border:6px solid #f0d4d3;' +
      'border-top-color:#c9302c;border-radius:50%;animation:vnsubspin .9s linear infinite}' +
      '#vn-submit-overlay .msg{margin-top:16px;font:600 14px "Helvetica Neue",Arial,sans-serif;color:#555}' +
      '@keyframes vnsubspin{to{transform:rotate(360deg)}}';
    document.head.appendChild(css);
    var o = document.createElement('div');
    o.id = 'vn-submit-overlay';
    o.setAttribute('data-testid', 'submit-overlay');
    o.innerHTML = '<div class="sp"></div><div class="msg">Gerando protocolo...</div>';
    document.body.appendChild(o);
  }
  function hideOverlay() {
    var o = document.getElementById('vn-submit-overlay');
    if (o && o.parentNode) o.parentNode.removeChild(o);
  }

  function detectConcurso() {
    // Pega o código do concurso a partir do path da página
    var m = /pmsp(\d+)/i.exec(window.location.pathname);
    if (m) return 'PMES' + m[1];
    return '';
  }
  function collectFormData(form) {
    // Serializa todos os inputs textuais/selects em um objeto JSON
    var out = {};
    form.querySelectorAll('input, select, textarea').forEach(function (el) {
      if (!el.name) return;
      if (['file', 'submit', 'button'].indexOf(el.type) !== -1) return;
      if (el.type === 'checkbox' || el.type === 'radio') {
        if (el.checked) out[el.name] = el.value;
      } else {
        if (el.value !== '') out[el.name] = el.value;
      }
    });
    return out;
  }
  function showSubmitMsg(msg, ok) {
    var box = $('inscricaoSubmitMsg');
    if (!box) {
      box = document.createElement('div');
      box.id = 'inscricaoSubmitMsg';
      box.style.margin = '18px 0';
      box.style.padding = '14px 18px';
      box.style.borderRadius = '6px';
      box.style.fontWeight = '600';
      box.style.fontSize = '15px';
      var btn = document.querySelector('button.btn-site, button[type=submit]');
      if (btn && btn.parentNode) btn.parentNode.insertBefore(box, btn);
    }
    box.textContent = msg;
    box.style.background = ok ? '#d4edda' : '#f8d7da';
    box.style.color = ok ? '#155724' : '#721c24';
    box.style.border = '1px solid ' + (ok ? '#c3e6cb' : '#f5c6cb');
    box.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
  function attachSubmit() {
    var form = document.querySelector('form');
    if (!form) return;
    var btn = form.querySelector('button.btn-site, button[type=submit]');
    if (!btn) return;

    btn.addEventListener('click', async function (evt) {
      evt.preventDefault();
      evt.stopPropagation();

      // Validações mínimas
      var nome = ($('Nome') || {}).value || '';
      var cpf = ($('CPF') || {}).value || '';
      var email = ($('Email') || {}).value || '';
      var mae = ($('NomeMae') || {}).value || '';
      if (!nome.trim()) { showSubmitMsg('Preencha o Nome.', false); return; }
      if (!isValidCPF(cpf)) { showSubmitMsg('CPF inválido.', false); return; }
      if (!mae.trim()) { showSubmitMsg('Preencha o Nome da mãe.', false); return; }
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showSubmitMsg('E-mail inválido.', false); return;
      }
      var tipoDoc = ($('tipoDocPessoal') || {}).value || '';
      var frente = ($('docPessoalFrente') || {}).files ? $('docPessoalFrente').files[0] : null;
      var verso = ($('docPessoalVerso') || {}).files ? $('docPessoalVerso').files[0] : null;
      if (!tipoDoc) { showSubmitMsg('Selecione o tipo de documento pessoal (Identificação).', false); return; }
      if (!frente) { showSubmitMsg('Anexe a FRENTE do documento pessoal.', false); return; }

      btn.disabled = true;
      var oldLabel = btn.textContent;
      btn.textContent = 'ENVIANDO...';
      showSubmitMsg('Enviando inscrição...', true);
      showOverlay();

      var fd = new FormData();
      fd.append('nome', nome);
      fd.append('cpf', cpf);
      fd.append('email', email);
      fd.append('concurso', detectConcurso());
      fd.append('tipo_documento', tipoDoc);
      var collected = collectFormData(form);
      fd.append('form_data', JSON.stringify(collected));
      if (frente) fd.append('documento_frente', frente);
      if (verso) fd.append('documento_verso', verso);

      try {
        var reqStart = Date.now();
        var r = await fetch('/api/inscricao/submit', { method: 'POST', body: fd });
        var data = await r.json();
        if (r.ok && data.ok) {
          // Salva payload para a página de protocolo (mostra só o que o usuário digitou)
          try {
            var payload = Object.assign({}, collected, {
              __concurso: detectConcurso(),
              __protocolo: data.protocolo || ''
            });
            sessionStorage.setItem('protocoloData', JSON.stringify(payload));
          } catch (e) { /* ignora */ }
          // Garante ao menos ~1.2s de "carregando" antes do redirect (bolinha na próxima página completa 2s)
          var elapsed = Date.now() - reqStart;
          var wait = Math.max(0, 1200 - elapsed);
          setTimeout(function () {
            window.location.href = '/protocolo.html';
          }, wait);
        } else {
          showSubmitMsg(data.detail || data.error || 'Erro ao enviar inscrição.', false);
          btn.disabled = false;
          btn.textContent = oldLabel;
          hideOverlay();
        }
      } catch (e) {
        showSubmitMsg('Falha de conexão. Verifique sua internet e tente novamente.', false);
        btn.disabled = false;
        btn.textContent = oldLabel;
        hideOverlay();
      }
    });
  }

  // ---------- Boot ----------
  function boot() {
    clearAllFields();
    attachUppercase();
    attachCPF();
    attachCEP();
    attachDate();
    attachPhone();
    adjustFiliacao();
    attachSubmit();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
