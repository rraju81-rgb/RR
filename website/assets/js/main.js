/* Carbon6 Studio — site scripts. No dependencies. */
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
  var WIPE_LOGO = { carbon: 'assets/img/carbon6-mark.svg', print: 'assets/img/pixl-logo-160.webp' };
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
    mark.className = 'wipe__logo';
    mark.src = WIPE_LOGO[kind];
    mark.alt = '';
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
     3D printer. Each model is described by its cross-section at every
     height. The printer lays it down one layer at a time, the nozzle
     tracing each layer's outline, and starts the next model when done.
     ------------------------------------------------------------------ */
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var TAU = Math.PI * 2;

  function ringPts(n, radius) {
    var pts = [];
    for (var i = 0; i < n; i++) {
      var a = i / n * TAU;
      var r = typeof radius === 'function' ? radius(a) : radius;
      pts.push([Math.cos(a) * r, Math.sin(a) * r]);
    }
    return pts;
  }
  function scalePts(pts, k) { return pts.map(function (p) { return [p[0] * k, p[1] * k]; }); }
  function rectPts(x0, x1, y0, y1) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; }
  function sectorPts(r0, r1, a0, a1, n) {
    var pts = [], i, a;
    for (i = 0; i <= n; i++) { a = a0 + (a1 - a0) * i / n; pts.push([Math.cos(a) * r1, Math.sin(a) * r1]); }
    for (i = n; i >= 0; i--) { a = a0 + (a1 - a0) * i / n; pts.push([Math.cos(a) * r0, Math.sin(a) * r0]); }
    return pts;
  }
  function gearPts(n, ro, rr, rot) {
    var pts = [], pitch = TAU / n;
    for (var i = 0; i < n; i++) {
      [[0, rr], [0.16, ro], [0.5, ro], [0.66, rr]].forEach(function (q) {
        var a = rot + (i + q[0]) * pitch;
        pts.push([Math.cos(a) * q[1], Math.sin(a) * q[1]]);
      });
    }
    return pts;
  }
  // Hollow models keep a solid floor, then print as a thin wall.
  function wall(outer, k) { return k < 2 ? [outer] : [outer, scalePts(outer, 0.86)]; }

  var PRINT_MODELS = [
    {
      name: 'Spiral vase', color: '#ff6b2c', layers: 44, height: 236, evenodd: true,
      slice: function (t, k) {
        var r = 46 + 40 * Math.sin(Math.PI * Math.min(t / 0.74, 1)) + 20 * Math.pow(Math.max(0, (t - 0.8) / 0.2), 2);
        return wall(ringPts(56, function (a) { return r + 2.6 * Math.sin(a * 8 + t * 9); }), k);
      }
    },
    {
      name: 'Helical gear', color: '#17a398', layers: 26, height: 116, evenodd: true,
      slice: function (t) {
        var bore = ringPts(28, 20);
        if (t > 0.72) return [ringPts(40, 42), bore];
        return [gearPts(14, 102, 86, t * 0.3), bore];
      }
    },
    {
      name: 'pi.XL sign', color: '#f2b632', layers: 34, height: 190,
      slice: function (t) {
        var d = 18;
        if (t >= 0.72) return [rectPts(-98, 98, -d, d)];
        var k = 1 - t / 0.72;
        var curl = 26 * k * k;
        return [rectPts(-66, -38, -d, d), rectPts(30 + curl, 58 + curl, -d, d)];
      }
    },
    {
      name: 'Twisted vase', color: '#7c5cff', layers: 44, height: 230, evenodd: true,
      slice: function (t, k) {
        var r = 50 + 24 * Math.sin(Math.PI * t) + 10 * t;
        var twist = t * Math.PI / 2.4;
        return wall(ringPts(72, function (a) { return r * (1 + 0.16 * Math.cos(6 * (a - twist))); }), k);
      }
    },
    {
      name: 'Chess rook', color: '#eef0f3', layers: 42, height: 226, evenodd: true,
      slice: function (t) {
        var r;
        if (t < 0.08) r = 70;
        else if (t < 0.14) r = 60;
        else if (t < 0.66) r = 52 - 10 * (t - 0.14) / 0.52;
        else r = 58;
        if (t < 0.74) return [ringPts(48, r)];
        if (t < 0.86) return [ringPts(48, 58), ringPts(40, 40)];
        var merlons = [];
        for (var i = 0; i < 4; i++) merlons.push(sectorPts(40, 58, i * TAU / 4 + 0.24, (i + 1) * TAU / 4 - 0.24, 10));
        return merlons;
      }
    },
    {
      name: 'PITLANE podium', color: '#9aa3ad', layers: 40, height: 220,
      slice: function (t) {
        var lean = -t * 66;
        if (t > 0.94) return [rectPts(-76, 76, lean - 10, lean + 10)];
        var parts = [rectPts(-76, -60, lean - 10, lean + 10), rectPts(60, 76, lean - 10, lean + 10)];
        [0.14, 0.36, 0.58, 0.8].forEach(function (s) {
          if (t > s && t < s + 0.065) parts.push(rectPts(-76, 76, lean - 8, lean + 24));
        });
        return parts;
      }
    }
  ];

  function shade(hex, k) {
    var n = parseInt(hex.slice(1), 16);
    var c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (v) {
      return Math.round(k <= 1 ? v * k : v + (255 - v) * (k - 1));
    });
    return '#' + c.map(function (v) { return ('0' + Math.min(255, Math.max(0, v)).toString(16)).slice(-2); }).join('');
  }

  function svgEl(name, attrs, parent) {
    var node = doc.createElementNS(SVG_NS, name);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  var buildCount = 0;

  function initPrintBuild(svg) {
    var id = 'pb' + (++buildCount);
    var LAYER_MS = parseInt(svg.getAttribute('data-layer-ms'), 10) || 180;
    var CX = 200, BED_Y = 404, RY = 0.3;
    var scope = svg.closest('[data-printer]') || svg.parentNode;
    var hudLayer = $('[data-hud-layer]', scope);
    var hudTotal = $('[data-hud-total]', scope);
    var hudModel = $('[data-hud-model]', scope);
    var modelIndex = (parseInt(svg.getAttribute('data-start'), 10) || 0) % PRINT_MODELS.length;

    var withCaption = svg.hasAttribute('data-caption');
    svg.setAttribute('viewBox', withCaption ? '0 -40 400 560' : '0 -40 400 520');
    svg.innerHTML = '';

    var defs = svgEl('defs', {}, svg);
    var glow = svgEl('radialGradient', { id: id + 'g' }, defs);
    svgEl('stop', { offset: '0', 'stop-color': '#ffd0a8', 'stop-opacity': '.95' }, glow);
    svgEl('stop', { offset: '1', 'stop-color': '#ff6b2c', 'stop-opacity': '0' }, glow);
    var feed = svgEl('linearGradient', { id: id + 'f', gradientUnits: 'userSpaceOnUse', x1: 0, y1: -150, x2: 0, y2: -330 }, defs);
    var feedStart = svgEl('stop', { offset: '0', 'stop-color': '#ff6b2c' }, feed);
    var feedEnd = svgEl('stop', { offset: '1', 'stop-color': '#ff6b2c', 'stop-opacity': '0' }, feed);
    var dots = svgEl('pattern', { id: id + 'd', width: 9, height: 9, patternUnits: 'userSpaceOnUse' }, defs);
    svgEl('circle', { cx: 4.5, cy: 4.5, r: 0.9, fill: '#3d444d' }, dots);
    var wallGrad = svgEl('linearGradient', { id: id + 'w', x1: 0, x2: 1, y1: 0, y2: 0 }, defs);

    // Build plate: textured black sheet on a steel bed.
    var bedRx = 176, bedRy = bedRx * RY;
    svgEl('ellipse', { cx: CX, cy: BED_Y + 12, rx: bedRx, ry: bedRy, fill: '#16191c' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 2, rx: bedRx, ry: bedRy, fill: '#2b3036' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 2, rx: bedRx, ry: bedRy, fill: 'url(#' + id + 'd)', opacity: '.8' }, svg);
    svgEl('ellipse', { cx: CX, cy: BED_Y + 2, rx: bedRx - 1, ry: bedRy - 1, fill: 'none', stroke: '#4a525b', 'stroke-width': 1.5 }, svg);

    var object = svgEl('g', {}, svg);
    var hot = svgEl('path', {
      fill: 'none', stroke: '#ffd18a', 'stroke-width': 2.4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'
    }, svg);

    // X gantry + print head. The head group's origin is the nozzle tip.
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

    if (withCaption && !hudModel) {
      var caption = svgEl('text', { x: CX, y: 502, 'text-anchor': 'middle', class: 'pb-caption' }, svg);
      caption.appendChild(doc.createTextNode('Now printing · '));
      hudModel = svgEl('tspan', { class: 'pb-model' }, caption);
    }

    var model, layers = [], hx = CX, hy = BED_Y;

    function setHead(x, y) {
      hx = x; hy = y;
      head.setAttribute('transform', 'translate(' + x.toFixed(2) + ' ' + y.toFixed(2) + ')');
      gantry.setAttribute('transform', 'translate(0 ' + y.toFixed(2) + ')');
    }

    function project(contours, yTop) {
      return contours.map(function (pts) {
        return 'M' + pts.map(function (p) {
          return (CX + p[0]).toFixed(1) + ' ' + (yTop + p[1] * RY).toFixed(1);
        }).join('L') + 'Z';
      }).join('');
    }

    function loadModel(m) {
      model = m;
      object.innerHTML = '';
      object.style.opacity = 1;
      layers = [];
      while (wallGrad.firstChild) wallGrad.removeChild(wallGrad.firstChild);
      [[0, 0.5], [0.18, 0.85], [0.38, 1.22], [0.56, 1], [0.86, 0.72], [1, 0.48]].forEach(function (s) {
        svgEl('stop', { offset: s[0], 'stop-color': shade(m.color, s[1]) }, wallGrad);
      });
      feedStart.setAttribute('stop-color', m.color);
      feedEnd.setAttribute('stop-color', m.color);
      var step = m.height / m.layers;
      var rule = m.evenodd ? 'evenodd' : 'nonzero';
      var line = shade(m.color, 0.55);
      var top = shade(m.color, 1.14);
      for (var k = 0; k < m.layers; k++) {
        var contours = m.slice((k + 0.5) / m.layers, k);
        var yTop = BED_Y - (k + 1) * step;
        // The wall is the layer's outline one step lower; the next layer
        // covers all of it except the band that faces the viewer.
        var wallEl = svgEl('path', {
          d: project(contours, yTop + step), fill: 'url(#' + id + 'w)', 'fill-rule': rule,
          stroke: line, 'stroke-width': 0.9, 'stroke-opacity': 0.6
        }, object);
        var capD = project(contours, yTop);
        var capEl = svgEl('path', { d: capD, fill: top, 'fill-rule': rule, stroke: line, 'stroke-width': 0.6, 'stroke-opacity': 0.5 }, object);
        wallEl.style.display = capEl.style.display = 'none';
        layers.push({ wall: wallEl, cap: capEl, d: capD, top: yTop });
      }
      if (hudModel) hudModel.textContent = m.name;
      if (hudTotal) hudTotal.textContent = String(m.layers).padStart(3, '0');
      setHud(0);
    }

    function setHud(n) { if (hudLayer) hudLayer.textContent = String(n).padStart(3, '0'); }

    var phase = 'build', progress = 0, shown = 0, current = -1, hotLen = 0;
    var phaseStart = 0, last = 0, running = false, visible = true, from = null, parkTo = null;

    function showUpTo(n) {
      while (shown < n) {
        layers[shown].wall.style.display = '';
        layers[shown].cap.style.display = '';
        shown++;
      }
    }

    function startPoint() {
      hot.setAttribute('d', layers[0].d);
      var p = hot.getPointAtLength(0);
      hot.setAttribute('d', '');
      return [p.x, p.y];
    }

    function renderBuild(p) {
      var k = Math.min(Math.floor(p), model.layers - 1);
      showUpTo(k);
      if (k !== current) {
        current = k;
        hot.setAttribute('d', layers[k].d);
        hotLen = hot.getTotalLength();
        hot.style.strokeDasharray = hotLen + ' ' + hotLen;
      }
      var frac = Math.min(p - k, 1);
      hot.style.strokeDashoffset = hotLen * (1 - frac);
      var pt = hot.getPointAtLength(hotLen * frac);
      setHead(pt.x, pt.y);
      setHud(k + 1);
    }

    function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

    function frame(now) {
      if (!running) return;
      var dt = last ? Math.min(now - last, 64) : 16;
      last = now;

      if (phase === 'build') {
        progress += dt / LAYER_MS;
        if (progress >= model.layers) {
          showUpTo(model.layers);
          hot.setAttribute('d', '');
          current = -1;
          setHud(model.layers);
          phase = 'park';
          phaseStart = now;
          from = [hx, hy];
          parkTo = [CX + 140, Math.max(96, layers[model.layers - 1].top - 48)];
        } else {
          renderBuild(progress);
        }
      } else if (phase === 'park') {
        var e = ease(Math.min((now - phaseStart) / 1100, 1));
        setHead(from[0] + (parkTo[0] - from[0]) * e, from[1] + (parkTo[1] - from[1]) * e);
        glowDot.style.opacity = 1 - e;
        if (now - phaseStart > 3200) { phase = 'clear'; phaseStart = now; }
      } else if (phase === 'clear') {
        var c = Math.min((now - phaseStart) / 1000, 1);
        object.style.opacity = 1 - c;
        if (c >= 1) {
          modelIndex = (modelIndex + 1) % PRINT_MODELS.length;
          loadModel(PRINT_MODELS[modelIndex]);
          shown = 0;
          progress = 0;
          phase = 'travel';
          phaseStart = now;
          from = [hx, hy];
          parkTo = startPoint();
        }
      } else if (phase === 'travel') {
        var tr = ease(Math.min((now - phaseStart) / 900, 1));
        setHead(from[0] + (parkTo[0] - from[0]) * tr, from[1] + (parkTo[1] - from[1]) * tr);
        glowDot.style.opacity = tr;
        if (tr >= 1) phase = 'build';
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

    loadModel(PRINT_MODELS[modelIndex]);

    if (reduceMotion.matches) {
      // Show a finished print with the nozzle parked.
      showUpTo(model.layers);
      setHud(model.layers);
      setHead(CX + 140, Math.max(96, layers[model.layers - 1].top - 48));
      glowDot.style.opacity = 0;
      return;
    }

    var sp = startPoint();
    setHead(sp[0], sp[1]);

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
    if (reduceMotion.addEventListener) {
      reduceMotion.addEventListener('change', function () { marquees.forEach(fillMarquee); });
    }

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
    var boxCta = $('[data-lightbox-cta]', box);
    var current = 0;

    var show = function (index) {
      current = (index + cards.length) % cards.length;
      var card = cards[current];
      var img = $('img', card);
      var caps = $$('.work-card__cap span', card);
      boxImg.src = img.currentSrc || img.src;
      boxImg.alt = img.alt;
      boxImg.width = img.width;
      boxImg.height = img.height;
      box.style.setProperty('--lb-ar', img.getAttribute('width') + ' / ' + img.getAttribute('height'));
      boxTitle.textContent = caps[0] ? caps[0].textContent : '';
      boxTag.textContent = caps[1] ? caps[1].textContent : '';
      boxCount.textContent = String(current + 1).padStart(2, '0') + ' / ' + String(cards.length).padStart(2, '0');
      if (boxCta) {
        var product = card.getAttribute('data-item-product');
        boxCta.hidden = !product;
        boxCta.setAttribute('data-product', product || '');
        boxCta.setAttribute('data-type', card.getAttribute('data-item-type') || '');
        boxCta.textContent = card.getAttribute('data-item-cta') || 'Ask about this';
      }
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
     Enquiry form. There is no server: the form writes the visitor's
     message into WhatsApp, addressed to the business they picked.
     Each option carries its own WhatsApp number and business name.
     ------------------------------------------------------------------ */
  $$('[data-enquiry-form]').forEach(function (form) {
    var waLink = $('[data-send="whatsapp"]', form);
    var status = $('[data-enquiry-status]', form);
    var fields = ['name', 'contact', 'message'].map(function (n) { return form.elements[n]; });

    function value(n) { return (form.elements[n] && form.elements[n].value || '').trim(); }

    function selected() {
      var sel = form.elements.type;
      var opt = sel && sel.options[sel.selectedIndex];
      return {
        label: opt ? opt.value : '',
        number: (opt && opt.getAttribute('data-whatsapp') || '').replace(/\D/g, ''),
        brand: opt && opt.getAttribute('data-brand') || '',
        picker: opt && opt.getAttribute('data-picker') || ''
      };
    }

    // Show the product choices of the business picked above, and only those.
    function syncPicker() {
      var set = selected().picker;
      $$('[data-picker-set]', form).forEach(function (group) {
        var on = group.getAttribute('data-picker-set') === set;
        group.hidden = !on;
        $$('input', group).forEach(function (input) {
          input.disabled = !on;
          if (!on) input.checked = false;
        });
      });
    }

    function product() {
      var chosen = $('input[name="product"]:checked:not(:disabled)', form);
      return chosen ? chosen.value : '';
    }

    function compose() {
      var to = selected();
      var name = value('name');
      var lines = [
        'Hi ' + to.brand + (name ? ', this is ' + name + '.' : '.'),
        "I'm looking for: " + to.label
      ];
      if (product()) lines.push("I'm interested in: " + product());
      lines.push('', value('message') || '(details to follow)');
      if (value('contact')) lines.push('', 'You can reach me at: ' + value('contact'));
      if (waLink) waLink.href = 'https://wa.me/' + to.number + '?text=' + encodeURIComponent(lines.join('\n'));
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
    form.addEventListener('change', function (e) {
      if (e.target === form.elements.type) syncPicker();
      compose();
    });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    form.pickProduct = function (type, value) {
      if (type && form.elements.type) form.elements.type.value = type;
      syncPicker();
      $$('input[name="product"]', form).forEach(function (input) {
        if (!input.disabled && input.value === value) input.checked = true;
      });
      compose();
    };
    syncPicker();
    compose();

    if (waLink) {
      waLink.addEventListener('click', function (e) {
        var bad = validate();
        if (bad) {
          e.preventDefault();
          if (status) status.textContent = 'Add the missing details above, then try again.';
          bad.focus();
          return;
        }
        compose();
        if (status) status.textContent = 'WhatsApp opens with your message filled in. Press send there to reach us.';
      });
    }
  });

  // Buttons that start an enquiry about one product: pick the business and
  // the product in the contact form, then move there.
  doc.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-product]');
    if (!btn || !btn.getAttribute('data-product')) return;
    var form = $('[data-enquiry-form]');
    if (!form || !form.pickProduct) return;
    var dialog = btn.closest('dialog');
    if (dialog && dialog.open) dialog.close();
    form.pickProduct(btn.getAttribute('data-type'), btn.getAttribute('data-product'));
    window.setTimeout(function () {
      if (form.elements.name) form.elements.name.focus({ preventScroll: true });
    }, reduceMotion.matches ? 0 : 650);
  });

  $$('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });
})();
