/* EARSHOT second-channel crypto — pure functions, no DOM.
 * Loads as a classic <script> (browser) or via eval/require (Node tests).
 * Exposes: globalThis.EarshotCrypto = { canonicalize, sha256Hex, planHash,
 *   makeApprovalToken, verifyApprovalToken }
 */
(function (g) {
  'use strict';

  // Deterministic canonical JSON: object keys sorted recursively, no whitespace.
  function canonicalize(v) {
    if (v === null || v === undefined) return 'null';
    if (Array.isArray(v)) return '[' + v.map(canonicalize).join(',') + ']';
    if (typeof v === 'object') {
      return '{' + Object.keys(v).sort().map(function (k) {
        return JSON.stringify(k) + ':' + canonicalize(v[k]);
      }).join(',') + '}';
    }
    return JSON.stringify(v);
  }

  function bytesToHex(bytes) {
    return Array.prototype.map.call(bytes, function (b) {
      return b.toString(16).padStart(2, '0');
    }).join('');
  }

  // Works in browsers (crypto.subtle) and Node >= 18 (globalThis.crypto.subtle).
  async function sha256Hex(str) {
    var subtle = g.crypto && g.crypto.subtle;
    if (!subtle) throw new Error('sha256Hex: no SubtleCrypto available');
    var data = new TextEncoder().encode(str);
    var digest = await subtle.digest('SHA-256', data);
    return bytesToHex(new Uint8Array(digest));
  }

  async function planHash(plan) {
    return sha256Hex(canonicalize(plan));
  }

  // token = sha256(plan_hash | request_id | decision | ts)
  async function makeApprovalToken(o) {
    var parts = [o.planHash, o.requestId, o.decision, String(o.ts)];
    return sha256Hex(parts.join('|'));
  }

  // Server-side verification. `store` maps request_id -> {planHash, expiresAt, consumed}.
  // Returns { ok:true, outcome } or { ok:false, outcome:'rejected:...' }.
  async function verifyApprovalToken(o) {
    var rec = o.store.get(o.requestId);
    if (!rec) return { ok: false, outcome: 'rejected:unknown' };
    if (o.nowMs > rec.expiresAt) return { ok: false, outcome: 'rejected:expired' };
    if (rec.consumed) return { ok: false, outcome: 'rejected:replay' };
    if (o.decision !== 'approve' && o.decision !== 'deny')
      return { ok: false, outcome: 'rejected:bad_decision' };
    var expect = await makeApprovalToken({
      planHash: rec.planHash, requestId: o.requestId,
      decision: o.decision, ts: o.ts
    });
    if (expect !== o.token) return { ok: false, outcome: 'rejected:plan_mismatch' };
    rec.consumed = true;
    return { ok: true, outcome: o.decision === 'approve' ? 'executed' : 'denied' };
  }

  g.EarshotCrypto = {
    canonicalize: canonicalize,
    sha256Hex: sha256Hex,
    planHash: planHash,
    makeApprovalToken: makeApprovalToken,
    verifyApprovalToken: verifyApprovalToken
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
