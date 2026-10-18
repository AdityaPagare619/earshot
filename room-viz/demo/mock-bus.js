/* Mock event bus until simulator-shell merges.
 * Shape EXACTLY matches the frozen contract in room-viz.js / README.md.
 * The simulator shell will replace this with its real bus — same event names.
 */
(function (global) {
  'use strict';

  function MockBus(logEl) {
    this.target = document.createElement('div'); // EventTarget
    this.logEl = logEl || null;
    this.t0 = performance.now();
  }

  MockBus.prototype.addEventListener = function (t, cb, o) {
    this.target.addEventListener(t, cb, o);
  };

  MockBus.prototype.emit = function (type, detail) {
    var ev = new CustomEvent(type, { detail: detail });
    this.target.dispatchEvent(ev);
    this._log(type, detail);
  };

  MockBus.prototype._log = function (type, detail) {
    if (!this.logEl) return;
    var t = ((performance.now() - this.t0) / 1000).toFixed(1);
    var row = document.createElement('div');
    row.className = 'bus-row';
    var short = type.replace('earshot:', '');
    row.innerHTML = '<span class="bus-t">' + t + 's</span>' +
      '<span class="bus-type">' + short + '</span>' +
      '<span class="bus-d">' + escapeHtml(JSON.stringify(detail)) + '</span>';
    this.logEl.prepend(row);
    while (this.logEl.children.length > 14) this.logEl.lastChild.remove();
  };

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  global.MockBus = MockBus;
})(window);
