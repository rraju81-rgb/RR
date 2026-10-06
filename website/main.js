/* pi.XL 3D Printing — site interactions. No dependencies. */
(() => {
  'use strict';

  // ============ EDIT YOUR CONTACT DETAILS HERE (one place only) ============
  const CONFIG = {
    brand: 'pi.XL 3D Printing',
    instagram: 'pi.xl3dprinting', // handle without the @
    whatsapp: '919999999999',     // country code + number, digits only  ⚠️ REPLACE with your real number
    email: 'pixldprinting@gmail.com',
  };
  // Build volumes in mm, used by the "Will it fit?" checker
  const OUR_BED = [420, 420, 500];
  const STD_BED = 256;
  // =========================================================================

  document.documentElement.classList.add('js');
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- Contact links ----
  const waLink = (text) => `https://wa.me/${CONFIG.whatsapp}?text=${encodeURIComponent(text)}`;
  $$('[data-wa]').forEach((a) => { a.href = waLink(`Hi ${CONFIG.brand}! I'd like to place an order / get a quote.`); });
  $$('[data-ig]').forEach((a) => { a.href = `https://instagram.com/${CONFIG.instagram}`; if (a.textContent.startsWith('@')) a.textContent = '@' + CONFIG.instagram; });
  $$('[data-ig-dm]').forEach((a) => { a.href = `https://ig.me/m/${CONFIG.instagram}`; });
  $$('[data-ig-label]').forEach((el) => { el.textContent = '@' + CONFIG.instagram; });
  $$('[data-mail-label]').forEach((el) => { el.textContent = CONFIG.email; });
  $$('[data-mail]').forEach((a) => { a.href = `mailto:${CONFIG.email}?subject=${encodeURIComponent('Order / quote request — ' + CONFIG.brand)}`; });

  // ---- Header + mobile nav ----
  const header = $('[data-header]');
  const nav = $('[data-nav]');
  const toggle = $('[data-nav-toggle]');
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const setNav = (open) => {
    nav.classList.toggle('open', open);
    header.classList.toggle('menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  };
  toggle.addEventListener('click', () => setNav(!nav.classList.contains('open')));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) setNav(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && nav.classList.contains('open')) { setNav(false); toggle.focus(); } });
  window.matchMedia('(min-width: 901px)').addEventListener('change', (m) => { if (m.matches) setNav(false); });

  // ---- Scroll effects ----
  const once = (els, fn, opts) => {
    if (!('IntersectionObserver' in window)) { els.forEach(fn); return; }
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { fn(en.target); io.unobserve(en.target); }
    }), opts);
    els.forEach((el) => io.observe(el));
  };

  $$('.reveal').forEach((el, i) => { el.style.transitionDelay = `${(i % 4) * 60}ms`; });
  once($$('.reveal'), (el) => el.classList.add('in'), { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  once($$('[data-bars]'), (el) => el.classList.add('in-view'), { threshold: 0.3 });

  // Count-up numbers (the HTML already holds the final values, so nothing breaks without JS)
  once($$('[data-count]'), (el) => {
    if (reduceMotion) return;
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const decimals = (el.dataset.count.split('.')[1] || '').length;
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min((t - t0) / 1200, 1);
      el.textContent = (target * (1 - Math.pow(1 - p, 3))).toFixed(decimals) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, { threshold: 0.6 });

  // Active nav link
  const links = $$('.nav a[href^="#"]:not(.btn)');
  if ('IntersectionObserver' in window) {
    const spy = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) links.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === '#' + en.target.id));
    }), { rootMargin: '-45% 0px -50% 0px' });
    links.map((a) => $(a.getAttribute('href'))).filter(Boolean).forEach((s) => spy.observe(s));
  }

  // Hide the floating WhatsApp button while the order form (which has its own) is on screen
  const fab = $('.fab');
  const orderCard = $('#order');
  if (fab && orderCard && 'IntersectionObserver' in window) {
    new IntersectionObserver(([en]) => fab.classList.toggle('hide', en.isIntersecting), { threshold: 0.1 }).observe(orderCard);
  }

  // ---- "Will it fit?" checker ----
  const fit = $('[data-fit]');
  if (fit) {
    const ours = $('[data-fit-ours]', fit);
    const std = $('[data-fit-std]', fit);
    const piecesFor = (dims, bed) => {
      // try each axis as the vertical one and keep the orientation needing the fewest pieces
      const [x, y, z] = bed;
      const orientations = [[dims[0], dims[1], dims[2]], [dims[0], dims[2], dims[1]], [dims[1], dims[2], dims[0]]];
      return Math.min(...orientations.map(([a, b, c]) =>
        Math.min(Math.ceil(a / x) * Math.ceil(b / y), Math.ceil(b / x) * Math.ceil(a / y)) * Math.ceil(c / z)));
    };
    const show = (box, n, extra) => {
      box.classList.toggle('bad', n > 1);
      $('b', box).textContent = n === 1 ? '✓ One piece' : `${n} pieces${extra}`;
    };
    const update = () => {
      const dims = ['l', 'w', 'h'].map((k) => Number(fit.elements[k].value));
      if (dims.some((d) => !(d > 0))) {
        $$('.fit-box', fit).forEach((b) => { b.classList.remove('bad'); $('b', b).textContent = 'Enter all 3 sizes'; });
        return;
      }
      show(ours, piecesFor(dims, OUR_BED), '');
      show(std, piecesFor(dims, [STD_BED, STD_BED, STD_BED]), ' + glue');
    };
    fit.addEventListener('input', update);
    fit.addEventListener('submit', (e) => e.preventDefault());
    update();
  }

  // ---- Display shelf field guide ----
  const guide = $('[data-guide]');
  const guideBody = $('[data-guide-body]');
  const fields = $('#fields');
  if (guide && typeof guide.showModal === 'function') {
    let opener = null;
    $$('[data-field]').forEach((card) => card.addEventListener('click', () => {
      const src = fields.content.querySelector(`[data-field-id="${card.dataset.field}"]`);
      if (!src) return;
      guideBody.replaceChildren(src.cloneNode(true));
      opener = card;
      guide.showModal();
    }));
    $('[data-guide-close]').addEventListener('click', () => guide.close());
    guide.addEventListener('click', (e) => { if (e.target === guide) guide.close(); });
    guide.addEventListener('close', () => opener?.focus());
  } else {
    // very old browsers: send people to the order form instead
    $$('[data-field]').forEach((card) => card.addEventListener('click', () => { location.hash = '#order'; }));
  }

  // ---- Order form → WhatsApp (pre-typed) or Instagram DM (copied) ----
  const form = $('[data-order]');
  if (form) {
    const status = $('[data-status]', form);
    const nameField = $('#o-name', form);
    const setStatus = (text, bad) => { status.textContent = text; status.classList.toggle('bad', !!bad); };

    const valid = () => {
      const ok = nameField.value.trim().length > 0;
      nameField.closest('.field').classList.toggle('invalid', !ok);
      nameField.setAttribute('aria-invalid', String(!ok));
      if (!ok) nameField.setAttribute('aria-describedby', 'o-name-err');
      return ok;
    };
    nameField.addEventListener('input', () => { if (nameField.closest('.field').classList.contains('invalid')) valid(); });

    const message = () => {
      const f = new FormData(form);
      const line = (label, v) => (v && String(v).trim() ? `${label}: ${String(v).trim()}\n` : '');
      return `Hi ${CONFIG.brand}! I'd like to place an order / get a quote.\n` +
        line('Name', f.get('name')) + line('Category', f.get('category')) + line('Size', f.get('size')) +
        (line('Material', f.get('material')) + line('Details', f.get('details'))).trimEnd();
    };

    const copy = async (text) => {
      try { await navigator.clipboard.writeText(text); return true; } catch {
        const ta = Object.assign(document.createElement('textarea'), { value: text });
        ta.style.cssText = 'position:fixed;opacity:0';
        document.body.appendChild(ta); ta.select();
        let ok = false;
        try { ok = document.execCommand('copy'); } catch { /* ignore */ }
        ta.remove();
        return ok;
      }
    };

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!valid()) { nameField.focus(); setStatus('Please add your name so we know who to reply to.', true); return; }
      window.open(waLink(message()), '_blank', 'noopener');
      setStatus('✅ WhatsApp opened with your order typed in. Just hit send.');
    });

    $('[data-send="ig"]', form).addEventListener('click', async () => {
      if (!valid()) { nameField.focus(); setStatus('Please add your name so we know who to reply to.', true); return; }
      const copied = await copy(message());
      window.open(`https://ig.me/m/${CONFIG.instagram}`, '_blank', 'noopener');
      setStatus(copied ? '✅ Message copied. Paste it into the Instagram chat that just opened.' : 'Instagram opened. Tell us your project in the chat.');
    });
  }
})();
