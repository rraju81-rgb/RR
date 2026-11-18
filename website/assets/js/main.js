/* RR · Carbon Fibre & 3D Printing — site scripts. No dependencies. */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  root.classList.add('js');

  /* ------------------------------------------------------------------
     Page transitions. Links with data-transition="carbon|print" play a
     cover animation, then navigate. The next page opens on the same
     frame (its own .wipe--enter) and plays the reveal in CSS.
     ------------------------------------------------------------------ */
  var STRIPS = { carbon: 7, print: 12 };
  var EXIT_MS = { carbon: 1080, print: 1100 };
  var leaving = false;
  var safetyTimer = 0;

  function buildWipe(kind, title) {
    var wipe = doc.createElement('div');
    wipe.className = 'wipe wipe--' + kind + ' wipe--exit';
    wipe.setAttribute('aria-hidden', 'true');

    var strips = doc.createElement('div');
    strips.className = 'wipe__strips';
    for (var i = 0; i < STRIPS[kind]; i++) {
      var strip = doc.createElement('i');
      strip.style.setProperty('--i', i);
      strips.appendChild(strip);
    }
    wipe.appendChild(strips);

    var label = doc.createElement('div');
    label.className = 'wipe__label';
    var mark = doc.createElement('img');
    mark.src = 'assets/img/logo-mark.svg';
    mark.alt = '';
    mark.width = 56;
    mark.height = 56;
    var name = doc.createElement('span');
    name.className = 'wipe__title';
    name.textContent = title;
    var bar = doc.createElement('span');
    bar.className = 'wipe__bar';
    label.appendChild(mark);
    label.appendChild(name);
    label.appendChild(bar);
    wipe.appendChild(label);
    return wipe;
  }

  function resetLeaving() {
    leaving = false;
    window.clearTimeout(safetyTimer);
    $$('.wipe--exit').forEach(function (w) { w.remove(); });
    var chooser = $('.chooser');
    if (chooser) chooser.removeAttribute('data-leaving');
  }

  function leaveTo(link) {
    if (leaving) return;
    var kind = link.getAttribute('data-transition');
    var href = link.href;
    if (!STRIPS[kind] || reduceMotion.matches) {
      window.location.assign(href);
      return;
    }
    leaving = true;
    setMenu(false);
    var chooser = $('.chooser');
    if (chooser) chooser.setAttribute('data-leaving', kind);
    doc.body.appendChild(buildWipe(kind, link.getAttribute('data-title') || ''));
    window.setTimeout(function () { window.location.assign(href); }, EXIT_MS[kind]);
    // If navigation never happens (offline, blocked), give the page back.
    safetyTimer = window.setTimeout(resetLeaving, 5000);
  }

  doc.addEventListener('click', function (e) {
    var link = e.target.closest && e.target.closest('a[data-transition]');
    if (!link) return;
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (link.target && link.target !== '_self') return;
    e.preventDefault();
    leaveTo(link);
  });

  // Back/forward cache: a restored page must not still be mid-transition.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      resetLeaving();
      setMenu(false);
    }
  });

  // Drop the entrance overlay once it has played.
  $$('.wipe--enter').forEach(function (w) {
    window.setTimeout(function () { w.remove(); }, 1600);
  });

  /* ------------------------------------------------------------------
     Carbon sheen: a light moves over the weave and flips the twill,
     like tilting a carbon panel under a lamp. Follows the pointer on
     desktop, drifts on its own elsewhere.
     ------------------------------------------------------------------ */
  function initSheen(el, opts) {
    var tilt = !!(opts && opts.tilt);
    var area = (opts && opts.area) || el;
    var x = 0.32, y = 0.42, tx = x, ty = y;
    var tracking = false;
    var visible = true;
    var raf = 0;
    var start = performance.now();

    function apply() {
      el.style.setProperty('--mx', (x * 100).toFixed(2) + '%');
      el.style.setProperty('--my', (y * 100).toFixed(2) + '%');
      if (tilt) {
        el.style.setProperty('--ry', ((x - 0.5) * 22).toFixed(2) + 'deg');
        el.style.setProperty('--rx', ((0.5 - y) * 16).toFixed(2) + 'deg');
      }
    }

    if (reduceMotion.matches) { apply(); return; }

    function frame(now) {
      raf = 0;
      if (!tracking) {
        var t = (now - start) / 1000;
        tx = 0.5 + 0.34 * Math.sin(t * 0.33);
        ty = 0.5 + 0.3 * Math.sin(t * 0.21 + 1.2);
      }
      x += (tx - x) * 0.07;
      y += (ty - y) * 0.07;
      apply();
      if (visible && !doc.hidden) raf = window.requestAnimationFrame(frame);
    }
    function kick() { if (!raf && visible && !doc.hidden) raf = window.requestAnimationFrame(frame); }

    if (finePointer.matches) {
      area.addEventListener('pointermove', function (e) {
        var r = el.getBoundingClientRect();
        if (!r.width || !r.height) return;
        tracking = true;
        tx = Math.min(1.1, Math.max(-0.1, (e.clientX - r.left) / r.width));
        ty = Math.min(1.1, Math.max(-0.1, (e.clientY - r.top) / r.height));
        kick();
      });
      area.addEventListener('pointerleave', function () {
        tracking = false;
        start = performance.now() - 4000;
      });
    }

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        kick();
      }).observe(el);
    }
    doc.addEventListener('visibilitychange', kick);
    kick();
  }

  var chooser = $('.chooser');
  if (chooser) initSheen(chooser, { area: chooser });
  var plate = $('[data-plate]');
  if (plate) initSheen(plate, { tilt: true, area: plate.closest('.hero') || plate });

  /* ------------------------------------------------------------------
     Print build: a vase printed one layer at a time, nozzle and all.
     ------------------------------------------------------------------ */
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var buildCount = 0;

  function svgEl(name, attrs, parent) {
    var node = doc.createElementNS(SVG_NS, name);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function initPrintBuild(svg) {
    var id = 'pb' + (++buildCount);
    var LAYERS = parseInt(svg.getAttribute('data-layers'), 10) || 60;
    var LAYER_MS = parseInt(svg.getAttribute('data-layer-ms'), 10) || 85;
    var LAYER_MM = 0.2;
    var CX = 200, BED_Y = 412, HEIGHT = 286, RY = 0.26;
    var step = HEIGHT / LAYERS;
    var hudLayer = svg.parentNode.querySelector('[data-hud-layer]');
    var hudZ = svg.parentNode.querySelector('[data-hud-z]');
    var hudTotal = svg.parentNode.querySelector('[data-hud-total]');
    if (hudTotal) hudTotal.textContent = String(LAYERS).padStart(3, '0');

    function profile(t) {
      var belly = 48 + 44 * Math.sin(Math.PI * Math.min(t / 0.74, 1));
      var flare = 22 * Math.pow(Math.max(0, (t - 0.8) / 0.2), 2);
      return belly + flare + 2.2 * Math.sin(t * Math.PI * 2 * 9);
    }

    svg.setAttribute('viewBox', '0 -40 400 520');
    svg.setAttribute('role', 'img');
    svg.innerHTML = '';

    var defs = svgEl('defs', {}, svg);
    var wall = svgEl('linearGradient', { id: id + 'w', x1: 0, x2: 1, y1: 0, y2: 0 }, defs);
    [['0', '#9c3a16'], ['.16', '#e05a24'], ['.36', '#ffa06b'], ['.52', '#ff7a3d'], ['.84', '#cf4e1c'], ['1', '#86300f']]
      .forEach(function (s) { svgEl('stop', { offset: s[0], 'stop-color': s[1] }, wall); });
    var glow = svgEl('radialGradient', { id: id + 'g' }, defs);
    svgEl('stop', { offset: '0', 'stop-color': '#ffd0a8', 'stop-opacity': '.95' }, glow);
    svgEl('stop', { offset: '1', 'stop-color': '#ff6b2c', 'stop-opacity': '0' }, glow);
    var feed = svgEl('linearGradient', { id: id + 'f', gradientUnits: 'userSpaceOnUse', x1: 0, y1: -150, x2: 0, y2: -330 }, defs);
    svgEl('stop', { offset: '0', 'stop-color': '#ff6b2c' }, feed);
    svgEl('stop', { offset: '1', 'stop-color': '#ff6b2c', 'stop-opacity': '0' }, feed);
    var dots = svgEl('pattern', { id: id + 'd', width: 9, height: 9, patternUnits: 'userSpaceOnUse' }, defs);
    svgEl('circle', { cx: 4.5, cy: 4.5, r: 0.9, fill: '#3d444d' }, dots);

    // Build plate: textured black sheet on a steel bed.
    var bedRx = 176, bedRy = bedRx * RY;
    svgEl('ellipse', { cx: CX, cy: BED_Y + 14, rx: bedRx, ry: bedRy, fill: '#16191c' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 4, rx: bedRx, ry: bedRy, fill: '#2b3036' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 4, rx: bedRx, ry: bedRy, fill: 'url(#' + id + 'd)', opacity: '.8' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 4, rx: bedRx - 1, ry: bedRy - 1, fill: 'none', stroke: '#4a525b', 'stroke-width': 1.5 }, svg);

    var object = svgEl('g', {}, svg);
    var arcs = [];
    for (var i = 0; i < LAYERS; i++) {
      var w = profile(i / (LAYERS - 1));
      var ly = BED_Y - i * step;
      var p = svgEl('path', {
        d: 'M' + (CX - w).toFixed(2) + ' ' + ly.toFixed(2) + 'A' + w.toFixed(2) + ' ' + (w * RY).toFixed(2) +
          ' 0 0 0 ' + (CX + w).toFixed(2) + ' ' + ly.toFixed(2),
        fill: 'none',
        stroke: 'url(#' + id + 'w)',
        'stroke-width': (step * 0.86).toFixed(2),
        'stroke-linecap': 'round'
      }, object);
      arcs.push({ el: p, w: w, y: ly, len: 0 });
    }
    arcs.forEach(function (a) {
      a.len = a.el.getTotalLength();
      a.el.style.strokeDasharray = a.len + ' ' + a.len;
      a.el.style.strokeDashoffset = a.len;
    });

    var rim = svgEl('path', {
      fill: 'none', stroke: '#6b260c', 'stroke-width': (step * 0.86).toFixed(2), 'stroke-linecap': 'round'
    }, object);

    // X gantry + print head. Origin of the head group is the nozzle tip.
    var gantry = svgEl('g', {}, svg);
    svgEl('rect', { x: 0, y: -122, width: 400, height: 12, rx: 2, fill: '#2b3036' }, gantry);
    svgEl('rect', { x: 0, y: -122, width: 400, height: 3, fill: '#4a525b' }, gantry);
    var head = svgEl('g', {}, svg);
    svgEl('rect', { x: -1.5, y: -330, width: 3, height: 200, fill: 'url(#' + id + 'f)' }, head);
    var glowDot = svgEl('circle', { cx: 0, cy: 0, r: 18, fill: 'url(#' + id + 'g)' }, head);
    svgEl('rect', { x: -40, y: -132, width: 80, height: 34, rx: 4, fill: '#1d2125' }, head);
    svgEl('rect', { x: -20, y: -98, width: 40, height: 46, fill: '#3a414a' }, head);
    for (var f = 0; f < 6; f++) svgEl('rect', { x: -24, y: -94 + f * 7, width: 48, height: 3, fill: '#59616a' }, head);
    svgEl('rect', { x: -27, y: -50, width: 54, height: 28, rx: 3, fill: '#a7afb8' }, head);
    svgEl('circle', { cx: -13, cy: -36, r: 5, fill: '#59616a' }, head);
    svgEl('rect', { x: -10, y: -22, width: 20, height: 8, fill: '#b88a2e' }, head);
    svgEl('path', { d: 'M-7 -14L7 -14L2.6 -1.5L-2.6 -1.5Z', fill: '#d4a640', stroke: '#8a6a22', 'stroke-width': 1 }, head);

    var phase = 'build';
    var progress = 0;
    var drawn = 0;
    var rimLayer = -1;
    var phaseStart = 0;
    var last = 0;
    var running = false;
    var visible = true;
    var hx = CX - arcs[0].w, hy = BED_Y;
    var parkFrom = null;

    function setHead(x, y) {
      hx = x; hy = y;
      head.setAttribute('transform', 'translate(' + x.toFixed(2) + ' ' + y.toFixed(2) + ')');
      gantry.setAttribute('transform', 'translate(0 ' + y.toFixed(2) + ')');
    }

    function setRim(k, frac) {
      if (k < 0) { rim.style.display = 'none'; return; }
      var a = arcs[k];
      if (rimLayer !== k) {
        rim.setAttribute('d', 'M' + (CX + a.w).toFixed(2) + ' ' + a.y.toFixed(2) + 'A' + a.w.toFixed(2) + ' ' +
          (a.w * RY).toFixed(2) + ' 0 0 0 ' + (CX - a.w).toFixed(2) + ' ' + a.y.toFixed(2));
        rim.__len = rim.getTotalLength();
        rim.style.strokeDasharray = rim.__len + ' ' + rim.__len;
        rimLayer = k;
      }
      rim.style.display = '';
      rim.style.strokeDashoffset = rim.__len * (1 - frac);
    }

    function setHud(layer) {
      if (hudLayer) hudLayer.textContent = String(layer).padStart(3, '0');
      if (hudZ) hudZ.textContent = (layer * LAYER_MM).toFixed(2);
    }

    function render(p) {
      var k = Math.min(Math.floor(p), LAYERS - 1);
      var frac = p >= LAYERS ? 1 : p - Math.floor(p);
      while (drawn < k) { arcs[drawn].el.style.strokeDashoffset = 0; drawn++; }
      var a = arcs[k];
      var ry = a.w * RY;
      if (frac < 0.5) {
        var u = frac * 2;
        a.el.style.strokeDashoffset = a.len * (1 - u);
        setRim(k - 1, 1);
        var phi = u * Math.PI;
        setHead(CX - a.w * Math.cos(phi), a.y + ry * Math.sin(phi));
      } else {
        var v = (frac - 0.5) * 2;
        a.el.style.strokeDashoffset = 0;
        setRim(k, v);
        var psi = v * Math.PI;
        setHead(CX + a.w * Math.cos(psi), a.y - ry * Math.sin(psi));
      }
      setHud(Math.min(k + 1, LAYERS));
    }

    function reset() {
      arcs.forEach(function (a) { a.el.style.strokeDashoffset = a.len; });
      object.style.opacity = 1;
      drawn = 0;
      rimLayer = -1;
      setRim(-1);
      progress = 0;
      setHud(0);
    }

    function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

    function frame(now) {
      if (!running) return;
      var dt = last ? Math.min(now - last, 64) : 16;
      last = now;

      if (phase === 'build') {
        progress += dt / LAYER_MS;
        if (progress >= LAYERS) {
          progress = LAYERS;
          render(LAYERS - 0.0001);
          phase = 'park';
          phaseStart = now;
          parkFrom = [hx, hy];
        } else {
          render(progress);
        }
      } else if (phase === 'park') {
        var t = Math.min((now - phaseStart) / 900, 1);
        var e = ease(t);
        setHead(parkFrom[0] + (CX + 130 - parkFrom[0]) * e, parkFrom[1] + (96 - parkFrom[1]) * e);
        glowDot.style.opacity = 1 - e;
        if (now - phaseStart > 2600) { phase = 'clear'; phaseStart = now; parkFrom = [hx, hy]; }
      } else if (phase === 'clear') {
        var c = Math.min((now - phaseStart) / 900, 1);
        var ec = ease(c);
        object.style.opacity = 1 - Math.min(c * 1.6, 1);
        setHead(parkFrom[0] + (CX - arcs[0].w - parkFrom[0]) * ec, parkFrom[1] + (BED_Y - parkFrom[1]) * ec);
        if (c >= 1) { reset(); glowDot.style.opacity = 1; phase = 'build'; }
      }
      window.requestAnimationFrame(frame);
    }

    function play() {
      if (running || reduceMotion.matches) return;
      running = true;
      last = 0;
      window.requestAnimationFrame(frame);
    }
    function pause() { running = false; }

    if (reduceMotion.matches) {
      // Show the finished print, nozzle parked.
      arcs.forEach(function (a) { a.el.style.strokeDashoffset = 0; });
      setRim(LAYERS - 1, 1);
      setHead(CX + 130, 96);
      glowDot.style.opacity = 0;
      setHud(LAYERS);
      return;
    }

    reset();
    setHead(CX - arcs[0].w, BED_Y);

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible && !doc.hidden) play(); else pause();
      }).observe(svg);
    } else {
      play();
    }
    doc.addEventListener('visibilitychange', function () {
      if (doc.hidden) pause(); else if (visible) play();
    });
  }

  $$('[data-print-build]').forEach(initPrintBuild);

  /* ------------------------------------------------------------------
     Header: solid background once scrolled, and the phone menu.
     ------------------------------------------------------------------ */
  var header = $('[data-header]');
  var navToggle = $('.nav-toggle');

  function setMenu(open) {
    if (!header || !navToggle) return;
    navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    header.classList.toggle('is-open', open);
  }

  if (header) {
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 24); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  if (navToggle) {
    navToggle.addEventListener('click', function () {
      setMenu(navToggle.getAttribute('aria-expanded') !== 'true');
    });
    $('#site-menu').addEventListener('click', function (e) {
      if (e.target.closest('a')) setMenu(false);
    });
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && header.classList.contains('is-open')) {
        setMenu(false);
        navToggle.focus();
      }
    });
  }

  /* ------------------------------------------------------------------
     Gallery rows: fill each row past the screen width, then loop it.
     ------------------------------------------------------------------ */
  var work = $('.work');
  var marquees = $$('[data-marquee]');
  var cards = [];

  marquees.forEach(function (m) {
    $$('.work-card', m).forEach(function (card) {
      card.setAttribute('data-index', cards.length);
      cards.push(card);
    });
  });

  function cloneCard(card) {
    var c = card.cloneNode(true);
    c.setAttribute('data-clone', '');
    c.setAttribute('aria-hidden', 'true');
    $$('button, a', c).forEach(function (b) { b.tabIndex = -1; });
    return c;
  }

  function fillMarquee(m) {
    var track = $('.marquee__track', m);
    $$('[data-clone]', track).forEach(function (n) { n.remove(); });
    m.classList.remove('is-running');
    if (reduceMotion.matches) return;

    var originals = $$('.work-card', track);
    if (!originals.length) return;
    var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    var setWidth = track.scrollWidth;
    var unitWidth = setWidth;
    var unit = originals.slice();
    var guard = 0;
    while (unitWidth < m.clientWidth + 1 && guard++ < 20) {
      originals.forEach(function (o) {
        var c = cloneCard(o);
        track.appendChild(c);
        unit.push(c);
      });
      unitWidth += setWidth + gap;
    }
    unit.forEach(function (n) { track.appendChild(cloneCard(n)); });
    var speed = parseFloat(m.getAttribute('data-speed')) || 40;
    track.style.setProperty('--duration', ((unitWidth + gap) / speed).toFixed(1) + 's');
    m.classList.add('is-running');
  }

  if (marquees.length) {
    marquees.forEach(fillMarquee);
    var lastWidth = window.innerWidth;
    var resizeTimer = 0;
    window.addEventListener('resize', function () {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(function () {
        if (Math.abs(window.innerWidth - lastWidth) < 40) return;
        lastWidth = window.innerWidth;
        marquees.forEach(fillMarquee);
      }, 200);
    });
    reduceMotion.addEventListener && reduceMotion.addEventListener('change', function () {
      marquees.forEach(fillMarquee);
    });

    if (work && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        work.classList.toggle('is-offscreen', !entries[0].isIntersecting);
      }).observe(work);
    }

    var toggle = $('[data-marquee-toggle]');
    if (toggle && work) {
      toggle.addEventListener('click', function () {
        var paused = work.classList.toggle('is-paused');
        toggle.setAttribute('aria-pressed', paused ? 'true' : 'false');
        toggle.querySelector('[data-label]').textContent = paused ? 'Play' : 'Pause';
      });
    }
  }

  /* ------------------------------------------------------------------
     Lightbox
     ------------------------------------------------------------------ */
  var box = $('[data-lightbox]');
  if (box && cards.length && typeof box.showModal === 'function') {
    var boxImg = $('.lightbox__img', box);
    var boxTitle = $('[data-lightbox-title]', box);
    var boxTag = $('[data-lightbox-tag]', box);
    var boxCount = $('[data-lightbox-count]', box);
    var current = 0;

    var show = function (index) {
      current = (index + cards.length) % cards.length;
      var card = cards[current];
      var img = $('img', card);
      var caps = $$('.work-card__cap span', card);
      boxImg.src = img.currentSrc || img.src;
      boxImg.alt = img.alt;
      boxTitle.textContent = caps[0] ? caps[0].textContent : '';
      boxTag.textContent = caps[1] ? caps[1].textContent : '';
      boxCount.textContent = String(current + 1).padStart(2, '0') + ' / ' + String(cards.length).padStart(2, '0');
    };

    doc.addEventListener('click', function (e) {
      var btn = e.target.closest('.work-card__btn');
      if (!btn) return;
      var card = btn.closest('.work-card');
      show(parseInt(card.getAttribute('data-index'), 10) || 0);
      box.showModal();
    });

    $('[data-lightbox-prev]', box).addEventListener('click', function () { show(current - 1); });
    $('[data-lightbox-next]', box).addEventListener('click', function () { show(current + 1); });
    $('[data-lightbox-close]', box).addEventListener('click', function () { box.close(); });
    box.addEventListener('click', function (e) { if (e.target === box) box.close(); });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(current - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); show(current + 1); }
    });
  }

  /* ------------------------------------------------------------------
     Enquiry form. There is no server: the form writes your message into
     a WhatsApp chat or an email, ready for you to press send.
     ------------------------------------------------------------------ */
  $$('[data-enquiry-form]').forEach(function (form) {
    var number = (form.getAttribute('data-whatsapp') || '').replace(/\D/g, '');
    var email = form.getAttribute('data-email') || '';
    var brand = form.getAttribute('data-brand') || '';
    var division = form.getAttribute('data-division') || '';
    var waLink = $('[data-send="whatsapp"]', form);
    var mailLink = $('[data-send="email"]', form);
    var status = $('[data-enquiry-status]', form);
    var fields = ['name', 'contact', 'type', 'message'].map(function (n) { return form.elements[n]; });

    function value(n) { return (form.elements[n] && form.elements[n].value || '').trim(); }

    function compose() {
      var name = value('name');
      var lines = [
        'Hi ' + brand + (name ? ', this is ' + name + '.' : '.'),
        'Enquiry: ' + value('type') + ' (' + division + ')',
        '',
        value('message') || '(details to follow)'
      ];
      if (value('contact')) lines.push('', 'You can reach me at: ' + value('contact'));
      var text = lines.join('\n');
      if (waLink) waLink.href = 'https://wa.me/' + number + '?text=' + encodeURIComponent(text);
      if (mailLink) {
        mailLink.href = 'mailto:' + email + '?subject=' +
          encodeURIComponent(division + ' enquiry: ' + value('type')) + '&body=' + encodeURIComponent(text);
      }
    }

    function setError(field, message) {
      var err = doc.getElementById(field.id + '-error');
      field.setAttribute('aria-invalid', message ? 'true' : 'false');
      if (err) err.textContent = message;
    }

    function validate() {
      var first = null;
      fields.forEach(function (field) {
        if (!field || !field.required) return;
        var empty = !field.value.trim();
        setError(field, empty ? field.getAttribute('data-error') || 'Please fill this in.' : '');
        if (empty && !first) first = field;
      });
      return first;
    }

    form.addEventListener('input', function (e) {
      if (e.target.getAttribute('aria-invalid') === 'true' && e.target.value.trim()) setError(e.target, '');
      compose();
    });
    form.addEventListener('change', compose);
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    compose();

    [waLink, mailLink].forEach(function (link) {
      if (!link) return;
      link.addEventListener('click', function (e) {
        var bad = validate();
        if (bad) {
          e.preventDefault();
          if (status) status.textContent = 'Add the missing details above, then try again.';
          bad.focus();
          return;
        }
        compose();
        if (status) {
          status.textContent = link === waLink
            ? 'WhatsApp opens with your message filled in. Press send there to reach us.'
            : 'Your email app opens with your message filled in. Press send there to reach us.';
        }
      });
    });
  });

  // Buttons elsewhere that start an enquiry of a given type.
  $$('[data-enquiry]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var form = $('[data-enquiry-form]');
      if (!form || !form.elements.type) return;
      form.elements.type.value = btn.getAttribute('data-enquiry');
      form.elements.type.dispatchEvent(new Event('change', { bubbles: true }));
      window.setTimeout(function () {
        if (form.elements.name) form.elements.name.focus({ preventScroll: true });
      }, reduceMotion.matches ? 0 : 650);
    });
  });

  $$('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });
})();
