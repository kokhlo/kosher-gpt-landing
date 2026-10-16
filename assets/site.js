// kosherno.app behaviour. Every block reads without JavaScript; this file adds the
// header tone, the language menu, the scanner and chat demos, and the forms.
(function () {
  'use strict';
  window.kgReady = true; // the inline failsafe in <head> keeps content visible if this file never runs
  // On a slow connection this file can arrive after the failsafe gave up: take the page back,
  // with everything already shown, so the demos still work.
  var late = !document.documentElement.classList.contains('js');
  document.documentElement.classList.add('js');

  // E1: blocks and headline words sharpen out of a blur as they reach the screen. A block's
  // place among the revealed blocks of its section staggers it a little.
  var REVEAL = 'main :is(h2, .lead, .actions, .visual, .arch-stage, .tag, .states, .feature-list li, .num-list li, .card, .steps li, .faq > div, .table-box, .chat-phone, .callout, .form-box, .checks li), .words';
  var revealables = Array.prototype.slice.call(document.querySelectorAll(REVEAL));
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  revealables.forEach(function (el) {
    if (el.style.getPropertyValue('--d')) return;
    var section = el.closest('section') || document.body;
    var siblings = revealables.filter(function (other) { return other.closest('section') === section; });
    el.style.setProperty('--d', Math.min(siblings.indexOf(el) * 80, 480) + 'ms');
  });
  if (!calm && !late && 'IntersectionObserver' in window) {
    var revealer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        revealer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.1 });
    revealables.forEach(function (el) { revealer.observe(el); });
  } else {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  }

  // Header text follows the band under it: light over the dark "night"
  // bands, dark over the light ones. No transition, it simply switches.
  var topbar = document.querySelector('.topbar');
  var bands = Array.prototype.slice.call(document.querySelectorAll('[data-tone]'));
  function updateTone() {
    if (!topbar) return;
    var y = 40;
    var tone = 'dark';
    for (var i = 0; i < bands.length; i++) {
      var r = bands[i].getBoundingClientRect();
      if (r.top <= y && r.bottom > y) { tone = bands[i].getAttribute('data-tone'); break; }
    }
    topbar.classList.toggle('on-light', tone === 'light');
    topbar.classList.toggle('on-dark', tone !== 'light');
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { ticking = false; updateTone(); });
  }, { passive: true });
  window.addEventListener('resize', updateTone);
  updateTone();

  // Glass panes [data-tilt] turn towards the cursor (mouse and pen only, never with reduced motion).
  // The reflection drifts against the tilt and the lit edge turns with it; nothing follows the cursor itself.
  if (!calm && window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    document.querySelectorAll('[data-tilt]').forEach(function (pane) {
      var frame = 0;
      pane.addEventListener('pointermove', function (e) {
        var r = pane.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5;
        var dy = (e.clientY - r.top) / r.height - 0.5;
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(function () {
          pane.classList.add('tilting');
          pane.style.setProperty('--rx', (-dy * 14).toFixed(2) + 'deg');
          pane.style.setProperty('--ry', (dx * 18).toFixed(2) + 'deg');
          pane.style.setProperty('--sx', (50 - dx * 40).toFixed(1) + '%');
          pane.style.setProperty('--ang', (135 + dx * 50 - dy * 30).toFixed(0) + 'deg');
          pane.style.setProperty('--glare', '1');
        });
      });
      pane.addEventListener('pointerleave', function () {
        cancelAnimationFrame(frame);
        pane.classList.remove('tilting');
        ['--rx', '--ry', '--sx', '--ang', '--glare'].forEach(function (name) { pane.style.removeProperty(name); });
      });
    });
  }

  // Language menu: a <details>; close it on an outside click or Escape.
  var lang = document.querySelector('.lang');
  if (lang) {
    document.addEventListener('click', function (e) { if (!lang.contains(e.target)) lang.open = false; });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !lang.open) return;
      var inside = lang.contains(document.activeElement);
      lang.open = false;
      if (inside) lang.querySelector('summary').focus(); // focus stays on a visible control
    });
  }

  // Suggest the visitor's language when this page exists in it.
  var hint = document.getElementById('langhint');
  if (hint) {
    try {
      var alternates = JSON.parse(hint.getAttribute('data-alternates'));
      var pageLang = hint.getAttribute('data-page-lang');
      var preferred = (navigator.languages || [navigator.language || '']).map(function (l) { return String(l).slice(0, 2).toLowerCase(); });
      for (var p = 0; p < preferred.length; p++) {
        if (preferred[p] === pageLang) break;
        var alt = alternates[preferred[p]];
        if (alt) {
          var link = document.createElement('a');
          link.href = alt.url;
          link.lang = preferred[p];
          link.textContent = alt.text;
          hint.dir = alt.dir;
          hint.appendChild(link);
          hint.hidden = false;
          break;
        }
      }
    } catch (e) { /* no hint */ }
  }

  // Scanner demo: the state buttons swap the result card.
  document.querySelectorAll('[data-scanner]').forEach(function (root) {
    var states;
    try { states = JSON.parse(root.getAttribute('data-states')); } catch (e) { return; }
    var buttons = root.querySelectorAll('[data-state]');
    function field(name) { return root.querySelectorAll('[data-f="' + name + '"]'); }
    function show(id) {
      var s = states.filter(function (x) { return x.id === id; })[0];
      if (!s) return;
      field('name').forEach(function (el) { el.textContent = s.name; });
      field('code').forEach(function (el) { el.textContent = s.code; });
      field('title').forEach(function (el) { el.textContent = s.title; });
      field('note').forEach(function (el) { el.textContent = s.note; });
      var verdict = root.querySelector('.verdict');
      if (verdict) verdict.className = 'verdict tone-' + s.tone;
      buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-state') === id)); });
    }
    buttons.forEach(function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-state')); }); });
  });

  // Live chat: a picked question is typed into the composer and sent, KosherGPT thinks for a
  // moment and answers word by word. Earlier answers stay in the thread, the suggestions start
  // over once all were asked, and a citation chip opens the answer's sources in a bottom sheet.
  document.querySelectorAll('[data-ask]').forEach(function (root) {
    var thread = root.querySelector('.chat-thread');
    var empty = root.querySelector('.ask-empty');
    var suggest = root.querySelector('.suggest');
    var buttons = Array.prototype.slice.call(root.querySelectorAll('[data-ask-for]'));
    var composer = root.querySelector('.composer');
    var text = root.querySelector('.composer-text');
    var placeholder = text.textContent;
    var sheet = root.querySelector('.sheet');
    var sheetBody = root.querySelector('.sheet-body');
    var closeButton = root.querySelector('.sheet-close');
    var behind = [thread, root.querySelector('.chat-foot')]; // covered by the sheet while it is open
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var answers = {};
    var round = [];
    var busy = false;
    var opener = null;
    // The answers are in the page for search engines and for readers without scripts.
    // Here they leave the thread and come back one by one, as they are asked.
    root.querySelectorAll('.qa').forEach(function (qa) {
      answers[qa.getAttribute('data-qa')] = qa;
      qa.remove();
    });
    function later(fn, ms) { setTimeout(fn, ms); }
    function toBottom() { thread.scrollTop = thread.scrollHeight; }
    function showSuggestions(focus) {
      var all = buttons.every(function (b) { return round.indexOf(b.getAttribute('data-ask-for')) >= 0; });
      if (all) round = [];
      buttons.forEach(function (b) { b.hidden = round.indexOf(b.getAttribute('data-ask-for')) >= 0; });
      suggest.hidden = false;
      suggest.classList.remove('is-in');
      void suggest.offsetWidth; // restart the entrance
      suggest.classList.add('is-in');
      toBottom();
      if (focus) {
        var first = buttons.filter(function (b) { return !b.hidden; })[0];
        if (first) first.focus({ preventScroll: true });
      }
    }
    function ask(button) {
      var id = button.getAttribute('data-ask-for');
      if (busy || !answers[id]) return;
      busy = true;
      round.push(id);
      var refocus = suggest.contains(document.activeElement);
      var qa = answers[id].cloneNode(true);
      var question = qa.querySelector('.bubble').textContent;
      var words = qa.querySelectorAll('.sw').length;
      suggest.hidden = true;
      function send() {
        if (empty) empty.hidden = true;
        composer.classList.remove('is-typing', 'is-sending');
        text.textContent = placeholder;
        qa.classList.add('streaming', 'thinking');
        thread.setAttribute('aria-busy', 'true');
        thread.appendChild(qa);
        toBottom();
        later(function () {
          qa.classList.remove('thinking');
          qa.classList.add('answering');
          thread.setAttribute('aria-busy', 'false');
          toBottom();
          later(function () {
            busy = false;
            showSuggestions(refocus);
          }, reduce ? 0 : words * 45 + 700);
        }, reduce ? 0 : 1100);
      }
      if (reduce) { send(); return; }
      composer.classList.add('is-typing');
      text.textContent = '';
      var start = 250;
      var step = 22;
      for (var i = 1; i <= question.length; i++) {
        (function (n) { later(function () { text.textContent = question.slice(0, n); }, start + n * step); })(i);
      }
      var typed = start + question.length * step;
      later(function () {
        composer.classList.remove('is-typing');
        composer.classList.add('is-sending');
      }, typed + 180);
      later(send, typed + 380);
    }
    buttons.forEach(function (b) { b.addEventListener('click', function () { ask(b); }); });

    function openSheet(chip) {
      var sources = chip.closest('.qa').querySelector('.sources');
      if (!sources) return;
      sheetBody.textContent = '';
      sources.querySelectorAll('.source').forEach(function (s) { sheetBody.appendChild(s.cloneNode(true)); });
      opener = chip;
      sheet.classList.remove('is-closing');
      sheet.classList.add('is-open');
      sheet.hidden = false;
      behind.forEach(function (el) { el.inert = true; });
      closeButton.focus({ preventScroll: true });
    }
    function closeSheet() {
      if (sheet.hidden || sheet.classList.contains('is-closing')) return;
      sheet.classList.add('is-closing');
      later(function () {
        sheet.hidden = true;
        sheet.classList.remove('is-open', 'is-closing');
        behind.forEach(function (el) { el.inert = false; });
        if (opener && opener.isConnected) opener.focus({ preventScroll: true });
      }, reduce ? 0 : 280);
    }
    thread.addEventListener('click', function (event) {
      var chip = event.target.closest('.cite');
      if (chip) openSheet(chip);
    });
    sheet.addEventListener('click', function (event) {
      if (event.target.closest('[data-close]')) closeSheet();
    });
    root.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeSheet();
      if (event.key !== 'Tab' || sheet.hidden) return;
      // Tab goes round the sheet's own controls while it is open.
      var stops = Array.prototype.slice.call(sheet.querySelectorAll('button, a[href]'));
      var first = stops[0];
      var last = stops[stops.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
  });

  // Forms: Cloudflare Turnstile checks that a person is sending, then the kosher-forms Worker
  // mails the team through Resend. The Turnstile script loads only when a form comes near
  // the screen, as on the SoftSys sites.
  var TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  var TOKEN_WAIT_MS = 20000;
  var SEND_TIMEOUT_MS = 20000;
  var EMAIL_RE = /^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[^\s@<>()",;:]{2,}$/; // the same rule as the Worker
  var scriptPromise = null;
  function loadTurnstile() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!scriptPromise) {
      scriptPromise = new Promise(function (resolve, reject) {
        var script = document.createElement('script');
        script.src = TURNSTILE_SRC;
        script.async = true;
        script.onload = function () { if (window.turnstile) resolve(window.turnstile); else reject(new Error('turnstile')); };
        script.onerror = function () { script.remove(); scriptPromise = null; reject(new Error('turnstile')); };
        document.head.appendChild(script);
      });
    }
    return scriptPromise;
  }

  document.querySelectorAll('form[data-form]').forEach(function (form) {
    var status = form.querySelector('.form-status');
    var submit = form.querySelector('[type="submit"]');
    var done = form.parentNode.querySelector('.form-done');
    var box = form.querySelector('[data-captcha]');
    var hint = form.querySelector('.check-hint');
    var endpoint = form.getAttribute('data-endpoint');
    var sitekey = form.getAttribute('data-sitekey');
    var widgetId = null;
    var token = '';
    var pending = false;
    var waiting = [];
    function say(text) { if (status) status.textContent = text || ''; }
    function settle(value) { pending = false; waiting.splice(0).forEach(function (resolve) { resolve(value); }); }

    function start() {
      if (widgetId !== null || pending || !sitekey || !box) return;
      pending = true;
      loadTurnstile().then(function (ts) {
        widgetId = ts.render(box, {
          sitekey: sitekey,
          action: 'contact',
          appearance: 'interaction-only',
          language: form.getAttribute('data-lang'),
          callback: function (value) { token = value; settle(value); },
          'before-interactive-callback': function () { if (hint) hint.hidden = false; },
          'after-interactive-callback': function () { if (hint) hint.hidden = true; },
          'expired-callback': function () { token = ''; },
          'error-callback': function () { token = ''; if (hint) hint.hidden = true; settle(''); return true; }
        });
      }).catch(function () { settle(''); });
    }

    function getToken() {
      if (token) return Promise.resolve(token);
      if (widgetId !== null && !pending) {
        pending = true; // the check failed or the token expired: run it again
        window.turnstile.reset(widgetId);
      } else {
        start();
      }
      return new Promise(function (resolve) {
        waiting.push(resolve);
        (function wait() {
          setTimeout(function () {
            if (hint && !hint.hidden) wait(); // a person is ticking the box: no time limit
            else resolve('');
          }, TOKEN_WAIT_MS);
        })();
      });
    }

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) { observer.disconnect(); start(); }
      }, { rootMargin: '600px 0px' });
      observer.observe(form);
    } else {
      start();
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!endpoint || !sitekey) { say(form.getAttribute('data-msg-nocfg')); return; }
      if (!form.checkValidity()) { form.reportValidity(); say(form.getAttribute('data-msg-invalid')); return; }
      var email = form.elements.namedItem('email');
      if (email && !EMAIL_RE.test(email.value.trim())) {
        email.setAttribute('aria-invalid', 'true');
        email.focus();
        say(form.getAttribute('data-msg-invalid'));
        return;
      }
      var data = {};
      new FormData(form).forEach(function (value, key) { data[key] = value; });
      var label = submit.textContent;
      submit.disabled = true;
      submit.textContent = form.getAttribute('data-msg-sending');
      say('');
      form.querySelectorAll('[aria-invalid]').forEach(function (el) { el.removeAttribute('aria-invalid'); });
      var controller = 'AbortController' in window ? new AbortController() : null;
      getToken().then(function (value) {
        if (!value) throw { kind: 'captcha' };
        token = ''; // a token works once
        if (controller) setTimeout(function () { controller.abort(); }, SEND_TIMEOUT_MS);
        return fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller ? controller.signal : undefined,
          body: JSON.stringify({
            // Only the page's address: a query string or fragment never reaches the mail.
            kind: form.getAttribute('data-kind'), lang: form.getAttribute('data-lang'), page: location.origin + location.pathname,
            name: data.name || '', organization: data.organization || '', email: data.email || '',
            phone: data.phone || '', place: data.place || '', message: data.message || '',
            website: data.website || '', token: value
          })
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (json) {
            if (res.ok && json.ok) {
              form.hidden = true;
              if (done) { done.hidden = false; done.focus(); }
              return;
            }
            throw { kind: ['invalid', 'captcha', 'rate'].indexOf(json.error) >= 0 ? json.error : 'error', fields: json.fields };
          });
        });
      }).catch(function (err) {
        var kind = err && err.kind;
        say(form.getAttribute(kind === 'invalid' ? 'data-msg-invalid' : kind === 'captcha' ? 'data-msg-captcha'
          : kind === 'rate' ? 'data-msg-rate' : 'data-msg-error'));
        // The Worker names the fields it refused: mark them and put the cursor in the first one.
        var first = null;
        ((err && err.fields) || []).forEach(function (name) {
          var control = form.elements.namedItem(name);
          if (control && control.setAttribute) {
            control.setAttribute('aria-invalid', 'true');
            if (!first) first = control;
          }
        });
        if (first) first.focus();
      }).then(function () {
        submit.disabled = false;
        submit.textContent = label;
        if (widgetId !== null && window.turnstile) { pending = true; window.turnstile.reset(widgetId); }
      });
    });
  });
})();
