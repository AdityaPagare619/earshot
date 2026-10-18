/* EARSHOT phone second channel — UI logic.
 * Renders withheld cards + approval requests from EarshotChannel messages,
 * fires the real buzz (vibrate + audible + visual, never silent), and closes
 * the plan-hash-bound approval loop. Exposes window.EarshotPhone for tests.
 */
(function (g) {
  'use strict';

  var C = g.EarshotCrypto;
  var VIBRATE_MS = 200;

  // --- Buzz: pure path selection, unit-testable ---------------------------
  // Returns ordered list of paths that WILL fire. 'visual' is always present:
  // this function never returns an empty list (no silent failure).
  function resolveBuzzPaths(nav) {
    var paths = [];
    if (nav && typeof nav.vibrate === 'function') paths.push('vibrate');
    paths.push('audio');   // WebAudio beep, armed by user gesture
    paths.push('visual');  // card flash + banner pulse — always available
    return paths;
  }

  var audioCtx = null;
  function armAudio() {
    try {
      var AC = g.AudioContext || g.webkitAudioContext;
      if (AC && !audioCtx) audioCtx = new AC();
      if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
    } catch (e) { /* audio unavailable: visual path still fires */ }
  }

  function beep() {
    if (!audioCtx) return false;
    try {
      var o = audioCtx.createOscillator();
      var gn = audioCtx.createGain();
      o.type = 'sine'; o.frequency.value = 880;
      gn.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gn.gain.exponentialRampToValueAtTime(0.5, audioCtx.currentTime + 0.02);
      gn.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.28);
      o.connect(gn); gn.connect(audioCtx.destination);
      o.start(); o.stop(audioCtx.currentTime + 0.3);
      return true;
    } catch (e) { return false; }
  }

  // Fires the buzz; returns the list of paths that actually fired.
  function fireBuzz(nav, el) {
    var fired = [];
    try {
      if (nav && typeof nav.vibrate === 'function' && nav.vibrate(VIBRATE_MS)) fired.push('vibrate');
    } catch (e) { /* fall through to fallbacks */ }
    if (beep()) fired.push('audio');
    if (el && el.classList) {
      el.classList.remove('flash');
      void el.offsetWidth; // restart CSS animation
      el.classList.add('flash');
      fired.push('visual');
    } else {
      fired.push('visual'); // page-level flash banner handled by caller
    }
    return fired;
  }

  // --- Formatting ----------------------------------------------------------
  function money(cents, currency) {
    var sym = currency === 'INR' ? '₹' : (currency === 'USD' ? '$' : currency + ' ');
    return sym + (cents / 100).toFixed(2);
  }
  function timeStr(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // --- Phone app ------------------------------------------------------------
  function PhoneApp(root) {
    this.root = root;
    this.channel = null;
    this.pendingApprovals = {}; // request_id -> {planHash, expiresAt}
    this.buzzArmed = false;
  }

  PhoneApp.prototype.logBuzz = function (paths) {
    var el = this.root.querySelector('#buzz-line');
    if (el) el.innerHTML = 'last nudge — <b>' + esc(paths.join(' + ')) + '</b>';
  };

  PhoneApp.prototype.setStatus = function (mode, text) {
    var el = this.root.querySelector('#status-chip');
    if (el) { el.className = 'status-chip ' + mode; el.textContent = text; }
  };

  PhoneApp.prototype.connect = function (room, backend) {
    var self = this;
    armAudio(); this.buzzArmed = true;
    this.setStatus('wait', 'connecting…');
    this.channel = new g.EarshotChannel({ room: room, backend: backend || 'broadcast' });
    return this.channel.start(function (msg) { self.onMessage(msg); })
      .then(function () {
        self.setStatus('live', '● live — room ' + esc(room));
        return true;
      })
      .catch(function (err) {
        self.setStatus('wait', 'channel unavailable');
        self.showError('Second channel unavailable: ' + err.message +
          '. Open this page over http (mock_gateway.py) in the same origin as the simulator.');
        throw err;
      });
  };

  PhoneApp.prototype.showError = function (text) {
    var list = this.root.querySelector('#inbox');
    var d = document.createElement('div');
    d.className = 'card';
    d.innerHTML = '<p class="result-bad">' + esc(text) + '</p>';
    list.prepend(d);
  };

  PhoneApp.prototype.onMessage = function (msg) {
    if (msg.type === 'withheld_card' || msg.type === 'notification_card') this.renderCard(msg);
    else if (msg.type === 'approval_request') this.renderApproval(msg);
    else if (msg.type === 'approval_result') this.renderResult(msg);
  };

  PhoneApp.prototype.renderCard = function (msg) {
    var card = msg.card || {};
    var list = this.root.querySelector('#inbox');
    var empty = list.querySelector('.empty');
    if (empty) empty.remove();
    var d = document.createElement('div');
    d.className = 'card'; d.id = 'card-' + (msg.id || Date.now());
    var silent = card.level === 'SILENT';
    var detailHtml = (silent && !card.revealed)
      ? '<p class="card-detail masked">🔇 silenced item — tap to reveal privately</p>'
      : '<p class="card-detail">' + esc(card.detail || '') + '</p>';
    d.innerHTML =
      '<div class="card-head"><span class="level ' + esc(card.level || '') + '">' + esc(card.level || '') + '</span>' +
      '<span class="card-time">' + esc(timeStr(msg.ts)) + '</span></div>' +
      '<p class="card-title">' + esc(card.title || 'Private item') + '</p>' +
      detailHtml +
      (card.speaker_heard ? '<p class="speaker-line">🔊 room heard: “' + esc(card.speaker_heard) + '”</p>' : '') +
      '<details class="why"><summary>why was this withheld?</summary><p>Under your rule <code>' +
      esc(card.winning_rule || 'default: unknown topics are HIGH') + '</code>' +
      ((card.reasons || []).length ? ' — ' + esc(card.reasons.join('; ')) : '') + '</p></details>';
    if (silent) {
      var self = this;
      d.style.cursor = 'pointer';
      d.addEventListener('click', function () {
        var det = d.querySelector('.card-detail');
        if (det && det.classList.contains('masked')) {
          det.classList.remove('masked');
          det.textContent = card.detail || '';
        }
      });
      void self;
    }
    list.prepend(d);
    var fired = fireBuzz(g.navigator, d);
    this.logBuzz(fired);
  };

  PhoneApp.prototype.renderApproval = function (msg) {
    var self = this;
    var plan = msg.plan || {};
    var items = (plan.items || []).map(function (it) {
      return '<tr><td>' + esc(it.qty || 1) + '× ' + esc(it.name || '') + '</td><td></td></tr>';
    }).join('');
    this.pendingApprovals[msg.request_id] = { planHash: msg.plan_hash, expiresAt: msg.expires_at };
    var list = this.root.querySelector('#inbox');
    var empty = list.querySelector('.empty');
    if (empty) empty.remove();
    var d = document.createElement('div');
    d.className = 'card approval'; d.id = 'apr-' + esc(msg.request_id);
    d.innerHTML =
      '<div class="card-head"><span class="level EXISTENCE">approval</span>' +
      '<span class="card-time">' + esc(timeStr(msg.ts)) + '</span></div>' +
      '<p class="card-title">The room heard: “' + esc(msg.speaker_heard || '') + '”</p>' +
      '<p class="card-detail">You see the exact plan:</p>' +
      '<table class="plan-table">' + items +
      '<tr><td>' + esc(plan.merchant || '') + '</td><td></td></tr>' +
      '<tr class="plan-total"><td>Total</td><td>' + esc(money(plan.amount_cents || 0, plan.currency)) + '</td></tr></table>' +
      '<p class="plan-hash">plan hash ' + esc((msg.plan_hash || '').slice(0, 24)) + '…</p>' +
      '<div class="btn-row"><button class="btn approve">Approve</button>' +
      '<button class="btn deny">Deny</button></div>' +
      '<p class="countdown"></p>';
    list.prepend(d);
    var fired = fireBuzz(g.navigator, d);
    this.logBuzz(fired);

    var done = false;
    var finish = function (decision) {
      if (done) return; done = true;
      self.decide(msg.request_id, decision).then(function () {
        d.querySelector('.btn-row').innerHTML =
          '<p>sent <b>' + esc(decision) + '</b> — waiting for the gateway…</p>';
      });
    };
    d.querySelector('.btn.approve').addEventListener('click', function () { finish('approve'); });
    d.querySelector('.btn.deny').addEventListener('click', function () { finish('deny'); });

    // expiry countdown; auto-expire display
    var cd = d.querySelector('.countdown');
    var tick = setInterval(function () {
      var left = Math.max(0, Math.round((msg.expires_at - Date.now()) / 1000));
      if (left <= 0) {
        clearInterval(tick);
        cd.textContent = 'expired — request a fresh approval';
        d.querySelector('.btn-row').innerHTML = '';
        delete self.pendingApprovals[msg.request_id];
      } else cd.textContent = 'expires in ' + left + 's';
    }, 1000);
    tick && cd && (cd.textContent = 'expires soon');
  };

  PhoneApp.prototype.decide = async function (requestId, decision) {
    var rec = this.pendingApprovals[requestId];
    if (!rec) throw new Error('unknown or expired request');
    var ts = Date.now();
    var token = await C.makeApprovalToken({
      planHash: rec.planHash, requestId: requestId, decision: decision, ts: ts
    });
    return this.channel.send({
      type: 'approval_token', trace_id: 'tr_' + requestId,
      ts: ts, request_id: requestId, decision: decision, token: token
    });
  };

  PhoneApp.prototype.renderResult = function (msg) {
    var d = this.root.querySelector('#apr-' + CSS.escape(msg.request_id));
    delete this.pendingApprovals[msg.request_id];
    var html;
    if (msg.outcome === 'executed') html = '<p class="result-ok">✅ approved — executed. ' + esc(msg.note || '') + '</p>';
    else if (msg.outcome === 'denied') html = '<p class="result-bad">🚫 denied — nothing was ordered.</p>';
    else html = '<p class="result-bad">⚠️ ' + esc(msg.outcome) + ' — ' + esc(msg.note || '') + '</p>';
    if (d) {
      var row = d.querySelector('.btn-row');
      if (row) row.innerHTML = html;
    } else {
      this.showError('approval result for unknown request: ' + msg.outcome);
    }
  };

  g.EarshotPhone = {
    PhoneApp: PhoneApp,
    resolveBuzzPaths: resolveBuzzPaths,
    fireBuzz: fireBuzz,
    VIBRATE_MS: VIBRATE_MS
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
