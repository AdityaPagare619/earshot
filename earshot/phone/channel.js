/* EarshotChannel — second-channel transport for earshot/phone.
 * Backends: 'broadcast' (BroadcastChannel, demo default — zero server) and
 * 'http' (SSE GET /second-channel/events + POST /second-channel/respond, per
 * PROTOCOL.md — implemented by the mcp-server lane; client code here is ready).
 * Message validation: v===1, known types; unknown types ignored (Postel).
 * Loads as a classic <script>; also loadable in Node (BroadcastChannel exists).
 */
(function (g) {
  'use strict';

  var KNOWN_TYPES = {
    withheld_card: 1, notification_card: 1, approval_request: 1,
    approval_token: 1, approval_result: 1
  };

  function EarshotChannel(opts) {
    opts = opts || {};
    this.room = opts.room || 'demo';
    this.backend = opts.backend || 'broadcast';
    this.httpBase = (opts.httpBase || '').replace(/\/$/, '');
    this._bc = null;
    this._es = null;
    this._handler = null;
    this._connected = false;
  }

  EarshotChannel.prototype.channelName = function () {
    return 'earshot-2ch-' + this.room;
  };

  EarshotChannel.prototype.isSupported = function () {
    if (this.backend === 'broadcast') return typeof g.BroadcastChannel === 'function';
    if (this.backend === 'http') {
      return typeof g.EventSource === 'function' && typeof g.fetch === 'function';
    }
    return false;
  };

  EarshotChannel.prototype.start = function (onMessage) {
    var self = this;
    this._handler = onMessage;
    if (this.backend === 'broadcast') {
      if (!this.isSupported()) throw new Error('BroadcastChannel unavailable');
      this._bc = new g.BroadcastChannel(this.channelName());
      this._bc.onmessage = function (ev) { self._ingest(ev.data); };
      this._connected = true;
      return Promise.resolve({ backend: 'broadcast', room: this.room });
    }
    if (this.backend === 'http') {
      if (!this.isSupported()) throw new Error('EventSource/fetch unavailable');
      var url = this.httpBase + '/second-channel/events?room=' + encodeURIComponent(this.room);
      this._es = new g.EventSource(url);
      this._es.addEventListener('earshot', function (ev) {
        try { self._ingest(JSON.parse(ev.data)); } catch (e) { /* malformed: ignore */ }
      });
      this._es.onerror = function () { self._connected = false; };
      this._es.onopen = function () { self._connected = true; };
      return Promise.resolve({ backend: 'http', room: this.room });
    }
    return Promise.reject(new Error('unknown backend: ' + this.backend));
  };

  EarshotChannel.prototype._ingest = function (msg) {
    if (!msg || msg.v !== 1 || !KNOWN_TYPES[msg.type]) return; // Postel: ignore
    if (typeof this._handler === 'function') {
      try { this._handler(msg); } catch (e) { /* handler errors must not kill channel */ }
    }
  };

  EarshotChannel.prototype.send = function (msg) {
    msg = Object.assign({ v: 1, room: this.room }, msg);
    if (this.backend === 'broadcast') {
      if (!this._bc) throw new Error('channel not started');
      this._bc.postMessage(msg);
      return Promise.resolve(true);
    }
    // http backend
    return g.fetch(this.httpBase + '/second-channel/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg)
    }).then(function (r) { return r.ok; });
  };

  EarshotChannel.prototype.connected = function () { return this._connected; };

  EarshotChannel.prototype.close = function () {
    if (this._bc) { this._bc.close(); this._bc = null; }
    if (this._es) { this._es.close(); this._es = null; }
    this._connected = false;
  };

  g.EarshotChannel = EarshotChannel;
})(typeof globalThis !== 'undefined' ? globalThis : this);
