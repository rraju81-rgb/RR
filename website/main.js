/* PiXL 3D Printing — site interactions. No dependencies. */
(() => {
  'use strict';

  // ---- Business settings: edit these ----
  const CONFIG = {
    email: 'hello@pixl3d.example',
    // Paste a Formspree / Web3Forms / Getform endpoint here to receive submissions
    // (with file attachments) directly. Leave empty to fall back to the visitor's email app.
    formEndpoint: '',
    currency: 'INR',
    locale: 'en-IN',
    // Estimator pricing (per cm³ of printed material, plus fixed costs)
    ratePerCm3: { pla: 6, petg: 7, abs: 8, tpu: 11, nylon: 16, resin: 18 },
    setupFee: 150,
    minPerPart: 99,
    finishPerPart: 120,
  };

  document.documentElement.classList.add('js');
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // ---- Header: shadow on scroll + mobile nav ----
  const header = $('[data-header]');
  const nav = $('[data-nav]');
  const toggle = $('[data-nav-toggle]');
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const setNav = (open) => {
    nav.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    header.classList.toggle('menu-open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  };
  toggle.addEventListener('click', () => setNav(!nav.classList.contains('open')));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) setNav(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && nav.classList.contains('open')) { setNav(false); toggle.focus(); } });
  window.matchMedia('(min-width: 881px)').addEventListener('change', (m) => { if (m.matches) setNav(false); });

  // ---- Active nav link while scrolling ----
  const links = $$('.nav a[href^="#"]:not(.btn)');
  const sections = links.map((a) => $(a.getAttribute('href'))).filter(Boolean);
  if ('IntersectionObserver' in window) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        links.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === '#' + en.target.id));
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach((s) => spy.observe(s));

    // ---- Reveal on scroll ----
    const rev = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add('in'); rev.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    $$('.reveal').forEach((el, i) => {
      el.style.transitionDelay = `${(i % 3) * 70}ms`;
      rev.observe(el);
    });
  } else {
    $$('.reveal').forEach((el) => el.classList.add('in'));
  }

  // ---- Accessible tabs (materials) ----
  $$('[data-tabs]').forEach((root) => {
    const tabs = $$('[role="tab"]', root);
    const select = (tab, focus) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        $('#' + t.getAttribute('aria-controls')).hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => select(t));
      t.addEventListener('keydown', (e) => {
        const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (d) { e.preventDefault(); select(tabs[(i + d + tabs.length) % tabs.length], true); }
      });
    });
  });

  // ---- FAQ: keep one open at a time ----
  const faqs = $$('.faq details');
  faqs.forEach((d) => d.addEventListener('toggle', () => {
    if (d.open) faqs.forEach((o) => { if (o !== d) o.open = false; });
  }));

  // ---- Price estimator ----
  const money = new Intl.NumberFormat(CONFIG.locale, { style: 'currency', currency: CONFIG.currency, maximumFractionDigits: 0 });
  const est = $('[data-estimator]');
  let lastEstimate = '';
  if (est) {
    const qty = $('#est-qty', est);
    const sizeOut = $('[data-size-out]', est);
    const totalEl = $('[data-est-total]', est);
    const eachEl = $('[data-est-each]', est);

    const clampQty = () => {
      const n = Math.round(Number(qty.value));
      qty.value = Number.isFinite(n) ? Math.min(999, Math.max(1, n)) : 1;
    };

    const calc = () => {
      const f = new FormData(est);
      const material = f.get('material');
      const size = Number(f.get('size'));
      const infill = Number(f.get('infill'));
      const n = Math.min(999, Math.max(1, Math.round(Number(f.get('qty'))) || 1));
      const finish = f.get('finish') === 'on';

      // Rough printed volume: bounding cube of the longest side, ~18% solid at standard infill.
      const cm = size / 10;
      const volume = Math.pow(cm, 3) * 0.18 * infill;
      let each = Math.max(CONFIG.minPerPart, volume * CONFIG.ratePerCm3[material]);
      if (finish) each += CONFIG.finishPerPart;

      // Volume discount: up to 25% off at 50+ units
      const discount = n >= 50 ? 0.25 : n >= 25 ? 0.18 : n >= 10 ? 0.12 : 0;
      each *= 1 - discount;
      const total = Math.round(each * n + CONFIG.setupFee);

      sizeOut.textContent = `${size} mm`;
      totalEl.textContent = money.format(total);
      eachEl.textContent = n > 1
        ? `${money.format(Math.round(each))} each${discount ? ` · ${Math.round(discount * 100)}% volume discount` : ''}`
        : 'Includes setup';

      const matLabel = $('#est-material', est).selectedOptions[0].textContent;
      const infLabel = $(`input[name="infill"]:checked + label`, est).textContent;
      lastEstimate = `${n} × ${matLabel}, ~${size} mm, ${infLabel.toLowerCase()} infill${finish ? ', post-processed' : ''}. Online estimate: ${money.format(total)}.`;
    };

    est.addEventListener('input', calc);
    est.addEventListener('submit', (e) => e.preventDefault());
    qty.addEventListener('change', () => { clampQty(); calc(); });
    $$('[data-qty]', est).forEach((b) => b.addEventListener('click', () => {
      qty.value = Number(qty.value || 1) + Number(b.dataset.qty);
      clampQty(); calc();
    }));

    // Carry the estimate into the contact form
    $('[data-est-cta]', est).addEventListener('click', () => {
      const msg = $('#c-msg');
      if (msg && !msg.value.trim()) msg.value = lastEstimate + '\n\n';
      setTimeout(() => $('#c-name')?.focus({ preventScroll: true }), 600);
    });
    calc();
  }

  // ---- File drop zone ----
  const drop = $('[data-drop]');
  const fileInput = $('#c-file');
  const dropText = $('[data-drop-text]');
  const MAX_MB = 25;
  const showFile = () => {
    const file = fileInput.files[0];
    if (!file) { drop.classList.remove('has-file'); dropText.innerHTML = 'Drop STL / STEP / OBJ here or <u>browse</u>'; return; }
    if (file.size > MAX_MB * 1024 * 1024) {
      fileInput.value = '';
      drop.classList.remove('has-file');
      dropText.textContent = `That file is over ${MAX_MB} MB. Please share a link in the message instead.`;
      return;
    }
    drop.classList.add('has-file');
    dropText.textContent = `${file.name} (${(file.size / 1048576).toFixed(1)} MB)`;
  };
  if (drop && fileInput) {
    fileInput.addEventListener('change', showFile);
    ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('drag'); }));
    drop.addEventListener('drop', (e) => {
      if (e.dataTransfer?.files?.length) { fileInput.files = e.dataTransfer.files; showFile(); }
    });
  }

  // ---- Contact form ----
  const form = $('[data-contact-form]');
  if (form) {
    const status = $('[data-form-status]', form);
    const submitBtn = $('button[type="submit"]', form);
    const required = $$('[required]', form);

    const validate = (el) => {
      const ok = el.type === 'email' ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value.trim()) : el.value.trim().length > 0;
      el.closest('.field').classList.toggle('invalid', !ok);
      el.setAttribute('aria-invalid', String(!ok));
      const err = $(`[data-err-for="${el.id}"]`, form);
      if (err) { err.id = err.id || `${el.id}-err`; el.setAttribute('aria-describedby', err.id); }
      return ok;
    };
    required.forEach((el) => {
      el.addEventListener('blur', () => { if (el.value) validate(el); });
      el.addEventListener('input', () => { if (el.closest('.field').classList.contains('invalid')) validate(el); });
    });

    const setStatus = (text, cls) => { status.textContent = text; status.className = `form-status ${cls || ''}`; };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const bad = required.filter((el) => !validate(el));
      if (bad.length) { bad[0].focus(); setStatus('Please fix the highlighted fields.', 'bad'); return; }

      const data = new FormData(form);

      if (!CONFIG.formEndpoint) {
        // No backend configured: open the visitor's email app with everything filled in.
        const body = `Name: ${data.get('name')}\nEmail: ${data.get('email')}\nProject: ${data.get('type')}\n\n${data.get('message')}` +
          (fileInput.files[0] ? `\n\n(I'll attach my file: ${fileInput.files[0].name})` : '');
        window.location.href = `mailto:${CONFIG.email}?subject=${encodeURIComponent('3D print request: ' + data.get('type'))}&body=${encodeURIComponent(body)}`;
        setStatus('Opening your email app… If nothing happens, email us at ' + CONFIG.email, 'ok');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending…';
      setStatus('');
      try {
        const res = await fetch(CONFIG.formEndpoint, { method: 'POST', body: data, headers: { Accept: 'application/json' } });
        if (!res.ok) throw new Error(String(res.status));
        form.reset();
        showFile();
        setStatus('Thanks! We got your request and will reply with a quote shortly.', 'ok');
      } catch {
        setStatus(`Something went wrong. Please email us at ${CONFIG.email}.`, 'bad');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send request';
      }
    });
  }

  // ---- Keep contact details in sync with CONFIG ----
  $$('a[href^="mailto:"]').forEach((a) => { a.href = `mailto:${CONFIG.email}`; if (a.textContent.includes('@')) a.textContent = CONFIG.email; });

  const y = $('[data-year]');
  if (y) y.textContent = new Date().getFullYear();
})();
