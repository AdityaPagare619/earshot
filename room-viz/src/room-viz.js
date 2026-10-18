/* EARSHOT room-viz — LEFT pane module (no build step, classic script).
 * Exposes window.RoomViz. Bus-agnostic: pass any EventTarget-like, or call
 * handleEvent() directly. Mock bus until simulator-shell merges: see demo/mock-bus.js.
 *
 * Contract (frozen):
 *   new RoomViz({ el, bus })
 *   bus events (CustomEvent detail):
 *     earshot:presence    { person, room|null, confidence }   room in kitchen|living|bedroom|hall
 *     earshot:disclosure  { room, level, itemId?, reasons?[] } level in FULL|ABSTRACT|EXISTENCE|SILENT
 *     earshot:wakeword     { ts }  -> fresh presence re-sample pulse (P0-1)
 *   RoomViz#handleEvent({type, detail}) mirrors the bus for direct calls.
 */
(function (global) {
  'use strict';

  var NS = 'http://www.w3.org/2000/svg';
  var LEVELS = ['FULL', 'ABSTRACT', 'EXISTENCE', 'SILENT'];
  var TOKEN_VAR = {
    FULL: '--esh-level-full',
    ABSTRACT: '--esh-level-abstract',
    EXISTENCE: '--esh-level-existence',
    SILENT: '--esh-level-silent',
    UNKNOWN: '--esh-level-unknown'
  };

  var ROOMS = {
    kitchen: { label: 'KITCHEN', x: 40,  y: 30,  w: 260, h: 210 },
    living:  { label: 'LIVING',  x: 300, y: 30,  w: 300, h: 210 },
    bedroom: { label: 'BEDROOM', x: 300, y: 240, w: 300, h: 210 },
    hall:    { label: 'HALL',    x: 40,  y: 240, w: 260, h: 210 }
  };
  // Resting spots + waypoint paths from the front door to each room.
  var DOOR = { x: 95, y: 438 };
  var PATHS = {
    kitchen: [[95, 438], [95, 330], [180, 330], [180, 246], [180, 180]],
    living:  [[95, 438], [95, 330], [270, 330], [300, 330], [380, 200]],
    bedroom: [[95, 438], [95, 330], [270, 380], [300, 380], [430, 350]],
    hall:    [[95, 438], [95, 330]]
  };
  var SPOTS = {
    kitchen: { x: 215, y: 140 },
    living:  { x: 430, y: 150 },
    bedroom: { x: 450, y: 330 },
    hall:    { x: 150, y: 340 }
  };
  // per-person resting spots so avatars never stack (kitchen is the walk-in stage)
  var SPOT_FOR = {
    'Priya|kitchen': [100, 168],
    'MIL|kitchen':   [238, 128],
    'Arjun|living':  [430, 150]
  };
  function spotFor(person, room) {
    var k = person + '|' + room;
    if (SPOT_FOR[k]) return { x: SPOT_FOR[k][0], y: SPOT_FOR[k][1] };
    return SPOTS[room];
  }
  var PEOPLE = {
    Priya: { initial: 'P', hue: '#7dd7ff' },
    Arjun: { initial: 'A', hue: '#9d8bff' },
    MIL:   { initial: 'M', hue: '#ffb03a' }
  };
  // Echo Show sits on the kitchen counter.
  var ECHO = { x: 115, y: 100 };

  function el(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function easeOutExpo(t) { return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t); }
  function easeInOut(t) { return t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  function RoomViz(opts) {
    if (!opts || !opts.el) throw new Error('RoomViz needs {el}');
    this.root = opts.el;
    this.root.classList.add('esh-roomviz');
    this.people = {};   // name -> {room, confidence, g, x, y, queue, raf}
    this.levels = {};   // room -> level
    this._build();
    if (opts.bus && opts.bus.addEventListener) {
      var self = this;
      ['earshot:presence', 'earshot:disclosure', 'earshot:wakeword'].forEach(function (t) {
        opts.bus.addEventListener(t, function (ev) { self.handleEvent({ type: t, detail: ev.detail || {} }); });
      });
    }
  }

  RoomViz.prototype._build = function () {
    var svg = el('svg', { viewBox: '0 0 640 480', class: 'esh-svg', role: 'img',
      'aria-label': 'Live floor plan of the Priya household' }, this.root);
    this.svg = svg;
    var defs = el('defs', {}, svg);
    var vg = el('radialGradient', { id: 'esh-vig', cx: '50%', cy: '42%', r: '75%' }, defs);
    el('stop', { offset: '0%', 'stop-color': '#0a1220', 'stop-opacity': '.9' }, vg);
    el('stop', { offset: '100%', 'stop-color': '#05070a', 'stop-opacity': '0' }, vg);
    el('rect', { x: 0, y: 0, width: 640, height: 480, fill: 'url(#esh-vig)' }, svg);

    // faint grid
    var grid = el('g', { class: 'esh-grid' }, svg);
    for (var gx = 40; gx <= 600; gx += 28)
      el('line', { x1: gx, y1: 30, x2: gx, y2: 450 }, grid);
    for (var gy = 30; gy <= 450; gy += 28)
      el('line', { x1: 40, y1: gy, x2: 600, y2: gy }, grid);

    this.roomLayer = el('g', {}, svg);
    this.borderLayer = el('g', {}, svg);
    this.fxLayer = el('g', {}, svg);      // ripples, pulses, trails
    this.avatarLayer = el('g', {}, svg);

    var self = this;
    Object.keys(ROOMS).forEach(function (key) {
      var r = ROOMS[key];
      var g = el('g', { class: 'esh-room', 'data-room': key }, self.roomLayer);
      el('rect', { x: r.x, y: r.y, width: r.w, height: r.h, rx: 8, class: 'esh-room-fill' }, g);
      el('text', { x: r.x + 14, y: r.y + 26, class: 'esh-room-label' }, g)
        .textContent = r.label;
      // level chip
      var chip = el('g', { class: 'esh-chip', transform: 'translate(' + (r.x + r.w - 118) + ',' + (r.y + 12) + ')' }, g);
      el('rect', { width: 106, height: 24, rx: 12, class: 'esh-chip-bg' }, chip);
      var t = el('text', { x: 53, y: 16.5, class: 'esh-chip-text', 'text-anchor': 'middle' }, chip);
      t.textContent = '—';
      // glowing disclosure border (crisp + bloom copies)
      var bb = el('g', { class: 'esh-border', 'data-level': 'UNKNOWN' }, self.borderLayer);
      el('rect', { x: r.x, y: r.y, width: r.w, height: r.h, rx: 8, class: 'esh-border-bloom' }, bb);
      el('rect', { x: r.x, y: r.y, width: r.w, height: r.h, rx: 8, class: 'esh-border-line' }, bb);
      self.levels[key] = 'UNKNOWN';
      self['_chip_' + key] = t;
      self['_border_' + key] = bb;
    });

    // doorways: cut gaps into the room fills + draw door markers
    this._doorway(150, 240, 210, 240, 'kitchen');   // hall -> kitchen threshold
    this._doorway(300, 300, 300, 360, 'hall');      // hall -> living
    this._doorway(300, 350, 300, 410, 'hall');      // hall -> bedroom
    // front door notch
    var fd = el('g', { class: 'esh-door' }, this.roomLayer);
    el('rect', { x: 60, y: 442, width: 70, height: 8, rx: 2, class: 'esh-door-notch' }, fd);
    var fdt = el('text', { x: 95, y: 472, class: 'esh-room-label esh-door-label', 'text-anchor': 'middle' }, fd);
    fdt.textContent = 'FRONT DOOR';

    // Echo Show on the kitchen counter
    var echo = el('g', { class: 'esh-echo', transform: 'translate(' + ECHO.x + ',' + ECHO.y + ')' }, this.roomLayer);
    el('rect', { x: -30, y: -22, width: 60, height: 44, rx: 9, class: 'esh-echo-body' }, echo);
    el('rect', { x: -24, y: -16, width: 48, height: 32, rx: 5, class: 'esh-echo-screen' }, echo);
    this.echoBars = el('g', { class: 'esh-echo-bars' }, echo);
    for (var i = 0; i < 5; i++)
      el('rect', { x: -16 + i * 8, y: -4, width: 4, height: 8, rx: 2, class: 'esh-echo-bar' }, this.echoBars);
    var et = el('text', { x: 0, y: 40, class: 'esh-room-label', 'text-anchor': 'middle' }, echo);
    et.textContent = 'ECHO SHOW';
  };

  RoomViz.prototype._doorway = function (x1, y1, x2, y2) {
    // paint a bg-colored gap over the wall line + threshold glow line
    var g = el('g', { class: 'esh-doorway' }, this.roomLayer);
    el('line', { x1: x1, y1: y1, x2: x2, y2: y2, class: 'esh-doorway-gap' }, g);
    el('line', { x1: x1, y1: y1, x2: x2, y2: y2, class: 'esh-doorway-line' }, g);
  };

  RoomViz.prototype._person = function (name) {
    var p = this.people[name];
    if (p) return p;
    var meta = PEOPLE[name] || { initial: name[0] || '?', hue: '#7dd7ff' };
    var g = el('g', { class: 'esh-avatar', opacity: 0 }, this.avatarLayer);
    el('circle', { r: 22, class: 'esh-avatar-glow', fill: meta.hue }, g);
    el('circle', { r: 16, class: 'esh-avatar-disc' }, g);
    el('circle', { r: 20.5, class: 'esh-avatar-ring' }, g);
    var t = el('text', { y: 6.5, class: 'esh-avatar-initial', 'text-anchor': 'middle' }, g);
    t.textContent = meta.initial;
    var nt = el('text', { y: 40, class: 'esh-avatar-name', 'text-anchor': 'middle' }, g);
    nt.textContent = name;
    p = this.people[name] = { name: name, hue: meta.hue, g: g, x: DOOR.x, y: DOOR.y,
      room: null, confidence: 1, moving: false };
    return p;
  };

  RoomViz.prototype.handleEvent = function (e) {
    var d = e.detail || {};
    if (e.type === 'earshot:presence') this.setPresence(d.person, d.room, d.confidence);
    else if (e.type === 'earshot:disclosure') this.setDisclosure(d.room, d.level, d.reasons);
    else if (e.type === 'earshot:wakeword') this.wakewordPulse(d);
  };

  RoomViz.prototype.setPresence = function (name, room, confidence) {
    if (!name) return;
    var p = this._person(name);
    confidence = (confidence == null) ? 1 : confidence;
    p.confidence = confidence;
    var ring = p.g.querySelector('.esh-avatar-ring');
    ring.classList.toggle('esh-lowconf', confidence < 0.6);
    if (room && !ROOMS[room]) return;
    if (p.room === room && !p.moving) { this._show(p); return; }
    var wasOutside = !p.room, goingOutside = !room;
    p.room = room || null;
    var pts = goingOutside
      ? [ [p.x, p.y], [DOOR.x, DOOR.y] ]
      : PATHS[room].concat([ (function(){ var s = spotFor(name, room); return [s.x, s.y]; })() ]);
    if (wasOutside) { p.x = DOOR.x; p.y = DOOR.y; }
    this._show(p);
    this._glide(p, pts, goingOutside);
  };

  RoomViz.prototype._show = function (p) {
    p.g.setAttribute('opacity', 1);
    p.g.style.opacity = 1;
  };

  RoomViz.prototype._glide = function (p, pts, exiting) {
    var self = this;
    if (p.raf) cancelAnimationFrame(p.raf);
    p.moving = true;
    // build segment list from current pos through waypoints; constant speed
    var path = [[p.x, p.y]].concat(pts.slice(1));
    var seg = 0, t0 = null, SPEED = 300; // px per second
    function segMs(a, b) {
      var d = Math.hypot(b[0] - a[0], b[1] - a[1]);
      return Math.max(120, d / SPEED * 1000);
    }
    var cur = segMs(path[0], path[1]);
    var lastTrail = 0;
    function frame(ts) {
      if (t0 == null) t0 = ts;
      var t = Math.min(1, (ts - t0) / cur);
      var e = easeInOut(t);
      var a = path[seg], b = path[seg + 1];
      p.x = a[0] + (b[0] - a[0]) * e;
      p.y = a[1] + (b[1] - a[1]) * e;
      p.g.setAttribute('transform', 'translate(' + p.x + ',' + p.y + ')' +
        (exiting && t > .6 ? ' scale(' + (1 - (t - .6) / .4 * .55) + ')' : ''));
      if (ts - lastTrail > 70) { lastTrail = ts; self._trail(p); }
      // threshold ripple when crossing the kitchen doorway line y=240 near x 150..210
      if (!p._rippled && b[1] <= 240 && a[1] > 240 && b[0] > 140 && b[0] < 220 && !exiting) {
        p._rippled = true;
        self._ripple(180, 240, p.hue);
      }
      if (t >= 1) {
        seg++; t0 = null;
        if (seg >= path.length - 1) {
          p.moving = false; p._rippled = false; p.raf = null;
          if (exiting) { p.g.style.opacity = 0; }
          return;
        }
        cur = segMs(path[seg], path[seg + 1]);
      }
      p.raf = requestAnimationFrame(frame);
    }
    p.raf = requestAnimationFrame(frame);
  };

  RoomViz.prototype._trail = function (p) {
    var c = el('circle', { cx: p.x, cy: p.y, r: 10, class: 'esh-trail', fill: p.hue }, this.fxLayer);
    setTimeout(function () { c.classList.add('esh-trail-fade'); }, 30);
    setTimeout(function () { c.remove(); }, 650);
  };

  RoomViz.prototype._ripple = function (x, y, color) {
    var c = el('circle', { cx: x, cy: y, r: 6, class: 'esh-ripple', stroke: color }, this.fxLayer);
    // force reflow so the CSS transition runs
    void c.getBoundingClientRect();
    c.classList.add('esh-ripple-go');
    setTimeout(function () { c.remove(); }, 900);
  };

  RoomViz.prototype.setDisclosure = function (room, level, reasons) {
    if (!ROOMS[room] || LEVELS.indexOf(level) < 0) return;
    this.levels[room] = level;
    var bb = this['_border_' + room];
    bb.setAttribute('data-level', level);
    bb.style.setProperty('--esh-active', 'var(' + TOKEN_VAR[level] + ')');
    var chip = this['_chip_' + room];
    chip.textContent = level;
    chip.parentNode.setAttribute('data-level', level);
    chip.parentNode.style.setProperty('--esh-active', 'var(' + TOKEN_VAR[level] + ')');
  };

  RoomViz.prototype.wakewordPulse = function () {
    // P0-1: wake-word triggers a fresh presence re-sample — violet pulse from the Echo.
    var self = this;
    [0, 140, 280].forEach(function (delay, i) {
      setTimeout(function () {
        var c = el('circle', { cx: ECHO.x, cy: ECHO.y, r: 10 + i * 4,
          class: 'esh-wake', stroke: 'var(--esh-level-unknown)' }, self.fxLayer);
        void c.getBoundingClientRect();
        c.classList.add('esh-wake-go');
        setTimeout(function () { c.remove(); }, 1100);
      }, delay);
    });
    this.echoBars.classList.add('esh-echo-live');
    setTimeout(function () { self.echoBars.classList.remove('esh-echo-live'); }, 1600);
    // kitchen border briefly shows the fail-closed re-sample state, then resolves
    var bb = this._border_kitchen;
    var prev = bb.getAttribute('data-level');
    bb.setAttribute('data-level', 'UNKNOWN');
    bb.style.setProperty('--esh-active', 'var(--esh-level-unknown)');
    setTimeout(function () {
      bb.setAttribute('data-level', prev);
      bb.style.setProperty('--esh-active', 'var(' + TOKEN_VAR[prev] + ')');
    }, 900);
  };

  RoomViz.prototype.levelOf = function (room) { return this.levels[room]; };
  RoomViz.prototype.presenceOf = function (name) {
    var p = this.people[name];
    return p ? { room: p.room, confidence: p.confidence } : null;
  };

  global.RoomViz = RoomViz;
})(window);
