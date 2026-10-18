// EARSHOT phone-channel: crypto unit tests (Node >= 18).
// Verifies plan-hash binding: tamper, replay, expiry, unknown-id all rejected.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const dir = dirname(fileURLToPath(import.meta.url));
const phoneDir = join(dir, '..');
for (const f of ['crypto.js']) {
  eval(readFileSync(join(phoneDir, f), 'utf8')); // attaches globalThis.EarshotCrypto
}
const C = globalThis.EarshotCrypto;
assert(C, 'EarshotCrypto failed to load');

const plan = { action: 'reorder', merchant: 'Blinkit',
  items: [{ name: 'Detergent 1kg', qty: 1 }], amount_cents: 1240, currency: 'INR' };

// 1. canonicalization is order-independent and deterministic
const shuffled = { currency: 'INR', amount_cents: 1240,
  items: [{ qty: 1, name: 'Detergent 1kg' }], merchant: 'Blinkit', action: 'reorder' };
assert.strictEqual(await C.planHash(plan), await C.planHash(shuffled));
console.log('ok  canonicalization order-independent');

// 2. hash changes when any plan field changes
const evil = { ...plan, amount_cents: 999900 };
assert.notStrictEqual(await C.planHash(plan), await C.planHash(evil));
console.log('ok  plan tampering changes plan_hash');

// 3. happy path: approve verifies
const ph = await C.planHash(plan);
const store = new Map();
store.set('apr_1', { planHash: ph, expiresAt: Date.now() + 120000, consumed: false });
const ts = Date.now();
const tok = await C.makeApprovalToken({ planHash: ph, requestId: 'apr_1', decision: 'approve', ts });
let r = await C.verifyApprovalToken({ store, requestId: 'apr_1', decision: 'approve', ts, token: tok, nowMs: Date.now() });
assert.deepStrictEqual(r, { ok: true, outcome: 'executed' });
console.log('ok  approve round trip verifies -> executed');

// 4. deny verifies
store.set('apr_2', { planHash: ph, expiresAt: Date.now() + 120000, consumed: false });
const tok2 = await C.makeApprovalToken({ planHash: ph, requestId: 'apr_2', decision: 'deny', ts });
r = await C.verifyApprovalToken({ store, requestId: 'apr_2', decision: 'deny', ts, token: tok2, nowMs: Date.now() });
assert.deepStrictEqual(r, { ok: true, outcome: 'denied' });
console.log('ok  deny verifies -> denied');

// 5. replay rejected (apr_1 already consumed)
r = await C.verifyApprovalToken({ store, requestId: 'apr_1', decision: 'approve', ts, token: tok, nowMs: Date.now() });
assert.strictEqual(r.outcome, 'rejected:replay');
console.log('ok  replay rejected');

// 6. tampered plan rejected
store.set('apr_3', { planHash: ph, expiresAt: Date.now() + 120000, consumed: false });
const evilTok = await C.makeApprovalToken({ planHash: await C.planHash(evil), requestId: 'apr_3', decision: 'approve', ts });
r = await C.verifyApprovalToken({ store, requestId: 'apr_3', decision: 'approve', ts, token: evilTok, nowMs: Date.now() });
assert.strictEqual(r.outcome, 'rejected:plan_mismatch');
console.log('ok  tampered plan rejected (plan_mismatch)');

// 7. expired rejected
store.set('apr_4', { planHash: ph, expiresAt: Date.now() - 1, consumed: false });
const tok4 = await C.makeApprovalToken({ planHash: ph, requestId: 'apr_4', decision: 'approve', ts });
r = await C.verifyApprovalToken({ store, requestId: 'apr_4', decision: 'approve', ts, token: tok4, nowMs: Date.now() });
assert.strictEqual(r.outcome, 'rejected:expired');
console.log('ok  expired rejected');

// 8. unknown request rejected
r = await C.verifyApprovalToken({ store, requestId: 'apr_nope', decision: 'approve', ts, token: tok, nowMs: Date.now() });
assert.strictEqual(r.outcome, 'rejected:unknown');
console.log('ok  unknown request rejected');

// 9. wrong decision string rejected
store.set('apr_5', { planHash: ph, expiresAt: Date.now() + 120000, consumed: false });
r = await C.verifyApprovalToken({ store, requestId: 'apr_5', decision: 'maybe', ts, token: tok, nowMs: Date.now() });
assert.strictEqual(r.outcome, 'rejected:bad_decision');
console.log('ok  bad decision rejected');

console.log('\nALL CRYPTO TESTS PASSED');
